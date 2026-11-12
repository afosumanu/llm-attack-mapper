"""Ask a local LLM which ATT&CK techniques each report describes."""
import argparse
import re
import time
from pathlib import Path

import ollama
import pandas as pd
from pydantic import BaseModel, Field

from attack_data import load_techniques

TEXT = Path("data/text")
CLIENT = ollama.Client(timeout=180)   # give up on any chunk after 3 minutes


# ---- The exact answer shape the model must return (capped to prevent loops) ----
class Finding(BaseModel):
    technique_id: str = Field(max_length=9)
    technique_name: str = Field(max_length=60)
    evidence: str = Field(max_length=300)


class Findings(BaseModel):
    findings: list[Finding] = Field(max_length=12)


PROMPT = """You are a cyber threat intelligence analyst.
Read the report excerpt below and list every MITRE ATT&CK Enterprise technique
that the excerpt describes the adversary actually performing.

Rules:
- Use the most specific ID you are confident in (e.g. T1059.001 rather than T1059).
- Include only adversary behavior described in the excerpt. Ignore mitigations and advice.
- For each technique, copy the exact sentence from the excerpt that shows it into "evidence".
- List each technique only once.
- If the excerpt describes no adversary behavior, return an empty list.

Excerpt:
{chunk}"""


def chunks(text, size=350):
    words = text.split()
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size])


def ask(model, chunk):
    response = CLIENT.chat(
        model=model,
        messages=[{"role": "user", "content": PROMPT.format(chunk=chunk)}],
        format=Findings.model_json_schema(),          # force the JSON shape
        options={
            "temperature": 0,                         # same answer every run
            "num_ctx": 8192,
            "num_predict": 1024,                      # cap answer length (stops loops)
        },
    )
    return Findings.model_validate_json(response.message.content).findings


def squash(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def map_report(path, model, valid_ids):
    text = path.read_text(encoding="utf-8")
    rows = []
    parts = list(chunks(text))
    for n, chunk in enumerate(parts):
        start = time.time()
        print(f"    chunk {n + 1}/{len(parts)} ...", end=" ", flush=True)
        try:
            found = ask(model, chunk)
        except Exception as err:
            print(f"skipped after {time.time() - start:.0f}s ({type(err).__name__})", flush=True)
            continue
        print(f"{len(found)} found in {time.time() - start:.0f}s", flush=True)
        for f in found:
            tid = f.technique_id.strip().upper()
            rows.append({
                "technique_id": tid,
                "technique_name": f.technique_name,
                "evidence": f.evidence,
                "chunk": n,
                "valid_id": tid in valid_ids,                          # real technique?
                "evidence_found": squash(f.evidence) in squash(chunk),  # real quote?
            })
    return pd.DataFrame(rows, columns=["technique_id", "technique_name", "evidence",
                                       "chunk", "valid_id", "evidence_found"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="name for this experiment")
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--only", help="test on one report_id")
    args = parser.parse_args()

    valid_ids = set(load_techniques()["technique_id"])
    out = Path("results") / args.run
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.txt").write_text(f"model: {args.model}\n\n{PROMPT}", encoding="utf-8")

    for path in sorted(TEXT.glob("*.txt")):
        if args.only and path.stem != args.only:
            continue
        out_file = out / f"{path.stem}.csv"
        if out_file.exists():                                  # resume: skip finished reports
            print(f"{path.stem}: already done, skipping")
            continue
        print(f"{path.stem} ...")
        df = map_report(path, args.model, valid_ids)
        df.to_csv(out_file, index=False)
        print(f"    {df['technique_id'].nunique()} techniques, "
              f"{(~df['valid_id']).sum()} invalid IDs, "
              f"{(~df['evidence_found']).sum()} unfound quotes")