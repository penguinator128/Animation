"""
Moving pictures: 4K / 24 fps clips rendered frame by frame (each frame is a pure function of its time) and piped
straight into ffmpeg.

    clip = Clip(style, dur=2.0, seed="intro-a")
    clip.art.tag = "logo";  clip.art.logo(...)          # build the artwork with the normal Art tools, tagging the parts
    clip.animate = lambda t: {"logo": {"a": 1, "s": 1.1}, "_": {"exposure": 1.0}}
    clip.render_h264(path, wav)                          # or clip.render_prores(path, wav) for a transparent .mov

Live grain: one tileable grain texture that jumps to a new random position every frame. Every frame shows a
different patch of grain (so it flickers like film), but because it is the same texture moved, the encoder can
follow it, and a 4K clip is about a ninth of the size it would be with unrelated noise per frame.
"""
import math
import multiprocessing as mp
import subprocess
import time

import cv2
import numpy as np

from .core import Art, apply_grain, grain_field, paper_texture, press, rng_for, smoothstep, soft_noise, hex_rgb

W, H, FPS = 3840, 2160, 24
SCALE = H / 1440.0                   # 4K is design scale 1.5

X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-x264-params", "keyint=240:me=umh:merange=24:subme=8",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def ease_out(x, p=3):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** p


