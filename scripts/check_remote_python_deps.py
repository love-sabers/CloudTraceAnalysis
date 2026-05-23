#!/usr/bin/env python3
import importlib.util

for module in ["pandas", "pyarrow", "datasets", "huggingface_hub", "matplotlib", "numpy"]:
    print(module, bool(importlib.util.find_spec(module)))
