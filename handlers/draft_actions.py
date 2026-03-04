"""Handles Accept/Edit buttons for drafts."""

from __future__ import annotations

import logging
import re

from services import gemini_service
from services.slack_blocks import build_image_style_checkboxes, build_manual_edit_modal, build_draft_messages
from state.session_store import SessionPhase, store

logger = logging.getLogger(__name__)

# Match action_ids like accept_draft_0, accept_draft_1, etc.
ACCEPT_PATTERN = re.compile(r"^accept_draft_(\d+)$")
EDIT_PATTERN = re.compile(r"^edit_draft_(\d+)$")
EDIT_MANUAL_PATTERN = re.compile(r"^edit_draft_manual_(\d+)$")


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

    @app.action(EDIT_MANUAL_PATTERN)
    def handle_edit_draft_manual(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_DRAFT_ACTION:
            return

        action_id = body["actions"][0]["action_id"]
        match = EDIT_MANUAL_PATTERN.match(action_id)
        idx = int(match.group(1))

        if idx >= len(session.drafts):
            return

        modal = build_manual_edit_modal(
            draft=session.drafts[idx],
            draft_index=idx,
            thread_ts=thread_ts,
            channel_id=channel_id,
        )
        client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.view("manual_edit_draft_submit")
    def handle_manual_edit_submit(ack, body, say, client):
        ack()
        metadata = body["view"]["private_metadata"]
        channel_id, thread_ts, draft_index_str = metadata.split("|")
        draft_index = int(draft_index_str)

        edited_text = (
            body["view"]["state"]["values"]
            ["draft_text_block"]["draft_text_input"]["value"]
        )

        session = store.get(channel_id, thread_ts)
        if not session:
            return

        # Replace the draft with the manually edited version
        if draft_index < len(session.drafts):
            session.drafts[draft_index] = edited_text

        session.phase = SessionPhase.AWAITING_DRAFT_ACTION

        blocks = build_draft_messages(session.drafts)
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Draft updated! Here are your drafts:",
            blocks=blocks,
        )
