"""
Sound design. One "kit" of instruments per style, all synthesised here (no samples):

    RED       warm analogue thuds, soft vinyl crackle, gentle tape hiss, a friendly low chime
    YELLOW    bright clapperboard snaps, crisp finger clicks, a sunny marimba / pluck, a light cheerful chime
    WILDCARD  print-press thunks, paper slaps, soft stamps, a gentle mallet chime

Every style plays the same two-note ASTRIS motif (a fourth up, "hel-lo") in its own voice.
build(style) writes the sound pack: whooshes, risers, impacts, clicks, chimes and tactile sounds (48 kHz, 24-bit, peak -1 dB).
The intro stingers are written by assets/intros.py with the same kit.
"""
import numpy as np
from scipy import signal

from engine import sfx as X
from engine import sound as S
from engine.paths import out

SR = S.SR
PEAK_DB = -1.0


def norm(x, peak_db=PEAK_DB):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = np.stack([x, x])
    pk = np.max(np.abs(x)) + 1e-12
    return x * (10 ** (peak_db / 20) / pk)


def fade_tail(x, ms=30):
    n = int(ms / 1000 * SR)
    x = np.array(x, np.float64)
    if n > 0 and x.shape[-1] > n:
        x[..., -n:] *= np.linspace(1, 0, n) ** 2
    if n > 0:
        x[..., :32] *= np.linspace(0, 1, 32)
    return x


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def tone(f, dur, partials, decays):
    t = S.tt(dur)
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for (r, a), d in zip(partials, decays)) * np.minimum(1, t / 0.002)


def wow(x, depth=0.0018, rate=0.7, seed=1):
    """Gentle tape wow: a slow pitch wobble."""
    n = len(x)
    t = np.arange(n) / SR
    d = depth * SR / (2 * np.pi * rate) * np.sin(2 * np.pi * rate * t + seed)
    idx = np.clip(np.arange(n) + d, 0, n - 1)
    return np.interp(idx, np.arange(n), x)


