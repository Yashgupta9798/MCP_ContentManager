"""
INTEGRATION GUIDE: How to use JourneyLogger in your existing code
===================================================================

This file shows code examples for integrating the JourneyLogger into each component
of your system. You can copy these code snippets into your respective files.

File Structure for Logging:
├── logs/
│   ├── audit.log                          # Main audit trail
│   ├── requests/
│   │   └── JOURNEY_YYYYMMDD_HHMMSS_XXXX.json    # Complete journey trace
│   ├── action_plans/
│   │   └── JOURNEY_YYYYMMDD_HHMMSS_XXXX_plan.json
│   ├── tool_calls/
│   │   └── JOURNEY_YYYYMMDD_HHMMSS_XXXX_<tool_name>.json
│   └── errors/
│       └── JOURNEY_YYYYMMDD_HHMMSS_XXXX_<stage>_error.json

"""

# =====================================================================
# 1. MAINCP_CLIENT.PY - Entry Point
# =====================================================================

"""
UPDATE: mcp_client.py

Replace the current main() function with this enhanced version:
"""

from agent.agent import Agent
from tools.search import search_records
from logging_config.journey_logger import get_journey_logger
import asyncio
import time


def main():
    print("===== CM AI SERVER STARTED =====")
    
    # Initialize the journey logger
    journey_logger = get_journey_logger()
    
    agent = Agent()

    while True:
        user_query = input("\nEnter your query (type 'exit' to stop): ")

        if user_query.lower() == "exit":
            print("Server stopped.")
            break

        print("\n--- Sending query to Agent ---")
        
        # START THE JOURNEY
        journey_id = journey_logger.start_journey(user_query)
        
        start_time = time.time()
        
        try:
            # Run the asynchronous handle_query method
            # PASS journey_logger and journey_id to agent
            response = asyncio.run(agent.handle_query(user_query, journey_id, journey_logger))

            total_time = time.time() - start_time
            
            # LOG JOURNEY COMPLETION
            journey_logger.log_journey_completion(
                journey_id=journey_id,
                final_response=response,
                total_time=total_time,
                success=True
            )

            print("\n--- Final Response Stored in Variable 'response' ---")
            print(response)
            
        except Exception as e:
            total_time = time.time() - start_time
            journey_logger.log_error(
                journey_id=journey_id,
                error_type="MainError",
                error_message=str(e),
                stage="main_execution",
                stack_trace=traceback.format_exc()
            )
            journey_logger.log_journey_completion(
                journey_id=journey_id,
                final_response=str(e),
                total_time=total_time,
                success=False
            )
            print(f"Error: {e}")


if __name__ == "__main__":
    main()


# =====================================================================
# 2. AGENT/AGENT.PY - Main Orchestrator
# =====================================================================

"""
UPDATE: agent/agent.py

Replace the current Agent class with this enhanced version:
"""

from llm.intent_router import IntentRouter
from tools.ActionPlanGenerator import ActionPlanGenerator
from logging_config.journey_logger import JourneyLogger, get_journey_logger
from mcp import ClientSession
from mcp.client.stdio import stdio_client as StdioClient
import time
import traceback


