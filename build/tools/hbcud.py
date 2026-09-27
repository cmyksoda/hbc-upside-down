"""Every knob for the Upside-Down HBC channel, plus the shared helpers."""

import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOOLS = os.path.join(ROOT, "build", "tools")
BENZIN = os.path.join(TOOLS, "benzin")
OUT = os.path.join(ROOT, "build", "out")

# Any official Homebrew Channel WAD; every 1.1.x release carries the same banner.
DONOR_HBC_WAD = os.path.join(ROOT, "donor", "hbc1.1.4-unpatched.wad")
# Any HBC forwarder WAD built the usual way (banner, NAND loader, forwarder DOL).
# Only its certs, ticket, TMD and NAND loader are kept.
DONOR_FORWARDER_WAD = os.path.join(ROOT, "donor", "Pink HBC - PHBC.wad")
FORWARDER_DOL = os.path.join(ROOT, "forwarder", "forwarder.dol")

# The Menu's "Wii Menu"/"Start" strip covers the banner below this pane y.
MENU_STRIP_Y = -118

# The flip is a 180-degree spin, not a mirror: the concept art's "homebrew" reads
# right to left. The banner then moves up so the flip is centred on the part the
# Menu leaves visible (+228 down to MENU_STRIP_Y); the icon has no strip.
BANNER_SHIFT_Y = 228 + MENU_STRIP_Y
ICON_SHIFT_Y = 0

TITLE_ID = "UHBC"
# IOS58 is what HBC itself and current forwarders use; the donor asks for IOS61.
IOS = 58
WAD_NAME = "Homebrew Channel Upside Down - UHBC [cmyksoda].wad"
WAD_PATH = os.path.join(ROOT, WAD_NAME)

BANNER_CANVAS = (832, 456)     # 16:9 shows 4/3 more width than 4:3
BANNER_43 = (608, 456)
ICON_CANVAS = (176, 96)
ICON_43 = (128, 96)


def benzin(*args):
    """Run Benzin under wine. 'r' rips a binary to XML, 'm' makes it back."""
    r = subprocess.run(["wine", "BENZIN.EXE", *args], cwd=BENZIN,
                       capture_output=True, env={**os.environ, "WINEDEBUG": "-all"})
    out = (r.stdout + r.stderr).decode(errors="replace")
    if "Couldn't" in out or r.returncode != 0:
        raise RuntimeError(f"benzin {args}: {out}")
    return out
