"""
Shared helpers for the idents, stills and banners (on top of common.py / sound.py):
text in any font with per-letter animation, two-line lockups with any type pairing, a lockup camera,
textures (paper, fbm noise, film dust/hair/scratches, light leaks, halation, VHS/CRT), bevel normals and
environment-mapped metal for any mask, and a standard runner (--test / --audio / full render).
"""
import math
import sys

import numpy as np

import common as C
import sound as S

cv2 = C.cv2
W, H, FPS = C.W, C.H, C.FPS
_FONTS = {}


def font(name):
    if name not in _FONTS:
        _FONTS[name] = C.Font(C.FONT_DIR / f"{name}.ttf")
    return _FONTS[name]


def rgb(h):
    return C.hexrgb(h)


def comp(img, mask, col):
    m = mask[..., None]
    return img * (1 - m) + np.asarray(col, np.float32) * m


# ------------------------------------------------------------------------------------------------
# camera: maps design space (the finished frame, Z=1) to the screen
# ------------------------------------------------------------------------------------------------
class Cam:
    def __init__(self, Z=1.0, P0=(W / 2, H / 2), Q=None, rot=0.0):
        self.Z, self.P0 = Z, np.asarray(P0, np.float64)
        self.Q = self.P0 if Q is None else np.asarray(Q, np.float64)
        self.rot = rot

    def __call__(self, p):
        p = np.asarray(p, np.float64) - self.P0
        if self.rot:
            c, s = math.cos(self.rot), math.sin(self.rot)
            p = np.stack([p[..., 0] * c - p[..., 1] * s, p[..., 0] * s + p[..., 1] * c], -1)
        return self.Q + self.Z * p

    def polys(self, polys):
        return [self(p) for p in polys]


IDENTITY = Cam()


# ------------------------------------------------------------------------------------------------
# type
# ------------------------------------------------------------------------------------------------
def line_letters(fontname, text, cap_px, cx, baseline, tracking_em=0.0, width_px=None, per_letter=None):
    """A line of text centred on cx, baseline at `baseline` (design px). Returns, per letter, a dict with
    its polygons (design space, after any per-letter transform) and its rest centre."""
    placed, width = C.layout_word(font(fontname), text, cap_px, tracking_em, width_px)
    out = []
    n = len(placed)
    for k, (cont, xl, i0, i1) in enumerate(placed):
        mid = (i0 + i1) / 2
        centre = np.array([cx + mid - width / 2, baseline - cap_px / 2])
        tr = per_letter(k, n) if per_letter else None
        polys = []
        for c in cont:
            q = np.stack([c[:, 0] - mid, c[:, 1] + cap_px / 2], 1)       # letter-local, centred
            if tr:
                s, r = tr.get("s", 1.0), tr.get("rot", 0.0)
                sx, sy = tr.get("sx", 1.0) * s, tr.get("sy", 1.0) * s
                q = q * [sx, sy]
                if r:
                    cr, sr = math.cos(r), math.sin(r)
                    q = np.stack([q[:, 0] * cr - q[:, 1] * sr, q[:, 0] * sr + q[:, 1] * cr], 1)
                q = q + [tr.get("dx", 0.0), tr.get("dy", 0.0)]
            polys.append(q + centre)
        out.append({"polys": polys, "centre": centre, "ch": text[k], "width": i1 - i0})
    return out, width


def letters_mask(letters, cam=IDENTITY, alpha=None, shape=(H, W)):
    m = np.zeros(shape, np.float32)
    for k, L in enumerate(letters):
        a = 1.0 if alpha is None else float(alpha[k])
        if a > 0.002 and L["polys"]:
            C.draw_polys_max(m, cam.polys(L["polys"]), a)
    return m


