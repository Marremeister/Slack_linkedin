"""Handles new channel messages and thread replies (feedback)."""

from __future__ import annotations

import logging

import config
from services import gemini_service
from services.slack_blocks import build_category_checkboxes, build_word_count_picker
from state.session_store import SessionPhase, store

logger = logging.getLogger(__name__)


def register(app):
    @app.event("message")
    def handle_message(event, say, client):
        # Ignore bot messages
        if event.get("subtype") == "bot_message" or "bot_id" in event:
            return

        channel_id = event.get("channel")
        user_id = event.get("user")
        text = event.get("text", "").strip()
        thread_ts = event.get("thread_ts")
        message_ts = event.get("ts")

        if not text:
            return

        # --- Thread reply: might be feedback ---
        if thread_ts:
            session = store.get(channel_id, thread_ts)
            if not session:
                return

            if session.phase == SessionPhase.AWAITING_DRAFT_FEEDBACK:
                _handle_draft_feedback(session, text, say, client)
                return

            if session.phase == SessionPhase.AWAITING_IMAGE_FEEDBACK:
                _handle_image_feedback(session, text, say, client)
                return

            # Not in a feedback phase — ignore thread reply
            return

        # --- New top-level message in target channel ---
        if channel_id != config.TARGET_CHANNEL_ID:
            return

        # Create session keyed by the message's ts (which becomes the thread)
        session = store.create(
            channel_id=channel_id,
            thread_ts=message_ts,
            user_id=user_id,
            original_message=text,
        )
        session.phase = SessionPhase.AWAITING_LENGTH_PICK

        blocks = build_word_count_picker()
        say(
            text="How long should your LinkedIn post be?",
            blocks=blocks,
            thread_ts=message_ts,
        )


def _handle_draft_feedback(session, feedback_text, say, client):
    from services.slack_blocks import build_draft_messages

    session.feedback_text = feedback_text
    session.phase = SessionPhase.GENERATING_DRAFTS

    say(
        text="Got your feedback! Generating 3 revised drafts...",
        thread_ts=session.thread_ts,
        channel=session.channel_id,
    )

    try:
        revised = gemini_service.revise_draft(
            session.original_message,
            session.draft_being_edited,
            feedback_text,
            session.word_count_range or "150-300",
        )
        session.drafts = revised
        session.phase = SessionPhase.AWAITING_DRAFT_ACTION

        blocks = build_draft_messages(revised)
        say(
            text="Here are your revised drafts:",
            blocks=blocks,
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )
    except Exception:
        logger.exception("Failed to revise draft")
        session.phase = SessionPhase.AWAITING_DRAFT_FEEDBACK
        say(
            text="Sorry, draft revision failed. Please reply with your feedback again.",
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )


def _handle_image_feedback(session, feedback_text, say, client):
    from services.slack_blocks import build_image_messages

    session.feedback_text = feedback_text
    session.phase = SessionPhase.GENERATING_IMAGES

    say(
        text="Got your feedback! Generating 3 revised images...",
        thread_ts=session.thread_ts,
        channel=session.channel_id,
    )

    try:
        description = (
            session.image_prompts_used[session.selected_image_index]
            if session.selected_image_index is not None and session.image_prompts_used
            else "LinkedIn post image"
        )
        revised_images = gemini_service.revise_images(
            session.selected_draft, description, feedback_text
        )

        # Upload images
        session.image_bytes_list = []
        uploaded_count = 0
        for i, img_bytes in enumerate(revised_images):
            if img_bytes:
                session.image_bytes_list.append(img_bytes)
                client.files_upload_v2(
                    channel=session.channel_id,
                    thread_ts=session.thread_ts,
                    content=img_bytes,
                    filename=f"revised_image_{i + 1}.png",
                    title=f"Revised Image {i + 1}",
                )
                uploaded_count += 1
            else:
                session.image_bytes_list.append(None)

        if uploaded_count == 0:
            session.phase = SessionPhase.AWAITING_IMAGE_FEEDBACK
            say(
                text="Image generation failed. Please reply with different feedback.",
                thread_ts=session.thread_ts,
                channel=session.channel_id,
            )
            return

        session.phase = SessionPhase.AWAITING_IMAGE_ACTION
        blocks = build_image_messages(len(session.image_bytes_list))
        say(
            text="Here are your revised images:",
            blocks=blocks,
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )
    except Exception:
        logger.exception("Failed to revise images")
        session.phase = SessionPhase.AWAITING_IMAGE_FEEDBACK
        say(
            text="Sorry, image revision failed. Please reply with your feedback again.",
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )
