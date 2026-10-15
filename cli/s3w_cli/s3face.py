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
import zlib
from pathlib import Path

from . import s3app, sim
from . import sim as sim_mod  # run_sim() has a parameter of that name
from .project import BuildError

PKG_MAX = 1024 * 1024
IMAGE_MAX = 256 * 1024
JSON_MAX = 16 * 1024
PREVIEW = "preview.png"
PREVIEW_SIZE = (200, 246)
BUILTIN_IDS = {"digital", "analog", "modular", "minimal"}
ID_RE = re.compile(r"^[a-z0-9_-][a-z0-9._-]{0,46}$")
VERSION_RE = re.compile(r"^(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})$")
# Files a face folder in the store repository holds that are not part of the package.
STORE_FILES = {"listing.json", "README", "README.md", "LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "CHANGELOG.md"}
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
IMAGE_SIDE_MAX = 1024
IMAGE_PIXELS_MAX = 512 * 1024      # one picture, decoded (the watch's loader refuses more)
IMAGE_CACHE_BYTES = 1536 * 1024    # all the face's pictures decoded, 3 bytes a pixel: what the watch keeps at once
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
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


def png_check(name, data):
    """What the watch's decoder needs of a picture: valid chunks (CRCs), a colour type and depth PNG allows, image
    data that inflates to the right size. Returns (width, height). BuildError with the reason."""
    size = png_size(data)
    if size is None:
        raise BuildError(f"{name} is not a PNG")
    pos, idat, ihdr = 8, b"", None
    while pos < len(data):
        if pos + 12 > len(data):
            raise BuildError(f"{name}: truncated")
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + ln]
        if len(body) != ln or pos + 12 + ln > len(data):
            raise BuildError(f"{name}: truncated")
        if zlib.crc32(tag + body) & 0xFFFFFFFF != struct.unpack(">I", data[pos + 8 + ln:pos + 12 + ln])[0]:
            raise BuildError(f"{name}: damaged ({tag.decode('ascii', 'replace')} chunk CRC)")
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    if ihdr is None or not idat:
        raise BuildError(f"{name}: no image data")
    w, h, depth, ctype, _, _, interlace = ihdr
    if ctype not in CHANNELS or depth not in DEPTHS[ctype]:
        raise BuildError(f"{name}: colour type {ctype} with {depth} bits is not a PNG")
    try:
        raw = zlib.decompress(idat)
    except zlib.error as e:
        raise BuildError(f"{name}: damaged image data ({e})")
    if not interlace:
        stride = (w * CHANNELS[ctype] * depth + 7) // 8
        if len(raw) != h * (1 + stride):
            raise BuildError(f"{name}: image data is the wrong size")
    return w, h


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
        if name != PREVIEW and not (0 < size[0] <= IMAGE_SIDE_MAX and 0 < size[1] <= IMAGE_SIDE_MAX):
            raise BuildError(f"{name}: size {size[0]}x{size[1]} not supported")
        if name != PREVIEW:
            w, h = png_check(name, data)
            if w * h > IMAGE_PIXELS_MAX:
                raise BuildError(f"{name}: {w}x{h} is over {IMAGE_PIXELS_MAX} pixels (the watch keeps 1.5 MB of pictures)")
    cache = sum(w * h * 3 for w, h in (png_size(files[n]) for n in set(images)))
    if cache > IMAGE_CACHE_BYTES:
        raise BuildError(f"the pictures need {cache // 1024} KB decoded; the watch keeps {IMAGE_CACHE_BYTES // 1024} KB at once")
    if sum(len(d) for d in files.values()) > PKG_MAX:
        raise BuildError(f"package over {PKG_MAX // 1024} KB")


def read_dir(src):
    """face.json and the other files of a face directory (not build/, not hidden ones), by name."""
    src = Path(src)
    if not (src / "face.json").is_file():
        raise BuildError(f"{src}: no face.json")
    files = {}
    for p in sorted(src.iterdir()):
        if p.name.startswith(".") or p.name == "build" or p.name == s3app.SIG_NAME or p.name in STORE_FILES:
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


def run_sim(face_dir, sim=None, script=None, screenshot=None, watch=True):
    """`s3w face run-sim`: the face in the simulator. A window reloads it whenever face.json or a picture is saved
    (a face the watch's parser refuses keeps the last good one on screen) and has keys for demo data; with a script
    or screenshot it runs headless once."""
    d = Path(face_dir).resolve()
    if not (d / "face.json").is_file():
        raise BuildError(f"{d}: no face.json (start with `s3w new --face`)")
    sim_path = sim_mod.find_sim(sim)
    check_face_json(sim_path, d / "face.json")  # a face the watch refuses is said at once, with line and column
    cmd = [sim_path, "--face", str(d)]
    if script:
        cmd += ["--script", script]
    if screenshot:
        cmd += ["--screenshot", screenshot]
    if script or screenshot:
        return subprocess.run(cmd).returncode
    if watch:
        cmd.append("--watch-face")
    print(f"simulator running {d.name}; saving face.json or a picture reloads it (Ctrl-C ends)")
    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        return 0
