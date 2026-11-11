#!/usr/bin/env python3
"""
Make the zips in downloads/. Every zip is under 100 MB, so bigger sets come in numbered parts.
Each part is a complete zip on its own: unzip any of them into the same place and they fill in the same
astris-brand-kit/ folder tree.

How the parts are cut: each style is split into four groups (YouTube and social / Premiere, sound, textures /
merch / everything else), and each group is packed into parts of up to 95 MB. A set such as "style 1 red" or
"merch" is then just the list of parts it needs. The same part in two sets is the same file, byte for byte
(fixed dates, fixed order), so Git LFS stores it once.

    python3 code/make_zips.py
"""
import os
import shutil
import sys
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
DL = KIT / "downloads"
LIMIT = 95_000_000
STAMP = (2026, 11, 11, 0, 0, 0)
STORE = {".mp4", ".mov", ".png", ".jpg", ".jpeg", ".zip", ".ico", ".pdf", ".ttf"}
SKIP = {"_work", "__pycache__", ".DS_Store", "downloads"}
STYLES = [("red", "02_Style-1-Red", "astris-style-1-red"), ("yellow", "03_Style-2-Yellow", "astris-style-2-yellow"),
          ("wildcard", "04_Style-3-Wildcard", "astris-style-3-wildcard")]
GROUPS = {"social": ["03_YouTube-and-Social"], "premiere": ["05_Premiere-Assets", "06_Sound", "10_Textures-and-LUTs"],
          "merch": ["07_Merch"], "rest": None}


def files_in(folder):
    return sorted([p for p in folder.rglob("*") if p.is_file() and not any(s in p.parts for s in SKIP)], key=lambda p: str(p))


def style_groups(sdir):
    base = KIT / sdir
    used = set()
    out = {}
    for g, subs in GROUPS.items():
        if subs is None:
            continue
        fs = []
        for s in subs:
            fs += files_in(base / s)
        out[g] = fs
        used.update(fs)
    out["rest"] = [f for f in files_in(base) if f not in used]
    return out


def pack(files):
    """Greedy, in path order: consecutive files fill a part until the next one would pass the limit."""
    parts, cur, size = [], [], 0
    for f in files:
        sz = f.stat().st_size + 200
        if cur and size + sz > LIMIT:
            parts.append(cur)
            cur, size = [], 0
        cur.append(f)
        size += sz
    if cur:
        parts.append(cur)
    return parts


def write_zip(path, files):
    tmp = path.with_suffix(".tmp")                      # written aside, then swapped in, so old links never see a half-written file
    with zipfile.ZipFile(tmp, "w", allowZip64=False) as z:
        for f in files:
            info = zipfile.ZipInfo("astris-brand-kit/" + str(f.relative_to(KIT)).replace("\\", "/"), STAMP)
            info.external_attr = 0o644 << 16
            if f.suffix.lower() in STORE:
                info.compress_type = zipfile.ZIP_STORED
                z.writestr(info, f.read_bytes())
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, f.read_bytes(), compresslevel=9)
    tmp.replace(path)
    assert path.stat().st_size < 100_000_000, f"{path.name} is over 100 MB"
    return path


