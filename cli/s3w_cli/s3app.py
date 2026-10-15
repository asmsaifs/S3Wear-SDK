#!/usr/bin/env python3
"""Make, sign and check mini app packages (.s3app). Python 3.9+, no
dependencies. The `s3w` CLI (P8-06) builds on this module; the watch's reader applies the same rules.

  python3 -m s3w_cli.s3app keygen KEY                         new Ed25519 key: KEY (secret, hex) and KEY.pub
  python3 -m s3w_cli.s3app pack DIR OUT.s3app [--key KEY]     DIR holds manifest.json, app.wasm, icon.png, assets/...
  python3 -m s3w_cli.s3app verify PKG [--pub HEX]             check CRCs, digest and signature; print the signer
  python3 -m s3w_cli.s3app pubkey KEY                         print the public key (hex), for `app key add` on the watch

Package: a zip with every entry stored, sorted by name, timestamps fixed (the same input gives the
same bytes). signature.sig = public key (32) || Ed25519(digest) (64), with
  digest = SHA-256(b"S3APP\\x01" + for each other entry, sorted by name:
                   name + b"\\0" + u32le(size) + SHA-256(data))
"""
import argparse
import hashlib
import json
import os
import struct
import sys
import zipfile

SIG_NAME = "signature.sig"
NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
MAX_ENTRIES = 64
MAX_NAME = 63

# --- Ed25519 (RFC 8032 §5.1, straight from its reference code; signing speed is not a concern) ---

_p = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _p - 2, _p) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _sha512(b):
    return hashlib.sha512(b).digest()


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _recover_x(y, sign):
    if y >= _p:
        return None
    x2 = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p != 0:
        x = x * _I % _p
    if (x * x - x2) % _p != 0:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


_gy = 4 * pow(5, _p - 2, _p) % _p
_gx = _recover_x(_gy, 0)
_G = (_gx, _gy, 1, _gx * _gy % _p)


def _compress(P):
    zinv = pow(P[2], _p - 2, _p)
    x, y = P[0] * zinv % _p, P[1] * zinv % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _p)


