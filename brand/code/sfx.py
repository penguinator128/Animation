"""
More instruments for the idents (all numpy/scipy, mono unless noted):
pencil, paper, wood, spray can, projector, optical crackle, vinyl, tape, old-film filter, strings, brass,
synth arp/stab, gated snare, bass drop, funk bass, wah scratch, snap, tambourine, underwater, glitch, plucks.
"""
import math

import numpy as np
from scipy import signal

from sound import (SR, chime, env_exp, midi, noise, pan2, sat, sos, sweep, tt)


def _norm(x, level=1.0):
    return x / (np.max(np.abs(x)) + 1e-9) * level


def _add(buf, x, i0):
    """Adds x into buf starting at sample i0, safely clipped at both ends."""
    i0 = int(i0)
    a0, b0 = max(0, i0), min(len(buf), i0 + len(x))
    if b0 > a0:
        buf[a0:b0] += x[a0 - i0:b0 - i0]


def grit(dur, rate, seed):
    """Sparse random impulses (Poisson): the raw material of scratches, crackle and fizz."""
    r = np.random.default_rng(seed)
    n = int(round(dur * SR))
    x = np.zeros(n)
    k = r.poisson(rate * dur)
    x[r.integers(0, n, k)] = r.uniform(-1, 1, k)
    return x


def curve(dur, keys):
    """Piecewise-linear control curve from [(t, value)] (t in seconds)."""
    t = tt(dur)
    ks = np.array(keys, np.float64)
    return np.interp(t, ks[:, 0], ks[:, 1])


# ---------------------------------------------------------------------------- hand-made / paper
def pencil(dur, speed=None, seed=1, bright=1.0):
    """Graphite on paper. `speed` is a control curve (array over dur, 0..1): loudness and grit follow it."""
    t = tt(dur)
    sp = np.ones(len(t)) if speed is None else np.interp(t, np.linspace(0, dur, len(speed)), speed)
    hiss = sos(noise(dur, "white", seed), "bandpass", [2200, 7500], 2) * 0.30
    g = sos(grit(dur, 14000, seed + 1), "bandpass", [2600, 9500 * bright], 2) * 2.4
    body = sos(noise(dur, "pink", seed + 2), "bandpass", [350, 1500], 2) * 0.22
    x = (hiss + g * (0.3 + 0.7 * sp) + body) * (0.08 + 0.92 * sp)
    x *= 0.82 + 0.18 * np.sin(2 * np.pi * np.cumsum(7 + 9 * sp) / SR)
    return _norm(x)


def paper_rustle(dur, seed=3, density=18):
    r = np.random.default_rng(seed)
    x = sos(noise(dur, "white", seed), "bandpass", [600, 6000], 2)
    env = np.zeros(len(x))
    for _ in range(int(density * dur)):
        c = r.uniform(0, dur)
        env += np.exp(-((tt(dur) - c) / r.uniform(0.01, 0.05)) ** 2) * r.uniform(0.3, 1)
    crackle = sos(grit(dur, 900, seed + 1), "bandpass", [1500, 7000], 2) * 3
    return _norm(x * env + crackle * env * 0.5)


def paper_slap(seed=5, size=1.0):
    d = 0.25
    t = tt(d)
    thud = sos(noise(d, "pink", seed), "lowpass", 700 / size, 2) * np.exp(-t / 0.035) * 2.2
    flap = sos(noise(d, "white", seed + 1), "bandpass", [900, 5000], 2) * np.exp(-t / 0.018)
    return _norm(sat(thud + flap * 0.8, 1.3))


def paper_pop(seed=7, pitch=1.0):
    d = 0.14
    t = tt(d)
    f = 520 * pitch * (1 + 1.5 * np.exp(-t / 0.008))
    blip = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03)
    click = sos(noise(d, "white", seed), "highpass", 2500) * np.exp(-t / 0.004)
    return _norm(blip + click * 0.6)


