"""
The moving pieces of a style: three short intros, the animated title logo (on colour and transparent) and the end card.
All 3840 x 2160, 24 fps, sound baked in, plus each soundtrack as a WAV.

    A  POP   2 s   a slanted door opens on the style's colour, the logo pops in, the name rises under it
    B  TYPE  4 s   the name arrives (letter by letter / pushed on by a clapper stick / printed in two passes),
                   then the supporting line, then the logo
    C  SLOW  7 s   a slow push in: the film strip and the bar draw themselves, the name fades up, a warm chime

The motion is deliberately calm: smooth easing, real motion blur, no camera shake, no flashes, no rubbery bounces,
and every piece ends on a still, held lockup you can cut away from.

Usage: python3 code/build.py intros [--style red] [a b c title alpha end]     (no names = everything)
"""
import shutil

import numpy as np

from assets.sounds import Kit, mix_master, save as save_wav
from engine import lockup as L
from engine import sound as S
from engine import type as T
from engine.paths import out
from engine.style import config
from engine.video import FPS, H, W, Clip, ease_in_out, ease_out, ease_in_out_sine, keys, smooth, wipe

F = 1.0 / FPS
CX, CY = W / 2, H / 2


def door_role(style):
    """The colour of the opening panel: the style's dark (red, yellow) or a flood of the blue ink (risograph)."""
    return {"red": "second", "yellow": "ink", "wildcard": "ink"}[style.key]


def add_door(art, style):
    art.tag = "door"
    art.rect(-4, -4, W + 4, H + 4, role=door_role(style), size=900, crisp=True, shadow=False)
    art.tag = "main"


# ====================================================================================================
# A - POP
# ====================================================================================================
A_DUR = 2.0
A_DOOR = (0.0, 0.34)             # the slanted panel slides off
A_LOGO = (0.18, 0.66)            # the logo pops in
A_W1, A_W2 = (0.56, 0.98), (0.70, 1.10)


def intro_a(style):
    clip = Clip(style, A_DUR, seed=f"{style.key}-intro-a")
    L.vertical(clip.art, CX, CY, 780)
    add_door(clip.art, style)

    def animate(t):
        s = {"door": wipe("diag", 1 - smooth((t - A_DOOR[0]) / (A_DOOR[1] - A_DOOR[0])), 0.012)}     # slides off, edge parallel to the logo's slant
        k = ease_out((t - A_LOGO[0]) / (A_LOGO[1] - A_LOGO[0]), 5)
        s["logo"] = {"a": min(1.0, max(0.0, (t - A_LOGO[0]) / 0.12)), "s": 0.80 + 0.20 * k, "dy": 36 * (1 - k)}
        for tag, (t0, t1), kind in (("word1", A_W1, "up"), ("word2", A_W2, "right")):
            p = ease_out((t - t0) / (t1 - t0), 4)
            s[tag] = dict(wipe(kind, p, 0.05), dy=(24 * (1 - p) if kind == "up" else 0.0))
        return s
    clip.animate = animate
    return clip


def audio_a(style):
    kit = Kit(style)
    m = S.Mix(A_DUR)
    m.add(kit.bed(A_DUR, 1), 0.0, gain=0.05, send=0.0)
    m.add(kit.whoosh(0.42, seed=2), 0.0, gain=0.30, send=0.25)
    m.add(kit.hit(1.1, seed=4), A_LOGO[0] + 0.02, gain=0.85, send=0.3)
    m.add(S.sub_drop(0.8, 74, 40, 0.25, 0.45), A_LOGO[0] + 0.02, gain=0.26, send=0.0)
    m.add(kit.chime(dur=1.6), A_LOGO[0] + 0.06, gain=0.40, send=0.5)
    m.add(kit.tap(seed=5), A_W1[0] + 0.04, gain=0.45, pan=-0.15, send=0.25)
    m.add(kit.tick(seed=6, pitch=1.2), A_W2[0] + 0.04, gain=0.28, pan=0.2, send=0.25)
    return mix_master(m, tail=0.25, kit=kit)


