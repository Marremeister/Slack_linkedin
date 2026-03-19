"""Shared fixtures for the test suite.

Environment variables are set BEFORE any app code is imported so that
``config.py`` does not call ``sys.exit(1)``.
"""

from __future__ import annotations

import os
import re
import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# 1. Seed required env vars so ``config.py`` passes validation on import.
# ---------------------------------------------------------------------------
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
os.environ.setdefault("SLACK_APP_TOKEN", "xapp-test-token")
os.environ.setdefault("TARGET_CHANNEL_ID", "C_TEST_CHANNEL")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("LINKEDIN_ACCESS_TOKEN", "")
os.environ.setdefault("LINKEDIN_PERSON_URN", "")

# ---------------------------------------------------------------------------
# 2. Stub out the google.genai Client that gemini_service creates at import
#    time, so we never hit the real API.
# ---------------------------------------------------------------------------
_genai_mock = MagicMock()
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.genai", _genai_mock)
sys.modules.setdefault("google.genai.types", MagicMock())
# Make `from google import genai` return our mock
sys.modules["google"].genai = _genai_mock
# Make `genai.Client(...)` return a mock client
_genai_mock.Client.return_value = MagicMock()

# Now it is safe to import app modules.
from state.session_store import Session, SessionPhase, SessionStore  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def session_store():
    """Return a fresh, empty ``SessionStore``."""
    return SessionStore()


@pytest.fixture()
def sample_session(session_store):
    """Create and return a pre-built ``Session`` in AWAITING_LENGTH_PICK."""
    return session_store.create(
        channel_id="C_TEST_CHANNEL",
        thread_ts="1234567890.000001",
        user_id="U_TEST_USER",
        original_message="This is a test message for LinkedIn",
    )


# ---------------------------------------------------------------------------
# FakeApp — lightweight stand-in for slack_bolt.App
# ---------------------------------------------------------------------------

class FakeApp:
    """Captures handler registrations so tests can invoke them directly.

    Usage::

        app = FakeApp()
        some_handler_module.register(app)

        handler = app.get_action_handler("confirm_length")
        handler(ack=MagicMock(), body={...}, say=MagicMock())
    """

    def __init__(self):
        self._action_handlers: dict[str, callable] = {}
        self._action_pattern_handlers: list[tuple[re.Pattern, callable]] = []
        self._event_handlers: dict[str, callable] = {}
        self._view_handlers: dict[str, callable] = {}

    # --- registration decorators ---

    def action(self, action_id):
        def decorator(fn):
            if isinstance(action_id, re.Pattern):
                self._action_pattern_handlers.append((action_id, fn))
            else:
                self._action_handlers[action_id] = fn
            return fn
        return decorator

    def event(self, event_type):
        def decorator(fn):
            self._event_handlers[event_type] = fn
            return fn
        return decorator

    def view(self, callback_id):
        def decorator(fn):
            self._view_handlers[callback_id] = fn
            return fn
        return decorator

    # --- lookup helpers ---

    def get_action_handler(self, action_id: str):
        if action_id in self._action_handlers:
            return self._action_handlers[action_id]
        for pattern, handler in self._action_pattern_handlers:
            if pattern.match(action_id):
                return handler
        raise KeyError(f"No handler for action_id={action_id!r}")

    def get_event_handler(self, event_type: str):
        return self._event_handlers[event_type]

    def get_view_handler(self, callback_id: str):
        return self._view_handlers[callback_id]


@pytest.fixture()
def fake_app():
    """Return a fresh ``FakeApp`` instance."""
    return FakeApp()
