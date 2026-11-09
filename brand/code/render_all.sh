#!/usr/bin/env bash
# Renders the ASTRIS brand package videos into ../output/videos (+ WAVs into ../output/audio).
# Usage: ./render_all.sh                 everything
#        ./render_all.sh hero2 ident03   just those pieces (script names without .py)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
pieces=("$@")
if [ ${#pieces[@]} -eq 0 ]; then
  pieces=(hero1_go_crazy hero2_3d_reveal hero3_style_switcher hero4_quick_ident)
  for f in ident*.py bonus*.py; do [ -e "$f" ] && pieces+=("${f%.py}"); done
fi
for p in "${pieces[@]}"; do
  f=$(ls ${p}*.py | head -1)
  echo "=== $f"
  python3 "$f" 2>&1 | tee "logs/${f%.py}.log"
done
[ -e master.py ] && python3 master.py 2>&1 | tee logs/master.log || true
