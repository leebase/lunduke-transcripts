from lunduke_transcripts.transforms.article_writer import normalize_article_timestamps


def test_normalize_moves_timestamp_to_paragraph_end() -> None:
    raw = (
        "[00:00:12] First paragraph sentence.\n\n"
        "[00:01:02] Second paragraph sentence with more text.\n"
    )
    result = normalize_article_timestamps(raw)
    assert "First paragraph sentence. [00:00:12]" in result
    assert "Second paragraph sentence with more text. [00:01:02]" in result
    assert "[00:00:12] First paragraph" not in result


def test_normalize_keeps_existing_end_timestamp() -> None:
    raw = "Paragraph already formatted. [00:02:33]\n"
    result = normalize_article_timestamps(raw)
    assert result.strip() == "Paragraph already formatted. [00:02:33]"
