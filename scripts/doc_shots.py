#!/usr/bin/env python3
"""Screenshots for the developer docs (docs/img/), taken in the simulator from the scripts in docs/shots/.

  doc_shots.py            write docs/img/<name>.png for every entry of docs/shots/shots.json
  doc_shots.py --check    fail if a committed picture differs from a fresh one (pixel for pixel)

Entry kinds: "template" (a new app from the C or Rust template), "app" (a project directory under docs/ or a sample
under examples/apps/), "face" (a face directory, rendered full size). The simulator's clock is pinned and nothing random
changes, so a picture is the same on every run, but it changes with the simulator build: --check belongs in the CI that
builds the simulator, not with a downloaded one.
"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDK = HERE.parent
DOCS = SDK / "docs"
for cand in (SDK / "tools" / "s3w-cli", SDK / "cli"):
    if (cand / "s3w_cli").is_dir():
        sys.path.insert(0, str(cand))

from s3w_cli import cli, sim  # noqa: E402


def sample_dir(name):
    for base in (SDK / "examples" / "apps", SDK.parent / "apps"):  # the public layout, then the private one
        if (base / name / "manifest.json").exists():
            return base / name
    raise SystemExit(f"doc_shots: no sample app '{name}'")


def render(entry, out, tmp, sim_path):
    kind = entry["kind"]
    script = DOCS / entry["script"] if "script" in entry else None
    if kind == "face":
        cmd = [sim_path, "--face", str(DOCS / entry["project"]), "--screenshot", str(out)]
        if script:
            cmd += ["--script", str(script)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"doc_shots: {entry['name']}: {r.stderr.strip()}")
        return
    if kind == "template":
        d = Path(tmp) / entry["name"]
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["new", str(d), "--lang", entry.get("lang", "c")])
    elif "sample" in entry:
        # The first-party samples are preinstalled apps on the watch and the simulator refuses their ids for a
        # package: copy the sample (with the common/ folder its sources include) under another id.
        src = sample_dir(entry["sample"])
        d = Path(tmp) / "apps" / src.name
        shutil.copytree(src.parent / "common", d.parent / "common", dirs_exist_ok=True)
        shutil.copytree(src, d, ignore=shutil.ignore_patterns("build", "target", "__pycache__"))
        manifest = json.loads((d / "manifest.json").read_text())
        manifest["id"] = "dev.docs." + src.name
        (d / "manifest.json").write_text(json.dumps(manifest, indent=2))
    else:
        d = DOCS / entry["project"]
    args = ["run-sim", str(d), "--sim", sim_path, "--screenshot", str(out)]
    if script:
        args += ["--script", str(script)]
    with contextlib.redirect_stdout(io.StringIO()):
        rc = cli.main(args)
    if rc:
        raise SystemExit(f"doc_shots: {entry['name']}: run-sim exited {rc}")


def main(argv):
    check = "--check" in argv
    shots = json.loads((DOCS / "shots" / "shots.json").read_text())["shots"]
    sim_path = sim.find_sim()
    img = DOCS / "img"
    img.mkdir(exist_ok=True)
    stale = []
    with tempfile.TemporaryDirectory() as tmp:
        for entry in shots:
            target = img / f"{entry['name']}.png"
            out = Path(tmp) / f"{entry['name']}.png" if check else target
            render(entry, out, tmp, sim_path)
            if check and (not target.exists() or target.read_bytes() != out.read_bytes()):
                stale.append(entry["name"])
    if stale:
        sys.exit("doc_shots: stale pictures: " + ", ".join(stale) + " (run sdk/tools/doc_shots.py after an intended change)")
    print(f"doc_shots: {len(shots)} pictures " + ("fresh" if check else "written"))


if __name__ == "__main__":
    main(sys.argv[1:])
