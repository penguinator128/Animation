# ASTRIS productions: logo reveal

A 10-second, 90 BPM logo reveal: "The flag was always there."
Six pride bands sit still behind everything; the logo's own pieces (the film strip and six slices of the
leaning bar) are windows that move into place, and the finished logo is the flag seen through the A.

- `assets/astris-logo-source.jpg`: the supplied logo. `scripts/trace_logo.py` traces it into exact polygons
  (`assets/logo-geometry.json`); `scripts/check_trace.py` verifies the trace against the file.
- `src/template.html` → `index.html` (geometry injected). All visuals are pure functions of `t` in `window.seek(t)`.
- `audio.js`: soundtrack built with OfflineAudioContext, exported to WAV.
- `scripts/beat_frames.js`: one frame per beat for review. `scripts/render.js`: 60 fps × 3 subframes → ffmpeg tmix → mux.

Rebuild: `python3 scripts/build_html.py Rebuild: `python3 -c "..."` (inject geometry, see commit history) then `node scripts/render.js`.Rebuild: `python3 -c "..."` (inject geometry, see commit history) then `node scripts/render.js`. node scripts/render.js`
