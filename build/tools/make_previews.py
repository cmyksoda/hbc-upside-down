"""README previews: icon GIFs, banner stills and the flipped intro, in preview/."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image

import render as R
from hbcud import DONOR_HBC_WAD, MENU_STRIP_Y, OUT, ROOT
from wiilib import U8, WAD

PREVIEW = os.path.join(ROOT, "preview")
STRIP = (214, 214, 218)
# 16:9 shows 810.67 x 456 layout units; render that and stretch to the export size.
VIEWS = {"4_3": ((608, 456), (128, 96), (608, 456), (384, 288)),
         "16_9": ((811, 456), (171, 96), (832, 456), (528, 288))}


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
    frames = [menu_view(R.render_frame(bp, bm, bt, start, f, (811, 456))
                        .resize((832, 456), Image.LANCZOS)).resize((416, 228), Image.LANCZOS)
              for f in range(0, ssize, step)]
    gif(frames, f"{PREVIEW}/banner_intro.gif", step)

    # Before and after, the stock banner rendered from the untouched donor.
    app = WAD.load(DONOR_HBC_WAD).contents[0]
    meta = U8.load(app[app.find(b"\x55\xAA\x38\x2D"):])
    open(f"{OUT}/stock_banner.bin", "wb").write(meta.get("meta/banner.bin"))
    _, sp, sm, st, sa = R.load(f"{OUT}/stock_banner.bin")
    sloop, _ = sa["banner_Loop"]
    pair = [menu_view(R.render_frame(*args, size // 2, (608, 456)))
            for args in ((sp, sm, st, sloop), (bp, bm, bt, loop))]
    both = Image.new("RGBA", (608 * 2 + 16, 456), (0, 0, 0, 0))
    both.paste(pair[0], (0, 0))
    both.paste(pair[1], (608 + 16, 0))
    both.save(f"{PREVIEW}/before_after.png")
    print("  preview/before_after.png")


if __name__ == "__main__":
    main()
