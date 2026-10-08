"""Pack the flipped banner and the forwarder into a forwarder WAD."""

import argparse
import hashlib
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from hbcud import DONOR_FORWARDER_WAD, FORWARDER_DOL, IOS, OUT, TITLE_ID, WAD_NAME, WAD_PATH
from hbcud import VWII_LOADER, VWII_LOADER_SHA256, VWII_WAD_PATH, WII_LOADER_SHA256, WII_WAD_PATH
from wiilib import WAD


def build_platform(platform, base_path=WAD_PATH, forwarder_path=FORWARDER_DOL,
                   loader_path=VWII_LOADER, output_path=None):
    """Keep the released banner and metadata, choosing the loader for each console."""
    if platform not in ("wii", "vwii"):
        raise ValueError("platform must be wii or vwii")
    if output_path is None:
        output_path = VWII_WAD_PATH if platform == "vwii" else WII_WAD_PATH
    if Path(output_path).resolve() == Path(base_path).resolve():
        raise ValueError("output must not overwrite the original Wii WAD")
    wad = WAD.load(base_path)
    if wad.title_id != bytes.fromhex("00010001") + TITLE_ID.encode("ascii"):
        raise ValueError("base WAD must be the UHBC channel")
    if wad.tik[0x1DC:0x1E4] != wad.title_id:
        raise ValueError("base ticket and TMD title IDs differ")
    if len(wad.contents) != 3 or struct.unpack_from(">H", wad.tmd, 0x1E0)[0] != 1:
        raise ValueError("expected three contents with NAND loader at boot index 1")
    if wad.tmd[0x184:0x18C] != struct.pack(">II", 1, IOS):
        raise ValueError("base WAD must already use IOS58")
    for i, content in enumerate(wad.contents):
        entry = 0x1E4 + i * 36
        if struct.unpack_from(">IH", wad.tmd, entry) != (i, i):
            raise ValueError("expected content IDs and indices 0, 1, 2 in order")
        if hashlib.sha1(content).digest() != wad.tmd[entry + 16:entry + 36]:
            raise ValueError(f"base content {i} SHA-1 mismatch")

    if platform == "vwii":
        loader = Path(loader_path).read_bytes()
        if hashlib.sha256(loader).hexdigest() != VWII_LOADER_SHA256:
            raise ValueError("vWii loader must be the unmodified FIX94 r2 00000001.app")
        wad.contents[1] = loader
    elif hashlib.sha256(wad.contents[1]).hexdigest() != WII_LOADER_SHA256:
        raise ValueError("Wii loader must match the original Wii release")
    wad.contents[2] = Path(forwarder_path).read_bytes()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    return wad.save(output_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument("--vwii", action="store_true",
                         help="reuse the released banner with FIX94's vWii NAND loader")
    targets.add_argument("--wii", action="store_true",
                         help="reuse the released banner with the original Wii NAND loader")
    args = parser.parse_args()
    if args.vwii or args.wii:
        size = build_platform("vwii" if args.vwii else "wii")
        path = VWII_WAD_PATH if args.vwii else WII_WAD_PATH
        print(f"  {path}: {size:,} bytes")
        return
    for p in (DONOR_FORWARDER_WAD, FORWARDER_DOL):
        assert os.path.exists(p), f"missing {p}"
    wad = WAD.load(DONOR_FORWARDER_WAD)
    assert len(wad.contents) == 3, "expected banner, NAND loader, forwarder DOL"
    wad.contents[0] = open(f"{OUT}/00000000.app", "rb").read()
    wad.contents[2] = open(FORWARDER_DOL, "rb").read()
    wad.set_title_id(TITLE_ID)
    tmd = bytearray(wad.tmd)
    tmd[0x184:0x18C] = struct.pack(">II", 1, IOS)
    # The donor's reserved fields hold its old fakesign bytes; clear them, and grant the
    # access rights HBC's own TMD has.
    tmd[0x1AE:0x1BA] = bytes(12)
    tmd[0x1C6:0x1D8] = bytes(18)
    tmd[0x1D8:0x1DC] = struct.pack(">I", 3)
    wad.tmd = bytes(tmd)
    size = wad.save(WAD_PATH)
    print(f"  {WAD_NAME}: {size:,} bytes")


if __name__ == "__main__":
    main()
