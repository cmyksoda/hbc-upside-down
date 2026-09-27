"""Render a banner.bin / icon.bin frame by frame, with full pane matrices and
texture SRT, so a rotated layout previews the way the Menu draws it.

    render.py <banner.bin|icon.bin> <out_prefix>
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from PIL import Image, ImageDraw

import tpl as T
from hbcud import (BANNER_43, BANNER_CANVAS, BENZIN, ICON_43, ICON_CANVAS,
                   MENU_STRIP_Y, benzin)
from wiilib import U8, unpack_lz77_imd5

TAGBLOCK = r'<tag type="(\w+)"((?:[^>]*[^/>])?)>(.*?)</tag>'
CHANNELS = {"X Translation": "tx", "Y Translation": "ty", "Z Rotate": "rz",
            "X Scale": "sx", "Y Scale": "sy"}
FLOAT = r"([-\d.eE+]+)"


def hermite(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for (f0, v0, m0), (f1, v1, m1) in zip(keys, keys[1:]):
        if f0 <= t <= f1:
            h = f1 - f0
            if h == 0:
                return v1
            s = (t - f0) / h
            return (v0 * (2*s**3 - 3*s**2 + 1) + v1 * (-2*s**3 + 3*s**2)
                    + h * m0 * (s**3 - 2*s**2 + s) + h * m1 * (s**3 - s**2))
    return keys[-1][1]


# ------------------------------------------------------------------ parsing

def parse_anim(xml):
    out = {}
    for m in re.finditer(r'<pane name="([^"]+)" type="(\d)">(.*?)</pane>', xml, re.S):
        name, kind, body = m.groups()
        if kind != "0":
            continue
        tracks = out.setdefault(name, {})
        for ttype, _a, tbody in re.findall(TAGBLOCK, body, re.S):
            for ch, ebody in re.findall(
                    r'<entry type1="\d+" type2="([^"]+)">(.*?)</entry>', tbody, re.S):
                key = CHANNELS.get(ch) if ttype == "RLPA" else (
                    "alpha" if ttype == "RLVC" and ch == "16" else None)
                if key:
                    tracks[key] = [tuple(map(float, k)) for k in re.findall(
                        rf"<frame>{FLOAT}</frame>\s*<value>{FLOAT}</value>"
                        rf"\s*<blend>{FLOAT}</blend>", ebody)]
    return out


def parse_materials(xml):
    mats = {}
    for name, body in re.findall(r'<entries name="([^"]+)">(.*?)</entries>', xml, re.S):
        t = re.search(r'<texture name="([^"]+)">\s*<wrap_s>(\w+)</wrap_s>'
                      r'\s*<wrap_t>(\w+)</wrap_t>', body)
        srt = dict(re.findall(rf"<(XTrans|YTrans|Rotate|XScale|YScale)>{FLOAT}<", body))
        mats[name] = dict(tex=t.group(1) if t else None,
                          wrap=(t.group(2), t.group(3)) if t else None,
                          srt={k: float(v) for k, v in srt.items()})
    return mats


def parse_layout(xml):
    """Flat pane list in draw order; pas1/pae1 resolve the parent links."""
    panes, stack = [], []
    for m in re.finditer(r'<tag type="(\w+)"((?:[^>]*[^/>])?)(?:>(.*?)</tag>|\s*/>)',
                         xml, re.S):
        kind, attrs, body = m.groups()
        if kind == "pas1":
            stack.append(len(panes) - 1)
            continue
        if kind == "pae1":
            stack.pop()
            continue
        if kind not in ("pan1", "pic1", "txt1", "wnd1", "bnd1") or body is None:
            continue
        tr = re.search(rf"<translate>\s*<x>{FLOAT}</x>\s*<y>{FLOAT}</y>", body)
        ro = re.search(rf"<rotate>.*?<z>{FLOAT}</z>", body, re.S)
        sc = re.search(rf"<scale>\s*<x>{FLOAT}</x>\s*<y>{FLOAT}</y>", body)
        sz = re.search(rf"<width>{FLOAT}</width>\s*<height>{FLOAT}</height>", body)
        mat = re.search(r'<material name="([^"]+)"', body)
        uv = re.findall(rf'<coord(TL|TR|BL|BR) s="{FLOAT}" t="{FLOAT}"', body)
        panes.append(dict(
            kind=kind, name=re.search(r'name="([^"]*)"', attrs).group(1),
            parent=stack[-1] if stack else None,
            visible=re.search(r"<visible>(\d+)</visible>", body).group(1) == "01",
            alpha=int(re.search(r"<alpha>(\w+)</alpha>", body).group(1), 16),
            tx=float(tr.group(1)), ty=float(tr.group(2)), rz=float(ro.group(1)),
            sx=float(sc.group(1)), sy=float(sc.group(2)),
            w=float(sz.group(1)), h=float(sz.group(2)),
            mat=mat.group(1) if mat else None,
            uv={c: (float(s), float(t)) for c, s, t in uv[:4]}))
    return panes


def decode_textures(arc, mats):
    out = {}
    for m in mats.values():
        name = m["tex"]
        if not name or name in out:
            continue
        data = arc.get(f"/arc/timg/{name}")
        info = T.parse(data)[0]
        img = T.decode(data[info["data_off"]:], info["w"], info["h"], info["fmt"],
                       info["pal"])
        out[name] = np.asarray(img.convert("RGBA"), dtype=np.float32) / 255.0
    return out


# ---------------------------------------------------------------- composing

def pane_matrix(p, tr, frame):
    val = lambda k: hermite(tr[k], frame) if k in tr else p[k]
    tx, ty, rz, sx, sy = (val(k) for k in ("tx", "ty", "rz", "sx", "sy"))
    c, s = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    return np.array([[c * sx, -s * sy, tx], [s * sx, c * sy, ty], [0, 0, 1]])


def texture_matrix(srt):
    """NW4R's CalcTextureMtx: scale and rotate about (0.5, 0.5), then translate."""
    sx, sy = srt.get("XScale", 1.0), srt.get("YScale", 1.0)
    r = math.radians(srt.get("Rotate", 0.0))
    c, s = math.cos(r), math.sin(r)
    a0, a1, b0, b1 = c * sx, -s * sy, s * sx, c * sy
    return (a0, a1, srt.get("XTrans", 0.0) + 0.5 - 0.5 * (a0 + a1),
            b0, b1, srt.get("YTrans", 0.0) + 0.5 - 0.5 * (b0 + b1))


