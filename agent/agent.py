from llm.intent_router import IntentRouter
from tools.ActionPlanGenerator import ActionPlanGenerator

from mcp import ClientSession
from mcp.client.stdio import stdio_client as StdioClient


class Agent:

    def __init__(self):
        self.intent_router = IntentRouter()

    async def handle_query(self, user_query: str):
        print("inside agent before intent detection")
        
        intent = self.intent_router.detect_intent(user_query)
        print("Detected intent:", intent)

        # -----------------------
        # ACTION PLAN GENERATION
        # -----------------------

        action_plan = ActionPlanGenerator().run(user_query, intent)

        print("\nAction Plan Generated:")
        print(action_plan)

        # -----------------------
        # EXECUTION (MCP)
        # -----------------------

        response = await self.ExecuteTool(action_plan)

        print("\nFinal Response:")
        print(response)

        return response

    # -------------------------------------------------
    # MCP EXECUTOR
    # -------------------------------------------------

    async def ExecuteTool(self, action_plan: dict):

        method = action_plan.get("method")
        tool = action_plan.get("tool")

        # Map plan → tool name
        if method == "GET":
            tool_name = "search_records"

        elif method == "POST" and tool == "create":
            tool_name = "create_record"

        elif method == "POST" and tool == "update":
            tool_name = "update_record"

        else:
            return "Unsupported operation"

        print(f"\nCalling MCP tool → {tool_name}")

        # MCP session
        async with StdioClient() as client:
            async with ClientSession(client) as session:
                await session.initialize()
                result = await session.call_tool(
                    tool_name,
                    arguments={
                        "action_plan": action_plan
                    }
                )

        return result
