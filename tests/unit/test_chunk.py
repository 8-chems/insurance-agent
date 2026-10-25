from src.ingestion.chunk import chunk_by_section, clean_text, semantic_chunks


def test_clean_text_rejoins_words_and_drops_footer():
    assert clean_text("cover-\nage\nPage 3 of 9\n") == "coverage"


def test_chunk_by_section_keeps_heading_with_text():
    pages = ["6.2 Outpatient care\nReimbursed at 80%, subject to a limit.\n6.3 Dental\nSeparate rules."]
    chunks = chunk_by_section(pages)
    assert len(chunks) == 2 and chunks[0]["text"].startswith("6.2 Outpatient care")


def test_semantic_chunks_splits_on_low_similarity():
    sents = ["a", "b", "c"]
    vecs = [[1, 0], [1, 0], [0, 1]]
    assert semantic_chunks(sents, vecs, threshold=0.5) == ["a b", "c"]
