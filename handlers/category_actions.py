"""Handles category and image style checkbox selections."""

from __future__ import annotations

import logging

from services import gemini_service
from services.slack_blocks import (
    build_category_checkboxes,
    build_draft_messages,
    build_image_messages,
    build_image_style_checkboxes,
)
from state.session_store import SessionPhase, store

logger = logging.getLogger(__name__)


def register(app):
    # --- Track radio button selection (word count) ---
    @app.action("length_select")
    def handle_length_select(ack, body):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session:
            return
        selected = body["actions"][0].get("selected_option")
        if selected:
            session.word_count_range = selected["value"]

    # --- Confirm length selection → suggest categories ---
    @app.action("confirm_length")
    def handle_confirm_length(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session:
            return

        if not session.word_count_range:
            say(
                text="Please select a post length first.",
                thread_ts=thread_ts,
            )
            return

        session.phase = SessionPhase.SUGGESTING_CATEGORIES
        say(
            text="Analyzing your message for LinkedIn post angles...",
            thread_ts=thread_ts,
        )

        try:
            categories = gemini_service.suggest_categories(session.original_message)
            session.suggested_categories = categories
            session.phase = SessionPhase.AWAITING_CATEGORY_PICK

            blocks = build_category_checkboxes(categories)
            say(
                text="Pick up to 3 angle categories:",
                blocks=blocks,
                thread_ts=thread_ts,
            )
        except Exception:
            logger.exception("Failed to suggest categories")
            say(
                text="Sorry, I had trouble analyzing your message. Please try again.",
                thread_ts=thread_ts,
            )

    # --- Track checkbox selections (categories) ---
    @app.action("category_select")
    def handle_category_select(ack, body):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session:
            return

        selected = body["actions"][0].get("selected_options", [])
        session.selected_categories = [opt["value"] for opt in selected][:3]

    # --- Confirm category selection → generate drafts ---
    @app.action("confirm_categories")
    def handle_confirm_categories(ack, body, say, client):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session:
            return

        if not session.selected_categories:
            say(
                text="Please select at least 1 category first.",
                thread_ts=thread_ts,
            )
            return

        session.phase = SessionPhase.GENERATING_DRAFTS
        say(
            text=f"Generating {len(session.selected_categories)} draft(s)...",
            thread_ts=thread_ts,
        )

        try:
            drafts = gemini_service.generate_drafts(
                session.original_message, session.selected_categories, session.word_count_range or "150-300"
            )
            session.drafts = drafts
            session.phase = SessionPhase.AWAITING_DRAFT_ACTION

            blocks = build_draft_messages(drafts)
            say(
                text="Here are your drafts:",
                blocks=blocks,
                thread_ts=thread_ts,
            )
        except Exception:
            logger.exception("Failed to generate drafts")
            session.phase = SessionPhase.AWAITING_CATEGORY_PICK
            say(
                text="Sorry, draft generation failed. Please try selecting categories again.",
                thread_ts=thread_ts,
            )

    # --- Track checkbox selections (image styles) ---
    @app.action("style_select")
    def handle_style_select(ack, body):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session:
            return

        selected = body["actions"][0].get("selected_options", [])
        session.selected_image_styles = [opt["value"] for opt in selected][:3]

    # --- Custom style text input (just acknowledge) ---
    @app.action("custom_style_input")
    def handle_custom_style_input(ack):
        ack()

    # --- Confirm style selection → generate images ---
    @app.action("confirm_styles")
    def handle_confirm_styles(ack, body, say, client):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session:
            return

        # Check for custom style from the input block
        state_values = body.get("state", {}).get("values", {})
        custom_block = state_values.get("custom_style_block", {})
        custom_input = custom_block.get("custom_style_input", {})
        custom_style = (custom_input.get("value") or "").strip()

        styles = list(session.selected_image_styles)
        if custom_style and len(styles) < 3:
            styles.append(custom_style)

        if not styles:
            say(
                text="Please select at least 1 image style or describe a custom one.",
                thread_ts=thread_ts,
            )
            return

        session.selected_image_styles = styles
        session.phase = SessionPhase.GENERATING_IMAGES
        say(
            text=f"Generating {len(styles)} image(s)... this may take a moment.",
            thread_ts=thread_ts,
        )

        try:
            results = gemini_service.generate_images(session.selected_draft, styles)

            session.image_bytes_list = []
            session.image_prompts_used = []
            uploaded_count = 0

            for i, (style, img_bytes) in enumerate(results):
                session.image_prompts_used.append(style)
                if img_bytes:
                    session.image_bytes_list.append(img_bytes)
                    client.files_upload_v2(
                        channel=channel_id,
                        thread_ts=thread_ts,
                        content=img_bytes,
                        filename=f"image_{i + 1}_{style.replace(' ', '_')}.png",
                        title=f"Image {i + 1}: {style}",
                    )
                    uploaded_count += 1
                else:
                    session.image_bytes_list.append(None)

            if uploaded_count == 0:
                session.phase = SessionPhase.AWAITING_STYLE_PICK
                say(
                    text="All image generation attempts failed. Please try different styles.",
                    thread_ts=thread_ts,
                )
                return

            session.phase = SessionPhase.AWAITING_IMAGE_ACTION
            blocks = build_image_messages(len(session.image_bytes_list))
            say(
                text="Here are your images:",
                blocks=blocks,
                thread_ts=thread_ts,
            )
        except Exception:
            logger.exception("Failed to generate images")
            session.phase = SessionPhase.AWAITING_STYLE_PICK
            say(
                text="Sorry, image generation failed. Please try again.",
                thread_ts=thread_ts,
            )
