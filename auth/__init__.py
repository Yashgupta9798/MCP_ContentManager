"""
Auth Package for MCP Server.

This package provides authentication and session management:
- auth_middleware: JWT validation using Okta JWKS
- session_store: Session storage with conversation and cache management

Usage:
    from auth import get_auth_middleware, get_session_store, AuthMiddleware, SessionStore
"""

from auth.auth_middleware import (
    AuthMiddleware,
    AuthMiddlewareError,
    get_auth_middleware,
    validate_jwt,
    extract_bearer_token,
    extract_user_id,
    check_token_expiry,
    fetch_jwks,
    encrypt_token,
    decrypt_token
)

from auth.session_store import (
    SessionStore,
    get_session_store,
    SESSION_TIMEOUT_MINUTES,
    IDLE_TIMEOUT_MINUTES,
    MAX_CONVERSATION_MESSAGES
)

__all__ = [
    # Middleware
    "AuthMiddleware",
    "AuthMiddlewareError",
    "get_auth_middleware",
    "validate_jwt",
    "extract_bearer_token",
    "extract_user_id",
    "check_token_expiry",
    "fetch_jwks",
    "encrypt_token",
    "decrypt_token",
    
    # Session Store
    "SessionStore",
    "get_session_store",
    "SESSION_TIMEOUT_MINUTES",
    "IDLE_TIMEOUT_MINUTES",
    "MAX_CONVERSATION_MESSAGES",
]
