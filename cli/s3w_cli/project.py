"""An app project: manifest.json plus C sources (src/*.c) or a Rust crate (Cargo.toml); building it
to build/app.wasm and packing build/<id>.s3app."""
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from . import s3app

PKG_DIR = Path(__file__).resolve().parent


def _find_sdk():
    """The SDK dir (include/, templates/, rust/): $S3W_SDK; else, in order, the copy vendored into an
    installed package (_sdk/), the public SDK repo (cli/ at its root) or the private repo (sdk/tools/s3w-cli)."""
    env = os.environ.get("S3W_SDK")
    if env:
        return Path(env)
    for cand in (PKG_DIR / "_sdk", PKG_DIR.parents[1], PKG_DIR.parents[2]):
        if (cand / "include" / "s3w.h").exists():
            return cand
    return PKG_DIR.parents[2]


SDK = _find_sdk()
# Private repo: sdk/ sits in the repo. Public SDK repo and installed package: no enclosing repo.
REPO = SDK.parent if SDK.name == "sdk" else SDK
STACK_BYTES = 8192
RUST_TARGET = "wasm32-unknown-unknown"
# WAMR on the watch: fast interpreter, bulk memory on, no reference types (docs/02 "Mini app
# runtime"). Recent clang and rustc emit reference-type call_indirect by default, so build for the
# MVP CPU plus the features the runtime has.
CLANG_FEATURES = ["-mcpu=mvp", "-mbulk-memory", "-msign-ext", "-mnontrapping-fptoint", "-mmutable-globals"]
RUST_FEATURES = ["-C", "target-cpu=mvp", "-C", "target-feature=+bulk-memory,+sign-ext,+nontrapping-fptoint,+mutable-globals"]


class BuildError(Exception):
    pass


ICON_PX = 80
ICON_MAX = 64 * 1024


def check_icon(png):
    """What the watch's decoder takes (firmware app_icon.h): an 80×80 PNG with 8-bit samples (grey,
    RGB, palette, grey + alpha or RGBA), not interlaced, ≤ 64 KB; the installer refuses others."""
    if len(png) > ICON_MAX:
        raise BuildError("icon.png: over 64 KB")
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR" or len(png) < 29:
        raise BuildError("icon.png: not a PNG")
    w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", png[16:29])
    if (w, h) != (ICON_PX, ICON_PX):
        raise BuildError(f"icon.png: {w}x{h}, must be {ICON_PX}x{ICON_PX}")
    if depth != 8 or ctype not in (0, 2, 3, 4, 6) or interlace:
        raise BuildError("icon.png: needs 8 bits per sample (grey, RGB, palette or RGBA), not interlaced")


def default_key():
    """$S3W_KEY, else ~/.s3w/dev.key if it exists, else None (unsigned)."""
    k = os.environ.get("S3W_KEY")
    if k:
        return k
    d = Path.home() / ".s3w" / "dev.key"
    return str(d) if d.exists() else None


def api_imports():
    """Every function the watch exports to apps (S3W_IMPORT in s3w.h)."""
    text = (SDK / "include" / "s3w.h").read_text()
    return set(re.findall(r"S3W_IMPORT\((\w+)\)", text))


def find_clang():
    cands = [os.environ.get("CLANG")] if os.environ.get("CLANG") else []
    cands += sorted(glob.glob("/opt/homebrew/opt/llvm*/bin/clang"), reverse=True)
    cands += ["/usr/local/opt/llvm/bin/clang", "/opt/wasi-sdk/bin/clang", "clang"]
    for c in cands:
        path = shutil.which(c)
        if not path:
            continue
        try:
            targets = subprocess.run([path, "--print-targets"], capture_output=True, text=True).stdout
        except OSError:
            continue
        if "wasm32" in targets:
            return path
    raise BuildError("no clang with the wasm32 target: install LLVM (brew install llvm) or wasi-sdk, or set CLANG")


def _leb(data, i):
    result = shift = 0
    while True:
        b = data[i]
        i += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            return result, i


