"""
Unified MCP server exposing Content Manager tools.

TOOL WORKFLOW (in order):
1. authenticate_user    - FIRST: Authenticate user via Okta OAuth
2. validate_email       - SECOND: Validate email exists in Content Manager
3. detect_intent        - THIRD: Detect user intent from query
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

mcp = FastMCP(
    name="CM Tools",
    instructions=(
        "Content Manager MCP Server for search, create, and update operations.\n\n"
        "IMPORTANT WORKFLOW - Follow these steps IN ORDER for every user query:\n\n"
        "1. FIRST: Call 'authenticate_user' tool (NO PARAMETERS NEEDED).\n"
        "   - This opens the browser for Okta login.\n"
        "   - Returns the authenticated user's email address.\n"
        "   - If authentication fails, STOP - do not proceed.\n\n"
        "2. SECOND: Call 'validate_email' tool with the email from step 1.\n"
        "   - Verifies the email exists in Content Manager.\n"
        "   - If user doesn't exist, STOP - do not proceed.\n"
        "   - If valid, returns 'Sign in successfully'.\n\n"
        "3. THIRD: Call 'detect_intent' tool with the user's query.\n"
        "   - This returns a system prompt for intent classification.\n"
        "   - Use the prompt to classify intent as: CREATE, UPDATE, SEARCH, or HELP.\n\n"
        "4. FOURTH: Call 'generate_action_plan' tool with user_query and detected intent.\n"
        "   - This returns a system prompt for action plan generation.\n"
        "   - Use the prompt to generate a valid JSON action plan.\n\n"
        "5. FIFTH: Call the appropriate execution tool based on the action plan's 'operation':\n"
        "   - operation='SEARCH' -> call 'search_records' with the action_plan\n"
        "   - operation='CREATE' -> call 'create_record' with the action_plan\n"
        "   - operation='UPDATE' -> call 'update_record' with the action_plan\n\n"
        "NEVER skip steps. Always start with authenticate_user for any user query.\n"
        "If authentication or email validation fails, do NOT call any other tools."
    ),
)


@mcp.tool()
async def authenticate_user() -> dict:
    """
    STEP 1 (FIRST TOOL TO CALL): Authenticate user via Okta OAuth.
    
    This tool opens the browser for Okta login, captures the OAuth callback,
    exchanges the auth code for tokens, and returns the user's email.
    
    NO PARAMETERS NEEDED - just call this tool to start authentication.
    
    Returns:
        dict containing:
        - authenticated: True/False
        - email: The user's email address (if successful)
        - name: The user's display name (if successful)
        - error: Error message (if failed)
        - next_step: What tool to call next (validate_email)
        
    NEXT STEP: If authenticated=True, call 'validate_email' tool with the email.
               If authenticated=False, STOP - do not call any other tools.
    """
    return await authenticate_user_impl()


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
        - next_step: What tool to call next (generate_action_plan)
        
    NEXT STEP: After detecting intent, call 'generate_action_plan' tool
               with the user_query and detected intent.
    """
    return await get_intent_prompt_impl(user_query)


@mcp.tool()
async def generate_action_plan(user_query: str, intent: str) -> dict:
    """
    STEP 4 (CALL AFTER detect_intent): Generate action plan for the operation.
    
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
    STEP 5 - SEARCH: Execute a search query in Content Manager.
    
    Call this tool AFTER generate_action_plan when operation='SEARCH'.
    
    Args:
        action_plan: The JSON action plan generated in Step 4 with structure:
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
        
    WORKFLOW: authenticate_user -> validate_email -> detect_intent -> generate_action_plan -> search_records (FINAL)
    """
    return await search_records_impl(action_plan)


@mcp.tool()
async def create_record(action_plan: dict) -> dict:
    """
    STEP 5 - CREATE: Create a new record in Content Manager.
    
    Call this tool AFTER generate_action_plan when operation='CREATE'.
    
    Args:
        action_plan: The JSON action plan generated in Step 4 with structure:
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
    WORKFLOW: authenticate_user -> validate_email -> detect_intent -> generate_action_plan -> create_record (FINAL)
    """
    return await create_record_impl(action_plan)


@mcp.tool()
async def update_record(action_plan: dict) -> dict:
    """
    STEP 5 - UPDATE: Update an existing record in Content Manager.
    
    Call this tool AFTER generate_action_plan when operation='UPDATE'.
    
    Args:
        action_plan: The JSON action plan generated in Step 4 with structure:
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
        
    WORKFLOW: authenticate_user -> validate_email -> detect_intent -> generate_action_plan -> update_record (FINAL)
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