class Kit:
    """The instruments of one style. Every method returns a mono or stereo float array at 48 kHz."""

    def __init__(self, style):
        self.k = style.key
        self.root = {"red": 50, "yellow": 62, "wildcard": 57}[self.k]          # D3, D4, A3

    # ---- pitched: the chime and the motif ---------------------------------------------------------------
    def chime(self, midi_note=None, dur=3.0):
        f = S.midi(midi_note if midi_note is not None else self.root + 12)
        if self.k == "red":          # low, round, a little wobbly: like a bell recorded to tape
            x = tone(f, dur, [(1, 1.0), (2.0, 0.42), (3.01, 0.20), (4.2, 0.08)], [1.6, 0.9, 0.5, 0.25])
            x = wow(S.sat(x * 0.9, 1.4), 0.0016, 0.8)
            return S.sos(x, "lowpass", 4200, 2)
        if self.k == "yellow":       # marimba with a little glassy sparkle on top
            x = tone(f, dur, [(1, 1.0), (4.0, 0.30), (10.0, 0.07)], [0.75, 0.16, 0.05])
            x = x + 0.18 * tone(f * 2, dur, [(1, 1.0), (2.76, 0.3)], [1.2, 0.5])
            return x
        # wildcard: soft mallet on a vibraphone bar, slow tremolo
        t = S.tt(dur)
        x = tone(f, dur, [(1, 1.0), (4.0, 0.22), (2.0, 0.12)], [1.9, 0.5, 0.9])
        return x * (1 - 0.22 * (0.5 + 0.5 * np.sin(2 * np.pi * 4.6 * t)))

    def motif(self, dur=3.2, gap=0.19, octave=0):
        """The two-note ASTRIS motif: a fourth up (sol -> do)."""
        r = self.root + 12 + octave
        n = int(dur * SR)
        out_ = np.zeros(n)
        a, b = self.chime(r - 5, dur), self.chime(r, dur - gap)
        out_[: len(a)] += a[:n] * 0.8
        i = int(gap * SR)
        out_[i:i + len(b)] += b[: n - i]
        return out_

    def chord(self, dur=4.0):
        """A warm held chord under the motif (root, fifth, tenth)."""
        r = self.root
        if self.k == "red":
            return S.pad([S.midi(n) for n in (r - 12, r, r + 7, r + 16)], dur, attack=0.5, release=1.8, cutoff=(250, 1500), level=1.0, seed=11)
        if self.k == "yellow":
            return S.pad([S.midi(n) for n in (r - 12, r, r + 7, r + 16, r + 19)], dur, attack=0.25, release=1.6, cutoff=(500, 3200), level=1.0, seed=12)
        return S.pad([S.midi(n) for n in (r - 12, r, r + 7, r + 14)], dur, attack=0.4, release=1.8, cutoff=(300, 2000), level=1.0, seed=13)

    def pluck(self, midi_note, dur=1.2):
        """Karplus-Strong pluck (yellow) / marimba note / mallet note."""
        if self.k != "yellow":
            return self.chime(midi_note, dur)
        f = S.midi(midi_note)
        n = int(dur * SR)
        period = int(SR / f)
        buf = np.random.default_rng(int(midi_note)).uniform(-1, 1, period)
        out_ = np.empty(n)
        for i in range(n):
            out_[i] = buf[i % period]
            buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
        return S.sos(out_, "lowpass", 5000, 2) * np.minimum(1, np.arange(n) / 60)

    # ---- hits ---------------------------------------------------------------------------------------------
    def hit(self, size=1.0, seed=1):
        """The satisfying stamp: the style's main impact."""
        r = np.random.default_rng(seed)
        d = 0.9
        t = S.tt(d)
        if self.k == "red":          # warm analogue thud: a sine that drops, soft knock, tape saturation
            body = np.sin(2 * np.pi * (46 * t + (92 - 46) * 0.05 * (1 - np.exp(-t / 0.05)))) * np.exp(-t / (0.22 * size))
            knock = S.sos(r.standard_normal(len(t)), "bandpass", (140, 900), 2) * np.exp(-t / 0.018) * 0.7
            return S.sat(body * 1.3 + knock, 1.8) * np.minimum(1, t / 0.0015)
        if self.k == "yellow":       # clapperboard: a sharp wooden crack with a short woody ring
            crack = S.sos(r.standard_normal(len(t)), "bandpass", (900, 5200), 2) * np.exp(-t / 0.007)
            wood = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / dd) for f, a, dd in ((520, 0.8, 0.035), (860, 0.5, 0.025), (1730, 0.3, 0.015)))
            body = np.sin(2 * np.pi * 120 * t) * np.exp(-t / 0.05) * 0.5 * size
            return (crack * 1.2 + wood * 0.8 + body) * np.minimum(1, t / 0.0006)
        # wildcard: print press: low thunk + mechanical clack + a breath of air
        thunk = np.sin(2 * np.pi * (58 * t + 30 * 0.04 * (1 - np.exp(-t / 0.04)))) * np.exp(-t / (0.16 * size))
        clack = S.sos(r.standard_normal(len(t)), "bandpass", (500, 2600), 2) * np.exp(-t / 0.012) * 0.6
        air = S.sos(r.standard_normal(len(t)), "highpass", 3000, 2) * np.exp(-((t - 0.09) / 0.06) ** 2) * 0.10
        return (thunk * 1.2 + clack + air) * np.minimum(1, t / 0.001)

    def tap(self, seed=2, pitch=1.0):
        """A small, friendly landing sound for text."""
        r = np.random.default_rng(seed)
        d = 0.3
        t = S.tt(d)
        if self.k == "red":
            x = np.sin(2 * np.pi * 110 * pitch * t) * np.exp(-t / 0.06) + S.sos(r.standard_normal(len(t)), "bandpass", (300, 1400), 2) * np.exp(-t / 0.01) * 0.4
            return S.sat(x, 1.5)
        if self.k == "yellow":
            return X.snap(seed)
        return X.paper_slap(seed, 0.8)

    def tick(self, seed=3, pitch=1.0):
        """The tiniest sound: one typed letter, one punched hole."""
        r = np.random.default_rng(seed)
        d = 0.09
        t = S.tt(d)
        if self.k == "red":          # a soft tape-recorder key
            x = S.sos(r.standard_normal(len(t)), "bandpass", (700 * pitch, 2400 * pitch), 2) * np.exp(-t / 0.006) + 0.5 * np.sin(2 * np.pi * 240 * pitch * t) * np.exp(-t / 0.012)
        elif self.k == "yellow":     # a crisp click
            x = S.sos(r.standard_normal(len(t)), "bandpass", (1800 * pitch, 6500), 2) * np.exp(-t / 0.003) + 0.3 * np.sin(2 * np.pi * 1500 * pitch * t) * np.exp(-t / 0.006)
        else:                        # a small rubber stamp
            x = S.sos(r.standard_normal(len(t)), "bandpass", (350 * pitch, 1500 * pitch), 2) * np.exp(-t / 0.010) + 0.6 * np.sin(2 * np.pi * 170 * pitch * t) * np.exp(-t / 0.02)
        return x * np.minimum(1, t / 0.0008)

    def whoosh(self, dur=0.6, seed=4, up=True):
        lo, hi = {"red": (180, 1800), "yellow": (500, 5200), "wildcard": (260, 2600)}[self.k]
        return S.whoosh(dur, peak=0.6 if up else 0.4, f_lo=lo, f_hi=hi, q=0.9, pan_from=-0.6, pan_to=0.6, seed=seed)

    def riser(self, dur=1.0, seed=5):
        lo, hi = {"red": (120, 1100), "yellow": (300, 3600), "wildcard": (180, 1800)}[self.k]
        return S.riser(dur, lo, hi, 1.0, seed)

    def bed(self, dur, seed=6):
        """The style's room: what you hear under everything, very quietly."""
        if self.k == "red":
            return X.vinyl_crackle(dur, seed) * 0.9 + X.tape_hiss(dur, seed + 1) * 0.5
        if self.k == "yellow":       # a bright, airy room tone
            return S.sos(S.noise(dur, "pink", seed), "bandpass", (400, 6000), 2) * 0.25
        return X.paper_rustle(dur, seed, density=5) * 0.5 + S.sos(S.noise(dur, "pink", seed), "lowpass", 900, 2) * 0.2

    def swell(self, dur=0.7, seed=7):
        return S.reverse_swell(dur, 1.0, seed, {"red": 1400, "yellow": 3200, "wildcard": 2000}[self.k])