def _name(data, i):
    n, i = _leb(data, i)
    return data[i:i + n].decode(errors="replace"), i + n


def module_info(wasm):
    """(imports [(module, name, kind)], exports [names]) of a wasm module."""
    if wasm[:8] != b"\0asm\x01\0\0\0":
        raise BuildError("not a wasm module")
    imports, exports = [], []
    i = 8
    while i < len(wasm):
        sid = wasm[i]
        size, i = _leb(wasm, i + 1)
        body, end = i, i + size
        if sid == 2:
            n, j = _leb(wasm, body)
            for _ in range(n):
                mod, j = _name(wasm, j)
                name, j = _name(wasm, j)
                kind = wasm[j]
                j += 1
                if kind == 0:  # function: type index
                    _, j = _leb(wasm, j)
                elif kind == 1:  # table: reftype, limits
                    j += 1
                    flags, j = _leb(wasm, j)
                    _, j = _leb(wasm, j)
                    if flags & 1:
                        _, j = _leb(wasm, j)
                elif kind == 2:  # memory: limits
                    flags, j = _leb(wasm, j)
                    _, j = _leb(wasm, j)
                    if flags & 1:
                        _, j = _leb(wasm, j)
                else:  # global: valtype, mutability
                    j += 2
                imports.append((mod, name, kind))
        elif sid == 7:
            n, j = _leb(wasm, body)
            for _ in range(n):
                name, j = _name(wasm, j)
                j += 1
                _, j = _leb(wasm, j)
                exports.append(name)
        i = end
    return imports, exports


