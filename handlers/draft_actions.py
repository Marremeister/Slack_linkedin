"""Handles Accept/Edit buttons for drafts."""

from __future__ import annotations

import logging
import re

from services import gemini_service
from services.slack_blocks import build_image_style_checkboxes
from state.session_store import SessionPhase, store

logger = logging.getLogger(__name__)

# Match action_ids like accept_draft_0, accept_draft_1, etc.
ACCEPT_PATTERN = re.compile(r"^accept_draft_(\d+)$")
EDIT_PATTERN = re.compile(r"^edit_draft_(\d+)$")


def register(app):
    @app.action(ACCEPT_PATTERN)
    def handle_accept_draft(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_DRAFT_ACTION:
            return

        action_id = body["actions"][0]["action_id"]
        match = ACCEPT_PATTERN.match(action_id)
        idx = int(match.group(1))

        if idx >= len(session.drafts):
            say(text="Invalid draft selection.", thread_ts=thread_ts)
            return

        session.selected_draft = session.drafts[idx]
        session.phase = SessionPhase.DRAFT_ACCEPTED

        say(
            text=f"Draft {idx + 1} accepted! Now suggesting image styles...",
            thread_ts=thread_ts,
        )

        # Move to image style suggestion
        session.phase = SessionPhase.SUGGESTING_IMAGE_STYLES

        try:
            styles = gemini_service.suggest_image_styles(session.selected_draft)
            session.suggested_image_styles = styles
            session.phase = SessionPhase.AWAITING_STYLE_PICK

            blocks = build_image_style_checkboxes(styles)
            say(
                text="Pick image styles:",
                blocks=blocks,
                thread_ts=thread_ts,
            )
        except Exception:
            logger.exception("Failed to suggest image styles")
            say(
                text="Sorry, I couldn't suggest image styles. Please try again.",
                thread_ts=thread_ts,
            )

    @app.action(EDIT_PATTERN)
    def handle_edit_draft(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_DRAFT_ACTION:
            return

        action_id = body["actions"][0]["action_id"]
        match = EDIT_PATTERN.match(action_id)
        idx = int(match.group(1))

        if idx >= len(session.drafts):
            say(text="Invalid draft selection.", thread_ts=thread_ts)
            return

        session.draft_being_edited = session.drafts[idx]
        session.phase = SessionPhase.AWAITING_DRAFT_FEEDBACK

        say(
            text=f"Editing Draft {idx + 1}. Reply in this thread with your feedback and I'll generate 3 revised versions.",
            thread_ts=thread_ts,
        )
