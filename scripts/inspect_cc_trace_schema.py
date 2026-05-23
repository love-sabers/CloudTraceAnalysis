#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("data/kv_cache_traces/cc_traces_weka_042026.jsonl")
with p.open("r", encoding="utf-8") as f:
    obj = json.loads(next(f))
print(type(obj), list(obj.keys()))
print(json.dumps(obj, ensure_ascii=False)[:5000])
