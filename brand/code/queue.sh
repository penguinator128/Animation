#!/usr/bin/env bash
# One-at-a-time render queue: append script names to queue.txt; each runs alone so memory stays safe.
cd "$(dirname "$0")"
mkdir -p logs
touch queue.txt
while true; do
  job=$(head -1 queue.txt 2>/dev/null)
  if [ -z "$job" ]; then sleep 15; continue; fi
  sed -i '1d' queue.txt
  echo "$(date +%T) START $job" >> logs/queue.log
  if python3 $job > "logs/${job%%.py*}.log" 2>&1; then
    echo "$(date +%T) DONE  $job" >> logs/queue.log
  else
    echo "$(date +%T) FAIL  $job" >> logs/queue.log
  fi
done
