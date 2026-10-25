import os
import re
from functools import lru_cache

import numpy as np

HEADING = re.compile(r"^(\d+(\.\d+)*)\s+[A-Z].+$", re.M)
HF_MODEL = os.environ.get("HF_BOUNDARY_MODEL",
                          "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


def clean_text(t: str) -> str:
    t = t.replace("\u00ad", "")
    t = re.sub(r"-\n(?=[a-z])", "", t)
    t = re.sub(r"^Page \d+ of \d+\s*$", "", t, flags=re.M)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def chunk_by_section(pages: list[str], max_chars: int = 1800):
    chunks = []
    for page_no, text in enumerate(pages, start=1):
        marks = [m.start() for m in HEADING.finditer(text)] + [len(text)]
        for a, b in zip(marks, marks[1:]):
            body = text[a:b].strip()
            if not body:
                continue
            title = body.splitlines()[0]
            for i in range(0, len(body), max_chars):
                chunks.append({"section": title, "page": page_no, "text": f"{title}\n{body[i:i + max_chars]}"})
    return chunks


def cosine_similarity(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return 0.0 if d == 0 else float(np.dot(a, b) / d)


def semantic_chunks(sentences, embeddings, threshold=0.65):
    if len(sentences) != len(embeddings):
        raise ValueError("counts must match")
    if not sentences:
        return []
    chunks, current = [], [sentences[0]]
    for i in range(1, len(sentences)):
        if cosine_similarity(embeddings[i - 1], embeddings[i]) < threshold:
            chunks.append(" ".join(current))
            current = []
        current.append(sentences[i])
    if current:
        chunks.append(" ".join(current))
    return chunks


# --- Hugging Face helpers (imported lazily so the API image does not need them) ---
@lru_cache(maxsize=1)
def _encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(HF_MODEL)


@lru_cache(maxsize=1)
def _tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(HF_MODEL)


def embed_for_boundaries(sentences: list[str]) -> list[list[float]]:
    return _encoder().encode(sentences, batch_size=64, normalize_embeddings=True).tolist()


def n_tokens(text: str) -> int:
    return len(_tokenizer().encode(text, add_special_tokens=False))


def split_oversized(chunks: list[str], max_tokens: int = 300) -> list[str]:
    out = []
    for c in chunks:
        if n_tokens(c) <= max_tokens:
            out.append(c)
            continue
        cur = []
        for sent in re.split(r"(?<=[.!?])\s+", c):
            if cur and n_tokens(" ".join(cur + [sent])) > max_tokens:
                out.append(" ".join(cur))
                cur = []
            cur.append(sent)
        if cur:
            out.append(" ".join(cur))
    return out