class Lockup2:
    """Logo on top, two lines of type under it, in any fonts. Everything in design px (the final frame).
    lines: [(font, text, cap_px, tracking_em, justify_to_line0)]"""

    def __init__(self, logo, logo_h=760, lines=(), gaps=(160, 70), centre=(W / 2, H / 2 - 20)):
        self.logo, self.logo_h, self.lines = logo, logo_h, list(lines)
        widths, caps = [], []
        for i, (f, txt, cap, tr, just) in enumerate(self.lines):
            _, w = C.layout_word(font(f), txt, cap, tr)
            widths.append(w)
            caps.append(cap)
        self.widths = widths
        total = logo_h + sum(gaps[: len(self.lines)]) + sum(caps)
        top = centre[1] - total / 2
        self.logo_c = np.array([centre[0], top + logo_h / 2])
        y = top + logo_h
        self.baselines = []
        for i, cap in enumerate(caps):
            y += gaps[i] + cap
            self.baselines.append(y)
        self.cx = centre[0]

    def logo_polys(self, cam=IDENTITY, pieces=None, scale=1.0, dx=0.0, dy=0.0, rot=0.0):
        h = self.logo_h * scale
        return cam.polys(self.logo.polys_px(self.logo_c[0] + dx, self.logo_c[1] + dy, h, rot, pieces))

    def line(self, i, per_letter=None):
        f, txt, cap, tr, just = self.lines[i]
        wpx = self.widths[0] * just if (just and i > 0) else None
        return line_letters(f, txt, cap, self.cx, self.baselines[i], tr, wpx, per_letter)[0]


# ------------------------------------------------------------------------------------------------
# textures
# ------------------------------------------------------------------------------------------------
def fbm(h, w, seed, octaves=6, base=2, persistence=0.55, aspect=None):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    asp = aspect or w / h
    for o in range(octaves):
        gh = max(2, int(base * 2 ** o))
        gw = max(2, int(gh * asp))
        g = r.standard_normal((gh, gw)).astype(np.float32)
        acc += cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp
        amp *= persistence
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min() + 1e-9)


