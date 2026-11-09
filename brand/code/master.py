"""
ASTRIS PRODUCTIONS - the idents master: all 11 idents in order, with a short black gap between each.

  videos/astris-idents-master.mp4   + videos/timestamps.txt   (+ audio/astris-idents-master.wav)

Picture: stream-copied with the concat demuxer, so not one video frame is re-encoded. The black gap clip is encoded
with exactly the same x264 settings as the idents (checked: identical SPS/PPS), so the joins are seamless.
Sound: built sample-accurately from the original lossless WAV masters (each ident's audio at the exact sample its
picture starts on, digital silence in the gaps) and encoded to AAC once - so nothing is encoded twice, and the sync
is exact at every join (stream-copying AAC across files drifts by its 1024-sample priming at each join).
Usage: python3 master.py
"""
import json
import sys
from pathlib import Path
import subprocess
import wave

import numpy as np

import common as C

FPS = 24
SR = 48000
GAP_FRAMES = 14                    # 0.583 s of black between idents
IDENTS = [f"astris-ident-{k:02d}" for k in range(1, 12)]
VID, AUD = C.OUT_DIR, C.AUDIO_DIR
WORK = C.ROOT / "cache" / "master"
NAME = "astris-idents-master"


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_streams", "-show_format", "-of", "json",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def read_wav24(path):
    with wave.open(str(path)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 2 and w.getsampwidth() == 3, path
        raw = np.frombuffer(w.readframes(w.getnframes()), np.uint8).reshape(-1, 3)
    v = (raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8) | (raw[:, 2].astype(np.int32) << 16))
    v = np.where(v >= 1 << 23, v - (1 << 24), v)
    return (v.astype(np.float64) / 8388607).reshape(-1, 2)          # exact inverse of sound.write_wav24


def avcc(path):
    """The H.264 decoder config box (SPS/PPS) - must be identical in every file for a clean stream copy."""
    data = open(path, "rb").read(8 << 20)
    i = data.find(b"avcC")
    assert i > 4, f"no avcC in {path}"
    size = int.from_bytes(data[i - 4:i], "big")
    return data[i + 4:i - 4 + size]


def tc(sec):
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:06.3f}"


