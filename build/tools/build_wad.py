"""Pack the flipped banner and the forwarder into a forwarder WAD."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from hbcud import DONOR_FORWARDER_WAD, FORWARDER_DOL, OUT, TITLE_ID, WAD_NAME
from wiilib import WAD


def main():
    for p in (DONOR_FORWARDER_WAD, FORWARDER_DOL):
        assert os.path.exists(p), f"missing {p}"
    wad = WAD.load(DONOR_FORWARDER_WAD)
    assert len(wad.contents) == 3, "expected banner, NAND loader, forwarder DOL"
    wad.contents[0] = open(f"{OUT}/00000000.app", "rb").read()
    wad.contents[2] = open(FORWARDER_DOL, "rb").read()
    wad.set_title_id(TITLE_ID)
    size = wad.save(f"{OUT}/{WAD_NAME}")
    print(f"  {WAD_NAME}: {size:,} bytes")


if __name__ == "__main__":
    main()
