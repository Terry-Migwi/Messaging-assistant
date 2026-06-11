# langchain/session_manager.py

import time
import logging
from langchain_community.chat_message_histories import ChatMessageHistory

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages per-user conversation sessions for the WhatsApp chatbot.

    Each session is keyed by phone number and stores:
      - chat_history: a ChatMessageHistory object (the actual messages)
      - last_active: Unix timestamp of the last message

    Sessions expire after `ttl_seconds` of inactivity (default: 30 minutes).
    On next message, an expired session is silently replaced with a fresh one.
    """

    def __init__(self, ttl_seconds: int = 1800):
        self.ttl_seconds = ttl_seconds
        # { phone_number: {"history": ChatMessageHistory, "last_active": float} }
        self._sessions: dict = {}

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        """
        Called by LangChain's RunnableWithMessageHistory on every chain invoke.

        If the session is fresh → return existing history (conversation continues).
        If the session is expired or new → return a blank history (fresh start).
        """
        now = time.time()

        if session_id in self._sessions:
            session = self._sessions[session_id]
            age = now - session["last_active"]

            if age > self.ttl_seconds:
                # Session expired — log it and start fresh
                msg_count = len(session["history"].messages)
                logger.info(
                    f"Session expired for {session_id} "
                    f"(idle {age/60:.1f} min, had {msg_count} messages)"
                )
                self._sessions.pop(session_id)
            else:
                # Active session — update timestamp and return history
                self._sessions[session_id]["last_active"] = now
                return self._sessions[session_id]["history"]

        # New or just-expired session — create a blank one
        logger.info(f"New session started for {session_id}")
        self._sessions[session_id] = {
            "history": ChatMessageHistory(),
            "last_active": now,
        }
        return self._sessions[session_id]["history"]

    # ── Utility methods ──────────────────────────────────────────────────────

    def list_active_sessions(self) -> list[dict]:
        """
        Returns a summary of all active (non-expired) sessions.
        Useful for debugging and monitoring.
        """
        now = time.time()
        active = []
        for session_id, data in self._sessions.items():
            age = now - data["last_active"]
            if age <= self.ttl_seconds:
                active.append({
                    "session_id": session_id,
                    "message_count": len(data["history"].messages),
                    "idle_minutes": round(age / 60, 1),
                })
        return active

    def clear_session(self, session_id: str) -> bool:
        """
        Manually clear a session (useful for testing or admin resets).
        Returns True if the session existed and was cleared.
        """
        if session_id in self._sessions:
            self._sessions.pop(session_id)
            logger.info(f"Session manually cleared for {session_id}")
            return True
        return False

    def session_count(self) -> int:
        """Returns number of sessions currently in memory (including expired)."""
        return len(self._sessions)