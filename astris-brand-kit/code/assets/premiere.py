"""
Premiere Pro assets in a style:
  corner bug       the logo as a watermark: PNG in three sizes (light + colour), a 150 x 150 YouTube watermark,
                   and a 10 s transparent ProRes 4444 clip that fades in, sits at 70 %, and fades out
  lower thirds     three designs, 5 s each, transparent ProRes 4444. Names and titles come from brand-config.json
  overlays         4K, 10 s, seamless loops: film grain (fine / medium / coarse), dust and scratches, soft light leaks
  PREMIERE-README  how to use all of it

Usage: python3 code/build.py premiere [--style red] [bug lower-thirds overlays readme]
"""
import shutil
import subprocess
import time

import cv2
import numpy as np

from engine import lockup as L
from engine import type as T
from engine.core import grain_field, hex_rgb, press, rng_for, save_png_alpha
from engine.paths import STYLE_DIRS, SUB, WORK, out
from engine.style import config
from engine.video import FPS, H, W, X264, Clip, ease_in_out, ease_out, ease_out_back, keys

F = 1.0 / FPS


def tones(style):
    """Colours for things that sit on top of footage (so they can't rely on the style's own background)."""
    h, k = style.hex, style.key
    if k == "red":
        return dict(light=h["light"], bar=h["signature"], on_bar=h["light"], box=h["dark"], on_box=h["light"], tab=h["signature"], on_tab=h["light"], line=h["signature"], shadow=None)
    if k == "yellow":
        return dict(light=h["light"], bar=h["signature"], on_bar=h["dark"], box=h["dark"], on_box=h["signature"], tab=h["signature"], on_tab=h["dark"], line=h["signature"], shadow=None)
    return dict(light=h["light"], bar=h["light"], on_bar=h["signature"], box=h["signature"], on_box=h["light"], tab=h["second"], on_tab=h["dark"], line=h["second"], shadow=h["second"])


# ====================================================================================================
# corner bug
# ====================================================================================================
def bug_png(style, width, colour, shadow=None, pad=0.10):
    """The logo alone on a transparent square-ish canvas `width` px wide -> (rgb, alpha). shadow = a second colour, offset behind."""
    lg = style.logo
    p = int(round(width * pad))
    w_in = width - 2 * p
    s = max(1.0, w_in / 700.0)
    a = press(lg.tight(w_in), w_in * 0.5, s, seed=f"{style.key}-bug-{width}", bleed=style.bleed, rough=style.rough, wear=0)
    hh = a.shape[0] + 2 * p

    def place(m, off=0):
        c = np.zeros((hh, width), np.float32)
        c[p + off:p + off + m.shape[0], p + off:p + off + m.shape[1]] = m
        return c
    top = place(a)
    rgb = np.zeros((hh, width, 3), np.float32)        # premultiplied while compositing
    al = np.zeros((hh, width), np.float32)
    if shadow:
        solid = place(press(lg.mask(a.shape, 0, 0, w_in / lg.aspect, holes=False), w_in * 0.5, s, seed="solid", wear=0))
        sh = place(a, max(1, int(round(w_in * 0.022)))) * (1 - solid)
        rgb += sh[..., None] * hex_rgb(shadow)
        al += sh
    rgb = rgb * (1 - top[..., None]) + top[..., None] * hex_rgb(colour)
    al = al * (1 - top) + top
    straight = rgb / np.maximum(al, 1e-4)[..., None]
    straight[al < 1e-4] = hex_rgb(colour)
    return straight, al


