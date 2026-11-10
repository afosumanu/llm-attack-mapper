"""Extract text from each PDF and strip anything that gives away the answers."""
import re
from pathlib import Path

from pypdf import PdfReader

RAW, OUT = Path("data/raw"), Path("data/text")
OUT.mkdir(parents=True, exist_ok=True)

TECHNIQUE_ID = re.compile(r"\[?\bT\d{4}(?:\.\d{3})?\b\]?")
ATTACK_HEADING = re.compile(r"MITRE ATT&CK\s+Tactics\s+and\s+Techniques", re.IGNORECASE)


def clean(text):
    # 1. Cut from the LAST ATT&CK heading onward (that's where the answer tables live)
    hits = list(ATTACK_HEADING.finditer(text))
    if hits:
        text = text[: hits[-1].start()]
    # 2. Delete any technique ID still in the body
    text = TECHNIQUE_ID.sub("", text)
    # 3. Tidy whitespace
    return re.sub(r"[ \t]+", " ", text)


if __name__ == "__main__":
    for pdf in sorted(RAW.glob("*.pdf")):
        pages = PdfReader(pdf).pages
        text = clean("\n".join(p.extract_text() or "" for p in pages))
        (OUT / f"{pdf.stem}.txt").write_text(text, encoding="utf-8")
        leftover = len(TECHNIQUE_ID.findall(text))
        print(f"{pdf.stem}: {len(text.split()):,} words, {leftover} IDs left")