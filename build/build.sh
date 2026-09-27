#!/usr/bin/env bash
# Builds build/out/<WAD_NAME>. Pass --previews to also render preview/ and an MP4.
set -euo pipefail
cd "$(dirname "$0")/.."

export DEVKITPRO="${DEVKITPRO:-/opt/devkitpro}"
export DEVKITPPC="${DEVKITPPC:-$DEVKITPRO/devkitPPC}"
PY=build/.venv/bin/python

if [ ! -x "$PY" ]; then
    python3 -m venv build/.venv
    "$PY" -m pip install -q pillow pycryptodome numpy
fi

echo "== forwarder"
make -C forwarder --no-print-directory
echo "== banner"
"$PY" build/tools/build_banner.py
echo "== wad"
"$PY" build/tools/build_wad.py
echo "== verify"
"$PY" build/tools/verify.py

if [ "${1:-}" = "--previews" ]; then
    echo "== previews"
    "$PY" build/tools/make_previews.py
    "$PY" build/tools/make_video.py
fi