class Agent:

    def __init__(self):
        self.intent_router = IntentRouter()
        self.journey_logger = get_journey_logger()

    async def handle_query(self, user_query: str, journey_id: str = None, 
                          journey_logger: JourneyLogger = None):
        """
        Main handler for processing user queries with comprehensive logging.
        
        Args:
            user_query: The user's input query
            journey_id: Optional journey ID for tracking
            journey_logger: Optional journey logger instance
        """
        
        # Use provided logger or get default
        if journey_logger is None:
            journey_logger = get_journey_logger()
        if journey_id is None:
            journey_id = journey_logger.start_journey(user_query)
        
        try:
            print("inside agent before intent detection")
            
            # -----------------------
            # INTENT DETECTION
            # -----------------------
            intent_start = time.time()
            
            intent = self.intent_router.detect_intent(user_query)
            
            intent_time = time.time() - intent_start
            
            print("Detected intent:", intent)
            
            # LOG INTENT
            journey_logger.log_intent_detection(
                journey_id=journey_id,
                intent=intent,
                confidence=None  # Add confidence if LLM provides it
            )

            # -----------------------
            # ACTION PLAN GENERATION
            # -----------------------
            plan_start = time.time()
            
            action_plan = ActionPlanGenerator().run(user_query, intent)
            
            plan_time = time.time() - plan_start

            print("\nAction Plan Generated:")
            print(action_plan)
            
            # LOG ACTION PLAN
            journey_logger.log_action_plan(
                journey_id=journey_id,
                action_plan=action_plan,
                generation_time=plan_time
            )

            # -----------------------
            # EXECUTION (MCP)
            # -----------------------
            response = await self.ExecuteTool(action_plan, journey_id, journey_logger)

            print("\nFinal Response:")
            print(response)

            return response
        
        except Exception as e:
            journey_logger.log_error(
                journey_id=journey_id,
                error_type="AgentError",
                error_message=str(e),
                stage="query_handling",
                stack_trace=traceback.format_exc()
            )
            raise

    async def ExecuteTool(self, action_plan: dict, journey_id: str, 
                         journey_logger: JourneyLogger):
        """
        Execute the tool specified in the action plan with logging.
        """
        
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
            error_msg = "Unsupported operation"
            journey_logger.log_error(
                journey_id=journey_id,
                error_type="OperationError",
                error_message=error_msg,
                stage="tool_mapping"
            )
            return error_msg

        print(f"\nCalling MCP tool → {tool_name}")
        
        # LOG TOOL EXECUTION START
        journey_logger.log_tool_execution_start(
            journey_id=journey_id,
            tool_name=tool_name,
            arguments={"action_plan": action_plan}
        )
        
        tool_start = time.time()
        
        try:
            # MCP session
            async with StdioClient() as client:
                async with ClientSession(client) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        tool_name,
                        arguments={"action_plan": action_plan}
                    )
            
            tool_time = time.time() - tool_start
            
            # LOG TOOL EXECUTION RESULT
            journey_logger.log_tool_execution_result(
                journey_id=journey_id,
                tool_name=tool_name,
                result=result,
                execution_time=tool_time,
                success=True
            )
            
            return result
        
        except Exception as e:
            tool_time = time.time() - tool_start
            
            journey_logger.log_tool_execution_result(
                journey_id=journey_id,
                tool_name=tool_name,
                result=None,
                execution_time=tool_time,
                success=False,
                error=str(e)
            )
            raise


# =====================================================================
# 3. LLM/INTENT_ROUTER.PY - Enhanced with Logging
# =====================================================================

"""
UPDATE: llm/intent_router.py

Add logging to the detect_intent method:
"""

import os
import json
import re
import time
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from logging_config.journey_logger import get_journey_logger


class IntentRouter:

    def __init__(self):
        endpoint = HuggingFaceEndpoint(
            repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
            huggingfacehub_api_token=os.getenv("HF_TOKEN"),
            temperature=0,
            max_new_tokens=100
        )

        self.llm = ChatHuggingFace(llm=endpoint)
        self.journey_logger = get_journey_logger()

    def _extract_json(self, text: str):
        match = re.search(r"\{[\s\S]*?\}", text)
        return match.group() if match else None

    def detect_intent(self, user_query: str, journey_id: str = None):
        """
        Detect user intent with optional logging.
        
        Args:
            user_query: The user query
            journey_id: Optional journey ID for logging
            
        Returns:
            str: The detected intent
        """
        
        intent_start = time.time()
        
        try:
            prompt = open("prompts/intent_prompt.md").read()
            prompt = prompt + f"\n\nUser query:\n{user_query}"

            response = self.llm.invoke(prompt)
            text = response.content.strip()

            json_text = self._extract_json(text)

            if not json_text:
                return "UNKNOWN"

            data = json.loads(json_text)
            intent = data.get("intent", "UNKNOWN")
            confidence = data.get("confidence", None)
            
            return intent
        
        except Exception as e:
            if journey_id:
                self.journey_logger.log_error(
                    journey_id=journey_id,
                    error_type="IntentDetectionError",
                    error_message=str(e),
                    stage="intent_detection"
                )
            return "UNKNOWN"


# =====================================================================
# 4. TOOLS/ACTIONPLANGENERATOR.PY - Enhanced with Logging
# =====================================================================

"""
UPDATE: tools/ActionPlanGenerator.py

Add logging for RAG retrieval and plan generation:
"""

import os
import json
import re
import time
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from rag.retriever import ToolRetriever
from logging_config.journey_logger import get_journey_logger

load_dotenv()