def assemble(seq, out, wav_out, gap_v, list_name):
    """seq: ident clips and "GAP"s in order. Picture: concat of the video-only copies (stream copy).
    Sound: the WAV masters laid end to end, sample-exact, digital silence in the gaps, encoded once."""
    from sound import write_wav24
    lines, parts, rows, frame = [], [], [], 0
    for item in seq:
        if item == "GAP":
            lines += [f"file '{gap_v}'", f"duration {GAP_FRAMES / FPS:.6f}"]
            parts.append(np.zeros((GAP_FRAMES * SR // FPS, 2)))
            frame += GAP_FRAMES
        else:
            lines += [f"file '{item['vonly']}'", f"duration {item['frames'] / FPS:.6f}"]
            rows.append((item["name"], frame, frame + item["frames"]))
            parts.append(item["pcm"])
            frame += item["frames"]
    total_frames = frame
    (WORK / list_name).write_text("\n".join(lines) + "\n")
    audio = np.concatenate(parts)
    assert len(audio) == total_frames * SR // FPS
    write_wav24(wav_out, audio.T)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(WORK / list_name), "-i", str(wav_out),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", str(out)], check=True)
    # checks: frame count, both streams start together, lengths match, every frame decodes, even timing
    info = probe(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert int(v["nb_read_packets"]) == total_frames, (v["nb_read_packets"], total_frames)
    dv, da = float(v["duration"]), float(a["duration"])
    sv, sa = float(v.get("start_time", 0)), float(a.get("start_time", 0))
    assert abs(sv - sa) < 0.001, f"picture starts at {sv:.4f} s but sound at {sa:.4f} s"
    assert abs(dv - total_frames / FPS) < 0.002 and abs(da - dv) < 0.03, (dv, da, total_frames / FPS)
    err = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-f", "null", "-"], capture_output=True, text=True).stderr
    assert not err.strip(), err[:2000]
    pts = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                          "-of", "csv=p=0", str(out)], capture_output=True, text=True, check=True).stdout.split()
    steps = np.diff(np.sort(np.array([float(t) for t in pts if t])))
    assert np.allclose(steps, 1 / FPS, atol=0.0015), f"uneven frame timing: {steps.min():.4f}..{steps.max():.4f}"
    return rows, total_frames, dv, da


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    clips = []
    for name in IDENTS:
        mp4, wav = VID / f"{name}.mp4", AUD / f"{name}.wav"
        assert mp4.exists() and wav.exists(), f"missing {name}"
        info = probe(mp4)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        a = next(s for s in info["streams"] if s["codec_type"] == "audio")
        assert (v["width"], v["height"], v["pix_fmt"], v["r_frame_rate"]) == (3840, 2160, "yuv420p", "24/1"), name
        assert (a["codec_name"], a["sample_rate"], a["channels"]) == ("aac", "48000", 2), name
        n = int(v["nb_read_packets"])
        pcm = read_wav24(wav)
        want = n * SR // FPS
        if len(pcm) != want:
            # durations that aren't a whole number of frames (6.4 s, 4.2 s) lose their last part-frame of picture
            # in the MP4; trim the sound to the picture (with a 15 ms fade so the cut can't click), or pad silence
            print(f"  {name}: wav {len(pcm)} samples -> {want} to match its {n} frames")
            if len(pcm) > want:
                pcm = pcm[:want].copy()
                k = int(0.015 * SR)
                pcm[-k:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k)))[:, None]
            else:
                pcm = np.concatenate([pcm, np.zeros((want - len(pcm), 2))])
        clips.append({"name": name, "frames": n, "pcm": pcm, "mp4": mp4})

    # black gap clip, same encoder settings as every ident (video only is used)
    gap = WORK / "gap.mp4"
    silent = WORK / "gap.wav"
    from sound import write_wav24
    write_wav24(silent, np.zeros((2, GAP_FRAMES * SR // FPS)))      # (channels, samples)
    p = subprocess.Popen(C.ffmpeg_cmd(gap, silent), stdin=subprocess.PIPE)
    p.stdin.write(bytes(C.W * C.H * 3) * GAP_FRAMES)
    p.stdin.close()
    assert p.wait() == 0
    ref = avcc(clips[0]["mp4"])
    for f in [c["mp4"] for c in clips] + [gap]:
        assert avcc(f) == ref, f"{f.name}: different SPS/PPS - stream copy would not be clean"

    # video-only copies (stream copy): if the concat inputs still carried their AAC tracks, the demuxer would offset
    # the picture by the AAC priming (21 ms) and the master's sound would lead its picture
    for c in clips:
        vo = WORK / f"{c['name']}-video.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(c["mp4"]), "-map", "0:v:0", "-c", "copy", "-an", str(vo)], check=True)
        c["vonly"] = vo
    gap_v = WORK / "gap-video.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(gap), "-map", "0:v:0", "-c", "copy", "-an", str(gap_v)], check=True)

    seq = []
    for k, c in enumerate(clips):
        seq.append(c)
        if k < len(clips) - 1:
            seq.append("GAP")
    out = VID / f"{NAME}.mp4"
    rows, total_frames, dv, da = assemble(seq, out, AUD / f"{NAME}.wav", gap_v, "list.txt")

    gap_s = GAP_FRAMES / FPS
    txt = [f"ASTRIS PRODUCTIONS - idents master  ({NAME}.mp4)",
           f"{len(clips)} idents in order, {gap_s:.3f} s ({GAP_FRAMES} frames) of black between each.  "
           f"24 fps.  Total {tc(total_frames / FPS)} ({total_frames} frames).",
           "Times are minutes:seconds.  'end' is the moment the ident's last frame finishes.", "",
           f"{'#':<4}{'file':<26}{'start':>11}{'end':>11}{'length':>10}   frames (start-end)"]
    for k, (name, f0, f1) in enumerate(rows, 1):
        txt.append(f"{k:02d}  {name + '.mp4':<26}{tc(f0 / FPS):>11}{tc(f1 / FPS):>11}{(f1 - f0) / FPS:>9.3f}s"
                   f"   {f0}-{f1 - 1}")
    (VID / "timestamps.txt").write_text("\n".join(txt) + "\n")
    print("\n".join(txt))
    print(f"\nwrote {out}  {out.stat().st_size / 1e6:.1f} MB   video {dv:.3f}s  audio {da:.3f}s  clean decode, even timing")

    # --parts DIR: the same master in three self-contained pieces (for upload limits), built the same way
    if "--parts" in sys.argv:
        pdir = Path(sys.argv[sys.argv.index("--parts") + 1])
        pdir.mkdir(parents=True, exist_ok=True)
        groups = [(0, 4), (4, 8), (8, 11)]
        for j, (i0, i1) in enumerate(groups, 1):
            sub = [] if j == 1 else ["GAP"]
            for k in range(i0, i1):
                sub.append(clips[k])
                if k < i1 - 1:
                    sub.append("GAP")
            po = pdir / f"{NAME}-part{j}of3.mp4"
            r, n, pv, pa = assemble(sub, po, WORK / f"part{j}.wav", gap_v, f"list_part{j}.txt")
            print(f"wrote {po.name}  {po.stat().st_size / 1e6:.1f} MB  {n} frames  idents {i0 + 1:02d}-{i1:02d}")


if __name__ == "__main__":
    main()
