"""s3w: the S3Wear mini app CLI.

  s3w new <dir> [--lang c|rust] [--id ID] [--name NAME]   an app from a template
  s3w build [dir] [--key K | --unsigned]                  build/app.wasm + build/<id>.s3app
  s3w pack [dir] [--key K | --unsigned]                   only the package, from build/app.wasm
  s3w sign <pkg> --key K                                  (re)sign a package
  s3w keygen [K]                                          a developer key (default ~/.s3w/dev.key)
  s3w key [K]                                             its public key, for `app key add` on the watch
  s3w verify <pkg> [--pub HEX]                            check a package
  s3w face build|pack|verify ...                          watch faces (.s3face): s3w face --help
  s3w run-sim [dir] [--script F --screenshot F]           the simulator, reloaded on every change
  s3w install [dir|pkg] --usb [--port P] [--yes] [--trust-key]   install on the watch over USB
  s3w logs [--port P] [--all]                             stream the watch's app logs

Packages are signed with --key, $S3W_KEY or ~/.s3w/dev.key when it exists, else unsigned.
"""
import argparse
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

from . import device, s3app, s3face, sim
from .project import SDK, BuildError, Project, default_key


def _key(args):
    if getattr(args, "unsigned", False):
        return None
    return args.key or default_key()


def cmd_new(args):
    dest = Path(args.dir).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise BuildError(f"{dest} exists and is not empty")
    slug = re.sub(r"[^a-z0-9_]", "_", dest.name.lower()).strip("_") or "app"
    app_id = args.id or f"dev.example.{slug}"
    name = args.name or dest.name.replace("_", " ").replace("-", " ").title()[:31]
    template = SDK / "templates" / args.lang
    subst = {
        "{{id}}": app_id,
        "{{name}}": name,
        "{{crate}}": slug.replace("_", "-"),
        "{{sdk_rust}}": os.path.relpath(SDK / "rust", dest).replace(os.sep, "/"),
    }
    for src in sorted(template.rglob("*")):
        rel = src.relative_to(template)
        out = dest / rel
        if src.is_dir():
            out.mkdir(parents=True, exist_ok=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text()
        for k, v in subst.items():
            text = text.replace(k, v)
        out.write_text(text)
    Project(dest)  # the manifest must parse
    print(f"{dest}: {args.lang} app {app_id} ('{name}')\n  s3w run-sim {os.path.relpath(dest)}")


def cmd_build(args):
    p = Project(args.dir)
    p.build()
    out = p.pack(_key(args))
    print(f"{out} ({out.stat().st_size} bytes, {'signed' if _key(args) else 'unsigned'})")


def cmd_pack(args):
    p = Project(args.dir)
    out = p.pack(_key(args))
    print(f"{out} ({out.stat().st_size} bytes, {'signed' if _key(args) else 'unsigned'})")


def cmd_sign(args):
    with zipfile.ZipFile(args.pkg) as z:
        files = {i.filename: z.read(i) for i in z.infolist() if not i.is_dir() and i.filename != s3app.SIG_NAME}
    secret = s3app.load_key(args.key)
    files[s3app.SIG_NAME] = s3app.ed25519_public(secret) + s3app.ed25519_sign(secret, s3app.digest(files))
    s3app.write_zip(args.pkg, files)
    print(f"{args.pkg}: signed by {s3app.ed25519_public(secret).hex()}")


def cmd_keygen(args):
    path = Path(args.key).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    s3app.main(["keygen", str(path)])
    print(f"on the watch console: app key add {(path.parent / (path.name + '.pub')).read_text().strip()}")


def cmd_key(args):
    print(s3app.ed25519_public(s3app.load_key(str(Path(args.key).expanduser()))).hex())


def cmd_verify(args):
    s3app.main(["verify", args.pkg] + (["--pub", args.pub] if args.pub else []))


def cmd_run_sim(args):
    return sim.run(Project(args.dir), sim=args.sim, script=args.script, screenshot=args.screenshot,
                   watch=not args.no_watch)


def cmd_install(args):
    if args.wifi:
        raise BuildError("Wi-Fi install comes with developer mode on the watch (P9-07); use --usb")
    if not args.usb:
        raise BuildError("say how: --usb")
    target = Path(args.target)
    if target.suffix == ".s3app":
        pkg = target
        with zipfile.ZipFile(pkg) as z:
            import json
            app_id = json.loads(z.read("manifest.json"))["id"]
    else:
        p = Project(target)
        p.build()
        pkg = p.pack(_key(args))
        app_id = p.id
        print(f"{pkg}: {'signed' if _key(args) else 'unsigned'}")
    trust = None
    if args.trust_key:
        key = _key(args)
        if not key:
            raise BuildError("--trust-key needs a key (--key, $S3W_KEY or ~/.s3w/dev.key)")
        trust = s3app.ed25519_public(s3app.load_key(key)).hex()
    ok = device.install(str(pkg), app_id, port=args.port, ask=not args.yes, trust_key=trust)
    return 0 if ok else 1


def cmd_face(args):
    if args.face_cmd == "verify":
        try:
            info, signer = s3face.verify(args.pkg, bytes.fromhex(args.pub) if args.pub else None)
        except SystemExit as e:
            raise BuildError(str(e))
        print(f"{args.pkg}: {info['id']} {info['version']}, " + (f"signed by {signer.hex()}" if signer else "unsigned"))
        return
    key = _key(args)
    out, info = s3face.pack(args.dir, args.out, key, sim.find_sim(args.sim), render=args.face_cmd == "build")
    print(f"{out}: {info['id']} {info['version']} ({out.stat().st_size} bytes, {'signed' if key else 'unsigned'})")


def cmd_logs(args):
    device.logs(port=args.port, everything=args.all)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="s3w", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def signing(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--key", help="secret key file (default: $S3W_KEY or ~/.s3w/dev.key)")
        g.add_argument("--unsigned", action="store_true")

    p = sub.add_parser("new", help="an app from a template")
    p.add_argument("dir")
    p.add_argument("--lang", choices=("c", "rust"), default="c")
    p.add_argument("--id")
    p.add_argument("--name")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("build", help="build and pack")
    p.add_argument("dir", nargs="?", default=".")
    signing(p)
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("pack", help="pack build/app.wasm")
    p.add_argument("dir", nargs="?", default=".")
    signing(p)
    p.set_defaults(fn=cmd_pack)
    p = sub.add_parser("sign", help="sign a package")
    p.add_argument("pkg")
    p.add_argument("--key", required=True)
    p.set_defaults(fn=cmd_sign)
    p = sub.add_parser("keygen", help="a new developer key")
    p.add_argument("key", nargs="?", default="~/.s3w/dev.key")
    p.set_defaults(fn=cmd_keygen)
    p = sub.add_parser("key", help="print a key's public half")
    p.add_argument("key", nargs="?", default="~/.s3w/dev.key")
    p.set_defaults(fn=cmd_key)
    p = sub.add_parser("verify", help="check a package")
    p.add_argument("pkg")
    p.add_argument("--pub")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("run-sim", help="run in the simulator, reload on change")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--sim", help="simulator binary (default: build/sim/s3w_sim or $S3W_SIM)")
    p.add_argument("--script", help="headless: run this scenario (firmware/test/ui/README.md)")
    p.add_argument("--screenshot", help="headless: write the last frame here")
    p.add_argument("--no-watch", action="store_true", help="do not rebuild on change")
    p.set_defaults(fn=cmd_run_sim)
    p = sub.add_parser("install", help="install on the watch")
    p.add_argument("target", nargs="?", default=".", help="app directory or .s3app")
    p.add_argument("--usb", action="store_true")
    p.add_argument("--wifi", metavar="IP")
    p.add_argument("--port")
    p.add_argument("--yes", action="store_true", help="no consent screen on the watch")
    p.add_argument("--trust-key", action="store_true", help="add the signing key on the watch first")
    signing(p)
    p.set_defaults(fn=cmd_install)
    p = sub.add_parser("face", help="watch faces (.s3face)")
    fsub = p.add_subparsers(dest="face_cmd", required=True)
    for name, text in (("build", "check face.json, render build/preview.png in the simulator, pack"),
                       ("pack", "check and pack with the preview of the last build")):
        fp = fsub.add_parser(name, help=text)
        fp.add_argument("dir", nargs="?", default=".")
        fp.add_argument("--out", help="package path (default: <dir>/build/<id>.s3face)")
        fp.add_argument("--sim", help="simulator binary (default: build/sim/s3w_sim or $S3W_SIM)")
        signing(fp)
    fp = fsub.add_parser("verify", help="check a face package")
    fp.add_argument("pkg")
    fp.add_argument("--pub")
    p.set_defaults(fn=cmd_face)
    p = sub.add_parser("logs", help="stream the watch's app logs")
    p.add_argument("--port")
    p.add_argument("--all", action="store_true", help="every log line, not only apps")
    p.set_defaults(fn=cmd_logs)

    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except (BuildError, device.DeviceError) as e:
        print(f"s3w {args.cmd}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
