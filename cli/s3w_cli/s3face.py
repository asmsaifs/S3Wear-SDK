"""Watch face packages (.s3face). Python 3.9+, no dependencies.
`s3w face build|pack|verify` and tools/store/gen_store.py build on this module; the watch's reader applies the same rules.

A face directory holds face.json and the images it names, nothing else (a `build/` folder and hidden
files are ignored). Packing adds preview.png (200x246: build/preview.png, from the simulator) and,
with a key, signature.sig. The package is a zip like a .s3app (stored entries, sorted, fixed
timestamps) with the digest tag "S3FACE\\x01".

face.json is checked with the watch's own parser: `s3w_sim --check-face` (the simulator binary,
build/sim/s3w_sim or $S3W_SIM).
`verify` does not need it: it checks the package (signature, entries, PNG headers, preview size) and
that face.json is JSON with an id, a name and a version.
"""
import json
import os
import re
import struct
import subprocess
import zipfile
from pathlib import Path

from . import s3app, sim
from .project import BuildError

PKG_MAX = 1024 * 1024
IMAGE_MAX = 256 * 1024
JSON_MAX = 16 * 1024
PREVIEW = "preview.png"
PREVIEW_SIZE = (200, 246)
BUILTIN_IDS = {"digital", "analog", "modular", "minimal"}
ID_RE = re.compile(r"^[a-z0-9_-][a-z0-9._-]{0,46}$")
VERSION_RE = re.compile(r"^(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})$")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CHECK_TIMEOUT_S = 30


def id_ok(face_id):
    """face_install.c face_id_ok(): [a-z0-9._-], 1..47, no leading '.', not ending in .new/.old/.del."""
    return bool(ID_RE.match(face_id)) and not face_id.endswith((".new", ".old", ".del"))


def id_reserved(face_id):
    return face_id in BUILTIN_IDS or face_id.startswith("s3w.")


def version_ok(v):
    return bool(VERSION_RE.match(v)) and all(int(p) <= 65535 for p in v.split("."))


def png_size(data):
    """(width, height) from the signature and IHDR, or None if it is not a PNG."""
    if len(data) < 33 or data[:8] != PNG_MAGIC or data[8:16] != b"\0\0\0\x0dIHDR":
        return None
    return struct.unpack(">II", data[16:24])


def digest(files):
    return s3app.digest(files, s3app.FACE_TAG)


