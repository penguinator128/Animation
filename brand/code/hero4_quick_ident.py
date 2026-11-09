"""
ASTRIS PRODUCTIONS - Intro 4: QUICK IDENT (3.0 s)

One idea, one motion, one hit: a single streak of white light races down the exact axis of the
logo's bar and SNAPS - it inflates into the bar. The light then spills sideways across the film strip
like white light through a prism: a rainbow band runs along its leading edge, leaving a clean white
logo behind. ASTRIS PRODUCTIONS settles in by 1.4 s and holds.
Sound: one whoosh into one impact (with a short resolved chord inside it) and a short shimmer.
"""
import math
import sys

import numpy as np

import common as C
import sound as S

NAME = "astris-hero-4-quick-ident"
DUR = 3.0
N = int(DUR * C.FPS)                 # 72 frames
T_SNAP = 10 / C.FPS                  # the hit lands exactly on frame 10 (0.417 s)

LOGO = C.Logo()
LOCK = C.Lockup(LOGO)
POST = C.Post(seed=44, grain=0.022, vignette=0.32)
BAR = len(LOGO.pieces) - 1           # the rightmost piece carries the light (the A's long bar)
FILM = [k for k in range(len(LOGO.pieces)) if k != BAR]

# background: near-black with the faintest cool lift in the middle
_yy, _xx = np.mgrid[0:C.H, 0:C.W].astype(np.float32)
_r = np.sqrt(((_xx - C.W / 2) / C.W) ** 2 + ((_yy - C.H / 2) / C.H) ** 2)
BG = (np.array([0.020, 0.022, 0.030], np.float32) * (1 - np.clip(_r * 1.6, 0, 1))[..., None]
      + np.array([0.006, 0.006, 0.009], np.float32))
WHITE = np.array([0.95, 0.965, 1.0], np.float32)


def bar_axis(Scam):
    """Centreline of the bar in screen pixels (from the bar's top-edge midpoint to its bottom midpoint)."""
    poly = LOCK.logo_polys(Scam, pieces=[BAR])[0]
    c = poly.mean(0)
    u, s, vt = np.linalg.svd(poly - c)
    d = vt[0] / np.linalg.norm(vt[0])
    if d[1] < 0:
        d = -d                                   # point downward
    proj = (poly - c) @ d
    top, bot = c + d * proj.min(), c + d * proj.max()
    n = np.array([-d[1], d[0]])                  # normal; make it point toward the film (left)
    if n[0] > 0:
        n = -n
    half_w = np.max(np.abs((poly - c) @ n))
    return top, bot, d, n, half_w, c


def cam_scale(t):
    return 0.962 + 0.038 * C.smoothstep(0.0, DUR, t)


def scene(t):
    img = BG.copy()
    Scam = cam_scale(t)
    top, bot, d, n, hw, bc = bar_axis(Scam)
    L = np.linalg.norm(bot - top)
    ts = t - T_SNAP

    # ---- the streak: enters at the top edge and races down the bar's axis, landing on the bar's foot
    if ts < 0.18:
        k = C.clamp((t - 0.03) / (T_SNAP - 0.03))
        u_in = -(top[1] / (d[1] * L)) - 0.08          # just above the top edge of the frame
        uh = u_in + (1.0 - u_in) * C.expo_in(k, 1.6)
        lam = 0.30 + 0.25 * k                          # tail grows as it accelerates
        if t > 0.03:
            # three passes (glow, body, core) drawn tail -> head so brighter segments win at the joints
            passes = [np.zeros((C.H, C.W), np.float32) for _ in range(3)]
            widths = (64, 20, 6)
            segs = 48
            for j in range(segs):
                u0 = uh - 1.8 * (1 - j / segs)
                u1 = uh - 1.8 * (1 - (j + 1) / segs)
                inten = math.exp(-(uh - u1) / lam) * min(1.0, (t - 0.03) / 0.05)
                if ts > 0:                              # after the snap the light above the bar dies away
                    inten *= math.exp(-ts / 0.045) if u1 < 0.02 else math.exp(-ts / 0.025)
                if inten < 0.008:
                    continue
                a0 = tuple(np.round((top + d * L * u0) * 16).astype(int))
                a1 = tuple(np.round((top + d * L * u1) * 16).astype(int))
                for buf, wpx in zip(passes, widths):
                    C.cv2.line(buf, a0, a1, float(inten), wpx, C.cv2.LINE_AA, shift=4)
            hp = top + d * L * uh
            if ts < 0.03:
                g = (1 if ts < 0 else math.exp(-ts / 0.015))
                hc = tuple(np.round(hp * 16).astype(int))
                for buf, rad in zip(passes, (70, 34, 13)):
                    C.cv2.circle(buf, hc, rad * 16, float(1.3 * g), -1, C.cv2.LINE_AA, shift=4)
            for buf, col in zip(passes, ((0.045, 0.065, 0.10), (0.33, 0.38, 0.42), (1.9, 1.9, 1.9))):
                img += buf[..., None] * np.array(col, np.float32)

    if ts < 0:
        return img, Scam, 0.0

    # ---- the snap: the streak inflates into the bar
    xx, yy = _xx, _yy
    rel_x, rel_y = xx - bc[0], yy - bc[1]
    dperp = rel_x * n[0] + rel_y * n[1]              # signed distance from the bar's axis (+ toward film)
    w = hw * C.expo_out(ts / 0.11, 6.0) + 1.0
    band = np.clip((w - np.abs(dperp)) / 2.0 + 0.5, 0, 1)
    bar = LOGO.mask(*LOCK.logo_xy(Scam), pieces=[BAR]) * band

    # ---- light spills toward the film strip: front s(t) moves along the normal, rainbow on its edge
    film_mask = C.poly_mask(LOCK.logo_polys(Scam, pieces=FILM))
    far = float(np.max([(p - bc) @ n for p in LOCK.logo_polys(Scam, pieces=FILM)[0]]))
    bandw = 760.0 * Scam
    s = -hw + (far + bandw * 1.15 + hw) * C.expo_out((ts - 0.01) / 0.46, 2.6)
    reveal = np.clip((s - dperp) / 3.0 + 0.5, 0, 1)
    film = film_mask * reveal
    logo = np.maximum(bar, film)

    heat = 1.0 + 0.9 * math.exp(-ts / 0.12)          # starts overexposed, cools to clean white
    colour = np.broadcast_to(WHITE * heat, img.shape).copy()
    # prism band: spectral colours ride the leading edge of the light (full strength right at the
    # front), then fade out behind it and leave clean white
    q = (s - dperp) / bandw                          # 0 at the front, 1 at the back of the band
    inband = (q > 0) & (q < 1) & (logo > 0.002)
    if np.any(inband):
        uq = q[inband]
        spec = C.spectrum(uq * 0.92) * (1.35 + 0.25 * math.exp(-ts / 0.12))
        wgt = (1 - C.smoothstep(0.62, 1.0, uq))[:, None] * 0.92
        colour[inband] = colour[inband] * (1 - wgt) + spec * wgt
    img = img * (1 - logo[..., None]) + colour * logo[..., None]

    # snap flash: a thin anamorphic flare through the bar's centre and a breath of light
    fl = math.exp(-ts / 0.09)
    if fl > 0.01:
        prof = np.exp(-((yy[:, 0] - bc[1]) / (7 * Scam)) ** 2)[:, None] * np.exp(-np.abs(xx[0] - bc[0]) / 1500)[None, :]
        img += (prof * 0.9 * fl)[..., None] * np.array([0.55, 0.75, 1.0], np.float32)
        img += 0.035 * fl
    return img, Scam, ts


