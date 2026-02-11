"""
Unified MCP server exposing Content Manager tools.

TOOL WORKFLOW (in order):

FIRST QUERY IN CHAT:
1. authenticate_user    - FIRST: Authenticate user via Okta OAuth (stores tokens)
2. validate_email       - SECOND: Validate email exists in Content Manager
3. detect_intent        - THIRD: Detect user intent from query
4. check_authorization  - FOURTH: Check if user is authorized for the intent
5. generate_action_plan - FIFTH: Generate action plan based on intent
6. search_records / create_record / update_record - SIXTH: Execute the operation

SUBSEQUENT QUERIES IN SAME CHAT:
1. detect_intent        - SECOND: Detect user intent from query
2. check_authorization  - THIRD: Check if user is authorized for the intent
3. generate_action_plan - FOURTH: Generate action plan based on intent
4. search_records / create_record / update_record - FIFTH: Execute the operation

All LLM processing is done by the MCP client (Claude, Copilot, etc.).
The tools return system prompts and context; the client does the reasoning.

- Run standalone: python mcp_server.py (stdio, for external MCP clients).
- In-process: use inprocess_mcp_streams() so the agent talks to this server
  over in-memory streams (avoids Windows subprocess "Connection closed" issues).
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

import anyio

from mcp.server.fastmcp import FastMCP

from tools.search import search_records_impl
from tools.create import create_record_impl
from tools.update import update_record_impl
from tools.intent_detection import get_intent_prompt_impl
from tools.ActionPlanGenerator import generate_action_plan_impl
from tools.authentication import authenticate_user_impl
from tools.email_validator import validate_email_impl
from tools.authorization import check_authorization_impl

# Session-based tools
from tools.session_tools import (
    get_session_info_impl,
    chat_memory_impl,
    update_memory_impl,
    clear_session_impl,
    update_session_state_impl,
    get_session_state_impl,
    validate_token_impl,
    create_session_from_token_impl
)

mcp = FastMCP(
    name="CM Tools",
    instructions=(
        "Content Manager MCP Server for search, create, and update operations.\n\n"
        "IMPORTANT: There are TWO different workflows depending on whether this is the FIRST query or a SUBSEQUENT query in the chat.\n\n"
        "=== FIRST QUERY IN CHAT (User has not authenticated yet) ===\n"
        "1. FIRST: Call 'authenticate_user' tool (NO PARAMETERS NEEDED).\n"
        "   - This opens the browser for Okta login.\n"
        "   - Returns: email, name, session_id, and token.\n"
        "   - IMPORTANT: Save the 'session_id' - you need it for ALL subsequent tool calls.\n"
        "   - If authentication fails, STOP - do not proceed.\n\n"
        "2. SECOND: Call 'validate_email' tool with the email from step 1.\n"
        "   - Verifies the email exists in Content Manager.\n"
        "   - If user doesn't exist, STOP - do not proceed.\n\n"
        "3. THIRD: Call 'detect_intent' tool with the user's query.\n"
        "   - Use the prompt to classify intent as: CREATE, UPDATE, SEARCH, or HELP.\n\n"
        "4. FOURTH: Call 'check_authorization' tool with email and intent.\n"
        "   - Verifies if the user is authorized for the intent.\n"
        "   - If not authorized, STOP - do not proceed.\n\n"
        "5. FIFTH: Call 'generate_action_plan' tool with user_query and intent.\n"
        "   - Returns action plan structure for the operation.\n\n"
        "6. SIXTH: Call the appropriate execution tool with action_plan:\n"
        "   - operation='SEARCH' -> call 'search_records'\n"
        "   - operation='CREATE' -> call 'create_record'\n"
        "   - operation='UPDATE' -> call 'update_record'\n"
        "   - NOTE: Session was already validated in step 1 (authenticate_user).\n\n"


        "=== SUBSEQUENT QUERIES IN SAME CHAT (User already authenticated) ===\n"
        "1. FIRST: Call 'validateSession' tool with the session_id from authentication.\n"
        "   - Validates the session is still active (STRICT validation).\n"
        "   - If session expired/invalid, call 'authenticate_user' again.\n"
        "   - If session valid, proceed to detect_intent.\n\n"
        "2. SECOND: Call 'detect_intent' tool with user's query.\n\n"
        "3. THIRD: Call 'check_authorization' tool with email, intent.\n\n"
        "4. FOURTH: Call 'generate_action_plan' tool with user_query, intent.\n\n"
        "5. FIFTH: Call the appropriate execution tool with action_plan.\n"
        "   - operation='SEARCH' -> call 'search_records'\n"
        "   - operation='CREATE' -> call 'create_record'\n"
        "   - operation='UPDATE' -> call 'update_record'\n"
        "SESSION-BASED SECURITY:\n"
        "- After authentication, you receive a 'session_id' - STORE THIS for the entire chat.\n"
        "- For FIRST query: Session is created by 'authenticate_user'.\n"
        "- For SUBSEQUENT queries: Call 'validateSession' FIRST to check session validity.\n"
        "- The session_id is used to validate the user and retrieve their context.\n"
        "- If session expires (1 minute) or becomes invalid, re-authenticate.\n"
        "- Session stores: user info, conversation history, and workflow state.\n\n"
        "NEVER skip steps. Always call 'validateSession' before 'detect_intent' for subsequent queries.\n"
    )
)


@mcp.tool()
async def authenticate_user() -> dict:
    """
    STEP 1 - FIRST QUERY ONLY (FIRST TOOL TO CALL): Authenticate user via Okta OAuth.
    
    This tool opens the browser for Okta login, captures the OAuth callback,
    exchanges the auth code for tokens, stores tokens for verification, and returns the user's email.
    
    NO PARAMETERS NEEDED - just call this tool to start authentication.
    
    Token Storage:
    - Stores id_token in server_token.txt (project folder)
    - Stores id_token in client_token.txt (path from Claude config)
    
    Returns:
        dict containing:
        - authenticated: True/False
        - email: The user's email address (if successful)
        - name: The user's display name (if successful)
        - token: The id_token for verification (if successful)
        - presentation_line: Exact URL string 'https://login.okta.com' — the MCP client must print this line as plain text immediately above any JSON output.
        - token_storage: Token storage status details
        - error: Error message (if failed)
        - next_step: What tool to call next (validate_email)
        
    NEXT STEP: If authenticated=True, call 'validate_email' tool with the email.
               If authenticated=False, STOP - do not call any other tools.
    
    NOTE: Only call this for the FIRST query in a chat.
          For subsequent queries, use 'validateSession' to check session validity.
    """
    return await authenticate_user_impl()


@mcp.tool()
async def validateSession(session_id: str = None, bearer_token: str = None) -> dict:
    """
    STEP 1 - SUBSEQUENT QUERIES: Validate the user's session is still active (STRICT).
    
    This tool performs STRICT session validation to ensure the session exists,
    is active, and has not expired. Use this for ALL SUBSEQUENT queries in the
    same chat after initial authentication.
    
    Args:
        session_id: The session ID from authenticate_user (preferred).
        bearer_token: Alternative: the bearer token for validation.
        
    Returns:
        dict containing:
        - valid: True/False
        - session_id: The session ID (if valid)
        - user_id: The user's ID (if valid)
        - email: The user's email (if valid)
        - name: The user's name (if valid)
        - status: Session status (if valid)
        - error: Error message (if invalid)
        - status_code: HTTP status code (if invalid)
        - instruction: What to do next (if invalid)
        
    NEXT STEP: If valid=True, proceed to 'detect_intent' with user's query.
               If valid=False, call 'authenticate_user' to re-authenticate.
    
    NOTE: Always use session_id when available. It's returned by authenticate_user.
          This tool uses strict validation to check session status and expiry.
    """
    from tools.session_validator import validate_session_for_tool
    return await validate_session_for_tool(session_id, bearer_token)


@mcp.tool()
async def validate_email(email: str) -> dict:
    """
    STEP 2 (CALL AFTER authenticate_user): Validate email exists in Content Manager.
    
    This tool verifies that the authenticated user's email is registered
    in the Content Manager system.
    
    Args:
        email: The email address from authenticate_user (step 1).
        
    Returns:
        dict containing:
        - valid: True/False
        - message: "Sign in successfully" (if valid)
        - user_name: The user's name in Content Manager (if valid)
        - user_uri: The user's URI in Content Manager (if valid)
        - error: Error message (if invalid)
        - next_step: What tool to call next
        
    NEXT STEP: If valid=True, call 'detect_intent' tool with the user's query.
               If valid=False, STOP - do not call any other tools.
    """
    return await validate_email_impl(email)


@mcp.tool()
async def detect_intent(user_query: str) -> dict:
    """
    STEP 3 (CALL AFTER validate_email): Detect intent from user query.
    
    This tool returns a system prompt for intent classification.
    YOU (the MCP client) must use this prompt to classify the user's query
    into one of: CREATE, UPDATE, SEARCH, or HELP.
    
    Args:
        user_query: The user's original request/question.
        
    Returns:
        dict containing:
        - system_prompt: The prompt to use for intent classification
        - user_query: The original query
        - instruction: How to process and respond
        - next_step: What tool to call next (check_authorization)
        
    NEXT STEP: After detecting intent, call 'check_authorization' tool
               with the email and detected intent.
    """
    return await get_intent_prompt_impl(user_query)


@mcp.tool()
async def check_authorization(email: str, intent: str) -> dict:
    """
    STEP 4 (CALL AFTER detect_intent): Check if user is authorized for the operation.
    
    This tool verifies that the user's type allows them to perform the detected intent.
    
    Authorization rules by user type:
    - Inquiry User: SEARCH only
    - Administrator: SEARCH, CREATE, UPDATE
    - Records Manager: SEARCH, CREATE, UPDATE
    - Records Co-ordinator: SEARCH, CREATE, UPDATE
    - Knowledge Worker: SEARCH, CREATE, UPDATE
    - Contributor: SEARCH, CREATE
    
    Args:
        email: The user's email address (from validate_email step 2).
        intent: The detected intent (CREATE, UPDATE, SEARCH, or HELP).
        
    Returns:
        dict containing:
        - authorized: True/False
        - user_type: The user's type in Content Manager
        - intent: The operation being authorized
        - message: Success message (if authorized)
        - error: Failure reason (if not authorized)
        - allowed_operations: List of operations this user can perform
        - next_step: What tool to call next
        
    NEXT STEP: If authorized=True, call 'generate_action_plan' tool with user_query and intent.
               If authorized=False, STOP - do not call any other tools.
    """
    return await check_authorization_impl(email, intent)


@mcp.tool()
async def generate_action_plan(
    user_query: str,
    intent: str,
) -> dict:
    """
    STEP 5 (CALL AFTER check_authorization): Generate action plan for the operation.
    
    Args:
        user_query: The user's original request/question.
        intent: The detected intent (CREATE, UPDATE, SEARCH, or HELP).
    
        
    Returns:
        dict containing:
        - system_prompt: The prompt for action plan generation
        - user_query: The original query
        - intent: The detected intent
        - retrieved_docs: Relevant documentation from RAG
        - instruction: How to generate the action plan
        - next_step: What tool to call next based on operation
       
    NEXT STEP: After generating the action plan JSON, call the appropriate tool:
               - operation='SEARCH' -> call 'search_records' with action_plan
               - operation='CREATE' -> call 'create_record' with action_plan
               - operation='UPDATE' -> call 'update_record' with action_plan
    
    """
    return await generate_action_plan_impl(user_query, intent)


@mcp.tool()
async def search_records(
    action_plan: dict
) -> dict:
    """
    STEP 6 - SEARCH: Execute a search query in Content Manager.
    
    Call this tool AFTER generate_action_plan when operation='SEARCH'.
    
    Args:
        action_plan: The JSON action plan generated in Step 5 with structure:
            {
                "path": "Record/",
                "method": "GET",
                "parameters": {
                    "number": "<optional>",
                    "combinedtitle": "<optional>",
                    "type": "Document|Folder <optional>",
                    "createdon": "mm/dd/yyyy <optional>",
                    "editstatus": "checkin|checkout <optional>",
                    "format": "json",
                    "properties": "NameString"
                },
                "operation": "SEARCH"
            }
        
    Returns:
        dict: JSON response from Content Manager API with search results.
        
    WORKFLOW: validateSession -> detect_intent -> check_authorization -> generate_action_plan -> search_records (FINAL)
    """
    return await search_records_impl(action_plan)


@mcp.tool()
async def create_record(
    action_plan: dict
) -> dict:
    """
    STEP 6 - CREATE: Create a new record in Content Manager.
    
    Call this tool AFTER generate_action_plan when operation='CREATE'.

    
    Args:
        action_plan: The JSON action plan generated in Step 5 with structure:
            {
                "path": "Record/",
                "method": "POST",
                "parameters": {
                    "RecordRecordType": "Document|Folder",  (REQUIRED)
                    "RecordTitle": "<title>",               (REQUIRED)
                    "RecordNumber": "<optional>",
                    "RecordDateCreated": "mm/dd/yyyy <optional>",
                    "RecordEditState": "<optional>"
                },
                "operation": "CREATE"
            }
            
    Returns:
        dict: JSON response from Content Manager API with created record details.
        
    IMPORTANT: RecordTitle and RecordRecordType are MANDATORY.
    WORKFLOW: validateSession -> detect_intent -> check_authorization -> generate_action_plan -> create_record (FINAL)
    """
    return await create_record_impl(action_plan)


@mcp.tool()
async def update_record(
    action_plan: dict,

) -> dict:
    """
    STEP 6 - UPDATE: Update an existing record in Content Manager.
    
    Call this tool AFTER generate_action_plan when operation='UPDATE'.
    

    Args:
        action_plan: The JSON action plan generated in Step 5 with structure:
            {
                "path": "Record/",
                "method": "POST",
                "parameters_to_search": {
                    "number": "<optional>",
                    "combinedtitle": "<optional>",
                    "type": "Document|Folder <optional>",
                    "format": "json",
                    "properties": "NameString"
                },
                "parameters_to_update": {
                    "RecordNumber": "<optional>",
                    "RecordTitle": "<optional>",
                    "RecordRecordType": "<optional>",
                    "RecordDateCreated": "<optional>",
                    "RecordEditState": "<optional>"
                },
                "operation": "UPDATE"
            }
            
    Returns:
        dict: JSON response from Content Manager API with updated record details.
        
    WORKFLOW: validateSession -> detect_intent -> check_authorization -> generate_action_plan -> update_record (FINAL)
    """
    return await update_record_impl(action_plan)


# =============================================================================
# SESSION-BASED TOOLS (New MCP Tool Layer)
# =============================================================================

@mcp.tool()
async def getSessionInfo(session_id: str = None, bearer_token: str = None) -> dict:
    """
    Get comprehensive session information and metadata.
    
    Retrieves session data including user info, status, and conversation count.
    
    Args:
        session_id: The session ID to look up (optional if bearer_token provided).
        bearer_token: The bearer token to identify session (optional).
        
    Returns:
        dict containing:
        - success: True/False
        - session_id, user_id, email, name
        - created_at, last_activity, expires_at
        - status: active/idle/expired
        - conversation_count: Number of messages
        - error: Error message if failed
    """
    return await get_session_info_impl(session_id, bearer_token)


@mcp.tool()
async def chatMemory(
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
        For read action:
        - success: True/False
        - messages: List of messages
        - count: Number of messages returned
        
        For append action:
        - success: True/False
        - message_id: ID of added message
        - stored: True if message was stored
    """
    return await chat_memory_impl(session_id, bearer_token, action, limit, message)


