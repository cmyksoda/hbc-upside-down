"""Pack the flipped banner and the forwarder into a forwarder WAD."""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))

from hbcud import DONOR_FORWARDER_WAD, FORWARDER_DOL, IOS, OUT, TITLE_ID, WAD_NAME, WAD_PATH
from wiilib import WAD


def main():
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
