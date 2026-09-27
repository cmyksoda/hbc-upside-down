"""A 720p widescreen MP4 of the banner as the Menu plays it: Start, then Loop,
with the channel's own BNS jingle (intro once, then its loop section).

    make_video.py [banner.bin] [out.mp4]
"""

import os
import struct
import subprocess
import sys
import wave
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np

import render as R
from hbcud import MENU_STRIP_Y, OUT, WAD_NAME
from wiilib import U8, WAD, imd5_unwrap

FPS = 60
SIZE = (1280, 720)
CANVAS = (810.67, 456)          # what 16:9 shows, in layout units
LOOPS = 1
STRIP = (214, 214, 218)


def clamp16(v):
    return max(-32768, min(32767, v))


def decode_dsp(data, coefs, count):
    out, h1, h2 = [], 0, 0
    for o in range(0, len(data), 8):
        ps = data[o]
        scale = (1 << (ps & 0xF)) * 2048
        c1, c2 = coefs[(ps >> 4 & 7) * 2], coefs[(ps >> 4 & 7) * 2 + 1]
        for i in range(14):
            n = data[o + 1 + i // 2]
            n = (n >> 4) if i % 2 == 0 else (n & 0xF)
            s = clamp16((c1 * h1 + c2 * h2 + scale * (n - 16 if n > 7 else n) + 1024) >> 11)
            h2, h1 = h1, s
            out.append(s)
    return out[:count]


def decode_bns(bns):
    """-> (rate, loop_start or None, [channel samples])."""
    io, dataoff = struct.unpack(">I", bns[16:20])[0], struct.unpack(">I", bns[24:28])[0]
    base = io + 8
    loop, chans, rate = bns[base + 1], bns[base + 2], struct.unpack(">H", bns[base + 4:base + 6])[0]
    loop_start, total, table = struct.unpack(">III", bns[base + 8:base + 20])
    out = []
    for c in range(chans):
        info = base + struct.unpack(">I", bns[base + table + 4 * c:base + table + 4 * c + 4])[0]
        doff, coff = struct.unpack(">II", bns[info:info + 8])
        coefs = struct.unpack(">16h", bns[base + coff:base + coff + 32])
        start = dataoff + 8 + doff
        out.append(decode_dsp(bns[start:start + (total + 13) // 14 * 8], coefs, total))
    return rate, (loop_start if loop else None), out


def soundtrack(bns, seconds, path):
    rate, loop_start, chans = decode_bns(bns)
    pcm = np.array(chans, dtype=np.int16).T
    parts, have = [pcm], len(pcm)
    while loop_start is not None and have < seconds * rate:
        parts.append(pcm[loop_start:])
        have += len(pcm) - loop_start
    track = np.concatenate(parts)[:int(seconds * rate)]
    with wave.open(path, "wb") as w:
        w.setnchannels(track.shape[1])
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(track.tobytes())


def frame(job):
    anim, f = job
    img = R.render_frame(PANES, MATS, TEX, ANIMS[anim][0], f, CANVAS, SIZE[1] / CANVAS[1])
    img = np.asarray(img.resize(SIZE)).copy()
    img[round(SIZE[1] / 2 - MENU_STRIP_Y * SIZE[1] / CANVAS[1]):] = STRIP
    return img.tobytes()


def main():
    global PANES, MATS, TEX, ANIMS
    src = sys.argv[1] if len(sys.argv) > 1 else f"{OUT}/banner.bin"
    dst = sys.argv[2] if len(sys.argv) > 2 else f"{OUT}/banner_16_9.mp4"
    _, PANES, MATS, TEX, ANIMS = R.load(src)
    jobs = [("banner_Start", f) for f in range(ANIMS["banner_Start"][1])]
    jobs += [("banner_Loop", f) for _ in range(LOOPS) for f in range(ANIMS["banner_Loop"][1])]
    seconds = len(jobs) / FPS

    app = WAD.load(f"{OUT}/{WAD_NAME}").contents[0]
    meta = U8.load(app[app.find(b"\x55\xAA\x38\x2D"):])
    wav = f"{OUT}/banner_sound.wav"
    soundtrack(imd5_unwrap(meta.get("meta/sound.bin")), seconds, wav)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{SIZE[0]}x{SIZE[1]}", "-r", str(FPS), "-i", "-", "-i", wav,
         "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", dst],
        stdin=subprocess.PIPE)
    with Pool() as pool:
        for i, raw in enumerate(pool.imap(frame, jobs, chunksize=4)):
            ff.stdin.write(raw)
            if i % 120 == 0:
                print(f"  frame {i}/{len(jobs)}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"  {dst}: {seconds:.1f}s, {os.path.getsize(dst) // 1024} KiB")


if __name__ == "__main__":
    main()
