"""Geometry for ident 04 (the fly-through): the logo plus ASTRIS in Playfair Display Black and PRODUCTIONS in
Cormorant Garamond, laid out as a lockup and exported in logo units (y up) for ident04_scene.html."""
import json

import common as C
import geometry3d as G
import kit as K

OUT = C.ROOT / "ident04_geometry.json"


def build():
    logo = C.Logo()
    lock = K.Lockup2(logo, logo_h=800, lines=[("playfair-display-900", "ASTRIS", 210, 0.34, None),
                                              ("cormorant-garamond-600", "PRODUCTIONS", 62, 0.0, 1.0)],
                     gaps=(150, 80), centre=(C.W / 2, C.H / 2 - 10))
    pieces, _ = G.logo_pieces(logo)
    text = G.lockup2_text(lock, lock.logo_c, lock.logo_h)
    data = {"pieces": pieces, "text": text, "logo_c": list(map(float, lock.logo_c)), "logo_h": lock.logo_h}
    OUT.write_text(json.dumps(data))
    a = text["astris"]
    print(f"[ident04] {len(a)} + {len(text['prod'])} letters; ASTRIS spans x {a[0]['bbox'][0]:.3f}..{a[-1]['bbox'][2]:.3f}, "
          f"baseline {a[0]['base']:.3f}, cap {a[0]['bbox'][3] - a[0]['bbox'][1]:.3f}; logo centre at y=835? {lock.logo_c}")
    return data


if __name__ == "__main__":
    build()
