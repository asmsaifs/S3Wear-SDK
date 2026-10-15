"""s3w CLI tests (P8-06): a new app from each template builds, packs and runs in the simulator.

  python3 -m unittest discover -s sdk/tools/s3w-cli/tests
  (ctest --test-dir build/sim runs them with S3W_SIM set)

Toolchain tests skip without clang (wasm32) / cargo + the wasm32 target / the simulator."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from s3w_cli import cli, s3app  # noqa: E402
from s3w_cli.project import SDK, BuildError, Project, check_icon, find_clang, module_info  # noqa: E402


def have_clang():
    try:
        find_clang()
        return True
    except BuildError:
        return False


def have_rust():
    if not shutil.which("cargo") or not shutil.which("rustup"):
        return False
    out = subprocess.run(["rustup", "target", "list", "--installed"], capture_output=True, text=True).stdout
    return "wasm32-unknown-unknown" in out


def sim_path():
    p = os.environ.get("S3W_SIM") or str(SDK.parent / "build" / "sim" / "s3w_sim")
    return p if Path(p).exists() else None


# Taps "+1" three times (the template's layout) and checks the app still runs.
SCRIPT = "wait 600\ntap 205 230\ntap 205 230\ntap 205 230\nwait 300\napp-is running\n"


class Ed25519(unittest.TestCase):
    def test_rfc8032_vector_1(self):
        sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        pk = s3app.ed25519_public(sk)
        self.assertEqual(pk.hex(), "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        sig = s3app.ed25519_sign(sk, b"")
        self.assertEqual(sig.hex()[:32], "e5564300c360ac729086e2cc806e828a")
        self.assertTrue(s3app.ed25519_verify(pk, b"", sig))
        self.assertFalse(s3app.ed25519_verify(pk, b"x", sig))


# Sample apps: apps/ in the private repo, examples/apps/ in the public SDK repo.
APPS = next(d for d in (SDK.parent / "apps", SDK / "examples" / "apps") if d.is_dir())


class Icon(unittest.TestCase):
    def test_preinstalled_icons_pass(self):
        icons = sorted(APPS.glob("*/icon.png"))
        self.assertTrue(icons)
        for p in icons:
            check_icon(p.read_bytes())

    def test_what_the_watch_refuses(self):
        good = (APPS / "snake" / "icon.png").read_bytes()
        for png, msg in [(b"GIF89a" + bytes(30), "not a PNG"),
                         (good[:16] + (64).to_bytes(4, "big") + good[20:], "64x80"),
                         (good[:24] + b"\x10" + good[25:], "8 bits"),
                         (good[:28] + b"\x01" + good[29:], "interlaced"),
                         (good + bytes(64 * 1024), "over 64 KB")]:
            with self.assertRaisesRegex(BuildError, msg):
                check_icon(png)


class RustBindings(unittest.TestCase):
    def test_s3w_sys_is_fresh(self):
        r = subprocess.run([sys.executable, str(SDK / "rust" / "s3w-sys" / "gen.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class Templates(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="s3w_cli_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def new_build(self, lang):
        app = self.tmp / f"my_{lang}_app"
        self.assertEqual(cli.main(["new", str(app), "--lang", lang]), 0)
        self.assertEqual(cli.main(["build", str(app), "--unsigned"]), 0)
        p = Project(app)
        self.assertEqual(p.id, f"dev.example.my_{lang}_app")
        imports, exports = module_info(p.wasm.read_bytes())
        self.assertTrue(all(m == "s3w" for m, _, _ in imports))
        self.assertIn("s3w_on_start", exports)
        self.assertIn("s3w_event_buf", exports)
        with zipfile.ZipFile(p.pkg) as z:
            self.assertEqual(sorted(z.namelist()), ["app.wasm", "manifest.json"])
        return app, p

    def run_sim(self, app, p):
        sim = sim_path()
        if not sim:
            self.skipTest("no simulator (build/sim/s3w_sim or S3W_SIM)")
        script = self.tmp / "s.txt"
        script.write_text(SCRIPT)
        shot = self.tmp / "s.png"
        t0 = time.time()
        r = subprocess.run([sys.executable, "-m", "s3w_cli", "run-sim", str(app), "--sim", sim,
                            "--script", str(script), "--screenshot", str(shot)],
                           cwd=HERE.parent, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"app {p.id}: started", r.stdout)
        self.assertNotIn("trapped", r.stdout + r.stderr)
        self.assertTrue(shot.exists())
        self.assertLess(time.time() - t0, 300)  # P8-06: from the template to the simulator in < 5 min

    @unittest.skipUnless(have_clang(), "no clang with the wasm32 target")
    def test_c_template(self):
        app, p = self.new_build("c")
        self.run_sim(app, p)

    @unittest.skipUnless(have_rust(), "no cargo with the wasm32-unknown-unknown target")
    def test_rust_template(self):
        app, p = self.new_build("rust")
        self.run_sim(app, p)

    @unittest.skipUnless(have_clang(), "no clang with the wasm32 target")
    def test_signed_package_verifies(self):
        app = self.tmp / "signed"
        cli.main(["new", str(app)])
        key = self.tmp / "dev.key"
        s3app.main(["keygen", str(key)])
        self.assertEqual(cli.main(["build", str(app), "--key", str(key)]), 0)
        m, signer = s3app.verify(str(Project(app).pkg))
        self.assertEqual(signer, s3app.ed25519_public(s3app.load_key(str(key))))

    def test_new_refuses_a_non_empty_dir(self):
        (self.tmp / "x").mkdir()
        (self.tmp / "x" / "f").write_text("keep")
        self.assertEqual(cli.main(["new", str(self.tmp / "x")]), 1)
        self.assertEqual((self.tmp / "x" / "f").read_text(), "keep")

    def test_imports_outside_the_api_are_refused(self):
        # A module importing env.memcpy (what a libc call would leave behind).
        wasm = bytes.fromhex("0061736d01000000") + bytes.fromhex("010401600000") + \
            bytes([2, 14, 1, 3]) + b"env" + bytes([6]) + b"memcpy" + bytes([0, 0])
        app = self.tmp / "imp"
        cli.main(["new", str(app)])
        p = Project(app)
        p.build_dir.mkdir()
        p.wasm.write_bytes(wasm)
        with self.assertRaises(BuildError) as e:
            p.check_module()
        self.assertIn("env.memcpy", str(e.exception))


class Faces(unittest.TestCase):
    """`s3w face` (P8-12): the watch's parser checks face.json, the simulator renders the 200x246 preview."""

    FACE = ('{"id": "dev.example.tick", "name": "Tick", "version": "1.0.0", "api": 1, "elements": ['
            '{"type": "text", "bind": "time.hh:mm", "x": 205, "y": 251, "font": "digits_96"}]}')

    def setUp(self):
        sim = sim_path()
        if not sim:
            self.skipTest("no simulator (build/sim/s3w_sim or S3W_SIM)")
        os.environ["S3W_SIM"] = sim
        self.tmp = Path(tempfile.mkdtemp(prefix="s3w_face_"))
        self.dir = self.tmp / "tick"
        self.dir.mkdir()
        (self.dir / "face.json").write_text(self.FACE)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_signs_and_verifies(self):
        key = self.tmp / "k"
        self.assertEqual(cli.main(["keygen", str(key)]), 0)
        self.assertEqual(cli.main(["face", "build", str(self.dir), "--key", str(key)]), 0)
        pkg = self.dir / "build" / "dev.example.tick.s3face"
        with zipfile.ZipFile(pkg) as z:
            self.assertEqual(sorted(z.namelist()), ["face.json", "preview.png", "signature.sig"])
        self.assertEqual(cli.main(["face", "verify", str(pkg), "--pub", (key.parent / "k.pub").read_text().strip()]), 0)
        self.assertEqual(cli.main(["face", "pack", str(self.dir), "--unsigned"]), 0)  # the last preview

    def test_what_the_watch_refuses(self):
        (self.dir / "face.json").write_text(self.FACE.replace("time.hh:mm", "time.nope"))
        self.assertEqual(cli.main(["face", "build", str(self.dir), "--unsigned"]), 1)
        (self.dir / "face.json").write_text(self.FACE.replace("dev.example.tick", "digital"))
        self.assertEqual(cli.main(["face", "build", str(self.dir), "--unsigned"]), 1)
        (self.dir / "face.json").write_text(self.FACE)
        (self.dir / "notes.txt").write_text("x")  # a face is face.json and its images
        self.assertEqual(cli.main(["face", "build", str(self.dir), "--unsigned"]), 1)


if __name__ == "__main__":
    unittest.main()