def text_layer(img, t, Scam):
    def reveal(t0, n, stagger, dur):
        return [C.expo_out((t - t0 - k * stagger) / dur, 5.0) for k in range(n)]

    a = reveal(0.62, 6, 0.045, 0.42)
    tr = 1.0 + 0.16 * (1 - C.expo_out((t - 0.62) / 0.75, 5.0))
    ma = LOCK.word_mask("astris", Scam, alpha=a, track_mul=tr, letter_dy=[18 * (1 - v) for v in a])
    p = reveal(0.86, 11, 0.022, 0.38)
    tp = 1.0 + 0.10 * (1 - C.expo_out((t - 0.86) / 0.7, 5.0))
    mp = LOCK.word_mask("prod", Scam, alpha=p, track_mul=tp)
    col = WHITE * 0.97
    img = img * (1 - ma[..., None]) + col * ma[..., None]
    img = img * (1 - mp[..., None]) + col * 0.82 * mp[..., None]
    return img


def frame(i):
    t = i / C.FPS
    # motion-blur the fast moments by averaging sub-frame renders across a 180-degree shutter
    fast = (T_SNAP - 0.20) <= t <= (T_SNAP + 0.30)
    subs = 10 if fast else 1
    acc = None
    for k in range(subs):
        tk = t - (k / subs) * (0.5 / C.FPS) if subs > 1 else t
        img, Scam, ts = scene(tk)
        acc = img if acc is None else acc + img
    img = acc / subs
    img = text_layer(img, t, Scam)
    ts = t - T_SNAP
    bloom = 0.42 + (0.7 * math.exp(-ts / 0.16) if ts >= 0 else 0.2 * C.clamp(t / T_SNAP))
    return POST.finish(img, i, bloom=bloom, threshold=0.72)


def audio():
    m = S.Mix(DUR)
    m.add(S.whoosh(T_SNAP + 0.06, peak=0.86, f_lo=180, f_hi=7000, q=1.4, pan_from=-0.55, pan_to=0.25, seed=41),
          0.0, gain=0.85, send=0.15)
    m.add(S.sub_build(T_SNAP, 28, 52, curve=3.0), 0.0, gain=0.35, send=0.0)
    m.add(S.impact(2.6, weight=1.0, bright=1.0, metal=0.8, seed=43, sub_f=(84, 34)), T_SNAP, gain=1.0, send=0.22)
    m.add(S.sting([S.midi(52), S.midi(59), S.midi(64), S.midi(68), S.midi(71)], 2.5, bright=0.8, seed=45),
          T_SNAP, gain=0.42, send=0.3)
    m.add(S.shimmer(2.4, root=S.midi(88), density=30, seed=47, rise=0.35), T_SNAP + 0.03, gain=0.36, send=0.55)
    mix = m.master(ir_seconds=1.9, wet=0.9, peak_db=-1.5, tail_fade=0.08)
    S.report(mix, NAME)
    return mix


def main():
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    C.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    wav = C.AUDIO_DIR / f"{NAME}.wav"
    if "--test" in sys.argv:
        fr = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else [4, 8, 10, 11, 12, 14, 17, 22, 30, 36, 50, 71]
        print(C.save_test_frames("intro4", frame, fr))
        return
    S.write_wav24(wav, audio())
    C.render_video(NAME, N, frame, wav, workers=3)


if __name__ == "__main__":
    main()
