"""
Session-based Tools for MCP Server.

This module provides session-aware tools:
- chatMemory: Read/write conversation history
- getSessionInfo: Get session metadata
- updateMemory: Append messages to history
- clearSession: Logout and clear session

Based on the workflow:
┌─────────────────────────────────────────┐
│ MCP TOOL LAYER                          │
│ /tools/chatMemory - Uses session memory │
│ /tools/getSessionInfo - Reads session   │
└─────────────────────────────────────────┘
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from auth.session_store import get_session_store, SessionStore
from auth.auth_middleware import (
    validate_jwt,
    encrypt_token,
    AuthMiddlewareError
)

async def get_session_info_impl(session_id: str = None, bearer_token: str = None) -> dict:
    """
    Get session information and metadata.
    
    This tool retrieves comprehensive session data including
    user info, session status, and conversation count.
    
    Args:
        session_id: The session ID to look up (optional if bearer_token provided).
        bearer_token: The bearer token to identify session (optional if session_id provided).
        
    Returns:
        dict containing:
        - success: True/False
        - session_id: The session ID
        - user_id: The user's ID
        - email: The user's email
        - name: The user's display name
        - created_at: Session creation timestamp
        - last_activity: Last activity timestamp
        - expires_at: Session expiration timestamp
        - status: Session status (active/idle/expired)
        - conversation_count: Number of messages in history
        - error: Error message if failed
    """
    session_store = get_session_store()
    
    try:
        session = None
        
        # Try to get session by ID first
        if session_id:
            session = await session_store.get_session(session_id)
        
        # If no session_id or session not found, try bearer_token
        if not session and bearer_token:
            try:
                # Clean bearer token if it has the prefix
                token = bearer_token
                if bearer_token.lower().startswith("bearer "):
                    token = bearer_token[7:]
                
                claims = validate_jwt(token)
                user_id = claims.get("sub")
                
                if user_id:
                    session = await session_store.get_session_by_user_id(user_id)
            except AuthMiddlewareError:
                pass  # Token validation failed, will return error below
        
        if not session:
            return {
                "success": False,
                "error": "Session not found. Please authenticate first.",
                "instruction": "Call 'authenticate_user' tool to create a session."
            }
        
        # Get session info
        session_info = await session_store.get_session_info(session["session_id"])
        
        if not session_info:
            return {
                "success": False,
                "error": "Failed to retrieve session info"
            }
        
        session_data = session_info["session"]
        
        return {
            "success": True,
            "session_id": session_data.get("session_id"),
            "user_id": session_data.get("user_id"),
            "email": session_data.get("email"),
            "name": session_data.get("name"),
            "created_at": session_data.get("created_at"),
            "last_activity": session_data.get("last_activity"),
            "expires_at": session_data.get("expires_at"),
            "status": session_data.get("status"),
            "conversation_count": session_info["conversation_count"],
            "cache_summary": session_info["cache_summary"],
            "metadata": session_data.get("metadata", {})
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def chat_memory_impl(
    session_id: str = None,
    bearer_token: str = None,
    action: str = "read",
    limit: int = 10,
    message: dict = None
) -> dict:
    """
    Read or write conversation memory for a session.
    
    This tool provides access to the conversation history stored in the session.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        action: "read" to retrieve messages, "append" to add a message.
        limit: Maximum number of messages to return (for read action).
        message: Message to append (for append action).
                 Format: {"role": "user|assistant", "content": "message text"}
        
    Returns:
        dict containing:
        - success: True/False
        - messages: List of messages (for read action)
        - message_id: ID of added message (for append action)
        - stored: True if message was stored (for append action)
        - error: Error message if failed
    """
    session_store = get_session_store()
    
    try:
        # Find session
        session = None
        
        if session_id:
            session = await session_store.get_session(session_id)
        
        if not session and bearer_token:
            try:
                token = bearer_token
                if bearer_token.lower().startswith("bearer "):
                    token = bearer_token[7:]
                
                claims = validate_jwt(token)
                user_id = claims.get("sub")
                
                if user_id:
                    session = await session_store.get_session_by_user_id(user_id)
            except AuthMiddlewareError:
                pass
        
        if not session:
            return {
                "success": False,
                "error": "Session not found. Please authenticate first.",
                "instruction": "Call 'authenticate_user' tool to create a session."
            }
        
        sid = session["session_id"]
        
        # Handle action
        if action == "read":
            messages = await session_store.get_conversation(sid, limit=limit)
            return {
                "success": True,
                "session_id": sid,
                "action": "read",
                "messages": messages,
                "count": len(messages),
                "limit": limit
            }
        
        elif action == "append":
            if not message:
                return {
                    "success": False,
                    "error": "No message provided for append action",
                    "instruction": "Provide message with 'role' and 'content' fields"
                }
            
            role = message.get("role")
            content = message.get("content")
            
            if not role or not content:
                return {
                    "success": False,
                    "error": "Message must have 'role' and 'content' fields"
                }
            
            tools_used = message.get("tools_used", [])
            metadata = message.get("metadata", {})
            
            result = await session_store.add_message(
                sid,
                role=role,
                content=content,
                tools_used=tools_used,
                metadata=metadata
            )
            
            if result:
                return {
                    "success": True,
                    "session_id": sid,
                    "action": "append",
                    "message_id": result["message_id"],
                    "stored": True,
                    "timestamp": result["timestamp"]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to store message"
                }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["read", "append"]
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def update_memory_impl(
    session_id: str = None,
    bearer_token: str = None,
    role: str = "assistant",
    content: str = "",
    tools_used: List[str] = None,
    metadata: dict = None
) -> dict:
    """
    Append a new message to the conversation history.
    
    This is a convenience wrapper around chat_memory with action='append'.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        role: The message role (user, assistant).
        content: The message content.
        tools_used: List of tools used.
        metadata: Additional metadata.
        
    Returns:
        dict containing:
        - success: True/False
        - message_id: ID of the added message
        - stored: True if successful
        - cache_updated: True if cache was updated
        - error: Error message if failed
    """
    result = await chat_memory_impl(
        session_id=session_id,
        bearer_token=bearer_token,
        action="append",
        message={
            "role": role,
            "content": content,
            "tools_used": tools_used or [],
            "metadata": metadata or {}
        }
    )
    
    if result.get("success"):
        result["cache_updated"] = True
    
    return result


async def clear_session_impl(
    session_id: str = None,
    bearer_token: str = None,
    clear_conversation_only: bool = False
) -> dict:
    """
    Clear session or logout completely.
    
    This tool can either:
    - Clear conversation history only (keep session active)
    - Full logout (invalidate session, clear all data)
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        clear_conversation_only: If True, only clear conversation, keep session.
        
    Returns:
        dict containing:
        - success: True/False
        - action: "clear_conversation" or "logout"
        - session_invalidated: True if session was invalidated
        - conversation_cleared: True if conversation was cleared
        - error: Error message if failed
    """
    session_store = get_session_store()
    
    try:
        # Find session
        session = None
        
        if session_id:
            session = await session_store.get_session(session_id)
        
        if not session and bearer_token:
            try:
                token = bearer_token
                if bearer_token.lower().startswith("bearer "):
                    token = bearer_token[7:]
                
                claims = validate_jwt(token)
                user_id = claims.get("sub")
                
                if user_id:
                    session = await session_store.get_session_by_user_id(user_id)
            except AuthMiddlewareError:
                pass
        
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "instruction": "No active session to clear"
            }
        
        sid = session["session_id"]
        
        if clear_conversation_only:
            # Just clear the conversation
            await session_store.clear_conversation(sid)
            return {
                "success": True,
                "action": "clear_conversation",
                "session_id": sid,
                "session_invalidated": False,
                "conversation_cleared": True,
                "message": "Conversation history cleared. Session still active."
            }
        else:
            # Full logout - invalidate session
            await session_store.invalidate_session(sid)
            return {
                "success": True,
                "action": "logout",
                "session_id": sid,
                "session_invalidated": True,
                "conversation_cleared": True,
                "message": "Session invalidated. User logged out."
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def update_session_state_impl(
    session_id: str = None,
    bearer_token: str = None,
    state: dict = None
) -> dict:
    """
    Update the state stored in the session cache.
    
    This is useful for storing workflow state, user context, or
    any data that should persist across tool calls.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        state: The state data to store.
        
    Returns:
        dict containing:
        - success: True/False
        - state_updated: True if state was updated
        - error: Error message if failed
    """
    session_store = get_session_store()
    
    try:
        # Find session
        session = None
        
        if session_id:
            session = await session_store.get_session(session_id)
        
        if not session and bearer_token:
            try:
                token = bearer_token
                if bearer_token.lower().startswith("bearer "):
                    token = bearer_token[7:]
                
                claims = validate_jwt(token)
                user_id = claims.get("sub")
                
                if user_id:
                    session = await session_store.get_session_by_user_id(user_id)
            except AuthMiddlewareError:
                pass
        
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "instruction": "Call 'authenticate_user' tool to create a session."
            }
        
        sid = session["session_id"]
        
        if state is None:
            state = {}
        
        success = await session_store.update_state(sid, state)
        
        if success:
            return {
                "success": True,
                "session_id": sid,
                "state_updated": True,
                "state_keys": list(state.keys())
            }
        else:
            return {
                "success": False,
                "error": "Failed to update state"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_session_state_impl(
    session_id: str = None,
    bearer_token: str = None
) -> dict:
    """
    Get the current state stored in the session cache.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        
    Returns:
        dict containing:
        - success: True/False
        - state: The stored state data
        - error: Error message if failed
    """
    session_store = get_session_store()
    
    try:
        # Find session
        session = None
        
        if session_id:
            session = await session_store.get_session(session_id)
        
        if not session and bearer_token:
            try:
                token = bearer_token
                if bearer_token.lower().startswith("bearer "):
                    token = bearer_token[7:]
                
                claims = validate_jwt(token)
                user_id = claims.get("sub")
                
                if user_id:
                    session = await session_store.get_session_by_user_id(user_id)
            except AuthMiddlewareError:
                pass
        
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "instruction": "Call 'authenticate_user' tool to create a session."
            }
        
        sid = session["session_id"]
        state = await session_store.get_state(sid)
        
        return {
            "success": True,
            "session_id": sid,
            "state": state or {}
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def validate_token_impl(bearer_token: str) -> dict:
    """
    Validate a bearer token and return its claims.
    
    This tool validates the JWT using Okta JWKS and returns
    the decoded claims if valid.
    
    Args:
        bearer_token: The bearer token to validate.
        
    Returns:
        dict containing:
        - valid: True/False
        - user_id: The user's sub claim
        - email: The user's email
        - name: The user's name
        - expires_in: Seconds until token expiry
        - claims: All decoded claims (if valid)
        - error: Error message (if invalid)
    """
    try:
        token = bearer_token
        if bearer_token.lower().startswith("bearer "):
            token = bearer_token[7:]
        
        claims = validate_jwt(token)
        
        import time
        exp = claims.get("exp", 0)
        expires_in = exp - time.time() if exp else None
        
        return {
            "valid": True,
            "user_id": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "expires_in": int(expires_in) if expires_in else None,
            "claims": claims
        }
        
    except AuthMiddlewareError as e:
        return {
            "valid": False,
            "error": e.message,
            "status_code": e.status_code
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


async def create_session_from_token_impl(bearer_token: str) -> dict:
    """
    Create a session from a valid bearer token.
    
    This is useful when the client already has a token (e.g., from OAuth flow)
    and wants to create a session in the MCP server.
    
    Args:
        bearer_token: The bearer token from OAuth.
        
    Returns:
        dict containing:
        - success: True/False
        - session_id: The created session ID
        - user_id: The user's ID
        - email: The user's email
        - error: Error message if failed
    """
    try:
        token = bearer_token
        if bearer_token.lower().startswith("bearer "):
            token = bearer_token[7:]
        
        # Validate token
        claims = validate_jwt(token)
        
        user_id = claims.get("sub")
        email = claims.get("email")
        name = claims.get("name")
        
        if not user_id:
            return {
                "success": False,
                "error": "No 'sub' claim in token"
            }
        
        # Encrypt token for storage
        encrypted_token = encrypt_token(token)
        
        # Create session
        session_store = get_session_store()
        session = await session_store.create_session(
            user_id=user_id,
            bearer_token=encrypted_token,
            email=email,
            name=name,
            metadata={"token_claims": claims}
        )
        
        return {
            "success": True,
            "session_id": session["session_id"],
            "user_id": user_id,
            "email": email,
            "name": name,
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "status": session["status"]
        }
        
    except AuthMiddlewareError as e:
        return {
            "success": False,
            "error": e.message,
            "status_code": e.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
