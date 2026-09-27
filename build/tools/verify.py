"""Check the built WAD for the traps that only show up on a console."""

import hashlib
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))

from hbcud import (BENZIN, DONOR_FORWARDER_WAD, FORWARDER_DOL, IOS, TITLE_ID, WAD_PATH,
                   benzin)
from wiilib import U8, WAD, imet_titles, imet_verify, unpack_lz77_imd5

ICON_CAP = 0x19000      # a bigger icon.bin bricks the Menu after Health & Safety
# Title IDs already used by HBC itself and by the HBC forwarders on MarioCube.
TAKEN = {"LULZ", "OHBC", "JODI", "HAXX", "MAUI", "SUSS", "BHBC", "ZD51", "ZD41",
         "DABA", "DHBC", "NHBC", "FNFA", "GHBC", "KGHB", "HBCJ", "BLEG", "PHBC",
         "POYO", "RHBC", "KHBC", "STWT", "DUFF", "FIXD", "AKFC", "PIRA", "POOL",
         "YHBC", "JBFB"}

failures = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok:
        failures.append(msg)


def main():
    wad = WAD.load(WAD_PATH)
    tmd = wad.tmd
    check(wad.title_id[4:].decode() == TITLE_ID, f"title ID is {TITLE_ID}")
    check(TITLE_ID not in TAKEN, f"{TITLE_ID} doesn't clash with HBC or known forwarders")
    check(len(wad.contents) == 3, "three contents: banner, NAND loader, forwarder")
    check(tmd[0x184:0x18C] == struct.pack(">II", 1, IOS), f"runs on IOS{IOS}")
    check(struct.unpack(">H", tmd[0x1E0:0x1E2])[0] == 1, "boot content is the NAND loader")
    for i, c in enumerate(wad.contents):
        e = 0x1E4 + i * 36
        check(tmd[e + 16:e + 36] == hashlib.sha1(c).digest(), f"content {i} SHA-1 matches TMD")
    check(hashlib.sha1(wad.tmd[0x140:]).digest()[0] == 0, "TMD fakesigned")
    check(tmd[0x19A:0x19C] == bytes(2), "TMD 0x19A left zero")
    check(hashlib.sha1(wad.tik[0x140:]).digest()[0] == 0, "ticket fakesigned")
    check(wad.contents[1] == WAD.load(DONOR_FORWARDER_WAD).contents[1],
          "NAND loader untouched from the donor")
    check(wad.contents[2] == open(FORWARDER_DOL, "rb").read(), "forwarder is our DOL")

    app = wad.contents[0]
    check(app[:0x40] == WAD.load(DONOR_FORWARDER_WAD).contents[0][:0x40],
          "build tag matches the community forwarder's")
    check(imet_verify(app), "IMET MD5 valid")
    off = app.find(b"IMET")
    sizes = struct.unpack(">III", app[off + 0x0C:off + 0x18])
    meta = U8.load(app[app.find(b"\x55\xAA\x38\x2D"):])
    for i, kind in enumerate(("icon", "banner")):
        u8 = unpack_lz77_imd5(meta.get(f"meta/{kind}.bin"))
        check(sizes[i] == len(u8), f"IMET {kind} size matches ({len(u8):,})")
        check(not U8.load(u8).check_tree(), f"{kind} U8 tree sound")
        if kind == "icon":
            check(len(u8) <= ICON_CAP, f"icon.bin {len(u8):,} <= {ICON_CAP:,}")
        arc = U8.load(u8)
        open(f"{BENZIN}/vfy_{kind}.brlyt", "wb").write(arc.get(f"/arc/blyt/{kind}.brlyt"))
        benzin("r", f"vfy_{kind}.brlyt", f"vfy_{kind}.xmlyt")
        rots = re.findall(r'<tag type="\w+" name="(background|water|title|boom)"[^>]*>'
                          r'.*?<rotate>.*?<z>([-\d.]+)</z>',
                          open(f"{BENZIN}/vfy_{kind}.xmlyt").read(), re.S)
        check(rots and all(abs(float(z) - 180) < 1e-3 for _, z in rots),
              f"{kind}: {', '.join(n for n, _ in rots)} turned 180")
    check(sizes[2] == len(meta.get("meta/sound.bin")) - 32, "IMET sound size matches")
    check(all(imet_titles(app)[1][i] for i in (0, 1, 9)), "channel names present")

    print(f"\n  {'all checks passed' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
