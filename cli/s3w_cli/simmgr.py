"""`s3w sim install|update|list`: the simulator binaries published on the firmware site.

The site has sim.json (the latest release) and sim/<version>/sim.json, each with a signature sim.json.sig:
Ed25519 over SHA-256("S3SIM\\x01" || the exact bytes of sim.json) with the OTA release key. The manifest lists
one zip per platform with its size and SHA-256. Nothing is unpacked before the signature, size and hash match.
Installed to $S3W_HOME/sim/<version>/ (default ~/.s3w/sim/<version>/) with its sim.json next to the binary.
"""
import hashlib
import io
import json
import os
import platform
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import __version__
from .project import BuildError
from .s3app import ed25519_verify

PREFIX = b"S3SIM\x01"
FORMAT = 1
BASE_URL = "https://s3wear-firmware.fiqraat.com/"
# The S3Wear release key: the same key signs the firmware feed, the full-install files and sim.json.
PUBLIC_KEY = bytes.fromhex("29acbae141bccaf0b22e1a94d34d0bc7361e526d0bfe12c89794bc9322966dd7")
PLATFORMS = ("macos-universal", "linux-x86_64")
BINARY = "s3w_sim"
UNPACK = (BINARY, "SIMULATOR-LICENSE")
MAX_ZIP = 256 * 1024 * 1024
TIMEOUT_S = 30
VERSION_FORM = re.compile(r"^(\d{1,5})\.(\d{1,5})\.(\d{1,5})(-[0-9A-Za-z.-]+)?$")


def digest(manifest_bytes):
    return hashlib.sha256(PREFIX + manifest_bytes).digest()


def home():
    return Path(os.environ.get("S3W_HOME") or Path.home() / ".s3w").expanduser() / "sim"


def host_platform(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system == "Darwin":
        return "macos-universal"
    if system == "Linux" and machine in ("x86_64", "amd64"):
        return "linux-x86_64"
    if system == "Windows":
        raise BuildError("no native Windows simulator: use WSL2 (Linux x86_64)")
    raise BuildError(f"no simulator binary for {system} {machine}; set $S3W_SIM to a simulator you built")


def version_key(v):
    m = VERSION_FORM.match(v)
    if not m:
        return None
    return (int(m[1]), int(m[2]), int(m[3]), m[4] is None, m[4] or "")


def check_manifest(manifest_bytes, signature_hex, public=PUBLIC_KEY, verify=ed25519_verify):
    """Signature first, then the structure. Returns the manifest dict, raises BuildError."""
    try:
        signature = bytes.fromhex(signature_hex.strip())
    except ValueError:
        raise BuildError("sim.json.sig is not hex")
    if len(signature) != 64 or not verify(public, digest(manifest_bytes), signature):
        raise BuildError("sim.json: bad signature")
    try:
        m = json.loads(manifest_bytes)
        if m["format"] != FORMAT:
            raise BuildError(f"sim.json: unknown format {m['format']!r}")
        if version_key(m["version"]) is None or not isinstance(m["api_level"], int) or not isinstance(m["face_api"], int):
            raise BuildError("sim.json: bad version, api_level or face_api")
        for name, f in m["files"].items():
            if name not in PLATFORMS:
                raise BuildError(f"sim.json: unknown platform {name!r}")
            if not (isinstance(f["path"], str) and re.fullmatch(r"[A-Za-z0-9._/-]+", f["path"]) and ".." not in f["path"]
                    and not f["path"].startswith("/") and isinstance(f["size"], int) and 0 < f["size"] <= MAX_ZIP
                    and re.fullmatch(r"[0-9a-f]{64}", f["sha256"])):
                raise BuildError(f"sim.json: bad entry for {name}")
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise BuildError(f"sim.json: malformed ({e!r})")
    return m


def fetch(url):
    if not url.startswith(("https://", "file://")):
        raise BuildError(f"{url}: only https:// (or file://) URLs")
    # The site is behind Cloudflare, which refuses urllib's default "Python-urllib" agent with a 403.
    req = urllib.request.Request(url, headers={"User-Agent": f"s3w-cli/{__version__} (+https://s3wear.fiqraat.com/developers/)"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            data = r.read(MAX_ZIP + 1)
    except OSError as e:
        raise BuildError(f"{url}: {e}")
    if len(data) > MAX_ZIP:
        raise BuildError(f"{url}: over {MAX_ZIP} bytes")
    return data


def _base(url):
    base = url or os.environ.get("S3W_SIM_URL") or BASE_URL
    return base if base.endswith("/") else base + "/"


def fetch_manifest(version=None, url=None, public=PUBLIC_KEY, verify=ed25519_verify):
    """-> (manifest dict, manifest bytes, base url)."""
    base = _base(url)
    rel = f"sim/{version}/sim.json" if version else "sim.json"
    raw = fetch(base + rel)
    sig = fetch(base + rel + ".sig").decode("ascii", "replace")
    m = check_manifest(raw, sig, public, verify)
    if version and m["version"] != version:
        raise BuildError(f"asked for {version}, the site says {m['version']}")
    return m, raw, base


def unpack(zip_bytes, dest):
    """Only the known files, flat names; the binary becomes executable."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = {i.filename for i in z.infolist() if not i.is_dir()}
        if BINARY not in names or not names <= set(UNPACK):
            raise BuildError(f"the archive holds {sorted(names)}, expected {BINARY} (and SIMULATOR-LICENSE)")
        for n in names:
            (dest / n).write_bytes(z.read(n))
    (dest / BINARY).chmod(0o755)


def install(version=None, url=None, force=False, public=PUBLIC_KEY, verify=ed25519_verify, plat=None, out=print):
    """Downloads, checks and unpacks a simulator. Returns the directory."""
    m, raw, base = fetch_manifest(version, url, public, verify)
    root = home()
    target = root / m["version"]
    if (target / BINARY).exists() and not force:
        out(f"simulator {m['version']} is installed ({target})")
        return target
    plat = plat or host_platform()
    entry = m["files"].get(plat)
    if not entry:
        raise BuildError(f"simulator {m['version']} has no {plat} build (it has {', '.join(m['files'])})")
    out(f"downloading simulator {m['version']} for {plat} ({entry['size']} bytes)")
    data = fetch(base + entry["path"])
    if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise BuildError(f"{entry['path']} differs from sim.json (size or SHA-256)")
    root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".install-", dir=root))
    try:
        unpack(data, tmp)
        (tmp / "sim.json").write_bytes(raw)
        if target.exists():
            shutil.rmtree(target)
        tmp.rename(target)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    out(f"installed simulator {m['version']} (api_level {m['api_level']}) in {target}")
    return target


def installed():
    """[(version, dir)] oldest first."""
    root = home()
    found = []
    if root.is_dir():
        for d in root.iterdir():
            if version_key(d.name) and (d / BINARY).exists():
                found.append((d.name, d))
    return sorted(found, key=lambda x: version_key(x[0]))


def latest_installed():
    found = installed()
    return found[-1][1] / BINARY if found else None


def update(url=None, public=PUBLIC_KEY, verify=ed25519_verify, plat=None, out=print):
    m, _, _ = fetch_manifest(None, url, public, verify)
    have = installed()
    if have and version_key(have[-1][0]) >= version_key(m["version"]):
        out(f"simulator {have[-1][0]} is up to date (latest is {m['version']})")
        return have[-1][1]
    return install(m["version"], url, False, public, verify, plat, out)
