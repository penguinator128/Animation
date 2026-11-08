"""
ASTRIS PRODUCTIONS - sound design kit. Everything is synthesised with numpy/scipy:
sub builds, rumbles, whooshes, impacts, shimmers, chimes, pads, stings and a convolution reverb.
Mixes are mastered with headroom (peak -1.5 dBFS, true-peak checked) and written as 24-bit 48 kHz WAVs.
"""
import math
import struct

import numpy as np
from scipy import signal

SR = 48000


# ------------------------------------------------------------------------------------------------
# basics
# ------------------------------------------------------------------------------------------------
def tt(dur):
    return np.arange(int(round(dur * SR))) / SR


def rng(seed):
    return np.random.default_rng(seed)


def noise(dur, color="white", seed=0):
    n = int(round(dur * SR))
    x = rng(seed).standard_normal(n)
    if color == "white":
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    X *= (1 / np.sqrt(f)) if color == "pink" else (1 / f)
    y = np.fft.irfft(X, n)
    return y / (np.std(y) + 1e-12)


def sos(x, kind, f, order=2):
    nyq = SR / 2
    if isinstance(f, (list, tuple)):
        wn = [min(0.999, max(1e-4, v / nyq)) for v in f]
    else:
        wn = min(0.999, max(1e-4, f / nyq))
    s = signal.butter(order, wn, btype=kind, output="sos")
    return signal.sosfilt(s, x)


def biquad_coeffs(kind, f, q):
    w0 = 2 * math.pi * min(f, SR * 0.45) / SR
    a = math.sin(w0) / (2 * q)
    c = math.cos(w0)
    if kind == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    elif kind == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    else:  # band-pass, constant 0 dB peak
        b = [a, 0, -a]
    A = [1 + a, -2 * c, 1 - a]
    return np.array(b) / A[0], np.array(A) / A[0]