# ====================================================================================================
# B - TYPE
# ====================================================================================================
B_DUR, B_TYPE0, B_TYPE1, B_TAG, B_LOGO = 4.0, 0.45, 1.85, 2.15, 2.65
B_LOGO_H, B_NAME_W = 660, 2500
B_LOGO_Y, B_NAME_Y = 730, 1450


def intro_b(style):
    clip = Clip(style, B_DUR, seed=f"{style.key}-intro-b")
    art, face = clip.art, style.display
    name = config()["brand"]["name_lowercase"]
    size = T.fit_size(name, face, B_NAME_W, L.TRACK_MAIN)
    art.tag = "logo"
    art.logo(CX, B_LOGO_Y, B_LOGO_H)
    mode = {"red": "typed", "yellow": "wiped", "wildcard": "printed"}[style.key]
    yb = B_NAME_Y + face.xh * size / 2
    x_left = CX - B_NAME_W / 2
    glyphs, _ = T.shape(name, face, size, L.TRACK_MAIN)
    letters = [(i, ch, gx) for i, (ch, _, gx) in enumerate(glyphs) if ch.strip()]
    if mode == "typed":
        for n, (i, ch, gx) in enumerate(letters):
            art.tag = f"ch{n:02d}"
            art.text(ch, x_left + gx, yb, size, anchor="ls")
    else:
        art.tag = "name"
        art.text(name, CX, yb, size, tracking=L.TRACK_MAIN, anchor="ms")
    art.tag = "tagline"
    art.text(style.tagline, CX, yb + size * 0.36, size * 0.20, tracking=L.TRACK_TAG, anchor="mt", shadow=False)
    if mode == "wiped":            # the clapper stick that pushes the wipe across
        art.tag = "stick"
        hgt = size * 1.5
        x0 = x_left - 60
        art.polygon([(x0, yb + hgt * 0.22), (x0 + 74, yb + hgt * 0.22), (x0 + 74 + hgt * 0.5, yb - hgt * 0.78), (x0 + hgt * 0.5, yb - hgt * 0.78)], crisp=False)
    nL = len(letters)
    step = (B_TYPE1 - 0.25 - B_TYPE0) / max(1, nL - 1)
    clip.letter_times = [B_TYPE0 + n * step for n in range(nL)]
    w0, w1 = B_TYPE0, B_TYPE1 - 0.25

    def animate(t):
        s = {}
        if mode == "typed":            # each letter rises into place and fades up, one after another
            for n, t0 in enumerate(clip.letter_times):
                k = ease_out((t - t0) / 0.30, 4)
                s[f"ch{n:02d}"] = {"a": min(1.0, max(0.0, (t - t0) / 0.10)), "dy": 30 * (1 - k)}
        elif mode == "wiped":          # the stick glides across and the name follows it
            p = smooth((t - w0) / (w1 - w0))
            s["name"] = wipe("right", p, 0.004)
            fade = min(1.0, max(0.0, (t - w0) / 0.12)) * (1 - smooth((t - (w1 - 0.04)) / 0.30))
            s["stick"] = {"a": fade, "dx": p * (B_NAME_W + 150) + 90 * smooth((t - w1) / 0.4)}
        else:                          # printed: the coral pass, then the blue pass over it
            s["name~"] = wipe("down", ease_in_out((t - w0) / 0.55), 0.035)
            s["name"] = wipe("down", ease_in_out((t - (w0 + 0.55)) / 0.55), 0.035)
        k = ease_out((t - B_TAG) / 0.45, 3)
        s["tagline"] = {"a": k, "dy": 16 * (1 - k)}
        k = ease_out((t - B_LOGO) / 0.70, 5)
        s["logo"] = {"a": min(1.0, max(0.0, (t - B_LOGO) / 0.20)), "s": 0.92 + 0.08 * k, "dy": 30 * (1 - k)}
        return s
    clip.animate = animate
    clip.mode = mode
    return clip


