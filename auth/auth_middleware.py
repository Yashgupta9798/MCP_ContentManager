"""
Auth Middleware for MCP Server.

This middleware handles:
1. Reading Authorization header (Bearer token)
2. Validating JWT using Okta JWKS
3. Extracting user 'sub' claim
4. Loading/validating session

Based on the workflow:
┌─────────────────────────────────────────┐
│ AUTH MIDDLEWARE                         │
│ - Reads Authorization header            │
│ - Validates JWT using Okta JWKS         │
│ - Extracts user "sub"                   │
│ - Loads session                         │
└─────────────────────────────────────────┘
"""

import os
import time
import requests
from typing import Optional, Tuple
from jose import jwt, JWTError
from functools import lru_cache
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import hashlib
import base64

# Okta configuration from environment
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN")
CLIENT_ID = os.getenv("CLIENT_ID")
ISSUER = os.getenv("ISSUER")

# JWKS cache settings
_jwks_cache = None
_jwks_cache_time = None
JWKS_CACHE_DURATION = 3600  # 1 hour in seconds


class AuthMiddlewareError(Exception):
    """Custom exception for auth middleware errors."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def _get_encryption_key() -> bytes:
    """
    Get or generate encryption key for token storage.
    Uses a deterministic key based on environment for consistency.
    """
    # Use a secret from environment or generate from domain
    secret = os.getenv("TOKEN_ENCRYPTION_SECRET", OKTA_DOMAIN or "default_secret")
    # Create a 32-byte key for Fernet
    key = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_token(token: str) -> str:
    """
    Encrypt a token for secure storage.
    
    Args:
        token: The plaintext token to encrypt.
        
    Returns:
        The encrypted token as a base64 string.
    """
    try:
        f = Fernet(_get_encryption_key())
        return f.encrypt(token.encode()).decode()
    except Exception as e:
        print(f"[AUTH_MIDDLEWARE] Encryption error: {e}")
        return token  # Fallback to plaintext if encryption fails


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted token.
    
    Args:
        encrypted_token: The encrypted token.
        
    Returns:
        The decrypted plaintext token.
    """
    try:
        f = Fernet(_get_encryption_key())
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        # If decryption fails, assume it's already plaintext
        return encrypted_token


def fetch_jwks(force_refresh: bool = False) -> dict:
    """
    Fetch JWKS (JSON Web Key Set) from Okta with caching.
    
    Args:
        force_refresh: Force refresh the cache.
        
    Returns:
        The JWKS as a dictionary.
        
    Raises:
        AuthMiddlewareError: If JWKS fetch fails.
    """
    global _jwks_cache, _jwks_cache_time
    
    current_time = time.time()
    
    # Check if cache is valid
    if not force_refresh and _jwks_cache and _jwks_cache_time:
        if current_time - _jwks_cache_time < JWKS_CACHE_DURATION:
            return _jwks_cache
    
    # Fetch fresh JWKS
    if not ISSUER:
        raise AuthMiddlewareError("ISSUER not configured", 500)
    
    jwks_url = f"{ISSUER}/oauth2/v1/keys"
    
    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = current_time
        print(f"[AUTH_MIDDLEWARE] JWKS fetched from {jwks_url}")
        return _jwks_cache
    except requests.RequestException as e:
        raise AuthMiddlewareError(f"Failed to fetch JWKS: {str(e)}", 500)


def _find_signing_key(token: str) -> dict:
    """
    Find the signing key for a JWT token from JWKS.
    
    Args:
        token: The JWT token.
        
    Returns:
        The matching JWK.
        
    Raises:
        AuthMiddlewareError: If no matching key is found.
    """
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        if not kid:
            raise AuthMiddlewareError("No 'kid' in token header")
        
        jwks = fetch_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        # Key not found, try refreshing JWKS
        jwks = fetch_jwks(force_refresh=True)
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        raise AuthMiddlewareError(f"No matching key found for kid: {kid}")
        
    except JWTError as e:
        raise AuthMiddlewareError(f"Invalid token header: {str(e)}")


def validate_jwt(token: str) -> dict:
    """
    Validate a JWT token using Okta JWKS.
    
    This function performs full JWT validation:
    1. Verifies signature using Okta's public keys
    2. Validates standard claims (iss, aud, exp)
    3. Returns decoded claims if valid
    
    Args:
        token: The JWT token (without 'Bearer ' prefix).
        
    Returns:
        The decoded JWT claims.
        
    Raises:
        AuthMiddlewareError: If validation fails.
    """
    if not token:
        raise AuthMiddlewareError("No token provided")
    
    # Find the signing key
    key = _find_signing_key(token)
    
    try:
        # Decode and validate token
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER,
            options={
                "verify_at_hash": False,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True
            }
        )
        return claims
        
    except jwt.ExpiredSignatureError:
        raise AuthMiddlewareError("Token has expired")
    except jwt.JWTClaimsError as e:
        raise AuthMiddlewareError(f"Invalid token claims: {str(e)}")
    except JWTError as e:
        raise AuthMiddlewareError(f"Token validation failed: {str(e)}")


