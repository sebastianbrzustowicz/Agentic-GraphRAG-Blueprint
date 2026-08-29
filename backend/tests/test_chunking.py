from src.ingestion import _split_sentences, chunk_text


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_one_chunk():
    chunks = chunk_text("This is a single sentence about alpha cells.")
    assert len(chunks) == 1
    assert "alpha cells" in chunks[0]


def test_long_text_splits_into_multiple_chunks_with_overlap():
    sentences = " ".join(f"{chr(65 + i)}." for i in range(20))
    chunks = chunk_text(sentences, chunk_tokens=8, overlap_tokens=2)
    assert len(chunks) > 1
    assert all(chunks)  # no empty chunks
    # The tail of the first chunk must reappear at the start of the second.
    assert chunks[1].startswith("G.")


def test_split_sentences_handles_newlines_and_punctuation():
    parts = _split_sentences("First sentence. Second one!\nThird line? And another.")
    assert parts == ["First sentence.", "Second one!", "Third line?", "And another."]
