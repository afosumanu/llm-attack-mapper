"""Find the ATT&CK techniques most similar to a chunk of text."""
from pathlib import Path

import numpy as np
import ollama

from attack_data import load_techniques

VEC_FILE = Path("data/attack/technique_vectors.npy")
TECH = load_techniques()


def embed(texts):
    vecs = np.array(ollama.embed(model="nomic-embed-text", input=texts).embeddings)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def technique_vectors():
    if VEC_FILE.exists():
        return np.load(VEC_FILE)
    texts = (TECH["name"] + ": " + TECH["description"].fillna("").str[:500]).tolist()
    vecs = np.vstack([embed(texts[i:i + 50]) for i in range(0, len(texts), 50)])
    np.save(VEC_FILE, vecs)          # first run takes a few minutes; then it's cached
    return vecs


VECS = technique_vectors()


def top_candidates(chunk, k=25):
    scores = VECS @ embed([chunk])[0]
    best = np.argsort(scores)[::-1][:k]
    return "\n".join(f"{TECH['technique_id'].iloc[i]} {TECH['name'].iloc[i]}" for i in best)