"""`s3w check`: the store's automated checks for an app or a watch face, run on your machine with the same code as the
store's job. Writes report.json and report.md (and the screenshots) and exits 1 when anything fails.

  s3w check [dir] [--developer LOGIN] [--profile FILE] [--changed FILE] [--published INDEX] [--out DIR]
            [--monkey-seconds N] [--seed N] [--sim PATH] [--blocklist FILE] [--verify-dns] [--no-run]

Checks (docs: Publish > Review guidelines): layout, listing, manifest / face.json, ownership, build, version, api_level,
icon, screenshots, run, monkey, budget, permissions, content, sizes. An error fails the submission, a warning goes to
the reviewer, a skip says why a check could not run (no simulator, no --developer, ...).
"""
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import __version__, rules, s3face
from . import sim as sim_mod
from .project import SDK, BuildError, Project, check_icon, module_info

FORMAT = 1
PACKAGE_MAX = {"app": 4 * 1024 * 1024, "face": 1024 * 1024}
DESCRIPTION_MAX = 200
RUN_FRAMES_MS = 12000        # the first screen, headless: 300 frames at the default 30 fps
MONKEY_SEGMENT_S = 30        # the monkey runs in segments; the app's handles and timers are read between them
P99_WARN_MS = 50             # over this at the 99th percentile: a warning (the watch is slower than the simulator)
WATCHDOG_MS = 250            # over this once: the watchdog would have counted a strike
LEAK_HANDLES = 24            # handles grown by this much, never fewer, over the monkey run: a leak
HANDLE_CAP = 480             # of 512
TIMER_CAP = 8
SIM_TIMEOUT_S = 300

IGNORED_DIRS = {"build", "target", ".git", "__pycache__", "node_modules"}
IGNORED_FILES = {".DS_Store", "Thumbs.db"}
BUILT_EXTENSIONS = {".wasm", ".s3app", ".s3face", ".so", ".dll", ".dylib", ".exe", ".a", ".o", ".zip", ".tar", ".gz",
                    ".pyc"}
