"""
Session Store for MCP Server.

This module provides session management functionality:
- Session creation and storage
- Conversation history management
- Cache management for user preferences
- Session lifecycle (active, idle, expired)

Based on the workflow:
┌─────────────────────────────────────────┐
│ SESSION STORE                           │
│ key = user_id (JWT sub)                 │
│ data = conversation, cache, state       │
└─────────────────────────────────────────┘

Data Structures:
- session:{session_id} - Session metadata
- conversation:{session_id}:{message_id} - Conversation messages
- cache:{session_id} - User cache/preferences
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

# Session configuration
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "1"))  # Default 1 minute
IDLE_TIMEOUT_MINUTES = int(os.getenv("IDLE_TIMEOUT_MINUTES", "5"))
MAX_CONVERSATION_MESSAGES = int(os.getenv("MAX_CONVERSATION_MESSAGES", "100"))

# Storage directory
SESSION_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth", "sessions")


class SessionStore:
    """
    In-memory session store with file persistence.
    
    For production, consider using Redis or a database.
    This implementation uses file storage for persistence across restarts.
    
    Session data structure:
    {
        "session_id": "uuid",
        "user_id": "user@company.com (JWT sub)",
        "bearer_token": "encrypted-jwt",
        "created_at": "ISO timestamp",
        "last_activity": "ISO timestamp",
        "expires_at": "ISO timestamp",
        "status": "active|idle|expired"
    }
    
    Conversation data structure:
    {
        "message_id": "uuid",
        "session_id": "session-uuid",
        "role": "user|assistant",
        "content": "message text",
        "timestamp": "ISO timestamp",
        "tools_used": ["tool1", "tool2"],
        "metadata": {}
    }
    
    Cache data structure:
    {
        "session_id": "uuid",
        "last_messages": [...],
        "conversation_summary": "...",
        "user_preferences": {...},
        "state": {...}
    }
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize the session store.
        
        Args:
            storage_dir: Directory for file persistence. Defaults to auth/sessions.
        """
        self.storage_dir = storage_dir or SESSION_STORE_DIR
        
        # In-memory caches
        self._sessions: Dict[str, dict] = {}  # session_id -> session data
        self._user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self._conversations: Dict[str, List[dict]] = {}  # session_id -> messages
        self._caches: Dict[str, dict] = {}  # session_id -> cache data
        
        # Ensure storage directory exists
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        
        # Load existing sessions from disk
        self._load_sessions()
    
    def _get_session_file(self, session_id: str) -> str:
        """Get the file path for a session."""
        return os.path.join(self.storage_dir, f"session_{session_id}.json")
    
    def _get_conversation_file(self, session_id: str) -> str:
        """Get the file path for a session's conversation."""
        return os.path.join(self.storage_dir, f"conversation_{session_id}.json")
    
    def _get_cache_file(self, session_id: str) -> str:
        """Get the file path for a session's cache."""
        return os.path.join(self.storage_dir, f"cache_{session_id}.json")
    
    def _load_sessions(self):
        """Load all sessions from disk on startup."""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.startswith("session_") and filename.endswith(".json"):
                    filepath = os.path.join(self.storage_dir, filename)
                    try:
                        with open(filepath, "r") as f:
                            session = json.load(f)
                            session_id = session.get("session_id")
                            user_id = session.get("user_id")
                            
                            if session_id:
                                self._sessions[session_id] = session
                                if user_id:
                                    self._user_sessions[user_id] = session_id
                                
                                # Load conversation
                                conv_file = self._get_conversation_file(session_id)
                                if os.path.exists(conv_file):
                                    with open(conv_file, "r") as cf:
                                        self._conversations[session_id] = json.load(cf)
                                
                                # Load cache
                                cache_file = self._get_cache_file(session_id)
                                if os.path.exists(cache_file):
                                    with open(cache_file, "r") as cf:
                                        self._caches[session_id] = json.load(cf)
                    except Exception as e:
                        print(f"[SESSION_STORE] Error loading session {filename}: {e}")
        except FileNotFoundError:
            pass
    
    def _save_session(self, session_id: str):
        """Save a session to disk."""
        session = self._sessions.get(session_id)
        if session:
            filepath = self._get_session_file(session_id)
            with open(filepath, "w") as f:
                json.dump(session, f, indent=2, default=str)
    
    def _save_conversation(self, session_id: str):
        """Save a session's conversation to disk."""
        conversation = self._conversations.get(session_id, [])
        filepath = self._get_conversation_file(session_id)
        with open(filepath, "w") as f:
            json.dump(conversation, f, indent=2, default=str)
    
    def _save_cache(self, session_id: str):
        """Save a session's cache to disk."""
        cache = self._caches.get(session_id, {})
        filepath = self._get_cache_file(session_id)
        with open(filepath, "w") as f:
            json.dump(cache, f, indent=2, default=str)
    
    async def create_session(
        self,
        user_id: str,
        bearer_token: str = None,
        email: str = None,
        name: str = None,
        metadata: dict = None
    ) -> dict:
        """
        Create a new session for a user.
        
        If a session already exists for the user, it will be invalidated first.
        
        Args:
            user_id: The user's ID (JWT sub claim).
            bearer_token: The encrypted bearer token.
            email: The user's email address.
            name: The user's display name.
            metadata: Additional metadata to store.
            
        Returns:
            The created session data.
        """
        # Invalidate any existing session for this user
        existing_session_id = self._user_sessions.get(user_id)
        if existing_session_id:
            await self.invalidate_session(existing_session_id)
        
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "email": email,
            "name": name,
            "bearer_token": bearer_token,
            "created_at": now.isoformat() + "Z",
            "last_activity": now.isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "status": "active",
            "metadata": metadata or {}
        }
        
        # Store in memory
        self._sessions[session_id] = session
        self._user_sessions[user_id] = session_id
        self._conversations[session_id] = []
        self._caches[session_id] = {
            "session_id": session_id,
            "last_messages": [],
            "conversation_summary": "",
            "user_preferences": {},
            "state": {}
        }
        
        # Persist to disk
        self._save_session(session_id)
        self._save_conversation(session_id)
        self._save_cache(session_id)
        
        print(f"[SESSION_STORE] Created session {session_id} for user {user_id}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get a session by its ID.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The session data or None if not found.
        """
        return self._sessions.get(session_id)
    
    async def get_session_by_user_id(self, user_id: str) -> Optional[dict]:
        """
        Get a session by user ID.
        
        Args:
            user_id: The user's ID (JWT sub).
            
        Returns:
            The session data or None if not found.
        """
        session_id = self._user_sessions.get(user_id)
        if session_id:
            return self._sessions.get(session_id)
        return None
    
    async def update_last_activity(self, session_id: str) -> bool:
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            True if updated, False if session not found.
        """
        session = self._sessions.get(session_id)
        if session:
            session["last_activity"] = datetime.utcnow().isoformat() + "Z"
            self._save_session(session_id)
            return True
        return False
    
    async def update_session_status(self, session_id: str, status: str) -> bool:
        """
        Update the status of a session.
        
        Args:
            session_id: The session ID.
            status: The new status (active, idle, expired).
            
        Returns:
            True if updated, False if session not found.
        """
        session = self._sessions.get(session_id)
        if session:
            session["status"] = status
            self._save_session(session_id)
            return True
        return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate and remove a session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            True if invalidated, False if session not found.
        """
        session = self._sessions.get(session_id)
        if session:
            user_id = session.get("user_id")
            
            # Update status before removal
            session["status"] = "expired"
            self._save_session(session_id)
            
            # Remove from memory
            del self._sessions[session_id]
            if user_id and self._user_sessions.get(user_id) == session_id:
                del self._user_sessions[user_id]
            
            # Remove conversation and cache
            if session_id in self._conversations:
                del self._conversations[session_id]
            if session_id in self._caches:
                del self._caches[session_id]
            
            print(f"[SESSION_STORE] Invalidated session {session_id}")
            return True
        return False
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tools_used: List[str] = None,
        metadata: dict = None
    ) -> Optional[dict]:
        """
        Add a message to a session's conversation history.
        
        Args:
            session_id: The session ID.
            role: The message role (user, assistant).
            content: The message content.
            tools_used: List of tools used in this message.
            metadata: Additional metadata.
            
        Returns:
            The created message or None if session not found.
        """
        if session_id not in self._conversations:
            return None
        
        message_id = str(uuid.uuid4())
        message = {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tools_used": tools_used or [],
            "metadata": metadata or {}
        }
        
        # Add to conversation
        self._conversations[session_id].append(message)
        
        # Trim if too many messages
        if len(self._conversations[session_id]) > MAX_CONVERSATION_MESSAGES:
            self._conversations[session_id] = self._conversations[session_id][-MAX_CONVERSATION_MESSAGES:]
        
        # Update cache with last messages
        cache = self._caches.get(session_id, {})
        cache["last_messages"] = self._conversations[session_id][-10:]  # Keep last 10 in cache
        self._caches[session_id] = cache
        
        # Update last activity
        await self.update_last_activity(session_id)
        
        # Persist
        self._save_conversation(session_id)
        self._save_cache(session_id)
        
        return message
    
    async def get_conversation(
        self,
        session_id: str,
        limit: int = None,
        offset: int = 0
    ) -> List[dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: The session ID.
            limit: Maximum number of messages to return.
            offset: Number of messages to skip from the end.
            
        Returns:
            List of messages.
        """
        conversation = self._conversations.get(session_id, [])
        
        if limit:
            if offset:
                return conversation[-(limit + offset):-offset] if offset < len(conversation) else []
            return conversation[-limit:]
        
        return conversation
    
    async def get_cache(self, session_id: str) -> Optional[dict]:
        """
        Get the cache data for a session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The cache data or None if not found.
        """
        return self._caches.get(session_id)
    
    async def update_cache(self, session_id: str, data: dict) -> bool:
        """
        Update the cache data for a session.
        
        This merges the provided data with existing cache.
        
        Args:
            session_id: The session ID.
            data: The data to merge into the cache.
            
        Returns:
            True if updated, False if session not found.
        """
        if session_id not in self._caches:
            return False
        
        self._caches[session_id].update(data)
        self._save_cache(session_id)
        return True
    
    async def update_state(self, session_id: str, state: dict) -> bool:
        """
        Update the state in the session cache.
        
        Args:
            session_id: The session ID.
            state: The state data to set.
            
        Returns:
            True if updated, False if session not found.
        """
        if session_id not in self._caches:
            return False
        
        self._caches[session_id]["state"] = state
        self._save_cache(session_id)
        return True
    
    async def get_state(self, session_id: str) -> Optional[dict]:
        """
        Get the state from the session cache.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The state data or None if not found.
        """
        cache = self._caches.get(session_id)
        if cache:
            return cache.get("state", {})
        return None
    
    async def update_user_preferences(self, session_id: str, preferences: dict) -> bool:
        """
        Update user preferences in the session cache.
        
        Args:
            session_id: The session ID.
            preferences: The preferences to set.
            
        Returns:
            True if updated, False if session not found.
        """
        if session_id not in self._caches:
            return False
        
        current_prefs = self._caches[session_id].get("user_preferences", {})
        current_prefs.update(preferences)
        self._caches[session_id]["user_preferences"] = current_prefs
        self._save_cache(session_id)
        return True
    
    async def clear_conversation(self, session_id: str) -> bool:
        """
        Clear the conversation history for a session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            True if cleared, False if session not found.
        """
        if session_id not in self._conversations:
            return False
        
        self._conversations[session_id] = []
        
        # Clear cache last_messages too
        if session_id in self._caches:
            self._caches[session_id]["last_messages"] = []
            self._caches[session_id]["conversation_summary"] = ""
        
        self._save_conversation(session_id)
        self._save_cache(session_id)
        
        return True
    
    async def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        Get comprehensive session information.
        
        Args:
            session_id: The session ID.
            
        Returns:
            dict with session info, conversation count, and cache summary.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        conversation = self._conversations.get(session_id, [])
        cache = self._caches.get(session_id, {})
        
        # Don't expose bearer_token
        safe_session = {k: v for k, v in session.items() if k != "bearer_token"}
        
        return {
            "session": safe_session,
            "conversation_count": len(conversation),
            "cache_summary": {
                "has_conversation_summary": bool(cache.get("conversation_summary")),
                "user_preferences": cache.get("user_preferences", {}),
                "state_keys": list(cache.get("state", {}).keys())
            }
        }
    
    async def check_idle_sessions(self) -> List[str]:
        """
        Check for and mark idle sessions.
        
        Sessions with no activity for IDLE_TIMEOUT_MINUTES are marked as idle.
        
        Returns:
            List of session IDs that were marked as idle.
        """
        now = datetime.utcnow()
        idle_threshold = now - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
        marked_idle = []
        
        for session_id, session in list(self._sessions.items()):
            if session.get("status") == "active":
                last_activity_str = session.get("last_activity")
                if last_activity_str:
                    last_activity = datetime.fromisoformat(last_activity_str.replace("Z", ""))
                    if last_activity < idle_threshold:
                        await self.update_session_status(session_id, "idle")
                        marked_idle.append(session_id)
        
        return marked_idle
    
    async def cleanup_expired_sessions(self) -> List[str]:
        """
        Remove expired sessions.
        
        Returns:
            List of session IDs that were removed.
        """
        now = datetime.utcnow()
        removed = []
        
        for session_id, session in list(self._sessions.items()):
            expires_at_str = session.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", ""))
                if expires_at < now:
                    await self.invalidate_session(session_id)
                    removed.append(session_id)
        
        return removed
    
    def get_active_session_count(self) -> int:
        """Get the count of active sessions."""
        return sum(1 for s in self._sessions.values() if s.get("status") == "active")
    
    def get_all_sessions_summary(self) -> List[dict]:
        """Get a summary of all sessions (for admin/debug)."""
        summaries = []
        for session_id, session in self._sessions.items():
            summaries.append({
                "session_id": session_id,
                "user_id": session.get("user_id"),
                "email": session.get("email"),
                "status": session.get("status"),
                "created_at": session.get("created_at"),
                "last_activity": session.get("last_activity")
            })
        return summaries


# Singleton session store instance
_session_store = None


def get_session_store() -> SessionStore:
    """
    Get or create the session store singleton.
    
    Returns:
        The SessionStore instance.
    """
    global _session_store
    
    if _session_store is None:
        _session_store = SessionStore()
    
    return _session_store
