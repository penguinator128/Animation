"""Where everything lives. All paths are relative to the kit folder, so the kit can be moved or pushed anywhere."""
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
CODE = KIT / "code"
FONTS = CODE / "fonts"
WORK = CODE / "_work"                     # scratch + caches (git-ignored)
ORIGINALS = KIT / "00_Originals"
LOGO_PACK = KIT / "01_Logo-Pack-Bare-Bones"
STYLE_DIRS = {"red": KIT / "02_Style-1-Red", "yellow": KIT / "03_Style-2-Yellow", "wildcard": KIT / "04_Style-3-Wildcard"}
SUB = {"guide": "01_Brand-Guide", "logos": "02_Logos", "social": "03_YouTube-and-Social", "video": "04_Intros-and-Video",
       "premiere": "05_Premiere-Assets", "sound": "06_Sound", "merch": "07_Merch", "paper": "08_Film-and-Paperwork",
       "web": "09_Website", "textures": "10_Textures-and-LUTs"}


def out(style, sub, *parts):
    """Folder (created) for a style's sub-section, e.g. out('red', 'social', 'banner')."""
    p = STYLE_DIRS[style] / SUB[sub]
    for part in parts:
        p = p / part
    p.mkdir(parents=True, exist_ok=True)
    return p
