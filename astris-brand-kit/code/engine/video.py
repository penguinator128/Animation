"""
Moving pictures: 4K / 24 fps clips rendered frame by frame (each frame is a pure function of its time) and piped
straight into ffmpeg.

    clip = Clip(style, dur=2.0, seed="intro-a")
    clip.art.tag = "logo";  clip.art.logo(...)          # build the artwork with the normal Art tools, tagging the parts
    clip.animate = lambda t: {"logo": {"a": 1, "s": 1.1}, "_": {"exposure": 1.0}}
    clip.render_h264(path, wav)                          # or clip.render_prores(path, wav) for a transparent .mov

Per tag, animate() can set: a (opacity), dx / dy (move, px), s (scale), r (turn, degrees clockwise), cx / cy (the point
to scale and turn about), wipe = (kind, progress 0..1, softness). Kinds: right, left, down, up, diag, strip_up, bar_down.
"_" holds settings for the whole frame: black (fade to the dark neutral), exposure, grain (strength x), flood, fade.

Smooth motion
    Anything that moves is sampled several times across a 180-degree shutter (half a frame) and the samples are
    averaged: real motion blur, so a fast move reads as one smooth movement and never as a stutter of sharp copies.
    A wipe's edge is softened by however far it travels during the shutter, for the same reason.

Live grain
    GRAIN_SETS unrelated grain textures, used in turn, each one moved to a new random place every time it comes back.
    Neighbouring frames never show the same grain shifted (which the eye reads as the picture trembling), yet the
    encoder can still find each texture a few frames back and only send the move, which keeps 4K files small.
    (Scene-cut detection is off: to the encoder, unrelated grain on every frame would otherwise look like a new scene each frame.)
"""
import math
import multiprocessing as mp
import subprocess
import time

import cv2
import numpy as np

from .core import Art, apply_grain, grain_field, hex_rgb, paper_texture, press, rng_for, smoothstep, soft_noise

W, H, FPS = 3840, 2160, 24
SCALE = H / 1440.0                   # 4K is design scale 1.5
GRAIN_SETS = 3                       # unrelated grain textures, used in turn (frame 1: A, frame 2: B, frame 3: C, frame 4: A moved on ...)
VIDEO_GRAIN = 0.85                   # grain in motion reads stronger than in a still, so it is set a touch lighter
SHUTTER = 0.5                        # 180-degree shutter
NS = 17                              # sample times available across the shutter

X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-x264-params", "keyint=240:scenecut=0:bframes=0:ref=4:me=umh:merange=32:subme=8",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


# ---- easing ---------------------------------------------------------------------------------------------------
def _c(x):
    return min(1.0, max(0.0, x))


def ease_out(x, p=3):
    """Fast start, gentle landing. p=3 cubic, p=5 quint."""
    return 1 - (1 - _c(x)) ** p


def ease_in(x, p=3):
    return _c(x) ** p


def ease_in_out(x):
    x = _c(x)
    return x * x * (3 - 2 * x)


