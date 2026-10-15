#!/usr/bin/env bash
# Copies include/, templates/ and rust/ into s3w_cli/_sdk/ so a wheel built from cli/ carries them
# (project.py finds them there after `pipx install s3w`). Run from the SDK repo before building:
#   cli/vendor_sdk.sh && (cd cli && python3 -m build)
set -euo pipefail
cli="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$cli/.."
dest="$cli/s3w_cli/_sdk"
rm -rf "$dest"; mkdir -p "$dest"
for d in include templates rust; do cp -R "$root/$d" "$dest/$d"; done
find "$dest" \( -name target -o -name build -o -name __pycache__ \) -prune -exec rm -rf {} +
echo "vendored SDK into $dest"
