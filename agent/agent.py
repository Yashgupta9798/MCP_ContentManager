from llm.intent_router import IntentRouter

from tools import ActionPlanGeneratorWrite
from tools import ActionPlanGenerator
from tools.search import SearchTool
from tools.create import CreateTool
from tools.update import UpdateTool


class Agent:

    def __init__(self):
        self.intent_router = IntentRouter()

    def handle_query(self, user_query: str):

        intent = self.intent_router.detect_intent(user_query)
        print("Detected intent:", intent)

        # -----------------------
        # ACTION PLAN GENERATION
        # -----------------------
        try:
            action_plan = ActionPlanGenerator().run(user_query, intent)
        except Exception as e:
            print("Unable to understand the request.")
            return

        print("\nAction Plan Generated:")
        print(action_plan)
        
        # -----------------------
        # EXECUTION
        # -----------------------

        response = self.ExecuteTool(action_plan)

        print("\nFinal Response:")
        print(response)

        return response
    
    

    # -------------------------------------------------
    # EXECUTOR
    # -------------------------------------------------

    def ExecuteTool(self, action_plan: dict):

        method = action_plan.get("method")
        tool = action_plan.get("tool")

        response = None

        # -----------------------
        # GET → SEARCH
        # -----------------------
        if method == "GET":

            print("\nExecutor: calling SEARCH tool")

            response = SearchTool().execute(action_plan)

        # -----------------------
        # POST → CREATE / UPDATE
        # -----------------------
        elif method == "POST":

            if tool == "create":
                print("\nExecutor: calling CREATE tool")
                response = CreateTool().execute(action_plan)

            elif tool == "update":
                print("\nExecutor: calling UPDATE tool")
                response = UpdateTool().execute(action_plan)

            else:
                response = "Unknown POST tool"

        else:
            response = "Unsupported HTTP method"

        return response