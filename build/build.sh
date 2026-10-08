#!/usr/bin/env bash
# Pass --release for both platform ZIPs, or --previews to regenerate Wii banner previews.
set -euo pipefail
cd "$(dirname "$0")/.."

export DEVKITPRO="${DEVKITPRO:-/opt/devkitpro}"
export DEVKITPPC="${DEVKITPPC:-$DEVKITPRO/devkitPPC}"
PY=build/.venv/bin/python

case "${1:-}" in
    ""|--previews|--wii|--vwii|--release) ;;
    *) echo "usage: $0 [--wii|--vwii|--release|--previews]" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
    echo "usage: $0 [--wii|--vwii|--release|--previews]" >&2
    exit 2
fi

if [ ! -x "$PY" ]; then
    python3 -m venv build/.venv
fi
if [[ "${1:-}" = --wii || "${1:-}" = --vwii || "${1:-}" = --release ]]; then
    "$PY" -c 'import Crypto' 2>/dev/null || "$PY" -m pip install -q pycryptodome
else
    "$PY" -c 'import PIL, Crypto, numpy' 2>/dev/null || \
        "$PY" -m pip install -q pillow pycryptodome numpy
fi

echo "== forwarder"
make -C forwarder --no-print-directory
if [ "${1:-}" = "--release" ]; then
    "$PY" build/tools/package_release.py
    exit
fi
if [[ "${1:-}" = --wii || "${1:-}" = --vwii ]]; then
    "$PY" build/tools/build_wad.py "$1"
    "$PY" build/tools/verify.py "$1"
    exit
fi
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
