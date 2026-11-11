"""
Film pieces in a style:
  the clapperboard      transparent PNG (open + closed), a still on the style's colour, a 3 s animated clap with sound
                        (on colour as MP4, and transparent as ProRes 4444 to drop over footage)
  the "presents" card   "ASTRIS PRODUCTIONS presents" as stills (main + dark) and as a 3 s animation with sound

Usage: python3 code/build.py film [--style red] [clapper presents]
"""
import shutil

import cv2
import numpy as np

from assets.sounds import Kit, mix_master, save as save_wav
from engine import lockup as L
from engine import sound as S
from engine import type as T
from engine.core import raster_polys, rounded_mask, save_png, save_png_alpha
from engine.paths import out
from engine.style import config
from engine.video import FPS, H, W, Clip, ease_in, ease_in_out, ease_out, keys, smooth, wipe

F = 1.0 / FPS
CX, CY = W / 2, H / 2
OPEN = -24.0            # degrees: how far the top stick is lifted


# ====================================================================================================
# the clapperboard drawing
# ====================================================================================================
def clapper(art, cx, cy, w, transparent=False):
    """Draw the board centred on (cx, cy), body `w` px wide. Layers are tagged 'board' and 'stick' (the hinged top stick).
    Returns the hinge point, which the stick turns about."""
    st, k = art.style, art.style.key
    if k == "red":            # warm-black slate, cream lettering and stripes
        body, text, stripe = dict(role="second"), dict(role="ink"), dict(role="ink")
        base, bars = body, stripe
    elif k == "yellow":       # black slate, yellow lettering, off-white stripes
        body, text, stripe = dict(role="ink"), dict(role="colour", colour=st.hex["signature"]), dict(role="second")
        base, bars = body, stripe
    else:                     # risograph: a blue slate with the lettering left as bare paper; the sticks are coral with blue stripes
        body = dict(role="ink")
        text = dict(role="colour", colour=st.hex["light"]) if transparent else dict(role="field")
        base, bars = dict(role="second"), dict(role="ink", shadow=False)
        stripe = base
    hs, hb, gap = 0.100 * w, 0.600 * w, 0.014 * w
    total = 2 * hs + gap + hb
    bx, top = cx - w / 2, cy - total / 2
    y_stick2, y_join, y_stick1 = top, top + hs, top + hs
    by = top + 2 * hs + gap
    hinge = (bx + 0.055 * w, y_join)

    def stick(y0, lean, tag):
        hh, ww = int(round(hs)), int(round(w))
        rr = rounded_mask(hh, ww, 0.016 * w)
        P = w / 6.0
        polys = []
        for i in range(-2, 9):
            x = i * P + 0.18 * P
            sh = lean * hs * 0.5                                    # the logo's own slope: 1 across for every 2 up
            polys.append((f"s{i}", np.array([(x, hh), (x + P / 2, hh), (x + P / 2 + sh, 0), (x + sh, 0)], float), []))
        bars_m = raster_polys(polys, (hh, ww), ss=4) * rr
        art.tag = tag
        art.add(rr, bx, y0, size=hs, wear=0.5, **dict(base, shadow=False))
        art.add(bars_m, bx, y0, size=hs, wear=0.5, **bars)

    # ---- the slate
    art.tag = "board"
    art.rect(bx, by, bx + w, by + hb, radius=0.030 * w, size=0.3 * w, wear=0.6, **body)
    stick(y_stick1, +1, "board")
    mx = 0.050 * w
    ix0, ix1 = bx + mx, bx + w - mx
    lw = max(2.0, 0.0052 * w)
    tk = dict(text, shadow=False, wear=0)
    f_lab = st.text_face(700)
    lab = 0.0205 * w

    def label(s, x, y):
        art.text(s, x, y, lab, face=f_lab, tracking=0.16, anchor="lt", **tk)

    def hline(y):
        art.rect(ix0, y - lw / 2, ix1, y + lw / 2, size=60 * art.s, **dict(tk, crisp=True))

    def vline(x, y0, y1):
        art.rect(x - lw / 2, y0, x + lw / 2, y1, size=60 * art.s, **dict(tk, crisp=True))

    name = config()["brand"]["name"]
    label("PRODUCTION", ix0, by + 0.040 * w)
    size = T.fit_size(name, st.display, 0.64 * w, 0.02)
    art.text(name, ix0, by + 0.168 * w, size, tracking=0.02, anchor="ls", **dict(text, shadow=False, wear=0.4))
    lh = 0.128 * w
    art.logo(ix1 - lh * st.logo.aspect / 2, by + 0.106 * w, lh, **dict(text, shadow=False, wear=0.4))
    y1, y2, y3 = by + 0.205 * w, by + 0.338 * w, by + 0.471 * w
    for y in (y1, y2, y3):
        hline(y)
    third = (ix1 - ix0) / 3
    for i, s in enumerate(("ROLL", "SCENE", "TAKE")):
        label(s, ix0 + i * third + (0.022 * w if i else 0), y1 + 0.022 * w)
        if i:
            vline(ix0 + i * third, y1, y2)
    half = (ix1 - ix0) / 2
    for i, s in enumerate(("DIRECTOR", "CAMERA")):
        label(s, ix0 + i * half + (0.022 * w if i else 0), y2 + 0.022 * w)
    vline(ix0 + half, y2, y3)
    label("DATE", ix0, y3 + 0.022 * w)
    art.text(st.tagline, ix1, by + hb - 0.046 * w, 0.058 * w, tracking=L.TRACK_MAIN, anchor="rs", **dict(text, shadow=False, wear=0.4))
    # ---- the hinged stick, then the hinge plate over both sticks
    stick(y_stick2, -1, "stick")
    art.tag = "board"
    pw, ph = 0.110 * w, 0.150 * w
    plate = dict(role="ink", shadow=False) if k == "wildcard" else stripe
    dot = dict(role="second", knockout=False) if k == "wildcard" else body
    art.rect(hinge[0] - pw / 2, hinge[1] - ph / 2, hinge[0] + pw / 2, hinge[1] + ph / 2, radius=0.018 * w, size=hs, wear=0.4, **dict(plate, shadow=False))
    art.circle(hinge[0], hinge[1], 0.021 * w, wear=0, **dict(dot, shadow=False))
    art.tag = "main"
    return hinge, (bx, top, bx + w, top + total)


