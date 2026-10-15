"""The developer docs (P16-05): structure, links, snippets that build, screenshots that are fresh.

  python3 -m unittest discover -s sdk/tools -p "test_check_docs*"
  (S3W_SIM, CLANG and a Rust wasm32 toolchain enable the snippet and screenshot tests; without them they skip)"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_docs as cd  # noqa: E402

TOOLS = cd.tool_clang(), cd.tool_rust(), cd.find_sim()
GOOD_C = '#include "s3w.h"\nvoid s3w_on_start(void) { s3w_log(S3W_LOG_INFO, "hi", 2); }\n'


class RealDocs(unittest.TestCase):
    def test_structure_and_links(self):
        self.assertEqual(list(cd.check_structure()), [])

    def test_every_page_has_a_title_and_text(self):
        for p in cd.pages():
            if cd.rel(p).startswith("api/"):
                continue  # generated
            text = p.read_text()
            self.assertTrue(text.startswith("# "), f"{cd.rel(p)} must start with a # title")
            self.assertGreater(len(text.split()), 40, f"{cd.rel(p)} is a stub")

    @unittest.skipUnless(all(TOOLS), "needs clang with wasm32, a Rust wasm32 toolchain and the simulator")
    def test_snippets_build_and_validate(self):
        probs, skipped, counts = cd.check_snippets(True)
        self.assertEqual(list(probs), [])
        self.assertEqual(skipped, [])
        self.assertGreaterEqual(counts["c-check"], 8)
        self.assertGreaterEqual(counts["rust-check"], 1)
        self.assertGreaterEqual(counts["manifest-check"], 3)
        self.assertGreaterEqual(counts["face-check"], 2)

    @unittest.skipUnless(TOOLS[2] and os.environ.get("S3W_SIM"), "needs S3W_SIM (a simulator built from these sources)")
    def test_screenshots_are_fresh(self):
        import doc_shots
        doc_shots.main(["--check"])


class Fixture(unittest.TestCase):
    """A tiny docs tree with one deliberately wrong page at a time."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.saved = cd.DOCS
        cd.DOCS = self.root
        (self.root / "projects" / "p" / "src").mkdir(parents=True)
        (self.root / "projects" / "p" / "src" / "main.c").write_text(GOOD_C)
        (self.root / "projects" / "p" / "manifest.json").write_text(json.dumps(
            {"id": "dev.a.p", "name": "P", "version": "1.0.0", "api_level": 1, "ui_mode": "widgets"}))
        self.write("index.md", "# Home\n\nText.\n")
        self.nav(["index.md"])

    def tearDown(self):
        cd.DOCS = self.saved
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def nav(self, paths):
        self.write("nav.json", json.dumps({"sections": [{"title": "All", "pages": [{"path": p, "title": p} for p in paths]}]}))

    def structure(self):
        return "\n".join(cd.check_structure())

    def snippets(self):
        probs, _, _ = cd.check_snippets(False)
        return "\n".join(probs)

    def test_page_missing_from_nav(self):
        self.write("extra.md", "# Extra\n")
        self.assertIn("extra.md: is not in nav.json", self.structure())

    def test_nav_names_a_missing_page(self):
        self.nav(["index.md", "gone.md"])
        self.assertIn("gone.md does not exist", self.structure())

    def test_broken_link_and_anchor(self):
        self.write("index.md", "# Home\n\n[a](nothing.md) [b](#no-such-heading) [c](index.md#home)\n")
        out = self.structure()
        self.assertIn("nothing.md does not resolve", out)
        self.assertIn("#no-such-heading: no such heading", out)
        self.assertNotIn("index.md#home", out)

    def test_missing_image(self):
        self.write("index.md", "# Home\n\n![x](img/none.png)\n")
        self.assertIn("img/none.png does not resolve", self.structure())

    def test_private_references_fail(self):
        self.write("index.md", "# Home\n\nSee docs/05 and P8-12 and firmware/" + "components/x and build/sim/s3w_sim.\n")
        out = self.structure()
        for what in ("a private doc", "a task id", "a private path", "a private build path"):
            self.assertIn(what, out)

    def test_code_blocks_are_not_scanned_for_private_names(self):
        self.write("index.md", "# Home\n\n```\ndocs/05 P8-12\n```\n")
        self.assertEqual(self.structure(), "")

    @unittest.skipUnless(TOOLS[0], "needs clang")
    def test_a_c_snippet_that_does_not_compile_fails(self):
        self.write("index.md", "# Home\n\n```c-check\n#include \"s3w.h\"\nvoid s3w_on_start(void) { nope(); }\n```\n")
        self.assertIn("index.md:3", self.snippets())

    @unittest.skipUnless(TOOLS[0], "needs clang")
    def test_a_c_snippet_that_imports_libc_fails(self):
        self.write("index.md", "# Home\n\n```c-check\n#include \"s3w.h\"\nint puts(const char *);\nvoid s3w_on_start(void) { puts(\"x\"); }\n```\n")
        self.assertIn("index.md:3", self.snippets())

    @unittest.skipUnless(TOOLS[0], "needs clang")
    def test_a_good_c_snippet_passes(self):
        self.write("index.md", f"# Home\n\n```c-check\n{GOOD_C}```\n")
        self.assertEqual(self.snippets(), "")

    @unittest.skipUnless(TOOLS[0], "needs clang")
    def test_a_project_snippet_must_equal_the_project(self):
        self.write("index.md", "# Home\n\n```c-check project=p\n" + GOOD_C.replace("hi", "ho") + "```\n")
        self.assertIn("differs from docs/projects/p", self.snippets())
        self.write("index.md", f"# Home\n\n```c-check project=p\n{GOOD_C}```\n")
        self.assertEqual(self.snippets(), "")

    def test_bad_manifests_fail(self):
        for what, patch in (("unknown", {"permissions": ["telepathy"]}), ("storage", {"storage_kb": 100}),
                            ("hosts", {"http_hosts": ["a.b"]}), ("api", {"api_level": 99}), ("id", {"id": "nodots"}),
                            ("mem", {"memory_kb": 8})):
            m = {"id": "dev.a.b", "name": "N", "version": "1.0.0", "api_level": 1, "ui_mode": "widgets"}
            m.update(patch)
            self.write("index.md", "# Home\n\n```manifest-check\n" + json.dumps(m) + "\n```\n")
            self.assertIn("index.md:3", self.snippets(), what)

    def test_a_manifest_with_a_missing_key_fails(self):
        self.write("index.md", '# Home\n\n```manifest-check\n{"id": "dev.a.b"}\n```\n')
        self.assertIn("name missing", self.snippets())

    @unittest.skipUnless(TOOLS[2], "needs the simulator")
    def test_a_bad_face_fails(self):
        face = {"id": "dev.a.b", "name": "N", "version": "1.0.0", "api": 1, "background": "#000000",
                "elements": [{"type": "text", "bind": "no.such.binding", "x": 205, "y": 251}]}
        self.write("index.md", "# Home\n\n```face-check\n" + json.dumps(face) + "\n```\n")
        self.assertIn("index.md:3", self.snippets())
        face["elements"][0]["bind"] = "time.hh:mm"
        self.write("index.md", "# Home\n\n```face-check\n" + json.dumps(face) + "\n```\n")
        self.assertEqual(self.snippets(), "")


if __name__ == "__main__":
    unittest.main()
