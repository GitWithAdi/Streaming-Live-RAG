"""
Ephemeral in-memory session manager.
Enforces session-bound state isolation per Samsung PRISM rules (no persistent cross-session profiling).
"""

from typing import Dict, Optional
from streaming_rag.schemas import SessionAnswerState


class EphemeralSessionStore:
    """Manages conversational session states strictly in volatile memory."""

    def __init__(self):
        self._sessions: Dict[str, SessionAnswerState] = {}

    def get_session(self, session_id: str) -> Optional[SessionAnswerState]:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str, base_query: str = "") -> SessionAnswerState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionAnswerState(
                session_id=session_id,
                version=1,
                base_query=base_query,
                active_constraints=[],
                claims=[],
                citations=[],
                raw_answer="",
                cached_evidence=[]
            )
        return self._sessions[session_id]

    def update_session(self, session_id: str, new_state: SessionAnswerState):
        self._sessions[session_id] = new_state

    def reset_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_all(self):
        self._sessions.clear()
