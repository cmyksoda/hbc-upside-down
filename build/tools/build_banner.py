"""Turn the Homebrew Channel's banner and icon upside down.

Each child of RootPane spins 180 degrees about the origin, since the Menu owns
RootPane itself. The banner also shifts so the flip centres on what the Menu shows.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from hbcud import BANNER_SHIFT_Y, BENZIN, DONOR_HBC_WAD, ICON_SHIFT_Y, OUT, benzin
from wiilib import U8, WAD, imet_set, pack_lz77_imd5, unpack_lz77_imd5

FLOAT = r"[-\d.eE+]+"
PANE = r'<tag type="(\w+)"((?:[^>]*[^/>])?)(?:>(.*?)</tag>|\s*/>)'


def root_children(xml):
    """Names of the panes sitting directly under RootPane."""
    depth, names = 0, []
    for m in re.finditer(PANE, xml, re.S):
        kind = m.group(1)
        if kind == "pas1":
            depth += 1
        elif kind == "pae1":
            depth -= 1
        elif depth == 1 and kind in ("pan1", "pic1", "txt1", "wnd1", "bnd1"):
            names.append(re.search(r'name="([^"]*)"', m.group(2)).group(1))
    return names


def flip_layout(xml, shift, grow):
    """Spin each root child; `grow` names panes to lengthen so the shift can't
    open a gap at the far edge."""
    names = root_children(xml)

    def edit(m):
        name = re.search(r'name="([^"]*)"', m.group(2) or "")
        if m.group(3) is None or not name or name.group(1) not in names:
            return m.group(0)
        body = m.group(3)
        body = re.sub(rf"(<translate>\s*<x>)({FLOAT})(</x>\s*<y>)({FLOAT})(</y>)",
                      lambda t: f"{t[1]}{-float(t[2]):.6f}{t[3]}{shift - float(t[4]):.6f}{t[5]}",
                      body, count=1)
        body = re.sub(rf"(<rotate>.*?<z>)({FLOAT})(</z>)",
                      lambda t: f"{t[1]}{float(t[2]) + 180:.6f}{t[3]}", body, count=1, flags=re.S)
        if name.group(1) in grow:
            body = re.sub(rf"(<height>)({FLOAT})(</height>)",
                          lambda t: f"{t[1]}{float(t[2]) + 2 * abs(shift):.6f}{t[3]}",
                          body, count=1)
        return m.group(0).replace(m.group(3), body)

    return re.sub(PANE, edit, xml, flags=re.S), names


def flip_anim(xml, names, shift):
    def keys(body, fn):
        def one(k):
            v, b = (x + 0.0 for x in fn(float(k[1]), float(k[3])))  # no -0.0
            return f"<value>{v:.6f}</value>{k[2]}<blend>{b:.6f}</blend>"
        return re.sub(rf"<value>({FLOAT})</value>(\s*)<blend>({FLOAT})</blend>", one, body)

    maps = {"X Translation": lambda v, b: (-v, -b),
            "Y Translation": lambda v, b: (shift - v, -b),
            "Z Rotate": lambda v, b: (v + 180, b)}

    def pane(m):
        if m.group(1) not in names:
            return m.group(0)
        return re.sub(r'(<entry type1="\d+" type2="([^"]+)">)(.*?)(</entry>)',
                      lambda e: e[1] + (keys(e[3], maps[e[2]]) if e[2] in maps else e[3])
                      + e[4], m.group(0), flags=re.S)

    return re.sub(r'<pane name="([^"]+)" type="0">.*?</pane>', pane, xml, flags=re.S)


def flip_archive(raw, kind, shift, grow):
    arc = U8.load(unpack_lz77_imd5(raw))
    open(f"{BENZIN}/src_{kind}.brlyt", "wb").write(arc.get(f"/arc/blyt/{kind}.brlyt"))
    benzin("r", f"src_{kind}.brlyt", f"src_{kind}.xmlyt")
    lyt, names = flip_layout(open(f"{BENZIN}/src_{kind}.xmlyt").read(), shift, grow)
    open(f"{BENZIN}/new_{kind}.xmlyt", "w").write(lyt)
    benzin("m", f"new_{kind}.xmlyt", f"new_{kind}.brlyt")
    arc.replace(f"/arc/blyt/{kind}.brlyt", open(f"{BENZIN}/new_{kind}.brlyt", "rb").read())
    for _, path in list(arc.paths()):
        if not path.endswith(".brlan"):
            continue
        stem = os.path.basename(path)[:-6]
        open(f"{BENZIN}/src_{stem}.brlan", "wb").write(arc.get(path))
        benzin("r", f"src_{stem}.brlan", f"src_{stem}.xmlan")
        an = flip_anim(open(f"{BENZIN}/src_{stem}.xmlan").read(), names, shift)
        open(f"{BENZIN}/new_{stem}.xmlan", "w").write(an)
        benzin("m", f"new_{stem}.xmlan", f"new_{stem}.brlan")
        arc.replace(path, open(f"{BENZIN}/new_{stem}.brlan", "rb").read())
    u8 = arc.to_bytes()
    print(f"  {kind}: spun {', '.join(names)} (shift {shift:+g}); {len(u8):,} bytes")
    return u8


def main():
    assert os.path.exists(DONOR_HBC_WAD), f"missing {DONOR_HBC_WAD}"
    app = WAD.load(DONOR_HBC_WAD).contents[0]
    cut = app.find(b"\x55\xAA\x38\x2D")
    meta = U8.load(app[cut:])
    sizes = {}
    for kind, shift in (("icon", ICON_SHIFT_Y), ("banner", BANNER_SHIFT_Y)):
        # The white backdrop has to reach the far edge once shifted.
        u8 = flip_archive(meta.get(f"meta/{kind}.bin"), kind, shift, {"background"})
        meta.replace(f"meta/{kind}.bin", pack_lz77_imd5(u8))
        sizes[kind] = len(u8)
    sizes["sound"] = len(meta.get("meta/sound.bin")) - 32
    out = imet_set(app[:cut] + meta.to_bytes(), None,
                   (sizes["icon"], sizes["banner"], sizes["sound"]))
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/00000000.app", "wb").write(out)
    for kind in ("icon", "banner"):
        open(f"{OUT}/{kind}.bin", "wb").write(meta.get(f"meta/{kind}.bin"))
    print(f"  banner app: {len(out):,} bytes")


if __name__ == "__main__":
    main()
