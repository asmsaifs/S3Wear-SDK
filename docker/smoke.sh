#!/usr/bin/env bash
# Checks the dev container: every example and template builds, and (with the simulator in the image) every app and
# template app starts in the simulator and gives a screenshot. Run inside the image with the repository mounted:
#
#   docker run --rm -v "$PWD:/work:ro" -v "$PWD/shots:/shots" s3w-sdk /work/docker/smoke.sh /shots
#
# Argument: the directory for the screenshots (default /tmp/shots). REQUIRE_SIM=1 fails when the image has no
# simulator instead of skipping the run-sim steps.
set -euo pipefail
src="${S3W_SMOKE_SRC:-/work}"
shots="${1:-/tmp/shots}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$shots"
cp -a "$src/." "$work/repo"   # build in a copy: the mounted checkout stays untouched
cd "$work/repo"

s3w --help >/dev/null
have_sim=1
if s3w sim list | grep -q '^none'; then
    have_sim=0
    if [ "${REQUIRE_SIM:-0}" = 1 ]; then echo "smoke: no simulator in the image" >&2; exit 1; fi
    echo "smoke: no simulator in the image, run-sim steps skipped"
fi

echo "== raw examples (examples/build.sh)"
examples/build.sh

shot() {  # <app dir> <name>
    if [ "$have_sim" = 1 ]; then
        s3w run-sim "$1" --screenshot "$shots/$2.png"
        test -s "$shots/$2.png"
        echo "   screenshot $2.png"
    fi
}

echo "== sample apps"
for d in examples/apps/*/; do
    [ -f "$d/manifest.json" ] || continue
    name="$(basename "$d")"
    echo "-- $name"
    s3w build "$d"
    shot "$d" "app-$name"
done

echo "== templates"
for lang in c rust; do
    echo "-- $lang"
    s3w new "$work/tpl-$lang" --lang "$lang"
    s3w build "$work/tpl-$lang"
    shot "$work/tpl-$lang" "template-$lang"
done
echo "smoke: ok"
