#!/usr/bin/env python3
"""Generates src/lib.rs (raw Rust bindings) from sdk/include/s3w.h, the single source of truth.

  gen.py           rewrite src/lib.rs
  gen.py --check   exit 1 if src/lib.rs is stale (the s3w CLI tests run this)

The header is written in a fixed style (one declaration per statement, S3W_IMPORT(name) on every
imported function), which is all this parser understands; it fails loudly on anything else in
the imported section.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HEADER = os.path.normpath(os.path.join(HERE, "..", "..", "include", "s3w.h"))
OUT = os.path.join(HERE, "src", "lib.rs")

SCALARS = {
    "int": "i32",
    "int32_t": "i32",
    "uint32_t": "u32",
    "int64_t": "i64",
    "uint16_t": "u16",
    "int16_t": "i16",
    "uint8_t": "u8",
    "bool": "bool",
    "float": "f32",
    "char": "u8",
    "void": "core::ffi::c_void",
}
RUST_KEYWORDS = {"type", "fn", "mod", "ref", "move", "loop", "match", "self", "box"}


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def rust_type(ctype, structs):
    """A C type ("const char *", "uint16_t", "s3w_tm_t *") to Rust."""
    t = ctype.strip()
    ptr = t.count("*")
    t = t.replace("*", " ").split()
    const = "const" in t
    t = [w for w in t if w != "const"]
    if len(t) != 1:
        raise SystemExit(f"gen.py: cannot map C type '{ctype}'")
    base = t[0]
    if base in SCALARS:
        r = SCALARS[base]
    elif base in structs:
        r = base
    else:
        raise SystemExit(f"gen.py: unknown C type '{base}'")
    if ptr == 0:
        if r == "core::ffi::c_void":
            return None  # void return
        return r
    if ptr > 1:
        raise SystemExit(f"gen.py: pointer to pointer in '{ctype}'")
    return ("*const " if const else "*mut ") + r


def field_name(name):
    return f"r#{name}" if name in RUST_KEYWORDS else name


def parse_decl(stmt):
    """One whitespace-normalised declaration ending in S3W_IMPORT(name) or S3W_EXPORT(name) ->
    (name, return type, [(param name, C type)], "import" | "export"). Shared with sdk/tools/gen_api_docs.py."""
    fm = re.match(r"^(.*?)\b(s3w_\w+)\s*\((.*)\)\s*S3W_(IMPORT|EXPORT)\((\w+)\)$", stmt)
    if not fm or fm.group(2) != fm.group(5):
        raise SystemExit(f"gen.py: cannot parse '{stmt}'")
    params = []
    if fm.group(3).strip() != "void":
        for p in fm.group(3).split(","):
            pm = re.match(r"^(.*?)(\w+)$", p.strip())
            params.append((pm.group(2), pm.group(1)))
    return fm.group(2), fm.group(1), params, fm.group(4).lower()


def parse(text):
    src = strip_comments(text)
    consts = []  # (name, value)
    for m in re.finditer(r"^\s*#define\s+(S3W_\w+)\s+\(?\s*(-?(?:0x[0-9A-Fa-f]+|\d+))\s*\)?\s*$", src, re.M):
        consts.append((m.group(1), int(m.group(2), 0)))
    for m in re.finditer(r"#define\s+(S3W_\w+)\s+\(\s*(\d+)\s*\*\s*(\d+)\s*\)", src):
        consts.append((m.group(1), int(m.group(2)) * int(m.group(3))))
    for m in re.finditer(r"\benum\s*\{(.*?)\}\s*;", src, re.S):
        value = -1
        for item in m.group(1).split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                name, v = (x.strip() for x in item.split("=", 1))
                value = int(v, 0)
            else:
                name, value = item, value + 1
            consts.append((name, value))
    structs = {}
    order = []
    for m in re.finditer(r"typedef\s+struct\s*\{(.*?)\}\s*(\w+)\s*;", src, re.S):
        fields = []
        for decl in m.group(1).split(";"):
            decl = decl.strip()
            if not decl:
                continue
            dm = re.match(r"((?:const\s+)?\w+)\s+(.*)$", decl, re.S)
            base, names = dm.group(1), dm.group(2)
            for n in names.split(","):
                n = n.strip()
                ptr = n.count("*")
                n = n.replace("*", "").strip()
                arr = re.match(r"(\w+)\[(\d+)\]$", n)
                if arr:
                    fields.append((arr.group(1), base + " " + "*" * ptr, int(arr.group(2))))
                else:
                    fields.append((n, base + " " + "*" * ptr, 0))
        structs[m.group(2)] = fields
        order.append(m.group(2))
    wasm = src.split("#if defined(__wasm__)", 1)[1].split("#endif", 1)[0]
    wasm = re.sub(r"^\s*#.*$", " ", wasm, flags=re.M)  # the import/export macros
    wasm = re.sub(r"\{[^{}]*\}", ";", wasm)  # s3w_event_buf()'s body (an export, not an import)
    funcs = []
    for stmt in wasm.split(";"):
        stmt = " ".join(stmt.split())
        if "S3W_IMPORT" not in stmt:
            continue
        name, ret, params, _ = parse_decl(stmt)
        funcs.append((name, ret, params))
    return consts, structs, order, funcs


def generate():
    with open(HEADER) as f:
        consts, structs, order, funcs = parse(f.read())
    out = [
        "//! Raw bindings to the S3Wear app API (`sdk/include/s3w.h`, api_level 1): every import of the",
        '//! "s3w" module, the constants and the `#[repr(C)]` structs. Generated by `gen.py`: do not edit.',
        "//! Use the safe `s3w` crate (`sdk/rust/s3w`) in apps.",
        "#![no_std]",
        "#![allow(non_camel_case_types, non_upper_case_globals, clippy::missing_safety_doc)]",
        "",
    ]
    for name, value in consts:
        out.append(f"pub const {name}: i32 = {value};")
    out.append("")
    for name in order:
        fields = structs[name]
        has_ptr = any("*" in t for _, t, _ in fields)
        big_array = any(count and int(count) > 32 for _, _, count in fields)  # Default stops at 32 elements
        derive = "Clone, Copy, Debug" if has_ptr or big_array else "Clone, Copy, Debug, Default"
        out.append("#[repr(C)]")
        out.append(f"#[derive({derive})]")
        out.append(f"pub struct {name} {{")
        for fname, ftype, count in fields:
            rt = rust_type(ftype, structs)
            out.append(f"    pub {field_name(fname)}: {f'[{rt}; {count}]' if count else rt},")
        out.append("}")
        out.append("")
    out.append('#[link(wasm_import_module = "s3w")]')
    out.append('extern "C" {')
    for name, ret, params in funcs:
        args = ", ".join(f"{field_name(p)}: {rust_type(t, structs)}" for p, t in params)
        r = rust_type(ret, structs)
        out.append(f"    pub fn {name}({args}){f' -> {r}' if r else ''};")
    out.append("}")
    return "\n".join(out) + "\n"


def main():
    text = generate()
    if "--check" in sys.argv[1:]:
        with open(OUT) as f:
            if f.read() != text:
                sys.exit("sdk/rust/s3w-sys/src/lib.rs is stale: run sdk/rust/s3w-sys/gen.py")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(text)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
