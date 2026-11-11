"""
Contact sheets: overview.png for a style (everything at a glance) and compare-styles.png at the top of the kit
(the same pieces in all three styles, side by side). Build these last.

Usage: python3 code/build.py overview [--style red]      (compare-styles.png is rebuilt every time)
"""
import subprocess

import numpy as np
from PIL import Image

from engine import lockup as L
from engine.core import Art
from engine.paths import KIT, STYLE_DIRS, SUB
from engine.style import STYLES, Style


def load(path, t=None):
    path = str(path)
    if path.endswith((".mp4", ".mov")):
        w = 1280
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t or 0:.3f}", "-i", path, "-frames:v", "1", "-vf", f"scale={w}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(len(raw) // (w * 3), w, 3))
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (236, 232, 226, 255))
        bg.alpha_composite(im)
        im = bg.convert("RGB")
    return im


def row(images, width, gap):
    """Scale a list of images to one shared height so that together they fill `width` exactly."""
    ratios = [im.width / im.height for im in images]
    h = (width - gap * (len(images) - 1)) / sum(ratios)
    out, x = [], 0.0
    for im, r in zip(images, ratios):
        w = int(round(h * r))
        out.append((im.resize((w, int(round(h))), Image.LANCZOS), int(round(x))))
        x += h * r + gap
    return out, int(round(h))


def pieces(k):
    """The rows of a style's overview: lists of (path, time) pictures."""
    b = STYLE_DIRS[k]
    so, vi, pa, me, pr, we, gu = (b / SUB[x] for x in ("social", "video", "paper", "merch", "premiere", "web", "guide"))
    posters = sorted((pa / "posters").glob("*-a3-*.jpg"))
    hl = sorted((so / "instagram-highlight-covers").glob("*.png"))
    posts = sorted((so / "instagram-posts").glob("*.png"))
    stories = sorted((so / "instagram-stories").glob("*.png"))
    thumbs = sorted((so / "thumbnails").glob("*.jpg"))
    pages = sorted((gu / "pages").glob("*.png"))
    return [
        [(so / "banner" / f"astris-{k}-banner-a-2560x1440.png", None), (so / "profile" / f"astris-{k}-profile-800x800.png", None), (so / "banner" / f"astris-{k}-banner-d-2560x1440.png", None)],
        [(vi / f"astris-{k}-intro-a-pop-2s-4k24.mp4", 1.9), (vi / f"astris-{k}-intro-b-type-4s-4k24.mp4", 3.9), (vi / f"astris-{k}-title-logo-5s-4k24.mp4", 4.9), (vi / f"astris-{k}-end-card-10s-4k24.mp4", 5.0)],
        [(p, None) for p in posters[:4]] + [(me / "stickers" / f"astris-{k}-sticker-sheet-a4-2480x3508.png", None)],
        [(me / "mock-ups" / f"astris-{k}-mockup-tshirt-illustration.jpg", None), (me / "mock-ups" / f"astris-{k}-mockup-cap-illustration.jpg", None),
         (me / "mock-ups" / f"astris-{k}-mockup-tote-illustration.jpg", None)],
        [(t, None) for t in thumbs[:3]] + [(pa / "business-card" / f"astris-{k}-business-card-preview.jpg", None)],
        [(h, None) for h in hl[:6]] + [(posts[0], None), (posts[3], None), (stories[1], None)],
        [(pa / "clapperboard" / f"astris-{k}-clapperboard-on-colour-3840x2160.png", None), (pa / "presents-card" / f"astris-{k}-presents-card-dark-3840x2160.png", None),
         (we / f"astris-{k}-website-hero-desktop-mockup.jpg", None)],
        [(pages[i], None) for i in (0, 4, 7)] + [(me / "mock-ups" / f"astris-{k}-mockup-hoodie-{ {'red': 'black', 'yellow': 'black', 'wildcard': 'blue'}[k]}-illustration.jpg", None)],
    ]


def sheet(rows, width, gap, header=None, back=(24, 23, 22)):
    laid = [row([load(p, t) for p, t in r], width - 2 * gap, gap) for r in rows]
    H = sum(h for _, h in laid) + gap * (len(laid) + 1) + (header.height if header else 0)
    out = Image.new("RGB", (width, H), back)
    y = gap
    if header:
        out.paste(header, (0, 0))
        y = header.height + gap
    for tiles, h in laid:
        for im, x in tiles:
            out.paste(im, (gap + x, y))
        y += h + gap
    return out


def header(style, width, height=300, text=None):
    art = Art(style, width, height, scale=1.0, seed=f"{style.key}-overview-head")
    L.horizontal(art, 330, height / 2, 150)
    art.tag = "main"
    art.text(text or f"style {style.number}: {style.name.lower()}.   {style.tagline}", width - 80, height / 2, 46, tracking=L.TRACK_TAG, anchor="rm", shadow=False)
    return Image.fromarray((np.clip(art.render(), 0, 1) * 255 + 0.5).astype(np.uint8))


def compare():
    """The same pieces in each style, one style per row."""
    width, gap = 3000, 14
    rows = []
    for k in STYLES:
        b = STYLE_DIRS[k]
        posters = sorted((b / SUB["paper"] / "posters").glob("*-a3-*.jpg"))
        rows.append([(b / SUB["social"] / "banner" / f"astris-{k}-banner-a-2560x1440.png", None), (b / SUB["social"] / "profile" / f"astris-{k}-profile-800x800.png", None),
                     (posters[0], None), (b / SUB["merch"] / "mock-ups" / f"astris-{k}-mockup-tshirt-illustration.jpg", None)])
        rows.append([(b / SUB["video"] / f"astris-{k}-intro-b-type-4s-4k24.mp4", 3.9), (b / SUB["paper"] / "business-card" / f"astris-{k}-business-card-preview.jpg", None),
                     (b / SUB["merch"] / "stickers" / f"astris-{k}-sticker-sheet-a4-2480x3508.png", None), (b / SUB["web"] / f"astris-{k}-website-hero-desktop-mockup.jpg", None)])
    out = sheet(rows, width, gap)
    p = KIT / "compare-styles.png"
    out.save(p, optimize=True)
    return p


def build(style):
    k = style.key
    width, gap = 2600, 14
    out = sheet(pieces(k), width, gap, header(style, width))
    p = STYLE_DIRS[k] / "overview.png"
    out.save(p, optimize=True)
    made = [f"overview.png  {out.width} x {out.height}, {p.stat().st_size / 1e6:.1f} MB"]
    if k == STYLES[-1] or all((STYLE_DIRS[s] / "overview.png").exists() for s in STYLES):
        c = compare()
        made.append(f"compare-styles.png  {c.stat().st_size / 1e6:.1f} MB")
    return made
