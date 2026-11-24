import os

from app.answer import build_answer_xml


def test_answer_xml_uses_bidirectional_inbound_audio_track(monkeypatch):
    monkeypatch.setenv("VOBIZ_ENCODING", "audio/x-mulaw")
    monkeypatch.setenv("VOBIZ_SAMPLE_RATE", "8000")

    xml = build_answer_xml("https://example.ngrok.app")

    assert 'bidirectional="true"' in xml
    assert 'audioTrack="inbound"' in xml
    assert "wss://example.ngrok.app/ws" in xml
    assert "audio/x-mulaw;rate=8000" in xml


def test_answer_xml_encodes_greeting(monkeypatch):
    xml = build_answer_xml(
        "https://example.ngrok.app",
        "Hello there!",
    )

    assert "greeting=Hello%20there%21" in xml


def test_answer_xml_rejects_invalid_public_url():
    import pytest

    with pytest.raises(ValueError):
        build_answer_xml("not-a-url")