def wrap(coord, size, mode):
    if mode == "GX_REPEAT":
        return np.mod(coord, size)
    if mode == "GX_MIRROR":
        period = np.mod(coord, 2 * size)
        return np.where(period < size, period, 2 * size - 1 - period)
    return np.clip(coord, 0, size - 1)


def sample(tex, s, t, wrap_s, wrap_t):
    """Bilinear fetch, GX style: texel centres at (i + 0.5) / size."""
    th, tw = tex.shape[:2]
    x, y = s * tw - 0.5, t * th - 0.5
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    xs = [wrap(x0, tw, wrap_s).astype(int), wrap(x0 + 1, tw, wrap_s).astype(int)]
    ys = [wrap(y0, th, wrap_t).astype(int), wrap(y0 + 1, th, wrap_t).astype(int)]
    top = tex[ys[0], xs[0]] * (1 - fx) + tex[ys[0], xs[1]] * fx
    bot = tex[ys[1], xs[0]] * (1 - fx) + tex[ys[1], xs[1]] * fx
    return top * (1 - fy) + bot * fy


def render_frame(panes, mats, tex, anim, frame, canvas):
    W, H = canvas
    img = np.zeros((H, W, 3), dtype=np.float32)
    world, galpha = [], []
    for p in panes:
        tr = anim.get(p["name"], {})
        m = pane_matrix(p, tr, frame)
        a = (hermite(tr["alpha"], frame) if "alpha" in tr else p["alpha"]) / 255.0
        vis = p["visible"]
        if p["parent"] is not None:
            m = world[p["parent"]] @ m
            a *= galpha[p["parent"]]
            vis = vis and panes[p["parent"]]["_vis"]
        p["_vis"] = vis
        world.append(m)
        galpha.append(max(0.0, min(1.0, a)))

    for p, m, a in zip(panes, world, galpha):
        if p["kind"] != "pic1" or not p["_vis"] or a <= 0.002:
            continue
        mat = mats[p["mat"]]
        if not mat["tex"]:
            continue
        w, h = p["w"], p["h"]
        corners = m @ np.array([[-w / 2, w / 2, -w / 2, w / 2],
                                [h / 2, h / 2, -h / 2, -h / 2], [1, 1, 1, 1]])
        px, py = corners[0] + W / 2, H / 2 - corners[1]
        x0, x1 = max(0, int(np.floor(px.min()))), min(W, int(np.ceil(px.max())))
        y0, y1 = max(0, int(np.floor(py.min()))), min(H, int(np.ceil(py.max())))
        if x0 >= x1 or y0 >= y1:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        inv = np.linalg.inv(m)
        lx = inv[0, 0] * (gx - W / 2) + inv[0, 1] * (H / 2 - gy) + inv[0, 2]
        ly = inv[1, 0] * (gx - W / 2) + inv[1, 1] * (H / 2 - gy) + inv[1, 2]
        u, v = (lx + w / 2) / w, (h / 2 - ly) / h
        inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
        if not inside.any():
            continue
        uv = p["uv"]
        bl = lambda i: ((1 - u) * (1 - v) * uv["TL"][i] + u * (1 - v) * uv["TR"][i]
                        + (1 - u) * v * uv["BL"][i] + u * v * uv["BR"][i])
        s, t = bl(0), bl(1)
        a0, a1, a2, b0, b1, b2 = texture_matrix(mat["srt"])
        s, t = a0 * s + a1 * t + a2, b0 * s + b1 * t + b2
        rgba = sample(tex[mat["tex"]], s, t, *mat["wrap"])
        alpha = rgba[..., 3] * a * inside
        region = img[y0:y1, x0:x1]
        region += (rgba[..., :3] - region) * alpha[..., None]
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


