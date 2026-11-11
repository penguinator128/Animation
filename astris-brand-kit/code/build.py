#!/usr/bin/env python3
"""
ASTRIS brand kit builder. Everything in the three style folders is made by this script from brand-config.json.

    python3 code/build.py <step> [--style red|yellow|wildcard|all]
    python3 code/build.py list                 # show the steps

See code/README.md for what each step makes.
"""
import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine.style import STYLES, Style        # noqa: E402

STEPS = {
    "youtube": ("assets.youtube", "banners A-D (+ masters), safe-area guide, device previews, profile pictures"),
    "logos": ("assets.logos", "logo files in the style's colours, lockups, animation-ready layers"),
    "social": ("assets.social", "thumbnail templates, Instagram highlight covers, posts and stories"),
    "posters": ("assets.posters", "one poster per film in films.txt, A3 and 2:3"),
    "stickers": ("assets.stickers", "sticker designs with cut lines + A4 sheet"),
    "paper": ("assets.paperwork", "business card, email signature, press kit, letterhead, invoice"),
    "film": ("assets.film", "clapperboard (stills + 3 s clap) and the 'presents' card (stills + 3 s animation)"),
    "merch": ("assets.merch", "cap, hoodie, t-shirt, tote, bottle, wallpapers and mock-ups"),
    "web": ("assets.website", "favicons, social sharing image, hero mock-ups, tokens, preview page"),
    "textures": ("assets.textures", "seamless grain and paper tiles, .cube colour looks"),
    "sound": ("assets.sounds", "the style's sound pack"),
    "intros": ("assets.intros", "the three short intros, animated title logo and end card"),
    "premiere": ("assets.premiere", "corner bug, lower thirds, overlay loops"),
    "guide": ("assets.guide", "brand guide PDF + page PNGs"),
    "overview": ("assets.overview", "contact sheet of the whole style"),
}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("list", "-h", "--help"):
        print(__doc__)
        for k, (_, what) in STEPS.items():
            print(f"  {k:10s} {what}")
        return
    step = args[0]
    which = STYLES
    if "--style" in args:
        v = args[args.index("--style") + 1]
        which = STYLES if v == "all" else [v]
    extra = [a for a in args[1:] if a not in ("--style",) and a not in which and a != "all"]
    mod = importlib.import_module(STEPS[step][0])
    for key in which:
        t0 = time.time()
        res = mod.build(Style(key), *extra) if extra else mod.build(Style(key))
        print(f"[{step}] {key}: done in {time.time() - t0:.0f}s")
        for line in res or []:
            print("   ", line)


if __name__ == "__main__":
    main()
