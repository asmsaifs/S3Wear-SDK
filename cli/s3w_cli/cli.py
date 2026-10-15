"""s3w: the S3Wear mini app CLI.

  s3w new <dir> [--lang c|rust] [--id ID] [--name NAME]   an app from a template
  s3w new <dir> --face [--id ID] [--name NAME]            a watch face from a template
  s3w build [dir] [--key K | --unsigned]                  build/app.wasm + build/<id>.s3app
  s3w pack [dir] [--key K | --unsigned]                   only the package, from build/app.wasm
  s3w sign <pkg> --key K                                  (re)sign a package
  s3w keygen [K]                                          a developer key (default ~/.s3w/dev.key)
  s3w key [K]                                             its public key, for `app key add` on the watch
  s3w verify <pkg> [--pub HEX]                            check a package
  s3w face build|pack|verify|run-sim ...                  watch faces (.s3face): s3w face --help
  s3w sim install [--version V] | update | list           simulator binaries from the firmware site (~/.s3w/sim)
  s3w run-sim [dir] [--script F --screenshot F]           the simulator, reloaded on every change
  s3w install [dir|pkg] --usb [--port P] [--yes] [--trust-key]   install on the watch over USB
  s3w check [dir] [--developer LOGIN] [--out DIR] ...     the store's automated checks (report.json + report.md)
  s3w logs [--port P] [--all]                             stream the watch's app logs

Packages are signed with --key, $S3W_KEY or ~/.s3w/dev.key when it exists, else unsigned.
"""
import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

from . import check as checker
from . import device, rules, s3app, s3face, sim, simmgr
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
    if args.face:
        if not s3face.id_ok(app_id) or s3face.id_reserved(app_id):
            raise BuildError(f"id '{app_id}': 1..47 of [a-z0-9._-], not starting with '.', not a built-in face's")
        template = SDK / "templates" / "face"
    else:
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
    if args.face:
        print(f"{dest}: watch face {app_id} ('{name}')\n  s3w face run-sim {os.path.relpath(dest)}")
        return
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


def cmd_sim(args):
    if args.sim_cmd == "install":
        simmgr.install(args.version, args.url, args.force)
    elif args.sim_cmd == "update":
        simmgr.update(args.url)
    else:
        found = simmgr.installed()
        for v, d in found:
            print(f"{v}  {d / simmgr.BINARY}")
        if not found:
            print("none installed (s3w sim install)")


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
    if args.face_cmd == "run-sim":
        return s3face.run_sim(args.dir, sim=args.sim, script=args.script, screenshot=args.screenshot, watch=not args.no_watch)
    key = _key(args)
    out, info = s3face.pack(args.dir, args.out, key, sim.find_sim(args.sim), render=args.face_cmd == "build")
    print(f"{out}: {info['id']} {info['version']} ({out.stat().st_size} bytes, {'signed' if key else 'unsigned'})")


def cmd_check(args):
    if args.print_schema:
        print(rules.listing_schema_json(), end="")
        return 0
    opts = checker.Options(developer=args.developer, out=args.out, monkey_seconds=args.monkey_seconds, seed=args.seed,
                           sim=args.sim, verify_dns=args.verify_dns, run=not args.no_run,
                           only=args.only.split(",") if args.only else None)
    try:
        if args.profile:
            opts.profile = json.loads(Path(args.profile).read_text())
        if args.changed:
            opts.changed = [ln.strip() for ln in Path(args.changed).read_text().splitlines() if ln.strip()]
        if args.published:
            opts.published = json.loads(Path(args.published).read_text())
        if args.blocklist:
            opts.blocklist = json.loads(Path(args.blocklist).read_text())
    except (OSError, ValueError) as e:
        raise BuildError(f"{e}")
    report = checker.run_checks(args.dir, opts)
    if args.out:
        checker.write_report(report, args.out)
    print(checker.markdown(report), end="")
    return 0 if report["summary"]["ok"] else 1


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
    p.add_argument("--face", action="store_true", help="a watch face (face.json) instead of an app")
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
    p.add_argument("--sim", help="simulator binary (default: $S3W_SIM, build/sim/s3w_sim, s3w sim install)")
    p.add_argument("--script", help="headless: run this scenario (firmware/test/ui/README.md)")
    p.add_argument("--screenshot", help="headless: write the last frame here")
    p.add_argument("--no-watch", action="store_true", help="do not rebuild on change")
    p.set_defaults(fn=cmd_run_sim)
    p = sub.add_parser("sim", help="simulator binaries (install, update, list)")
    ssub = p.add_subparsers(dest="sim_cmd", required=True)
    sp = ssub.add_parser("install", help="download, verify and unpack a simulator")
    sp.add_argument("--version", help="release version (default: the latest)")
    sp.add_argument("--force", action="store_true", help="again, even if installed")
    sp.add_argument("--url", help="release site (default: $S3W_SIM_URL or the firmware site)")
    sp = ssub.add_parser("update", help="install the latest if it is newer")
    sp.add_argument("--url", help="release site (default: $S3W_SIM_URL or the firmware site)")
    ssub.add_parser("list", help="installed simulators")
    p.set_defaults(fn=cmd_sim)
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
        fp.add_argument("--sim", help="simulator binary (default: $S3W_SIM, build/sim/s3w_sim, s3w sim install)")
        signing(fp)
    fp = fsub.add_parser("run-sim", help="show the face in the simulator, reloaded on every save")
    fp.add_argument("dir", nargs="?", default=".")
    fp.add_argument("--sim", help="simulator binary (default: $S3W_SIM, build/sim/s3w_sim, s3w sim install)")
    fp.add_argument("--script", help="headless: run this scenario (see the simulator scripts reference)")
    fp.add_argument("--screenshot", help="headless: write the last frame here")
    fp.add_argument("--no-watch", action="store_true", help="do not reload on change")
    fp = fsub.add_parser("verify", help="check a face package")
    fp.add_argument("pkg")
    fp.add_argument("--pub")
    p.set_defaults(fn=cmd_face)
    p = sub.add_parser("check", help="the store's automated checks, on your machine")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--developer", help="your login in the store repository (enables the ownership check)")
    p.add_argument("--profile", help="your developer profile (developers/<login>.json): namespaces")
    p.add_argument("--changed", help="a file with the paths changed in the pull request, one per line")
    p.add_argument("--published", help="the published store index (index.json): the version must be higher")
    p.add_argument("--out", help="write report.json, report.md and screenshots here")
    p.add_argument("--monkey-seconds", type=int, default=120, help="random-input test length in simulated seconds (0: skip)")
    p.add_argument("--seed", type=int, default=1, help="the monkey test's seed")
    p.add_argument("--sim", help="simulator binary (default: $S3W_SIM, build/sim/s3w_sim, s3w sim install)")
    p.add_argument("--blocklist", help="a JSON file with more names to keep out: trademarks, brands, offensive")
    p.add_argument("--verify-dns", action="store_true", help="check the DNS TXT record of a domain namespace (needs dig)")
    p.add_argument("--no-run", action="store_true", help="skip the simulator runs (run, monkey test)")
    p.add_argument("--only", help="run only these checks (comma separated ids: layout, listing, manifest, ownership, build, ...)")
    p.add_argument("--print-schema", action="store_true", help="print the JSON Schema of listing.json and exit")
    p.set_defaults(fn=cmd_check)
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