# ====================================================================================================
# 3 s clap
# ====================================================================================================
K_DUR, K_IN, K_LIFT, K_CLAP = 3.0, 0.12, 0.80, 1.25
K_W, K_DROP = 1500, 200          # the open board sits a little low so the lifted stick stays in frame, then rises to the centre


def clap(style, transparent=False):
    clip = Clip(style, K_DUR, seed=f"{style.key}-clap", transparent=transparent)
    hinge, box = clapper(clip.art, CX, CY + 40, K_W, transparent=transparent)
    hx, hy = hinge

    def animate(t):
        # the board glides up into frame, the stick lifts a little further, then shuts in one clean move,
        # and the closed board rises gently to the centre. No bounce, no shake, no flash.
        k = ease_out((t - K_IN) / 0.55, 5)
        dy = 160 * (1 - k) + K_DROP * (1 - smooth((t - (K_CLAP + 0.25)) / 0.70))
        a = min(1.0, max(0.0, (t - K_IN) / 0.18))
        r = OPEN - 5 * ease_in_out((t - K_LIFT) / (K_CLAP - 0.14 - K_LIFT))
        r *= 1 - ease_in((t - (K_CLAP - 0.14)) / 0.14, 3)
        return {"board": {"a": a, "dy": dy}, "stick": {"a": a, "dy": dy, "r": r, "cx": hx, "cy": hy}}
    clip.animate = animate
    return clip