def check_face_json(sim_path, face_json):
    """The watch's check of a face.json file: {"id", "name", "version", "api", "images": [...]}.
    BuildError with the parser's line, column and reason when it is refused."""
    try:
        r = subprocess.run([sim_path, "--check-face", str(face_json)], capture_output=True, timeout=CHECK_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise BuildError(f"{sim_path}: {e}")
    if r.returncode != 0:
        raise BuildError(r.stderr.decode(errors="replace").strip() or f"{face_json}: refused")
    return json.loads(r.stdout)


def check_identity(info):
    """The install rules on top of the parser's: an id the watch accepts, a real version."""
    if not id_ok(info["id"]):
        raise BuildError(f"id '{info['id']}': 1..47 of [a-z0-9._-], not starting with '.', not ending in .new, .old or .del")
    if id_reserved(info["id"]):
        raise BuildError(f"id '{info['id']}' is a built-in face's (digital, analog, modular, minimal, s3w.*)")
    if not version_ok(info["version"]):
        raise BuildError(f"version '{info['version']}': MAJOR.MINOR.PATCH" if info["version"] else "version missing")


def check_files(files, images):
    """The entries a package may hold (face_install.c check_entries()): face.json, preview.png, the
    images face.json names and signature.sig, nothing else; PNG headers; the preview's size."""
    allowed = {"face.json", PREVIEW, s3app.SIG_NAME, *images}
    for name in sorted(files):
        if name not in allowed:
            raise BuildError(f"{name}: not part of a face")
    for name in images:
        if name not in files:
            raise BuildError(f"{name} missing (face.json uses it)")
    if PREVIEW not in files:
        raise BuildError(f"{PREVIEW} missing")
    for name, data in sorted(files.items()):
        if name != PREVIEW and not name.endswith(".png"):
            continue
        if len(data) > IMAGE_MAX:
            raise BuildError(f"{name} over {IMAGE_MAX // 1024} KB")
        size = png_size(data)
        if size is None:
            raise BuildError(f"{name} is not a PNG")
        if name == PREVIEW and size != PREVIEW_SIZE:
            raise BuildError(f"{PREVIEW} is {size[0]}x{size[1]}, not {PREVIEW_SIZE[0]}x{PREVIEW_SIZE[1]}")
        if name != PREVIEW and not (0 < size[0] <= 1024 and 0 < size[1] <= 1024):
            raise BuildError(f"{name}: size {size[0]}x{size[1]} not supported")
    if sum(len(d) for d in files.values()) > PKG_MAX:
        raise BuildError(f"package over {PKG_MAX // 1024} KB")


def read_dir(src):
    """face.json and the other files of a face directory (not build/, not hidden ones), by name."""
    src = Path(src)
    if not (src / "face.json").is_file():
        raise BuildError(f"{src}: no face.json")
    files = {}
    for p in sorted(src.iterdir()):
        if p.name.startswith(".") or p.name == "build" or p.name == s3app.SIG_NAME:
            continue
        if p.is_dir():
            raise BuildError(f"{p.name}/: a face is face.json and its images, no folders")
        if not s3app.name_ok(p.name):
            raise BuildError(f"{p.name}: bad name (A-Z a-z 0-9 . _ - only)")
        files[p.name] = p.read_bytes()
    if len(files["face.json"]) > JSON_MAX:
        raise BuildError(f"face.json over {JSON_MAX // 1024} KB")
    return files


def render_preview(sim_path, src, out):
    """preview.png of the face in directory src, 200x246, from the simulator (pinned clock and demo data)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    try:
        r = subprocess.run([sim_path, "--face", str(src), "--preview", "--screenshot", str(out)], capture_output=True,
                           timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise BuildError(f"preview: {e}")
    if r.returncode != 0 or not out.exists():
        raise BuildError("preview: the simulator failed\n" + r.stderr.decode(errors="replace").strip())
    if png_size(out.read_bytes()) != PREVIEW_SIZE:
        raise BuildError("preview: the simulator did not make a 200x246 PNG")
    return out


def pack(src, out=None, key=None, sim_path=None, render=True):
    """Checks, previews and packs the face in directory src into out (default src/build/<id>.s3face),
    signed when key (a secret key file) is given. render=False packs the preview of an earlier build
    (src/build/preview.png, or src/preview.png) instead of making it. Returns (path, info)."""
    src = Path(src)
    files = read_dir(src)
    if sim_path is None:
        sim_path = sim.find_sim()
    info = check_face_json(sim_path, src / "face.json")
    check_identity(info)
    preview = src / "build" / PREVIEW
    if render:
        render_preview(sim_path, src, preview)
    elif not preview.exists() and PREVIEW not in files:
        raise BuildError(f"no {PREVIEW}: `s3w face build` makes it")
    if PREVIEW not in files:
        files[PREVIEW] = preview.read_bytes()
    check_files(files, info["images"])
    if key:
        secret = s3app.load_key(key)
        files[s3app.SIG_NAME] = s3app.ed25519_public(secret) + s3app.ed25519_sign(secret, digest(files))
    out = Path(out) if out else src / "build" / f"{info['id']}.s3face"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    s3app.write_zip(str(tmp), files)
    os.replace(tmp, out)
    return out, info


def read_package(path):
    """{name: bytes} of a package; SystemExit with the reason on any zip problem (like s3app.verify)."""
    files = {}
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            if i.is_dir():
                continue
            if i.compress_type != zipfile.ZIP_STORED:
                raise SystemExit(f"{i.filename}: compressed (packages are stored)")
            if not s3app.name_ok(i.filename):
                raise SystemExit(f"{i.filename}: bad name")
            files[i.filename] = z.read(i)  # checks the CRC
    return files


def verify(path, trusted=None):
    """Returns (info, signer public key or None); info has id, name, version. Exits with a message on
    any error. Checks what is checkable without the watch's parser (see the module docstring)."""
    files = read_package(path)
    if os.path.getsize(path) > PKG_MAX:
        raise SystemExit(f"package over {PKG_MAX // 1024} KB")
    try:
        face = json.loads(files.get("face.json", b""))
        info = {k: str(face[k]) for k in ("id", "name", "version")}
        check_identity(info)
        images = {face["background"]} if str(face.get("background", "")).endswith((".png", ".bin")) else set()
        for e in face.get("elements", []) + face.get("aod", {}).get("elements", []):
            if "image" in e:
                images.add(e["image"])
        check_files(files, sorted(images))
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise SystemExit(f"face.json: {e!r}")
    except BuildError as e:
        raise SystemExit(str(e))
    sig = files.get(s3app.SIG_NAME)
    if sig is None:
        return info, None
    if len(sig) != 96 or not s3app.ed25519_verify(sig[:32], digest(files), sig[32:]):
        raise SystemExit("signature does not match the package")
    if trusted is not None and sig[:32] != trusted:
        raise SystemExit("signed by another key")
    return info, sig[:32]