def paper(h, w, base, seed=0, fibres=0.05, grain=0.03, mottle=0.06, tooth=0.0):
    """Paper: soft mottling, directional fibres, fine grain (and optional tooth for pencil)."""
    r = np.random.default_rng(seed)
    mot = fbm(h // 8, w // 8, seed, 5)
    mot = cv2.resize(mot, (w, h), interpolation=cv2.INTER_CUBIC)
    # short fibres in every direction (real paper), not long streaks
    fib = np.zeros((h // 2, w // 2), np.float32)
    for _ in range(int(w * h / 1600)):
        x, y = r.uniform(0, w // 2), r.uniform(0, h // 2)
        a = r.uniform(0, math.pi)
        L = r.uniform(4, 22)
        cv2.line(fib, (int(x * 4), int(y * 4)), (int((x + math.cos(a) * L) * 4), int((y + math.sin(a) * L) * 4)),
                 float(r.choice([-1.0, 1.0]) * r.uniform(0.4, 1.0)), 1, cv2.LINE_AA, 2)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.6)
    fib = cv2.resize(fib / (fib.std() + 1e-6), (w, h))
    fine = cv2.GaussianBlur(r.standard_normal((h, w)).astype(np.float32), (0, 0), 0.8)
    fine /= fine.std() + 1e-6
    t = 1 + mottle * (mot - 0.5) * 2 + fibres * fib * 0.5 + grain * fine * 0.5
    img = np.asarray(base, np.float32)[None, None] * t[..., None]
    if tooth > 0:
        img = img * (1 - tooth * np.clip(fine, 0, None)[..., None] * 0.15)
    return img.astype(np.float32)


def tooth_map(h, w, seed):
    """Paper tooth for pencil: graphite catches on the peaks."""
    r = np.random.default_rng(seed)
    n = cv2.GaussianBlur(r.standard_normal((h, w)).astype(np.float32), (0, 0), 1.1)
    n2 = cv2.GaussianBlur(r.standard_normal((h // 3, w // 3)).astype(np.float32), (0, 0), 1.5)
    n = n / n.std() + 0.6 * cv2.resize(n2 / n2.std(), (w, h))
    return np.clip(0.5 + 0.28 * n, 0, 1).astype(np.float32)


def dust_layer(frame, seed, density=1.0, shape=(H, W), hair=True, scratches=True):
    """Film dirt for one frame: dark dust specks, a few bright specks, an occasional hair and
    vertical scratches. Returns (dark, light) masks in [0,1]."""
    r = np.random.default_rng(seed * 7919 + frame)
    dark = np.zeros((shape[0] // 2, shape[1] // 2), np.float32)
    light = np.zeros_like(dark)
    hh, ww = dark.shape
    for _ in range(int(r.poisson(14 * density))):
        x, y = r.uniform(0, ww), r.uniform(0, hh)
        rad = r.uniform(0.6, 3.2) * (2.5 if r.uniform() < 0.08 else 1)
        tgt = dark if r.uniform() < 0.75 else light
        cv2.ellipse(tgt, ((float(x), float(y)), (float(rad * r.uniform(0.6, 1.6)), float(rad)), float(r.uniform(0, 180))),
                    float(r.uniform(0.5, 1.0)), -1, cv2.LINE_AA)
    if hair and r.uniform() < 0.22 * density:
        x, y = r.uniform(0, ww), r.uniform(0, hh)
        pts = [(x, y)]
        ang = r.uniform(0, 6.28)
        for _ in range(int(r.integers(8, 20))):
            ang += r.normal(0, 0.35)
            x, y = x + math.cos(ang) * 9, y + math.sin(ang) * 9
            pts.append((x, y))
        cv2.polylines(dark, [np.round(np.array(pts) * 16).astype(np.int32)], False, 0.85, 1, cv2.LINE_AA, 4)
    if scratches:
        for k in range(int(r.poisson(1.2 * density))):
            x = r.uniform(0, ww)
            x2 = x + r.normal(0, 3)
            cv2.line(light if r.uniform() < 0.6 else dark, (int(x * 16), 0), (int(x2 * 16), hh * 16),
                     float(r.uniform(0.25, 0.7)), 1, cv2.LINE_AA, 4)
    dark = cv2.resize(cv2.GaussianBlur(dark, (0, 0), 0.6), (shape[1], shape[0]))
    light = cv2.resize(cv2.GaussianBlur(light, (0, 0), 0.6), (shape[1], shape[0]))
    return dark, light


def light_leak(t, seed, colours=("#ff6a1a", "#ffb347", "#ff2d55"), strength=1.0, shape=(H, W)):
    """Drifting warm light leak (additive), computed at low resolution."""
    r = np.random.default_rng(seed)
    h, w = shape[0] // 8, shape[1] // 8
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acc = np.zeros((h, w, 3), np.float32)
    for k, col in enumerate(colours):
        cx = w * (r.uniform(-0.1, 0.4) + 0.25 * math.sin(t * r.uniform(0.3, 0.8) + k))
        cy = h * (r.uniform(0.0, 1.0) + 0.15 * math.cos(t * r.uniform(0.3, 0.7) + k * 2))
        rad = w * r.uniform(0.25, 0.5)
        g = np.exp(-(((xx - cx) / rad) ** 2 + ((yy - cy) / (rad * 1.4)) ** 2))
        acc += g[..., None] * rgb(col)
    acc = cv2.GaussianBlur(acc, (0, 0), 6)
    return cv2.resize(acc, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR) * strength


def halation(img, threshold=0.7, sigma=18, colour=(1.0, 0.35, 0.15), strength=0.6):
    """Film halation: a red-orange glow bleeding out of the highlights."""
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    lum = small.max(axis=2)
    hi = np.clip((lum - threshold) / (1 - threshold), 0, 1)
    g = cv2.GaussianBlur(hi, (0, 0), sigma / 4) * 0.7 + cv2.GaussianBlur(hi, (0, 0), sigma) * 0.5
    return img + C.up(g)[..., None] * np.asarray(colour, np.float32) * strength


def chroma_shift(img, dx_r, dx_b, dy=0.0):
    out = img.copy()
    for ch, dx in ((0, dx_r), (2, dx_b)):
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        out[..., ch] = cv2.warpAffine(img[..., ch], M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REFLECT101)
    return out


_CRT = {}


def crt_curve(img, k=0.06):
    """Barrel distortion like a curved CRT, with a dark rounded bezel."""
    if k not in _CRT:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        u, v = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
        r2 = u * u + v * v
        f = 1 + k * r2
        mx = (u * f) * (W / 2) + W / 2
        my = (v * f) * (H / 2) + H / 2
        inside = ((np.abs(u * f) < 1) & (np.abs(v * f) < 1)).astype(np.float32)
        edge = np.clip((1 - np.maximum(np.abs(u * f), np.abs(v * f))) * 60, 0, 1)
        _CRT[k] = (mx, my, cv2.GaussianBlur(inside * edge, (0, 0), 3))
    mx, my, vig = _CRT[k]
    out = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out * vig[..., None]


def scanlines(img, period=6, depth=0.22, phase=0.0):
    y = np.arange(H, dtype=np.float32)
    s = 1 - depth * (0.5 + 0.5 * np.cos(2 * math.pi * (y + phase) / period))
    return img * s[:, None, None]


def halftone(value, cell=24, angle=0.4, shape=(H, W)):
    """Halftone dots: value (HxW in [0,1], 1 = full ink) -> dot coverage mask."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    c, s = math.cos(angle), math.sin(angle)
    u = (xx * c + yy * s) / cell
    v = (-xx * s + yy * c) / cell
    du, dv = u - np.floor(u) - 0.5, v - np.floor(v) - 0.5
    d = np.sqrt(du * du + dv * dv)
    rad = np.sqrt(np.clip(value, 0, 1) / math.pi) * 1.05
    return np.clip((rad - d) * cell / 1.2 + 0.5, 0, 1).astype(np.float32)


# ------------------------------------------------------------------------------------------------
# bevel normals + environment-mapped metal for any mask
# ------------------------------------------------------------------------------------------------
def bevel_normals(mask, width, height, blur=1.0):
    di = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    x = np.clip(di / width, 0, 1)
    hgt = np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1)).astype(np.float32)
    hgt = cv2.GaussianBlur(hgt, (0, 0), blur)
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8 * height
    gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8 * height
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def env_metal(n, ramp, uu, vv, bend=1.0, light=(-0.4, -0.8, 0.6), spec_pow=60, spec=1.2):
    """Reflection of a vertical gradient environment (ramp: [(pos, hex)]) + a specular highlight.
    uu/vv: position across the object (for a gentle curvature on the flat faces)."""
    ry = 2 * n[..., 2] * n[..., 1] + vv * bend
    rx = 2 * n[..., 2] * n[..., 0] + uu * bend * 0.4
    u = np.clip(0.5 + 0.5 * (ry * 0.85 + rx * 0.25), 0, 1)
    keys = np.array([p for p, _ in ramp], np.float32)
    cols = np.array([rgb(h) for _, h in ramp], np.float32)
    env = np.stack([np.interp(u, keys, cols[:, c]) for c in range(3)], -1).astype(np.float32)
    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    hv = L + np.array([0, 0, 1], np.float32)
    hv /= np.linalg.norm(hv)
    sp = np.clip((n * hv).sum(-1), 0, 1) ** spec_pow
    return env + sp[..., None] * spec


# ------------------------------------------------------------------------------------------------
# runner
# ------------------------------------------------------------------------------------------------
def run(name, dur, frame_fn, audio_fn, tests, workers=3, sheet_cols=4, tag=None):
    """--test [f1,f2..] renders full-size test frames; --audio writes only the WAV; otherwise full render."""
    n = int(round(dur * FPS))
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    C.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if "--test" in sys.argv:
        i = sys.argv.index("--test")
        fr = [int(a) for a in sys.argv[i + 1].split(",")] if len(sys.argv) > i + 1 else tests
        print(C.save_test_frames(tag or name, frame_fn, [min(f, n - 1) for f in fr], sheet_cols=sheet_cols))
        return
    wav = C.AUDIO_DIR / f"{name}.wav"
    mix = audio_fn()
    assert mix.shape[1] == int(round(dur * S.SR)), "audio length must match the video"
    S.write_wav24(wav, mix)
    if "--audio" in sys.argv:
        return
    C.render_video(name, n, frame_fn, wav, workers=workers)


# ------------------------------------------------------------------------------------------------
# three.js scenes: stream frames from headless Chromium (render3d.js), composite in Python, encode
# ------------------------------------------------------------------------------------------------
def frames_3d(scene, frame_list, log_name, size=(W, H)):
    import json
    import os
    import subprocess
    contiguous = frame_list == list(range(frame_list[0], frame_list[0] + len(frame_list)))
    args = [str(frame_list[0]), str(frame_list[0] + len(frame_list))] if contiguous else [",".join(map(str, frame_list))]
    env = dict(os.environ, SIZE=f"{size[0]}x{size[1]}")
    (C.ROOT / "logs").mkdir(exist_ok=True)
    proc = subprocess.Popen(["node", str(C.ROOT / "render3d.js"), scene] + args, stdout=subprocess.PIPE,
                            stderr=open(C.ROOT / "logs" / log_name, "a"), cwd=C.ROOT, env=env)
    nbytes = size[0] * size[1] * 4
    for f in frame_list:
        head = proc.stdout.read(512)
        if len(head) < 512:
            raise RuntimeError(f"3D renderer stopped early - see logs/{log_name}")
        info = json.loads(head.decode().strip())
        yield (f, info, proc.stdout.read(nbytes))
    proc.wait()


def rgba_from(raw, size=(W, H)):
    a = np.frombuffer(raw, np.uint8).reshape(size[1], size[0], 4)[::-1]
    return a[..., :3].astype(np.float32) * (1 / 255), a[..., 3].astype(np.float32) * (1 / 255)


def run3d(name, dur, scene, composite, audio_fn, tests, workers=2, tag=None):
    """Like run(), for three.js pieces: composite((f, info, rgba_bytes)) -> uint8 frame."""
    import multiprocessing as mp
    import subprocess
    import time
    n = int(round(dur * FPS))
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    C.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if "--test" in sys.argv:
        i = sys.argv.index("--test")
        fr = [int(a) for a in sys.argv[i + 1].split(",")] if len(sys.argv) > i + 1 else tests
        fr = [min(f, n - 1) for f in fr]
        rendered = [composite(item) for item in frames_3d(scene, fr, f"{tag or name}_3d.log")]
        print(C.save_test_frames(tag or name, None, fr, rendered=rendered))
        return
    wav = C.AUDIO_DIR / f"{name}.wav"
    mix = audio_fn()
    S.write_wav24(wav, mix)
    if "--audio" in sys.argv:
        return
    out = C.OUT_DIR / f"{name}.mp4"
    proc = subprocess.Popen(C.ffmpeg_cmd(out, wav), stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.get_context("fork").Pool(workers, initializer=C._worker_init) as pool:
        for k, fr in enumerate(pool.imap(composite, frames_3d(scene, list(range(n)), f"{tag or name}_3d.log"), chunksize=1)):
            proc.stdin.write(fr.tobytes())
            if k % 24 == 0 or k == n - 1:
                el = time.time() - t0
                print(f"[{name}] frame {k + 1}/{n}  {el:6.1f}s elapsed  eta {el / (k + 1) * (n - k - 1):6.1f}s", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    print(f"[{name}] wrote {out}")
