"""Handles new channel messages and thread replies (feedback)."""

from __future__ import annotations

import logging

import config
from services import gemini_service
from services.slack_blocks import build_category_checkboxes, build_publish_options, build_word_count_picker
from services.url_fetcher import extract_urls, strip_urls, fetch_all_urls
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

        has_files = bool(event.get("files"))
        if not text and not has_files:
            return

        # --- Thread reply: might be feedback ---
        if thread_ts:
            session = store.get(channel_id, thread_ts)
            if not session:
                return

            if session.phase == SessionPhase.AWAITING_DRAFT_FEEDBACK:
                _handle_draft_feedback(session, text, say, client)
                return

            if session.phase == SessionPhase.AWAITING_IMAGE_UPLOAD:
                _handle_image_upload(session, event, say, client)
                return

            if session.phase == SessionPhase.AWAITING_IMAGE_FEEDBACK:
                _handle_image_feedback(session, text, say, client)
                return

            # Not in a feedback phase — ignore thread reply
            return

        # --- New top-level message in target channel ---
        if channel_id != config.TARGET_CHANNEL_ID:
            return

        # Check if message contains URLs — fetch their content
        urls = extract_urls(text)
        user_commentary = strip_urls(text)
        original_message = text

        if urls:
            say(
                text="Fetching content from your link(s)...",
                thread_ts=message_ts,
            )
            fetched = fetch_all_urls(urls)
            if fetched:
                if user_commentary:
                    original_message = f"User's note: {user_commentary}\n\n{fetched}"
                else:
                    original_message = fetched
            elif not user_commentary:
                say(
                    text="I couldn't read the content from that URL. Try posting the text directly instead.",
                    thread_ts=message_ts,
                )
                return

        # Create session keyed by the message's ts (which becomes the thread)
        session = store.create(
            channel_id=channel_id,
            thread_ts=message_ts,
            user_id=user_id,
            original_message=original_message,
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


def _handle_image_upload(session, event, say, client):
    files = event.get("files", [])
    if not files:
        say(
            text="Please upload an image in this thread.",
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )
        return

    # Take the first image file
    uploaded_file = None
    for f in files:
        if f.get("mimetype", "").startswith("image/"):
            uploaded_file = f
            break

    if not uploaded_file:
        say(
            text="That doesn't look like an image. Please upload a PNG, JPG, or similar image file.",
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )
        return

    # Download the file from Slack
    try:
        import requests
        url = uploaded_file["url_private"]
        headers = {"Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"}
        download = requests.get(url, headers=headers, timeout=30)
        download.raise_for_status()
        image_bytes = download.content
    except Exception:
        logger.exception("Failed to download uploaded image")
        say(
            text="Sorry, I couldn't download that image. Please try uploading again.",
            thread_ts=session.thread_ts,
            channel=session.channel_id,
        )
        return

    session.selected_image_bytes = image_bytes
    session.image_bytes_list = [image_bytes]
    session.selected_image_index = 0
    session.phase = SessionPhase.IMAGE_ACCEPTED

    say(
        text="Image received!",
        thread_ts=session.thread_ts,
        channel=session.channel_id,
    )

    # Move to publish options
    session.phase = SessionPhase.AWAITING_PUBLISH_DECISION
    blocks = build_publish_options(session.selected_draft, has_image=True)
    say(
        text="Ready to publish?",
        blocks=blocks,
        thread_ts=session.thread_ts,
        channel=session.channel_id,
    )