def sweep(x, kind, fcurve, q=0.9, block=64):
    """Time-varying biquad: fcurve is an array (same length as x) of cutoff/centre frequencies."""
    y = np.zeros_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        b, a = biquad_coeffs(kind, float(fcurve[min(i + block // 2, len(x) - 1)]), q)
        y[i:i + block], zi = signal.lfilter(b, a, x[i:i + block], zi=zi)
    return y


def env_exp(dur, attack, decay, hold=0.0):
    t = tt(dur)
    e = np.where(t < attack, (t / max(attack, 1e-5)) ** 2, np.exp(-np.maximum(t - attack - hold, 0) / decay))
    return e


def fade(x, fin=0.002, fout=0.01):
    n = len(x)
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[n - b:] *= np.linspace(1, 0, b)
    return x


def sat(x, drive=1.5):
    return np.tanh(x * drive) / math.tanh(drive)


def pan2(x, pan):
    """Equal-power pan; pan may be a scalar or an array in [-1, 1]."""
    p = (np.asarray(pan) + 1) * math.pi / 4
    return np.stack([x * np.cos(p), x * np.sin(p)])


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------------------------------------
# instruments
# ------------------------------------------------------------------------------------------------
def rumble(dur, level=1.0, f=55, seed=1, swell=None):
    """Low, slowly breathing bed: brown noise below ~f Hz plus a sub sine."""
    x = sos(noise(dur, "brown", seed), "lowpass", f, 4)
    x /= np.max(np.abs(x)) + 1e-9
    t = tt(dur)
    sub = np.sin(2 * math.pi * (f * 0.6) * t + 0.4 * np.sin(2 * math.pi * 0.23 * t)) * 0.5
    y = (x * 0.8 + sub) * (0.8 + 0.2 * np.sin(2 * math.pi * 0.31 * t + seed))
    if swell is not None:
        y *= swell(t)
    return y * level


def sub_drop(dur, f0=80, f1=34, glide=0.35, decay=1.2, level=1.0):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t / (glide / 3))
    ph = 2 * math.pi * np.cumsum(f) / SR
    e = np.minimum(1, t / 0.003) * np.exp(-t / decay)
    return sat(np.sin(ph) * e, 1.3) * level


def sub_build(dur, f0=30, f1=58, level=1.0, curve=2.5):
    """Rising sub tone that swells into a hit."""
    t = tt(dur)
    k = (t / dur) ** curve
    f = f0 + (f1 - f0) * k
    ph = 2 * math.pi * np.cumsum(f) / SR
    e = (t / dur) ** 1.8
    x = np.sin(ph) + 0.25 * np.sin(2 * ph)
    return sat(x * e, 1.2) * level


def whoosh(dur, peak=0.7, f_lo=300, f_hi=4500, q=1.2, level=1.0, pan_from=-0.7, pan_to=0.7, seed=3,
           tail_f=None, sharp=3.0):
    """Air rushing past: band-passed pink noise whose centre and level swell to `peak` (fraction of dur)."""
    t = tt(dur)
    u = t / dur
    pk = peak
    rise = np.clip(u / pk, 0, 1)
    fall = np.clip((u - pk) / (1 - pk), 0, 1)
    tf = f_lo if tail_f is None else tail_f
    fc = np.where(u < pk, f_lo * (f_hi / f_lo) ** (rise ** 1.6), f_hi * (tf / f_hi) ** (fall ** 0.7))
    x = noise(dur, "pink", seed)
    y = sweep(x, "bp", fc, q) * 1.6 + sweep(x, "lp", fc * 0.5, 0.7) * 0.5
    e = np.where(u < pk, rise ** sharp, np.exp(-fall * 5.0))
    y *= e
    y /= np.max(np.abs(y)) + 1e-9
    pan = pan_from + (pan_to - pan_from) * np.clip(u / pk, 0, 1) ** 1.5
    return pan2(y * level, pan)


def riser(dur, f0=200, f1=3000, level=1.0, seed=5):
    t = tt(dur)
    u = t / dur
    fc = f0 * (f1 / f0) ** (u ** 1.4)
    n = sweep(noise(dur, "white", seed), "bp", fc, 2.0)
    tone_f = 110 * (2 ** (u ** 1.6 * 2.5))
    ph = 2 * math.pi * np.cumsum(tone_f) / SR
    tone = signal.sawtooth(ph) * 0.15 + np.sin(ph * 2) * 0.15
    trem = 0.75 + 0.25 * np.sin(2 * math.pi * np.cumsum(4 + 22 * u ** 2) / SR)
    y = (n * 1.2 + sos(tone, "lowpass", 2500)) * trem * u ** 2.2
    y /= np.max(np.abs(y)) + 1e-9
    return y * level


def impact(dur=3.0, weight=1.0, bright=1.0, metal=1.0, seed=7, sub_f=(78, 33)):
    """Cinematic hit: sub drop + thump + crack + body + metallic ring. Returns stereo."""
    r = rng(seed)
    t = tt(dur)
    sub = sub_drop(dur, sub_f[0], sub_f[1], 0.3, 1.0 + 0.4 * weight)
    thump = sos(noise(dur, "white", seed), "lowpass", 160, 4) * env_exp(dur, 0.002, 0.09) * 3.0
    body = sos(noise(dur, "pink", seed + 1), "bandpass", [250, 1400], 2) * env_exp(dur, 0.001, 0.16) * 1.4
    crack = sos(noise(dur, "white", seed + 2), "highpass", 2500, 2) * env_exp(dur, 0.0005, 0.025) * 1.5 * bright
    ring = np.zeros_like(t)
    for f in (97, 143, 211, 367, 523, 811, 1187, 1733, 2410):
        f2 = f * r.uniform(0.97, 1.03)
        ring += np.sin(2 * math.pi * f2 * t + r.uniform(0, 6)) * np.exp(-t / r.uniform(0.35, 1.6)) * (300 / f) ** 0.6
    ring = ring / (np.max(np.abs(ring)) + 1e-9) * 0.35 * metal * np.minimum(1, t / 0.004)
    mono = sat(sub * 1.1 * weight + thump * weight + body * 0.8 + ring, 1.25)
    wide = crack + body * 0.4
    L = mono + wide * 0.9 + ring * 0.25 * np.sin(2 * math.pi * 0.7 * t)
    R = mono + wide * 0.9 - ring * 0.25 * np.sin(2 * math.pi * 0.7 * t)
    return np.stack([L, R]) * 0.6


def shimmer(dur, root=1200, density=26, level=1.0, seed=11, spread=1.0, rise=0.15):
    """Glittering high partials (bells + air) that bloom and decay; stereo."""
    r = rng(seed)
    t = tt(dur)
    out = np.zeros((2, len(t)))
    ratios = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8]
    for k in range(density):
        f = root * ratios[r.integers(0, len(ratios))] * r.uniform(0.995, 1.005) * (2 ** r.integers(0, 2))
        if f > 15000:
            f /= 2
        onset = r.uniform(0, rise)
        d = r.uniform(0.6, 2.6)
        e = np.where(t >= onset, np.exp(-(t - onset) / d) * np.minimum(1, (t - onset) / 0.01), 0)
        vib = 1 + 0.002 * np.sin(2 * math.pi * r.uniform(3, 6) * t)
        x = np.sin(2 * math.pi * np.cumsum(f * vib) / SR) * e * (1500 / f) ** 0.5
        out += pan2(x, r.uniform(-0.8, 0.8) * spread)
    air = sos(noise(dur, "white", seed + 1), "highpass", 7000, 2) * env_exp(dur, 0.05, 0.9) * 0.08
    out += pan2(air, 0)
    return out / (np.max(np.abs(out)) + 1e-9) * level


def chime(freq, dur=3.0, level=1.0, decay=2.2):
    t = tt(dur)
    y = np.zeros_like(t)
    for ratio, amp, dk in ((1, 1, 1.0), (2.0, 0.5, 0.7), (2.76, 0.35, 0.5), (4.07, 0.22, 0.35), (5.4, 0.12, 0.25)):
        y += amp * np.sin(2 * math.pi * freq * ratio * t) * np.exp(-t / (decay * dk))
    return y * np.minimum(1, t / 0.002) * level / 2.2


def pad(freqs, dur, attack=1.0, release=1.5, cutoff=(400, 2400), level=1.0, detune=0.008, seed=13,
        hold=None):
    """Warm detuned saw pad with an opening filter. Returns stereo."""
    r = rng(seed)
    t = tt(dur)
    hold = dur - release if hold is None else hold
    e = np.minimum(1, (t / attack) ** 1.5) * np.where(t > hold, np.exp(-(t - hold) / (release / 3)), 1)
    out = np.zeros((2, len(t)))
    for f in freqs:
        for v in range(3):
            d = 1 + detune * (v - 1) + r.uniform(-0.001, 0.001)
            x = signal.sawtooth(2 * math.pi * f * d * t + r.uniform(0, 6)) * 0.6 + np.sin(2 * math.pi * f * d * t) * 0.6
            out += pan2(x, (v - 1) * 0.6)
    fc = cutoff[0] * (cutoff[1] / cutoff[0]) ** np.clip(t / max(attack * 1.5, 1e-3), 0, 1)
    out = np.stack([sweep(out[0], "lp", fc, 0.7), sweep(out[1], "lp", fc, 0.7)])
    out *= e
    return out / (np.max(np.abs(out)) + 1e-9) * level


def sting(freqs, dur=4.0, level=1.0, bright=1.0, seed=17):
    """Resolved final chord hit: brassy saw stack with a filter envelope + sub + bell layer. Stereo."""
    t = tt(dur)
    r = rng(seed)
    out = np.zeros((2, len(t)))
    for i, f in enumerate(freqs):
        for v in (-1, 0, 1):
            x = signal.sawtooth(2 * math.pi * f * (1 + 0.004 * v) * t + r.uniform(0, 6))
            out += pan2(x, v * 0.5 + (i - len(freqs) / 2) * 0.08)
    fc = 600 + 5200 * bright * np.exp(-t / 0.35)
    out = np.stack([sweep(out[0], "lp", fc, 0.8), sweep(out[1], "lp", fc, 0.8)])
    e = np.minimum(1, t / 0.006) * (0.35 + 0.65 * np.exp(-t / 0.5)) * np.exp(-t / (dur * 0.45))
    out *= e
    sub = np.sin(2 * math.pi * min(freqs) / 2 * t) * np.exp(-t / (dur * 0.35)) * np.minimum(1, t / 0.01)
    out += pan2(sub * 1.2, 0)
    bells = sum(chime(f * 4, dur, 0.5, 1.8) for f in freqs[:3])
    out += pan2(bells, 0.25)
    return out / (np.max(np.abs(out)) + 1e-9) * level


def tick(freq, dur=0.25, level=1.0, click=1.0, seed=19, body=1.0):
    """Punchy switch tick: pitched blip with a pitch-drop, a click and a little body. Mono."""
    t = tt(dur)
    f = freq * (1 + 1.2 * np.exp(-t / 0.006))
    ph = 2 * math.pi * np.cumsum(f) / SR
    blip = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.exp(-t / 0.06) * body
    clk = sos(noise(dur, "white", seed), "highpass", 3000, 2) * np.exp(-t / 0.004) * click
    thud = np.sin(2 * math.pi * 90 * t) * np.exp(-t / 0.035) * 0.6
    return sat((blip + clk * 0.6 + thud) * np.minimum(1, t / 0.0008), 1.4) * level


def reverse_swell(dur, level=1.0, seed=23, f=2400):
    """Reverse-cymbal style inhale (noise swell that cuts off at the end)."""
    t = tt(dur)
    u = t / dur
    x = sos(noise(dur, "white", seed), "bandpass", [600, f * 3], 2)
    x = sweep(x, "lp", 500 * (f * 4 / 500) ** u, 0.7)
    y = x * u ** 3
    return y / (np.max(np.abs(y)) + 1e-9) * level


# ------------------------------------------------------------------------------------------------
# reverb + mix bus + mastering
# ------------------------------------------------------------------------------------------------
def make_ir(seconds=2.6, seed=29, damp=0.55, predelay=0.018):
    r = rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    chans = []
    for c in range(2):
        x = r.standard_normal(n)
        lo = sos(x, "lowpass", 900, 2) * np.exp(-t / (seconds * 0.30))
        mid = sos(x, "bandpass", [900, 4500], 2) * np.exp(-t / (seconds * 0.22 * (1 - damp * 0.3)))
        hi = sos(x, "highpass", 4500, 2) * np.exp(-t / (seconds * 0.11))
        ir = lo + mid * 0.8 + hi * 0.5
        for k in range(10):     # a few early reflections
            d = int(r.uniform(0.008, 0.07) * SR)
            if d < n:
                ir[d] += r.uniform(-1, 1) * 2.5
        ir *= np.minimum(1, t / 0.004)
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])[:n]
        chans.append(ir / np.sqrt(np.sum(ir ** 2)))
    return np.stack(chans)


