#!/usr/bin/env bash
# Builds the SDK examples to freestanding wasm32 (no libc) with any clang that has the wasm32
# target and wasm-ld (LLVM >= 16; e.g. Homebrew llvm, or wasi-sdk's clang). The `s3w` CLI
# replaces this in P8-06. The .wasm files are committed: the firmware embeds widgets.wasm and the
# simulator's snapshot tests run it, so neither needs a wasm toolchain.
#
#   sdk/examples/build.sh [example...]      default: all; CLANG=/path/to/clang to choose one
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sdk="$(dirname "$here")"

find_clang() {
    if [[ -n "${CLANG:-}" ]]; then echo "$CLANG"; return; fi
    for c in /opt/homebrew/opt/llvm/bin/clang /opt/homebrew/opt/llvm@*/bin/clang /usr/local/opt/llvm/bin/clang \
             /opt/wasi-sdk/bin/clang clang; do
        if command -v "$c" >/dev/null 2>&1 && "$c" --print-targets 2>/dev/null | grep -q wasm32; then
            echo "$c"; return
        fi
    done
    echo "no clang with the wasm32 target found; set CLANG" >&2
    exit 1
}
cc="$(find_clang)"

examples=("$@")
if [[ ${#examples[@]} -eq 0 ]]; then
    for d in "$here"/*/; do
        # only folders with C sources (examples/apps/ holds sample apps built with the s3w CLI)
        compgen -G "$d*.c" >/dev/null && examples+=("$(basename "$d")")
    done
fi
for ex in "${examples[@]}"; do
    out="$here/$ex/$ex.wasm"
    # 1 page (64 KB) of memory with an 8 KB stack; exports come from S3W_EXPORT in s3w.h.
    "$cc" --target=wasm32 -Oz -ffreestanding -nostdlib -fno-builtin -Wall -Wextra -Werror \
        -I "$sdk/include" "$here/$ex"/*.c -o "$out" \
        -Wl,--no-entry -Wl,--strip-all -Wl,--initial-memory=65536 -Wl,--max-memory=65536 \
        -Wl,-z,stack-size=8192
    echo "built $out ($(wc -c <"$out" | tr -d ' ') bytes)"
done
