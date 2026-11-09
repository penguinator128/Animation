"""
ASTRIS PRODUCTIONS - Intro 2: 3D REVEAL, PURPLE ZOOM-OUT (10.0 s)

Inspired by the classic studio globe reveal. We start INSIDE a 3D scene (rendered by three.js in headless
Chromium, see intro2_scene.html): glossy iridescent shards cut from the logo, metal rings and pearls orbit
around us, oil-slick rainbow shimmer sliding across every surface. The shards spiral home, centre outward,
and lock into a mosaic that fuses into the solid bevelled logo. Then the camera pulls all the way OUT while
the rings settle into a halo, purple light floods in from behind and volumetric rays pour through the
film strip's sprocket holes. ASTRIS PRODUCTIONS arrives in the purple glow.
Sound: a swelling build with a glassy tick for every shard that locks, a deep bloom when it fuses, and a
warm IV -> I chord that resolves as the camera pulls out.
"""
import json
import math
import subprocess
import sys

import numpy as np

import common as C
import sound as S

cv2 = C.cv2
NAME = "astris-hero-2-3d-reveal"
DUR = 10.0
N = int(DUR * C.FPS)
W, H = C.W, C.H
T_FUSE, T_PULL0, T_PULL1 = 5.75, 5.55, 8.6
T_ASTRIS, T_PROD = 6.85, 7.4      # the 3D lettering stands up from here (see hero2_scene.html)
FRAME_BYTES = W * H * 4

LOGO = C.Logo()
LOCK = C.Lockup(LOGO)
POST = C.Post(seed=22, grain=0.022, vignette=0.36)

# ---- atmosphere (static fields, shared with workers via fork) -------------------------------------
QW, QH = W // 4, H // 4
_yq, _xq = np.mgrid[0:QH, 0:QW].astype(np.float32)
_xq = _xq * 4 + 2
_yq = _yq * 4 + 2


def _fbm(w, h, seed, octaves=6):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        g = r.standard_normal((max(2, int(2 * 2 ** o)), max(2, int(3 * 2 ** o)))).astype(np.float32)
        acc += cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp
        amp *= 0.55
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())


HAZE = _fbm(QW, QH, 3)
HAZE2 = _fbm(QW, QH, 8)
_r = np.random.default_rng(5)
STARS = np.zeros((H, W), np.float32)
for _ in range(900):
    x, y = _r.uniform(0, W), _r.uniform(0, H)
    cv2.circle(STARS, (int(x * 16), int(y * 16)), int(16 * _r.uniform(1.0, 2.6)), float(_r.uniform(0.15, 0.7)), -1,
               cv2.LINE_AA, 4)
STAR_PH = _r.uniform(0, 6.28, 1)[0]
PURPLE = np.array([0.55, 0.28, 1.0], np.float32)
MAGENTA = np.array([0.95, 0.35, 0.85], np.float32)


def bg_at(t, light, p):
    """Deep violet space; a volumetric glow blooms behind the logo as the light comes up."""
    lx, ly = light
    r = np.hypot(_xq - lx, (_yq - ly) * 1.15)
    base = np.array([0.025, 0.012, 0.05], np.float32) + np.array([0.04, 0.015, 0.07], np.float32) * \
        np.exp(-np.hypot(_xq - W / 2, _yq - H * 0.45) / 1700)[..., None]
    drift = cv2.warpAffine(HAZE, np.float32([[1, 0, -t * 6], [0, 1, -t * 2]]), (QW, QH), borderMode=cv2.BORDER_REFLECT101)
    haze = 0.55 + 0.9 * drift * HAZE2
    glow = (np.exp(-r / 420) * 0.26 + np.exp(-r / 1200) * 0.24 + np.exp(-r / 2600) * 0.14) * haze
    col = PURPLE[None, None] * glow[..., None] + MAGENTA[None, None] * (np.exp(-r / 700) * 0.12 * haze)[..., None]
    img = base + col * (0.12 + 0.88 * p)
    return img


def rays(alpha_q, light, p, t):
    """Volumetric light: the bright core behind the logo, seen only where the 3D layer lets it through
    (sprocket holes, the gap in the A, around the edges), streaked outward with a radial blur."""
    lx, ly = light[0] / 4, light[1] / 4
    r = np.hypot(_xq / 4 - lx, _yq / 4 - ly)
    core = (np.exp(-r / 80) * 0.55 + np.exp(-r / 240) * 0.32).astype(np.float32)
    src = core * (1 - alpha_q)
    acc = np.zeros_like(src)
    wsum = 0.0
    for k in range(28):
        s = 1.0 / (1 + k * 0.045)
        M = cv2.getRotationMatrix2D((lx, ly), 0, 1 / s)
        w = 0.93 ** k
        acc += cv2.warpAffine(src, M, (QW, QH), flags=cv2.INTER_LINEAR, borderValue=0) * w
        wsum += w
    acc /= wsum
    shimmer = 0.85 + 0.15 * math.sin(t * 2.3)
    return acc * p * shimmer