def audio_b(style, clip):
    kit = Kit(style)
    m = S.Mix(B_DUR)
    m.add(kit.bed(B_DUR, 11), 0.0, gain=0.06, send=0.0)
    m.add(kit.swell(0.45, 12), 0.0, gain=0.08, send=0.3)
    w0, w1 = B_TYPE0, B_TYPE1 - 0.25
    if clip.mode == "typed":
        r = np.random.default_rng(13)
        for n, t0 in enumerate(clip.letter_times):
            m.add(kit.tick(seed=20 + n, pitch=r.uniform(0.9, 1.15)), t0, gain=r.uniform(0.24, 0.34), pan=-0.5 + n / len(clip.letter_times), send=0.25)
        m.add(kit.tap(seed=14), clip.letter_times[-1] + 0.06, gain=0.30, send=0.25)          # the full stop
    elif clip.mode == "wiped":
        m.add(kit.whoosh(w1 - w0 + 0.1, seed=15), w0, gain=0.34, send=0.3)
        m.add(kit.tap(seed=16), w1, gain=0.40, send=0.3)
    else:
        for j, t0 in enumerate((w0, w0 + 0.55)):
            m.add(kit.hit(0.75 + 0.15 * j, seed=17 + j), t0 + 0.02, gain=0.48 + 0.12 * j, send=0.25)
            m.add(S.sos(S.noise(0.55, "pink", 19 + j), "bandpass", (700, 4200), 2) * np.sin(np.pi * np.linspace(0, 1, int(0.55 * S.SR))) ** 0.8,
                  t0, gain=0.08, pan=-0.2 + 0.4 * j, send=0.2)
    m.add(kit.tick(seed=30, pitch=1.3), B_TAG + 0.02, gain=0.22, send=0.3)
    m.add(kit.swell(0.4, 31), B_LOGO - 0.38, gain=0.10, send=0.3)
    m.add(kit.hit(0.85, seed=32), B_LOGO + 0.02, gain=0.55, send=0.3)
    m.add(kit.motif(1.5), B_LOGO + 0.06, gain=0.50, send=0.55)
    return mix_master(m, tail=0.3, kit=kit)


# ====================================================================================================
# C - SLOW
# ====================================================================================================
C_DUR = 7.0
C_STRIP, C_BAR, C_W1, C_W2, C_CHIME = (0.7, 2.4), (1.8, 3.5), (3.7, 4.7), (4.1, 5.1), 4.0
C_PUSH = 0.03                     # the whole picture grows by 3 % over the 7 seconds: a slow push in


def intro_c(style):
    clip = Clip(style, C_DUR, seed=f"{style.key}-intro-c")
    art = clip.art
    logo_h = 780
    probe = Clip(style, 1, seed="probe")
    box = L.vertical(probe.art, CX, CY, logo_h)                     # same placement as the vertical lockup
    top = box[1]
    for part, tag in (("film-strip", "strip"), ("bar", "bar")):     # the two halves are separate so each can draw on
        art.tag = tag
        art.logo(CX, top + logo_h / 2, logo_h, parts=[part])
    width = logo_h * style.logo.aspect
    s1, s2, track = L.stacked_sizes(style.display, width)
    words_h = style.display.cap * s1 * 1.20 + style.display.cap * s2
    L.stacked(art, CX, top + logo_h + 0.26 * logo_h + words_h / 2, width)

    def animate(t):
        cam = 1.0 + C_PUSH * ease_in_out_sine(t / C_DUR)
        base = {"s": cam, "cx": CX, "cy": CY}
        s = {"_": {"exposure": 0.93 + 0.07 * smooth(t / 1.4)}}
        s["strip"] = dict(base, **wipe("strip_up", ease_in_out_sine((t - C_STRIP[0]) / (C_STRIP[1] - C_STRIP[0])), 0.08))
        s["bar"] = dict(base, **wipe("bar_down", ease_in_out_sine((t - C_BAR[0]) / (C_BAR[1] - C_BAR[0])), 0.08))
        for tag, (t0, t1) in (("word1", C_W1), ("word2", C_W2)):
            k = ease_out((t - t0) / (t1 - t0), 3)
            s[tag] = dict(base, a=k, dy=22 * (1 - k))
        return s
    clip.animate = animate
    return clip