def ease_in_out(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_out_back(x, k=1.70158):
    x = min(1.0, max(0.0, x))
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def keys(t, pts):
    """Piecewise-linear keyframes [(time, value), ...]."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / max(1e-9, t1 - t0)
    return pts[-1][1]


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
            col = None
            if role == "colour":
                col = hex_rgb(opts["colour"])
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
            self.G = grain_field(self.H, self.W, self.seed, st.grain_sigma * s)
            r = rng_for("walk", self.seed)
            steps = r.integers(6, 15, (self.n + 2, 2)) * r.choice([-1, 1], (self.n + 2, 2))
            self.walk = np.cumsum(steps, axis=0)
        self._ready = True

    # ---- a layer's alpha at time t, after its tag's animation state ---------------------------------------------
    def _alpha(self, L, stt):
        a = L["a"]
        x0, y0 = L["x0"], L["y0"]
        op = stt.get("a", 1.0)
        if op <= 0.003:
            return None
        wipe = stt.get("wipe")
        if wipe:
            kind, p, soft = wipe
            if p <= 0:
                return None
            if p < 1:
                c = L["coords"].get(kind)
                if c is None:
                    hh, ww = a.shape
                    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
                    vx, vy = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1), "strip_up": (0.4472, -0.8944),
                              "bar_down": (0.4472, 0.8944), "diag": (0.8944, -0.4472)}[kind]
                    c = xx * vx + yy * vy
                    ink = a > 0.02
                    lo, hi = (float(c[ink].min()), float(c[ink].max())) if ink.any() else (0.0, 1.0)
                    c = (c - lo) / max(1e-6, hi - lo)
                    L["coords"][kind] = c
                edge = p * (1 + 2 * soft) - soft
                a = a * (1 - smoothstep(edge - soft, edge + soft, c))
        if op < 1:
            a = a * op
        dx, dy, sc = stt.get("dx", 0.0), stt.get("dy", 0.0), stt.get("s", 1.0)
        if abs(sc - 1) > 1e-4 or abs(dx) > 0.01 or abs(dy) > 0.01:
            hh, ww = a.shape
            cx, cy = stt.get("cx", x0 + ww / 2), stt.get("cy", y0 + hh / 2)        # scale about this point (frame coords)
            nx0 = int(math.floor(cx + (x0 - cx) * sc + dx)) - 1
            ny0 = int(math.floor(cy + (y0 - cy) * sc + dy)) - 1
            nw, nh = int(math.ceil(ww * sc)) + 3, int(math.ceil(hh * sc)) + 3
            M = np.float32([[sc, 0, cx + (x0 - cx) * sc + dx - nx0], [0, sc, cy + (y0 - cy) * sc + dy - ny0]])
            a = cv2.warpAffine(a, M, (nw, nh), flags=cv2.INTER_LINEAR)
            x0, y0 = nx0, ny0
        # clip to the frame
        hh, ww = a.shape
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(self.W, x0 + ww), min(self.H, y0 + hh)
        if cx1 <= cx0 or cy1 <= cy0:
            return None
        return cx0, cy0, a[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]

    @staticmethod
    def _state(S, tag):
        st = S.get(tag)
        if st is None and tag.endswith("~"):
            st = S.get(tag[:-1])
        if st is None:
            st = {"a": 0.0} if S.get("_hide_missing") else {}
        return st

    def frame(self, i):
        """-> uint8 RGB (or RGBA when transparent) for frame i."""
        self.prepare()
        t = i / self.fps
        S = self.animate(t)
        g = S.get("_", {})
        sch = self.art.sch
        if self.transparent:
            return self._frame_alpha(S)
        black = g.get("black", 0.0)                     # 1 = the style's dark neutral instead of the field
        if black >= 1.0:
            img = np.empty((self.H, self.W, 3), np.float32)
            img[:] = self.style.rgb["dark"] * 0.55
        elif self.riso:
            img = self._riso(S)
        else:
            img = self.field.copy()
            for L in self.L:
                if L["role"] == "clear_second":
                    continue
                r = self._alpha(L, self._state(S, L["tag"]))
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
            oy, ox = self.walk[i % len(self.walk)]
            gg = np.roll(np.roll(self.G, int(oy), 0), int(ox), 1)
            img = apply_grain(img, gg, self.style.grain_amount * sch.get("grain_gain", 1.0) * g.get("grain", 1.0), self.style.grain_lift)
        sh = g.get("shake")
        out = np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
        if sh and (abs(sh[0]) >= 1 or abs(sh[1]) >= 1):
            out = np.roll(np.roll(out, int(round(sh[1])), 0), int(round(sh[0])), 1)
        return out

    def _riso(self, S):
        sch = self.art.sch
        plates = {"ink": np.zeros((self.H, self.W), np.float32), "second": np.zeros((self.H, self.W), np.float32)}
        flood_a = S.get("_", {}).get("flood", 1.0)
        if self.flood:
            plates[self.flood][:] = flood_a
        box = [self.W, self.H, 0, 0]
        extra = []
        hide = S.get("_hide_missing")
        for L in self.L:
            r = self._alpha(L, self._state(S, L["tag"]))
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
                a = a * self.dens[name][sl] * self.mott[name][sl]
                reg *= 1.0 - a[..., None] * (1.0 - sch[name][None, None, :])
            for sl2, a, col in extra:
                r2 = img[sl2]
                r2[:] = r2 * (1 - a[..., None]) + col * a[..., None]
        return img

    def _frame_alpha(self, S):
        """Transparent background: straight-alpha RGBA. Colours are laid over each other normally."""
        sch = self.art.sch
        rgb = np.zeros((self.H, self.W, 3), np.float32)        # premultiplied while compositing
        al = np.zeros((self.H, self.W), np.float32)
        hide = S.get("_hide_missing")
        for L in self.L:
            if L["role"] == "clear_second":
                r = self._alpha(L, self._state(S, L["tag"]))
                if r is not None:                                   # erase what is underneath (the shadow in the holes)
                    x0, y0, a = r
                    sl = (slice(y0, y0 + a.shape[0]), slice(x0, x0 + a.shape[1]))
                    rgb[sl] *= (1 - a[..., None])
                    al[sl] *= (1 - a)
                continue
            r = self._alpha(L, self._state(S, L["tag"]))
            if r is None:
                continue
            x0, y0, a = r
            sl = (slice(y0, y0 + a.shape[0]), slice(x0, x0 + a.shape[1]))
            if L["role"] == "field":                                # a knock-out: cut a hole
                rgb[sl] *= (1 - a[..., None])
                al[sl] *= (1 - a)
                continue
            col = L["col"] if L["role"] == "colour" else sch[L["role"]]
            rgb[sl] = rgb[sl] * (1 - a[..., None]) + col * a[..., None]
            al[sl] = al[sl] * (1 - a) + a
        g = S.get("_", {})
        fade = g.get("fade", 1.0)
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