def clack(freq=900, seed=9, decay=0.05):
    """Wood block / cardboard clack: resonant partials struck by a click."""
    d = 0.3
    t = tt(d)
    x = sum(np.sin(2 * np.pi * freq * k * t) * np.exp(-t / (decay / k ** 0.5)) / k for k in (1, 2.76, 5.4))
    x += sos(noise(d, "white", seed), "bandpass", [1500, 7000]) * np.exp(-t / 0.003) * 0.8
    return _norm(x)


def tap(seed=11, soft=1.0):
    d = 0.2
    t = tt(d)
    x = sos(noise(d, "pink", seed), "lowpass", 1800 * soft) * np.exp(-t / 0.012)
    x += np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.03) * 0.6
    return _norm(x)


# ---------------------------------------------------------------------------- spray can
def spray(dur, seed=13, pressure=None, colour=1.0):
    """Aerosol hiss: an initial 'pssh' burst then a steady, slightly fluttering hiss."""
    t = tt(dur)
    p = np.ones(len(t)) if pressure is None else np.interp(t, np.linspace(0, dur, len(pressure)), pressure)
    x = sos(noise(dur, "white", seed), "highpass", 2500 * colour, 2)
    x = x + sos(noise(dur, "white", seed + 1), "bandpass", [5000, 11000], 2) * 0.6
    flutter = 0.85 + 0.15 * np.sin(2 * np.pi * np.cumsum(23 + 7 * np.sin(t * 3)) / SR)
    onset = 1 + 1.2 * np.exp(-t / 0.05)
    env = np.minimum(1, t / 0.012) * np.minimum(1, (dur - t) / 0.04)
    return _norm(x * flutter * onset * env * p)


def can_rattle(n=7, rate=8.0, seed=15):
    """Shaking a spray can: the marble clacking inside a resonant tin."""
    r = np.random.default_rng(seed)
    dur = n / rate + 0.3
    out = np.zeros(int(dur * SR))
    for k in range(n):
        t0 = k / rate + r.normal(0, 0.008)
        for hit in range(2):
            i0 = int((t0 + hit * r.uniform(0.02, 0.05)) * SR)
            d = 0.12
            t = tt(d)
            ping = sum(np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * np.exp(-t / r.uniform(0.012, 0.03))
                       for f in r.uniform(2400, 6500, 4))
            body = np.sin(2 * np.pi * r.uniform(650, 900) * t) * np.exp(-t / 0.05) * 0.5
            x = (ping * 0.5 + body) * (1.0 if hit == 0 else 0.45)
            _add(out, x, i0)
    hiss = sos(noise(dur, "white", seed), "bandpass", [3000, 8000]) * 0.04
    n = min(len(out), len(hiss))
    out[:n] += hiss[:n]
    return _norm(out)


# ---------------------------------------------------------------------------- film / tape / vinyl
def projector(dur, fps=24, seed=17):
    """Film projector: motor hum with flutter, the shutter/claw clicking at the frame rate, a soft whine."""
    r = np.random.default_rng(seed)
    t = tt(dur)
    fl = 1 + 0.004 * np.sin(2 * np.pi * 0.9 * t) + 0.002 * np.sin(2 * np.pi * 7.1 * t)
    hum = sum(np.sin(2 * np.pi * 60 * k * np.cumsum(fl) / SR) / k ** 1.3 for k in (1, 2, 3, 4, 6))
    clicks = np.zeros(len(t))
    for k in range(int(dur * fps)):
        i0 = int((k / fps + r.normal(0, 0.0015)) * SR)
        d = 0.02
        c = sos(noise(d, "white", seed + k), "bandpass", [1200, 5000]) * np.exp(-tt(d) / 0.004)
        _add(clicks, c * (1.0 if k % 2 == 0 else 0.6), i0)
    whine = np.sin(2 * np.pi * 1180 * np.cumsum(fl) / SR) * 0.04
    rattle = sos(noise(dur, "pink", seed + 1), "bandpass", [150, 700]) * 0.25
    return _norm(hum * 0.35 + clicks * 1.0 + whine + rattle)


