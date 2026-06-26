from pathlib import Path

ROOT = Path("/root/liujun/saber/project/CloudTrace")
base = ROOT / "raw" / "agent_reward_bench" / "cleaned"
for path in sorted(base.rglob("*.json")):
    size = path.stat().st_size
    if size < 1024:
        print("---", path, size)
        print(path.read_text(errors="replace"))
