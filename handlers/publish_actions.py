"""Handles Publish Now / Schedule / date-time picker actions."""

from __future__ import annotations

import logging
from datetime import datetime

from services import linkedin_service
from services.slack_blocks import build_publish_edit_modal, build_publish_options, build_schedule_picker
from state.session_store import SessionPhase, store

logger = logging.getLogger(__name__)


def register(app):
    @app.action("publish_now")
    def handle_publish_now(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_PUBLISH_DECISION:
            return

        result = linkedin_service.publish_post(
            session.selected_draft, session.selected_image_bytes
        )
        session.phase = SessionPhase.DONE

        say(
            text=(
                f"*Published!* :white_check_mark:\n"
                f"Post ID: `{result['post_id']}`\n"
                f"URL: {result['url']}\n"
                f"_(This is a mock publish — LinkedIn integration coming soon)_"
            ),
            thread_ts=thread_ts,
        )

    @app.action("schedule_post")
    def handle_schedule_post(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_PUBLISH_DECISION:
            return

        session.phase = SessionPhase.AWAITING_SCHEDULE_TIME

        blocks = build_schedule_picker()
        say(
            text="Pick a date and time:",
            blocks=blocks,
            thread_ts=thread_ts,
        )

    # Track date/time picker selections (just acknowledge)
    @app.action("schedule_date")
    def handle_schedule_date(ack):
        ack()

    @app.action("schedule_time")
    def handle_schedule_time(ack):
        ack()

    @app.action("confirm_schedule")
    def handle_confirm_schedule(ack, body, say):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_SCHEDULE_TIME:
            return

        # Extract date and time from state
        state_values = body.get("state", {}).get("values", {})
        selected_date = None
        selected_time = None

        for block_values in state_values.values():
            for action_id, action_data in block_values.items():
                if action_id == "schedule_date":
                    selected_date = action_data.get("selected_date")
                elif action_id == "schedule_time":
                    selected_time = action_data.get("selected_time")

        if not selected_date or not selected_time:
            say(
                text="Please select both a date and time before confirming.",
                thread_ts=thread_ts,
            )
            return

        scheduled_dt = datetime.fromisoformat(f"{selected_date}T{selected_time}")

        result = linkedin_service.schedule_post(
            session.selected_draft,
            scheduled_dt,
            session.selected_image_bytes,
        )
        session.phase = SessionPhase.DONE

        say(
            text=(
                f"*Scheduled!* :calendar:\n"
                f"Post ID: `{result['post_id']}`\n"
                f"Scheduled for: {result['scheduled_for']}\n"
                f"URL: {result['url']}\n"
                f"_(This is a mock schedule — LinkedIn integration coming soon)_"
            ),
            thread_ts=thread_ts,
        )

    @app.action("edit_before_publish")
    def handle_edit_before_publish(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
        session = store.get(channel_id, thread_ts)
        if not session or session.phase != SessionPhase.AWAITING_PUBLISH_DECISION:
            return

        modal = build_publish_edit_modal(
            draft=session.selected_draft,
            thread_ts=thread_ts,
            channel_id=channel_id,
        )
        client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.view("publish_edit_submit")
    def handle_publish_edit_submit(ack, body, client):
        ack()
        metadata = body["view"]["private_metadata"]
        channel_id, thread_ts = metadata.split("|")

        edited_text = (
            body["view"]["state"]["values"]
            ["draft_text_block"]["draft_text_input"]["value"]
        )

        session = store.get(channel_id, thread_ts)
        if not session:
            return

        session.selected_draft = edited_text
        session.phase = SessionPhase.AWAITING_PUBLISH_DECISION

        has_image = session.selected_image_bytes is not None
        blocks = build_publish_options(session.selected_draft, has_image=has_image)
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Draft updated! Ready to publish:",
            blocks=blocks,
        )
