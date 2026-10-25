import os
from functools import lru_cache
from google import genai
from google.genai.types import EmbedContentConfig

MODEL = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001")   # check current model names


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    return genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                        location=os.environ["GOOGLE_CLOUD_LOCATION"])


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    out = []
    for i in range(0, len(texts), 50):                 # batch; add retries for production
        r = _client().models.embed_content(model=MODEL, contents=texts[i:i + 50],
                                           config=EmbedContentConfig(task_type=task_type))
        out += [e.values for e in r.embeddings]
    return out


def embed_for_index(chunks): return embed(chunks, "RETRIEVAL_DOCUMENT")
def embed_query(question): return embed([question], "RETRIEVAL_QUERY")[0]
