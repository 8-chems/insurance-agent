from google.cloud import bigquery
from src.ingestion.embeddings import embed_query

SQL = """
SELECT base.chunk_id, base.document_id, base.version, base.section, base.page,
       base.source_uri, base.text, distance
FROM VECTOR_SEARCH(
  (SELECT * FROM kb.chunks
   WHERE status IN UNNEST(@statuses)
     AND effective_from <= @as_of AND (effective_to IS NULL OR effective_to >= @as_of)),
  'embedding', (SELECT @q AS embedding), top_k => @k, distance_type => 'COSINE')
ORDER BY distance"""


def search(question: str, as_of: str, k: int = 5, statuses=("active",)):
    q = embed_query(question)
    job = bigquery.Client().query(SQL, job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("q", "FLOAT64", q),
        bigquery.ArrayQueryParameter("statuses", "STRING", list(statuses)),
        bigquery.ScalarQueryParameter("as_of", "DATE", as_of),
        bigquery.ScalarQueryParameter("k", "INT64", k)]))
    return [dict(r) for r in job.result()]
