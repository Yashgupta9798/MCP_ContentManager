from llm.intent_router import IntentRouter
from tools.ActionPlanGenerator import ActionPlanGenerator

from mcp import ClientSession

from mcp_server import inprocess_mcp_streams

import json


def _parse_call_tool_result(result) -> str:
    """Extract response from MCP CallToolResult (content list, is_error)."""
    if getattr(result, "is_error", False):
        return f"Tool error: {result}"
    content = getattr(result, "content", None) or []
    parts = []
    for item in content:
        if hasattr(item, "text"):
            parts.append(item.text)
        elif isinstance(item, dict) and "text" in item:
            parts.append(item["text"])
    if parts:
        return "\n".join(parts)
    return str(result)


def _parse_result_to_dict(result) -> dict:
    """Parse MCP CallToolResult to dictionary."""
    text = _parse_call_tool_result(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text}


class Agent:

    def __init__(self):
        self.intent_router = IntentRouter()
        self._authenticated_email = None
        self._user_validated = False

    async def handle_query(self, user_query: str):
        """
        Handle user query with full authentication flow.
        
        WORKFLOW ORDER:
        1. authenticate_user - Get user email via Okta OAuth (once per session)
        2. validate_email - Verify email exists in Content Manager (once per session)
        3. detect_intent - Classify user intent (EVERY query)
        4. check_authorization - Verify user can perform the intent (EVERY query)
        5. generate_action_plan - Create action plan
        6. Execute operation (search/create/update)
        """
        
        # -----------------------
        # STEP 1: AUTHENTICATION (if not already authenticated)
        # -----------------------
        if not self._authenticated_email:
            print("\n[AGENT] STEP 1: Starting authentication...")
            auth_result = await self._authenticate_user()
            
            if not auth_result.get("authenticated", False):
                error_msg = auth_result.get("error", "Authentication failed")
                print(f"[AGENT] ERROR: Authentication failed: {error_msg}")
                return f"Authentication failed: {error_msg}. Cannot proceed."
            
            self._authenticated_email = auth_result.get("email")
            print(f"[AGENT] SUCCESS: Authenticated as: {self._authenticated_email}")
        else:
            print(f"[AGENT] Already authenticated as: {self._authenticated_email}")
        
        # -----------------------
        # STEP 2: EMAIL VALIDATION (if not already validated)
        # -----------------------
        if not self._user_validated:
            print("\n[AGENT] STEP 2: Validating email in Content Manager...")
            validation_result = await self._validate_email(self._authenticated_email)
            
            if not validation_result.get("valid", False):
                error_msg = validation_result.get("error", "Email validation failed")
                print(f"[AGENT] ERROR: Email validation failed: {error_msg}")
                # Reset authentication on validation failure
                self._authenticated_email = None
                return f"User validation failed: {error_msg}. Cannot proceed."
            
            self._user_validated = True
            user_name = validation_result.get("user_name", "Unknown")
            print(f"[AGENT] SUCCESS: User validated: {user_name}")
            print(f"[AGENT] {validation_result.get('message', 'Sign in successfully')}")
        else:
            print(f"[AGENT] User already validated: {self._authenticated_email}")
        
        # -----------------------
        # STEP 3: INTENT DETECTION (called for EVERY query)
        # -----------------------
        print("\n[AGENT] STEP 3: Detecting intent...")
        intent = self.intent_router.detect_intent(user_query)
        print(f"[AGENT] Detected intent: {intent}")

        # -----------------------
        # STEP 4: AUTHORIZATION CHECK (called for EVERY query)
        # -----------------------
        print("\n[AGENT] STEP 4: Checking authorization...")
        auth_check_result = await self._check_authorization(self._authenticated_email, intent)
        
        if not auth_check_result.get("authorized", False):
            error_msg = auth_check_result.get("error", "Authorization failed")
            allowed_ops = auth_check_result.get("allowed_operations", [])
            user_type = auth_check_result.get("user_type", "Unknown")
            print(f"[AGENT] ERROR: Authorization denied: {error_msg}")
            return f"Authorization denied: {error_msg}. Your user type '{user_type}' can only perform: {', '.join(allowed_ops) if allowed_ops else 'no operations'}."
        
        print(f"[AGENT] SUCCESS: User authorized for {intent}")

        # -----------------------
        # STEP 5: ACTION PLAN GENERATION
        # -----------------------
        print("\n[AGENT] STEP 5: Generating action plan...")
        action_plan = ActionPlanGenerator().run(user_query, intent)
        print(f"[AGENT] Action Plan Generated: {action_plan}")

        # -----------------------
        # STEP 6: EXECUTION (MCP) — no direct tool calling; all via MCP server
        # -----------------------
        print("\n[AGENT] STEP 6: Executing operation via MCP...")
        response = await self._execute_via_mcp(action_plan)

        print("\n[AGENT] Final Response:")
        print(response)

        return response

    # -------------------------------------------------
    # AUTHENTICATION METHODS
    # -------------------------------------------------

    async def _authenticate_user(self) -> dict:
        """Call authenticate_user MCP tool."""
        try:
            async with inprocess_mcp_streams() as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "authenticate_user",
                        arguments={},
                    )
                    return _parse_result_to_dict(result)
        except Exception as e:
            print(f"[AGENT] Authentication error: {e}")
            return {"authenticated": False, "error": str(e)}

    async def _validate_email(self, email: str) -> dict:
        """Call validate_email MCP tool."""
        try:
            async with inprocess_mcp_streams() as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "validate_email",
                        arguments={"email": email},
                    )
                    return _parse_result_to_dict(result)
        except Exception as e:
            print(f"[AGENT] Email validation error: {e}")
            return {"valid": False, "error": str(e)}

    async def _check_authorization(self, email: str, intent: str) -> dict:
        """Call check_authorization MCP tool to verify user can perform the intent."""
        try:
            async with inprocess_mcp_streams() as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "check_authorization",
                        arguments={"email": email, "intent": intent},
                    )
                    return _parse_result_to_dict(result)
        except Exception as e:
            print(f"[AGENT] Authorization check error: {e}")
            return {"authorized": False, "error": str(e)}

    # -------------------------------------------------
    # MCP EXECUTOR — spawn MCP server via stdio, call tool by name
    # -------------------------------------------------

    async def _execute_via_mcp(self, action_plan: dict):
        method = action_plan.get("method")
        operation = action_plan.get("operation", "").upper()

        # Map action plan → MCP tool name (no direct Python calls)
        if method == "GET" or operation == "SEARCH":
            tool_name = "search_records"
        elif method == "POST" and (operation == "CREATE" or str(operation).lower() == "create"):
            tool_name = "create_record"
        elif method == "POST" and (operation == "UPDATE" or str(operation).lower() == "update"):
            tool_name = "update_record"
        else:
            return "Unsupported operation"

        print(f"\n[AGENT] Calling MCP tool → {tool_name}")

        try:
            # In-process MCP: same process, in-memory streams (avoids Windows subprocess "Connection closed")
            async with inprocess_mcp_streams() as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        tool_name,
                        arguments={"action_plan": action_plan},
                    )
                    return _parse_call_tool_result(result)
        except Exception as e:
            print(f"\n[AGENT] Error calling tool: {e}")
            raise
