"""
Final checks for the whole package, written to brand/output/MANIFEST.txt:
  videos   ffprobe: 3840x2160, 24 fps, H.264 yuv420p, AAC 48 kHz stereo, audio length = video length
  audio    WAV: 48 kHz, 24-bit, stereo, same length as its video
  stills   2000x2000 RGBA and 150x150 RGBA (< 1 MB), nothing touching the canvas edge
  banners  2560x1440, < 6 MB          profiles  1600x1600 + 800x800
Usage: python3 checks.py   (exit code 1 if anything fails)
"""
import json
import subprocess
import sys
import wave

import numpy as np
from PIL import Image

import common as C

OUT = C.ROOT.parent / "output"
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)
    return "ok" if cond else "FAIL"


def mb(p):
    return p.stat().st_size / 1e6


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_streams", "-show_format", "-of", "json", str(p)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main():
    lines = ["ASTRIS PRODUCTIONS - brand package manifest", "=" * 44, ""]
    # ---------------- videos
    lines += ["VIDEOS  (videos/)   3840x2160 . 24 fps . H.264 High yuv420p CRF 15 . AAC 320k 48 kHz stereo", ""]
    vids = sorted((OUT / "videos").glob("*.mp4"), key=lambda p: (0 if "hero" in p.name else 1 if "ident-" in p.name else 2 if "master" in p.name else 3, p.name))
    total = 0.0
    for p in vids:
        try:
            info = probe(p)
        except subprocess.CalledProcessError:
            ok(False, f"unreadable video (still rendering?): {p.name}")
            lines.append(f"  {p.name:<38} UNREADABLE")
            continue
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        dur = float(info["format"]["duration"])
        nfr = int(v["nb_read_packets"])
        good = all([v["codec_name"] == "h264", v["width"] == 3840, v["height"] == 2160, v["r_frame_rate"] == "24/1",
                    v["pix_fmt"] == "yuv420p", a is not None and a["codec_name"] == "aac", a and a["sample_rate"] == "48000",
                    a and a["channels"] == 2, abs(nfr / 24 - dur) < 0.05])
        ok(good, f"video spec: {p.name}")
        ad = float(a["duration"]) if a else 0
        ok(abs(ad - nfr / 24) < 0.05, f"audio/video length: {p.name} ({ad:.3f} vs {nfr / 24:.3f})")
        total += mb(p)
        lines.append(f"  {p.name:<38} {dur:6.2f} s  {nfr:4d} frames  {mb(p):7.1f} MB   {'ok' if good else 'CHECK'}")
    lines += ["", f"  {len(vids)} videos, {total / 1000:.2f} GB", ""]
    ts = OUT / "videos" / "timestamps.txt"
    if ts.exists():
        lines += ["  timestamps.txt (where each ident sits in the master):", ""] + ["    " + l for l in ts.read_text().splitlines()] + [""]
    # ---------------- audio
    lines += ["AUDIO  (audio/)   24-bit / 48 kHz stereo WAV, same mix as the video", ""]
    for p in sorted((OUT / "audio").glob("*.wav")):
        with wave.open(str(p)) as w:
            sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        vid = OUT / "videos" / (p.stem + ".mp4")
        match = ""
        if vid.exists():
            try:
                vd = int(probe(vid)["streams"][0]["nb_read_packets"]) / 24
            except subprocess.CalledProcessError:
                vd = -1
            match = ok(abs(n / sr - vd) < 0.01, f"wav length vs video: {p.name}")
        ok(sr == 48000 and ch == 2 and sw == 3, f"wav format: {p.name}")
        lines.append(f"  {p.name:<38} {n / sr:6.2f} s  {mb(p):6.2f} MB  {match}")
    lines.append("")
    # ---------------- stills
    lines += ["STILLS  (stills/2000 and stills/150)   transparent badge logos, no text", ""]
    for p in sorted((OUT / "stills" / "2000").glob("*.png")):
        big = Image.open(p)
        small_p = OUT / "stills" / "150" / p.name
        small = Image.open(small_p)
        a = np.asarray(big.getchannel("A"))
        edge = max(a[:3].max(), a[-3:].max(), a[:, :3].max(), a[:, -3:].max())
        g = ok(big.size == (2000, 2000) and big.mode == "RGBA" and small.size == (150, 150) and small.mode == "RGBA"
               and mb(small_p) < 1.0 and edge < 8, f"still: {p.name}")
        lines.append(f"  {p.name:<30} 2000x2000 {mb(p):5.2f} MB  |  150x150 {small_p.stat().st_size / 1024:5.1f} KB   {g}")
    ov = OUT / "stills" / "stills-overview.png"
    lines += [f"  stills-overview.png  {Image.open(ov).size[0]}x{Image.open(ov).size[1]}" if ov.exists() else "  (no overview)", ""]
    # ---------------- banners + profiles
    lines += ["BANNERS  (banners/)   2560x1440 PNG, < 6 MB, logo + type inside the 1546x423 safe area", ""]
    safe = {}
    sj = C.ROOT / "logs" / "safe_area.json"
    if sj.exists():
        safe = json.loads(sj.read_text())
    for p in sorted((OUT / "banners").glob("*.png")):
        im = Image.open(p)
        s = safe.get(p.stem, {})
        g = ok(im.size == (2560, 1440) and mb(p) < 6.0 and s.get("inside", False), f"banner: {p.name}")
        lines.append(f"  {p.name:<42} {im.size[0]}x{im.size[1]}  {mb(p):5.2f} MB  safe-area margins {s.get('margins_lrtb', '?')}  {g}")
    lines += ["", "PROFILE PICTURES  (profiles/)   1600x1600 + 800x800, circle-safe", ""]
    for p in sorted((OUT / "profiles").glob("*-1600.png")):
        im = Image.open(p)
        p8 = p.with_name(p.name.replace("-1600", "-800"))
        im8 = Image.open(p8)
        s = safe.get(p.stem.replace("-1600", ""), {})
        g = ok(im.size == (1600, 1600) and im8.size == (800, 800) and s.get("inside_circle", False), f"profile: {p.name}")
        lines.append(f"  {p.name:<44} + -800   {mb(p):5.2f} / {mb(p8):4.2f} MB   logo reaches {s.get('logo_max_radius_px', '?')} px of 800   {g}")
    lines += ["", "PREVIEWS  (previews/)", ""]
    for p in sorted((OUT / "previews").glob("*.png")):
        lines.append(f"  {p.name:<52} {Image.open(p).size[0]}x{Image.open(p).size[1]}")
    lines += ["", "RESULT: " + ("all checks passed" if not fails else f"{len(fails)} problem(s): " + "; ".join(fails)), ""]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
