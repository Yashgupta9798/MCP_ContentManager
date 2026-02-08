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
1. compare_token        - FIRST: Verify user is same as authenticated user
2. detect_intent        - SECOND: Detect user intent from query
3. check_authorization  - THIRD: Check if user is authorized for the intent
4. generate_action_plan - FOURTH: Generate action plan based on intent
5. search_records / create_record / update_record - FIFTH: Execute the operation

All LLM processing is done by the MCP client (Claude, Copilot, etc.).
The tools return system prompts and context; the client does the reasoning.

- Run standalone: python mcp_server.py (stdio, for external MCP clients).
- In-process: use inprocess_mcp_streams() so the agent talks to this server
  over in-memory streams (avoids Windows subprocess "Connection closed" issues).
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

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
from tools.compare_token import compare_token_impl

mcp = FastMCP(
    name="CM Tools",
    instructions=(
        "Content Manager MCP Server for search, create, and update operations.\n\n"
        "IMPORTANT: There are TWO different workflows depending on whether this is the FIRST query or a SUBSEQUENT query in the chat.\n\n"
        "=== FIRST QUERY IN CHAT (User has not authenticated yet) ===\n"
        "1. FIRST: Call 'authenticate_user' tool (NO PARAMETERS NEEDED).\n"
        "   - This opens the browser for Okta login.\n"
        "   - PRESENTATION REQUIREMENT: The MCP client MUST print the exact URL https://login.okta.com as a standalone, dark-black non-bold plain-text line immediately above any JSON output.\n"
        "     To make this reliable, the `authenticate_user` tool will include a top-level return field named `presentation_line` whose value is exactly this URL.\n"
        "     The MCP client MUST render that field as a single plain-text line (no JSON, no quotes) immediately before printing any JSON returned by tools.\n"
        "     Example (the client should output exactly the line below before JSON):\n"
        "     https://login.okta.com\n"
        "   - Returns the authenticated user's email address and token.\n"
        "   - Stores tokens in server_token.txt and client_token.txt for later verification.\n"
        "   - If authentication fails, STOP - do not proceed.\n\n"
        "2. SECOND: Call 'validate_email' tool with the email from step 1.\n"
        "   - Verifies the email exists in Content Manager.\n"
        "   - If user doesn't exist, STOP - do not proceed.\n"
        "   - If valid, returns 'Sign in successfully'.\n\n"
        "3. THIRD: Call 'detect_intent' tool with the user's query.\n"
        "   - This returns a system prompt for intent classification.\n"
        "   - Use the prompt to classify intent as: CREATE, UPDATE, SEARCH, or HELP.\n\n"
        "4. FOURTH: Call 'check_authorization' tool with email and detected intent.\n"
        "   - Verifies if the user type is allowed to perform the intent.\n"
        "   - If not authorized, STOP - do not proceed.\n"
        "   - If authorized, proceed to generate action plan.\n\n"
        "5. FIFTH: Call 'generate_action_plan' tool with user_query and detected intent.\n"
        "   - This returns a system prompt for action plan generation.\n"
        "   - Use the prompt to generate a valid JSON action plan.\n\n"
        "6. SIXTH: Call the appropriate execution tool based on the action plan's 'operation':\n"
        "   - operation='SEARCH' -> call 'search_records' with the action_plan\n"
        "   - operation='CREATE' -> call 'create_record' with the action_plan\n"
        "   - operation='UPDATE' -> call 'update_record' with the action_plan\n\n"
        "=== SUBSEQUENT QUERIES IN SAME CHAT (User already authenticated) ===\n"
        "1. FIRST: Call 'compare_token' tool (NO PARAMETERS NEEDED).\n"
        "   - Compares server_token.txt and client_token.txt to verify same user.\n"
        "   - If tokens DON'T match, STOP - tell user to start a new chat.\n"
        "   - If tokens match, proceed to detect_intent.\n\n"
        "2. SECOND: Call 'detect_intent' tool with the user's query.\n\n"
        "3. THIRD: Call 'check_authorization' tool with email and detected intent.\n\n"
        "4. FOURTH: Call 'generate_action_plan' tool with user_query and detected intent.\n\n"
        "5. FIFTH: Call the appropriate execution tool (search_records/create_record/update_record).\n\n"
        "SECURITY: The compare_token step ensures that if someone else logs in and tries to use\n"
        "an existing chat session, they will be blocked. Token mismatch = potential session hijacking.\n\n"
        "NEVER skip steps. Always start with authenticate_user for FIRST query, compare_token for SUBSEQUENT queries.\n"
        "If authentication, token comparison, email validation, or authorization fails, do NOT call any other tools."
    ),
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
    - These tokens are used by compare_token for subsequent queries
    
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
          For subsequent queries, use 'compare_token' instead.
    """
    return await authenticate_user_impl()


@mcp.tool()
async def compare_token() -> dict:
    """
    STEP 1 - SUBSEQUENT QUERIES ONLY: Verify user is same as authenticated user.
    
    This tool compares tokens stored in server_token.txt and client_token.txt
    to verify that the current user is the same as the originally authenticated user.
    
    SECURITY: This prevents session hijacking where someone else logs in and
    tries to use an existing chat session.
    
    NO PARAMETERS NEEDED - just call this tool to verify the user.
    
    Returns:
        dict containing:
        - tokens_match: True/False
        - verified: True/False (same as tokens_match)
        - message: Success message (if tokens match)
        - error: Error message (if tokens don't match)
        - next_step: What tool to call next
        
    NEXT STEP: If tokens_match=True, call 'detect_intent' tool with the user's query.
               If tokens_match=False, STOP - tell user to start a new chat.
    
    NOTE: Only call this for SUBSEQUENT queries (2nd, 3rd, etc.) in a chat.
          For the FIRST query, use 'authenticate_user' instead.
    """
    return await compare_token_impl()


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
async def generate_action_plan(user_query: str, intent: str) -> dict:
    """
    STEP 5 (CALL AFTER check_authorization): Generate action plan for the operation.
    
    This tool returns a system prompt for generating a structured action plan.
    YOU (the MCP client) must use this prompt to create a valid JSON action plan.
    
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
async def search_records(action_plan: dict) -> dict:
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
        
    WORKFLOW: authenticate_user -> validate_email -> detect_intent -> check_authorization -> generate_action_plan -> search_records (FINAL)
    """
    return await search_records_impl(action_plan)


@mcp.tool()
async def create_record(action_plan: dict) -> dict:
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
    WORKFLOW: authenticate_user -> validate_email -> detect_intent -> check_authorization -> generate_action_plan -> create_record (FINAL)
    """
    return await create_record_impl(action_plan)


@mcp.tool()
async def update_record(action_plan: dict) -> dict:
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
        
    WORKFLOW: authenticate_user -> validate_email -> detect_intent -> check_authorization -> generate_action_plan -> update_record (FINAL)
    """
    return await update_record_impl(action_plan)

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
