#!/usr/bin/env bash
set -euo pipefail

cd /root/liujun/saber/project/CloudTrace

while pgrep -f "python3 scripts/batch_osworld_zips.py" >/dev/null 2>&1; do
  sleep 300
done

python3 scripts/retry_failed_osworld_zips.py
python3 scripts/aggregate_osworld_results.py
python3 scripts/merge_p0_results.py
