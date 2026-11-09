"""
ASTRIS PRODUCTIONS - Ident 04: THE SLOW FLY-THROUGH (9.0 s, slow and graceful)

Real 3D (three.js, see ident04_scene.html). Giant champagne-gold letters - ASTRIS in Playfair Display Black -
and the logo float in a midnight-teal void full of drifting dust. The camera glides behind the letters, threads
the gap between R and I, skims past T, S and A, rises past the logo, then breathes and pulls slowly back into
one elegant final lockup. True depth of field follows the camera's focus; the motes become bokeh.
Sound: a warm swelling pad, soft deep bass, air as we pass through the gaps, a delicate chime on the reveal.
"""
import math

import numpy as np

import common as C
import ident04_geometry
import kit as K
import sfx as X
import sound as S

NAME = "astris-ident-04"
DUR = 9.0
SCENE = "ident04_scene.html"
POST = C.Post(seed=404, grain=0.02, vignette=0.40)
T_GAP, T_RISE, T_REVEAL = 2.4, 4.4, 7.9


def composite(item):
    i, info, raw = item
    rgb, _ = K.rgba_from(raw)
    img = rgb * np.array([0.98, 1.0, 1.02], np.float32)          # a hair of teal in the grade
    return POST.finish(img, i, bloom=0.5, threshold=0.62)


def audio():
    m = S.Mix(DUR)
    fmaj9 = [S.midi(41), S.midi(48), S.midi(53), S.midi(57), S.midi(64), S.midi(67)]
    m.add(S.pad(fmaj9, DUR, attack=3.2, release=1.6, cutoff=(260, 2400), level=1.0, seed=401), 0.0, gain=0.42, send=0.55)
    m.add(X.strings([S.midi(65), S.midi(69), S.midi(72), S.midi(76)], DUR - 2.0, attack=2.5, release=1.8, seed=402, bright=0.7),
          2.0, gain=0.16, send=0.6)
    sub = np.sin(2 * np.pi * S.midi(29) * S.tt(DUR)) * np.clip(S.tt(DUR) / 3.0, 0, 1) * np.clip((DUR - S.tt(DUR)) / 1.8, 0, 1)
    m.add(sub * 0.9, 0.0, gain=0.35, send=0.0)
    m.add(S.whoosh(2.2, peak=0.55, f_lo=150, f_hi=1800, q=0.8, pan_from=0.7, pan_to=-0.7, seed=403), T_GAP - 1.2, gain=0.22, send=0.35)
    m.add(S.whoosh(2.0, peak=0.5, f_lo=150, f_hi=2200, q=0.8, pan_from=-0.4, pan_to=0.4, seed=404), T_RISE - 1.0, gain=0.18, send=0.35)
    m.add(S.whoosh(3.0, peak=0.45, f_lo=120, f_hi=1200, q=0.7, pan_from=0, pan_to=0, seed=405), 5.0, gain=0.14, send=0.4)
    for k, (f, dt, pan) in enumerate(((S.midi(84), 0.0, -0.2), (S.midi(91), 0.07, 0.25), (S.midi(88), 0.16, 0.05))):
        m.add(X.glass_ping(f, 2.6), T_REVEAL + dt, gain=0.11, pan=pan, send=0.65)
    m.add(S.shimmer(2.2, root=S.midi(96), density=14, seed=406, rise=0.4), T_REVEAL, gain=0.07, send=0.7)
    mix = m.master(ir_seconds=3.4, wet=1.0, peak_db=-1.5, tail_fade=0.2)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    if not (C.ROOT / "ident04_geometry.json").exists():
        ident04_geometry.build()
    K.run3d(NAME, DUR, SCENE, composite, audio, [0, 24, 48, 60, 72, 96, 120, 144, 168, 190, 215], tag="ident04")
