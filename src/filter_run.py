"""Copy a run, keeping only real technique IDs with quotes found in the text."""
import argparse
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--src", required=True)
parser.add_argument("--dst", required=True)
args = parser.parse_args()

src, dst = Path("results") / args.src, Path("results") / args.dst
dst.mkdir(parents=True, exist_ok=True)
for f in src.glob("*.csv"):
    if f.name.startswith(("scores", "false_positives")):
        continue
    df = pd.read_csv(f)
    df[df["valid_id"] & df["evidence_found"]].to_csv(dst / f.name, index=False)
print(f"Filtered copy saved to {dst}")