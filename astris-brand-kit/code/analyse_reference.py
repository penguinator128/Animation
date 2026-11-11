#!/usr/bin/env python3
"""
Measure a style reference picture, so a style can be matched by numbers rather than by eye.

    python3 code/analyse_reference.py                      # looks for 00_Originals/reference-style.png (or .jpg)
    python3 code/analyse_reference.py path/to/picture.png

It reads STYLE and APPROACH only: the colours, how much of the picture is empty field, where the one focal point
sits, and how strong the grain is. It never copies the picture's words, name, face or photo.
It writes 00_Originals/reference-findings.md and 00_Originals/reference-analysis.png.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KIT = Path(__file__).resolve().parent.parent
ORIG = KIT / "00_Originals"


def find():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    for name in ("reference-style.png", "reference-style.jpg", "reference-style.jpeg", "reference-style.webp"):
        if (ORIG / name).exists():
            return ORIG / name
    return None


def hexof(c):
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in c)


def analyse(path):
    img = np.asarray(Image.open(path).convert("RGB"))
    h, w = img.shape[:2]
    sc = 1200 / max(h, w)
    small = cv2.resize(img, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA) if sc < 1 else img
    px = cv2.GaussianBlur(small, (0, 0), 2).reshape(-1, 3).astype(np.float32)
    # the picture's few colours
    _, labels, centres = cv2.kmeans(px, 5, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 4, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=5)
    order = np.argsort(-counts)
    colours = [(hexof(centres[i]), counts[i] / counts.sum()) for i in order]
    field = labels.reshape(small.shape[:2]) == order[0]
    # grain: what is left of the field once the smooth picture is taken away
    grey = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32)
    hp = grey - cv2.GaussianBlur(grey, (0, 0), 3)
    inner = cv2.erode(field.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    grain = float(hp[inner].std() / 255 * 100) if inner.sum() > 500 else float("nan")
    # the focal point: everything that is not field
    ys, xs = np.nonzero(~field)
    box = (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else (0, 0, 0, 0)
    cx, cy = (xs.mean() / small.shape[1], ys.mean() / small.shape[0]) if len(xs) else (0.5, 0.5)
    return dict(size=(w, h), colours=colours, field_share=float(field.mean()), grain=grain, centre=(float(cx), float(cy)),
                box=tuple(int(v / sc) if sc < 1 else int(v) for v in box), small=small, sbox=box)


def write(path, r):
    sm = r["small"].copy()
    x0, y0, x1, y1 = r["sbox"]
    cv2.rectangle(sm, (int(x0), int(y0)), (int(x1), int(y1)), (255, 255, 255), 2)
    cv2.drawMarker(sm, (int(r["centre"][0] * sm.shape[1]), int(r["centre"][1] * sm.shape[0])), (255, 255, 255), cv2.MARKER_CROSS, 40, 2)
    sw = np.zeros((90, sm.shape[1], 3), np.uint8)
    x = 0
    for hx, share in r["colours"]:
        wpx = int(round(share * sm.shape[1]))
        sw[:, x:x + wpx] = [int(hx[i:i + 2], 16) for i in (1, 3, 5)]
        x += wpx
    Image.fromarray(np.concatenate([sm, sw], 0)).save(ORIG / "reference-analysis.png")
    lines = ["# What the style reference shows", "", f"Measured from `{path.name}` ({r['size'][0]} x {r['size'][1]} px) by `code/analyse_reference.py`.",
             "Only style and approach are read. Nothing of the picture's words, name, face or photo is used anywhere in the kit.", "",
             "## Colours (largest first)", "", "| Colour | Share of the picture |", "|---|---|"]
    lines += [f"| `{hx}` | {share * 100:.0f} % |" for hx, share in r["colours"]]
    lines += ["", f"The first one is the field. It covers {r['field_share'] * 100:.0f} % of the picture, so that is how much breathing room the layout has.", "",
              "## Layout", "", f"- The focal point is centred at {r['centre'][0] * 100:.0f} % across and {r['centre'][1] * 100:.0f} % down.",
              f"- Everything that is not field sits inside the box {r['box']} (left, top, right, bottom, in pixels).", "",
              "## Grain", "", f"- Fine detail left on the flat field: about {r['grain']:.1f} % (standard deviation of brightness).",
              "  The kit's styles use about 5 to 7.5 % measured the same way.", "", "`reference-analysis.png` shows the box, the centre mark and the colour strip.", ""]
    (ORIG / "reference-findings.md").write_text("\n".join(lines))


def main():
    path = find()
    if not path or not path.exists():
        print("No style reference found.\n"
              "Put the picture at 00_Originals/reference-style.png and run this again.\n"
              "Until then the red style follows the written brief: field about #C23A3A, lettering about #F4E3DA, dark #1A1210,\n"
              "one centred focal point, fine even grain of roughly 6 to 10 %.")
        return
    r = analyse(path)
    write(path, r)
    print(f"field {r['colours'][0][0]} covers {r['field_share'] * 100:.0f} %, grain {r['grain']:.1f} %, focal point at "
          f"{r['centre'][0] * 100:.0f} % / {r['centre'][1] * 100:.0f} %. Written to 00_Originals/reference-findings.md")


if __name__ == "__main__":
    main()