def bug(style):
    k, t = style.key, tones(style)
    d = out(k, "premiere", "corner-bug")
    n = 0
    for name, colour, shadow in (("light", t["light"], None), ("colour", style.hex["signature"], t["shadow"])):
        for size in (512, 256, 128):
            rgb, al = bug_png(style, size, colour, shadow)
            save_png_alpha(rgb, al, d / f"astris-{k}-bug-{name}-{size}.png")
            n += 1
    # YouTube video watermark: 150 x 150, transparent, one colour
    rgb, al = bug_png(style, 130, t["light"])
    cv_rgb = np.empty((150, 150, 3), np.float32)
    cv_rgb[:] = hex_rgb(t["light"])
    cv_al = np.zeros((150, 150), np.float32)
    y0, x0 = (150 - al.shape[0]) // 2, 10
    cv_al[y0:y0 + al.shape[0], x0:x0 + 130] = al
    p = save_png_alpha(cv_rgb, cv_al, d / f"astris-{k}-youtube-watermark-150x150.png")
    assert p.stat().st_size < 1e6
    # the 10 s clip: bottom-right, inside the title-safe area
    dur = 10.0
    clip = Clip(style, dur, seed=f"{k}-bug", transparent=True)
    hpx = 170
    cx, cy = W - 230 - hpx * style.logo.aspect / 2, H - 200 - hpx / 2
    clip.art.tag = "bug"
    clip.art.logo(cx, cy, hpx, role="colour", colour=t["light"], wear=0, shadow=False)
    clip.animate = lambda tt: {"bug": {"a": 0.70 * keys(tt, [(0, 0), (0.5, 1), (dur - 0.5 - F, 1), (dur - F, 0)])}}
    clip.render_prores(d / f"astris-{k}-bug-10s-4k24-prores4444.mov")
    return n + 2


# ====================================================================================================
# lower thirds
# ====================================================================================================
LT_DUR, LT_X = 5.0, 230
LT_OUT = 4.30
LT_NAMES = {1: "bar", 2: "line", 3: "stack"}


def lt_entry(i):
    lts = config().get("lower_thirds") or [{"name": "[YOUR NAME]", "title": "[YOUR ROLE]"}]
    return lts[(i - 1) % len(lts)]


