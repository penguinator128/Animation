#!/usr/bin/env python3
"""
Final checks on the whole kit. Prints every problem it finds and a short summary; writes the full report to
code/_work/check-report.txt.

    python3 code/check_kit.py
"""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

KIT = Path(__file__).resolve().parent.parent
SKIP = {"_work", "__pycache__", ".DS_Store"}
STYLES = {"red": "02_Style-1-Red", "yellow": "03_Style-2-Yellow", "wildcard": "04_Style-3-Wildcard"}
problems, notes = [], []


def bad(msg):
    problems.append(msg)


def files():
    return sorted([p for p in KIT.rglob("*") if p.is_file() and not any(s in p.parts for s in SKIP)])


def rel(p):
    return str(p.relative_to(KIT))


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels",
                          "-of", "json", str(p)], capture_output=True, text=True).stdout
    return json.loads(out or "{}")


def wav_peak_db(p):
    with wave.open(str(p)) as w:
        sr, sw, ch, n = w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getnframes()
        raw = w.readframes(n)
    if sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(x >= 1 << 23, x - (1 << 24), x) / float(1 << 23)
    else:
        x = np.frombuffer(raw, np.int16) / 32768.0
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    return sr, sw * 8, ch, n / sr, (20 * np.log10(peak) if peak > 0 else -120.0)