def smooth(x):
    """Smootherstep: starts and ends with zero speed and zero acceleration."""
    x = _c(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def ease_in_out_sine(x):
    return 0.5 - 0.5 * math.cos(math.pi * _c(x))


def ease_out_back(x, k=1.70158):
    x = _c(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def keys(t, pts):
    """Piecewise-linear keyframes [(time, value), ...]."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / max(1e-9, t1 - t0)
    return pts[-1][1]


def wipe(kind, p, soft=0.03):
    """A wipe state that is valid for any progress (hidden below 0, complete above 1)."""
    return {"wipe": (kind, min(1.0, max(0.0, p)), soft)}


# ---- clips ----------------------------------------------------------------------------------------------------
class Clip:
    def __init__(self, style, dur, scheme="main", seed="clip", transparent=False, size=(W, H), fps=FPS):
        self.style, self.dur, self.fps = style, dur, fps
        self.W, self.H = size
        self.n = int(round(dur * fps))
        self.seed = seed
        self.transparent = transparent
        self.art = Art(style, self.W, self.H, scheme=scheme, scale=self.H / 1440.0, grain=False, seed=seed)
        self.art.tag = "main"
        self.animate = lambda t: {}
        self._ready = False
        self.live_grain = not transparent
        self.shutter = SHUTTER

    # ---- one-off preparation (runs before the worker pool forks, so the big arrays are shared) -------------
    def prepare(self):
        if self._ready:
            return
        art, st, sch = self.art, self.style, self.art.sch
        s = art.s
        self.riso = sch["mode"] == "riso"
        self.L = []
        for k, layer in enumerate(art.layers):
            role, x0, y0, m, size, opts = layer
            a = m if opts.get("crisp") else press(m, size, s, seed=f"{self.seed}-{k}", bleed=st.bleed * opts.get("bleed", 1.0),
                                                   rough=st.rough * opts.get("rough", 1.0), wear=st.wear * opts.get("wear", 1.0))
            col = hex_rgb(opts["colour"]) if role == "colour" else None
            self.L.append({"tag": opts.get("tag", "main"), "role": role, "x0": x0, "y0": y0, "a": np.ascontiguousarray(a * opts.get("alpha", 1.0), np.float32),
                           "col": col, "opts": opts, "coords": {}})
        if self.riso:
            paper = paper_texture(self.H, self.W, s, self.seed)
            self.field = (sch["field"][None, None, :] * paper[..., None]).astype(np.float32)
            r = rng_for("riso", self.seed)
            self.dens, self.mott = {}, {}
            for name in ("second", "ink"):
                self.dens[name] = (0.978 + 0.022 * np.clip(soft_noise(self.H, self.W, r, 420 * s), -2, 1)).astype(np.float32)
                fine = grain_field(self.H, self.W, f"{self.seed}-{name}", 0.7 * s)
                self.mott[name] = (1.0 - 0.10 * st.wear * np.clip(fine - 0.4, 0, 2.5)).astype(np.float32)
            self.flood = sch.get("flood")
            self.misreg = sch.get("misregister", (2.0, 1.4))
        else:
            self.field = np.empty((self.H, self.W, 3), np.float32)
            self.field[:] = sch["field"]
        if self.live_grain:
            self.G = [grain_field(self.H, self.W, f"{self.seed}-grain-{k}", st.grain_sigma * s).astype(np.float16) for k in range(GRAIN_SETS)]
            r = rng_for("walk", self.seed)
            uses = self.n // GRAIN_SETS + 2
            steps = r.integers(8, 25, (uses, GRAIN_SETS, 2)) * r.choice([-1, 1], (uses, GRAIN_SETS, 2))
            self.walk = np.cumsum(steps, axis=0)
        self._ready = True

    # ---- states -------------------------------------------------------------------------------------------------
    @staticmethod
    def _state(S, tag):
        st = S.get(tag)
        if st is None and tag.endswith("~"):
            st = S.get(tag[:-1])
        if st is None:
            st = {"a": 0.0} if S.get("_hide_missing") else {}
        return st

    def _states(self, t):
        """animate() at the sample times across the shutter, centred on t."""
        if self.shutter <= 0:
            return [self.animate(t)]
        return [self.animate(t + (j / (NS - 1) - 0.5) * self.shutter / self.fps) for j in range(NS)]

    @staticmethod
    def _corners(L, st):
        hh, ww = L["a"].shape
        x0, y0 = L["x0"], L["y0"]
        dx, dy, sc, rot = st.get("dx", 0.0), st.get("dy", 0.0), st.get("s", 1.0), st.get("r", 0.0)
        cx, cy = st.get("cx", x0 + ww / 2), st.get("cy", y0 + hh / 2)
        co, si = sc * math.cos(math.radians(rot)), sc * math.sin(math.radians(rot))
        return [(cx + co * (px - cx) - si * (py - cy) + dx, cy + si * (px - cx) + co * (py - cy) + dy)
                for px, py in ((x0, y0), (x0 + ww, y0), (x0, y0 + hh), (x0 + ww, y0 + hh))]

    # ---- a layer's alpha for one state --------------------------------------------------------------------------
    def _alpha(self, L, stt, op=None, wspan=None):
        """-> (x0, y0, alpha patch) or None. op: opacity to use instead of the state's. wspan: (kind, p_lo, p_hi, soft),
        the wipe's progress at the start and end of the shutter (the edge is spread across the distance it travels)."""
        a = L["a"]
        x0, y0 = L["x0"], L["y0"]
        op = stt.get("a", 1.0) if op is None else op
        if op <= 0.003:
            return None
        if wspan is None and stt.get("wipe"):
            kind, p, soft = stt["wipe"]
            wspan = (kind, p, p, soft)
        if wspan:
            kind, lo, hi, soft = wspan
            if hi <= 0:
                return None
            if lo < 1:
                c = L["coords"].get(kind)
                if c is None:
                    hh, ww = a.shape
                    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
                    vx, vy = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1), "strip_up": (0.4472, -0.8944),
                              "bar_down": (0.4472, 0.8944), "diag": (0.8944, -0.4472)}[kind]
                    c = xx * vx + yy * vy
                    ink = a > 0.02
                    lo_c, hi_c = (float(c[ink].min()), float(c[ink].max())) if ink.any() else (0.0, 1.0)
                    c = (c - lo_c) / max(1e-6, hi_c - lo_c)
                    L["coords"][kind] = c
                e0, e1 = lo * (1 + 2 * soft) - soft, hi * (1 + 2 * soft) - soft
                a = a * (1 - smoothstep(e0 - soft, e1 + soft, c))
        if op < 1:
            a = a * op
        dx, dy, sc, rot = stt.get("dx", 0.0), stt.get("dy", 0.0), stt.get("s", 1.0), stt.get("r", 0.0)
        if abs(sc - 1) > 1e-4 or abs(dx) > 0.004 or abs(dy) > 0.004 or abs(rot) > 1e-3:
            hh, ww = a.shape
            cx, cy = stt.get("cx", x0 + ww / 2), stt.get("cy", y0 + hh / 2)        # scale / turn about this point (frame coords)
            co, si = sc * math.cos(math.radians(rot)), sc * math.sin(math.radians(rot))
            px = [cx + co * (x0 + u - cx) - si * (y0 + v - cy) + dx for u, v in ((0, 0), (ww, 0), (0, hh), (ww, hh))]
            py = [cy + si * (x0 + u - cx) + co * (y0 + v - cy) + dy for u, v in ((0, 0), (ww, 0), (0, hh), (ww, hh))]
            nx0, ny0 = int(math.floor(min(px))) - 2, int(math.floor(min(py))) - 2
            nw, nh = int(math.ceil(max(px))) - nx0 + 3, int(math.ceil(max(py))) - ny0 + 3
            M = np.float32([[co, -si, cx + co * (x0 - cx) - si * (y0 - cy) + dx - nx0],
                            [si, co, cy + si * (x0 - cx) + co * (y0 - cy) + dy - ny0]])
            a = np.clip(cv2.warpAffine(a, M, (nw, nh), flags=cv2.INTER_CUBIC), 0.0, 1.0)
            x0, y0 = nx0, ny0
        hh, ww = a.shape
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(self.W, x0 + ww), min(self.H, y0 + hh)
        if cx1 <= cx0 or cy1 <= cy0:
            return None
        return cx0, cy0, a[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]

    # ---- a layer's alpha for a whole frame, with motion blur ----------------------------------------------------
    def _layer(self, L, SS):
        tag = L["tag"]
        sts = [self._state(S, tag) for S in SS]
        first, mid, last = sts[0], sts[len(sts) // 2], sts[-1]
        moving = 0.0
        if len(sts) > 1 and any(k in first or k in last for k in ("dx", "dy", "s", "r")):
            moving = max(math.hypot(ax - bx, ay - by) for (ax, ay), (bx, by) in zip(self._corners(L, first), self._corners(L, last)))
        if moving < 0.75:
            ops = [st.get("a", 1.0) for st in (first, mid, last)]
            op = ops[1] if max(ops) - min(ops) < 1e-4 else float(np.mean(ops))
            wspan = None
            w = next((st["wipe"] for st in (mid, first, last) if st.get("wipe")), None)
            if w:
                ps = [st["wipe"][1] if st.get("wipe") else (1.0 if st.get("a", 1.0) > 0.003 else 0.0) for st in (first, last)]
                wspan = (w[0], min(ps), max(ps), w[2])
            return self._alpha(L, mid, op=op if op > 0.003 else max(ops), wspan=wspan)
        n = int(min(NS, max(3, math.ceil(moving / 1.6) + 1)))
        idx = np.unique(np.round(np.linspace(0, len(sts) - 1, n)).astype(int))
        parts = [r for r in (self._alpha(L, sts[j]) for j in idx) if r is not None]
        if not parts:
            return None
        x0 = min(p[0] for p in parts)
        y0 = min(p[1] for p in parts)
        x1 = max(p[0] + p[2].shape[1] for p in parts)
        y1 = max(p[1] + p[2].shape[0] for p in parts)
        acc = np.zeros((y1 - y0, x1 - x0), np.float32)
        for px, py, a in parts:
            acc[py - y0:py - y0 + a.shape[0], px - x0:px - x0 + a.shape[1]] += a
        acc *= 1.0 / len(idx)
        return x0, y0, acc

    # ---- frames ----------------------------------------------------------------------------------------------------
    def frame(self, i):
        """-> uint8 RGB (or RGBA when transparent) for frame i."""
        self.prepare()
        t = i / self.fps
        SS = self._states(t)
        S = SS[len(SS) // 2]
        g = S.get("_", {})
        sch = self.art.sch
        if self.transparent:
            return self._frame_alpha(SS)
        self._shift = tuple(int(v) for v in self.walk[i // GRAIN_SETS, i % GRAIN_SETS]) if self.live_grain else (0, 0)
        black = g.get("black", 0.0)                     # 1 = the style's dark neutral instead of the field
        if black >= 1.0:
            img = np.empty((self.H, self.W, 3), np.float32)
            img[:] = self.style.rgb["dark"] * 0.55
        elif self.riso:
            img = self._riso(SS)
        else:
            img = self.field.copy()
            for L in self.L:
                if L["role"] == "clear_second":
                    continue
                r = self._layer(L, SS)
                if r is None:
                    continue
                x0, y0, a = r
                col = sch["field"] if L["role"] == "field" else L["col"] if L["role"] == "colour" else sch[L["role"]]
                reg = img[y0:y0 + a.shape[0], x0:x0 + a.shape[1]]
                reg[:] = reg * (1 - a[..., None]) + col * a[..., None]
        if 0 < black < 1:
            img = img * (1 - black) + self.style.rgb["dark"] * 0.55 * black
        ex = g.get("exposure", 1.0)
        if ex != 1.0:
            img = img * ex
        if self.live_grain:
            gg = np.roll(np.roll(self.G[i % GRAIN_SETS], self._shift[0], 0), self._shift[1], 1).astype(np.float32)
            img = apply_grain(img, gg, self.style.grain_amount * VIDEO_GRAIN * sch.get("grain_gain", 1.0) * g.get("grain", 1.0), self.style.grain_lift)
        return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)

    def _riso(self, SS):
        S = SS[len(SS) // 2]
        sch = self.art.sch
        plates = {"ink": np.zeros((self.H, self.W), np.float32), "second": np.zeros((self.H, self.W), np.float32)}
        flood_a = S.get("_", {}).get("flood", 1.0)
        if self.flood:
            plates[self.flood][:] = flood_a
        box = [self.W, self.H, 0, 0]
        extra = []
        for L in self.L:
            r = self._layer(L, SS)
            if r is None:
                continue
            x0, y0, a = r
            sl = (slice(y0, y0 + a.shape[0]), slice(x0, x0 + a.shape[1]))
            box = [min(box[0], x0), min(box[1], y0), max(box[2], x0 + a.shape[1]), max(box[3], y0 + a.shape[0])]
            role = L["role"]
            if role == "field":
                for p in plates.values():
                    p[sl] *= (1 - a)
            elif role == "clear_second":
                plates["second"][sl] *= (1 - a)
            elif role == "colour":
                extra.append((sl, a, L["col"]))
            else:
                if L["opts"].get("knockout", (role == "ink") != bool(self.flood)):
                    plates["second" if role == "ink" else "ink"][sl] *= (1 - a)
                plates[role][sl] = np.maximum(plates[role][sl], a)
        img = self.field.copy()
        if self.flood:
            box = [0, 0, self.W, self.H]
        pad = int(8 * self.art.s)
        bx0, by0, bx1, by1 = max(0, box[0] - pad), max(0, box[1] - pad), min(self.W, box[2] + pad), min(self.H, box[3] + pad)
        if bx1 > bx0 and by1 > by0:
            sl = (slice(by0, by1), slice(bx0, bx1))
            reg = img[sl]
            for name in ("second", "ink"):
                a = plates[name][sl]
                if name == "second":
                    dx, dy = self.misreg
                    M = np.float32([[1, 0, dx * self.art.s], [0, 1, dy * self.art.s]])
                    a = cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                mott = self.mott[name]
                if self.flood and self.live_grain:
                    # a full flood of ink: its speckle moves with the grain texture in use, so the encoder can follow both together
                    mott = np.roll(np.roll(mott, self._shift[0], 0), self._shift[1], 1)
                a = a * self.dens[name][sl] * mott[sl]
                reg *= 1.0 - a[..., None] * (1.0 - sch[name][None, None, :])
            for sl2, a, col in extra:
                r2 = img[sl2]
                r2[:] = r2 * (1 - a[..., None]) + col * a[..., None]
        return img

    def _frame_alpha(self, SS):
        """Transparent background: straight-alpha RGBA. Colours are laid over each other normally."""
        S = SS[len(SS) // 2]
        sch = self.art.sch
        rgb = np.zeros((self.H, self.W, 3), np.float32)        # premultiplied while compositing
        al = np.zeros((self.H, self.W), np.float32)
        for L in self.L:
            r = self._layer(L, SS)
            if r is None:
                continue
            x0, y0, a = r
            sl = (slice(y0, y0 + a.shape[0]), slice(x0, x0 + a.shape[1]))
            if L["role"] in ("clear_second", "field"):             # erase what is underneath (a knock-out)
                rgb[sl] *= (1 - a[..., None])
                al[sl] *= (1 - a)
                continue
            col = L["col"] if L["role"] == "colour" else sch[L["role"]]
            rgb[sl] = rgb[sl] * (1 - a[..., None]) + col * a[..., None]
            al[sl] = al[sl] * (1 - a) + a
        fade = S.get("_", {}).get("fade", 1.0)
        out = np.empty((self.H, self.W, 4), np.uint8)
        straight = rgb / np.maximum(al, 1e-4)[..., None]
        straight[al < 1e-4] = sch["ink"]
        out[..., :3] = np.clip(straight * 255 + 0.5, 0, 255)
        out[..., 3] = np.clip(al * fade * 255 + 0.5, 0, 255)
        return out

    # ---- encoding ---------------------------------------------------------------------------------------------
    def _frames(self, workers):
        self.prepare()
        ctx = mp.get_context("fork")
        global _CLIP
        _CLIP = self
        with ctx.Pool(workers, initializer=_init) as pool:
            for fr in pool.imap(_render, range(self.n), chunksize=1):
                yield fr

    def render_h264(self, path, wav=None, workers=4, log=None):
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}",
               "-r", str(self.fps), "-i", "-"]
        if wav:
            cmd += ["-i", str(wav), "-map", "0:v:0", "-map", "1:a:0"]
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p"] + X264
        if wav:
            cmd += ["-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2"]
        cmd += ["-movflags", "+faststart", str(path)]
        self._pipe(cmd, workers, path)

    def render_prores(self, path, wav=None, workers=4, q=11):
        """ProRes 4444 with an alpha channel (.mov). Straight (unmatted) alpha."""
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{self.W}x{self.H}",
               "-r", str(self.fps), "-i", "-"]
        if wav:
            cmd += ["-i", str(wav), "-map", "0:v:0", "-map", "1:a:0"]
        cmd += ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", "-qscale:v", str(q),
                "-alpha_bits", "16", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        if wav:
            cmd += ["-c:a", "pcm_s24le", "-ar", "48000", "-ac", "2"]
        cmd += [str(path)]
        self._pipe(cmd, workers, path)

    def _pipe(self, cmd, workers, path):
        t0 = time.time()
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for k, fr in enumerate(self._frames(workers)):
            proc.stdin.write(fr)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed for {path}")
        print(f"    {path.name}: {self.n} frames in {time.time() - t0:.0f}s, {path.stat().st_size / 1e6:.1f} MB", flush=True)

    def still(self, i):
        """One frame as an image array (for test sheets and poster frames)."""
        return self.frame(i)


_CLIP = None


def _init():
    cv2.setNumThreads(1)


def _render(i):
    return _CLIP.frame(i).tobytes()