def optical_crackle(dur, seed=19, hiss=1.0):
    """Optical soundtrack noise: crackle, pops, hiss and a little mains hum."""
    t = tt(dur)
    cr = sos(grit(dur, 60, seed), "bandpass", [600, 6000]) * 6
    pops = sos(grit(dur, 4, seed + 1), "lowpass", 900) * 9
    hs = sos(noise(dur, "white", seed + 2), "bandpass", [2000, 9000]) * 0.08 * hiss
    hum = np.sin(2 * np.pi * 50 * t) * 0.04 + np.sin(2 * np.pi * 150 * t) * 0.015
    return _norm(cr + pops + hs + hum)


def vinyl_crackle(dur, seed=21):
    cr = sos(grit(dur, 140, seed), "bandpass", [1500, 9000]) * 5
    pops = sos(grit(dur, 3, seed + 1), "lowpass", 1500) * 8
    rumble = sos(noise(dur, "brown", seed + 2), "lowpass", 60) * 0.3
    return _norm(cr + pops + rumble)


def tape_hiss(dur, seed=23):
    x = sos(noise(dur, "pink", seed), "highpass", 1800) + sos(noise(dur, "white", seed + 1), "highpass", 6000) * 0.5
    return _norm(x)


def old_film(x, seed=25, wow=0.004, band=(260, 4200), drive=1.6):
    """Make a clean signal sound like a worn film print: band-limited, wow and flutter, saturated."""
    x = np.asarray(x, np.float64)
    stereo = x.ndim == 2
    chans = x if stereo else x[None]
    n = chans.shape[1]
    t = np.arange(n) / SR
    mod = 1 + wow * np.sin(2 * np.pi * 0.7 * t) + wow * 0.4 * np.sin(2 * np.pi * 6.3 * t + 1)
    pos = np.clip(np.cumsum(mod) - mod[0], 0, n - 1)
    out = []
    for c in chans:
        y = np.interp(pos, np.arange(n), c)
        y = sos(y, "bandpass", list(band), 2)
        out.append(sat(y * drive, 1.4))
    out = np.array(out)
    return out if stereo else out[0]


# ---------------------------------------------------------------------------- tonal instruments
def strings(freqs, dur, attack=0.25, release=0.8, seed=27, bright=1.0):
    """String ensemble: detuned saws with vibrato, soft attack, lowpassed. Stereo."""
    r = np.random.default_rng(seed)
    t = tt(dur)
    out = np.zeros((2, len(t)))
    for f in freqs:
        for v in range(4):
            vib = 1 + 0.004 * np.sin(2 * np.pi * r.uniform(4.6, 5.8) * t + r.uniform(0, 6)) * np.clip(t / 0.4, 0, 1)
            ph = 2 * np.pi * f * (1 + r.uniform(-0.006, 0.006)) * np.cumsum(vib) / SR
            out += pan2(signal.sawtooth(ph + r.uniform(0, 6)), r.uniform(-0.7, 0.7))
    out = np.stack([sos(c, "lowpass", 3500 * bright, 2) for c in out])
    env = np.minimum(1, t / attack) * np.where(t > dur - release, np.clip((dur - t) / release, 0, 1), 1)
    return _norm(out * env)


def brass(freqs, dur, seed=29, bright=1.0, swell=0.03):
    """Brass section hit: saws with a fast filter 'blat', a little pitch scoop, a short swell. Stereo."""
    r = np.random.default_rng(seed)
    t = tt(dur)
    out = np.zeros((2, len(t)))
    scoop = 1 - 0.02 * np.exp(-t / 0.04)
    for f in freqs:
        for v in range(3):
            ph = 2 * np.pi * f * (1 + r.uniform(-0.004, 0.004)) * np.cumsum(scoop) / SR
            out += pan2(signal.sawtooth(ph + r.uniform(0, 6)), r.uniform(-0.6, 0.6))
    fc = 700 + 4200 * bright * np.exp(-t / 0.18) + 900 * np.exp(-t / 1.2)
    out = np.stack([sweep(c, "lp", fc, 1.1) for c in out])
    env = np.minimum(1, t / swell) * (0.45 + 0.55 * np.exp(-t / 0.35)) * np.exp(-t / (dur * 0.6))
    return _norm(sat(out * env * 1.5, 1.3))