def audio_c(style):
    kit = Kit(style)
    m = S.Mix(C_DUR)
    m.add(kit.bed(C_DUR, 41), 0.0, gain=0.09, send=0.0)
    r = kit.root
    m.add(S.pad([S.midi(n) for n in (r - 12, r - 5, r)], 4.4, attack=2.4, release=1.6, cutoff=(200, 1300), level=1.0, seed=42), 0.4, gain=0.16, send=0.5)
    m.add(kit.whoosh(1.7, seed=43), C_STRIP[0], gain=0.09, send=0.4)
    m.add(kit.whoosh(1.7, seed=44, up=False), C_BAR[0], gain=0.09, send=0.4)
    m.add(kit.tick(seed=45, pitch=0.9), C_BAR[1] - 0.05, gain=0.18, send=0.4)
    m.add(kit.swell(0.6, 46), C_CHIME - 0.6, gain=0.11, send=0.4)
    m.add(kit.chord(3.0), C_CHIME, gain=0.26, send=0.6)
    m.add(kit.motif(3.0), C_CHIME, gain=0.75, send=0.6)
    m.add(kit.chime(kit.root + 24, 2.4), C_W2[0] + 0.3, gain=0.14, pan=0.25, send=0.6)
    return mix_master(m, tail=0.9, wet=0.75, ir=2.4, kit=kit)


# ====================================================================================================
# animated title logo (on colour, and transparent)
# ====================================================================================================
T_DUR, T_STRIP, T_BAR, T_HOLES, T_HOLE_STEP = 5.0, (0.25, 1.20), (0.45, 1.40), 1.45, 0.030
T_TRAVEL = 720


def title_logo(style, transparent=False):
    clip = Clip(style, T_DUR, seed=f"{style.key}-title", transparent=transparent)
    art, lg = clip.art, style.logo
    h = 1150
    cx, cy = CX, CY + 10
    art.tag = "strip"
    art.logo(cx, cy, h, parts=["film-strip"], solid=True)
    art.tag = "bar"
    art.logo(cx, cy, h, parts=["bar"])
    # the sprocket holes open one after another, bottom to top, the two columns taking turns
    polys = lg.polys(cx - h * lg.aspect / 2, cy - h / 2, h, ["film-strip"])[0][2]
    names = [q["name"] for q in lg.parts[0]["holes"]]
    left = sorted([i for i, n in enumerate(names) if "left" in n], key=lambda i: -polys[i][:, 1].mean())
    right = sorted([i for i, n in enumerate(names) if "right" in n], key=lambda i: -polys[i][:, 1].mean())
    order = []
    for j in range(max(len(left), len(right))):
        order += [left[j]] if j < len(left) else []
        order += [right[j]] if j < len(right) else []
    clip.hole_times = {}
    for n, i in enumerate(order):
        art.tag = f"hole{i:02d}"
        art.polygon(polys[i], role="field", crisp=True)
        clip.hole_times[f"hole{i:02d}"] = (T_HOLES + n * T_HOLE_STEP, float(polys[i][:, 0].mean() - cx) / (h * 0.6))
    up, down = np.array([0.4472, -0.8944]), np.array([0.4472, 0.8944])

    def animate(t):
        s = {}
        for tag, (t0, t1), axis in (("strip", T_STRIP, up), ("bar", T_BAR, down)):
            k = ease_out((t - t0) / (t1 - t0), 5)
            d = -axis * T_TRAVEL * (1 - k)            # each half glides in along its own slant
            s[tag] = {"a": min(1.0, max(0.0, (t - t0) / 0.16)), "dx": float(d[0]), "dy": float(d[1])}
        for tag, (t0, _) in clip.hole_times.items():
            s[tag] = {"a": min(1.0, max(0.0, (t - t0) / (2 * F)))}
        return s
    clip.animate = animate
    return clip