@mcp.tool()
async def updateMemory(
    session_id: str = None,
    bearer_token: str = None,
    role: str = "assistant",
    content: str = "",
    tools_used: List[str] = None,
    metadata: dict = None
) -> dict:
    """
    Append a new message to the conversation history.
    
    Convenience tool for adding messages to session memory.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        role: The message role (user, assistant).
        content: The message content.
        tools_used: List of tools used in this interaction.
        metadata: Additional metadata to store.
        
    Returns:
        dict containing:
        - success: True/False
        - message_id: ID of the added message
        - stored: True if successful
        - cache_updated: True if cache was updated
    """
    return await update_memory_impl(session_id, bearer_token, role, content, tools_used, metadata)


@mcp.tool()
async def clearSession(
    session_id: str = None,
    bearer_token: str = None,
    clear_conversation_only: bool = False
) -> dict:
    """
    Clear session data or logout completely.
    
    Can either clear conversation history only or perform full logout.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        clear_conversation_only: If True, only clear conversation, keep session active.
                                 If False (default), perform full logout.
        
    Returns:
        dict containing:
        - success: True/False
        - action: "clear_conversation" or "logout"
        - session_invalidated: True if session was invalidated
        - conversation_cleared: True if conversation was cleared
    """
    return await clear_session_impl(session_id, bearer_token, clear_conversation_only)