class Project:
    def __init__(self, path="."):
        self.dir = Path(path).resolve()
        mf = self.dir / "manifest.json"
        if not mf.exists():
            raise BuildError(f"{self.dir}: no manifest.json (start with `s3w new`)")
        try:
            self.manifest = json.loads(mf.read_text())
        except ValueError as e:
            raise BuildError(f"manifest.json: {e}")
        for key in ("id", "name", "version", "api_level", "ui_mode"):
            if key not in self.manifest:
                raise BuildError(f"manifest.json: {key} missing")
        self.id = self.manifest["id"]
        self.lang = "rust" if (self.dir / "Cargo.toml").exists() else "c"
        self.build_dir = self.dir / "build"
        self.wasm = self.build_dir / "app.wasm"
        self.pkg = self.build_dir / f"{self.id}.s3app"

    def memory_bytes(self):
        kb = int(self.manifest.get("memory_kb", 256))
        return max(64, kb // 64 * 64) * 1024  # whole 64 KB pages, ≤ the manifest's limit

    def sources(self):
        """Files whose change needs a rebuild (run-sim watches them)."""
        files = [self.dir / "manifest.json", self.dir / "Cargo.toml"]
        for sub in ("src", "include", "assets"):
            files += [p for p in (self.dir / sub).rglob("*") if p.is_file()]
        files += list(self.dir.glob("*.c")) + list(self.dir.glob("*.h")) + [self.dir / "icon.png"]
        return [f for f in files if f.exists()]

    # --- Build -------------------------------------------------------------------------------

    def build(self, quiet=False):
        self.build_dir.mkdir(exist_ok=True)
        if self.lang == "rust":
            self._build_rust(quiet)
        else:
            self._build_c(quiet)
        self.check_module()
        return self.wasm

    def _run(self, cmd, env=None, quiet=False):
        r = subprocess.run(cmd, cwd=self.dir, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise BuildError((r.stdout + r.stderr).strip() or f"{cmd[0]} failed")
        if not quiet and (r.stderr.strip() and "warning" in r.stderr):
            print(r.stderr.strip(), file=sys.stderr)

    def _build_c(self, quiet):
        srcs = sorted((self.dir / "src").glob("*.c")) + sorted(self.dir.glob("*.c"))
        if not srcs:
            raise BuildError("no C sources (src/*.c)")
        mem = self.memory_bytes()
        cmd = [find_clang(), "--target=wasm32", "-Oz", "-ffreestanding", "-nostdlib", "-fno-builtin",
               "-Wall", "-Wextra", *CLANG_FEATURES, "-I", str(SDK / "include"), "-I", str(self.dir / "src"),
               "-I", str(self.dir / "include"), *map(str, srcs), "-o", str(self.wasm),
               "-Wl,--no-entry", "-Wl,--strip-all", f"-Wl,--initial-memory={mem}", f"-Wl,--max-memory={mem}",
               f"-Wl,-z,stack-size={STACK_BYTES}"]
        self._run(cmd, quiet=quiet)

    def _build_rust(self, quiet):
        if not shutil.which("cargo"):
            raise BuildError("cargo not found: install Rust (https://rustup.rs)")
        if shutil.which("rustup"):
            installed = subprocess.run(["rustup", "target", "list", "--installed"], capture_output=True, text=True)
            if RUST_TARGET not in installed.stdout:
                raise BuildError(f"the Rust target is missing: rustup target add {RUST_TARGET}")
        mem = self.memory_bytes()
        flags = RUST_FEATURES + ["-C", f"link-arg=-zstack-size={STACK_BYTES}", "-C", f"link-arg=--initial-memory={mem}",
                                 "-C", f"link-arg=--max-memory={mem}", "-C", "link-arg=--strip-all"]
        env = dict(os.environ, RUSTFLAGS=" ".join(flags))
        target_dir = self.dir / "target"
        self._run(["cargo", "build", "--release", "--target", RUST_TARGET, "--target-dir", str(target_dir)],
                  env=env, quiet=quiet)
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', (self.dir / "Cargo.toml").read_text(), re.M)
        out = target_dir / RUST_TARGET / "release" / (m.group(1).replace("-", "_") + ".wasm")
        shutil.copyfile(out, self.wasm)

    def check_module(self):
        """Imports only from the watch's API; exports at least one lifecycle function."""
        imports, exports = module_info(self.wasm.read_bytes())
        known = api_imports()
        bad = [f"{m}.{n}" for m, n, kind in imports if m != "s3w" or kind != 0 or n not in known]
        if bad:
            raise BuildError("imports the watch does not provide: " + ", ".join(bad) +
                             " (no libc: use only s3w.h; for C, -nostdlib)")
        if not {"s3w_on_start", "s3w_on_frame", "s3w_on_event"} & set(exports):
            print("warning: the module exports no s3w_on_start / s3w_on_event / s3w_on_frame", file=sys.stderr)

    # --- Pack ----------------------------------------------------------------------------------

    def files(self):
        if not self.wasm.exists():
            raise BuildError(f"{self.wasm} missing: run `s3w build` first")
        files = {"manifest.json": (self.dir / "manifest.json").read_bytes(),
                 self.manifest.get("entry", "app.wasm"): self.wasm.read_bytes()}
        assets = self.dir / "assets"
        for p in sorted(assets.rglob("*")) if assets.exists() else []:
            if p.is_file() and not p.name.startswith("."):
                name = p.relative_to(self.dir).as_posix()
                if not s3app.name_ok(name):
                    raise BuildError(f"{name}: bad name (A-Z a-z 0-9 . _ - only, ≤ {s3app.MAX_NAME} bytes)")
                files[name] = p.read_bytes()
        if (self.dir / "icon.png").exists():
            files["icon.png"] = (self.dir / "icon.png").read_bytes()
            check_icon(files["icon.png"])
        if len(files) + 1 > s3app.MAX_ENTRIES:
            raise BuildError(f"more than {s3app.MAX_ENTRIES} files")
        return files

    def pack(self, key=None, out=None):
        """Writes the package (signed with key, a secret key file, or unsigned) atomically."""
        files = self.files()
        if key:
            secret = s3app.load_key(key)
            files[s3app.SIG_NAME] = s3app.ed25519_public(secret) + s3app.ed25519_sign(secret, s3app.digest(files))
        out = Path(out) if out else self.pkg
        tmp = out.with_name(out.name + ".tmp")
        s3app.write_zip(str(tmp), files)
        os.replace(tmp, out)
        return out
