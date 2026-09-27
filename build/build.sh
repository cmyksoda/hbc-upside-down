#!/usr/bin/env bash
# Builds build/out/<WAD_NAME>. Pass --previews to also render GIFs (a few minutes).
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
    mkdir -p build/out/preview
    "$PY" build/tools/render.py build/out/banner.bin build/out/preview/banner
    "$PY" build/tools/render.py build/out/icon.bin build/out/preview/icon
fi