def lower_third(style, design, entry=None):
    k, t = style.key, tones(style)
    e = entry or lt_entry(design)
    name, title = e["name"], e["title"].upper()
    clip = Clip(style, LT_DUR, seed=f"{k}-lt-{design}", transparent=True)
    art, face, tf = clip.art, style.display, style.text_face(500)

    def put(tag, s, x, y, size, colour, fnt=None, tracking=0.0, **kw):
        art.tag = tag
        return art.text(s, x, y, size, face=fnt, tracking=tracking, anchor="ls", role="colour", colour=colour, shadow=False, **kw)

    def out_p(tt, t0=LT_OUT, d=0.34):
        return 1.0 - ease_in_out((tt - t0) / d)

    if design == 1:
        # the logo on a dark tile, and a bar of the style's colour that slides out of it with the name
        y0, bh = 1640, 260
        size = min(140.0, T.fit_size(name, face, 2300, 0.01))
        wn = T.text_width(name, face, size, 0.01)
        wt = T.text_width(title, tf, 46, 0.16)
        bw = int(max(wn, wt) + 2 * 64)
        art.tag = "bar"
        art.rect(LT_X + bh - 40, y0, LT_X + bh + bw, y0 + bh, role="colour", colour=t["bar"], radius=18, size=bh, wear=0, shadow=False)
        art.tag = "tile"
        art.rect(LT_X, y0, LT_X + bh, y0 + bh, role="colour", colour=t["box"], radius=18, size=bh, wear=0, shadow=False)
        art.logo(LT_X + bh / 2, y0 + bh / 2, bh * 0.52, role="colour", colour=t["on_box"], wear=0, shadow=False)
        tx = LT_X + bh + 64
        if t["shadow"]:
            put("name", name, tx + 5, y0 + 46 + face.cap * size + 5, size, t["shadow"], tracking=0.01)
        put("name", name, tx, y0 + 46 + face.cap * size, size, t["on_bar"], tracking=0.01)
        put("title", title, tx + 3, y0 + bh - 36, 46, t["on_bar"], tf, 0.16, wear=0)
        pv = (LT_X + bh / 2, y0 + bh / 2)

        def animate(tt):
            o = out_p(tt)
            k1 = ease_out_back((tt - 0.20) / 0.30, 1.6)
            s = {"tile": {"a": 0.0} if tt < 0.20 else {"s": (0.6 + 0.4 * k1) * (0.7 + 0.3 * o) if o < 1 else 0.6 + 0.4 * k1, "a": min(1.0, (tt - 0.2) / (2 * F)) * min(1.0, o * 2), "cx": pv[0], "cy": pv[1]}}
            p = min(ease_in_out((tt - 0.34) / 0.42), out_p(tt, LT_OUT - 0.06))
            s["bar"] = {"a": 0.0} if p <= 0 else ({"wipe": ("right", p, 0.01)} if p < 1 else {})
            p = min(ease_in_out((tt - 0.52) / 0.36), out_p(tt, LT_OUT - 0.14, 0.24))
            s["name"] = {"a": 0.0} if p <= 0 else ({"wipe": ("right", p, 0.03)} if p < 1 else {})
            a = min(ease_out((tt - 0.78) / 0.25), out_p(tt, LT_OUT - 0.16, 0.2))
            s["title"] = {"a": max(0.0, a)}
            return s
    elif design == 2:
        # no box: a line draws on, the name rises out of it, the title settles under it
        size = min(190.0, T.fit_size(name, face, 2600, 0.01))
        yb = 1800
        wn = T.text_width(name, face, size, 0.01)
        wt = T.text_width(title, tf, 50, 0.16)
        if t["shadow"]:
            put("name", name, LT_X + 6, yb + 6, size, t["shadow"], tracking=0.01)
        put("name", name, LT_X, yb, size, t["light"], tracking=0.01)
        art.tag = "line"
        art.rect(LT_X, yb + 34, LT_X + max(wn, wt), yb + 48, role="colour", colour=t["line"], size=40, wear=0, shadow=False)
        put("title", title, LT_X + 3, yb + 48 + 34 + tf.cap * 50, 50, t["light"], tf, 0.16, wear=0)

        def animate(tt):
            p = min(ease_in_out((tt - 0.20) / 0.40), out_p(tt))
            s = {"line": {"a": 0.0} if p <= 0 else ({"wipe": ("right", p, 0.01)} if p < 1 else {})}
            kk = ease_out((tt - 0.42) / 0.40, 3)
            o = out_p(tt, LT_OUT - 0.10, 0.26)
            p = min(kk, o)
            s["name"] = {"a": 0.0} if p <= 0 else ({"wipe": ("up", p, 0.04), "dy": 34 * (1 - p)} if p < 1 else {})
            a = min(ease_out((tt - 0.72) / 0.28), out_p(tt, LT_OUT - 0.14, 0.2))
            s["title"] = {"a": max(0.0, a), "dx": -24 * (1 - max(0.0, a))}
            return s
    else:
        # two labels, stamped on at a slight tilt: the name on the dark one, the title on a tab of colour
        size = min(132.0, T.fit_size(name, face, 2300, 0.01))
        wn = T.text_width(name, face, size, 0.01)
        wt = T.text_width(title, tf, 46, 0.16)
        y0, bh, th = 1640, 196, 88
        bw, tw = int(wn + 2 * 52), int(wt + 2 * 40)
        if t["shadow"]:
            art.tag = "box"
            art.rect(LT_X + 12, y0 + 12, LT_X + bw + 12, y0 + bh + 12, role="colour", colour=t["shadow"], radius=14, size=bh, wear=0, shadow=False)
        art.tag = "tab"
        tx0, ty0 = LT_X + 70, y0 + bh - 16
        art.rect(tx0, ty0, tx0 + tw, ty0 + th, role="colour", colour=t["tab"], radius=12, size=th, wear=0, shadow=False)
        put("tab", title, tx0 + 40, ty0 + th / 2 + tf.cap * 46 / 2 + 6, 46, t["on_tab"], tf, 0.16, wear=0)
        art.tag = "box"
        art.rect(LT_X, y0, LT_X + bw, y0 + bh, role="colour", colour=t["box"], radius=14, size=bh, wear=0, shadow=False)
        put("box", name, LT_X + 52, y0 + bh / 2 + face.cap * size / 2, size, t["on_box"], tracking=0.01)
        pv = (LT_X + bw / 2, y0 + bh / 2)
        tilt = -2.0

        def animate(tt):
            o = out_p(tt, LT_OUT, 0.22)
            t0 = 0.25
            s = {"box": {"a": 0.0} if tt < t0 else {"a": min(1.0, (tt - t0) / F) * o, "r": tilt, "cx": pv[0], "cy": pv[1],
                                                     "s": keys(tt, [(t0, 1.28), (t0 + 2 * F, 0.97), (t0 + 4 * F, 1.0)]) * (0.9 + 0.1 * o)}}
            kk = ease_out_back((tt - 0.46) / 0.30, 1.4)
            s["tab"] = {"a": 0.0} if tt < 0.46 else {"a": min(1.0, (tt - 0.46) / (2 * F)) * o, "r": tilt, "cx": pv[0], "cy": pv[1], "dy": -70 * (1 - kk)}
            return s
    clip.animate = animate
    return clip


