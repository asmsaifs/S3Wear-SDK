"""s3w check (P16-09): every rule has a fixture that fails it, and the monkey test catches a planted leak and trap.

  python3 -m unittest discover -s sdk/tools/s3w-cli/tests -p "test_check*"

The C fixtures need clang with wasm32 and the simulator (S3W_SIM): without them those tests skip."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from s3w_cli import check as checker, cli, rules  # noqa: E402
from s3w_cli.project import SDK, find_clang, BuildError  # noqa: E402
from test_cli import make_png  # noqa: E402

FIX = HERE / "fixtures" / "check"
LISTING = {"developer": "octocat", "summary": "A small test app.", "support_url": "https://example.com/support",
           "source_url": "https://example.com/source", "content_rating": "everyone"}


def have_clang():
    try:
        find_clang()
        return True
    except BuildError:
        return False


def sim_path():
    p = os.environ.get("S3W_SIM") or str(SDK.parent / "build" / "sim" / "s3w_sim")
    return p if Path(p).exists() else None


TOOLS = have_clang() and sim_path()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="s3w_check_test_"))
        if sim_path():
            os.environ["S3W_SIM"] = sim_path()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def app(self, name="demo", id_="io.github.octocat.demo", manifest=None, listing=None, listing_extra=None):
        """A C app from the template with a valid listing; manifest / listing replace or add keys."""
        d = self.tmp / "apps" / id_
        d.parent.mkdir(exist_ok=True)
        shutil.rmtree(d, ignore_errors=True)  # a test may make several apps with the same id
        with __import__("contextlib").redirect_stdout(io.StringIO()):
            cli.main(["new", str(d), "--id", id_, "--name", name.title()])
        m = json.loads((d / "manifest.json").read_text())
        m.update(manifest or {})
        (d / "manifest.json").write_text(json.dumps(m))
        lst = dict(LISTING if listing is None else listing)
        lst.update(listing_extra or {})
        (d / "listing.json").write_text(json.dumps(lst))
        return d

    def fixture(self, name, listing_extra=None):
        d = self.tmp / "apps" / f"fx.{name}"
        d.parent.mkdir(exist_ok=True)
        shutil.copytree(FIX / name, d)
        (d / "listing.json").write_text(json.dumps({**LISTING, "developer": "octocat", **(listing_extra or {})}))
        return d

    def run_checks(self, d, only=None, **kw):
        opts = checker.Options(developer=kw.pop("developer", "octocat"), only=only, monkey_seconds=kw.pop("monkey_seconds", 30),
                               sim=kw.pop("sim", None), **kw)
        rep = checker.run_checks(d, opts)
        return rep, {c["id"]: c for c in rep["checks"]}

    def messages(self, check):
        return [f["message"] for f in check["findings"]]

    def assertFails(self, check, text):
        self.assertEqual(check["status"], "fail", check)
        self.assertTrue(any(text in m for m in self.messages(check)), f"{text!r} not in {self.messages(check)}")


class Layout(Base):
    def test_a_stray_file_a_binary_and_a_missing_listing(self):
        d = self.app()
        (d / "notes.txt").write_text("x")
        (d / "src" / "game.wasm").write_bytes(b"\0asm")
        (d / "listing.json").unlink()
        (d / "assets").mkdir()
        (d / "assets" / "movie.mp4").write_bytes(b"x")
        _, c = self.run_checks(d, ["layout"])
        msgs = self.messages(c["layout"])
        self.assertTrue(any("notes.txt" in str(f) for f in c["layout"]["findings"]))
        self.assertIn("a built file: the store builds from source", msgs)
        self.assertIn("listing.json is missing", msgs)
        self.assertEqual(sum("not part of an app" in m for m in msgs), 2)  # notes.txt, movie.mp4
        self.assertEqual(c["layout"]["status"], "fail")

    def test_the_folder_must_be_named_like_the_id(self):
        d = self.app()
        other = d.parent / "other-name"
        d.rename(other)
        _, c = self.run_checks(other, ["layout"])
        self.assertFails(c["layout"], "the folder is named 'other-name'")

    def test_build_output_and_dot_files_are_ignored(self):
        d = self.app()
        (d / "build").mkdir()
        (d / "build" / "app.wasm").write_bytes(b"\0asm")
        (d / ".DS_Store").write_bytes(b"x")
        _, c = self.run_checks(d, ["layout"])
        self.assertEqual(c["layout"]["status"], "pass")

    def test_a_face_may_hold_only_face_json_pictures_and_listing(self):
        d = self.tmp / "faces" / "io.github.octocat.f"
        d.mkdir(parents=True)
        (d / "face.json").write_text("{}")
        (d / "bg.png").write_bytes(b"x")
        (d / "listing.json").write_text(json.dumps(LISTING))
        (d / "extra.txt").write_text("x")
        (d / "sub").mkdir()
        (d / "sub" / "a.png").write_bytes(b"x")
        _, c = self.run_checks(d, ["layout"])
        self.assertEqual(sorted(f["file"] for f in c["layout"]["findings"]), ["extra.txt", "sub/a.png"])


class Listing(Base):
    def problems(self, **extra):
        d = self.app(**extra)
        _, c = self.run_checks(d, ["listing"])
        return c["listing"], self.messages(c["listing"])

    def test_a_valid_listing_passes(self):
        c, _ = self.problems()
        self.assertEqual(c["status"], "pass")

    def test_each_rule(self):
        for what, patch, text in (
                ("summary", {"summary": "x" * 81}, "81 characters, at most 80"),
                ("url", {"support_url": "http://example.com"}, "https:// URL"),
                ("unknown", {"colour": "red"}, "not a listing field"),
                ("rating", {"content_rating": "adult"}, "one of everyone, teen"),
                ("captions", {"screenshot_captions": ["a"] * 9}, "9 items, at most 8"),
                ("caption long", {"screenshot_captions": ["a" * 61]}, "61 characters"),
                ("developer", {"developer": "bad login!"}, "does not look right")):
            c, msgs = self.problems(listing_extra=patch)
            self.assertEqual(c["status"], "fail", what)
            self.assertTrue(any(text in m for m in msgs), (what, msgs))

    def test_missing_fields(self):
        c, msgs = self.problems(listing={"developer": "octocat"})
        self.assertIn("listing.summary: missing", msgs)
        self.assertIn("listing.support_url: missing", msgs)

    def test_every_permission_and_host_needs_a_reason(self):
        c, msgs = self.problems(manifest={"permissions": ["imu", "phone.http"], "http_hosts": "api.example.com"},
                                listing_extra={"permission_reasons": {"imu": "Tilt to steer"}})
        self.assertIn("permission_reasons.phone.http: missing (every permission needs a reason)", msgs)
        self.assertIn("http_reasons.api.example.com: missing (every host needs a reason)", msgs)
        c, msgs = self.problems(listing_extra={"permission_reasons": {"imu": "x"}, "http_reasons": {"a.b": "x"}})
        self.assertTrue(any("'imu' is not in the manifest's permissions" in m for m in msgs))
        self.assertTrue(any("'a.b' is not in the manifest's http_hosts" in m for m in msgs))

    def test_a_privacy_policy_is_required_for_the_data_permissions(self):
        for perm in sorted(rules.PRIVACY_PERMISSIONS):
            c, msgs = self.problems(manifest={"permissions": [perm]}, listing_extra={"permission_reasons": {perm: "Needed"}})
            self.assertTrue(any(f"privacy_url: required with {perm}" in m for m in msgs), perm)
        c, msgs = self.problems(manifest={"permissions": ["imu"]}, listing_extra={"permission_reasons": {"imu": "Needed"}})
        self.assertEqual(c["status"], "pass")  # imu needs none

    def test_the_developer_must_be_the_submitter(self):
        d = self.app(listing_extra={"developer": "someoneelse"})
        _, c = self.run_checks(d, ["listing"])
        self.assertFails(c["listing"], "the submitter is 'octocat'")

    def test_the_schema_file_is_what_the_tool_prints(self):
        want = rules.listing_schema_json()
        self.assertEqual((HERE.parent / "s3w_cli" / "listing_schema.json").read_text(), want)
        store = HERE.parents[3] / "tools" / "store" / "listing_schema.json"
        if store.exists():
            self.assertEqual(store.read_text(), want)
        schema = json.loads(want)
        self.assertEqual(sorted(schema["required"]), ["content_rating", "developer", "source_url", "summary", "support_url"])


class Manifest(Base):
    def test_rules(self):
        for what, patch, text in (("permission", {"permissions": ["telepathy"]}, "unknown 'telepathy'"),
                                  ("api", {"api_level": 99}, "api_level: 1.."),
                                  ("storage", {"storage_kb": 100}, "needs the storage permission"),
                                  ("memory", {"memory_kb": 8}, "memory_kb"),
                                  ("mode", {"ui_mode": "hologram"}, "ui_mode")):
            d = self.app(id_=f"io.github.octocat.m{abs(hash(what)) % 1000}", manifest=patch)
            _, c = self.run_checks(d, ["manifest"])
            self.assertFails(c["manifest"], text)

    def test_a_manifest_that_is_not_json(self):
        d = self.app()
        (d / "manifest.json").write_text("{ nope")
        _, c = self.run_checks(d, ["manifest"])
        self.assertEqual(c["manifest"]["status"], "fail")

    @unittest.skipUnless(sim_path(), "needs the simulator")
    def test_a_face_the_watch_refuses(self):
        d = self.tmp / "faces" / "io.github.octocat.f"
        d.mkdir(parents=True)
        (d / "face.json").write_text(json.dumps({"id": "io.github.octocat.f", "name": "F", "version": "1.0.0", "api": 1,
                                                  "elements": [{"type": "text", "bind": "no.such", "x": 205, "y": 251}]}))
        (d / "listing.json").write_text(json.dumps(LISTING))
        _, c = self.run_checks(d, ["manifest"], sim=sim_path())
        self.assertEqual(c["manifest"]["status"], "fail")
        (d / "face.json").write_text(json.dumps({"id": "digital", "name": "F", "version": "1.0.0", "api": 1,
                                                  "elements": [{"type": "text", "bind": "time.hh:mm", "x": 205, "y": 251}]}))
        _, c = self.run_checks(d, ["manifest"], sim=sim_path())
        self.assertFails(c["manifest"], "built-in")


class Ownership(Base):
    def test_skipped_without_a_developer(self):
        d = self.app()
        rep, c = self.run_checks(d, ["ownership"], developer=None)
        self.assertEqual(c["ownership"]["status"], "skip")

    def test_the_id_must_be_in_a_namespace_of_the_developer(self):
        _, c = self.run_checks(self.app(id_="io.github.octocat.ok"), ["ownership"])
        self.assertEqual(c["ownership"]["status"], "pass")
        _, c = self.run_checks(self.app(id_="io.github.mallory.x"), ["ownership"])
        self.assertFails(c["ownership"], "outside your namespaces")
        _, c = self.run_checks(self.app(id_="com.example.snake"), ["ownership"])
        self.assertFails(c["ownership"], "outside your namespaces")

    def test_reserved_ids(self):
        for ident in ("dev.s3wear.snake", "s3w.thing", "com.s3wear.app"):
            _, c = self.run_checks(self.app(id_=ident), ["ownership"])
            self.assertFails(c["ownership"], "reserved")

    def test_a_domain_namespace_needs_the_dns_record(self):
        d = self.app(id_="com.example.snake")
        prof = {"namespaces": ["com.example"]}
        _, c = self.run_checks(d, ["ownership"], profile=prof, verify_dns=True, dns_lookup=lambda dom: ["s3wear-developer=octocat"])
        self.assertEqual(c["ownership"]["status"], "pass")
        _, c = self.run_checks(d, ["ownership"], profile=prof, verify_dns=True, dns_lookup=lambda dom: ["s3wear-developer=mallory"])
        self.assertFails(c["ownership"], "DNS TXT record 's3wear-developer=octocat' was not found")
        _, c = self.run_checks(d, ["ownership"], profile=prof)  # not asked to verify: a warning for the reviewer
        self.assertEqual(c["ownership"]["status"], "warn")

        def broken(domain):
            raise OSError("no network")
        _, c = self.run_checks(d, ["ownership"], profile=prof, verify_dns=True, dns_lookup=broken)
        self.assertEqual(c["ownership"]["status"], "warn")

    def test_changes_to_other_developers_files_are_refused(self):
        d = self.app(id_="io.github.octocat.ok")
        changed = ["apps/io.github.octocat.ok/src/main.c", "developers/octocat.json",
                   "apps/io.github.mallory.x/src/main.c", "developers/mallory.json", ".github/workflows/store.yml"]
        _, c = self.run_checks(d, ["ownership"], changed=changed)
        files = {f["file"]: f["message"] for f in c["ownership"]["findings"]}
        self.assertEqual(set(files), {"apps/io.github.mallory.x/src/main.c", "developers/mallory.json", ".github/workflows/store.yml"})
        self.assertIn("another developer's app", files["apps/io.github.mallory.x/src/main.c"])
        self.assertIn("another developer's profile", files["developers/mallory.json"])
        _, c = self.run_checks(d, ["ownership"], changed=changed[:2])
        self.assertEqual(c["ownership"]["status"], "pass")


class Version(Base):
    INDEX = {"apps": [{"id": "io.github.octocat.demo", "version": "1.2.0"}], "faces": []}

    def test_must_be_higher_than_the_published_version(self):
        d = self.app(manifest={"version": "1.2.0"})
        _, c = self.run_checks(d, ["version"], published=self.INDEX)
        self.assertFails(c["version"], "not higher than the published 1.2.0")
        d = self.app(manifest={"version": "1.10.0"})
        _, c = self.run_checks(d, ["version"], published=self.INDEX)
        self.assertEqual(c["version"]["status"], "pass")  # 1.10.0 > 1.2.0: numbers, not text
        d = self.app(id_="io.github.octocat.new", manifest={"version": "0.1.0"})
        _, c = self.run_checks(d, ["version"], published=self.INDEX)
        self.assertEqual(c["version"]["status"], "pass")  # a new id
        _, c = self.run_checks(d, ["version"])
        self.assertEqual(c["version"]["status"], "skip")


@unittest.skipUnless(TOOLS, "needs clang with wasm32 and the simulator (S3W_SIM)")
class WithTools(Base):
    def test_a_good_app_passes_everything(self):
        d = self.app(listing_extra={"screenshot_captions": ["The counter"]})
        rep, c = self.run_checks(d, published={"apps": []})
        self.assertTrue(rep["summary"]["ok"], [(k, v["findings"]) for k, v in c.items() if v["status"] == "fail"])
        for cid in ("layout", "listing", "manifest", "ownership", "build", "api_level", "run", "monkey", "budget", "permissions",
                    "content", "sizes"):
            self.assertIn(c[cid]["status"], ("pass", "warn"), (cid, c[cid]))
        self.assertGreater(c["build"]["data"]["package_bytes"], 1000)
        self.assertGreaterEqual(c["monkey"]["data"]["events"], 1)

    def test_a_build_that_fails(self):
        d = self.app()
        (d / "src" / "main.c").write_text('#include "s3w.h"\nvoid s3w_on_start(void) { nope(); }\n')
        _, c = self.run_checks(d, ["build"])
        self.assertEqual(c["build"]["status"], "fail")

    def test_a_module_that_imports_libc_is_refused(self):
        d = self.app()
        (d / "src" / "main.c").write_text('#include "s3w.h"\nint puts(const char *);\nvoid s3w_on_start(void) { puts("x"); }\n')
        _, c = self.run_checks(d, ["build"])
        msgs = self.messages(c["build"])
        self.assertTrue(any("imports the watch does not provide" in m or "undefined symbol: puts" in m for m in msgs), msgs)

    def test_a_package_over_the_limit(self):
        d = self.app()
        (d / "assets").mkdir()
        (d / "assets" / "big.dat").write_bytes(os.urandom(4 * 1024 * 1024 + 1024))
        _, c = self.run_checks(d, ["build"])
        self.assertEqual(c["build"]["status"], "fail")
        self.assertTrue(any("over" in m or "4096" in m for m in self.messages(c["build"])), self.messages(c["build"]))

    def test_api_level_above_the_simulators(self):
        d = self.app(manifest={"api_level": 99})
        _, c = self.run_checks(d, ["api_level"], sim=sim_path())
        self.assertFails(c["api_level"], "above the newest released firmware's")

    def test_icon_rules(self):
        d = self.app()
        _, c = self.run_checks(d, ["icon"])
        self.assertEqual(c["icon"]["status"], "warn")  # none: a warning
        (d / "icon.png").write_bytes(make_png(64, 64))
        _, c = self.run_checks(d, ["icon"])
        self.assertFails(c["icon"], "must be 80x80")
        (d / "icon.png").write_bytes(make_png(80, 80))
        _, c = self.run_checks(d, ["icon"])
        self.assertEqual(c["icon"]["status"], "pass")

    def test_screenshot_scripts(self):
        d = self.app(listing_extra={"screenshot_captions": ["One", "Two", "Three"]})
        (d / "screens").mkdir()
        (d / "screens" / "start.txt").write_text("wait 600\n")
        (d / "screens" / "broken.txt").write_text("wait 300\napp-is trapped\n")
        _, c = self.run_checks(d, ["build", "screenshots"])
        self.assertTrue(any(f.get("file") == "screens/broken.txt" for f in c["screenshots"]["findings"]), c["screenshots"])
        self.assertTrue(any("3 screenshot captions for 2" in m for m in self.messages(c["screenshots"])))

    def test_an_app_that_traps_at_start_fails_the_run(self):
        d = self.fixture("boot_trap")
        _, c = self.run_checks(d, ["build", "run"])
        self.assertFails(c["run"], "did not survive")

    def test_the_monkey_catches_a_planted_leak(self):
        d = self.fixture("leak")
        _, c = self.run_checks(d, ["build", "monkey"], monkey_seconds=60)
        self.assertFails(c["monkey"], "UI handles leak")
        self.assertGreater(c["monkey"]["data"]["handles"][-1], c["monkey"]["data"]["handles"][0])

    def test_the_monkey_catches_a_planted_timer_leak(self):
        d = self.fixture("timers")
        _, c = self.run_checks(d, ["build", "monkey"], monkey_seconds=60)
        self.assertFails(c["monkey"], "timers leak")

    def test_the_monkey_catches_a_planted_trap(self):
        d = self.fixture("trap")
        _, c = self.run_checks(d, ["build", "monkey"], monkey_seconds=60)
        self.assertFails(c["monkey"], "the app ended (trapped)")
        self.assertTrue(any("tap" in m for m in self.messages(c["monkey"])), "the message names the last action")

    def test_the_monkey_is_repeatable(self):
        d = self.fixture("trap")
        _, a = self.run_checks(d, ["build", "monkey"], monkey_seconds=60, seed=5)
        _, b = self.run_checks(d, ["build", "monkey"], monkey_seconds=60, seed=5)
        self.assertEqual(self.messages(a["monkey"]), self.messages(b["monkey"]))

    def test_slow_callbacks_warn(self):
        d = self.fixture("slow")
        _, c = self.run_checks(d, ["build", "monkey", "budget"], monkey_seconds=30)
        self.assertEqual(c["budget"]["status"], "warn", c["budget"])
        self.assertTrue(any("s3w_on_event" in m and "99th percentile" in m for m in self.messages(c["budget"])))

    def test_permissions_used_and_listed(self):
        d = self.app()
        (d / "src" / "main.c").write_text((HERE / "fixtures" / "check" / "imu_no_perm.c").read_text())
        _, c = self.run_checks(d, ["build", "permissions"])
        self.assertFails(c["permissions"], "needs the permission 'imu'")
        m = json.loads((d / "manifest.json").read_text())
        m["permissions"] = ["imu", "audio.play"]
        (d / "manifest.json").write_text(json.dumps(m))
        _, c = self.run_checks(d, ["build", "permissions"])
        self.assertEqual(c["permissions"]["status"], "warn")
        self.assertTrue(any("'audio.play' is listed but no function" in x for x in self.messages(c["permissions"])))

    def test_a_good_face_passes_and_a_bad_one_fails(self):
        d = self.tmp / "faces" / "io.github.octocat.sunrise"
        d.parent.mkdir(exist_ok=True)
        with __import__("contextlib").redirect_stdout(io.StringIO()):
            cli.main(["new", str(d), "--face", "--id", "io.github.octocat.sunrise", "--name", "Sunrise"])
        (d / "listing.json").write_text(json.dumps(LISTING))
        rep, c = self.run_checks(d, sim=sim_path())
        self.assertTrue(rep["summary"]["ok"], [(k, v["findings"]) for k, v in c.items() if v["status"] == "fail"])
        self.assertEqual(c["build"]["status"], "pass")
        self.assertEqual(c["run"]["status"], "pass")
        self.assertEqual(c["monkey"]["status"], "skip")  # apps only
        self.assertIn("preview.png", rep["screenshots"])
        face = json.loads((d / "face.json").read_text())
        face["name"] = "Mario Time"
        (d / "face.json").write_text(json.dumps(face))
        rep, c = self.run_checks(d, ["content"], sim=sim_path())
        self.assertFails(c["content"], "'mario'")

    def test_the_cli_exit_codes_and_report_files(self):
        good = self.app(listing_extra={"screenshot_captions": ["One"]})
        out = self.tmp / "report"
        with __import__("contextlib").redirect_stdout(io.StringIO()) as buf:
            rc = cli.main(["check", str(good), "--developer", "octocat", "--monkey-seconds", "30", "--out", str(out)])
        self.assertEqual(rc, 0, buf.getvalue())
        rep = json.loads((out / "report.json").read_text())
        self.assertEqual((rep["format"], rep["target"]["id"], rep["summary"]["ok"]), (1, "io.github.octocat.demo", True))
        self.assertIn("| ✅ |", (out / "report.md").read_text())
        self.assertTrue((out / "screens" / "first-screen.png").exists())
        bad = self.fixture("leak")
        with __import__("contextlib").redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["check", str(bad), "--developer", "octocat", "--monkey-seconds", "60"]), 1)


class Content(Base):
    def test_game_images_and_firmware(self):
        d = self.app()
        (d / "assets").mkdir()
        (d / "assets" / "tetris.gb").write_bytes(b"x")
        (d / "assets" / "gba_bios.dat").write_bytes(b"x")
        _, c = self.run_checks(d, ["content"])
        msgs = self.messages(c["content"])
        self.assertTrue(any("a game or disc image (.gb)" in m for m in msgs))
        self.assertTrue(any("a console's firmware" in m for m in msgs))

    def test_names_in_the_listing_text(self):
        for field, patch, word in (
                ("name", {"manifest": {"name": "Mario Run"}}, "mario"),
                ("description", {"manifest": {"description": "A Game Boy emulator"}}, "game boy"),
                ("summary", {"listing_extra": {"summary": "Better than a Nintendo"}}, "nintendo"),
                ("brand", {"manifest": {"description": "Syncs with Google Fit"}}, "google"),
                ("rude", {"manifest": {"description": "this is shit"}}, "shit"),
                ("caption", {"listing_extra": {"screenshot_captions": ["Pokemon style"]}}, "pokemon")):
            d = self.app(id_=f"io.github.octocat.c{abs(hash(field)) % 1000}", **patch)
            _, c = self.run_checks(d, ["content"])
            self.assertTrue(any(f"'{word}'" in m for m in self.messages(c["content"])), (field, c["content"]))

    def test_the_store_name_is_kept(self):
        for name in ("S3Wear Snake", "s3w calc", "S3Wear"):
            d = self.app(id_=f"io.github.octocat.n{abs(hash(name)) % 1000}", manifest={"name": name})
            _, c = self.run_checks(d, ["content"])
            self.assertFails(c["content"], "kept for the store's own apps")
        d = self.app(id_="io.github.octocat.nn", manifest={"name": "Snake for S3Wear"})
        _, c = self.run_checks(d, ["content"])
        self.assertEqual(c["content"]["status"], "pass")

    def test_words_inside_other_words_are_fine(self):
        d = self.app(manifest={"description": "Classic, shiitake and a grassy mariner"})
        _, c = self.run_checks(d, ["content"])
        self.assertEqual(c["content"]["status"], "pass")

    def test_an_extra_blocklist(self):
        d = self.app(manifest={"description": "Powered by Zorp"})
        _, c = self.run_checks(d, ["content"], blocklist={"brands": ["zorp"]})
        self.assertFails(c["content"], "'zorp' is someone else's brand")


class Sizes(Base):
    def test_description_and_name(self):
        d = self.app(manifest={"description": "x" * 201})
        _, c = self.run_checks(d, ["sizes"])
        self.assertFails(c["sizes"], "description is 201 characters, at most 200")
        d = self.app(id_="io.github.octocat.long", manifest={"name": "N" * 32})
        _, c = self.run_checks(d, ["sizes"])
        self.assertFails(c["sizes"], "name is 32 bytes")


class Report(Base):
    def test_structure_and_markdown(self):
        d = self.app(manifest={"permissions": ["telepathy"]})
        rep, c = self.run_checks(d, ["layout", "listing", "manifest"])
        self.assertEqual(rep["format"], 1)
        self.assertFalse(rep["summary"]["ok"])
        self.assertEqual(rep["summary"]["errors"], sum(len(x["findings"]) for x in rep["checks"] if x["status"] == "fail"))
        self.assertEqual([x["id"] for x in rep["checks"]], ["layout", "listing", "manifest"])
        md = checker.markdown(rep)
        self.assertIn("**Failed**", md)
        self.assertIn("| ❌ | Manifest / face.json |", md)
        self.assertIn("unknown 'telepathy'", md)

    def test_a_check_that_crashes_does_not_hide_the_others(self):
        d = self.app()
        saved = checker.check_layout
        try:
            checker.CHECKS[0] = ("layout", "Files and layout", lambda ctx, c: 1 / 0)
            rep, c = self.run_checks(d, ["layout", "listing"])
        finally:
            checker.CHECKS[0] = ("layout", "Files and layout", saved)
        self.assertFails(c["layout"], "the check itself failed")
        self.assertIn(c["listing"]["status"], ("skip", "pass", "fail"))

    def test_the_directory_must_be_an_app_or_a_face(self):
        with self.assertRaises(BuildError):
            checker.run_checks(self.tmp, checker.Options())


if __name__ == "__main__":
    unittest.main()
