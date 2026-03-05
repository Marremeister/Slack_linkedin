"""Tests for services/url_fetcher.py."""

from unittest.mock import MagicMock, patch

from services.url_fetcher import extract_urls, fetch_all_urls, fetch_page_content, strip_urls


class TestExtractUrls:
    def test_slack_format(self):
        text = "Check this out <https://example.com>"
        assert extract_urls(text) == ["https://example.com"]

    def test_slack_with_label(self):
        text = "See <https://example.com|Example Site> for details"
        assert extract_urls(text) == ["https://example.com"]

    def test_plain_url(self):
        text = "Visit https://example.com for more info"
        assert extract_urls(text) == ["https://example.com"]

    def test_no_urls(self):
        assert extract_urls("no links here") == []

    def test_multiple_slack_urls(self):
        text = "<https://a.com> and <https://b.com>"
        assert extract_urls(text) == ["https://a.com", "https://b.com"]


class TestStripUrls:
    def test_strip_slack_url(self):
        text = "Check this <https://example.com> out"
        result = strip_urls(text)
        assert "https://example.com" not in result
        assert "Check this" in result

    def test_strip_plain_url(self):
        text = "Visit https://example.com today"
        result = strip_urls(text)
        assert "https://example.com" not in result

    def test_strip_preserves_commentary(self):
        text = "My thoughts on this article <https://example.com>"
        result = strip_urls(text)
        assert result == "My thoughts on this article"


class TestFetchPageContent:
    @patch("services.url_fetcher.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><p>Hello World</p></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_page_content("https://example.com")
        assert result is not None
        assert "Hello World" in result
        mock_get.assert_called_once()

    @patch("services.url_fetcher.requests.get")
    def test_failure(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = fetch_page_content("https://example.com")
        assert result is None

    @patch("services.url_fetcher.requests.get")
    def test_truncation_at_max_chars(self, mock_get):
        long_content = "A" * 6000
        mock_resp = MagicMock()
        mock_resp.text = f"<html><body><p>{long_content}</p></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_page_content("https://example.com", max_chars=100)
        assert result is not None
        assert result.endswith("...")
        # 100 chars of content + "..."
        assert len(result) == 103


class TestFetchAllUrls:
    @patch("services.url_fetcher.fetch_page_content")
    def test_combines_multiple(self, mock_fetch):
        mock_fetch.side_effect = ["Content A", "Content B"]
        result = fetch_all_urls(["https://a.com", "https://b.com"])
        assert "Content A" in result
        assert "Content B" in result
        assert "---" in result

    @patch("services.url_fetcher.fetch_page_content")
    def test_skips_failed(self, mock_fetch):
        mock_fetch.side_effect = ["Content A", None]
        result = fetch_all_urls(["https://a.com", "https://b.com"])
        assert "Content A" in result
        assert "b.com" not in result

    @patch("services.url_fetcher.fetch_page_content")
    def test_all_failed(self, mock_fetch):
        mock_fetch.return_value = None
        result = fetch_all_urls(["https://a.com"])
        assert result == ""