def clack(seed=1, bright=1.0):
    """Two bits of wood meeting: a sharp crack, two short woody resonances and a small thump."""
    r = np.random.default_rng(seed)
    n = int(0.5 * S.SR)
    t = np.arange(n) / S.SR
    crack = S.sos(r.standard_normal(n), "bandpass", (1400, 7500 * bright), 2) * np.exp(-t / 0.011)
    wood = sum(g * np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * np.exp(-t / d) for f, g, d in ((1180, 0.7, 0.030), (2320, 0.4, 0.018), (640, 0.5, 0.045)))
    thump = np.sin(2 * np.pi * (170 * np.exp(-t / 0.05) + 70) * t) * np.exp(-t / 0.06) * 0.6
    x = crack * 1.3 + wood + thump
    x[: int(0.0006 * S.SR)] *= np.linspace(0, 1, int(0.0006 * S.SR))
    return S.sat(x * 0.9, 1.6)


def audio_clap(style):
    kit = Kit(style)
    m = S.Mix(K_DUR)
    m.add(kit.bed(K_DUR, 81), 0.0, gain=0.05, send=0.0)
    m.add(kit.whoosh(0.4, seed=82), K_IN, gain=0.22, send=0.25)
    m.add(kit.tap(seed=83, pitch=0.9), K_IN + 0.36, gain=0.3, send=0.2)
    m.add(kit.tick(seed=84, pitch=1.4), K_CLAP - 3 * F - 0.16, gain=0.16, send=0.2)             # the little lift
    m.add(clack(85, {"red": 0.8, "yellow": 1.15, "wildcard": 1.0}[kit.k]), K_CLAP - 0.004, gain=1.0, send=0.22)
    m.add(S.sub_drop(0.5, 90, 48, 0.2, 0.3), K_CLAP, gain=0.22, send=0.0)
    m.add(kit.motif(1.5), K_CLAP + 0.30, gain=0.30, send=0.5)
    return mix_master(m, tail=0.35, kit=kit)


# ====================================================================================================
# "ASTRIS PRODUCTIONS presents"
# ====================================================================================================
P_DUR = 3.0


def presents(style, scheme="main"):
    clip = Clip(style, P_DUR, scheme=scheme, seed=f"{style.key}-presents-{scheme}")
    art, k = clip.art, style.key
    line = config()["brand"]["presents_line"]
    name, word = line.rsplit(" ", 1) if " " in line else (line, "presents")
    art.tag = "logo"
    art.logo(CX, CY - 330, 560, role="second" if (scheme == "dark" and k == "red") else "ink")
    art.tag = "name"
    size = T.fit_size(name, style.display, 2050, 0.20)
    art.text(name, CX, CY + 190, size, tracking=0.20, anchor="mm")
    art.tag = "word"
    art.text(word, CX, CY + 420, 92, face=style.text_face(500), tracking=0.36, anchor="mm", shadow=False, wear=0.3)

    def animate(t):
        s = {"_": {"black": 1 - smooth(t / 0.5) + smooth((t - (P_DUR - 0.5)) / 0.5)}}
        s["logo"] = {"a": ease_out((t - 0.30) / 0.40, 2), "s": 1.05 - 0.05 * ease_out((t - 0.30) / 1.0, 4)}
        s["name"] = wipe("right", smooth((t - 0.75) / 0.65), 0.06)
        k3 = ease_out((t - 1.35) / 0.50, 3)
        s["word"] = {"a": k3, "dy": 18 * (1 - k3)}
        return s
    clip.animate = animate
    return clip


