"""
Textures and colour looks in a style:
  textures/   seamless 4096 x 4096 tiles: neutral film grain (fine / medium / coarse) and the style's own surfaces
              (its colour field, its paper, its dark) with the same grain as every graphic in the kit
  luts/       three 33-point .cube colour looks for footage (natural, strong, print) + a preview chart

Usage: python3 code/build.py textures [--style red] [textures luts]
"""
import math
import shutil

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from engine.core import apply_grain, hex_rgb, rng_for, save_jpg, save_png
from engine.paths import STYLE_DIRS, SUB, WORK, out

N = 4096
S = 1.5                       # textures are made at the same scale as the 4K video graphics


# ====================================================================================================
# seamless building blocks (everything wraps round the edges)
# ====================================================================================================
def blur_wrap(a, sigma):
    p = int(math.ceil(sigma * 4)) + 1
    b = cv2.GaussianBlur(np.pad(a, p, mode="wrap"), (0, 0), sigma)
    return b[p:-p, p:-p]


def tile_grain(n, seed, sigma):
    g = rng_for("tile-grain", seed).standard_normal((n, n), dtype=np.float32)
    if sigma > 0.25:
        g = blur_wrap(g, sigma)
    return g / float(g.std())


def tile_soft(n, seed, cell):
    """Smooth noise, period n."""
    k = max(2, int(round(n / cell)))
    low = rng_for("tile-soft", seed).standard_normal((k, k), dtype=np.float32)
    big = cv2.resize(np.pad(low, 2, mode="wrap"), ((k + 4) * (n // k + 1), (k + 4) * (n // k + 1)), interpolation=cv2.INTER_CUBIC)
    step = big.shape[0] / (k + 4)
    o = int(round(2 * step))
    crop = big[o:o + int(round(k * step)), o:o + int(round(k * step))]
    crop = cv2.resize(crop, (n, n), interpolation=cv2.INTER_LINEAR)
    return crop / float(crop.std())


def tile_paper(n, s, seed):
    """Paper: short fibres and the faintest mottle, multiplicative (about 1.0), seamless."""
    r = rng_for("tile-paper", seed)
    p = int(40 * s)
    big1 = np.zeros((n + 2 * p, n + 2 * p), np.uint8)
    big2 = np.zeros_like(big1)
    cnt = int(n * n / (5200.0 * s * s))
    xs, ys = r.uniform(0, n, cnt), r.uniform(0, n, cnt)
    ang, ln, bend = r.uniform(0, math.pi, cnt), r.uniform(9, 34, cnt) * s, r.normal(0, 0.35, cnt)
    for k in range(cnt):
        pts = []
        for t in (-0.5, -0.17, 0.17, 0.5):
            a = ang[k] + bend[k] * t
            pts.append([(xs[k] + p + math.cos(a) * ln[k] * t) * 16, (ys[k] + p + math.sin(a) * ln[k] * t) * 16])
        cv2.polylines(big1 if k % 3 else big2, [np.asarray(pts, np.int32)], False, int(r.integers(90, 255)), max(1, int(round(0.9 * s))), cv2.LINE_AA, 4)

    def fold(b):          # whatever spilled past an edge comes back in on the opposite side
        t = b[p:-p, p:-p].copy()
        t[:, :p] = np.maximum(t[:, :p], b[p:-p, n + p:])
        t[:, -p:] = np.maximum(t[:, -p:], b[p:-p, :p])
        t[:p, :] = np.maximum(t[:p, :], b[n + p:, p:-p])
        t[-p:, :] = np.maximum(t[-p:, :], b[:p, p:-p])
        return t.astype(np.float32) / 255.0
    tex = np.ones((n, n), np.float32)
    tex -= blur_wrap(fold(big1), 0.45 * s) * 0.050
    tex += blur_wrap(fold(big2), 0.45 * s) * 0.030
    tex *= 1.0 + 0.004 * tile_soft(n, f"{seed}-m", 260 * s)
    return tex


# ====================================================================================================
# textures
# ====================================================================================================
GRAINS = {"fine": (0.70, 0.050), "medium": (1.20, 0.056), "coarse": (2.00, 0.062)}


def surface(style, kind):
    """One of the style's own surfaces as a seamless tile (float RGB)."""
    k, rgb = style.key, style.rgb
    g = tile_grain(N, f"{k}-{kind}", style.grain_sigma * S)
    if kind == "paper":
        img = rgb["light"][None, None, :] * tile_paper(N, S, f"{k}-paper")[..., None]
    elif kind in ("ink-blue", "ink-coral"):
        ink = rgb["signature"] if kind == "ink-blue" else rgb["second"]
        paper = rgb["light"][None, None, :] * tile_paper(N, S, f"{k}-paper")[..., None]
        dens = 0.978 + 0.022 * np.clip(tile_soft(N, f"{k}-{kind}-d", 420 * S), -2, 1)
        mott = 1.0 - 0.10 * style.wear * np.clip(tile_grain(N, f"{k}-{kind}-s", 0.7 * S) - 0.4, 0, 2.5)
        a = (dens * mott).astype(np.float32)
        img = paper * (1.0 - a[..., None] * (1.0 - ink[None, None, :]))
    else:
        img = np.empty((N, N, 3), np.float32)
        img[:] = rgb["signature"] if kind == "field" else rgb["dark"]
    return np.clip(apply_grain(img, g, style.grain_amount, style.grain_lift), 0, 1)


def textures(style):
    k = style.key
    d = out(k, "textures", "textures")
    shared = WORK / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    made = []
    for name, (sigma, amp) in GRAINS.items():                      # neutral: the same files in every style
        f = shared / f"astris-texture-grain-{name}-4096x4096.png"
        if not f.exists():
            g = tile_grain(N, f"neutral-{name}", sigma)
            Image.fromarray(np.clip((0.5 + amp * g) * 255.0 + 0.5, 0, 255).astype(np.uint8), "L").save(f, optimize=True)
        shutil.copyfile(f, d / f.name)
        made.append(f.name)
    kinds = ["paper", "ink-blue", "ink-coral"] if k == "wildcard" else ["field", "paper", "dark"]
    check = []
    for kind in kinds:
        img = surface(style, kind)
        p = save_png(img, d / f"astris-{k}-texture-{kind}-4096x4096.png", max_err=2.2)
        made.append(f"{p.name}  {p.stat().st_size / 1e6:.1f} MB")
        # proof that it tiles: the four corners of a 2 x 2 repeat meet in the middle of this crop
        t2 = np.roll(np.roll(img, N // 2, 0), N // 2, 1)
        check.append(t2[N // 2 - 300:N // 2 + 300, N // 2 - 400:N // 2 + 400])
    save_jpg(np.concatenate(check, 1), d / f"astris-{k}-texture-seam-check.jpg", 90)
    return made


# ====================================================================================================
# colour looks (.cube)
# ====================================================================================================
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def grid(n=33):
    v = np.linspace(0, 1, n, dtype=np.float32)
    b, g, r = np.meshgrid(v, v, v, indexing="ij")              # .cube order: red changes fastest, blue slowest
    return np.stack([r, g, b], -1)


def hue_of(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    return h, (mx - mn)


def film_look(rgb, style, amount):
    """A gentle film grade pulled toward the style's palette. amount 1 = natural, 1.8 = strong."""
    k = style.key
    P = {"red":      dict(curve=0.10, lift=0.30, warm=(1.035, 1.000, 0.955), white=0.45, sat=0.94, boost=0.22),
         "yellow":   dict(curve=0.09, lift=0.12, warm=(1.040, 1.010, 0.925), white=0.40, sat=1.04, boost=0.20),
         "wildcard": dict(curve=0.10, lift=0.55, warm=(1.010, 1.000, 0.985), white=0.50, sat=0.90, boost=0.25)}[k]
    a = amount
    x = np.clip(rgb, 0, 1)
    x = x - (P["curve"] * a) * np.sin(2 * np.pi * x) / (2 * np.pi)                 # S-curve: more contrast in the middle
    x = x * (1 + (np.array(P["warm"], np.float32) - 1) * a)                         # where the mid-tones lean
    y = (x @ LUMA)[..., None]
    h, chroma = hue_of(x)
    sig_h, _ = hue_of(style.rgb["signature"][None, :])
    dh = np.abs(((h - sig_h[0] + 180) % 360) - 180)
    w = np.exp(-(dh / 38.0) ** 2) * np.clip(chroma * 4, 0, 1)                       # the signature colour sings a little more
    sat = 1 + (P["sat"] - 1) * a + P["boost"] * a * w
    x = y + (x - y) * sat[..., None]
    black = style.rgb["dark"] * P["lift"] * a                                        # blacks sit on the style's dark neutral
    lw = style.rgb["light"] / style.rgb["light"].max()
    white = 1 + (lw - 1) * P["white"] * a                                            # whites lean to the style's light neutral
    x = black + (white - black) * x
    return np.clip(x, 0, 1)


def print_look(rgb, style):
    """A graphic look: brightness is mapped onto the style's own colours, like a two- or three-ink print."""
    k, c = style.key, style.rgb
    if k == "wildcard":
        stops = [(0.0, c["dark"]), (0.34, c["signature"]), (0.70, c["second"]), (1.0, c["light"])]
    else:
        stops = [(0.0, c["dark"]), (0.46 if k == "red" else 0.62, c["signature"]), (1.0, c["light"])]
    y = np.clip(rgb @ LUMA, 0, 1)
    y = y - 0.10 * np.sin(2 * np.pi * y) / (2 * np.pi)
    out_ = np.zeros(rgb.shape, np.float32)
    xs = [s for s, _ in stops]
    for ch in range(3):
        out_[..., ch] = np.interp(y, xs, [col[ch] for _, col in stops])
    return np.clip(out_ * 0.88 + rgb * 0.12, 0, 1)


def write_cube(path, lut, title):
    n = lut.shape[0]
    flat = lut.reshape(-1, 3)
    lines = [f'TITLE "{title}"', "# ASTRIS PRODUCTIONS brand kit. Made for Rec. 709 footage. 33-point 3D LUT.", f"LUT_3D_SIZE {n}",
             "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0", ""]
    lines += [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in flat]
    path.write_text("\n".join(lines) + "\n")
    return path


def apply_lut(img, lut):
    n = lut.shape[0]
    co = [img[..., 2] * (n - 1), img[..., 1] * (n - 1), img[..., 0] * (n - 1)]     # lut is indexed [blue, green, red]
    return np.stack([map_coordinates(lut[..., ch], co, order=1, mode="nearest") for ch in range(3)], -1)


def chart(w=1200, h=800):
    """A test picture made of maths (no photo is used): colour sweep, grey ramp, and 24 familiar patch colours."""
    img = np.zeros((h, w, 3), np.float32)
    hh = int(h * 0.42)
    xx, yy = np.meshgrid(np.linspace(0, 1, w, dtype=np.float32), np.linspace(0, 1, hh, dtype=np.float32))
    hsv = np.stack([xx * 179, np.full_like(xx, 190), (1.0 - yy * 0.85) * 255], -1).astype(np.uint8)
    img[:hh] = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255
    r0, r1 = hh, hh + int(h * 0.10)
    img[r0:r1] = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    patches = ["#735244", "#c29682", "#627a9d", "#576c43", "#8580b1", "#67bdaa", "#d67e2c", "#505ba6", "#c15a63", "#5e3c6c", "#9dbc40", "#e0a32e",
               "#383d96", "#469449", "#af363c", "#e7c71f", "#bb5695", "#0885a1", "#f3f3f2", "#c8c8c8", "#a0a0a0", "#7a7a79", "#555555", "#343434"]
    pw, ph = w / 12.0, (h - r1) / 2.0
    for i, c in enumerate(patches):
        x0, y0 = int((i % 12) * pw), int(r1 + (i // 12) * ph)
        img[y0:int(y0 + ph), x0:int(x0 + pw)] = hex_rgb(c)
    return img


def luts(style):
    k = style.key
    d = out(k, "textures", "luts")
    g = grid(33)
    looks = [("1-natural", film_look(g, style, 1.0), "natural"), ("2-strong", film_look(g, style, 1.8), "strong"), ("3-print", print_look(g, style), "print")]
    made = []
    ch = chart()
    tiles = [ch]
    for slug_, lut, nice in looks:
        p = write_cube(d / f"astris-{k}-look-{slug_}-33.cube", lut, f"ASTRIS {style.name} - {nice}")
        made.append(p.name)
        tiles.append(apply_lut(ch, lut))
    gap = np.ones((ch.shape[0], 16, 3), np.float32) * 0.1
    row = []
    for t in tiles:
        row += [t, gap]
    save_jpg(np.concatenate(row[:-1], 1), d / f"astris-{k}-looks-preview.jpg", 90)
    (d / "LUTS-README.md").write_text(f"""# Colour looks ({style.name})

Three 33-point `.cube` files that pull your footage toward this style's palette.

| File | What it does | Where to use it |
|---|---|---|
| `astris-{k}-look-1-natural-33.cube` | A gentle film grade. Blacks sit on the style's dark neutral, whites lean to its light neutral, and the signature colour gets a little more life. | Everyday footage. Start at 70 to 100 % intensity. |
| `astris-{k}-look-2-strong-33.cube` | The same idea, pushed further. | Moody scenes, b-roll, anything that should feel graded. Start at 50 to 80 %. |
| `astris-{k}-look-3-print-33.cube` | A graphic look: brightness is mapped onto the style's own colours, like a {'two-ink risograph print' if k == 'wildcard' else 'duotone print'}. | Title sequences, freeze frames, thumbnails. Not for skin tones in a normal scene. |

`astris-{k}-looks-preview.jpg` shows a test chart: original, natural, strong, print (left to right). The chart is
generated, not a photograph, so judge the looks on your own footage.

## Using them in Premiere Pro (Lumetri Color)

1. Select the clip (or an adjustment layer above several clips).
2. Open **Lumetri Color**, then the **Creative** section.
3. In the **Look** menu choose **Browse...** and pick a `.cube` file from this folder.
4. Use the **Intensity** slider to taste. It is normal to end up below 100 %.

Do your basic correction first (exposure, white balance) in **Basic Correction**, then add the look in **Creative**.
These looks expect normal Rec. 709 footage. If you shoot in a log profile, convert it to Rec. 709 first
(Basic Correction, Input LUT, with your camera maker's conversion LUT), then add the look.

To have them appear in the Look menu every time, copy the `.cube` files into Adobe's shared folder
(create the folders if they are not there yet), then restart Premiere:

- macOS: `/Library/Application Support/Adobe/Common/LUTs/Creative`
- Windows: `C:\\Program Files\\Adobe\\Common\\LUTs\\Creative`

The same files work in DaVinci Resolve, Final Cut Pro (Custom LUT effect), After Effects (Apply Color LUT) and Photoshop
(Color Lookup adjustment layer).
""")
    return made


def readme(style):
    k = style.key
    kinds = ["paper", "ink-blue", "ink-coral"] if k == "wildcard" else ["field", "paper", "dark"]
    what = {"field": "the style's colour with its grain", "paper": "the light neutral as paper, with fibres and grain", "dark": "the dark neutral with grain",
            "ink-blue": "a full flood of the blue ink on paper", "ink-coral": "a full flood of the coral ink on paper"}
    rows = "\n".join(f"| `textures/astris-{k}-texture-{x}-4096x4096.png` | {what[x].capitalize()} | Use as a background, or behind titles. Normal blend mode. |" for x in kinds)
    (STYLE_DIRS[k] / SUB["textures"] / "README.md").write_text(f"""# Textures and colour looks ({style.name})

## Textures (`textures/`)

All tiles are 4096 x 4096 and seamless: they repeat in every direction with no visible join
(`astris-{k}-texture-seam-check.jpg` shows where the edges meet).

| File | What | How to use it |
|---|---|---|
| `textures/astris-texture-grain-fine-4096x4096.png` | Neutral film grain on mid-grey, fine | Lay over a picture or video, blend mode **Overlay**, 60 to 75 % opacity. |
| `textures/astris-texture-grain-medium-4096x4096.png` | The same, medium | Same. |
| `textures/astris-texture-grain-coarse-4096x4096.png` | The same, coarse | Same. Good for thumbnails. |
{rows}

The three neutral grain tiles are the same files in all three style folders.

For moving grain on video use the loops in `../{SUB['premiere']}/overlays/` instead: a still texture over video looks like a dirty window.

## Colour looks (`luts/`)

Three `.cube` files and how to load them in Premiere's Lumetri panel: see `luts/LUTS-README.md`.
""")


def build(style, *which):
    which = [w for w in which if w in ("textures", "luts")] or ["textures", "luts"]
    made = []
    if "luts" in which:
        made += luts(style)
    if "textures" in which:
        made += textures(style)
    readme(style)
    return made