# ------------------------------------------------------------------ outputs

def load(path):
    """-> (kind, panes, mats, textures, {anim_name: tracks}) from a .bin."""
    arc = U8.load(unpack_lz77_imd5(open(path, "rb").read()))
    kind = "banner" if any(p.endswith("banner.brlyt") for _, p in arc.paths()) else "icon"
    open(f"{BENZIN}/rd_{kind}.brlyt", "wb").write(arc.get(f"/arc/blyt/{kind}.brlyt"))
    benzin("r", f"rd_{kind}.brlyt", f"rd_{kind}.xmlyt")
    lyt = open(f"{BENZIN}/rd_{kind}.xmlyt").read()
    anims = {}
    for _, p in arc.paths():
        if p.endswith(".brlan"):
            stem = os.path.basename(p)[:-6]
            open(f"{BENZIN}/rd_{stem}.brlan", "wb").write(arc.get(p))
            benzin("r", f"rd_{stem}.brlan", f"rd_{stem}.xmlan")
            xan = open(f"{BENZIN}/rd_{stem}.xmlan").read()
            size = int(re.search(r'framesize="(\d+)"', xan).group(1))
            anims[stem] = (parse_anim(xan), size)
    mats = parse_materials(lyt)
    return kind, parse_layout(lyt), mats, decode_textures(arc, mats), anims


def guides(img, kind, menu_view):
    """Outline the 4:3 area; in menu view, grey out what the button strip hides."""
    W, H = img.size
    sw, sh = BANNER_43 if kind == "banner" else ICON_43
    d = ImageDraw.Draw(img, "RGBA")
    if kind == "banner" and menu_view:
        cut = H / 2 - MENU_STRIP_Y
        d.rectangle([0, cut, W, H], fill=(210, 210, 214, 235))
    d.rectangle([(W - sw) // 2, (H - sh) // 2, (W + sw) // 2 - 1, (H + sh) // 2 - 1],
                outline=(0, 255, 170, 160))
    return img


def main():
    src, prefix = sys.argv[1], sys.argv[2]
    kind, panes, mats, tex, anims = load(src)
    canvas = BANNER_CANVAS if kind == "banner" else ICON_CANVAS
    scale = 0.5 if kind == "banner" else 2
    fit = lambda im: im.resize((int(im.width * scale), int(im.height * scale)),
                               Image.LANCZOS)
    for name, (anim, size) in anims.items():
        step = 3
        frames = [fit(guides(render_frame(panes, mats, tex, anim, f, canvas), kind, True))
                  for f in range(0, size, step)]
        out = f"{prefix}_{name}.gif"
        frames[0].save(out, save_all=True, append_images=frames[1:],
                       duration=int(1000 * step / 60), loop=0)
        print(f"  {os.path.basename(out)}: {len(frames)} frames of {size}")
    # A still from mid-Loop for side-by-side comparisons.
    anim, size = anims.get(f"{kind}_Loop", anims.get(kind))
    still = guides(render_frame(panes, mats, tex, anim, size // 2, canvas), kind, True)
    if kind == "icon":
        still = still.resize((still.width * 3, still.height * 3), Image.LANCZOS)
    still.save(f"{prefix}_still.png")
    print(f"  {os.path.basename(prefix)}_still.png")


if __name__ == "__main__":
    main()
