"""
The moving pieces of a style: three short intros, the animated title logo (on colour and transparent) and the end card.
All 3840 x 2160, 24 fps, sound baked in, plus each soundtrack as a WAV.

    A  POP   2 s   the field snaps in, the logo stamps on, the name lands under it
    B  TYPE  4 s   the name reveals (typed / wiped / printed, by style), then the supporting line, then the logo
    C  SLOW  7 s   the grain breathes, the logo draws itself, the name fades up, a warm chime rings out

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
from engine.video import FPS, H, W, Clip, ease_in_out, ease_out, ease_out_back, keys

F = 1.0 / FPS
CX, CY = W / 2, H / 2


def on(t, t0):
    return 1.0 if t >= t0 else 0.0


# ====================================================================================================
# A - POP
# ====================================================================================================
A_FIELD, A_STAMP, A_TEXT, A_DUR = 2 * F, 10 * F, 21 * F, 2.0


def intro_a(style):
    clip = Clip(style, A_DUR, seed=f"{style.key}-intro-a")
    L.vertical(clip.art, CX, CY, 780)

    def animate(t):
        s = {"_": {"black": 1.0 if t < A_FIELD else 0.0, "exposure": keys(t, [(A_FIELD, 1.18), (A_FIELD + 3 * F, 1.0)]),
                   "shake": (0, keys(t, [(A_STAMP + 1 * F, 0), (A_STAMP + 2 * F, 10), (A_STAMP + 3 * F, -4), (A_STAMP + 4 * F, 0)]))}}
        s["logo"] = {"a": 0.0} if t < A_STAMP else {
            "a": keys(t, [(A_STAMP, 0.6), (A_STAMP + F, 1.0)]),
            "s": keys(t, [(A_STAMP, 1.34), (A_STAMP + F, 1.10), (A_STAMP + 2 * F, 0.962), (A_STAMP + 3 * F, 1.014), (A_STAMP + 4 * F, 1.0)])}
        for tag, t0 in (("word1", A_TEXT), ("word2", A_TEXT + 2 * F)):
            s[tag] = {"a": 0.0} if t < t0 else {"a": keys(t, [(t0, 0.6), (t0 + F, 1.0)]),
                                                 "dy": keys(t, [(t0, -70), (t0 + F, 12), (t0 + 2 * F, -5), (t0 + 3 * F, 0)])}
        return s
    clip.animate = animate
    return clip


def audio_a(style):
    kit = Kit(style)
    m = S.Mix(A_DUR)
    m.add(kit.bed(A_DUR, 1), 0.0, gain=0.05, send=0.0)
    m.add(kit.tick(seed=2, pitch=0.8), A_FIELD, gain=0.5, send=0.2)
    m.add(kit.swell(0.3, 3), max(0.0, A_STAMP - 0.3), gain=0.16, send=0.2)
    m.add(kit.hit(1.25, seed=4), A_STAMP, gain=1.0, send=0.3)
    m.add(S.sub_drop(0.9, 78, 40, 0.25, 0.5), A_STAMP, gain=0.35, send=0.0)
    m.add(kit.tap(seed=5), A_TEXT, gain=0.55, pan=-0.15, send=0.25)
    m.add(kit.tick(seed=6, pitch=1.2), A_TEXT + 2 * F, gain=0.35, pan=0.2, send=0.25)
    m.add(kit.chime(dur=1.5), A_STAMP + 0.04, gain=0.42, send=0.5)
    return mix_master(m, tail=0.22, kit=kit)


# ====================================================================================================
# B - TYPE
# ====================================================================================================
B_DUR, B_TYPE0, B_TYPE1, B_TAG, B_LOGO = 4.0, 0.55, 1.85, 2.2, 2.8
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
    step = (B_TYPE1 - B_TYPE0) / nL
    clip.letter_times = [B_TYPE0 + n * step for n in range(nL)]

    def animate(t):
        s = {"_": {"exposure": keys(t, [(0, 1.10), (0.5, 1.0)]), "grain": keys(t, [(0, 1.7), (0.5, 1.0)])}}
        if mode == "typed":
            for n, t0 in enumerate(clip.letter_times):
                s[f"ch{n:02d}"] = {"a": 0.0} if t < t0 else {"s": keys(t, [(t0, 1.22), (t0 + 2 * F, 0.975), (t0 + 3 * F, 1.0)])}
        elif mode == "wiped":
            p = ease_in_out((t - B_TYPE0) / (B_TYPE1 - 0.35 - B_TYPE0))
            s["name"] = {"wipe": ("right", p, 0.004)} if p < 1 else {}
            if p <= 0:
                s["name"] = {"a": 0.0}
            s["stick"] = {"a": 1.0 if 0 < p < 1 else 0.0, "dx": p * (B_NAME_W + 150)}
        else:   # printed: second colour first, then the main ink over it
            p1 = ease_in_out((t - B_TYPE0) / 0.42)
            p2 = ease_in_out((t - (B_TYPE0 + 0.62)) / 0.42)
            s["name~"] = {"wipe": ("down", p1, 0.03)} if 0 < p1 < 1 else ({"a": 0.0} if p1 <= 0 else {})
            s["name"] = {"wipe": ("down", p2, 0.03)} if 0 < p2 < 1 else ({"a": 0.0} if p2 <= 0 else {})
        s["tagline"] = {"a": ease_out((t - B_TAG) / (6 * F)), "dy": 14 * (1 - ease_out((t - B_TAG) / (6 * F)))}
        k = (t - B_LOGO) / (8 * F)
        s["logo"] = {"a": 0.0} if t < B_LOGO else {"a": min(1.0, k * 2.5), "s": 0.86 + 0.14 * ease_out_back(k)}
        return s
    clip.animate = animate
    clip.mode = mode
    return clip


def audio_b(style, clip):
    kit = Kit(style)
    m = S.Mix(B_DUR)
    m.add(kit.bed(B_DUR, 11), 0.0, gain=0.06, send=0.0)
    m.add(kit.swell(0.5, 12), 0.0, gain=0.10, send=0.3)
    if clip.mode == "typed":
        r = np.random.default_rng(13)
        for n, t0 in enumerate(clip.letter_times):
            m.add(kit.tick(seed=20 + n, pitch=r.uniform(0.85, 1.2)), t0, gain=r.uniform(0.32, 0.46), pan=-0.5 + n / len(clip.letter_times), send=0.2)
        m.add(kit.tap(seed=14), B_TYPE1 + 0.02, gain=0.35, send=0.25)          # the full stop
    elif clip.mode == "wiped":
        m.add(kit.whoosh(B_TYPE1 - 0.35 - B_TYPE0, seed=15), B_TYPE0, gain=0.4, send=0.3)
        m.add(kit.hit(0.9, seed=16), B_TYPE1 - 0.35, gain=0.7, send=0.3)         # the stick claps home
    else:
        for j, t0 in enumerate((B_TYPE0, B_TYPE0 + 0.62)):
            m.add(kit.hit(0.85 + 0.15 * j, seed=17 + j), t0, gain=0.6 + 0.15 * j, send=0.25)
            m.add(S.sos(S.noise(0.42, "pink", 19 + j), "bandpass", (700, 4200), 2) * np.sin(np.pi * np.linspace(0, 1, int(0.42 * S.SR))) ** 0.8,
                  t0, gain=0.10, pan=-0.2 + 0.4 * j, send=0.2)
    m.add(kit.tick(seed=30, pitch=1.3), B_TAG, gain=0.3, send=0.3)
    m.add(kit.swell(0.35, 31), B_LOGO - 0.35, gain=0.13, send=0.3)
    m.add(kit.hit(1.0, seed=32), B_LOGO + F, gain=0.75, send=0.3)
    m.add(kit.motif(1.6), B_LOGO + 0.03, gain=0.5, send=0.55)
    return mix_master(m, tail=0.3, kit=kit)


# ====================================================================================================
# C - SLOW
# ====================================================================================================
C_DUR = 7.0
C_STRIP, C_BAR, C_W1, C_W2, C_CHIME = (0.8, 2.4), (1.9, 3.4), (3.7, 4.5), (4.1, 4.9), 4.0


def intro_c(style):
    clip = Clip(style, C_DUR, seed=f"{style.key}-intro-c")
    art = clip.art
    lg = style.logo
    logo_h = 780
    # same placement as the vertical lockup, but the two halves of the logo are separate so each can draw on
    probe = Clip(style, 1, seed="probe")
    box = L.vertical(probe.art, CX, CY, logo_h)
    top = box[1]
    for part, tag in (("film-strip", "strip"), ("bar", "bar")):
        art.tag = tag
        art.logo(CX, top + logo_h / 2, logo_h, parts=[part])
    width = logo_h * lg.aspect
    s1, s2, track = L.stacked_sizes(style.display, width)
    words_h = style.display.cap * s1 * 1.20 + style.display.cap * s2
    L.stacked(art, CX, top + logo_h + 0.26 * logo_h + words_h / 2, width)

    def animate(t):
        breathe = 1.0 + 0.26 * np.sin(2 * np.pi * t / 3.5)
        s = {"_": {"grain": float(breathe), "exposure": keys(t, [(0, 0.90), (1.0, 1.0)])}}
        p = ease_in_out((t - C_STRIP[0]) / (C_STRIP[1] - C_STRIP[0]))
        s["strip"] = {"a": 0.0} if p <= 0 else ({"wipe": ("strip_up", p, 0.07)} if p < 1 else {})
        p = ease_in_out((t - C_BAR[0]) / (C_BAR[1] - C_BAR[0]))
        s["bar"] = {"a": 0.0} if p <= 0 else ({"wipe": ("bar_down", p, 0.07)} if p < 1 else {})
        for tag, (t0, t1) in (("word1", C_W1), ("word2", C_W2)):
            k = ease_out((t - t0) / (t1 - t0), 2)
            s[tag] = {"a": k, "dy": 22 * (1 - k)}
        return s
    clip.animate = animate
    return clip


def audio_c(style):
    kit = Kit(style)
    m = S.Mix(C_DUR)
    m.add(kit.bed(C_DUR, 41), 0.0, gain=0.09, send=0.0)
    r = kit.root
    m.add(S.pad([S.midi(n) for n in (r - 12, r - 5, r)], 4.4, attack=2.4, release=1.6, cutoff=(200, 1300), level=1.0, seed=42), 0.5, gain=0.16, send=0.5)
    m.add(kit.whoosh(1.6, seed=43), C_STRIP[0], gain=0.10, send=0.4)
    m.add(kit.whoosh(1.5, seed=44, up=False), C_BAR[0], gain=0.10, send=0.4)
    m.add(kit.tick(seed=45, pitch=0.9), C_BAR[1], gain=0.22, send=0.4)
    m.add(kit.swell(0.6, 46), C_CHIME - 0.6, gain=0.12, send=0.4)
    m.add(kit.chord(3.0), C_CHIME, gain=0.26, send=0.6)
    m.add(kit.motif(3.0), C_CHIME, gain=0.75, send=0.6)
    m.add(kit.chime(kit.root + 24, 2.4), C_W2[0] + 0.25, gain=0.16, pan=0.25, send=0.6)
    return mix_master(m, tail=0.9, wet=0.75, ir=2.4, kit=kit)


# ====================================================================================================
# animated title logo (on colour, and transparent)
# ====================================================================================================
T_DUR, T_STRIP, T_BAR, T_HOLES, T_SETTLE = 5.0, (0.3, 1.0), (0.55, 1.3), 1.42, 2.3
T_HOLE_STEP = 0.034


def title_logo(style, transparent=False):
    clip = Clip(style, T_DUR, seed=f"{style.key}-title", transparent=transparent)
    art, lg = clip.art, style.logo
    h = 1150
    cx, cy = CX, CY + 10
    art.tag = "strip"
    art.logo(cx, cy, h, parts=["film-strip"], solid=True)
    art.tag = "bar"
    art.logo(cx, cy, h, parts=["bar"])
    # each sprocket hole is punched out of the strip on its own beat (bottom to top, the two columns taking turns)
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
        pop = keys(t, [(T_SETTLE - 0.08, 1.0), (T_SETTLE + 0.03, 1.035), (T_SETTLE + 0.2, 1.0)])
        s = {"_": {}}
        k = ease_out((t - T_STRIP[0]) / (T_STRIP[1] - T_STRIP[0]), 3)
        d = -up * 1050 * (1 - k)
        s["strip"] = {"a": 0.0} if t < T_STRIP[0] else {"a": min(1.0, (t - T_STRIP[0]) / (4 * F)), "dx": d[0], "dy": d[1], "s": pop, "cx": cx, "cy": cy}
        k = ease_out_back((t - T_BAR[0]) / (T_BAR[1] - T_BAR[0]), 1.1)
        d = -down * 1150 * (1 - k)
        s["bar"] = {"a": 0.0} if t < T_BAR[0] else {"a": min(1.0, (t - T_BAR[0]) / (4 * F)), "dx": d[0], "dy": d[1], "s": pop, "cx": cx, "cy": cy}
        for tag, (t0, _) in clip.hole_times.items():
            s[tag] = {"a": on(t, t0), "s": pop, "cx": cx, "cy": cy}
        return s
    clip.animate = animate
    return clip


def audio_title(style, clip):
    kit = Kit(style)
    m = S.Mix(T_DUR)
    m.add(kit.bed(T_DUR, 51), 0.0, gain=0.05, send=0.0)
    m.add(kit.whoosh(0.7, seed=52), T_STRIP[0], gain=0.32, pan=-0.3, send=0.3)
    m.add(kit.whoosh(0.75, seed=53, up=False), T_BAR[0], gain=0.32, pan=0.3, send=0.3)
    m.add(kit.tap(seed=54), T_STRIP[1] - 0.05, gain=0.45, pan=-0.2, send=0.25)
    m.add(kit.hit(1.1, seed=55), T_BAR[1] - 0.06, gain=0.85, pan=0.1, send=0.3)
    for n, (tag, (t0, pan)) in enumerate(sorted(clip.hole_times.items(), key=lambda kv: kv[1][0])):
        m.add(kit.tick(seed=60 + n, pitch=0.8 + 0.022 * n), t0, gain=0.26, pan=float(np.clip(pan, -0.7, 0.7)), send=0.25)
    m.add(kit.swell(0.4, 56), T_SETTLE - 0.4, gain=0.12, send=0.3)
    m.add(kit.chord(2.6), T_SETTLE, gain=0.22, send=0.55)
    m.add(kit.motif(2.6), T_SETTLE, gain=0.7, send=0.55)
    return mix_master(m, tail=0.5, wet=0.65, ir=2.0, kit=kit)


# ====================================================================================================
# end card: room for two video suggestions and the channel icon; loops seamlessly
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
        w = 2 * np.pi * t / E_DUR
        s = {"_": {"grain": 1.0 + 0.12 * np.sin(2 * w)}}
        s["slot0"] = {"a": 0.80 + 0.20 * np.sin(2 * w)}
        s["slot1"] = {"a": 0.80 + 0.20 * np.sin(2 * w + np.pi)}
        s["fill0"] = {"a": 0.75 + 0.25 * np.sin(2 * w + 0.6)}
        s["fill1"] = {"a": 0.75 + 0.25 * np.sin(2 * w + np.pi + 0.6)}
        s["icon"] = {"s": 1.0 + 0.022 * np.sin(3 * w), "cx": cx, "cy": cy}
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


def test_sheet(style, which=("a", "b", "c", "title", "end")):
    """Small contact sheet of key frames (for checking before a full render)."""
    import cv2
    from PIL import Image
    rows = []
    for w in which:
        clip = {"a": intro_a, "b": intro_b, "c": intro_c, "title": title_logo, "end": end_card}[w](style)
        n = clip.n
        fr = {"a": [1, 3, 10, 12, 21, 24, 47], "b": [4, 22, 34, 46, 56, 68, 95], "c": [10, 36, 52, 70, 92, 104, 167],
              "title": [10, 18, 28, 36, 44, 56, 119], "end": [0, 60, 120, 180]}[w]
        tiles = [cv2.resize(clip.frame(min(f, n - 1)), (640, 360), interpolation=cv2.INTER_AREA) for f in fr]
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