APP_TOP = {"manifest.json", "listing.json", "icon.png", "Cargo.toml", "Cargo.lock", ".gitignore", "README", "README.md",
           "LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "CHANGELOG.md"}
FACE_TOP = {"face.json", "listing.json", ".gitignore", "README", "README.md", "LICENSE", "LICENSE.md", "LICENSE.txt",
            "NOTICE", "CHANGELOG.md"}
ASSET_EXTENSIONS = {".png", ".wav", ".json", ".txt", ".csv", ".dat", ".bin"}


class Check:
    def __init__(self, cid, title):
        self.id, self.title = cid, title
        self.findings, self.notes, self.skipped = [], [], False
        self.data = {}

    def error(self, msg, file=None):
        self.findings.append({"severity": "error", "message": msg, **({"file": file} if file else {})})

    def warn(self, msg, file=None):
        self.findings.append({"severity": "warning", "message": msg, **({"file": file} if file else {})})

    def skip(self, why):
        self.skipped = True
        self.notes.append(why)

    @property
    def status(self):
        if any(f["severity"] == "error" for f in self.findings):
            return "fail"
        if self.skipped:
            return "skip"
        return "warn" if self.findings else "pass"

    def as_dict(self):
        d = {"id": self.id, "title": self.title, "status": self.status, "findings": self.findings}
        if self.notes:
            d["notes"] = self.notes
        if self.data:
            d["data"] = self.data
        return d


class Options:
    def __init__(self, **kw):
        self.developer = None
        self.profile = None      # the developer's profile (a dict) with "namespaces"
        self.changed = None      # paths changed in the pull request, relative to the store root
        self.published = None    # the published index (a dict)
        self.out = None
        self.monkey_seconds = 120
        self.seed = 1
        self.sim = None
        self.blocklist = {}
        self.verify_dns = False
        self.dns_lookup = None   # fn(domain) -> [TXT strings]; tests replace it
        self.run = True
        self.only = None         # a list of check ids: run just those (tests, `--only`)
        self.__dict__.update(kw)


# --- helpers ----------------------------------------------------------------------------------------------------------

def sim_api():
    m = re.search(r"^#define\s+S3W_API_LEVEL\s+(\d+)", (SDK / "include" / "s3w.h").read_text(), re.M)
    return int(m.group(1)) if m else 1


def perm_map():
    """{function: (permissions, mode)} from the `@perm` tags in s3w.h; mode "all" or "any"."""
    text = (SDK / "include" / "s3w.h").read_text()
    out = {}
    for m in re.finditer(r"/\*(.*?)\*/\s*[^;{/]*?\b\w+\s*\([^;{]*?\)\s*S3W_(?:IMPORT|EXPORT)\((\w+)\)", text, re.S):
        tag = re.search(r"@perm\s+([^@\n*]+)", m.group(1))
        if tag:
            raw = tag.group(1).strip()
            names, mode = ([p.strip() for p in raw.split(" or ")], "any") if " or " in raw else (
                [p.strip() for p in raw.split(",")], "all")
            out[m.group(2)] = (names, mode)
    return out


def run_sim(sim_path, args, timeout=SIM_TIMEOUT_S):
    try:
        r = subprocess.run([sim_path, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", "the simulator did not finish in time"
    except OSError as e:
        return 127, "", str(e)
    return r.returncode, r.stdout, r.stderr


def last_line(text):
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def parse_stats(stdout):
    """The `app-stats: {...}` lines of a script's output."""
    out = []
    for ln in stdout.splitlines():
        if ln.startswith("app-stats: "):
            try:
                out.append(json.loads(ln[len("app-stats: "):]))
            except ValueError:
                pass
    return out


def end_reason(stdout, stderr):
    """Why the app ended, from the simulator's output: 'trapped ...', 'hung ...' or the monkey's message."""
    for ln in (stderr + "\n" + stdout).splitlines():
        if ln.startswith("monkey: the app ended"):
            return ln[len("monkey: "):]
    for ln in stdout.splitlines():
        m = re.match(r"app [\w.-]+: (trapped|hung|exited|stopped)\b(.*)", ln)
        if m:
            return (m.group(1) + m.group(2)).strip()
    # the script's own "bad command" line only says which line failed; the line before it says why
    why = [ln for ln in stderr.splitlines() if ln.strip() and "bad command:" not in ln]
    return (why[-1] if why else "") or last_line(stdout) or last_line(stderr) or "the simulator failed"


# --- the checks -------------------------------------------------------------------------------------------------------

def list_files(root):
    """The submission's files (relative paths), without build output and editor litter."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
        for fn in sorted(filenames):
            if fn not in IGNORED_FILES:
                files.append(Path(dirpath, fn).relative_to(root).as_posix())
    return files


def check_layout(ctx, c):
    root, kind = ctx["dir"], ctx["kind"]
    files = ctx["files"]
    for rel in files:
        ext = Path(rel).suffix.lower()
        parts = rel.split("/")
        if ext in BUILT_EXTENSIONS:
            c.error("a built file: the store builds from source", rel)
            continue
        ok = False
        if len(parts) == 1:
            ok = rel in (APP_TOP if kind == "app" else FACE_TOP) or (kind == "face" and ext == ".png")
        elif kind == "app":
            top = parts[0]
            ok = (top == "src") or (top == "include" and ext in {".h", ".hpp"}) or \
                 (top == "assets" and ext in ASSET_EXTENSIONS) or (top == "screens" and len(parts) == 2 and ext == ".txt")
        if not ok:
            c.error(f"not part of {'an app' if kind == 'app' else 'a face'}", rel)
    if "listing.json" not in files:
        c.error("listing.json is missing", "listing.json")
    if root.parent.name in ("apps", "faces") and ctx.get("id") and root.name != ctx["id"]:
        c.error(f"the folder is named '{root.name}', the id is '{ctx['id']}'")
    c.data["files"] = len(files)


def check_listing(ctx, c):
    path = ctx["dir"] / "listing.json"
    if not path.exists():
        c.skip("no listing.json (reported by layout)")
        return
    try:
        listing = json.loads(path.read_text())
    except ValueError as e:
        c.error(f"not JSON: {e}", "listing.json")
        return
    for msg in rules.listing_problems(listing, ctx.get("manifest") if ctx["kind"] == "app" else None):
        c.error(msg, "listing.json")
    if ctx["opts"].developer and isinstance(listing, dict) and listing.get("developer") not in (None, ctx["opts"].developer):
        c.error(f"developer is '{listing.get('developer')}', the submitter is '{ctx['opts'].developer}'", "listing.json")


def check_manifest(ctx, c):
    if ctx["kind"] == "app":
        if ctx.get("manifest") is None:
            c.error(ctx.get("manifest_error", "manifest.json is missing or not JSON"), "manifest.json")
            return
        for msg in rules.manifest_problems(ctx["manifest"], ctx["api_level"]):
            c.error(msg, "manifest.json")
        return
    if not ctx["sim"]:
        c.skip("no simulator: face.json is checked by the watch's own parser")
        return
    try:
        info = s3face.check_face_json(ctx["sim"], ctx["dir"] / "face.json")
        s3face.check_identity(info)
        ctx["face_info"] = info
    except BuildError as e:
        c.error(str(e), "face.json")


def _under(ident, prefixes):
    return any(ident.startswith(p + ".") for p in prefixes)


def namespaces(opts):
    ns = [f"io.github.{opts.developer.lower()}"] if opts.developer else []  # GitHub logins ignore case, ids are lower case
    ns += list((opts.profile or {}).get("namespaces", []))
    return ns


def check_ownership(ctx, c):
    opts, ident = ctx["opts"], ctx.get("id")
    if not opts.developer:
        c.skip("no --developer: ownership not checked")
        return
    if not ident:
        c.skip("no id to check")
        return
    if any(ident.startswith(p) for p in rules.RESERVED_PREFIXES) or ident in rules.BUILTIN_FACE_IDS:
        c.error(f"the id '{ident}' is reserved for the store")
        return
    ns = namespaces(opts)
    if not _under(ident, ns):
        c.error(f"the id '{ident}' is outside your namespaces ({', '.join(ns)})")
    for n in (opts.profile or {}).get("namespaces", []):
        if not ident.startswith(n + "."):
            continue
        if opts.verify_dns:
            lookup = opts.dns_lookup or dns_txt
            want = f"s3wear-developer={opts.developer}"
            try:
                found = lookup(n)
            except OSError as e:
                c.warn(f"could not look up the DNS TXT record of {n}: {e}")
                continue
            if want not in found:
                c.error(f"{n}: the DNS TXT record '{want}' was not found")
        else:
            c.warn(f"{n}: the DNS TXT record was not verified (--verify-dns)")
    for rel in opts.changed or []:
        parts = rel.split("/")
        if rel == "CODEOWNERS":
            continue  # the store's job compares it with what the profiles and folders give
        if len(parts) >= 2 and parts[0] in ("apps", "faces") and parts[1] != ident and not _under(parts[1], ns):
            c.error("changes another developer's app", rel)
        elif parts[0] == "developers" and rel != f"developers/{opts.developer}.json":
            c.error("changes another developer's profile", rel)
        elif parts[0] not in ("apps", "faces", "developers"):
            c.error("outside apps/, faces/ and developers/: a submission does not change the store's own files", rel)


def dns_txt(domain):
    r = subprocess.run(["dig", "+short", "TXT", domain], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise OSError(r.stderr.strip() or "dig failed")
    return [t.strip().strip('"') for t in r.stdout.split() if t.strip()]


def check_build(ctx, c):
    out = ctx["work"]
    try:
        if ctx["kind"] == "app":
            p = Project(ctx["dir"])
            p.build(quiet=True)
            pkg = p.pack(None, out / f"{p.id}.s3app")
            ctx["project"] = p
        else:
            if not ctx["sim"]:
                c.skip("no simulator: a face is built with it")
                return
            pkg, _ = s3face.pack(ctx["dir"], out / f"{ctx.get('id', 'face')}.s3face", None, ctx["sim"], render=True)
    except (BuildError, SystemExit) as e:
        c.error(str(e).strip() or "the build failed")
        return
    except OSError as e:
        c.error(str(e))
        return
    size = Path(pkg).stat().st_size
    ctx["pkg"] = Path(pkg)
    c.data["package_bytes"] = size
    if size > PACKAGE_MAX[ctx["kind"]]:
        c.error(f"the package is {size // 1024} KB, over {PACKAGE_MAX[ctx['kind']] // 1024} KB")


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def check_version(ctx, c):
    idx, ident = ctx["opts"].published, ctx.get("id")
    version = (ctx.get("manifest") or ctx.get("face_info") or {}).get("version")
    if idx is None:
        c.skip("no --published index: not compared with the published version")
        return
    if not ident or not version or not rules.SEMVER.match(str(version)):
        c.skip("no valid version to compare")
        return
    entries = [e for key in ("apps", "faces") for e in idx.get(key, []) if e.get("id") == ident]
    if not entries:
        c.data["published"] = None
        return
    have = max((e["version"] for e in entries), key=vtuple)
    c.data["published"] = have
    if vtuple(version) <= vtuple(have):
        c.error(f"version {version} is not higher than the published {have}")


def check_api_level(ctx, c):
    info = ctx.get("sim_info")
    if not info:
        c.skip("no simulator: the newest released api_level is unknown")
        return
    if ctx["kind"] == "app":
        want = (ctx.get("manifest") or {}).get("api_level")
        if isinstance(want, int) and want > info["api_level"]:
            c.error(f"api_level {want} is above the newest released firmware's {info['api_level']}")
    else:
        try:
            want = json.loads((ctx["dir"] / "face.json").read_text()).get("api", 1)
        except ValueError:
            return
        if isinstance(want, int) and want > info["face_api"]:
            c.error(f"face api {want} is above the newest released firmware's {info['face_api']}")


def check_icon_rule(ctx, c):
    if ctx["kind"] != "app":
        c.skip("a face has a preview instead (made by the build)")
        return
    icon = ctx["dir"] / "icon.png"
    if not icon.exists():
        c.warn("no icon.png: the launcher shows the first letter of the name")
        return
    try:
        check_icon(icon.read_bytes())
    except BuildError as e:
        c.error(str(e), "icon.png")


def check_screenshots(ctx, c):
    shots = ctx["work"] / "screens"
    shots.mkdir(parents=True, exist_ok=True)
    if ctx["kind"] == "face":
        prev = ctx["dir"] / "build" / s3face.PREVIEW
        if prev.exists():
            shutil.copy(prev, shots / "preview.png")
            ctx["shots"] = ["preview.png"]
        else:
            c.skip("the preview comes from the build")
        return
    if not (ctx.get("pkg") and ctx["sim"]):
        c.skip("needs the build and the simulator")
        return
    scripts = sorted((ctx["dir"] / "screens").glob("*.txt"))
    names = []
    jobs = [(s.stem, s) for s in scripts] or [("first-screen", None)]
    if not scripts:
        c.warn("no screens/*.txt: the store shows the first screen only")
    for name, script in jobs:
        out = shots / f"{name}.png"
        args = ["--dev", str(ctx["pkg"]), "--screenshot", str(out)] + (["--script", str(script)] if script else [])
        rc, so, se = run_sim(ctx["sim"], args, 120)
        if rc != 0 or not out.exists():
            c.error(f"screenshot script failed: {end_reason(so, se)}", f"screens/{name}.txt" if script else None)
        else:
            names.append(out.name)
    ctx["shots"] = names
    caps = (ctx.get("listing") or {}).get("screenshot_captions") if isinstance(ctx.get("listing"), dict) else None
    if isinstance(caps, list) and len(caps) > len(jobs):
        c.error(f"{len(caps)} screenshot captions for {len(jobs)} screenshot(s)", "listing.json")


def check_run(ctx, c):
    if not ctx["opts"].run:
        c.skip("--no-run")
        return
    if not ctx["sim"]:
        c.skip("no simulator")
        return
    if ctx["kind"] == "face":
        rc, so, se = run_sim(ctx["sim"], ["--face", str(ctx["dir"]), "--screenshot", str(ctx["work"] / "run.png")], 120)
        if rc != 0:
            c.error(f"the face does not render: {end_reason(so, se)}")
            return
        script = ctx["work"] / "aod.txt"
        script.write_text("wait 200\naod on\nwait 300\nlit 10\n")
        rc, so, se = run_sim(ctx["sim"], ["--face", str(ctx["dir"]), "--script", str(script), "--screenshot", str(ctx["work"] / "aod.png")], 120)
        if rc != 0:
            c.warn(f"the always-on layout lights 10 % or more of the pixels, or fails: {last_line(se)}")
        return
    if not ctx.get("pkg"):
        c.skip("needs the build")
        return
    script = ctx["work"] / "run.txt"
    script.write_text(f"wait {RUN_FRAMES_MS}\napp-stats\napp-is running\n")
    rc, so, se = run_sim(ctx["sim"], ["--dev", str(ctx["pkg"]), "--script", str(script), "--screenshot", str(ctx["work"] / "run.png")])
    stats = parse_stats(so)
    if rc != 0:
        c.error(f"the app did not survive its first {RUN_FRAMES_MS // 1000} s: {end_reason(so, se)}")
    if stats and stats[-1].get("state") == "running":
        ctx["run_stats"] = stats[-1]
        c.data["frames"] = stats[-1]["frames"]
        c.data["handles"] = stats[-1]["handles"]


def check_monkey(ctx, c):
    if ctx["kind"] != "app":
        c.skip("apps only")
        return
    if not ctx["opts"].run or ctx["opts"].monkey_seconds <= 0:
        c.skip("--no-run" if not ctx["opts"].run else "--monkey-seconds 0")
        return
    if not (ctx.get("pkg") and ctx["sim"]):
        c.skip("needs the build and the simulator")
        return
    opts = ctx["opts"]
    segments = max(1, math.ceil(opts.monkey_seconds / MONKEY_SEGMENT_S))
    lines = ["wait 1000", "app-stats"]
    for i in range(segments):
        lines += [f"monkey {min(MONKEY_SEGMENT_S, opts.monkey_seconds - i * MONKEY_SEGMENT_S)} {opts.seed + i}", "app-stats"]
    lines.append("app-is running")
    script = ctx["work"] / "monkey.txt"
    script.write_text("\n".join(lines) + "\n")
    rc, so, se = run_sim(ctx["sim"], ["--dev", str(ctx["pkg"]), "--script", str(script), "--screenshot", str(ctx["work"] / "monkey.png")])
    stats = [s for s in parse_stats(so) if s.get("state") == "running"]
    if rc != 0:
        c.error(f"random input stopped the app: {end_reason(so, se)}")
        return
    if len(stats) < 2:
        c.error("the monkey test gave no statistics")
        return
    ctx["monkey_stats"] = stats[-1]
    handles, timers = [s["handles"] for s in stats[1:]], [s["timers"] for s in stats[1:]]
    c.data.update({"seconds": opts.monkey_seconds, "seed": opts.seed, "handles": handles, "timers": timers,
                   "events": stats[-1]["calls"]["event"]["n"]})
    grew = lambda xs: len(xs) >= 2 and xs[-1] - xs[0] >= LEAK_HANDLES and all(b >= a for a, b in zip(xs, xs[1:]))
    if grew(handles) or handles[-1] >= HANDLE_CAP:
        c.error(f"UI handles leak: {handles[0]} after the first {MONKEY_SEGMENT_S} s, {handles[-1]} at the end (of 512): "
                "widgets are made and never deleted")
    t_grew = len(timers) >= 2 and timers[-1] - timers[0] >= 2 and all(b >= a for a, b in zip(timers, timers[1:]))
    if t_grew or timers[-1] >= TIMER_CAP:
        c.error(f"timers leak: {timers[0]} running after the first {MONKEY_SEGMENT_S} s, {timers[-1]} at the end (of {TIMER_CAP}): "
                "timers are started and never stopped")


def check_budget(ctx, c):
    stats = [s for s in (ctx.get("run_stats"), ctx.get("monkey_stats")) if s]
    if not stats:
        c.skip("no timing: the run did not happen")
        return
    worst = {}
    for s in stats:
        for kind, v in s["calls"].items():
            w = worst.setdefault(kind, {"n": 0, "p99": 0, "max": 0})
            w["n"] += v["n"]
            w["p99"], w["max"] = max(w["p99"], v["p99"]), max(w["max"], v["max"])
    c.data["callbacks_ms"] = worst
    for kind, w in worst.items():
        if w["max"] > WATCHDOG_MS:
            c.error(f"s3w_on_{kind} took {w['max']} ms once: over the {WATCHDOG_MS} ms watchdog limit")
        elif w["p99"] > P99_WARN_MS:
            c.warn(f"s3w_on_{kind}: {w['p99']} ms at the 99th percentile: the watch is slower than the simulator")


def check_permissions(ctx, c):
    p = ctx.get("project")
    if ctx["kind"] != "app" or p is None or not p.wasm.exists():
        c.skip("needs the build of an app")
        return
    perms = set((ctx.get("manifest") or {}).get("permissions", []))
    imports = {n for m, n, kind in module_info(p.wasm.read_bytes())[0] if m == "s3w"}
    needed = set()
    for fn, (names, mode) in perm_map().items():
        if fn not in imports:
            continue
        if mode == "any":
            if not set(names) & perms:
                c.error(f"calls {fn}, which needs one of: {', '.join(names)}")
            needed.update(names)
        else:
            for n in names:
                needed.add(n)
                if n not in perms:
                    c.error(f"calls {fn}, which needs the permission '{n}'")
    for perm in sorted(perms - needed - {"storage", "background", "location"}):
        c.warn(f"the permission '{perm}' is listed but no function that needs it is called")
    if (ctx.get("manifest") or {}).get("http_hosts") and "s3w_http_request" not in imports:
        c.warn("http_hosts is listed but the app never makes a request")


def check_content(ctx, c):
    extra = ctx["opts"].blocklist
    for rel in ctx.get("files", []):
        why = rules.file_problem(rel)
        if why:
            c.error(why, rel)
    texts = []
    m = ctx.get("manifest") if ctx["kind"] == "app" else (ctx.get("face_info") or {})
    face = {}
    if ctx["kind"] == "face":
        try:
            face = json.loads((ctx["dir"] / "face.json").read_text())
        except ValueError:
            pass
    src = m if ctx["kind"] == "app" else face
    for key in ("name", "description", "author"):
        if isinstance(src, dict) and isinstance(src.get(key), str):
            texts.append((f"{'manifest' if ctx['kind'] == 'app' else 'face'}.{key}", src[key]))
    listing = ctx.get("listing") if isinstance(ctx.get("listing"), dict) else {}
    if isinstance(listing.get("summary"), str):
        texts.append(("listing.summary", listing["summary"]))
    for i, cap in enumerate(listing.get("screenshot_captions", []) if isinstance(listing.get("screenshot_captions"), list) else []):
        if isinstance(cap, str):
            texts.append((f"listing.screenshot_captions[{i}]", cap))
    for key in ("permission_reasons", "http_reasons"):
        for k, v in (listing.get(key, {}) if isinstance(listing.get(key), dict) else {}).items():
            if isinstance(v, str):
                texts.append((f"listing.{key}.{k}", v))
    for label, text in texts:
        for msg in rules.text_problems(label, text, extra):
            c.error(msg)
    if isinstance(src, dict) and isinstance(src.get("name"), str):
        for msg in rules.name_problems(f"{'manifest' if ctx['kind'] == 'app' else 'face'}.name", src["name"]):
            c.error(msg)


def check_sizes(ctx, c):
    src = ctx.get("manifest") if ctx["kind"] == "app" else None
    if ctx["kind"] == "face":
        try:
            src = json.loads((ctx["dir"] / "face.json").read_text())
        except ValueError:
            return
    if not isinstance(src, dict):
        c.skip("no manifest or face.json to read")
        return
    limit = 31 if ctx["kind"] == "app" else 31
    name = src.get("name")
    if isinstance(name, str) and len(name.encode()) > limit:
        c.error(f"name is {len(name.encode())} bytes, at most {limit}")
    desc = src.get("description")
    if isinstance(desc, str) and len(desc) > DESCRIPTION_MAX:
        c.error(f"description is {len(desc)} characters, at most {DESCRIPTION_MAX}")


CHECKS = [
    ("layout", "Files and layout", check_layout),
    ("listing", "listing.json", check_listing),
    ("manifest", "Manifest / face.json", check_manifest),
    ("ownership", "Ids and ownership", check_ownership),
    ("build", "Build", check_build),
    ("version", "Version", check_version),
    ("api_level", "api_level", check_api_level),
    ("icon", "Icon", check_icon_rule),
    ("screenshots", "Screenshots", check_screenshots),
    ("run", "Run", check_run),
    ("monkey", "Monkey test", check_monkey),
    ("budget", "Callback time", check_budget),
    ("permissions", "Permissions", check_permissions),
    ("content", "Content policy", check_content),
    ("sizes", "Sizes", check_sizes),
]


def detect_kind(root):
    app, face = (root / "manifest.json").exists(), (root / "face.json").exists()
    if app == face:
        raise BuildError(f"{root}: needs exactly one of manifest.json (an app) or face.json (a face)")
    return "app" if app else "face"


def run_checks(target, opts):
    """Runs every check on the app or face in directory `target`. Returns the report (a dict)."""
    root = Path(target).resolve()
    kind = detect_kind(root)
    sim_path = None
    try:
        sim_path = sim_mod.find_sim(opts.sim)
    except BuildError:
        pass
    info = sim_mod.sim_info(sim_path) if sim_path else None
    work = Path(opts.out).resolve() if opts.out else Path(tempfile.mkdtemp(prefix="s3w_check_"))
    work.mkdir(parents=True, exist_ok=True)
    ctx = {"dir": root, "kind": kind, "opts": opts, "sim": sim_path, "sim_info": info, "work": work,
           "api_level": (info or {}).get("api_level") or sim_api()}
    try:
        if kind == "app":
            ctx["manifest"] = json.loads((root / "manifest.json").read_text())
            ctx["id"] = ctx["manifest"].get("id") if isinstance(ctx["manifest"], dict) else None
        else:
            ctx["id"] = json.loads((root / "face.json").read_text()).get("id")
    except ValueError as e:
        ctx["manifest"] = None
        ctx["manifest_error"] = f"not JSON: {e}"
        ctx["id"] = None
    if not isinstance(ctx.get("manifest"), dict) and kind == "app":
        ctx["manifest"] = None
    ctx["files"] = list_files(root)
    try:
        ctx["listing"] = json.loads((root / "listing.json").read_text())  # the listing check reports what is wrong with it
    except (OSError, ValueError):
        pass
    checks = []
    for cid, title, fn in CHECKS:
        if opts.only and cid not in opts.only:
            continue
        c = Check(cid, title)
        try:
            fn(ctx, c)
        except Exception as e:  # a bug in a check must not hide the others
            c.error(f"the check itself failed: {type(e).__name__}: {e}")
        checks.append(c)
    errors = sum(f["severity"] == "error" for c in checks for f in c.findings)
    warnings = sum(f["severity"] == "warning" for c in checks for f in c.findings)
    report = {
        "format": FORMAT,
        "target": {"kind": kind, "id": ctx.get("id"), "version": (ctx.get("manifest") or ctx.get("face_info") or {}).get("version"),
                   "dir": root.name},
        "tool": {"s3w": __version__, "simulator": info},
        "summary": {"errors": errors, "warnings": warnings, "ok": errors == 0,
                    "checks": {s: sum(c.status == s for c in checks) for s in ("pass", "warn", "fail", "skip")}},
        "checks": [c.as_dict() for c in checks],
        "screenshots": ctx.get("shots", []),
    }
    return report


# --- the Markdown summary (what the bot posts on the pull request) ---------------------------------------------------

ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}


def markdown(report):
    t, s = report["target"], report["summary"]
    lines = [f"## S3Wear check: {t['id'] or t['dir']} {t.get('version') or ''}".rstrip(), "",
             f"**{'Passed' if s['ok'] else 'Failed'}**: {s['errors']} error(s), {s['warnings']} warning(s). "
             f"({t['kind']}, s3w {report['tool']['s3w']})", "", "| | Check | Result |", "|---|---|---|"]
    for c in report["checks"]:
        n = len(c["findings"])
        what = {"pass": "ok", "warn": f"{n} warning(s)", "fail": f"{n} finding(s)", "skip": "skipped"}[c["status"]]
        lines.append(f"| {ICON[c['status']]} | {c['title']} | {what} |")
    for c in report["checks"]:
        if not c["findings"] and not c.get("notes"):
            continue
        lines += ["", f"### {c['title']}"]
        lines += [f"- **{f['severity']}**{' `' + f['file'] + '`' if f.get('file') else ''}: {f['message']}" for f in c["findings"]]
        lines += [f"- _{n}_" for n in c.get("notes", [])]
    if report["screenshots"]:
        lines += ["", "Screenshots: " + ", ".join(f"`screens/{n}`" for n in report["screenshots"])]
    return "\n".join(lines) + "\n"


def write_report(report, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "report.md").write_text(markdown(report))
