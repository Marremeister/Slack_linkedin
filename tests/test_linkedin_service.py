"""Tests for services/linkedin_service.py."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from services import linkedin_service


# ===================================================================
# Helpers
# ===================================================================

def _reset_cached_urn():
    """Clear the module-level URN cache between tests."""
    linkedin_service._cached_person_urn = None


@pytest.fixture(autouse=True)
def _clean_urn_cache():
    _reset_cached_urn()
    yield
    _reset_cached_urn()


# ===================================================================
# Mock mode (no credentials)
# ===================================================================

class TestMockMode:
    @patch("services.linkedin_service.config")
    def test_publish_returns_mock_shape(self, mock_config):
        mock_config.LINKEDIN_ACCESS_TOKEN = ""
        result = linkedin_service.publish_post("Hello world")
        assert result["status"] == "published"
        assert result["mock"] is True
        assert "post_id" in result
        assert "url" in result

    @patch("services.linkedin_service.config")
    def test_publish_with_image_returns_mock(self, mock_config):
        mock_config.LINKEDIN_ACCESS_TOKEN = ""
        result = linkedin_service.publish_post("Hello", image_bytes=b"IMG")
        assert result["mock"] is True

    @patch("services.linkedin_service.config")
    def test_schedule_returns_mock_shape(self, mock_config):
        mock_config.LINKEDIN_ACCESS_TOKEN = ""
        dt = datetime(2025, 6, 1, 10, 0)
        result = linkedin_service.schedule_post("Hello", dt)
        assert result["status"] == "scheduled"
        assert result["mock"] is True
        assert "scheduled_for" in result


# ===================================================================
# Real mode — image upload
# ===================================================================

class TestImageUpload:
    @patch("services.linkedin_service.requests")
    @patch("services.linkedin_service.config")
    def test_upload_image_makes_two_requests(self, mock_config, mock_requests):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_config.LINKEDIN_PERSON_URN = "urn:li:person:abc"

        # initializeUpload response
        init_resp = MagicMock()
        init_resp.json.return_value = {
            "value": {
                "uploadUrl": "https://upload.example.com/put-here",
                "image": "urn:li:image:999",
            }
        }
        # PUT response
        put_resp = MagicMock()

        mock_requests.post.return_value = init_resp
        mock_requests.put.return_value = put_resp

        urn = linkedin_service._upload_image(b"IMGDATA")

        assert urn == "urn:li:image:999"
        mock_requests.post.assert_called_once()
        mock_requests.put.assert_called_once()
        # Verify PUT was to the correct URL with the image bytes
        put_call = mock_requests.put.call_args
        assert put_call.args[0] == "https://upload.example.com/put-here"
        assert put_call.kwargs["data"] == b"IMGDATA"


# ===================================================================
# Real mode — post creation
# ===================================================================

class TestCreatePost:
    @patch("services.linkedin_service.requests")
    @patch("services.linkedin_service.config")
    def test_create_post_with_image(self, mock_config, mock_requests):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_config.LINKEDIN_PERSON_URN = "urn:li:person:abc"

        resp = MagicMock()
        resp.headers = {"x-restli-id": "urn:li:share:456"}
        mock_requests.post.return_value = resp

        result = linkedin_service._create_post("My post", image_urn="urn:li:image:999")

        assert result["status"] == "published"
        assert result["post_id"] == "urn:li:share:456"
        # Verify JSON body contains content with media
        call_kwargs = mock_requests.post.call_args.kwargs
        assert call_kwargs["json"]["content"]["media"]["id"] == "urn:li:image:999"

    @patch("services.linkedin_service.requests")
    @patch("services.linkedin_service.config")
    def test_create_post_text_only_omits_content(self, mock_config, mock_requests):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_config.LINKEDIN_PERSON_URN = "urn:li:person:abc"

        resp = MagicMock()
        resp.headers = {"x-restli-id": "urn:li:share:789"}
        mock_requests.post.return_value = resp

        linkedin_service._create_post("Text only post")

        call_kwargs = mock_requests.post.call_args.kwargs
        assert "content" not in call_kwargs["json"]


# ===================================================================
# Real mode — publish_post / schedule_post
# ===================================================================

class TestPublishPost:
    @patch("services.linkedin_service._create_post")
    @patch("services.linkedin_service._upload_image")
    @patch("services.linkedin_service.config")
    def test_publish_with_image_uploads_then_posts(
        self, mock_config, mock_upload, mock_create
    ):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_upload.return_value = "urn:li:image:111"
        mock_create.return_value = {
            "status": "published",
            "post_id": "urn:li:share:222",
            "url": "https://www.linkedin.com/feed/update/urn:li:share:222",
            "timestamp": "2025-01-01T00:00:00",
        }

        result = linkedin_service.publish_post("Hello", image_bytes=b"IMG")

        mock_upload.assert_called_once_with(b"IMG")
        mock_create.assert_called_once_with("Hello", "urn:li:image:111")
        assert result["status"] == "published"

    @patch("services.linkedin_service._create_post")
    @patch("services.linkedin_service.config")
    def test_publish_text_only_skips_upload(self, mock_config, mock_create):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_create.return_value = {
            "status": "published",
            "post_id": "urn:li:share:333",
            "url": "https://www.linkedin.com/feed/update/urn:li:share:333",
            "timestamp": "2025-01-01T00:00:00",
        }

        result = linkedin_service.publish_post("Text only")

        mock_create.assert_called_once_with("Text only", None)
        assert result["status"] == "published"

    @patch("services.linkedin_service._create_post")
    @patch("services.linkedin_service.config")
    def test_api_error_returns_error_dict(self, mock_config, mock_create):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_create.side_effect = requests.RequestException("Connection refused")

        result = linkedin_service.publish_post("Hello")

        assert result["status"] == "error"
        assert "Connection refused" in result["error"]


class TestSchedulePost:
    @patch("services.linkedin_service._create_post")
    @patch("services.linkedin_service.config")
    def test_schedule_publishes_immediately_with_note(self, mock_config, mock_create):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_create.return_value = {
            "status": "published",
            "post_id": "urn:li:share:444",
            "url": "https://www.linkedin.com/feed/update/urn:li:share:444",
            "timestamp": "2025-01-01T00:00:00",
        }

        dt = datetime(2025, 6, 1, 10, 0)
        result = linkedin_service.schedule_post("Hello", dt)

        assert result["status"] == "published"
        assert "note" in result
        assert "immediately" in result["note"]

    @patch("services.linkedin_service._create_post")
    @patch("services.linkedin_service.config")
    def test_schedule_api_error(self, mock_config, mock_create):
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok123"
        mock_create.side_effect = requests.RequestException("Timeout")

        dt = datetime(2025, 6, 1, 10, 0)
        result = linkedin_service.schedule_post("Hello", dt)

        assert result["status"] == "error"
        assert "Timeout" in result["error"]


# ===================================================================
# Person URN resolution
# ===================================================================

class TestResolvePersonUrn:
    @patch("services.linkedin_service.requests")
    @patch("services.linkedin_service.config")
    def test_uses_config_urn_when_set(self, mock_config, mock_requests):
        mock_config.LINKEDIN_PERSON_URN = "urn:li:person:fromconfig"
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok"

        result = linkedin_service._resolve_person_urn()

        assert result == "urn:li:person:fromconfig"
        mock_requests.get.assert_not_called()

    @patch("services.linkedin_service.requests")
    @patch("services.linkedin_service.config")
    def test_fetches_urn_from_userinfo(self, mock_config, mock_requests):
        mock_config.LINKEDIN_PERSON_URN = ""
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok"

        resp = MagicMock()
        resp.json.return_value = {"sub": "abc123"}
        mock_requests.get.return_value = resp

        result = linkedin_service._resolve_person_urn()

        assert result == "urn:li:person:abc123"
        mock_requests.get.assert_called_once()

    @patch("services.linkedin_service.requests")
    @patch("services.linkedin_service.config")
    def test_caches_resolved_urn(self, mock_config, mock_requests):
        mock_config.LINKEDIN_PERSON_URN = ""
        mock_config.LINKEDIN_ACCESS_TOKEN = "tok"

        resp = MagicMock()
        resp.json.return_value = {"sub": "abc123"}
        mock_requests.get.return_value = resp

        linkedin_service._resolve_person_urn()
        linkedin_service._resolve_person_urn()

        # Only one API call despite two invocations
        assert mock_requests.get.call_count == 1