def main():
    all_files = files()
    total = sum(p.stat().st_size for p in all_files)
    # ---- 1. nothing over 100 MB ---------------------------------------------------------------------------------------
    for p in all_files:
        if p.stat().st_size >= 100_000_000:
            bad(f"over 100 MB: {rel(p)} ({p.stat().st_size / 1e6:.1f} MB)")
    # ---- 2. MANIFEST matches the files on disk --------------------------------------------------------------------
    man = (KIT / "MANIFEST.md").read_text() if (KIT / "MANIFEST.md").exists() else ""
    listed = set()
    folder = None
    for line in man.splitlines():
        m = re.match(r"### `(.+)/`", line)
        if m:
            folder = m.group(1)
            continue
        m = re.match(r"\| `([^`]+)` \|", line)
        if m and folder is not None:
            listed.add(str(Path(folder) / m.group(1)) if folder != "." else m.group(1))
    on_disk = {rel(p) for p in all_files if not (rel(p).startswith("downloads/") and p.suffix == ".zip")}
    missing = sorted(listed - on_disk)
    unlisted = sorted(on_disk - listed - {"MANIFEST.md"})
    for m in missing[:20]:
        bad(f"in MANIFEST but not on disk: {m}")
    for m in unlisted[:20]:
        bad(f"on disk but not in MANIFEST: {m}")
    notes.append(f"MANIFEST lists {len(listed)} files; {len(on_disk)} on disk (excluding downloads/)")
    # ---- 3. every picture opens, and the sizes the brief asked for --------------------------------------------------
    n_img = 0
    for p in all_files:
        if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
            try:
                with Image.open(p) as im:
                    im.verify()
                n_img += 1
            except Exception as e:
                bad(f"picture does not open: {rel(p)} ({e})")
    notes.append(f"{n_img} pictures open cleanly")
    exact = {r"banner-[abcd]-2560x1440\.png$": (2560, 1440), r"banner-[abcd]-master-5120x2880\.png$": (5120, 2880),
             r"profile-800x800\.png$": (800, 800), r"profile-master-1600x1600\.png$": (1600, 1600),
             r"profile-general-(square|circle)-1000x1000\.png$": (1000, 1000), r"thumbnail-.*-1280x720\.(jpg|png)$": (1280, 720),
             r"highlight-.*-1080x1920\.png$": (1080, 1920), r"post-.*-1080x1350\.png$": (1080, 1350), r"story-.*-1080x1920\.png$": (1080, 1920),
             r"wallpaper-.*-1290x2796\.png$": (1290, 2796), r"wallpaper-.*-1179x2556\.png$": (1179, 2556), r"wallpaper-.*-1440x3200\.png$": (1440, 3200),
             r"business-card-(front|back)-with-bleed-1134x720\.png$": (1134, 720), r"og-image-1200x630\.(png|jpg)$": (1200, 630),
             r"poster-.*-a3-3508x4961\.jpg$": (3508, 4961), r"poster-.*-2x3-4000x6000\.jpg$": (4000, 6000),
             r"youtube-watermark-150x150\.png$": (150, 150), r"icon-512\.png$": (512, 512), r"icon-192\.png$": (192, 192),
             r"apple-touch-icon-180\.png$": (180, 180), r"favicon-32\.png$": (32, 32), r"-4096x4096\.png$": (4096, 4096)}
    for p in all_files:
        for pat, wh in exact.items():
            if re.search(pat, p.name):
                with Image.open(p) as im:
                    if im.size != wh:
                        bad(f"wrong size: {rel(p)} is {im.size}, expected {wh}")
    for p in all_files:
        if re.search(r"banner-[abcd]-2560x1440\.png$", p.name) and p.stat().st_size >= 6e6:
            bad(f"banner over 6 MB: {rel(p)}")
        if re.search(r"thumbnail-.*-1280x720\.jpg$", p.name) and p.stat().st_size >= 2e6:
            bad(f"thumbnail JPG over 2 MB: {rel(p)}")
        if p.name.endswith("youtube-watermark-150x150.png") and p.stat().st_size >= 1e6:
            bad(f"watermark over 1 MB: {rel(p)}")
    # ---- 4. videos: length, size, frame rate, codecs ---------------------------------------------------------------
    n_vid = 0
    for p in all_files:
        if p.suffix.lower() not in (".mp4", ".mov"):
            continue
        j = probe(p)
        n_vid += 1
        dur = float(j.get("format", {}).get("duration", 0))
        v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), {})
        a = next((s for s in j.get("streams", []) if s["codec_type"] == "audio"), None)
        m = re.search(r"-(\d+)s-", p.name)
        if m and abs(dur - int(m.group(1))) > 0.05:
            bad(f"length {dur:.2f} s does not match the name: {rel(p)}")
        if (v.get("width"), v.get("height")) != (3840, 2160):
            bad(f"not 3840 x 2160: {rel(p)}")
        if v.get("r_frame_rate") != "24/1":
            bad(f"not 24 fps: {rel(p)}")
        if p.suffix == ".mp4":
            if v.get("codec_name") != "h264" or v.get("pix_fmt") != "yuv420p":
                bad(f"not H.264 yuv420p: {rel(p)}")
            if "overlay" not in p.name and (not a or a.get("codec_name") != "aac" or a.get("sample_rate") != "48000"):
                bad(f"no AAC 48 kHz sound: {rel(p)}")
        else:
            if v.get("codec_name") != "prores" or not str(v.get("pix_fmt", "")).startswith("yuva444"):
                bad(f"not ProRes 4444 with alpha: {rel(p)}")
    notes.append(f"{n_vid} videos checked (length, 4K, 24 fps, codecs)")
    # ---- 5. sound: 48 kHz, 24-bit, peak at or under -1 dB --------------------------------------------------------------
    n_wav, worst = 0, -120.0
    for p in all_files:
        if p.suffix.lower() != ".wav":
            continue
        sr, bits, ch, dur, pk = wav_peak_db(p)
        n_wav += 1
        worst = max(worst, pk)
        if sr != 48000 or bits != 24:
            bad(f"not 48 kHz 24-bit: {rel(p)} ({sr} Hz, {bits}-bit)")
        if pk > -0.99:
            bad(f"peak {pk:.2f} dB is above -1 dB: {rel(p)}")
    notes.append(f"{n_wav} WAVs checked: all 48 kHz / 24-bit, loudest peak {worst:.2f} dB")
    # ---- 6. PDFs open, with the right number of pages ---------------------------------------------------------------
    from pypdf import PdfReader
    pages_expected = {r"brand-guide-a4-landscape\.pdf$": 12, r"business-card-print-.*\.pdf$": 2, r"press-kit-one-page-a4\.pdf$": 1,
                      r"press-kit-full-a4\.pdf$": 5, r"letterhead-a4\.pdf$": 1, r"invoice-template-a4\.pdf$": 1}
    n_pdf = 0
    for p in all_files:
        if p.suffix.lower() != ".pdf":
            continue
        try:
            n = len(PdfReader(str(p)).pages)
            n_pdf += 1
        except Exception as e:
            bad(f"PDF does not open: {rel(p)} ({e})")
            continue
        for pat, want in pages_expected.items():
            if re.search(pat, p.name) and n != want:
                bad(f"{rel(p)} has {n} pages, expected {want}")
    notes.append(f"{n_pdf} PDFs open")
    # ---- 7. words the brief ruled out ----------------------------------------------------------------------------------
    for p in all_files:
        if p.suffix.lower() in (".md", ".html", ".json", ".txt", ".svg", ".css", ".py", ".webmanifest"):
            t = p.read_text(errors="ignore").lower()
            if "subscribe" in t and p.name != "check_kit.py":
                bad(f"the word 'subscribe' appears in {rel(p)}")
    # ---- 8. the email-signature pictures must not be in Git LFS (their raw links must serve the picture) ---------------
    sig = [p for p in all_files if "email-signature" in p.parts and p.suffix == ".png"]
    if sig:
        out = subprocess.run(["git", "check-attr", "filter", "--"] + [str(p) for p in sig], capture_output=True, text=True, cwd=KIT).stdout
        if "lfs" in out:
            bad("an email-signature picture is set to Git LFS (its raw link would not show the picture)")
    # ---- 9. each style has the same structure --------------------------------------------------------------------------
    shapes = {}
    for k, d in STYLES.items():
        # merch files are named after the garment colour, which differs by style on purpose (on-red, on-yellow, on-blue ...)
        shapes[k] = sorted(re.sub(r"-(on-)?(red|yellow|black|cream|blue|natural)-(\d+mm|235x160mm|illustration)", r"-\1COLOUR-\3",
                                  re.sub(rf"astris-{k}-", "astris-STYLE-", str(p.relative_to(KIT / d))))
                           for p in (KIT / d).rglob("*") if p.is_file() and p.name != ".DS_Store")
    base = set(shapes["red"])
    for k in ("yellow", "wildcard"):
        diff = (base ^ set(shapes[k]))
        # the textures folder legitimately differs (the risograph style has ink floods instead of field / dark),
        # and each style's tactile sounds are its own on purpose
        diff = {x for x in diff if "texture-" not in x and "06_Sound/tactile/" not in x}
        for x in sorted(diff)[:10]:
            bad(f"structure differs between red and {k}: {x}")
    report = ["ASTRIS brand kit: final checks", "", f"{len(all_files)} files, {total / 1e9:.2f} GB", ""] + notes + [""]
    report += ["PROBLEMS:"] + (problems or ["none"])
    out = KIT / "code" / "_work" / "check-report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n")
    print("\n".join(report[:12 + len(notes)]))
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems[:60]:
            print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
