import pytest

from readme_forge.escaping import enc, escape_attr, escape_html, escape_md, escape_md_text, safe_url

WEB = ["http", "https"]


def test_escape_html_neutralizes_tags():
    assert "<" not in escape_html("<img src=x onerror=alert(1)>")


def test_escape_html_handles_none():
    assert escape_html(None) == ""


def test_escape_attr_flattens_newlines():
    assert escape_attr('a\r\nb"') == "a b&quot;"


def test_escape_md_escapes_pipe():
    assert escape_md("a|b") == "a\\|b"


def test_escape_md_flattens_newlines():
    assert "\n" not in escape_md("a\nb")


def test_escape_md_text_keeps_prose_readable():
    assert escape_md_text("e.g. a-b") == "e.g. a-b"


def test_escape_md_text_escapes_pipe():
    assert escape_md_text("a|b") == "a\\|b"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "vbscript:x"])
def test_safe_url_rejects_script_schemes(url):
    assert safe_url(url, WEB) == ""


def test_safe_url_upgrades_bare_domain():
    assert safe_url("example.com", WEB) == "https://example.com/"


def test_safe_url_rejects_markup_characters():
    assert safe_url('https://example.com/"onload="x', WEB) == ""


def test_safe_url_allows_mailto_when_asked():
    assert safe_url("mailto:a@b.com", ["mailto"]) == "mailto:a@b.com"


def test_safe_url_blocks_mailto_by_default():
    assert safe_url("mailto:a@b.com", WEB) == ""


def test_enc_matches_encode_uri_component():
    assert enc("a b/c!'()*~") == "a%20b%2Fc!'()*~"