class Mix:
    def __init__(self, dur):
        self.dur = dur
        self.n = int(round(dur * SR))
        self.dry = np.zeros((2, self.n))
        self.bus = np.zeros((2, self.n))
        self.ducks = []

    def duck(self, t0, t1, depth_db=-42.0, fade=0.05):
        """Pull the whole mix (dry + reverb) down to near silence between t0 and t1, snapping back at t1."""
        self.ducks.append((t0, t1, depth_db, fade))

    def add(self, sig, t0, gain=1.0, pan=0.0, send=0.25):
        x = np.asarray(sig, np.float64)
        if x.ndim == 1:
            x = pan2(x, pan)
        i0 = int(round(t0 * SR))
        if i0 < 0:
            x = x[:, -i0:]
            i0 = 0
        m = min(x.shape[1], self.n - i0)
        if m <= 0:
            return
        self.dry[:, i0:i0 + m] += x[:, :m] * gain
        self.bus[:, i0:i0 + m] += x[:, :m] * gain * send

    def master(self, ir_seconds=2.6, wet=1.0, peak_db=-1.5, tail_fade=0.06, seed=29):
        ir = make_ir(ir_seconds, seed)
        wetsig = np.stack([signal.fftconvolve(self.bus[c], ir[c])[: self.n] for c in range(2)])
        mix = self.dry + wetsig * wet
        mix = np.stack([sos(mix[c], "highpass", 24, 2) for c in range(2)])
        for t0, t1, depth_db, fd in self.ducks:
            env = np.ones(self.n)
            g = 10 ** (depth_db / 20)
            i0, i1, nf, nb = int(t0 * SR), int(t1 * SR), int(fd * SR), int(0.003 * SR)
            env[i0:i0 + nf] = np.linspace(1, g, nf) ** 2 if g < 1 else 1
            env[i0 + nf:i1 - nb] = g
            env[i1 - nb:i1] = np.linspace(g, 1, nb)
            mix *= env
        # gentle glue: soft-knee compression on the summed level (slow envelope)
        lvl = np.sqrt(sos(np.mean(mix ** 2, 0), "lowpass", 8, 1).clip(1e-12))
        thr = np.percentile(lvl, 99.5) * 0.6
        gain = np.where(lvl > thr, (lvl / thr) ** (-0.35), 1.0)
        mix *= gain
        # ring-out: make sure the very end lands on silence without a click
        nf = int(tail_fade * SR)
        mix[:, -nf:] *= np.linspace(1, 0, nf) ** 2
        mix[:, :48] *= np.linspace(0, 1, 48)
        # normalise to the target peak, then verify true peak with 4x oversampling
        target = 10 ** (peak_db / 20)
        mix *= target / (np.max(np.abs(mix)) + 1e-12)
        over = signal.resample_poly(mix, 4, 1, axis=1)
        tp = np.max(np.abs(over))
        if tp > 10 ** (-1.0 / 20):
            mix *= 10 ** (-1.0 / 20) / tp
        return mix


def write_wav24(path, stereo):
    x = np.clip(np.asarray(stereo).T, -1, 1)
    i = np.ascontiguousarray(np.round(x * 8388607).astype("<i4"))
    b = i.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(b)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, 2, SR, SR * 6, 6, 24))
        f.write(b"data" + struct.pack("<I", len(b)) + b)


def report(mix, name):
    pk = 20 * math.log10(np.max(np.abs(mix)) + 1e-12)
    rms = 20 * math.log10(np.sqrt(np.mean(mix ** 2)) + 1e-12)
    end = 20 * math.log10(np.sqrt(np.mean(mix[:, -int(0.1 * SR):] ** 2)) + 1e-12)
    print(f"[{name}] audio peak {pk:.2f} dBFS, rms {rms:.1f} dBFS, last 100ms {end:.1f} dBFS")
