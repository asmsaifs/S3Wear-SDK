#!/usr/bin/env python3
"""Checks the developer docs (docs/): structure, links and every code block marked for checking.

  check_docs.py [--require] [--only structure|snippets]

Structure: nav.json lists every page, every relative link and image resolves (with its #anchor), nothing private is named.
Snippets (fenced blocks whose info string starts with one of these; `project=NAME` ties a block to docs/projects/NAME,
`template=c|rust` to the template's source with the name Counter):
  c-check         a C app: built with the s3w CLI (the same flags, import check and memory as `s3w build`)
  rust-check      a Rust app lib.rs: built in a project from the Rust template
  manifest-check  a manifest.json: checked against the rules, and installed in the simulator when there is one
  face-check      a face.json: checked by the simulator's parser (`s3w_sim --check-face`)
A block whose tool is missing (clang, cargo, the simulator) is skipped, unless --require (CI) makes that an error.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDK = HERE.parent
DOCS = SDK / "docs"
for cand in (SDK / "tools" / "s3w-cli", SDK / "cli"):  # the private layout, then the public one
    if (cand / "s3w_cli").is_dir():
        sys.path.insert(0, str(cand))
sys.path.insert(0, str(HERE))
import gen_api_docs  # noqa: E402  (api_level_of)

FORBIDDEN = [
    (r"docs/\d\d\b", "a private doc"),
    (r"\bP\d{1,2}-\d\d\b", "a task id"),
    (r"firmware/(components|main|simulator|test)", "a private path"),
    (r"tools/(store|release|ota|export_sdk)", "a private tool"),
    (r"build/sim/", "a private build path"),
]
KINDS = ("c-check", "rust-check", "manifest-check", "face-check")
FENCE = re.compile(r"^```([^\n]*)\n(.*?)^```[ \t]*$", re.S | re.M)


class Problems(list):
    def add(self, where, msg):
        self.append(f"{where}: {msg}")


def pages():
    return sorted(p for p in DOCS.rglob("*.md"))


def rel(p):
    return str(Path(p).relative_to(DOCS))


def blocks(text):
    for m in FENCE.finditer(text):
        info = m.group(1).split()
        yield (info[0] if info else ""), dict(a.split("=", 1) for a in info[1:] if "=" in a), m.group(2), text.count("\n", 0, m.start()) + 1


def slug(heading):
    s = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return s.replace(" ", "-")


def anchors(text):
    out = set()
    for h in re.findall(r"^#{1,6}\s+(.+?)\s*$", FENCE.sub("", text), re.M):
        out.add(slug(re.sub(r"`", "", h)))
    return out


# --- structure ---------------------------------------------------------------------------------------

def check_structure():
    probs = Problems()
    nav = json.loads((DOCS / "nav.json").read_text())
    listed = [p["path"] for s in nav["sections"] for p in s["pages"]]
    for path in listed:
        if not (DOCS / path).is_file():
            probs.add("nav.json", f"{path} does not exist")
    if len(set(listed)) != len(listed):
        probs.add("nav.json", "a page is listed twice")
    for p in pages():
        r = rel(p)
        if not r.startswith(("api/", "projects/")) and r not in listed:
            probs.add(r, "is not in nav.json")
    texts = {rel(p): p.read_text() for p in pages()}
    index = texts.get("api/index.md", "")
    for r in texts:
        if r.startswith("api/") and r != "api/index.md" and Path(r).name not in index:
            probs.add(r, "is not linked from api/index.md")
    for r, text in texts.items():
        body = FENCE.sub("", text)
        for pat, what in FORBIDDEN:
            if re.search(pat, body):
                probs.add(r, f"names {what} ({pat})")
        for m in re.finditer(r"!?\[[^\]]*\]\(([^)\s]+)\)", body):
            target = m.group(1)
            if re.match(r"[a-z]+:", target) or target.startswith("#") and False:
                continue
            path, _, frag = target.partition("#")
            dest = (DOCS / r).parent / path if path else DOCS / r
            dest = Path(os.path.normpath(dest))
            if not dest.exists():
                probs.add(r, f"link to {target} does not resolve")
            elif frag and dest.suffix == ".md":
                if frag not in anchors(dest.read_text()):
                    probs.add(r, f"link to {target}: no such heading")
    return probs


# --- snippets ----------------------------------------------------------------------------------------

def manifest_problems(m, api_level):
    from s3w_cli import rules  # the CLI's rules: the same ones `s3w check` applies
    return rules.manifest_problems(m, api_level)


def tool_clang():
    from s3w_cli.project import find_clang, BuildError
    try:
        find_clang()
        return True
    except BuildError:
        return False


def tool_rust():
    if not shutil.which("cargo") or not shutil.which("rustup"):
        return False
    out = subprocess.run(["rustup", "target", "list", "--installed"], capture_output=True, text=True).stdout
    return "wasm32-unknown-unknown" in out


def find_sim():
    from s3w_cli import sim
    try:
        return sim.find_sim()
    except Exception:
        return None


def build_with_cli(project_dir):
    from s3w_cli.project import BuildError, Project
    try:
        Project(project_dir).build(quiet=True)
        return None
    except BuildError as e:
        return str(e).strip().splitlines()[-1][:300] if str(e).strip() else "build failed"


def new_project(tmp, lang):
    from s3w_cli import cli
    dest = Path(tmp) / f"snippet-{lang}"
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        cli.main(["new", str(dest), "--lang", lang, "--id", "dev.docs.snippet"])
    return dest


def sim_install_check(sim, manifest_text):
    """Installs a do-nothing app with this manifest in the simulator: its package check is the authority."""
    from s3w_cli import cli
    from s3w_cli.project import BuildError, Project
    import io, contextlib
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "m"
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["new", str(d), "--lang", "c"])
        (d / "src" / "main.c").write_text('#include "s3w.h"\nvoid s3w_on_start(void) {}\n')
        (d / "manifest.json").write_text(manifest_text)
        script = Path(tmp) / "s.txt"
        script.write_text("wait 300\napp-is running\n")
        try:
            p = Project(d)
            p.build(quiet=True)
            pkg = p.pack(key=None, out=p.build_dir / "m.s3app")
        except BuildError as e:
            return f"build: {str(e).strip()[-200:]}"
        r = subprocess.run([sim, "--dev", str(pkg), "--script", str(script), "--screenshot", str(Path(tmp) / "o.png")],
                           capture_output=True, text=True, timeout=60)
        return None if r.returncode == 0 else (r.stderr.strip().splitlines() or ["the simulator refused the package"])[-1]


def check_snippets(require):
    probs = Problems()
    skipped = []
    have_clang, have_rust, sim = tool_clang(), tool_rust(), find_sim()
    api_level = gen_api_docs.api_level_of((SDK / "include" / "s3w.h").read_text())
    counts = {k: 0 for k in KINDS}
    with tempfile.TemporaryDirectory() as tmp:
        for p in pages():
            for kind, attrs, code, line in blocks(p.read_text()):
                if kind not in KINDS:
                    continue
                where = f"{rel(p)}:{line}"
                counts[kind] += 1
                project = attrs.get("project")
                if "template" in attrs:
                    t = SDK / "templates" / attrs["template"] / ("src/main.c" if attrs["template"] == "c" else "src/lib.rs")
                    want = t.read_text().replace("{{name}}", "Counter").replace("{{id}}", "dev.you.counter")
                    if want.strip() != code.strip():
                        probs.add(where, f"differs from the {attrs['template']} template (sdk/templates)")
                        continue
                if project:
                    pdir = DOCS / "projects" / project
                    want = (pdir / ("face.json" if kind == "face-check" else "src/main.c")).read_text()
                    if want.strip() != code.strip():
                        probs.add(where, f"differs from docs/projects/{project}")
                        continue
                if kind == "manifest-check":
                    try:
                        m = json.loads(code)
                    except ValueError as e:
                        probs.add(where, f"manifest is not JSON: {e}")
                        continue
                    for msg in manifest_problems(m, api_level):
                        probs.add(where, msg)
                    if sim:
                        why = sim_install_check(sim, code)
                        if why:
                            probs.add(where, f"the simulator refuses it: {why}")
                    else:
                        skipped.append(f"{where} (simulator)")
                elif kind == "face-check":
                    if not sim:
                        skipped.append(f"{where} (simulator)")
                        continue
                    f = Path(tmp) / "face.json"
                    f.write_text(code)
                    r = subprocess.run([sim, "--check-face", str(f)], capture_output=True, text=True)
                    if r.returncode != 0:
                        probs.add(where, r.stderr.strip() or "face.json refused")
                elif kind == "c-check":
                    if not have_clang:
                        skipped.append(f"{where} (clang)")
                        continue
                    if project:
                        why = build_with_cli(DOCS / "projects" / project)
                    else:
                        d = new_project(tmp, "c")
                        (d / "src" / "main.c").write_text(code)
                        why = build_with_cli(d)
                        shutil.rmtree(d)
                    if why:
                        probs.add(where, why)
                elif kind == "rust-check":
                    if not have_rust:
                        skipped.append(f"{where} (cargo + wasm32)")
                        continue
                    d = new_project(tmp, "rust")
                    (d / "src" / "lib.rs").write_text(code)
                    why = build_with_cli(d)
                    shutil.rmtree(d, ignore_errors=True)
                    if why:
                        probs.add(where, why)
    return probs, skipped, counts


def main(argv):
    require = "--require" in argv
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    probs = Problems()
    if only in (None, "structure"):
        probs += check_structure()
    skipped, counts = [], {}
    if only in (None, "snippets"):
        p, skipped, counts = check_snippets(require)
        probs += p
        if require:
            for s in skipped:
                probs.add(s, "skipped, but --require is set")
    if probs:
        sys.exit("check_docs: " + "\n  ".join([f"{len(probs)} problem(s)"] + list(probs)))
    if skipped:
        print("check_docs: skipped " + ", ".join(skipped))
    print("check_docs: ok" + (f" ({', '.join(f'{n} {k}' for k, n in counts.items())})" if counts else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
