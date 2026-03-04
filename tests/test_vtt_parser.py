from lunduke_transcripts.transforms.vtt_parser import (
    parse_vtt,
    render_plain_text,
    render_timestamped_markdown,
)


def test_parse_and_render_vtt() -> None:
    raw = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello <c.colorE5E5E5>world</c>

00:00:03.500 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:06.000
Second line
"""
    cues = parse_vtt(raw)
    assert len(cues) == 2
    assert cues[0].text == "Hello world"
    assert cues[1].text == "Second line"

    ts = render_timestamped_markdown(cues)
    assert "[00:00:01] Hello world" in ts

    plain = render_plain_text(cues)
    assert "Hello world" in plain
    assert "Second line" in plain
