"""Tests for state/session_store.py."""

from state.session_store import SessionPhase, SessionStore


class TestSessionStore:
    def test_create_and_get(self, session_store):
        session = session_store.create("C1", "ts1", "U1", "hello")
        retrieved = session_store.get("C1", "ts1")
        assert retrieved is session
        assert retrieved.original_message == "hello"

    def test_get_missing(self, session_store):
        assert session_store.get("C_NOPE", "ts_nope") is None

    def test_get_by_thread(self, session_store):
        session_store.create("C1", "ts_abc", "U1", "msg")
        found = session_store.get_by_thread("ts_abc")
        assert found is not None
        assert found.thread_ts == "ts_abc"

    def test_get_by_thread_missing(self, session_store):
        assert session_store.get_by_thread("no_such_ts") is None

    def test_delete(self, session_store):
        session_store.create("C1", "ts1", "U1", "msg")
        session_store.delete("C1", "ts1")
        assert session_store.get("C1", "ts1") is None

    def test_delete_nonexistent(self, session_store):
        # Should not raise
        session_store.delete("C_NOPE", "ts_nope")

    def test_default_phase(self, session_store):
        session = session_store.create("C1", "ts1", "U1", "msg")
        assert session.phase == SessionPhase.AWAITING_LENGTH_PICK

    def test_multiple_sessions(self, session_store):
        s1 = session_store.create("C1", "ts1", "U1", "msg1")
        s2 = session_store.create("C1", "ts2", "U2", "msg2")
        assert s1 is not s2
        assert session_store.get("C1", "ts1").original_message == "msg1"
        assert session_store.get("C1", "ts2").original_message == "msg2"
