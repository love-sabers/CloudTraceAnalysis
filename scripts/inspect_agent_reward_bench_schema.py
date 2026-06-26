import json
from pathlib import Path

ROOT = Path("/root/liujun/saber/project/CloudTrace")
base = ROOT / "raw" / "agent_reward_bench" / "cleaned"

for path in sorted(base.rglob("*.json")):
    if path.stat().st_size < 1024:
        continue
    print("\n---", path, path.stat().st_size)
    data = json.loads(path.read_text(errors="replace"))
    print("type", type(data).__name__)
    if isinstance(data, dict):
        print("keys", sorted(data.keys()))
        for key in ["benchmark", "agent", "task_id", "success", "steps", "trajectory"]:
            if key in data:
                value = data[key]
                print(key, type(value).__name__, len(value) if hasattr(value, "__len__") else value)
        steps = data.get("steps") or data.get("trajectory") or []
        print("steps", type(steps).__name__, len(steps) if hasattr(steps, "__len__") else "")
        if isinstance(steps, list) and steps:
            for i, step in enumerate(steps[:2]):
                print(" step", i, "keys", sorted(step.keys()) if isinstance(step, dict) else type(step).__name__)
                print(repr(step)[:1200])
    elif isinstance(data, list):
        print("len", len(data))
        print("first", repr(data[0])[:1200] if data else None)
