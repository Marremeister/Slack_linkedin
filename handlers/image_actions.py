"""Handles Accept/Edit buttons for images."""

from __future__ import annotations

import logging
import re

from services.slack_blocks import build_publish_options
from state.session_store import SessionPhase, store

logger = logging.getLogger(__name__)

ACCEPT_PATTERN = re.compile(r"^accept_image_(\d+)$")
EDIT_PATTERN = re.compile(r"^edit_image_(\d+)$")


def register(app):
    @app.action(ACCEPT_PATTERN)
    def handle_accept_image(ack, body, say, client):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_IMAGE_ACTION:
            return

        action_id = body["actions"][0]["action_id"]
        match = ACCEPT_PATTERN.match(action_id)
        idx = int(match.group(1))

        if idx >= len(session.image_bytes_list):
            say(text="Invalid image selection.", thread_ts=thread_ts)
            return

        selected_bytes = session.image_bytes_list[idx]
        if selected_bytes is None:
            say(
                text="That image failed to generate. Please pick another or edit.",
                thread_ts=thread_ts,
            )
            return

        session.selected_image_index = idx
        session.selected_image_bytes = selected_bytes
        session.phase = SessionPhase.IMAGE_ACCEPTED

        say(
            text=f"Image {idx + 1} accepted!",
            thread_ts=thread_ts,
        )

        # Show publish options
        session.phase = SessionPhase.AWAITING_PUBLISH_DECISION
        blocks = build_publish_options(session.selected_draft, has_image=True)
        say(
            text="Ready to publish?",
            blocks=blocks,
            thread_ts=thread_ts,
        )

    @app.action(EDIT_PATTERN)
    def handle_edit_image(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_IMAGE_ACTION:
            return

        action_id = body["actions"][0]["action_id"]
        match = EDIT_PATTERN.match(action_id)
        idx = int(match.group(1))

        session.selected_image_index = idx
        session.phase = SessionPhase.AWAITING_IMAGE_FEEDBACK

        say(
            text=f"Editing Image {idx + 1}. Reply in this thread with your feedback and I'll generate 3 revised versions.",
            thread_ts=thread_ts,
        )
