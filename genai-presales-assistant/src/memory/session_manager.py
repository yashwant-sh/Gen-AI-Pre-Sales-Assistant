"""
Session & Memory Manager for GenAI Pre-Sales Assistant

Provides:
 - Per-session conversation memory (last N turns sent as LLM context)
 - Query result cache with TTL (avoids redundant DB hits / LLM calls)
"""

import time
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ConversationTurn:
    role: str          # "user" or "assistant"
    content: str       # the message text
    query_type: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConversationMemory:
    """Stores conversation history for a single session."""
    session_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    max_turns: int = 20

    def add_user_message(self, content: str):
        self._add("user", content)

    def add_assistant_message(self, content: str, query_type: str = ""):
        self._add("assistant", content, query_type)

    def _add(self, role: str, content: str, query_type: str = ""):
        self.turns.append(ConversationTurn(role=role, content=content, query_type=query_type))
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        self.last_active = time.time()

    def get_context_for_llm(self, last_n: int = 6) -> List[Dict[str, str]]:
        """Return the last N turns formatted for the LLM messages array."""
        recent = self.turns[-last_n:] if len(self.turns) > last_n else self.turns
        return [{"role": t.role, "content": t.content} for t in recent]

    def get_last_result_summary(self) -> Optional[str]:
        """Get the last assistant response — useful for follow-up questions."""
        for turn in reversed(self.turns):
            if turn.role == "assistant" and turn.content:
                return turn.content
        return None


@dataclass
class CacheEntry:
    result: Any
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """Manages conversation sessions and query caching."""

    def __init__(self, session_ttl: int = 3600, cache_ttl: int = 300):
        self._sessions: Dict[str, ConversationMemory] = {}
        self._cache: Dict[str, CacheEntry] = {}
        self.session_ttl = session_ttl   # 1 hour default
        self.cache_ttl = cache_ttl       # 5 minutes default
        logger.info(f"SessionManager initialized (session_ttl={session_ttl}s, cache_ttl={cache_ttl}s)")

    # ── Session management ──────────────────────────────────────

    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationMemory:
        self._cleanup_expired_sessions()
        if session_id and session_id in self._sessions:
            mem = self._sessions[session_id]
            mem.last_active = time.time()
            return mem
        new_id = session_id or str(uuid.uuid4())
        mem = ConversationMemory(session_id=new_id)
        self._sessions[new_id] = mem
        logger.info(f"Created new session: {new_id}")
        return mem

    def _cleanup_expired_sessions(self):
        now = time.time()
        expired = [sid for sid, mem in self._sessions.items()
                   if now - mem.last_active > self.session_ttl]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    # ── Query result cache ──────────────────────────────────────

    @staticmethod
    def _cache_key(query: str) -> str:
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get_cached_result(self, query: str) -> Optional[Any]:
        key = self._cache_key(query)
        entry = self._cache.get(key)
        if entry and (time.time() - entry.created_at) < self.cache_ttl:
            logger.info(f"Cache HIT for query: {query[:60]}...")
            return entry.result
        if entry:
            del self._cache[key]
        return None

    def set_cached_result(self, query: str, result: Any):
        key = self._cache_key(query)
        self._cache[key] = CacheEntry(result=result)

    def clear_cache(self):
        self._cache.clear()

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "cached_queries": len(self._cache),
            "session_ttl_seconds": self.session_ttl,
            "cache_ttl_seconds": self.cache_ttl,
        }