def composite(item):
    i, info, rgba = item
    t = i / C.FPS
    a = np.frombuffer(rgba, np.uint8).reshape(H, W, 4)[::-1]
    prem = a[..., :3].astype(np.float32) * (1 / 255)
    alpha = a[..., 3].astype(np.float32) * (1 / 255)
    light = info["light"]
    p = C.smoothstep(T_PULL0 - 0.2, T_PULL1 - 0.4, t)
    bg = bg_at(t, light, p)
    stars = STARS * (0.55 + 0.45 * np.sin(STAR_PH + t * 1.3)) * (0.5 + 0.5 * C.smoothstep(4.5, 8.5, t))
    alpha_q = cv2.resize(alpha, (QW, QH), interpolation=cv2.INTER_AREA)
    ry = rays(alpha_q, light, p, t)
    ray_col = (ry[..., None] * np.array([0.78, 0.55, 1.0], np.float32))
    back = C.up(bg + ray_col * 0.75) + stars[..., None] * np.array([0.8, 0.75, 1.0], np.float32)
    img = prem + back * (1 - alpha[..., None])
    img += C.up(ray_col) * 0.05 * alpha[..., None]           # haze in front of the logo scatters a little light
    # a light glint sweeps across the moment it fuses
    g = (t - (T_FUSE - 0.05)) / 0.55
    if 0 <= g <= 1:
        cx, cy, hh = info["logo"]
        band = np.exp(-((((_xq - cx) / hh) * 0.8 - ((_yq - cy) / hh) * 0.45 - (-1.0 + 2.2 * g)) / 0.06) ** 2)
        img += (C.up(band.astype(np.float32)) * alpha * 0.55)[..., None] * np.array([1.0, 0.95, 1.0], np.float32)
    # gentle purple grade: lift the shadows toward violet
    img = img + np.array([0.012, 0.0, 0.022], np.float32) * (0.5 + 0.5 * p)
    bloom = 0.45 + 0.2 * p + 0.4 * C.pulse(t, T_FUSE, 0.05, 0.4)
    return POST.finish(img, i, bloom=bloom, threshold=0.74)


def frames_from_node(frame_list):
    contiguous = frame_list == list(range(frame_list[0], frame_list[0] + len(frame_list)))
    args = [str(frame_list[0]), str(frame_list[0] + len(frame_list))] if contiguous else [",".join(map(str, frame_list))]
    cmd = ["node", str(C.ROOT / "render3d.js"), "hero2_scene.html"] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=open(C.ROOT / "logs" / "hero2_3d.log", "a"), cwd=C.ROOT)
    for f in frame_list:
        head = proc.stdout.read(512)
        if len(head) < 512:
            raise RuntimeError("3D renderer stopped early - see logs/hero2_3d.log")
        info = json.loads(head.decode().strip())
        rgba = proc.stdout.read(FRAME_BYTES)
        yield (f, info, rgba)
    proc.wait()


# ================================================================================================
# sound
# ================================================================================================
def shard_arrivals():
    """Same arrival schedule as the 3D scene: 47 shards, centre outward, 1.75 s -> 5.5 s."""
    geo = json.loads((C.ROOT / "hero2_geometry.json").read_text())
    n = len(geo["shards"])
    return [1.75 + 3.75 * (k / (n - 1)) ** 0.85 for k in range(n)]


