"""`s3w run-sim`: the firmware simulator with the app installed, rebuilt and reloaded on change."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import simmgr
from .project import REPO, BuildError

POLL_S = 0.5  # how often the sources are checked; the simulator checks the package as often


def find_sim(path=None):
    """--sim, $S3W_SIM, a checkout's build/sim, then the newest `s3w sim install`ed one."""
    cands = [path, os.environ.get("S3W_SIM"), str(REPO / "build" / "sim" / "s3w_sim"), simmgr.latest_installed()]
    for c in cands:
        if c and Path(c).exists():
            return str(c)
    raise BuildError("no simulator: run `s3w sim install`, set S3W_SIM to the s3w_sim binary or pass --sim")


def sim_info(sim):
    """`s3w_sim --version` as a dict ({version, api_level, face_api}), or None for a simulator without it."""
    try:
        out = subprocess.run([sim, "--version"], capture_output=True, text=True, timeout=10).stdout
        return json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _stamps(files):
    out = {}
    for f in files:
        try:
            st = f.stat()
            out[str(f)] = (st.st_mtime_ns, st.st_size)
        except OSError:
            pass
    return out


def run(project, sim=None, script=None, screenshot=None, watch=True):
    """Builds and packs (unsigned: the simulator accepts it), then runs the simulator with --dev.
    Headless with a script or screenshot; otherwise a window, rebuilt on every source change."""
    sim = find_sim(sim)
    info = sim_info(sim)
    if info and project.manifest.get("api_level", 0) > info["api_level"]:
        print(f"warning: the app asks for api_level {project.manifest['api_level']}, this simulator runs {info['api_level']}"
              " (`s3w sim update`)", file=sys.stderr)
    project.build()
    pkg = project.pack(key=None, out=project.build_dir / f"{project.id}.sim.s3app")
    cmd = [sim, "--dev", str(pkg)]
    if script:
        cmd += ["--script", script]
    if screenshot:
        cmd += ["--screenshot", screenshot]
    if script or screenshot:
        return subprocess.run(cmd).returncode
    proc = subprocess.Popen(cmd)
    print(f"simulator running {project.id}; editing {project.dir.name}/ rebuilds and reloads it (Ctrl-C ends)")
    seen = _stamps(project.sources())
    try:
        while proc.poll() is None:
            time.sleep(POLL_S)
            if not watch:
                continue
            now = _stamps(project.sources())
            if now == seen:
                continue
            seen = now
            t0 = time.time()
            try:
                project.build(quiet=True)
                project.pack(key=None, out=pkg)  # atomic replace: the simulator reloads it
                print(f"rebuilt in {time.time() - t0:.1f} s")
            except BuildError as e:
                print(f"build failed (the simulator keeps the last build):\n{e}", file=sys.stderr)
    except KeyboardInterrupt:
        proc.terminate()
    return proc.wait()