def mix_master(m, tail=0.25, wet=None, ir=None, kit=None):
    k = kit.k if kit else "red"
    ir = ir or {"red": 1.6, "yellow": 1.2, "wildcard": 1.4}[k]
    wet = wet if wet is not None else {"red": 0.55, "yellow": 0.45, "wildcard": 0.5}[k]
    mix = m.master(ir_seconds=ir, wet=wet, peak_db=PEAK_DB, tail_fade=tail)
    assert np.max(np.abs(mix)) <= 10 ** (PEAK_DB / 20) + 1e-6
    return mix


def save(path, x):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = np.stack([x, x])
    assert np.max(np.abs(x)) < 0.9999, f"{path.name} clips"
    S.write_wav24(path, x)
    return path


def build(style):
    """The style's sound pack (everything except the intro stingers, which assets/intros.py writes)."""
    kit = Kit(style)
    k = style.key
    n = 0

    def put(sub, name, x, tail=30):
        nonlocal n
        save(out(k, "sound", sub) / f"astris-{k}-{name}.wav", norm(fade_tail(x, tail)))
        n += 1

    def wet(x, t_extra=0.8, send=0.35, gain=1.0):
        d = (x.shape[-1] if hasattr(x, "shape") else len(x)) / SR + t_extra
        m = S.Mix(d)
        m.add(x, 0.0, gain=gain, send=send)
        return mix_master(m, tail=0.15, kit=kit)

    for nm, d in (("short-0.4s", 0.4), ("medium-0.8s", 0.8), ("long-1.5s", 1.5)):
        put("whooshes", f"whoosh-{nm}", wet(kit.whoosh(d, seed=20 + int(d * 10)), 0.5, 0.3))
    for nm, d in (("1s", 1.0), ("2s", 2.0)):
        put("risers", f"riser-{nm}", wet(kit.riser(d, seed=30 + int(d)), 0.4, 0.3))
    for nm, sz, gain in (("soft", 0.7, 0.6), ("medium", 1.0, 0.85), ("big", 1.5, 1.0)):
        x = kit.hit(sz, seed=40)
        if nm == "big":
            sub = S.sub_drop(1.2, 70, 36, 0.3, 0.8) * 0.6
            n_ = max(len(x), len(sub))
            x = np.pad(x, (0, n_ - len(x))) + np.pad(sub, (0, n_ - len(sub)))
        put("impacts", f"impact-{nm}", wet(x, 1.0, 0.3))
    for j in range(3):
        put("clicks", f"click-{j + 1}", wet(kit.tick(seed=50 + j, pitch=0.85 + 0.15 * j), 0.25, 0.15), tail=10)
    put("clicks", "tap", wet(kit.tap(seed=54), 0.4, 0.2))
    put("chimes", "chime-single", wet(kit.chime(dur=3.0), 1.0, 0.5))
    put("chimes", "chime-motif", wet(kit.motif(3.4), 1.0, 0.5))
    put("chimes", "chime-motif-with-chord", chord_motif(kit))
    # tactile: the sounds that make each style feel like itself
    if k == "red":
        put("tactile", "vinyl-crackle-loop-10s", loopable(X.vinyl_crackle(10.5, 61)), tail=0)
        put("tactile", "tape-hiss-loop-10s", loopable(X.tape_hiss(10.5, 62)), tail=0)
        put("tactile", "needle-drop", wet(needle_drop(), 0.6, 0.2))
        put("tactile", "tape-stop", wet(tape_stop(kit), 0.3, 0.2))
        put("tactile", "analogue-thud", wet(kit.hit(1.2, 63), 0.8, 0.25))
    elif k == "yellow":
        put("tactile", "clapper-snap-1", wet(kit.hit(1.0, 64), 0.5, 0.25))
        put("tactile", "clapper-snap-2-double", wet(double(kit.hit(0.8, 65), 0.11), 0.5, 0.25))
        put("tactile", "finger-click", wet(X.snap(66), 0.4, 0.3))
        put("tactile", "marimba-note", wet(kit.chime(74, 2.0), 0.6, 0.4))
        put("tactile", "pluck-riff", wet(riff(kit), 0.8, 0.4))
    else:
        put("tactile", "press-thunk", wet(kit.hit(1.2, 67), 0.6, 0.25))
        put("tactile", "paper-slap", wet(X.paper_slap(68, 1.0), 0.4, 0.2))
        put("tactile", "stamp", wet(stamp(kit), 0.4, 0.2))
        put("tactile", "paper-rustle-3s", wet(X.paper_rustle(3.0, 69, density=16), 0.3, 0.15))
        put("tactile", "ink-roller", wet(roller(), 0.4, 0.2))
    return [f"{n} sounds"]