def audio():
    m = S.Mix(DUR)
    # the swell: rumble + sub + an airy pad that opens up while the shards gather
    m.add(S.rumble(T_FUSE + 0.6, level=1.0, f=55, seed=201, swell=lambda tt: (np.clip(tt / T_FUSE, 0, 1) ** 1.4) * 0.9 + 0.1),
          0.0, gain=0.45, send=0.05)
    m.add(S.sub_build(T_FUSE, 30, 49, curve=1.8), 0.0, gain=0.35, send=0.0)
    bm = [S.midi(47), S.midi(54), S.midi(59), S.midi(62), S.midi(66), S.midi(73)]     # B minor add9: unresolved
    m.add(S.pad(bm, T_FUSE + 0.5, attack=3.5, release=0.8, cutoff=(250, 2200), seed=203), 0.0, gain=0.24, send=0.45)
    m.add(S.riser(2.6, 300, 6000, seed=205), T_FUSE - 2.6, gain=0.16, send=0.3)
    # objects whooshing past the lens early on
    for k, (t0, pan) in enumerate(((0.05, 0.6), (0.9, -0.5), (1.9, 0.4), (3.0, -0.6))):
        m.add(S.whoosh(0.9, peak=0.55, f_lo=250, f_hi=3800, q=1.0, pan_from=pan, pan_to=-pan, seed=210 + k), t0,
              gain=0.30, send=0.25)
    # one glassy tick per shard locking into place (pentatonic, rising as the logo completes)
    scale = [0, 2, 4, 7, 9]
    for k, ta in enumerate(shard_arrivals()):
        note = 74 + scale[k % 5] + 12 * (k // 15)
        x = S.chime(S.midi(min(note, 100)), 0.9, decay=0.35)
        click = S.tick(S.midi(min(note, 100)) / 4, 0.08, 0.3, 0.6, seed=k)
        x[:len(click)] += click                       # glassy ring with a tiny click as it seats
        m.add(x, ta, gain=0.075, pan=float(np.sin(k * 1.7) * 0.6), send=0.5)
    # FUSE: deep bloom + reverse swell leading into it + shimmer
    m.add(S.reverse_swell(0.7, seed=221, f=3000), T_FUSE - 0.7, gain=0.30, send=0.2)
    m.add(S.impact(3.0, weight=0.9, bright=0.55, metal=0.5, seed=223, sub_f=(70, 30)), T_FUSE, gain=0.55, send=0.4)
    m.add(S.shimmer(3.0, root=S.midi(86), density=30, seed=225, rise=0.4), T_FUSE, gain=0.22, send=0.6)
    # PULL-OUT: warm IV -> I resolution (G add9 -> D add9) blooming as the camera travels back
    g_ch = [S.midi(43), S.midi(50), S.midi(55), S.midi(59), S.midi(62), S.midi(69)]
    d_ch = [S.midi(38), S.midi(45), S.midi(50), S.midi(54), S.midi(57), S.midi(64), S.midi(66)]
    m.add(S.pad(g_ch, 2.3, attack=0.5, release=0.6, cutoff=(500, 2800), seed=231), T_FUSE, gain=0.40, send=0.5)
    m.add(S.pad(d_ch, DUR - 7.35, attack=0.35, release=1.8, cutoff=(700, 3200), seed=233), 7.35, gain=0.46, send=0.55)
    m.add(S.sting(d_ch, DUR - 7.35, bright=0.45, seed=235), 7.35, gain=0.20, send=0.5)
    m.add(S.chime(S.midi(78), 2.4, decay=1.4), 7.35, gain=0.12, pan=-0.3, send=0.6)
    m.add(S.chime(S.midi(85), 2.4, decay=1.4), 7.42, gain=0.09, pan=0.3, send=0.6)
    m.add(S.shimmer(2.2, root=S.midi(90), density=20, seed=237, rise=0.6), T_ASTRIS, gain=0.12, send=0.6)
    mix = m.master(ir_seconds=3.0, wet=1.0, peak_db=-1.5, tail_fade=0.15)
    S.report(mix, NAME)
    return mix


def main():
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    C.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    (C.ROOT / "logs").mkdir(exist_ok=True)
    if not (C.ROOT / "hero2_geometry.json").exists():
        import geometry3d
        geometry3d.build(C.ROOT / "hero2_geometry.json")
    if "--test" in sys.argv:
        fr = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else [20, 70, 120, 138, 150, 170, 190, 239]
        rendered = [composite(item) for item in frames_from_node(fr)]
        print(C.save_test_frames("hero2", None, fr, rendered=rendered))
        return
    wav = C.AUDIO_DIR / f"{NAME}.wav"
    S.write_wav24(wav, audio())
    import multiprocessing as mp
    import time
    out = C.OUT_DIR / f"{NAME}.mp4"
    proc = subprocess.Popen(C.ffmpeg_cmd(out, wav), stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.get_context("fork").Pool(2, initializer=C._worker_init) as pool:
        for k, fr in enumerate(pool.imap(composite, frames_from_node(list(range(N))), chunksize=1)):
            proc.stdin.write(fr.tobytes())
            if k % 24 == 0 or k == N - 1:
                el = time.time() - t0
                print(f"[{NAME}] frame {k + 1}/{N}  {el:6.1f}s elapsed  eta {el / (k + 1) * (N - k - 1):6.1f}s", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    print(f"[{NAME}] wrote {out}")


if __name__ == "__main__":
    main()
