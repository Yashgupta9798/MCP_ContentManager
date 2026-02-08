"""
Token Comparison Tool for MCP Server.

This tool compares the tokens stored in server_token.txt and client_token.txt
to verify that the user making a subsequent query is the same user who 
authenticated at the start of the chat session.

WORKFLOW: This is called for the 2nd, 3rd, ... queries in the SAME chat session.
          For the FIRST query, use authenticate_user instead.

SECURITY: If tokens don't match, it means someone else may have logged in
          and is trying to use an existing chat session. This is blocked.

NEXT STEP: If tokens match, proceed to 'detect_intent' tool.
           If tokens don't match, STOP - user must start a new chat.
"""

import os

# Token storage paths (same as in authentication.py)
SERVER_TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server_token.txt")
CLIENT_TOKEN_PATH = os.getenv("CLIENT_TOKEN_PATH")


def _read_token(file_path: str, token_name: str) -> tuple[str | None, str | None]:
    """
    Read token from a file.
    
    Args:
        file_path: Path to the token file.
        token_name: Name of the token for error messages.
        
    Returns:
        tuple: (token_value or None, error_message or None)
    """
    if not file_path:
        return None, f"{token_name} path not configured"
    
    if not os.path.exists(file_path):
        return None, f"{token_name} file not found at: {file_path}"
    
    try:
        with open(file_path, "r") as f:
            token = f.read().strip()
            if not token:
                return None, f"{token_name} file is empty"
            return token, None
    except Exception as e:
        return None, f"Failed to read {token_name}: {str(e)}"


async def compare_token_impl() -> dict:
    """
    Compare tokens from server_token.txt and client_token.txt.
    
    This function:
    1. Reads the token from server_token.txt (project folder)
    2. Reads the token from client_token.txt (path from Claude config)
    3. Compares them to verify the user is the same
    
    Returns:
        dict: Contains comparison result and status.
              {
                  "tokens_match": True/False,
                  "verified": True/False (same as tokens_match),
                  "message": "Success or error message",
                  "error": "Error description if failed",
                  "next_step": "What to do next"
              }
    
    NEXT STEP: If tokens_match=True, proceed to 'detect_intent' tool.
               If tokens_match=False, STOP - tell user to start a new chat.
    """
    print("\n[TOKEN] Comparing authentication tokens...")
    
    # Read server token
    server_token, server_error = _read_token(SERVER_TOKEN_PATH, "Server token")
    if server_error:
        print(f"[TOKEN] ERROR: {server_error}")
        return {
            "tokens_match": False,
            "verified": False,
            "error": server_error,
            "instruction": "Token verification failed. Authentication may not have been completed.",
            "next_step": "STOP - Cannot verify user identity. Ask user to start a new chat and authenticate again."
        }
    
    # Read client token
    client_token, client_error = _read_token(CLIENT_TOKEN_PATH, "Client token")
    if client_error:
        print(f"[TOKEN] ERROR: {client_error}")
        return {
            "tokens_match": False,
            "verified": False,
            "error": client_error,
            "instruction": "Token verification failed. Client token not found.",
            "next_step": "STOP - Cannot verify user identity. Ask user to start a new chat and authenticate again."
        }
    
    # Compare tokens
    if server_token == client_token:
        print("[TOKEN] SUCCESS: Tokens match - user verified")
        return {
            "tokens_match": True,
            "verified": True,
            "message": "User identity verified. Tokens match.",
            "instruction": "User is verified as the same authenticated user. Proceed with query processing.",
            "next_step": "Call 'detect_intent' tool with the user's query."
        }
    else:
        print("[TOKEN] SECURITY WARNING: Tokens do not match!")
        return {
            "tokens_match": False,
            "verified": False,
            "error": "Token mismatch detected. A different user may have logged in.",
            "instruction": "SECURITY: The current user is NOT the same as the originally authenticated user. This could be a session hijacking attempt.",
            "next_step": "STOP - Do NOT proceed with any operations. Tell the user: 'Your session cannot be verified. Please start a new chat and authenticate again.'"
        }
