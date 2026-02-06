"""
Authentication Tool for MCP Server.

This tool handles Okta OAuth2 authentication flow:
1. Opens browser for user login
2. Captures auth code from callback
3. Exchanges auth code for tokens
4. Validates ID token and extracts user email

WORKFLOW: This is the FIRST tool to be called before any user query processing.
NEXT STEP: After getting the email, call 'validate_email' tool.
"""

import base64
import webbrowser
import requests
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from jose import jwt

# ==============================
# OKTA CONFIGURATION (Hardcoded)
# ==============================
# OKTA_DOMAIN = "https://integrator-3291278.okta.com"
OKTA_DOMAIN = "https://integrator-4714775.okta.com"
# CLIENT_ID = "0oaztakr35wCwuEWk697"
CLIENT_ID = "0oaztaww8zVWgsbOt697"
# CLIENT_SECRET = "PcaUJ5DfaAM-5mwKEY_iIYYyFOhgNnKvYylDjFsxBQSWSg7V_K3oTph41_cZFWPQ"
CLIENT_SECRET = "iDz4Y-bcm_dTyNInq6YP7YBpC-MckB3L6esxyMBj75BEAGn7gavQBVsv7ToWKS6F"
REDIRECT_URI = "http://localhost:8080/authorization-code/callback"
ISSUER = OKTA_DOMAIN  # Same as OKTA_DOMAIN for ORG server

# Global variable to store the auth code received from callback
_auth_code = None
_auth_error = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback with authorization code."""
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass
    
    def do_GET(self):
        global _auth_code, _auth_error
        
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == "/authorization-code/callback":
            if "code" in params:
                _auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html>
                    <body style="font-family: Arial; text-align: center; padding-top: 50px;">
                        <h1 style="color: green;">&#10004; Authentication Successful!</h1>
                        <p>You can close this window and return to the application.</p>
                    </body>
                    </html>
                """)
            elif "error" in params:
                _auth_error = params.get("error_description", params.get("error", ["Unknown error"]))[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html>
                    <body style="font-family: Arial; text-align: center; padding-top: 50px;">
                        <h1 style="color: red;">&#10008; Authentication Failed</h1>
                        <p>{_auth_error}</p>
                    </body>
                    </html>
                """.encode())
            else:
                self.send_response(400)
                self.end_headers()


def _start_callback_server(timeout: int = 120) -> str:
    """
    Start a local HTTP server to capture OAuth callback.
    
    Args:
        timeout: Maximum seconds to wait for the callback.
        
    Returns:
        The authorization code received from the callback.
        
    Raises:
        Exception: If authentication fails or times out.
    """
    global _auth_code, _auth_error
    _auth_code = None
    _auth_error = None
    
    server = HTTPServer(("localhost", 8080), OAuthCallbackHandler)
    server.timeout = timeout
    
    # Handle one request (the callback)
    server.handle_request()
    server.server_close()
    
    if _auth_error:
        raise Exception(f"Authentication failed: {_auth_error}")
    if not _auth_code:
        raise Exception("Authentication timeout: No authorization code received")
    
    return _auth_code


def _get_authorize_url() -> str:
    """Build the Okta authorization URL."""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": REDIRECT_URI,
        "state": "cm_auth_state"
    }
    return f"{OKTA_DOMAIN}/oauth2/v1/authorize?{urlencode(params)}"


def _exchange_code_for_tokens(auth_code: str) -> dict:
    """
    Exchange authorization code for tokens.
    
    Args:
        auth_code: The authorization code from OAuth callback.
        
    Returns:
        dict: Token response containing access_token, id_token, etc.
        
    Raises:
        Exception: If token exchange fails.
    """
    token_url = f"{OKTA_DOMAIN}/oauth2/v1/token"
    
    # Encode client credentials
    basic_auth = base64.b64encode(
        f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    
    if response.status_code != 200:
        raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
    
    return response.json()


def _validate_id_token(id_token: str) -> dict:
    """
    Validate the ID token and extract claims.
    
    Args:
        id_token: The JWT ID token from Okta.
        
    Returns:
        dict: Decoded claims from the ID token.
        
    Raises:
        Exception: If token validation fails.
    """
    # Fetch JWKS (JSON Web Key Set) from Okta
    jwks_url = f"{ISSUER}/oauth2/v1/keys"
    jwks = requests.get(jwks_url).json()
    
    # Get the key ID from token header
    header = jwt.get_unverified_header(id_token)
    kid = header["kid"]
    
    # Find matching key
    key = None
    for k in jwks["keys"]:
        if k["kid"] == kid:
            key = k
            break
    
    if not key:
        raise Exception(f"No matching key found for kid: {kid}")
    
    # Decode and validate token
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=ISSUER,
        options={"verify_at_hash": False}
    )
    
    return claims


async def authenticate_user_impl() -> dict:
    """
    Perform full Okta OAuth2 authentication flow.
    
    This function:
    1. Opens the browser to Okta login page
    2. Starts a local server to capture the callback
    3. Exchanges the auth code for tokens
    4. Validates the ID token and extracts user email
    
    Returns:
        dict: Contains user email and authentication status.
              {
                  "authenticated": True/False,
                  "email": "user@example.com",
                  "name": "User Name",
                  "error": "Error message if failed"
              }
    
    NEXT STEP: After authentication, call 'validate_email' tool with the email.
    """
    try:
        print("\n[AUTH] Starting Okta authentication...")
        
        # Build authorization URL
        auth_url = _get_authorize_url()
        print(f"[AUTH] Opening browser for login...")
        
        # Open browser for user login
        webbrowser.open(auth_url)
        
        print("[AUTH] Waiting for authentication callback...")
        
        # Start local server and wait for callback (blocking call)
        auth_code = _start_callback_server(timeout=120)
        print(f"[AUTH] Received authorization code")
        
        # Exchange code for tokens
        print("[AUTH] Exchanging code for tokens...")
        token_response = _exchange_code_for_tokens(auth_code)
        
        id_token = token_response.get("id_token")
        if not id_token:
            return {
                "authenticated": False,
                "error": "No ID token received from Okta"
            }
        
        # Validate ID token and extract claims
        print("[AUTH] Validating ID token...")
        claims = _validate_id_token(id_token)
        
        email = claims.get("email")
        name = claims.get("name", "Unknown")
        
        print(f"[AUTH] SUCCESS: Authentication successful for: {email}")
        
        return {
            "authenticated": True,
            "email": email,
            "name": name,
            "instruction": "User is authenticated. Now call 'validate_email' tool to verify this email exists in Content Manager.",
            "next_step": "Call 'validate_email' tool with this email address."
        }
        
    except Exception as e:
        print(f"[AUTH] ERROR: Authentication failed: {str(e)}")
        return {
            "authenticated": False,
            "error": str(e),
            "instruction": "Authentication failed. Cannot proceed with any operations."
        }