def synth_arp(notes, step, dur, seed=31, wave="saw", cutoff=2600, res=2.5, gate=0.7, delay=0.18):
    """Analogue arpeggio: notes (Hz) cycled every `step` seconds, filter blips, a ping-pong echo. Stereo."""
    t = tt(dur)
    x = np.zeros(len(t))
    k = 0
    while k * step < dur:
        f = notes[k % len(notes)]
        i0 = int(k * step * SR)
        nd = min(step * gate, dur - k * step)
        if nd <= 0:
            break
        tn = tt(nd)
        osc = signal.sawtooth(2 * np.pi * f * tn) if wave == "saw" else signal.square(2 * np.pi * f * tn, 0.4)
        fc = 300 + cutoff * np.exp(-tn / 0.06)
        y = sweep(osc, "lp", fc, res) * np.minimum(1, tn / 0.003) * np.exp(-tn / (nd * 0.8))
        _add(x, y, i0)
        k += 1
    d = int(delay * SR)
    L, R = x.copy(), x.copy()
    L[d:] += x[:-d] * 0.45
    R[2 * d:] += x[:-2 * d] * 0.3
    return _norm(np.stack([L, R]))


def synth_stab(freqs, dur=1.5, seed=33, bright=1.0):
    """Big 80s polysynth stab: stacked detuned saws + square, quick filter fall, wide. Stereo."""
    r = np.random.default_rng(seed)
    t = tt(dur)
    out = np.zeros((2, len(t)))
    for f in freqs:
        for v in (-1, 0, 1):
            ph = 2 * np.pi * f * (1 + 0.006 * v) * t
            out += pan2(signal.sawtooth(ph + r.uniform(0, 6)) + 0.4 * signal.square(ph * 0.5), v * 0.7)
    fc = 500 + 6500 * bright * np.exp(-t / 0.22)
    out = np.stack([sweep(c, "lp", fc, 1.3) for c in out])
    return _norm(out * np.minimum(1, t / 0.004) * np.exp(-t / (dur * 0.35)))


def gated_snare(seed=35, gate=0.32):
    """80s snare through a big reverb that is chopped off by a gate."""
    d = 0.9
    t = tt(d)
    body = (np.sin(2 * np.pi * 190 * t) + 0.6 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t / 0.06)
    wires = sos(noise(d, "white", seed), "bandpass", [1500, 9000]) * np.exp(-t / 0.12)
    dry = body * 0.7 + wires
    r = np.random.default_rng(seed)
    ir = r.standard_normal(int(0.8 * SR)) * np.exp(-np.arange(int(0.8 * SR)) / SR / 0.5)
    wet = signal.fftconvolve(dry, ir)[: len(t)] / 40
    g = np.where(t < gate, 1.0, np.exp(-(t - gate) / 0.01))
    L = dry + wet * g * 1.2
    R = dry + np.roll(wet, 37) * g * 1.2
    return _norm(np.stack([L, R]))


def bass_drop(dur=1.6, f0=110, f1=30, seed=37):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.25))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return _norm(sat(x * 1.8, 1.5) * np.minimum(1, t / 0.005) * np.exp(-t / (dur * 0.5)))


def funk_bass(events, dur, seed=39):
    """events: [(t, length, midi_note, slide_to_midi or None)] - a rubbery synth bass with slides."""
    t = tt(dur)
    f = np.zeros(len(t))
    amp = np.zeros(len(t))
    for t0, ln, m, slide in events:
        i0, i1 = int(t0 * SR), min(len(t), int((t0 + ln) * SR))
        tl = (np.arange(i1 - i0)) / SR
        f0 = midi(m)
        f1 = midi(slide) if slide is not None else f0
        f[i0:i1] = f0 * (f1 / f0) ** np.clip(tl / max(ln * 0.8, 1e-3), 0, 1) ** 1.5
        amp[i0:i1] = np.minimum(1, tl / 0.004) * np.exp(-tl / max(ln, 0.05))
    ph = 2 * np.pi * np.cumsum(f) / SR
    osc = signal.sawtooth(ph) * 0.6 + np.sin(ph) * 0.8 + np.sin(ph * 0.5) * 0.3
    fc = 250 + 1800 * amp
    return _norm(sat(sweep(osc * amp, "lp", fc, 2.2) * 1.6, 1.4))