def _equal(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % _p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


def _expand(secret):
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def ed25519_public(secret):
    a, _ = _expand(secret)
    return _compress(_mul(a, _G))


def ed25519_sign(secret, msg):
    a, prefix = _expand(secret)
    A = _compress(_mul(a, _G))
    r = int.from_bytes(_sha512(prefix + msg), "little") % _L
    R = _compress(_mul(r, _G))
    h = int.from_bytes(_sha512(R + A + msg), "little") % _L
    return R + int.to_bytes((r + h * a) % _L, 32, "little")


def ed25519_verify(public, msg, sig):
    if len(public) != 32 or len(sig) != 64:
        return False
    A = _decompress(public)
    R = _decompress(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if A is None or R is None or s >= _L:
        return False
    h = int.from_bytes(_sha512(sig[:32] + public + msg), "little") % _L
    return _equal(_mul(s, _G), _add(R, _mul(h, A)))


# --- Package ---------------------------------------------------------------------------------------


def name_ok(name):
    if not name or len(name) > MAX_NAME or name.startswith("/") or name.endswith("/"):
        return False
    return all(part not in ("", ".", "..") and set(part) <= NAME_CHARS for part in name.split("/"))


APP_TAG = b"S3APP\x01"
FACE_TAG = b"S3FACE\x01"  # watch face packages (s3face.py): a signature for one kind never passes as the other's


def digest(files, tag=APP_TAG):
    """files: {name: bytes}. The package digest (signature.sig left out)."""
    h = hashlib.sha256(tag)
    for name in sorted(files, key=lambda n: n.encode()):
        if name == SIG_NAME:
            continue
        data = files[name]
        h.update(name.encode() + b"\0" + struct.pack("<I", len(data)) + hashlib.sha256(data).digest())
    return h.digest()


def write_zip(path, files):
    """Stored entries, sorted, fixed timestamps: reproducible bytes."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files, key=lambda n: n.encode()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[name])


def read_dir(src):
    files = {}
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            name = os.path.relpath(full, src).replace(os.sep, "/")
            if fn.startswith(".") or name == SIG_NAME:
                continue
            if not name_ok(name):
                sys.exit(f"{name}: bad name (A-Z a-z 0-9 . _ - only, at most {MAX_NAME} bytes)")
            with open(full, "rb") as f:
                files[name] = f.read()
    return files


def check_manifest(files):
    if "manifest.json" not in files:
        sys.exit("manifest.json missing")
    try:
        m = json.loads(files["manifest.json"])
    except ValueError as e:
        sys.exit(f"manifest.json: {e}")
    for key in ("id", "name", "version", "api_level", "ui_mode"):
        if key not in m:
            sys.exit(f"manifest.json: {key} missing")
    if m.get("entry", "app.wasm") not in files:
        sys.exit(f"{m.get('entry', 'app.wasm')} missing")
    return m


def load_key(path):
    with open(path) as f:
        secret = bytes.fromhex(f.read().strip())
    if len(secret) != 32:
        sys.exit(f"{path}: not an Ed25519 secret key (64 hex digits)")
    return secret


def pack(src, out, key_path=None):
    files = read_dir(src)
    m = check_manifest(files)
    if len(files) + (1 if key_path else 0) > MAX_ENTRIES:
        sys.exit(f"more than {MAX_ENTRIES} files")
    if key_path:
        secret = load_key(key_path)
        files[SIG_NAME] = ed25519_public(secret) + ed25519_sign(secret, digest(files))
    write_zip(out, files)
    return m


def verify(path, trusted=None):
    """Returns (manifest, signer public key or None). Exits with a message on any error."""
    with zipfile.ZipFile(path) as z:
        files = {}
        for info in z.infolist():
            if info.is_dir():
                continue
            if info.compress_type != zipfile.ZIP_STORED:
                sys.exit(f"{info.filename}: compressed (packages are stored)")
            if not name_ok(info.filename):
                sys.exit(f"{info.filename}: bad name")
            files[info.filename] = z.read(info)  # checks the CRC
    m = check_manifest(files)
    sig = files.get(SIG_NAME)
    if sig is None:
        return m, None
    if len(sig) != 96 or not ed25519_verify(sig[:32], digest(files), sig[32:]):
        sys.exit("signature does not match the package")
    if trusted is not None and sig[:32] != trusted:
        sys.exit("signed by another key")
    return m, sig[:32]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("key")
    p = sub.add_parser("pack")
    p.add_argument("dir")
    p.add_argument("out")
    p.add_argument("--key")
    v = sub.add_parser("verify")
    v.add_argument("pkg")
    v.add_argument("--pub")
    pk = sub.add_parser("pubkey")
    pk.add_argument("key")
    a = ap.parse_args(argv)
    if a.cmd == "keygen":
        if os.path.exists(a.key):
            sys.exit(f"{a.key} exists")
        secret = os.urandom(32)
        fd = os.open(a.key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secret.hex() + "\n")
        with open(a.key + ".pub", "w") as f:
            f.write(ed25519_public(secret).hex() + "\n")
        print(f"{a.key} (keep it secret), {a.key}.pub: {ed25519_public(secret).hex()}")
    elif a.cmd == "pack":
        m = pack(a.dir, a.out, a.key)
        print(f"{a.out}: {m['id']} {m['version']} ({os.path.getsize(a.out)} bytes, {'signed' if a.key else 'unsigned'})")
    elif a.cmd == "verify":
        m, signer = verify(a.pkg, bytes.fromhex(a.pub) if a.pub else None)
        print(f"{a.pkg}: {m['id']} {m['version']}, " + (f"signed by {signer.hex()}" if signer else "unsigned"))
    elif a.cmd == "pubkey":
        print(ed25519_public(load_key(a.key)).hex())


if __name__ == "__main__":
    main()
