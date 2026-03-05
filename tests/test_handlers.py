"""Tests for handlers/*.py.

Uses FakeApp from conftest to capture handler registrations, then invokes
handlers directly with mock arguments.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from state.session_store import SessionPhase, SessionStore, store


# ===================================================================
# Helpers
# ===================================================================

def _make_action_body(channel_id, thread_ts, action_id, extra=None):
    """Build a minimal Slack action ``body`` dict."""
    body = {
        "channel": {"id": channel_id},
        "message": {"thread_ts": thread_ts, "ts": thread_ts},
        "actions": [{"action_id": action_id}],
        "trigger_id": "T_TRIGGER",
        "state": {"values": {}},
    }
    if extra:
        body.update(extra)
    return body


def _make_view_body(callback_id, metadata, values):
    return {
        "view": {
            "callback_id": callback_id,
            "private_metadata": metadata,
            "state": {"values": values},
        }
    }


# ===================================================================
# message_handler
# ===================================================================

class TestMessageHandler:
    @pytest.fixture(autouse=True)
    def _setup(self, fake_app):
        # Clear the global store between tests
        store._sessions.clear()

        from handlers import message_handler
        message_handler.register(fake_app)
        self.handler = fake_app.get_event_handler("message")

    def test_new_message_creates_session_and_posts_picker(self):
        say = MagicMock()
        event = {
            "channel": "C_TEST_CHANNEL",
            "user": "U1",
            "text": "I want to post about AI",
            "ts": "100.001",
        }
        self.handler(event=event, say=say, client=MagicMock())

        session = store.get("C_TEST_CHANNEL", "100.001")
        assert session is not None
        assert session.phase == SessionPhase.AWAITING_LENGTH_PICK
        say.assert_called()
        # The say call should include blocks (word count picker)
        call_kwargs = say.call_args_list[-1]
        assert "blocks" in (call_kwargs.kwargs if call_kwargs.kwargs else {})

    def test_ignores_bot_message(self):
        say = MagicMock()
        event = {
            "channel": "C_TEST_CHANNEL",
            "user": "U1",
            "text": "bot says hi",
            "ts": "100.002",
            "subtype": "bot_message",
        }
        self.handler(event=event, say=say, client=MagicMock())
        say.assert_not_called()
        assert store.get("C_TEST_CHANNEL", "100.002") is None

    def test_ignores_wrong_channel(self):
        say = MagicMock()
        event = {
            "channel": "C_OTHER",
            "user": "U1",
            "text": "hello",
            "ts": "100.003",
        }
        self.handler(event=event, say=say, client=MagicMock())
        say.assert_not_called()

    @patch("handlers.message_handler.gemini_service")
    def test_thread_reply_draft_feedback(self, mock_gemini):
        mock_gemini.revise_draft.return_value = ["rev1", "rev2", "rev3"]

        # Create session in AWAITING_DRAFT_FEEDBACK phase
        session = store.create("C_TEST_CHANNEL", "200.001", "U1", "original")
        session.phase = SessionPhase.AWAITING_DRAFT_FEEDBACK
        session.draft_being_edited = "old draft"

        say = MagicMock()
        event = {
            "channel": "C_TEST_CHANNEL",
            "user": "U1",
            "text": "make it shorter",
            "ts": "200.002",
            "thread_ts": "200.001",
        }
        self.handler(event=event, say=say, client=MagicMock())

        assert session.phase == SessionPhase.AWAITING_DRAFT_ACTION
        assert session.drafts == ["rev1", "rev2", "rev3"]

    def test_thread_reply_image_upload(self):
        session = store.create("C_TEST_CHANNEL", "300.001", "U1", "original")
        session.phase = SessionPhase.AWAITING_IMAGE_UPLOAD
        session.selected_draft = "my draft"

        say = MagicMock()
        mock_client = MagicMock()

        # requests is imported locally inside _handle_image_upload
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = b"FAKE_IMAGE_BYTES"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            event = {
                "channel": "C_TEST_CHANNEL",
                "user": "U1",
                "text": "",
                "ts": "300.002",
                "thread_ts": "300.001",
                "files": [{"mimetype": "image/png", "url_private": "https://files.slack.com/img.png"}],
            }
            self.handler(event=event, say=say, client=mock_client)

        assert session.phase == SessionPhase.AWAITING_PUBLISH_DECISION
        assert session.selected_image_bytes == b"FAKE_IMAGE_BYTES"


# ===================================================================
# category_actions
# ===================================================================

class TestCategoryActions:
    @pytest.fixture(autouse=True)
    def _setup(self, fake_app):
        store._sessions.clear()

        from handlers import category_actions
        category_actions.register(fake_app)
        self.app = fake_app

    def test_length_select_stores_value(self):
        session = store.create("C1", "ts1", "U1", "msg")
        body = _make_action_body("C1", "ts1", "length_select")
        body["actions"][0]["selected_option"] = {"value": "100-200"}

        handler = self.app.get_action_handler("length_select")
        handler(ack=MagicMock(), body=body)

        assert session.word_count_range == "100-200"

    def test_confirm_length_no_selection(self):
        store.create("C1", "ts1", "U1", "msg")
        body = _make_action_body("C1", "ts1", "confirm_length")

        say = MagicMock()
        handler = self.app.get_action_handler("confirm_length")
        handler(ack=MagicMock(), body=body, say=say)

        say.assert_called_once()
        assert "select a post length" in say.call_args.kwargs["text"].lower()

    @patch("handlers.category_actions.gemini_service")
    def test_confirm_length_success(self, mock_gemini):
        mock_gemini.suggest_categories.return_value = ["Cat A", "Cat B"]

        session = store.create("C1", "ts1", "U1", "msg")
        session.word_count_range = "100-200"

        body = _make_action_body("C1", "ts1", "confirm_length")
        say = MagicMock()
        handler = self.app.get_action_handler("confirm_length")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.phase == SessionPhase.AWAITING_CATEGORY_PICK
        assert session.suggested_categories == ["Cat A", "Cat B"]

    def test_category_select_stores_values(self):
        session = store.create("C1", "ts1", "U1", "msg")
        body = _make_action_body("C1", "ts1", "category_select")
        body["actions"][0]["selected_options"] = [
            {"value": "Cat A"},
            {"value": "Cat B"},
        ]

        handler = self.app.get_action_handler("category_select")
        handler(ack=MagicMock(), body=body)

        assert session.selected_categories == ["Cat A", "Cat B"]

    def test_confirm_categories_no_selection(self):
        store.create("C1", "ts1", "U1", "msg")
        body = _make_action_body("C1", "ts1", "confirm_categories")

        say = MagicMock()
        handler = self.app.get_action_handler("confirm_categories")
        handler(ack=MagicMock(), body=body, say=say, client=MagicMock())

        say.assert_called_once()
        assert "select at least 1" in say.call_args.kwargs["text"].lower()

    def test_confirm_categories_with_custom(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.selected_categories = ["Cat A"]

        body = _make_action_body("C1", "ts1", "confirm_categories")
        body["state"]["values"] = {
            "custom_category_block": {
                "custom_category_input": {"value": "My Custom Cat"},
            },
        }

        say = MagicMock()
        # Mock gemini to prevent actual API call
        with patch("handlers.category_actions.gemini_service") as mock_gemini:
            mock_gemini.generate_drafts.return_value = ["draft1"]
            handler = self.app.get_action_handler("confirm_categories")
            handler(ack=MagicMock(), body=body, say=say, client=MagicMock())

        assert "My Custom Cat" in session.selected_categories

    @patch("handlers.category_actions.gemini_service")
    def test_confirm_categories_success(self, mock_gemini):
        mock_gemini.generate_drafts.return_value = ["Draft 1", "Draft 2"]

        session = store.create("C1", "ts1", "U1", "msg")
        session.selected_categories = ["Cat A", "Cat B"]
        session.word_count_range = "100-200"

        body = _make_action_body("C1", "ts1", "confirm_categories")
        say = MagicMock()
        handler = self.app.get_action_handler("confirm_categories")
        handler(ack=MagicMock(), body=body, say=say, client=MagicMock())

        assert session.phase == SessionPhase.AWAITING_DRAFT_ACTION
        assert session.drafts == ["Draft 1", "Draft 2"]


# ===================================================================
# draft_actions
# ===================================================================

class TestDraftActions:
    @pytest.fixture(autouse=True)
    def _setup(self, fake_app):
        store._sessions.clear()

        from handlers import draft_actions
        draft_actions.register(fake_app)
        self.app = fake_app

    @patch("handlers.draft_actions.gemini_service")
    def test_accept_draft(self, mock_gemini):
        mock_gemini.suggest_image_styles.return_value = ["Style A"]

        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_DRAFT_ACTION
        session.drafts = ["Draft 0", "Draft 1"]

        body = _make_action_body("C1", "ts1", "accept_draft_0")
        say = MagicMock()
        handler = self.app.get_action_handler("accept_draft_0")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.selected_draft == "Draft 0"
        assert session.phase == SessionPhase.AWAITING_STYLE_PICK

    def test_edit_draft_ai(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_DRAFT_ACTION
        session.drafts = ["Draft 0", "Draft 1"]

        body = _make_action_body("C1", "ts1", "edit_draft_1")
        say = MagicMock()
        handler = self.app.get_action_handler("edit_draft_1")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.phase == SessionPhase.AWAITING_DRAFT_FEEDBACK
        assert session.draft_being_edited == "Draft 1"

    def test_edit_draft_manual_opens_modal(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_DRAFT_ACTION
        session.drafts = ["Draft 0"]

        body = _make_action_body("C1", "ts1", "edit_draft_manual_0")
        mock_client = MagicMock()
        handler = self.app.get_action_handler("edit_draft_manual_0")
        handler(ack=MagicMock(), body=body, client=mock_client)

        mock_client.views_open.assert_called_once()
        call_kwargs = mock_client.views_open.call_args.kwargs
        assert call_kwargs["view"]["callback_id"] == "manual_edit_draft_submit"

    def test_manual_edit_submit(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_DRAFT_ACTION
        session.drafts = ["Old Draft"]

        body = _make_view_body(
            "manual_edit_draft_submit",
            "C1|ts1|0",
            {"draft_text_block": {"draft_text_input": {"value": "Edited Draft"}}},
        )
        mock_client = MagicMock()
        handler = self.app.get_view_handler("manual_edit_draft_submit")
        handler(ack=MagicMock(), body=body, say=MagicMock(), client=mock_client)

        assert session.drafts[0] == "Edited Draft"
        assert session.phase == SessionPhase.AWAITING_DRAFT_ACTION
        mock_client.chat_postMessage.assert_called_once()


# ===================================================================
# image_actions
# ===================================================================

class TestImageActions:
    @pytest.fixture(autouse=True)
    def _setup(self, fake_app):
        store._sessions.clear()

        from handlers import image_actions
        image_actions.register(fake_app)
        self.app = fake_app

    def test_accept_image(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_IMAGE_ACTION
        session.selected_draft = "my draft"
        session.image_bytes_list = [b"IMG0", b"IMG1"]

        body = _make_action_body("C1", "ts1", "accept_image_0")
        say = MagicMock()
        handler = self.app.get_action_handler("accept_image_0")
        handler(ack=MagicMock(), body=body, say=say, client=MagicMock())

        assert session.selected_image_bytes == b"IMG0"
        assert session.phase == SessionPhase.AWAITING_PUBLISH_DECISION

    def test_accept_image_null_bytes(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_IMAGE_ACTION
        session.selected_draft = "my draft"
        session.image_bytes_list = [None]

        body = _make_action_body("C1", "ts1", "accept_image_0")
        say = MagicMock()
        handler = self.app.get_action_handler("accept_image_0")
        handler(ack=MagicMock(), body=body, say=say, client=MagicMock())

        assert "failed to generate" in say.call_args.kwargs["text"].lower()

    def test_edit_image(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_IMAGE_ACTION
        session.image_bytes_list = [b"IMG0"]

        body = _make_action_body("C1", "ts1", "edit_image_0")
        say = MagicMock()
        handler = self.app.get_action_handler("edit_image_0")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.phase == SessionPhase.AWAITING_IMAGE_FEEDBACK
        assert session.selected_image_index == 0


# ===================================================================
# publish_actions
# ===================================================================

class TestPublishActions:
    @pytest.fixture(autouse=True)
    def _setup(self, fake_app):
        store._sessions.clear()

        from handlers import publish_actions
        publish_actions.register(fake_app)
        self.app = fake_app

    @patch("handlers.publish_actions.linkedin_service")
    def test_publish_now(self, mock_linkedin):
        mock_linkedin.publish_post.return_value = {
            "post_id": "p1",
            "url": "https://linkedin.com/p1",
        }

        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_PUBLISH_DECISION
        session.selected_draft = "Final post"
        session.selected_image_bytes = b"IMG"

        body = _make_action_body("C1", "ts1", "publish_now")
        say = MagicMock()
        handler = self.app.get_action_handler("publish_now")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.phase == SessionPhase.DONE
        mock_linkedin.publish_post.assert_called_once_with("Final post", b"IMG")

    def test_schedule_post(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_PUBLISH_DECISION

        body = _make_action_body("C1", "ts1", "schedule_post")
        say = MagicMock()
        handler = self.app.get_action_handler("schedule_post")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.phase == SessionPhase.AWAITING_SCHEDULE_TIME
        # Should have posted schedule picker blocks
        say.assert_called()

    @patch("handlers.publish_actions.linkedin_service")
    def test_confirm_schedule(self, mock_linkedin):
        mock_linkedin.schedule_post.return_value = {
            "post_id": "s1",
            "scheduled_for": "2025-06-01T10:00:00",
            "url": "https://linkedin.com/s1",
        }

        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_SCHEDULE_TIME
        session.selected_draft = "Post text"
        session.selected_image_bytes = b"IMG"

        body = _make_action_body("C1", "ts1", "confirm_schedule")
        body["state"]["values"] = {
            "block1": {
                "schedule_date": {"selected_date": "2025-06-01"},
                "schedule_time": {"selected_time": "10:00"},
            },
        }

        say = MagicMock()
        handler = self.app.get_action_handler("confirm_schedule")
        handler(ack=MagicMock(), body=body, say=say)

        assert session.phase == SessionPhase.DONE
        mock_linkedin.schedule_post.assert_called_once()

    def test_edit_before_publish_opens_modal(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_PUBLISH_DECISION
        session.selected_draft = "Draft to edit"

        body = _make_action_body("C1", "ts1", "edit_before_publish")
        mock_client = MagicMock()
        handler = self.app.get_action_handler("edit_before_publish")
        handler(ack=MagicMock(), body=body, client=mock_client)

        mock_client.views_open.assert_called_once()
        view = mock_client.views_open.call_args.kwargs["view"]
        assert view["callback_id"] == "publish_edit_submit"

    def test_publish_edit_submit(self):
        session = store.create("C1", "ts1", "U1", "msg")
        session.phase = SessionPhase.AWAITING_PUBLISH_DECISION
        session.selected_draft = "Old draft"

        body = _make_view_body(
            "publish_edit_submit",
            "C1|ts1",
            {"draft_text_block": {"draft_text_input": {"value": "New draft"}}},
        )
        mock_client = MagicMock()
        handler = self.app.get_view_handler("publish_edit_submit")
        handler(ack=MagicMock(), body=body, client=mock_client)

        assert session.selected_draft == "New draft"
        assert session.phase == SessionPhase.AWAITING_PUBLISH_DECISION
        mock_client.chat_postMessage.assert_called_once()
