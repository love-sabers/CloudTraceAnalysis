#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
import pandas as pd

p = Path("data/kv_cache_traces/mooncake_trace.jsonl")
rows = []
with p.open("r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        o = json.loads(line)
        hashes = o.get("hash_ids", [])
        rows.append(
            {
                "i": i,
                "timestamp": o.get("timestamp"),
                "input_length": o.get("input_length"),
                "output_length": o.get("output_length"),
                "hash_count": len(hashes),
                "ceil_512": int(np.ceil(o.get("input_length", 0) / 512)),
                "ceil_64": int(np.ceil(o.get("input_length", 0) / 64)),
                "hash_ids": hashes,
            }
        )

df = pd.DataFrame(rows)
seen = set()
reuse = []
prefix_reuse = []
new = []
for hashes in df["hash_ids"]:
    r = sum(1 for h in hashes if h in seen)
    pr = 0
    for h in hashes:
        if h in seen:
            pr += 1
        else:
            break
    reuse.append(r)
    prefix_reuse.append(pr)
    new.append(len(hashes) - r)
    seen.update(hashes)
df["reuse_blocks"] = reuse
df["prefix_reuse_blocks"] = prefix_reuse
df["new_blocks"] = new
df["reuse_ratio"] = df["reuse_blocks"] / df["hash_count"].replace(0, np.nan)
df["prefix_reuse_ratio"] = df["prefix_reuse_blocks"] / df["hash_count"].replace(0, np.nan)

print("rows", len(df))
print("input/hash block consistency")
print(df[["input_length", "hash_count", "ceil_512", "ceil_64"]].head(10).to_string(index=False))
print("\nhash_count == ceil(input/512)", (df["hash_count"] == df["ceil_512"]).mean())
print("hash_count == ceil(input/64)", (df["hash_count"] == df["ceil_64"]).mean())
print("\nreuse ratio summary")
print(df["reuse_ratio"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).to_string())
print("\nweighted overall reuse", df["reuse_blocks"].sum() / df["hash_count"].sum())
print("weighted prefix-only reuse", df["prefix_reuse_blocks"].sum() / df["hash_count"].sum())
print("rows where seen-set differs from prefix-only", int((df["reuse_blocks"] != df["prefix_reuse_blocks"]).sum()))
print("unique blocks", len(seen), "total blocks", int(df["hash_count"].sum()))
print("\nzero reuse requests", int((df["reuse_blocks"] == 0).sum()))
print("full reuse requests", int((df["reuse_blocks"] == df["hash_count"]).sum()))
print("\nfirst 20")
print(df[["i", "timestamp", "input_length", "hash_count", "reuse_blocks", "new_blocks", "reuse_ratio"]].head(20).to_string(index=False))
