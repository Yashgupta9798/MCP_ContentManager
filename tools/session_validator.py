"""
Session Validator Helper for MCP Tools.

This module provides session validation that can be used by all tools
that require authentication before execution.

Usage:
    from tools.session_validator import validate_session_for_tool
    
    async def my_tool_impl(action_plan, session_id=None, bearer_token=None):
        # Validate session first
        validation = await validate_session_for_tool(session_id, bearer_token)
        if not validation["valid"]:
            return validation  # Return error response
        
        # Session is valid, proceed with tool logic
        session = validation["session"]
        user_email = session.get("email")
        ...
"""

from typing import Optional
from auth.session_store import get_session_store
from auth.auth_middleware import validate_jwt, AuthMiddlewareError


async def validate_session_for_tool(
    session_id: str = None,
    bearer_token: str = None,
    require_active: bool = True
) -> dict:
    """
    Validate session before intent detection for every subsequent query.
    
    This function checks that a valid, active session exists for the user.
    It can validate using either session_id or bearer_token.
    
    Args:
        session_id: The session ID from authenticate_user (preferred).
        bearer_token: The bearer token for validation (alternative).
        require_active: If True, session must have status="active".
        
    Returns:
        dict containing:
        - valid: True/False
        - session: The session data (if valid)
        - user_id: The user's ID (if valid)
        - email: The user's email (if valid)
        - error: Error message (if invalid)
        - status_code: HTTP status code for error (401/403)
    """
    session_store = get_session_store()
    session = None
    
    # Try to find session by session_id first (preferred)
    if session_id:
        session = await session_store.get_session(session_id)
        if not session:
            return {
                "valid": False,
                "error": f"Session not found: {session_id}",
                "status_code": 401,
                "instruction": "Session expired or invalid. Call 'authenticate_user' to re-authenticate."
            }
    
    # If no session_id provided, try bearer_token
    if not session and bearer_token:
        try:
            # Clean bearer token if it has the prefix
            token = bearer_token
            if bearer_token.lower().startswith("bearer "):
                token = bearer_token[7:]
            
            # Validate the JWT
            claims = validate_jwt(token)
            user_id = claims.get("sub")
            
            if user_id:
                # Look up session by user_id
                session = await session_store.get_session_by_user_id(user_id)
                
                if not session:
                    return {
                        "valid": False,
                        "error": "No session found for this token. User may need to authenticate.",
                        "status_code": 401,
                        "instruction": "Call 'authenticate_user' to create a session."
                    }
        except AuthMiddlewareError as e:
            return {
                "valid": False,
                "error": f"Token validation failed: {e.message}",
                "status_code": e.status_code,
                "instruction": "Token is invalid or expired. Call 'authenticate_user' to re-authenticate."
            }
    
    # If still no session found
    if not session:
        return {
            "valid": False,
            "error": "No session_id or bearer_token provided",
            "status_code": 401,
            "instruction": "You must provide either session_id or bearer_token for authentication. Call 'authenticate_user' first."
        }
    
    # Check session status if required
    if require_active:
        status = session.get("status")
        if status != "active":
            return {
                "valid": False,
                "error": f"Session is not active (status: {status})",
                "status_code": 403,
                "session_id": session.get("session_id"),
                "instruction": f"Session is {status}. Call 'authenticate_user' to re-authenticate."
            }
    
    # Check session expiry
    from datetime import datetime
    expires_at_str = session.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", ""))
            if expires_at < datetime.utcnow():
                # Mark session as expired
                await session_store.update_session_status(session.get("session_id"), "expired")
                return {
                    "valid": False,
                    "error": "Session has expired",
                    "status_code": 401,
                    "session_id": session.get("session_id"),
                    "instruction": "Session expired. Call 'authenticate_user' to re-authenticate."
                }
        except Exception:
            pass  # If we can't parse expiry, continue
    
    # Update last activity
    await session_store.update_last_activity(session.get("session_id"))
    
    # Session is valid!
    return {
        "valid": True,
        "session": session,
        "session_id": session.get("session_id"),
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "name": session.get("name"),
        "status": session.get("status")
    }
