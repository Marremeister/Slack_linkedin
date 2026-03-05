"""Tests for services/gemini_service.py.

The module-level ``genai.Client`` is mocked in conftest.py so these tests
never touch the real Gemini API.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from services.gemini_service import (
    _parse_json,
    generate_drafts,
    generate_image,
    suggest_categories,
    suggest_image_styles,
    revise_draft,
)


# ---------------------------------------------------------------------------
# _parse_json
# ---------------------------------------------------------------------------

class TestParseJson:
    def test_plain_json(self):
        result = _parse_json('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_json_with_fences(self):
        text = '```json\n["a", "b"]\n```'
        result = _parse_json(text)
        assert result == ["a", "b"]

    def test_json_with_bare_fences(self):
        text = '```\n{"key": "val"}\n```'
        result = _parse_json(text)
        assert result == {"key": "val"}

    def test_dict(self):
        result = _parse_json('{"x": 1}')
        assert result == {"x": 1}


# ---------------------------------------------------------------------------
# suggest_categories
# ---------------------------------------------------------------------------

class TestSuggestCategories:
    @patch("services.gemini_service.client")
    def test_returns_list(self, mock_client):
        mock_resp = MagicMock()
        mock_resp.text = '["Thought Leadership", "Hot Take"]'
        mock_client.models.generate_content.return_value = mock_resp

        result = suggest_categories("my message")
        assert result == ["Thought Leadership", "Hot Take"]
        mock_client.models.generate_content.assert_called_once()


# ---------------------------------------------------------------------------
# generate_drafts
# ---------------------------------------------------------------------------

class TestGenerateDrafts:
    @patch("services.gemini_service.client")
    def test_returns_draft_strings(self, mock_client):
        payload = [
            {"category": "A", "draft": "Draft A text"},
            {"category": "B", "draft": "Draft B text"},
        ]
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(payload)
        mock_client.models.generate_content.return_value = mock_resp

        result = generate_drafts("msg", ["A", "B"], "100-200")
        assert result == ["Draft A text", "Draft B text"]


# ---------------------------------------------------------------------------
# revise_draft
# ---------------------------------------------------------------------------

class TestReviseDraft:
    @patch("services.gemini_service.client")
    def test_returns_list(self, mock_client):
        mock_resp = MagicMock()
        mock_resp.text = '["rev1", "rev2", "rev3"]'
        mock_client.models.generate_content.return_value = mock_resp

        result = revise_draft("orig", "draft", "feedback")
        assert result == ["rev1", "rev2", "rev3"]


# ---------------------------------------------------------------------------
# suggest_image_styles
# ---------------------------------------------------------------------------

class TestSuggestImageStyles:
    @patch("services.gemini_service.client")
    def test_returns_list(self, mock_client):
        mock_resp = MagicMock()
        mock_resp.text = '["Minimalist", "Photo"]'
        mock_client.models.generate_content.return_value = mock_resp

        result = suggest_image_styles("my draft")
        assert result == ["Minimalist", "Photo"]


# ---------------------------------------------------------------------------
# generate_image
# ---------------------------------------------------------------------------

class TestGenerateImage:
    @patch("services.gemini_service.client")
    def test_returns_bytes(self, mock_client):
        inline_data = MagicMock()
        inline_data.inline_data.data = b"\x89PNG_FAKE"
        inline_data.inline_data.__bool__ = lambda self: True

        # Make inline_data check `is not None` work
        part_with_data = MagicMock()
        part_with_data.inline_data = MagicMock()
        part_with_data.inline_data.data = b"\x89PNG_FAKE"

        mock_resp = MagicMock()
        mock_resp.candidates = [MagicMock()]
        mock_resp.candidates[0].content.parts = [part_with_data]
        mock_client.models.generate_content.return_value = mock_resp

        result = generate_image("draft", "Minimalist")
        assert result == b"\x89PNG_FAKE"

    @patch("services.gemini_service.client")
    def test_returns_none_on_failure(self, mock_client):
        mock_client.models.generate_content.side_effect = Exception("API error")

        result = generate_image("draft", "Minimalist")
        assert result is None
