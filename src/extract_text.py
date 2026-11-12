"""Extract text from each PDF and strip anything that gives away the answers."""
import re
from pathlib import Path

from pypdf import PdfReader

RAW, OUT = Path("data/raw"), Path("data/text")
OUT.mkdir(parents=True, exist_ok=True)

# Technique IDs (T1566, T1059.001) AND tactic IDs (TA0001), with or without [brackets]
TECHNIQUE_ID = re.compile(r"\[?\b(?:TA|T)\d{4}(?:\.\d{3})?\b\]?")

# Only a line that is JUST the ATT&CK heading. Handles:
#   "MITRE ATT&CK Tactics and Techniques", "MITRE ATT&CK TECHNIQUES",
#   "Appendix A: MITRE ATT&CK tactics and techniques",
#   "Appendix: MITRE ATT&CK Techniques and Software", and ® or ™ after ATT&CK.
# Skips sentences like "See the MITRE ATT&CK Tactics and Techniques section..."
ATTACK_HEADING = re.compile(
    r"^\s*(?:Appendix\s*\w*\s*[:.\-]?\s*)?MITRE\s+ATT&CK\W{0,3}\s*"
    r"(?:Tactics\s+and\s+)?Techniques(?:\s+and\s+Software)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def clean(text):
    """Return (cleaned text, share of the original kept, whether a heading was found)."""
    original_len = len(text)
    hits = list(ATTACK_HEADING.finditer(text))
    if hits:
        text = text[: hits[-1].start()]      # cut from the last ATT&CK heading onward
    text = TECHNIQUE_ID.sub("", text)        # delete any IDs left in the body
    text = re.sub(r"[ \t]+", " ", text)      # tidy spaces
    return text, len(text) / max(original_len, 1), bool(hits)


if __name__ == "__main__":
    for pdf in sorted(RAW.glob("*.pdf")):
        raw = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
        text, kept, found = clean(raw)
        (OUT / f"{pdf.stem}.txt").write_text(text, encoding="utf-8")
        leftover = len(TECHNIQUE_ID.findall(text))
        flag = "" if found else "   <-- WARNING: no ATT&CK heading found, check by hand"
        print(f"{pdf.stem}: {len(text.split()):,} words, kept {kept:.0%}, {leftover} IDs left{flag}")