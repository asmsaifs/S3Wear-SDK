"""API reference generator (P16-04): the header is fully documented and docs/api is fresh.

  python3 -m unittest discover -s sdk/tools     (CI of the SDK repo runs this too)

S3W_SIM (a simulator binary) also checks docs/api/face-registry.json against `--list-face-registry`."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_api_docs as g  # noqa: E402

HEADER = Path(g.HEADER).read_text()
REGISTRY = json.loads(Path(g.REGISTRY).read_text())

MINI = """
#define S3W_API_LEVEL 2
#if defined(__wasm__)
#define S3W_IMPORT(name) __attribute__((import_module("s3w"), import_name(#name)))
#define S3W_EXPORT(name) __attribute__((export_name(#name)))
/* --- Things --- */
/* Does a thing.
 * @since 1 */
int s3w_thing(int a) S3W_IMPORT(s3w_thing);
/* Needs a card. Works with s3w_thing or S3W_ERR_IO.
 * @since 2  @perm files */
int s3w_card(void) S3W_IMPORT(s3w_card);
#endif /* __wasm__ */
"""


def build(header):
    return g.generate(header, REGISTRY)


class Header(unittest.TestCase):
    def test_every_function_is_documented(self):
        groups, problems = g.parse_header(HEADER)
        self.assertEqual(problems + g.problems_of(groups, g.api_level_of(HEADER)), [])

    def test_all_functions_are_listed(self):
        want = re.findall(r"S3W_(?:IMPORT|EXPORT)\((s3w_\w+)\)\s*;", HEADER)
        listed = [f["name"] for grp in json.loads((Path(g.OUT) / "api.json").read_text())["groups"] for f in grp["functions"]]
        self.assertEqual(sorted(listed), sorted(want))

    def test_docs_are_fresh(self):
        files, problems = g.generate(HEADER, REGISTRY)
        self.assertEqual(problems, [])
        for name, text in files.items():
            self.assertEqual((Path(g.OUT) / name).read_text(), text,
                             f"docs/api/{name} is stale: run sdk/tools/gen_api_docs.py")
        extra = {p.name for p in Path(g.OUT).iterdir()} - set(files) - {"face-registry.json"}
        self.assertEqual(extra, set())

    @unittest.skipUnless(os.environ.get("S3W_SIM") and Path(os.environ["S3W_SIM"]).exists(), "needs S3W_SIM")
    def test_face_registry_matches_the_simulator(self):
        self.assertEqual(g.registry_from_sim(os.environ["S3W_SIM"]), REGISTRY,
                         "run sdk/tools/gen_api_docs.py --sim $S3W_SIM")


class Rules(unittest.TestCase):
    def problems(self, header):
        files, problems = build(header)
        return problems

    def test_mini_header_is_fine(self):
        files, problems = build(MINI)
        self.assertEqual(problems, [])
        page = files["things.md"]
        self.assertIn("## s3w_card", page)
        self.assertIn("api_level 2 · permission `files`", page)
        self.assertIn("[`s3w_thing`](#s3w_thing)", page)  # a function named in prose links to its entry
        self.assertIn("`S3W_ERR_IO`", page)

    def test_undocumented_function_fails(self):
        bad = MINI.replace("/* Does a thing.\n * @since 1 */\n", "")
        self.assertTrue(any("s3w_thing: no doc comment" in p for p in self.problems(bad)))

    def test_comment_without_text_fails(self):
        bad = MINI.replace("/* Does a thing.\n * @since 1 */", "/* @since 1 */")
        self.assertTrue(any("s3w_thing: no doc comment" in p for p in self.problems(bad)))

    def test_missing_since_fails(self):
        bad = MINI.replace(" * @since 1 */", " */")
        self.assertTrue(any("s3w_thing: no @since" in p for p in self.problems(bad)))

    def test_since_beyond_the_api_level_fails(self):
        bad = MINI.replace("@since 2", "@since 3")
        self.assertTrue(any("@since 3 is outside" in p for p in self.problems(bad)))

    def test_unknown_permission_and_tag_fail(self):
        self.assertTrue(any("unknown permission 'fies'" in p for p in self.problems(MINI.replace("@perm files", "@perm fies"))))
        self.assertTrue(any("unknown tag @sinec" in p for p in self.problems(MINI.replace("@since 1", "@sinec 1 @since 1"))))

    def test_function_outside_a_section_fails(self):
        bad = MINI.replace("/* --- Things --- */\n", "")
        self.assertTrue(any("outside a" in p for p in self.problems(bad)))

    def test_two_functions_under_one_comment_fail(self):
        bad = MINI.replace("int s3w_thing(int a) S3W_IMPORT(s3w_thing);",
                           "int s3w_thing(int a) S3W_IMPORT(s3w_thing);\nint s3w_other(void) S3W_IMPORT(s3w_other);")
        self.assertTrue(any("s3w_other: no doc comment" in p for p in self.problems(bad)))

    def test_internal_is_skipped(self):
        files, problems = build(MINI.replace("#endif", "/* Helper. @internal */\nint s3w_helper(void) S3W_IMPORT(s3w_helper);\n#endif"))
        self.assertEqual(problems, [])
        self.assertNotIn("s3w_helper", files["things.md"])

    def test_alternative_permissions(self):
        files, _ = build(MINI.replace("@perm files", "@perm phone.http or wifi.http"))
        self.assertIn("permission `phone.http` or `wifi.http`", files["things.md"])


if __name__ == "__main__":
    unittest.main()