def wah_scratch(dur=0.35, seed=41, up=True):
    """Muted guitar chord scratch through a wah sweep."""
    t = tt(dur)
    strum = sos(grit(dur, 2500, seed), "bandpass", [300, 4000]) * np.exp(-t / 0.06) * 5
    strum += sos(noise(dur, "pink", seed + 1), "bandpass", [400, 3000]) * np.exp(-t / 0.05)
    fc = (400 + 1800 * (t / dur)) if up else (2200 - 1800 * (t / dur))
    return _norm(sweep(strum, "bp", fc, 3.5))


def snap(seed=43):
    d = 0.15
    t = tt(d)
    x = sos(noise(d, "white", seed), "bandpass", [1200, 4500]) * np.exp(-t / 0.01) * 2
    x += np.sin(2 * np.pi * 2100 * t) * np.exp(-t / 0.006)
    return _norm(x)


def tambourine(dur=0.5, seed=45):
    r = np.random.default_rng(seed)
    t = tt(dur)
    jing = sum(np.sin(2 * np.pi * f * t + r.uniform(0, 6)) for f in r.uniform(5000, 10500, 9)) * np.exp(-t / 0.12)
    shk = sos(noise(dur, "white", seed), "highpass", 6000) * np.exp(-t / 0.08)
    return _norm(jing * 0.15 + shk)


def bloop(freq=420, seed=47, size=1.0):
    """Underwater drop: a bubble 'plip' (rising resonant pitch) + muffled splash."""
    d = 0.5
    t = tt(d)
    f = freq / size * (1 + 1.4 * (1 - np.exp(-t / 0.04)))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.07)
    x += sos(noise(d, "pink", seed), "lowpass", 700) * np.exp(-t / 0.05) * 0.4
    return _norm(x)


def underwater(dur, seed=49):
    """Muffled water ambience with occasional tiny bubbles."""
    r = np.random.default_rng(seed)
    t = tt(dur)
    bed = sos(noise(dur, "brown", seed), "lowpass", 380, 2) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.2 * t))
    bed = bed / (np.max(np.abs(bed)) + 1e-9)
    for _ in range(int(dur * 3)):
        b = bloop(r.uniform(900, 2200), seed + _, 1.0) * 0.06
        i0 = int(r.uniform(0, dur - 0.5) * SR)
        _add(bed, b, i0)
    return _norm(bed)


def static_burst(dur, seed=51, crush=6):
    x = noise(dur, "white", seed)
    q = 2 ** crush
    x = np.round(x * q) / q
    hold = np.repeat(x[::8], 8)[: len(x)]
    return _norm(sos(hold, "highpass", 400))


def stutter(x, slice_s=0.03, repeats=4):
    n = int(slice_s * SR)
    s = x[..., :n]
    return np.concatenate([s] * repeats, axis=-1)


def beep(freq=1800, dur=0.06, seed=53):
    t = tt(dur)
    return signal.square(2 * np.pi * freq * t) * np.minimum(1, t / 0.002) * np.minimum(1, (dur - t) / 0.004) * 0.5


def kalimba(freq, dur=1.6):
    t = tt(dur)
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.9) + 0.25 * np.sin(2 * np.pi * freq * 5.95 * t) * np.exp(-t / 0.12)
    return x * np.minimum(1, t / 0.002)


def xylophone(freq, dur=1.0):
    t = tt(dur)
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, 0.35), (3.93, 0.4, 0.08), (9.2, 0.15, 0.03)))
    return x * np.minimum(1, t / 0.001)


def glass_ping(freq, dur=2.0):
    """Struck crystal glass: very pure partials with slow beating."""
    t = tt(dur)
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / d) for r, a, d in
            ((1, 1, 1.4), (1.003, 0.5, 1.4), (2.32, 0.3, 0.6), (4.25, 0.12, 0.3)))
    return x * np.minimum(1, t / 0.001) / 1.8