class ActionPlanGenerator:

    def __init__(self):
        endpoint = HuggingFaceEndpoint(
            repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
            huggingfacehub_api_token=os.getenv("HF_TOKEN"),
            temperature=0,
            max_new_tokens=300
        )

        self.llm = ChatHuggingFace(llm=endpoint)
        self.journey_logger = get_journey_logger()

    def _extract_json(self, text: str):
        match = re.search(r"\{[\s\S]*?\}", text)
        return match.group() if match else None

    def run(self, user_query: str, intent: str, journey_id: str = None):
        """
        Generate action plan for SEARCH/HELP operations with logging.
        
        Args:
            user_query: The user's request
            intent: The detected intent (SEARCH OR HELP)
            journey_id: Optional journey ID for logging
            
        Returns:
            dict: The action plan as a JSON object
        """
        
        try:
            # RAG RETRIEVAL
            rag_start = time.time()
            
            retrieved_docs = ToolRetriever().match(user_query)
            
            rag_time = time.time() - rag_start
            
            print(retrieved_docs)
            
            # LOG RAG RETRIEVAL
            if journey_id:
                self.journey_logger.log_rag_retrieval(
                    journey_id=journey_id,
                    query=user_query,
                    retrieved_docs=retrieved_docs if isinstance(retrieved_docs, list) else [],
                    retrieval_time=rag_time
                )
            
            # GENERATE ACTION PLAN
            plan_start = time.time()
            
            prompt = open(f"prompts/tool_selection_prompt.md").read()
            prompt = prompt + f"\n\nUser query:\n{user_query}\n\nUser intent:\n{intent}\n\nRetrieved documents:\n{retrieved_docs}"

            response = self.llm.invoke(prompt)
            text = response.content.strip()

            json_text = self._extract_json(text)

            plan_time = time.time() - plan_start

            if not json_text:
                return {
                    "error": "Failed to generate action plan",
                    "operation": intent
                }

            action_plan = json.loads(json_text)
            return action_plan
            
        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON in action plan",
                "operation": intent
            }
        except Exception as e:
            if journey_id:
                self.journey_logger.log_error(
                    journey_id=journey_id,
                    error_type="ActionPlanError",
                    error_message=str(e),
                    stage="action_plan_generation"
                )
            return {
                "error": str(e),
                "operation": intent
            }


# =====================================================================
# USAGE EXAMPLES IN YOUR MAIN CODE
# =====================================================================

"""
Example 1: Simple usage in mcp_client.py
--------------------------------------------

from logging_config.journey_logger import get_journey_logger

# Get the logger
logger = get_journey_logger()

# Start a journey
journey_id = logger.start_journey(user_query)

# Use it throughout your code
logger.log_intent_detection(journey_id, intent)
logger.log_action_plan(journey_id, action_plan)
logger.log_tool_execution_start(journey_id, tool_name, arguments)
logger.log_tool_execution_result(journey_id, tool_name, result, time_taken)
logger.log_journey_completion(journey_id, final_response, total_time)

# Retrieve journey logs
journey = logger.get_journey_log(journey_id)
print(json.dumps(journey, indent=2))


Example 2: Error handling
--------------------------

try:
    # some operation
except Exception as e:
    logger.log_error(
        journey_id=journey_id,
        error_type="CustomError",
        error_message=str(e),
        stage="operation_name",
        stack_trace=traceback.format_exc()
    )


Example 3: List recent journeys
--------------------------------

logger = get_journey_logger()
recent_journeys = logger.list_journeys(limit=10)

for journey in recent_journeys:
    print(f"ID: {journey['journey_id']}")
    print(f"Query: {journey['query']}")
    print(f"Time: {journey['timestamp']}")
    print("---")


Example 4: View complete journey
--------------------------------

logger = get_journey_logger()
full_journey = logger.get_journey_log("JOURNEY_20260201_143022_5678")

print(json.dumps(full_journey, indent=2))


LOG FILE LOCATIONS
===================

After running your system, you'll see:

logs/
├── audit.log
│   └── Main audit trail with all activities
│
├── requests/
│   └── JOURNEY_20260201_143022_5678.json
│       └── Complete journey trace with all stages
│
├── action_plans/
│   └── JOURNEY_20260201_143022_5678_plan.json
│       └── The generated action plan
│
├── tool_calls/
│   └── JOURNEY_20260201_143022_5678_search_records.json
│       └── Tool execution details
│
└── errors/
    └── JOURNEY_20260201_143022_5678_intent_detection_error.json
        └── Error details if something goes wrong


VIEWING LOGS
============

1. Real-time console output:
   - Each stage prints formatted information
   - Easy to follow the journey as it happens

2. Audit log:
   cat logs/audit.log

3. Journey details (JSON):
   cat logs/requests/JOURNEY_20260201_143022_5678.json | jq .

4. Pretty print a journey:
   python -c "import json; print(json.dumps(json.load(open('logs/requests/JOURNEY_20260201_143022_5678.json')), indent=2))"

"""
