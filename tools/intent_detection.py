"""
Intent Detection Tool for MCP Server.

This tool returns the system prompt for intent classification.
The actual LLM processing is done by the MCP client (e.g., Claude).

WORKFLOW: This is the FIRST tool to be called when a user enters a query.
NEXT STEP: After getting the intent, call the 'generate_action_plan' tool.
"""

import os

# Path to the intent prompt file
INTENT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "intent_prompt.md")


async def get_intent_prompt_impl(user_query: str) -> dict:
    """
    Returns the system prompt and user query for intent detection.
    
    The MCP client (Claude/Copilot/etc.) should use this prompt to classify
    the user's query into one of the intents: CREATE, UPDATE, SEARCH, or HELP.
    
    Args:
        user_query: The user's original request/question.
        
    Returns:
        dict: Contains system_prompt and user_query for the client to process.
              The client should return a JSON with {"intent": "CREATE|UPDATE|SEARCH|HELP"}
    
    NEXT STEP: After detecting intent, call 'generate_action_plan' tool with 
               the user_query and detected intent.
    """
    
    try:
        with open(INTENT_PROMPT_PATH, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        return {
            "error": "Intent prompt file not found",
            "details": f"Expected at: {INTENT_PROMPT_PATH}"
        }
    
    return {
        "system_prompt": system_prompt,
        "user_query": user_query,
        "instruction": "Use the system_prompt to classify the user_query into exactly ONE intent (CREATE, UPDATE, SEARCH, or HELP). Return JSON format: {\"intent\": \"<INTENT>\"}",
        "next_step": "After detecting the intent, call the 'generate_action_plan' tool with the user_query and the detected intent."
    }
