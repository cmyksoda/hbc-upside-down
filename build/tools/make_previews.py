"""README previews in preview/: icon GIFs and banner stills. banner_intro.gif is cut
from a Dolphin recording of the real Wii Menu instead."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image

import render as R
from hbcud import MENU_STRIP_Y, OUT, ROOT

PREVIEW = os.path.join(ROOT, "preview")
STRIP = (255, 255, 255)
# 16:9 shows 810.67 x 456 layout units; render that and stretch to the export size.
VIEWS = {"4_3": ((608, 456), (128, 96), (608, 456), (384, 288)),
         "16_9": ((811, 456), (171, 96), (832, 456), (528, 288))}


def menu_view(img):
    """Blank out the part of the banner the Menu's button strip hides."""
    cut = round(img.height / 2 - MENU_STRIP_Y)
    img.paste(STRIP, (0, cut, img.width, img.height))
    return img


def gif(frames, path, step):
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=round(1000 * step / 60), loop=0, optimize=True)
    print(f"  {os.path.relpath(path, ROOT)}: {os.path.getsize(path) // 1024} KiB")


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    _, bp, bm, bt, ba = R.load(f"{OUT}/banner.bin")
    _, ip, im, it, ia = R.load(f"{OUT}/icon.bin")
    loop, size = ba["banner_Loop"]
    icon, isize = ia["icon"]

    for name, (bcanvas, icanvas, bout, iout) in VIEWS.items():
        still = R.render_frame(bp, bm, bt, loop, size // 2, bcanvas).resize(bout, Image.LANCZOS)
        menu_view(still).save(f"{PREVIEW}/banner_{name}.png")
        print(f"  preview/banner_{name}.png")
        step = 6
        frames = [R.render_frame(ip, im, it, icon, f, icanvas).resize(iout, Image.NEAREST)
                  for f in range(0, isize, step)]
        gif(frames, f"{PREVIEW}/icon_{name}.gif", step)


if __name__ == "__main__":
    main()