def audio_title(style, clip):
    kit = Kit(style)
    m = S.Mix(T_DUR)
    m.add(kit.bed(T_DUR, 51), 0.0, gain=0.05, send=0.0)
    m.add(kit.whoosh(0.8, seed=52), T_STRIP[0], gain=0.26, pan=-0.3, send=0.3)
    m.add(kit.whoosh(0.8, seed=53, up=False), T_BAR[0], gain=0.26, pan=0.3, send=0.3)
    m.add(kit.tap(seed=54), T_STRIP[0] + 0.55, gain=0.30, pan=-0.2, send=0.25)
    m.add(kit.hit(0.9, seed=55), T_BAR[0] + 0.55, gain=0.55, pan=0.1, send=0.3)
    for n, (tag, (t0, pan)) in enumerate(sorted(clip.hole_times.items(), key=lambda kv: kv[1][0])):
        m.add(kit.tick(seed=60 + n, pitch=0.85 + 0.018 * n), t0, gain=0.16, pan=float(np.clip(pan, -0.7, 0.7)), send=0.3)
    settle = T_HOLES + len(clip.hole_times) * T_HOLE_STEP + 0.1
    m.add(kit.swell(0.4, 56), settle - 0.4, gain=0.10, send=0.3)
    m.add(kit.chord(2.6), settle, gain=0.22, send=0.55)
    m.add(kit.motif(2.6), settle, gain=0.68, send=0.55)
    return mix_master(m, tail=0.5, wet=0.65, ir=2.0, kit=kit)


# ====================================================================================================
# end card: room for two video suggestions and the channel icon; loops seamlessly, and barely moves
# ====================================================================================================
E_DUR = 10.0
E_SLOT_W, E_SLOT_H = 1400, 788
E_SLOTS = [(CX - 110 - E_SLOT_W, 430), (CX + 110, 430)]
E_ICON = (CX, 1640, 190)


def end_card(style):
    clip = Clip(style, E_DUR, seed=f"{style.key}-end")
    art = clip.art
    line = config()["brand"]["end_card_line"]
    art.tag = "line"
    art.text(line, CX, 250, 150, tracking=L.TRACK_MAIN, anchor="mm")
    from engine.core import rounded_mask
    for j, (x, y) in enumerate(E_SLOTS):
        outer = rounded_mask(E_SLOT_H, E_SLOT_W, 44)
        inner = np.zeros_like(outer)
        inner[9:-9, 9:-9] = rounded_mask(E_SLOT_H - 18, E_SLOT_W - 18, 36)
        art.tag = f"slot{j}"
        art.add(outer - inner, x, y, size=300, shadow=False)
        art.tag = f"fill{j}"
        art.add(inner, x, y, size=300, alpha=0.10, shadow=False, wear=0)
    cx, cy, r = E_ICON
    art.tag = "ring"
    art.circle(cx, cy, r, ring=9, shadow=False)
    art.tag = "icon"
    from assets.youtube import logo_fit
    lx, ly, lh = logo_fit(style, 2 * r, fill=0.60)
    art.logo(cx - r + lx, cy - r + ly, lh)
    art.tag = "tag"
    art.text(style.tagline, CX, cy + r + 86, 54, tracking=L.TRACK_TAG, anchor="mm", shadow=False)

    def animate(t):
        w = 2 * np.pi * t / E_DUR                         # one slow cycle in ten seconds, so the loop has no seam
        s = {"fill0": {"a": 0.86 + 0.14 * np.sin(w)}, "fill1": {"a": 0.86 + 0.14 * np.sin(w + np.pi)}}
        float_y = 6.0 * np.sin(w)
        s["icon"] = {"dy": float_y}
        s["ring"] = {"dy": float_y}
        return s
    clip.animate = animate
    return clip


