import re
from google.cloud import bigquery
from src.ingestion import embeddings
from src.ingestion.chunk import (chunk_by_section, clean_text, embed_for_boundaries,
                                 semantic_chunks, split_oversized)
from src.ingestion.extract import extract_pages

CHUNKER_VERSION = "2026-10-a"


def semantic_fallback(pages):
    out = []
    for n, text in enumerate(pages, 1):
        sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sents:
            continue
        vecs = embed_for_boundaries(sents)
        for t in split_oversized(semantic_chunks(sents, vecs)):
            out.append({"section": "(unstructured)", "page": n, "text": t})
    return out


def process(document_id: str, version: int, source_uri: str, meta: dict, processor_name: str) -> int:
    bq = bigquery.Client()
    pages = [clean_text(p) for p in extract_pages(source_uri, processor_name)]
    chunks = chunk_by_section(pages) or semantic_fallback(pages)
    vecs = embeddings.embed_for_index([c["text"] for c in chunks])
    rows = [{**meta, "chunk_id": f"{document_id}-{i}", "document_id": document_id,
             "version": version, "source_uri": source_uri, "status": "staged",
             "chunker_version": CHUNKER_VERSION, "embedding_model": embeddings.MODEL,
             "section": c["section"], "page": c["page"], "text": c["text"], "embedding": v}
            for i, (c, v) in enumerate(zip(chunks, vecs))]
    bq.query("DELETE FROM kb.chunks WHERE document_id=@d AND status='staged'",
             job_config=bigquery.QueryJobConfig(query_parameters=[
                 bigquery.ScalarQueryParameter("d", "STRING", document_id)])).result()
    bq.load_table_from_json(rows, "kb.chunks").result()
    return len(rows)
