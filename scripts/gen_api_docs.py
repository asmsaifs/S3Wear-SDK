#!/usr/bin/env python3
"""Generates the API reference (docs/api/) from include/s3w.h, the single source of truth.

  gen_api_docs.py                       rewrite docs/api/*.md and docs/api/api.json
  gen_api_docs.py --check               exit 1 if a problem is found or a generated file is stale (CI runs this)
  gen_api_docs.py --sim PATH            also refresh docs/api/face-registry.json from `PATH --list-face-registry`
                                        (with --check: fail if the committed registry differs from that simulator)

Every function in the header's wasm section needs a doc comment directly above it with the tags
  @since N          the api_level that added it (1..S3W_API_LEVEL)
  @perm a, b        permissions it needs (all of them); "a or b": any one of them
  @internal         not documented (the runtime's own helpers)
A section comment `/* --- Name ... --- */` starts a page; comments that do not sit directly above a function are
that page's introduction. The declaration parser is the one of rust/s3w-sys/gen.py.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDK = os.path.normpath(os.path.join(HERE, ".."))
HEADER = os.path.join(SDK, "include", "s3w.h")
OUT = os.path.join(SDK, "docs", "api")
REGISTRY = os.path.join(OUT, "face-registry.json")

sys.path.insert(0, os.path.join(SDK, "rust", "s3w-sys"))
import gen  # noqa: E402  (the header parser shared with the Rust bindings)

# The manifest's permission names (docs/05 §4); a typo in @perm is a bug in the header.
PERMISSIONS = {"storage", "imu", "audio.play", "audio.record", "health.read", "notify", "phone.http", "wifi.http",
               "location", "keep_screen_on", "background", "files", "gameboy"}
KNOWN_TAGS = ("@since", "@perm", "@internal")


class Func:
    def __init__(self, name, ret, params, kind, doc, group):
        self.name, self.ret, self.params, self.kind, self.group = name, ret, params, kind, group
        self.doc_raw = doc
        text = clean_comment(doc) if doc else ""
        self.since = None
        m = re.search(r"@since\s+(\d+)", text)
        if m:
            self.since = int(m.group(1))
        self.perm = None
        m = re.search(r"@perm\s+([^@\n]+)", text)
        if m:
            self.perm = m.group(1).strip()
        self.internal = "@internal" in text
        self.text = re.sub(r"@(since|perm)\b[^@\n]*|@internal", "", text).strip()

    @property
    def signature(self):
        params = ", ".join(f"{t.strip()} {n}".replace("* ", "*") if t.strip().endswith("*") else f"{t.strip()} {n}"
                           for n, t in self.params) or "void"
        ret = self.ret.strip()
        return f"{ret}{'' if ret.endswith('*') else ' '}{self.name}({params})"

    def perm_list(self):
        """(names, mode): mode is "all" or "any"."""
        if not self.perm:
            return [], "all"
        if " or " in self.perm:
            return [p.strip() for p in self.perm.split(" or ")], "any"
        return [p.strip() for p in self.perm.split(",")], "all"


class Group:
    def __init__(self, title):
        self.name = re.split(r"\s*[:\[(]", title, 1)[0].strip()
        sub = title.split(":", 1)[1].strip() if ":" in title.split("[")[0] else ""
        self.subtitle = sub
        self.slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        self.notes = []
        self.funcs = []


def clean_comment(c):
    body = c.strip()
    body = re.sub(r"^/\*+", "", body)
    body = re.sub(r"\*+/$", "", body)
    lines = [re.sub(r"^\s*\*\s?", "", ln).rstrip() for ln in body.split("\n")]
    return "\n".join(lines).strip()


def wasm_section(text):
    if "#if defined(__wasm__)" not in text:
        raise SystemExit("gen_api_docs: no wasm section in the header")
    return text.split("#if defined(__wasm__)", 1)[1].split("#endif /* __wasm__ */", 1)[0]


def parse_header(text):
    """-> (groups, problems). Walks the wasm section as comments and statements, in order."""
    problems = []
    groups, group = [], None
    section = wasm_section(text)
    prev_comment = None  # a comment with nothing but whitespace between it and the next token
    pos = 0
    for m in re.finditer(r"/\*.*?\*/", section, re.S):
        code, comment = section[pos:m.start()], m.group(0)
        pos = m.end()
        group, prev_comment = _take_code(code, prev_comment, group, groups, problems)
        title = re.match(r"/\*\s*---\s*(.+?)\s*-{3,}\s*\*/$", comment, re.S)
        if title:
            group = Group(" ".join(title.group(1).split()))
            groups.append(group)
            prev_comment = None
            continue
        if prev_comment is not None:
            _note(group, prev_comment)  # two comments in a row: the first one is a note
        prev_comment = comment
    group, prev_comment = _take_code(section[pos:], prev_comment, group, groups, problems)
    return [g for g in groups if g.funcs or g.notes], problems


def _note(group, comment):
    text = clean_comment(comment)
    if group is not None and "@internal" not in text and text:
        group.notes.append(text)


def _take_code(code, prev_comment, group, groups, problems):
    code = re.sub(r"^\s*#.*$", " ", code, flags=re.M)  # the import/export macros
    code = re.sub(r"\{[^{}]*\}", ";", code)  # s3w_event_buf()'s body
    stmts = [" ".join(s.split()) for s in code.split(";")]
    for i, stmt in enumerate(stmts):
        if "S3W_IMPORT" not in stmt and "S3W_EXPORT" not in stmt:
            if stmt.startswith("__attribute__((weak"):  # the runtime's helper: documented as @internal, not parsed
                if prev_comment is not None:
                    _note(group, prev_comment)
                prev_comment = None
            continue
        name, ret, params, kind = gen.parse_decl(stmt)
        doc = prev_comment if i == 0 else None
        prev_comment = None
        f = Func(name, ret, params, kind, doc, group)
        if f.internal:
            continue
        if group is None:
            problems.append(f"{name}: declared outside a '/* --- Section --- */'")
            continue
        group.funcs.append(f)
    return group, prev_comment


def problems_of(groups, api_level):
    out = []
    seen = set()
    for g in groups:
        for f in g.funcs:
            where = f"{f.name}"
            if f.name in seen:
                out.append(f"{where}: declared twice")
            seen.add(f.name)
            if not f.doc_raw or not f.text:
                out.append(f"{where}: no doc comment directly above it")
            if f.since is None:
                out.append(f"{where}: no @since")
            elif not 1 <= f.since <= api_level:
                out.append(f"{where}: @since {f.since} is outside 1..{api_level}")
            names, _ = f.perm_list()
            for p in names:
                if p not in PERMISSIONS:
                    out.append(f"{where}: unknown permission '{p}' in @perm")
            if f.perm is not None and not names:
                out.append(f"{where}: empty @perm")
            for tag in re.findall(r"@\w+", f.doc_raw or ""):
                if tag not in KNOWN_TAGS:
                    out.append(f"{where}: unknown tag {tag}")
    if not seen:
        out.append("no functions found")
    return out


def api_level_of(text):
    m = re.search(r"^#define\s+S3W_API_LEVEL\s+(\d+)", text, re.M)
    if not m:
        raise SystemExit("gen_api_docs: no S3W_API_LEVEL in the header")
    return int(m.group(1))


# --- Markdown -------------------------------------------------------------------------------------

def link_names(groups):
    return {f.name: g.slug for g in groups for f in g.funcs}


def inline(text, links, page_slug):
    """Prose to Markdown: identifiers in code spans (functions link to their page), other markup escaped."""
    parts = re.split(r"(`[^`]*`)", text)
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(part)
            continue
        pieces = re.split(r"(\bs3w_[a-z0-9_]+\b|\bS3W_[A-Z0-9_]*\*?)", part)
        for j, piece in enumerate(pieces):
            if j % 2 == 0:
                out.append(piece.replace("\\", "\\\\").replace("*", "\\*").replace("<", "&lt;").replace(">", "&gt;"))
            elif piece in links:
                target = f"#{piece}" if links[piece] == page_slug else f"{links[piece]}.md#{piece}"
                out.append(f"[`{piece}`]({target})")
            else:
                out.append(f"`{piece}`")
    return "".join(out)


def paragraphs(text, links, slug):
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    return [inline(" ".join(b.split()), links, slug) for b in blocks]


def perm_md(f):
    names, mode = f.perm_list()
    if not names:
        return None
    joined = (" or " if mode == "any" else " and ").join(f"`{n}`" for n in names)
    return f"permission {joined}"


def group_page(g, links, api_level):
    out = [f"# {g.name}", ""]
    if g.subtitle:
        out += [f"_{g.subtitle[0].upper() + g.subtitle[1:]}_", ""]
    for note in g.notes:
        out += paragraphs(note, links, g.slug)
        out.append("")
    for f in g.funcs:
        out += [f"## {f.name}", "", "```c", f.signature + ";", "```", ""]
        meta = [f"api_level {f.since}" if f.since > 1 else "api_level 1", "callback the app exports" if f.kind == "export" else None,
                perm_md(f)]
        out += ["_" + " · ".join(m for m in meta if m) + "_", ""]
        for para in paragraphs(f.text, links, g.slug):
            out += [para, ""]
    return "\n".join(out).rstrip() + "\n"


def constants_page(text):
    start = text.index("#define S3W_API_LEVEL")
    start = text.rfind("/*", 0, start)
    end = text.index("#if defined(__wasm__)")
    body = text[start:end].rstrip()
    return ("# Constants and types\n\n"
            "Everything the header defines apart from the functions: error codes, events, structs and limits. The header is\n"
            "the reference; this page shows it as written.\n\n```c\n" + body + "\n```\n")


def index_page(groups, api_level):
    out = ["# API reference", "",
           f"The app API of the S3Wear watch, api_level {api_level}. Generated from `include/s3w.h`; every function has the "
           "api_level that added it, and the permission it needs, if any. A manifest's `api_level` must not be higher than "
           "the watch's.", "",
           "| Page | Functions |", "|---|---|"]
    for g in groups:
        out.append(f"| [{g.name}]({g.slug}.md) | {len(g.funcs)} |")
    out += ["| [Constants and types](constants.md) | |", "| [Watch face registry](faces.md) | |", ""]
    perms = {}
    for g in groups:
        for f in g.funcs:
            for p in f.perm_list()[0]:
                perms.setdefault(p, []).append(f.name)
    out += ["## Permissions", "", "A function that needs a permission traps the app when the manifest lacks it.", "",
            "| Permission | Functions |", "|---|---|"]
    for p in sorted(perms):
        out.append(f"| `{p}` | " + ", ".join(f"[`{n}`]({next(g.slug for g in groups for f in g.funcs if f.name == n)}.md#{n})"
                                             for n in perms[p]) + " |")
    out += ["", "## By api_level", "", "| api_level | New functions |", "|---|---|"]
    for level in range(1, api_level + 1):
        names = [f.name for g in groups for f in g.funcs if f.since == level]
        if level == 1:
            out.append(f"| 1 | {len(names)} functions: the original API |")
        else:
            out.append(f"| {level} | " + ", ".join(f"`{n}`" for n in names) + " |")
    return "\n".join(out) + "\n"


DATE_NOTE = """A `date.<pattern>` binding formats the date with a pattern: `EEEE` (Saturday), `EEE` (Sat), `d` (3), `dd` (03),
`MMMM` (October), `MMM` (Oct), `MM` (10), `M` (10), `yyyy` (2026), `yy` (26). Other letters are invalid, anything else is
copied. The names are English."""


def faces_page(reg):
    out = ["# Watch face registry", "",
           f"What a `face.json` (face format api {reg['api']}) can name. Generated from the simulator "
           "(`s3w_sim --list-face-registry`), so it is what the watch accepts.", "",
           "## Bindings", "",
           "An element's `bind` is one of these. _Text_ is the form a text element shows, _value_ the number a gauge or hand "
           "uses. _Updates on_ is the data that makes it redraw.", "",
           "| Binding | Text | Value | Updates on |", "|---|---|---|---|"]
    for b in reg["bindings"]:
        out.append(f"| `{b['name']}` | {'yes' if b['text'] else '—'} | {'yes' if b['value'] else '—'} | "
                   f"{', '.join(b['deps'])} |")
    out += ["", DATE_NOTE, "", "## Fonts", "", "| Name |", "|---|"]
    out += [f"| `{f}` |" for f in reg["fonts"]]
    out += ["", "## Complications", "",
            "A slot's `default` complication, and what a tap on it opens.", "",
            "| Id | Name | Opens | Updates on |", "|---|---|---|---|"]
    for c in reg["complications"]:
        out.append(f"| `{c['id']}` | {c['name']} | {'`' + c['app'] + '`' if c['app'] else '—'} | {', '.join(c['deps'])} |")
    return "\n".join(out) + "\n"


def api_json(groups, api_level):
    return json.dumps({
        "api_level": api_level,
        "groups": [{
            "name": g.name, "slug": g.slug,
            "functions": [{"name": f.name, "kind": f.kind, "signature": f.signature, "since": f.since,
                           "permissions": f.perm_list()[0], "permissions_mode": f.perm_list()[1],
                           "doc": " ".join(f.text.split())} for f in g.funcs]} for g in groups],
    }, indent=2) + "\n"


def generate(header_text, registry):
    """-> ({file name: text}, problems)."""
    api_level = api_level_of(header_text)
    groups, problems = parse_header(header_text)
    problems += problems_of(groups, api_level)
    if problems:
        return {}, problems
    links = link_names(groups)
    files = {"index.md": index_page(groups, api_level), "constants.md": constants_page(header_text),
             "faces.md": faces_page(registry), "api.json": api_json(groups, api_level)}
    for g in groups:
        files[f"{g.slug}.md"] = group_page(g, links, api_level)
    return files, []


def registry_from_sim(sim):
    out = subprocess.run([sim, "--list-face-registry"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def registry_text(reg):
    return json.dumps(reg, indent=1) + "\n"


def main(argv):
    check = "--check" in argv
    sim = argv[argv.index("--sim") + 1] if "--sim" in argv else None
    with open(HEADER) as f:
        header = f.read()
    if sim and not check:
        with open(REGISTRY, "w") as f:
            f.write(registry_text(registry_from_sim(sim)))
    with open(REGISTRY) as f:
        registry = json.load(f)
    files, problems = generate(header, registry)
    if problems:
        sys.exit("gen_api_docs: " + "\n  ".join(["problems in include/s3w.h:"] + problems))
    if check:
        stale = []
        for name, text in files.items():
            path = os.path.join(OUT, name)
            if not os.path.exists(path) or open(path).read() != text:
                stale.append(name)
        extra = [n for n in os.listdir(OUT) if n not in files and n != "face-registry.json"] if os.path.isdir(OUT) else []
        if sim and registry_from_sim(sim) != registry:
            stale.append("face-registry.json (differs from the simulator)")
        if stale or extra:
            sys.exit("gen_api_docs: docs/api is stale (" + ", ".join(stale + [f"{e} is not generated" for e in extra]) +
                     "): run sdk/tools/gen_api_docs.py")
        print(f"docs/api: {len(files)} files fresh")
        return
    os.makedirs(OUT, exist_ok=True)
    for n in os.listdir(OUT):
        if n not in files and n != "face-registry.json":
            os.remove(os.path.join(OUT, n))
    for name, text in files.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(text)
    print(f"wrote {len(files)} files to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
