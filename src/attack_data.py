"""Turn MITRE's ATT&CK STIX file into a simple table of techniques."""
from pathlib import Path

import pandas as pd
from mitreattack.stix20 import MitreAttackData

STIX = "data/attack/enterprise-attack.json"
OUT = Path("data/attack/techniques.csv")


def build_table():
    attack = MitreAttackData(STIX)
    rows = []
    for t in attack.get_techniques(remove_revoked_deprecated=True):
        rows.append({
            "technique_id": attack.get_attack_id(t.id),     # e.g. T1059.001
            "name": t.name,                                   # e.g. PowerShell
            "tactics": ", ".join(p.phase_name for p in t.get("kill_chain_phases", [])),
            "description": t.get("description", ""),
        })
    return pd.DataFrame(rows).sort_values("technique_id")


def load_techniques():
    """Used by the other scripts. Builds the table the first time."""
    if not OUT.exists():
        build_table().to_csv(OUT, index=False)
    return pd.read_csv(OUT)


if __name__ == "__main__":
    df = load_techniques()
    print(f"{len(df)} techniques and sub-techniques loaded")
    print(df[["technique_id", "name", "tactics"]].head())