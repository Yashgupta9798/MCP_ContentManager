"""
Action Plan Generator Tool for MCP Server.

This tool returns the system prompt for generating action plans.
The actual LLM processing is done by the MCP client (e.g., Claude).

WORKFLOW: This is STEP 5 - called after:
         1. authenticate_user
         2. validate_email
         3. detect_intent
         4. check_authorization
NEXT STEP: After generating the action plan, call the appropriate tool (STEP 6)
           based on the operation in the action plan:
           - If operation is "SEARCH" -> call 'search_records' tool
           - If operation is "CREATE" -> call 'create_record' tool  
           - If operation is "UPDATE" -> call 'update_record' tool
"""

import os
from rag.retriever import ToolRetriever

# Path to the tool selection prompt file
TOOL_SELECTION_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "tool_selection_prompt.md")


async def generate_action_plan_impl(user_query: str, intent: str) -> dict:
    """
    Returns the system prompt and context for action plan generation.
    
    The MCP client (Claude/Copilot/etc.) should use this prompt to generate
    a structured action plan JSON based on the user's query and detected intent.
    
    Args:
        user_query: The user's original request/question.
        intent: The detected intent (CREATE, UPDATE, SEARCH, or HELP).
        
    Returns:
        dict: Contains system_prompt, user_query, intent, and retrieved_docs
              for the client to process and generate an action plan JSON.
    
    NEXT STEP: After generating the action plan, call the appropriate tool:
               - "SEARCH" operation -> call 'search_records' tool with the action_plan
               - "CREATE" operation -> call 'create_record' tool with the action_plan
               - "UPDATE" operation -> call 'update_record' tool with the action_plan
    """
    
    try:
        with open(TOOL_SELECTION_PROMPT_PATH, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        return {
            "error": "Tool selection prompt file not found",
            "details": f"Expected at: {TOOL_SELECTION_PROMPT_PATH}"
        }
    
    # Get relevant documentation using RAG
    try:
        retrieved_docs = ToolRetriever().match(user_query)
    except Exception as e:
        retrieved_docs = f"(RAG retrieval failed: {str(e)})"
    
    return {
        "system_prompt": system_prompt,
        "user_query": user_query,
        "intent": intent,
        "retrieved_docs": str(retrieved_docs),
        "instruction": (
            "Use the system_prompt to generate a valid JSON action plan based on the user_query and intent. "
            "Follow the exact JSON structure specified in the prompt for the given intent (SEARCH, CREATE, or UPDATE). "
            "Return ONLY the JSON action plan, no explanations."
        ),
        "next_step": (
            "After generating the action plan JSON, call the appropriate tool based on the 'operation' field: "
            "- If operation is 'SEARCH' -> call 'search_records' tool with the action_plan as parameter. "
            "- If operation is 'CREATE' -> call 'create_record' tool with the action_plan as parameter. "
            "- If operation is 'UPDATE' -> call 'update_record' tool with the action_plan as parameter."
        )
    }


# Legacy class kept for backward compatibility (not used in MCP flow)
class ActionPlanGenerator:
    """
    Legacy class - kept for backward compatibility.
    For MCP flow, use generate_action_plan_impl() instead.
    """
    
    def __init__(self):
        pass

    def run(self, user_query: str, intent: str):
        """
        Legacy method - now just returns a message to use the async implementation.
        """
        return {
            "message": "Use generate_action_plan_impl() for MCP flow",
            "user_query": user_query,
            "intent": intent
        }