"""Score one run against the answer keys."""
import argparse
import csv
from pathlib import Path

import pandas as pd

GOLD = Path("data/gold")


def ids(path):
    """Read just the technique_id column. Tolerates stray commas in other columns."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    header = [h.strip().lower() for h in rows[0]]
    col = header.index("technique_id")
    return {r[col].strip().upper() for r in rows[1:] if len(r) > col and r[col].strip()}


def parents(s):
    return {t.split(".")[0] for t in s}


def counts(pred, gold):
    return len(pred & gold), len(pred - gold), len(gold - pred)   # tp, fp, fn


def add_scores(df):
    df["precision"] = df.tp / (df.tp + df.fp)
    df["recall"] = df.tp / (df.tp + df.fn)
    df["f1"] = 2 * df.precision * df.recall / (df.precision + df.recall)
    return df.fillna(0).round(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    run_dir = Path("results") / args.run

    rows, review = [], []
    for gold_file in sorted(GOLD.glob("*.csv")):
        if gold_file.stem.endswith("_mine"):
            continue
        rid = gold_file.stem
        pred_file = run_dir / f"{rid}.csv"
        if not pred_file.exists():
            print(f"{rid}: no results in this run, skipping")
            continue
        gold, pred = ids(gold_file), ids(pred_file)
        for level, g, p in [("strict", gold, pred), ("parent", parents(gold), parents(pred))]:
            tp, fp, fn = counts(p, g)
            rows.append({"report_id": rid, "level": level, "tp": tp, "fp": fp, "fn": fn})
        # save the model's "extra" answers so you can judge them by hand
        preds = pd.read_csv(pred_file).drop_duplicates("technique_id")
        extra = preds[~preds["technique_id"].isin(gold)].assign(report_id=rid, verdict="")
        review.append(extra[["report_id", "technique_id", "technique_name", "evidence", "verdict"]])

    per_report = add_scores(pd.DataFrame(rows))
    overall = add_scores(per_report.groupby("level")[["tp", "fp", "fn"]].sum().reset_index())
    per_report.to_csv(run_dir / "scores_by_report.csv", index=False)
    overall.to_csv(run_dir / "scores_overall.csv", index=False)
    pd.concat(review).to_csv(run_dir / "false_positives_review.csv", index=False)
    print(overall.to_string(index=False))