def extract_bearer_token(authorization_header: str) -> str:
    """
    Extract bearer token from Authorization header.
    
    Args:
        authorization_header: The full Authorization header value.
        
    Returns:
        The token without 'Bearer ' prefix.
        
    Raises:
        AuthMiddlewareError: If header format is invalid.
    """
    if not authorization_header:
        raise AuthMiddlewareError("Authorization header missing")
    
    parts = authorization_header.split()
    
    if len(parts) != 2:
        raise AuthMiddlewareError("Invalid Authorization header format")
    
    if parts[0].lower() != "bearer":
        raise AuthMiddlewareError("Authorization type must be Bearer")
    
    return parts[1]


def extract_user_id(claims: dict) -> str:
    """
    Extract user ID (sub claim) from JWT claims.
    
    Args:
        claims: The decoded JWT claims.
        
    Returns:
        The user ID (sub claim value).
        
    Raises:
        AuthMiddlewareError: If sub claim is missing.
    """
    user_id = claims.get("sub")
    
    if not user_id:
        raise AuthMiddlewareError("No 'sub' claim in token")
    
    return user_id


def check_token_expiry(claims: dict, buffer_minutes: int = 5) -> Tuple[bool, Optional[int]]:
    """
    Check if token is expired or expiring soon.
    
    Args:
        claims: The decoded JWT claims.
        buffer_minutes: Minutes before expiry to consider "expiring soon".
        
    Returns:
        Tuple of (is_expiring_soon, seconds_until_expiry).
    """
    exp = claims.get("exp")
    
    if not exp:
        return True, None
    
    current_time = time.time()
    seconds_until_expiry = exp - current_time
    
    # Check if expiring within buffer time
    buffer_seconds = buffer_minutes * 60
    is_expiring_soon = seconds_until_expiry < buffer_seconds
    
    return is_expiring_soon, int(seconds_until_expiry)


class AuthMiddleware:
    """
    Auth Middleware class for MCP Server authentication.
    
    This middleware:
    1. Reads Authorization header
    2. Validates JWT using Okta JWKS
    3. Extracts user 'sub' claim
    4. Loads/validates session
    """
    
    def __init__(self, session_store=None):
        """
        Initialize the auth middleware.
        
        Args:
            session_store: Optional SessionStore instance for session management.
        """
        self.session_store = session_store
    
    async def authenticate(self, authorization_header: str = None, bearer_token: str = None) -> dict:
        """
        Authenticate a request using Bearer token.
        
        This is the main entry point for authentication. It validates the token,
        extracts user info, and loads the session.
        
        Args:
            authorization_header: The full Authorization header (e.g., "Bearer xxx").
            bearer_token: Direct token (alternative to header).
            
        Returns:
            dict containing:
            - authenticated: True/False
            - user_id: The user's sub claim
            - email: The user's email (if available)
            - session: The session data (if session_store is configured)
            - token_expires_in: Seconds until token expiry
            - error: Error message (if failed)
        """
        try:
            # Extract token
            if bearer_token:
                token = bearer_token
            elif authorization_header:
                token = extract_bearer_token(authorization_header)
            else:
                raise AuthMiddlewareError("No token provided")
            
            # Validate JWT
            claims = validate_jwt(token)
            
            # Extract user info
            user_id = extract_user_id(claims)
            email = claims.get("email")
            name = claims.get("name")
            
            # Check token expiry
            is_expiring_soon, seconds_until_expiry = check_token_expiry(claims)
            
            result = {
                "authenticated": True,
                "user_id": user_id,
                "email": email,
                "name": name,
                "claims": claims,
                "token_expires_in": seconds_until_expiry,
                "token_expiring_soon": is_expiring_soon
            }
            
            # Load session if session_store is available
            if self.session_store:
                session = await self.session_store.get_session_by_user_id(user_id)
                if session:
                    result["session"] = session
                    result["session_id"] = session.get("session_id")
                    # Update last activity
                    await self.session_store.update_last_activity(session.get("session_id"))
            
            return result
            
        except AuthMiddlewareError as e:
            return {
                "authenticated": False,
                "error": e.message,
                "status_code": e.status_code
            }
        except Exception as e:
            return {
                "authenticated": False,
                "error": str(e),
                "status_code": 500
            }
    
    async def validate_session(self, session_id: str) -> dict:
        """
        Validate a session exists and is active.
        
        Args:
            session_id: The session ID to validate.
            
        Returns:
            dict with validation result.
        """
        if not self.session_store:
            return {
                "valid": False,
                "error": "Session store not configured"
            }
        
        session = await self.session_store.get_session(session_id)
        
        if not session:
            return {
                "valid": False,
                "error": "Session not found"
            }
        
        if session.get("status") != "active":
            return {
                "valid": False,
                "error": f"Session is {session.get('status', 'unknown')}"
            }
        
        # Check if session is expired
        expires_at = session.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at < datetime.utcnow():
                await self.session_store.invalidate_session(session_id)
                return {
                    "valid": False,
                    "error": "Session has expired"
                }
        
        return {
            "valid": True,
            "session": session
        }


# Singleton middleware instance
_auth_middleware = None


def get_auth_middleware(session_store=None) -> AuthMiddleware:
    """
    Get or create the auth middleware singleton.
    
    Args:
        session_store: Optional SessionStore instance.
        
    Returns:
        The AuthMiddleware instance.
    """
    global _auth_middleware
    
    if _auth_middleware is None or session_store is not None:
        _auth_middleware = AuthMiddleware(session_store)
    
    return _auth_middleware
