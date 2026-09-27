"""README previews: icon GIFs, banner stills and the flipped intro, in preview/."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image

import render as R
from hbcud import MENU_STRIP_Y, OUT, ROOT

PREVIEW = os.path.join(ROOT, "preview")
STRIP = (214, 214, 218)
# 16:9 shows 810.67 x 456 layout units; render that and stretch to the export size.
VIEWS = {"4_3": ((608, 456), (128, 96), (608, 456), (384, 288)),
         "16_9": ((811, 456), (171, 96), (832, 456), (528, 288))}


# The Wii Menu's own button strip, cropped from a 16:9 Dolphin capture (836x456).
REAL_STRIP = os.path.join(os.path.dirname(__file__), "assets", "menu_strip_16_9.png")
REAL_STRIP_TOP = 339


def real_strip(img):
    img.paste(Image.open(REAL_STRIP).convert("RGB"), (0, REAL_STRIP_TOP))
    return img


def menu_view(img):
    """Paint the Menu's button strip over the part of the banner it hides."""
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

    start, ssize = ba["banner_Start"]
    step = 4
    frames = [real_strip(R.render_frame(bp, bm, bt, start, f, (811, 456))
                         .resize((836, 456), Image.LANCZOS)).resize((418, 228), Image.LANCZOS)
              for f in range(0, ssize, step)]
    gif(frames, f"{PREVIEW}/banner_intro.gif", step)


if __name__ == "__main__":
    main()
