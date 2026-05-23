#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import re
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PAT = re.compile(r"kv|key.?value|cache|token|sequence|seq|length|prompt", re.I)


def csv_header(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8", errors="replace") as f:
        return next(csv.reader(f))


def tar_csv_headers(path: Path) -> list[tuple[str, list[str]]]:
    headers: list[tuple[str, list[str]]] = []
    with tarfile.open(path, "r:gz") as tar:
        for member in tar:
            if member.isfile() and member.name.endswith(".csv"):
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                with gzip.open(path, "rb"):
                    pass
                text = extracted.readline().decode("utf-8", errors="replace").strip()
                headers.append((member.name, next(csv.reader([text]))))
    return headers


def main() -> None:
    print("README keyword hits:")
    for path in sorted(DATA.glob("*/README.md")):
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if PAT.search(line):
                print(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")

    print("\nCSV headers and keyword-matched columns:")
    for path in sorted(DATA.rglob("*.csv")):
        header = csv_header(path)
        matches = [col for col in header if PAT.search(col)]
        print(f"{path.relative_to(ROOT)}")
        print(f"  columns: {header}")
        print(f"  matched: {matches}")

    print("\ntar.gz internal CSV headers and keyword-matched columns:")
    for path in sorted(DATA.rglob("*.tar.gz")):
        try:
            headers = tar_csv_headers(path)
        except Exception as exc:
            print(f"{path.relative_to(ROOT)}: ERROR {exc}")
            continue
        for name, header in headers:
            matches = [col for col in header if PAT.search(col)]
            print(f"{path.relative_to(ROOT)}::{name}")
            print(f"  columns: {header}")
            print(f"  matched: {matches}")


if __name__ == "__main__":
    main()