def audio_end(style):
    kit = Kit(style)
    m = S.Mix(E_DUR)
    r = kit.root
    m.add(kit.bed(E_DUR, 71), 0.0, gain=0.07, send=0.0)
    m.add(S.pad([S.midi(n) for n in (r - 12, r - 5, r, r + 4, r + 7)], E_DUR, attack=1.6, release=3.2, cutoff=(220, 1500), level=1.0, seed=72), 0.0, gain=0.24, send=0.55)
    m.add(kit.motif(3.0), 0.5, gain=0.42, send=0.6)
    m.add(kit.chime(r + 19, 2.6), 3.6, gain=0.14, pan=-0.3, send=0.6)
    m.add(kit.motif(3.0, octave=-12), 5.5, gain=0.26, send=0.6)
    m.add(kit.chime(r + 24, 2.4), 7.4, gain=0.10, pan=0.3, send=0.6)
    mix = mix_master(m, tail=2.2, wet=0.8, ir=2.6, kit=kit)
    n = int(0.6 * S.SR)
    mix[:, :n] *= np.linspace(0, 1, n) ** 1.5
    return mix


# ====================================================================================================
PIECES = ["a", "b", "c", "title", "alpha", "end"]
KEY_TIMES = {"a": [0.0, 0.12, 0.22, 0.34, 0.62, 0.80, 1.95], "b": [0.5, 0.9, 1.3, 1.75, 2.3, 2.85, 3.95],
             "c": [0.4, 1.4, 2.2, 3.0, 3.9, 4.6, 6.95], "title": [0.3, 0.5, 0.8, 1.2, 1.6, 2.0, 4.95], "end": [0.0, 2.5, 5.0, 7.5]}


def test_sheet(style, which=("a", "b", "c", "title", "end")):
    """Small contact sheet of key frames (for checking before a full render)."""
    import cv2
    from PIL import Image
    rows = []
    for w in which:
        clip = {"a": intro_a, "b": intro_b, "c": intro_c, "title": title_logo, "end": end_card}[w](style)
        tiles = [cv2.resize(clip.frame(min(int(round(tt * FPS)), clip.n - 1)), (640, 360), interpolation=cv2.INTER_AREA) for tt in KEY_TIMES[w]]
        while len(tiles) < 7:
            tiles.append(np.zeros((360, 640, 3), np.uint8))
        rows.append(np.concatenate(tiles, 1))
    return Image.fromarray(np.concatenate(rows, 0))


def build(style, *which):
    k = style.key
    which = [w for w in which if w in PIECES] or PIECES
    vdir, sdir = out(k, "video"), out(k, "sound", "stingers")
    made = []

    def emit(name, clip, mix, prores=False):
        wav = save_wav(vdir / f"{name}.wav", mix)
        shutil.copyfile(wav, sdir / f"{name.replace('-4k24', '')}.wav")
        if prores:
            clip.render_prores(vdir / f"{name}-prores4444.mov", wav)
        else:
            clip.render_h264(vdir / f"{name}.mp4", wav)
        made.append(name)

    if "a" in which:
        emit(f"astris-{k}-intro-a-pop-2s-4k24", intro_a(style), audio_a(style))
    if "b" in which:
        c = intro_b(style)
        emit(f"astris-{k}-intro-b-type-4s-4k24", c, audio_b(style, c))
    if "c" in which:
        emit(f"astris-{k}-intro-c-slow-7s-4k24", intro_c(style), audio_c(style))
    if "title" in which:
        c = title_logo(style)
        emit(f"astris-{k}-title-logo-5s-4k24", c, audio_title(style, c))
    if "alpha" in which:
        c = title_logo(style, transparent=True)
        emit(f"astris-{k}-title-logo-alpha-5s-4k24", c, audio_title(style, c), prores=True)
    if "end" in which:
        emit(f"astris-{k}-end-card-10s-4k24", end_card(style), audio_end(style))
    return made
