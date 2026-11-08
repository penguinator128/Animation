#!/usr/bin/env bash
# Renders all four ASTRIS intros at 4K into ./output (MP4 + WAV each).
# Usage: ./render_all.sh            (all four)
#        ./render_all.sh 1 3        (only intros 1 and 3)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output logs
which=("$@"); [ ${#which[@]} -eq 0 ] && which=(1 2 3 4)
for n in "${which[@]}"; do
  case $n in
    1) python3 intro1_go_crazy.py        2>&1 | tee logs/intro1.log ;;
    2) python3 intro2_3d_reveal.py       2>&1 | tee logs/intro2.log ;;
    3) python3 intro3_style_switcher.py  2>&1 | tee logs/intro3.log ;;
    4) python3 intro4_quick_ident.py     2>&1 | tee logs/intro4.log ;;
  esac
done