def lower_thirds(style):
    k = style.key
    d = out(k, "premiere", "lower-thirds")
    for i in (1, 2, 3):
        clip = lower_third(style, i)
        stem = f"astris-{k}-lower-third-{i}-{LT_NAMES[i]}"
        rgba = clip.frame(int(2.5 * FPS))
        save_png_alpha(rgba[..., :3] / 255.0, rgba[..., 3] / 255.0, d / f"{stem}-still-3840x2160-transparent.png")
        clip.render_prores(d / f"{stem}-5s-4k24-prores4444.mov")
    return 6


# ====================================================================================================
# overlay loops
# ====================================================================================================
OV_DUR = 10.0
OV_N = int(OV_DUR * FPS)


def _encode(path, frames, pix="gray"):
    t0 = time.time()
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"] + X264 + ["-movflags", "+faststart", str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in frames:
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {path}")
    print(f"    {path.name}: {time.time() - t0:.0f}s, {path.stat().st_size / 1e6:.1f} MB", flush=True)
    return path


GRAINS = {"fine": (0.70, 0.050), "medium": (1.20, 0.056), "coarse": (2.00, 0.062)}        # softness in px at 4K, strength


def grain_loop(name, path):
    sigma, amp = GRAINS[name]
    g = grain_field(H, W, f"overlay-{name}", sigma)
    base = np.clip((0.5 + amp * g) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    r = rng_for("overlay-walk", name)
    steps = r.integers(6, 15, (OV_N, 2)) * r.choice([-1, 1], (OV_N, 2))
    walk = np.cumsum(steps, axis=0)
    return _encode(path, (np.roll(np.roll(base, int(walk[i, 0]), 0), int(walk[i, 1]), 1) for i in range(OV_N)))


def dust_loop(path):
    r = rng_for("overlay-dust")
    # scratches live for a while; their lifetimes wrap round the end so the loop has no seam
    scratches = []
    for _ in range(9):
        scratches.append(dict(x=r.uniform(0.04, 0.96) * W, start=int(r.integers(0, OV_N)), life=int(r.integers(5, 34)), w=r.uniform(1.4, 3.0),
                              b=r.uniform(0.35, 0.8), drift=r.uniform(-1.2, 1.2), broken=r.random() < 0.5))

    def frames():
        for i in range(OV_N):
            im = np.zeros((H, W), np.uint8)
            fr = np.random.default_rng(1000 + i)
            for _ in range(int(fr.integers(14, 46))):                       # specks
                x, y, rad = fr.uniform(0, W), fr.uniform(0, H), fr.gamma(2.0, 1.5) + 1.2
                cv2.circle(im, (int(x * 16), int(y * 16)), int(rad * 16), int(fr.uniform(70, 235)), -1, cv2.LINE_AA, 4)
            if fr.random() < 0.16:                                           # the odd hair
                x, y, ang = fr.uniform(0, W), fr.uniform(0, H), fr.uniform(0, np.pi)
                ln, bend = fr.uniform(60, 260), fr.normal(0, 0.9)
                pts = [[(x + np.cos(ang + bend * u) * ln * u) * 16, (y + np.sin(ang + bend * u) * ln * u) * 16] for u in np.linspace(-0.5, 0.5, 9)]
                cv2.polylines(im, [np.asarray(pts, np.int32)], False, int(fr.uniform(90, 200)), 2, cv2.LINE_AA, 4)
            if fr.random() < 0.05:                                           # a bigger blotch, rarely
                x, y = fr.uniform(0, W), fr.uniform(0, H)
                cv2.ellipse(im, (int(x), int(y)), (int(fr.uniform(8, 22)), int(fr.uniform(5, 14))), fr.uniform(0, 180), 0, 360, int(fr.uniform(60, 150)), -1, cv2.LINE_AA)
            for sc in scratches:
                age = (i - sc["start"]) % OV_N
                if age < sc["life"]:
                    x = sc["x"] + sc["drift"] * age + fr.normal(0, 0.7)
                    b = int(255 * sc["b"] * fr.uniform(0.55, 1.0))
                    if sc["broken"]:
                        y = 0.0
                        while y < H:
                            seg = fr.uniform(120, 700)
                            if fr.random() < 0.7:
                                cv2.line(im, (int(x * 16), int(y * 16)), (int(x * 16), int(min(H, y + seg) * 16)), b, max(1, int(round(sc["w"]))), cv2.LINE_AA, 4)
                            y += seg
                    else:
                        cv2.line(im, (int(x * 16), 0), (int((x + fr.normal(0, 1.5)) * 16), H * 16), b, max(1, int(round(sc["w"]))), cv2.LINE_AA, 4)
            yield cv2.GaussianBlur(im, (0, 0), 0.9)
    return _encode(path, frames())


def leak_loop(style, path):
    """Soft blobs of the style's colours drifting round the edges of the frame. Every path and pulse closes after 10 s."""
    k, h = style.key, style.hex
    cols = {"red": [h["signature"], "#F08A3C", h["light"], "#E0522E"], "yellow": [h["signature"], "#FF8A00", h["light"], "#FFD45C"],
            "wildcard": [h.get("second", h["signature"]), h["signature"], h["light"], "#FF9A6B"]}[k]
    r = rng_for("leaks", k)
    lw, lh = 480, 270
    yy, xx = np.mgrid[0:lh, 0:lw].astype(np.float32)
    blobs = []
    for j, c in enumerate(cols):
        side = j % 4
        blobs.append(dict(col=hex_rgb(c), side=side, base=r.uniform(0.2, 0.8), amp=r.uniform(0.12, 0.3), cyc=int(r.integers(1, 3)), ph=r.uniform(0, 6.28),
                          rad=r.uniform(0.22, 0.42) * lw, pulse=int(r.integers(1, 4)), pph=r.uniform(0, 6.28), gain=r.uniform(0.34, 0.6), sq=r.uniform(0.5, 0.9)))
    dither = rng_for("leak-dither").uniform(-0.6, 0.6, (H, W, 3)).astype(np.float32)

    def frames():
        for i in range(OV_N):
            w = 2 * np.pi * i / OV_N
            img = np.zeros((lh, lw, 3), np.float32)
            for b in blobs:
                u = b["base"] + b["amp"] * np.sin(b["cyc"] * w + b["ph"])
                e = 0.10 * np.sin(b["cyc"] * w + b["ph"] + 1.3)
                cx, cy = {0: (-0.06 + e, u), 1: (1.06 - e, u), 2: (u, -0.10 + e), 3: (u, 1.10 - e)}[b["side"]]
                cx, cy = cx * lw, cy * lh
                rx, ry = (b["rad"] * b["sq"], b["rad"]) if b["side"] < 2 else (b["rad"], b["rad"] * b["sq"])
                d2 = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
                g = np.exp(-d2 * 1.6) * b["gain"] * (0.72 + 0.28 * np.sin(b["pulse"] * w + b["pph"]))
                img += g[..., None] * b["col"][None, None, :]
            img = 1.0 - np.exp(-img * 1.25)                                  # soft shoulder, never clips
            big = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)
            yield np.clip(big * 255.0 + 0.5 + np.roll(dither, i * 37, 1), 0, 255).astype(np.uint8)
    return _encode(path, frames(), pix="rgb24")