def place(src, dst):
    """The same part under another name: a hard link where the disk allows it (no extra space), a copy otherwise."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def main():
    # ---- the parts ------------------------------------------------------------------------------------------------
    chunks = {}                                  # name -> list of files
    basics = [KIT / n for n in ("README.md", "MANIFEST.md", "brand-config.json", "films.txt", "taglines.txt", "fonts.md",
                                "compare-styles.png", "preview.html", ".gitignore", ".gitattributes") if (KIT / n).exists()]
    basics += files_in(KIT / "00_Originals") + files_in(KIT / "code")
    for i, p in enumerate(pack(basics), 1):
        chunks[f"basics-{i}"] = p
    for i, p in enumerate(pack(files_in(KIT / "01_Logo-Pack-Bare-Bones")), 1):
        chunks[f"logo-pack-{i}"] = p
    per_style = {}
    for key, sdir, _ in STYLES:
        per_style[key] = {}
        for g, fs in style_groups(sdir).items():
            names = []
            for i, p in enumerate(pack(fs), 1):
                n = f"{key}-{g}-{i}"
                chunks[n] = p
                names.append(n)
            per_style[key][g] = names
    # ---- the sets ---------------------------------------------------------------------------------------------------
    order = ["social", "premiere", "merch", "rest"]
    sets = {"astris-brand-kit-complete": [n for n in chunks if n.startswith("basics")] + [n for n in chunks if n.startswith("logo-pack")]
            + [n for key, _, _ in STYLES for g in order for n in per_style[key][g]],
            "astris-logo-pack-bare-bones": [n for n in chunks if n.startswith("logo-pack")],
            "astris-premiere-assets": [n for key, _, _ in STYLES for n in per_style[key]["premiere"]],
            "astris-merch": [n for key, _, _ in STYLES for n in per_style[key]["merch"]],
            "astris-youtube-and-social": [n for key, _, _ in STYLES for n in per_style[key]["social"]]}
    for key, _, setname in STYLES:
        sets[setname] = [n for g in order for n in per_style[key][g]]
    # ---- write each distinct part once, then copy it under every set's name ---------------------------------------------
    work = KIT / "code" / "_work" / "zips"
    work.mkdir(parents=True, exist_ok=True)
    built = {}
    for n, fs in chunks.items():
        built[n] = write_zip(work / f"{n}.zip", fs)
        print(f"  part {n}: {len(fs)} files, {built[n].stat().st_size / 1e6:.1f} MB", flush=True)
    if DL.exists():
        for old in DL.rglob("*.zip"):
            old.unlink()
    rows = []
    for setname, names in sets.items():
        d = DL / setname
        d.mkdir(parents=True, exist_ok=True)
        total = 0
        for i, n in enumerate(names, 1):
            dst = d / (f"{setname}.zip" if len(names) == 1 else f"{setname}-part-{i:02d}-of-{len(names):02d}.zip")
            place(built[n], dst)
            total += dst.stat().st_size
        rows.append((setname, len(names), total))
        print(f"{setname}: {len(names)} part(s), {total / 1e6:.0f} MB", flush=True)
    unique = sum(p.stat().st_size for p in built.values())
    (DL / "README.md").write_text(readme(rows, unique))
    print(f"unique bytes across all sets: {unique / 1e9:.2f} GB")


def readme(rows, unique):
    what = {"astris-brand-kit-complete": "Everything: all three styles, the logo pack, the originals, the docs and the code.",
            "astris-style-1-red": "The whole of Style 1 (Red).", "astris-style-2-yellow": "The whole of Style 2 (Yellow).",
            "astris-style-3-wildcard": "The whole of Style 3 (Wildcard, the risograph look).",
            "astris-logo-pack-bare-bones": "Just the logo pack: the report, the faithful and geometric versions, every format.",
            "astris-premiere-assets": "For editing, all three styles: corner bugs, lower thirds, overlays, sound packs, textures and colour looks.",
            "astris-merch": "All the merch, all three styles: stickers, cap, hoodie, T-shirt, tote, bottle wrap, wallpapers, mock-ups.",
            "astris-youtube-and-social": "Banners, profile pictures, thumbnails, Instagram covers, posts and stories, all three styles."}
    lines = ["# downloads", "",
             "The kit as zip files. **Each zip is under 100 MB**, so the bigger sets are split into numbered parts.",
             "", "| Folder | What is in it | Parts | Total |", "|---|---|---|---|"]
    for name, n, total in rows:
        lines.append(f"| [`{name}/`]({name}/) | {what.get(name, '')} | {n} | {total / 1e6:.0f} MB |")
    lines += ["", "## How to use the parts", "",
              "- **Each part is a normal zip that opens on its own.** You don't need all of them at once and no special tool is needed.",
              "- Unzip every part of a set into **the same place**. They all fill in the same `astris-brand-kit/` folder, so the parts slot together into the full set.",
              "- Downloading from GitHub: open a zip, then press the download button (top right of the file view). Repeat for each part you want.",
              "- The parts of a style are grouped so you can take only what you need: the first parts hold the YouTube and social files,",
              "  then the Premiere / sound / textures files, then the merch, then everything else (guide, logos, videos, paperwork, website).",
              "", "## Good to know", "",
              "- These zips hold exactly the same files as the folders in this kit. Nothing extra and nothing different.",
              "- Several sets share some of the same parts (the merch set and a style set both include that style's merch part, for example).",
              "  Identical parts are stored only once, so the downloads folder is smaller than the table above adds up to "
              f"(about {unique / 1e9:.1f} GB in all).",
              "- If you change anything in the kit, `python3 code/make_zips.py` makes the zips again.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
