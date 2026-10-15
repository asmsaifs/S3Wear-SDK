"""`s3w run-sim`: the firmware simulator with the app installed, rebuilt and reloaded on change."""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .project import REPO, BuildError

POLL_S = 0.5  # how often the sources are checked; the simulator checks the package as often


def find_sim(path=None):
    cands = [path, os.environ.get("S3W_SIM"), str(REPO / "build" / "sim" / "s3w_sim")]
    for c in cands:
        if c and Path(c).exists():
            return c
    raise BuildError("no simulator: set S3W_SIM to the s3w_sim binary or pass --sim")


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