@mcp.tool()
async def updateSessionState(
    session_id: str = None,
    bearer_token: str = None,
    state: dict = None
) -> dict:
    """
    Update the state stored in the session cache.
    
    Useful for storing workflow state, user context, or any data
    that should persist across tool calls within the session.
    
    Args:
        session_id: The session ID (optional if bearer_token provided).
        bearer_token: The bearer token (optional if session_id provided).
        state: The state data to store (replaces existing state).
        
    Returns:
        dict containing:
        - success: True/False
        - state_updated: True if state was updated
        - state_keys: List of keys in the stored state
    """
    return await update_session_state_impl(session_id, bearer_token, state)


@mcp.tool()
async def getSessionState(
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
    """
    return await get_session_state_impl(session_id, bearer_token)


@mcp.tool()
async def validateToken(bearer_token: str) -> dict:
    """
    Validate a bearer token and return its claims.
    
    Validates the JWT using Okta JWKS and returns decoded claims.
    
    Args:
        bearer_token: The bearer token to validate (with or without "Bearer " prefix).
        
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
    return await validate_token_impl(bearer_token)


@mcp.tool()
async def createSessionFromToken(bearer_token: str) -> dict:
    """
    Create a session from a valid bearer token.
    
    Creates a session in the MCP server from an existing OAuth token.
    Useful when the client already has a token from the OAuth flow.
    
    Args:
        bearer_token: The bearer token from OAuth (with or without "Bearer " prefix).
        
    Returns:
        dict containing:
        - success: True/False
        - session_id: The created session ID
        - user_id: The user's ID
        - email: The user's email
        - name: The user's name
        - created_at: Session creation timestamp
        - expires_at: Session expiration timestamp
        - error: Error message if failed
    """
    return await create_session_from_token_impl(bearer_token)


@asynccontextmanager
async def inprocess_mcp_streams() -> AsyncIterator[tuple]:
    """
    Yield (read_stream, write_stream) for an MCP client in the same process.
    Use with ClientSession(read_stream, write_stream) so the agent can call
    tools without spawning a subprocess (avoids Windows stdio "Connection closed").
    """
    # Client writes -> a_send; server reads <- a_receive
    # Server writes -> b_send; client reads <- b_receive
    a_send, a_receive = anyio.create_memory_object_stream(0)
    b_send, b_receive = anyio.create_memory_object_stream(0)

    init_options = mcp._mcp_server.create_initialization_options()

    async def run_server() -> None:
        try:
            await mcp._mcp_server.run(a_receive, b_send, init_options)
        except anyio.ClosedResourceError:
            pass
        finally:
            await b_send.aclose()

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        try:
            yield b_receive, a_send
        finally:
            await a_send.aclose()


if __name__ == "__main__":
    mcp.run()
