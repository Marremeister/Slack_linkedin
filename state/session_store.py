from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class SessionPhase(enum.Enum):
    AWAITING_LENGTH_PICK = "awaiting_length_pick"
    SUGGESTING_CATEGORIES = "suggesting_categories"
    AWAITING_CATEGORY_PICK = "awaiting_category_pick"
    GENERATING_DRAFTS = "generating_drafts"
    AWAITING_DRAFT_ACTION = "awaiting_draft_action"
    AWAITING_DRAFT_FEEDBACK = "awaiting_draft_feedback"
    DRAFT_ACCEPTED = "draft_accepted"
    SUGGESTING_IMAGE_STYLES = "suggesting_image_styles"
    AWAITING_STYLE_PICK = "awaiting_style_pick"
    GENERATING_IMAGES = "generating_images"
    AWAITING_IMAGE_ACTION = "awaiting_image_action"
    AWAITING_IMAGE_FEEDBACK = "awaiting_image_feedback"
    IMAGE_ACCEPTED = "image_accepted"
    AWAITING_PUBLISH_DECISION = "awaiting_publish_decision"
    AWAITING_SCHEDULE_TIME = "awaiting_schedule_time"
    DONE = "done"


@dataclass
class Session:
    channel_id: str
    thread_ts: str
    user_id: str
    original_message: str
    phase: SessionPhase = SessionPhase.AWAITING_LENGTH_PICK
    word_count_range: Optional[str] = None
    suggested_categories: list[str] = field(default_factory=list)
    selected_categories: list[str] = field(default_factory=list)
    drafts: list[str] = field(default_factory=list)
    selected_draft: Optional[str] = None
    draft_being_edited: Optional[str] = None
    suggested_image_styles: list[str] = field(default_factory=list)
    selected_image_styles: list[str] = field(default_factory=list)
    image_bytes_list: list[bytes] = field(default_factory=list)
    image_prompts_used: list[str] = field(default_factory=list)
    selected_image_index: Optional[int] = None
    selected_image_bytes: Optional[bytes] = None
    feedback_text: Optional[str] = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    @staticmethod
    def _key(channel_id: str, thread_ts: str) -> str:
        return f"{channel_id}:{thread_ts}"

    def create(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        original_message: str,
    ) -> Session:
        key = self._key(channel_id, thread_ts)
        session = Session(
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
            original_message=original_message,
        )
        self._sessions[key] = session
        return session

    def get(self, channel_id: str, thread_ts: str) -> Optional[Session]:
        return self._sessions.get(self._key(channel_id, thread_ts))

    def get_by_thread(self, thread_ts: str) -> Optional[Session]:
        """Look up a session by thread_ts alone (for thread replies)."""
        for key, session in self._sessions.items():
            if session.thread_ts == thread_ts:
                return session
        return None

    def delete(self, channel_id: str, thread_ts: str) -> None:
        self._sessions.pop(self._key(channel_id, thread_ts), None)


store = SessionStore()
