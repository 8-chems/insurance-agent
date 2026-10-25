from google.cloud import documentai, storage


def extract_pages(gcs_uri: str, processor_name: str) -> list[str]:
    bucket, blob = gcs_uri.removeprefix("gs://").split("/", 1)
    data = storage.Client().bucket(bucket).blob(blob).download_as_bytes()
    client = documentai.DocumentProcessorServiceClient(
        client_options={"api_endpoint": "eu-documentai.googleapis.com"})   # match processor location
    result = client.process_document(request=documentai.ProcessRequest(
        name=processor_name,
        raw_document=documentai.RawDocument(content=data, mime_type="application/pdf")))
    doc = result.document
    pages = []
    for p in doc.pages:
        seg = p.layout.text_anchor.text_segments[0]
        pages.append(doc.text[seg.start_index:seg.end_index])
    return pages