def chord_motif(kit):
    m = S.Mix(5.0)
    m.add(kit.chord(4.2), 0.0, gain=0.35, send=0.5)
    m.add(kit.motif(3.6), 0.25, gain=0.8, send=0.5)
    return mix_master(m, tail=0.5, kit=kit)


def loopable(x, xf=0.5):
    """Crossfade the tail into the head so the file loops seamlessly (10.5 s in -> 10.0 s out)."""
    n = int(xf * SR)
    x = np.asarray(x, np.float64)
    body = x[: len(x) - n].copy()
    w = np.linspace(0, 1, n)
    body[:n] = body[:n] * w + x[len(x) - n:] * (1 - w)
    return body[: int(10.0 * SR)]


def double(x, gap):
    n = int(gap * SR)
    out_ = np.zeros(len(x) + n)
    out_[: len(x)] += x * 0.75
    out_[n:] += x
    return out_


def needle_drop():
    r = np.random.default_rng(71)
    d = 1.4
    t = S.tt(d)
    bump = np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.05) + S.sos(r.standard_normal(len(t)), "bandpass", (400, 3000), 2) * np.exp(-t / 0.01) * 0.6
    return bump + X.vinyl_crackle(d, 72) * np.minimum(1, t / 0.1) * 0.6


def tape_stop(kit):
    x = kit.motif(1.6)
    n = len(x)
    speed = np.clip(1 - (np.arange(n) / n) ** 1.6, 0.02, 1)
    idx = np.cumsum(speed)
    idx = idx[idx < n - 1]
    return np.interp(idx, np.arange(n), x) * np.linspace(1, 0.2, len(idx))


def riff(kit):
    notes = [(0.0, 74), (0.16, 78), (0.32, 81), (0.56, 86)]
    out_ = np.zeros(int(2.4 * SR))
    for t0, nn in notes:
        p = kit.pluck(nn, 1.4)
        i = int(t0 * SR)
        out_[i:i + len(p)] += p[: len(out_) - i]
    return out_


def stamp(kit):
    r = np.random.default_rng(73)
    d = 0.5
    t = S.tt(d)
    thud = np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.05)
    squelch = S.sos(r.standard_normal(len(t)), "bandpass", (900, 3800), 2) * np.exp(-((t - 0.03) / 0.02) ** 2) * 0.35
    lift = S.sos(r.standard_normal(len(t)), "bandpass", (1500, 5000), 2) * np.exp(-((t - 0.2) / 0.025) ** 2) * 0.15
    return thud + squelch + lift


def roller():
    r = np.random.default_rng(74)
    d = 1.6
    t = S.tt(d)
    e = np.sin(np.pi * t / d) ** 0.7
    sticky = S.sos(r.standard_normal(len(t)), "bandpass", (1200, 5200), 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t) ** 2)
    low = S.sos(r.standard_normal(len(t)), "lowpass", 300, 2) * 0.8
    return (sticky * 0.5 + low) * e