def overlays(style):
    k = style.key
    d = out(k, "premiere", "overlays")
    shared = WORK / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    n = 0
    # grain and dust are colour-neutral, so one render is shared by all three styles (same file, same name)
    for name in GRAINS:
        f = shared / f"astris-overlay-grain-{name}-10s-4k24.mp4"
        if not f.exists():
            grain_loop(name, f)
        shutil.copyfile(f, d / f.name)
        n += 1
    f = shared / "astris-overlay-dust-and-scratches-10s-4k24.mp4"
    if not f.exists():
        dust_loop(f)
    shutil.copyfile(f, d / f.name)
    leak_loop(style, d / f"astris-{k}-overlay-light-leaks-10s-4k24.mp4")
    return n + 2


# ====================================================================================================
def readme(style):
    import json
    k, name = style.key, style.name
    lts = config().get("lower_thirds", [])
    lts_json = ",\n".join("  " + json.dumps(e) for e in lts)
    (STYLE_DIRS[k] / SUB["premiere"] / "PREMIERE-README.md").write_text(f"""# Premiere Pro assets ({name})

Everything here drops straight onto a Premiere Pro timeline. Nothing needs a plug-in.

**One honest note first:** there are no `.mogrt` Motion Graphics Templates in this kit. Those can only be made inside
After Effects or Premiere, and this kit was built with code. Instead you get rendered clips with transparency
(ProRes 4444) that behave like any other clip, and a one-line command to re-render the lower thirds with your own names.

## What is in this folder

| Folder | What | How to use it |
|---|---|---|
| `corner-bug/` | The logo as a watermark: PNG at 512, 256 and 128 px (light and colour), and a 10 s clip that fades in, sits at 70 % and fades out | Put it on the top video track, bottom-right. The clip is already positioned inside the title-safe area. For a whole film use a PNG and set Opacity to 70 %. |
| `corner-bug/astris-{k}-youtube-watermark-150x150.png` | YouTube's own watermark slot | YouTube Studio, Customisation, Branding, Video watermark. |
| `lower-thirds/` | Three designs, 5 s each, with transparency, plus a still PNG of each | Drop on a track above your footage. They animate in, hold, and animate out. To hold longer, use the still PNG between two cuts of the clip. |
| `overlays/` | 4K, 10 s seamless loops: film grain (fine, medium, coarse), dust and scratches, light leaks | Put on a track above your footage and set the blend mode (table below). Loop by duplicating the clip end to end. |

Sound effects are in `../{SUB['sound']}/`, textures and colour looks in `../{SUB['textures']}/`, and the intros,
title logo and end card in `../{SUB['video']}/`.

## Blend modes for the overlays

Select the overlay clip, open Effect Controls, Opacity, Blend Mode.

| Overlay | Blend mode | Opacity to start with |
|---|---|---|
| `astris-overlay-grain-fine / medium / coarse` (grey) | **Overlay** (or Soft Light for less) | 60 to 75 % matches the grain in the brand graphics. 100 % is strong. |
| `astris-overlay-dust-and-scratches` (white on black) | **Screen** | 40 to 70 % |
| `astris-{k}-overlay-light-leaks` (colour on black) | **Screen** (or Linear Dodge (Add) for more) | 50 to 100 % |

The grain and dust loops are colour-neutral, so they are the same files in all three style folders.

## Transparent clips (ProRes 4444)

The `.mov` files carry an alpha channel. Premiere reads it automatically. If a clip ever shows a black background,
right-click it in the Project panel, Modify, Interpret Footage, Alpha Channel, and make sure "Ignore Alpha Channel" is off
and "Premultiplied Alpha" is off (these files use straight alpha).

## Putting your own name on the lower thirds

The text comes from `brand-config.json` at the top of the kit:

```json
"lower_thirds": [
{lts_json}
]
```

Design 1 uses the first entry, design 2 the second, design 3 the third. Change the names, then run:

```
python3 code/build.py premiere --style {k} lower-thirds
```

Each clip takes under a minute to render. See `code/README.md` for the one-time setup.

## Sequence settings these were made for

3840 x 2160, 24 fps, Rec. 709. They scale cleanly to 1920 x 1080 (set Scale to 50 % or use "Set to Frame Size").
At other frame rates Premiere will conform them; the animations are short enough that it is not noticeable.
""")
    return 1


PIECES = ["bug", "lower-thirds", "overlays", "readme"]


def build(style, *which):
    which = [w for w in which if w in PIECES] or PIECES
    n = 0
    if "bug" in which:
        n += bug(style)
    if "lower-thirds" in which:
        n += lower_thirds(style)
    if "overlays" in which:
        n += overlays(style)
    if "readme" in which:
        n += readme(style)
    return [f"{n} Premiere files"]
