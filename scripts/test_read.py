
import pathlib
import sys

path = pathlib.Path("raw_data/raw_products_20251213.jsonl")
print(f"Reading {path.absolute()}")
try:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f):
            print(f"Line {i} length: {len(line)}")
            if i >= 5: break
            print(f"Sample: {line[:50]}")
except Exception as e:
    print(f"Error: {e}")