def audio_presents(style):
    kit = Kit(style)
    m = S.Mix(P_DUR)
    r = kit.root
    m.add(kit.bed(P_DUR, 91), 0.0, gain=0.07, send=0.0)
    m.add(S.pad([S.midi(n) for n in (r - 12, r - 5, r, r + 7)], P_DUR, attack=0.7, release=1.2, cutoff=(220, 1600), level=1.0, seed=92), 0.0, gain=0.22, send=0.5)
    m.add(kit.swell(0.5, 93), 0.28, gain=0.10, send=0.4)
    m.add(kit.motif(2.2), 0.78, gain=0.6, send=0.6)
    m.add(kit.tick(seed=94, pitch=1.2), 1.36, gain=0.14, send=0.4)
    mix = mix_master(m, tail=0.6, wet=0.7, ir=2.0, kit=kit)
    n = int(0.25 * S.SR)
    mix[:, :n] *= np.linspace(0, 1, n) ** 1.5
    return mix


# ====================================================================================================
def crop_alpha(rgba, pad, width=None):
    """Trim to the artwork, add an even margin, and (optionally) centre it on a canvas of an exact width."""
    al = rgba[..., 3]
    ys, xs = np.where(al > 2)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cut = rgba[y0:y1, x0:x1]
    hh, ww = cut.shape[:2]
    Wc = width or ww + 2 * pad
    canvas = np.zeros((hh + 2 * pad, Wc, 4), np.uint8)
    canvas[..., :3] = cut[0, 0, :3]
    ox = (Wc - ww) // 2
    canvas[pad:pad + hh, ox:ox + ww] = cut
    return canvas


def build(style, *which):
    k = style.key
    which = [w for w in which if w in ("clapper", "presents")] or ["clapper", "presents"]
    sdir = out(k, "sound", "stingers")
    made = []
    if "clapper" in which:
        d = out(k, "paper", "clapperboard")
        # ---- transparent stills: one drawing, two poses
        big = Clip(style, F, seed=f"{k}-clapper-still", transparent=True, size=(4096, 5000))
        hinge, _ = clapper(big.art, 2048, 3200, 3700, transparent=True)
        for pose, ang in (("open", OPEN), ("closed", 0.0)):
            big.animate = lambda t, ang=ang: {"stick": {"r": ang, "cx": hinge[0], "cy": hinge[1]}}
            rgba = crop_alpha(big.frame(0), 120, 4096)
            p = d / f"astris-{k}-clapperboard-{pose}-transparent-4096.png"
            save_png_alpha(rgba[..., :3] / 255.0, rgba[..., 3] / 255.0, p)
            small = cv2.resize(rgba, (1024, int(round(rgba.shape[0] * 1024 / rgba.shape[1]))), interpolation=cv2.INTER_AREA)
            save_png_alpha(small[..., :3] / 255.0, small[..., 3] / 255.0, d / f"astris-{k}-clapperboard-{pose}-transparent-1024.png")
            made.append(p.name)
        # ---- the clap
        clip = clap(style)
        save_png(clip.frame(18), d / f"astris-{k}-clapperboard-on-colour-3840x2160.png")
        name = f"astris-{k}-clapperboard-clap-3s-4k24"
        wav = save_wav(d / f"{name}.wav", audio_clap(style))
        shutil.copyfile(wav, sdir / f"astris-{k}-clapperboard-clap-3s.wav")
        clip.render_h264(d / f"{name}.mp4", wav)
        clap(style, transparent=True).render_prores(d / f"astris-{k}-clapperboard-clap-alpha-3s-4k24-prores4444.mov", wav)
        made.append(name)
    if "presents" in which:
        d = out(k, "paper", "presents-card")
        mix = audio_presents(style)
        name = f"astris-{k}-presents-card-3s-4k24"
        wav = save_wav(d / f"{name}.wav", mix)
        shutil.copyfile(wav, sdir / f"astris-{k}-presents-card-3s.wav")
        for scheme, tag in (("main", ""), ("dark", "-dark")):
            clip = presents(style, scheme)
            save_png(clip.frame(48), d / f"astris-{k}-presents-card{tag}-3840x2160.png")
            clip.render_h264(d / f"astris-{k}-presents-card{tag}-3s-4k24.mp4", wav)
            made.append(f"astris-{k}-presents-card{tag}-3s-4k24")
    return made
