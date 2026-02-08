"""
Authorization Check Tool for MCP Server.

This tool checks if the authenticated user is authorized to perform 
the detected operation (SEARCH, CREATE, UPDATE) based on their user type.

WORKFLOW: This is STEP 4 - called after:
         1. authenticate_user
         2. validate_email
         3. detect_intent
NEXT STEP: If authorized, call 'generate_action_plan' tool (step 5).
           If NOT authorized, STOP - do not call any other tools.
"""

import requests

# Content Manager API endpoint
CM_API_BASE = "http://10.194.93.112/CMServiceAPI"

# Authorization mapping: user type -> allowed operations
AUTHORIZATION_MAP = {
    "Inquiry User": ["SEARCH"],
    "Administrator": ["SEARCH", "CREATE", "UPDATE"],
    "Records Manager": ["SEARCH", "CREATE", "UPDATE"],
    "Records Co-ordinator": ["SEARCH", "CREATE", "UPDATE"],
    "Knowledge Worker": ["SEARCH", "CREATE", "UPDATE"],
    "Contributor": ["SEARCH", "CREATE"],
}


async def check_authorization_impl(email: str, intent: str) -> dict:
    """
    Check if the user is authorized to perform the detected intent.
    
    This function:
    1. Makes a GET request to Content Manager API to get the user's type
    2. Checks if the user type is allowed to perform the detected operation
    3. Returns authorization result
    
    Args:
        email: The user's email address (from validate_email step).
        intent: The detected intent (CREATE, UPDATE, SEARCH, or HELP).
        
    Returns:
        dict: Contains authorization result.
              If authorized:
              {
                  "authorized": True,
                  "user_type": "Administrator",
                  "intent": "SEARCH",
                  "message": "User is authorized to perform SEARCH",
                  "next_step": "Call 'generate_action_plan' tool..."
              }
              If NOT authorized:
              {
                  "authorized": False,
                  "user_type": "Inquiry User",
                  "intent": "CREATE",
                  "error": "User is not authorized to perform CREATE",
                  "allowed_operations": ["SEARCH"],
                  "instruction": "STOP - Do not call any other tools"
              }
              
    NEXT STEP: If authorized=True, call 'generate_action_plan' tool.
               If authorized=False, STOP - do not proceed with any other tools.
    """
    url = f"{CM_API_BASE}/Location"
    
    params = {
        "q": f"email={email}",
        "format": "json",
        "properties": "userType"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    
    print(f"\n[AUTHORIZATION] Checking user type for: {email}")
    print(f"[AUTHORIZATION] Intent to authorize: {intent}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"[AUTHORIZATION] Response status: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        
        results = data.get("Results", [])
        
        if not results or len(results) == 0:
            return {
                "authorized": False,
                "error": f"User not found with email: {email}",
                "instruction": "STOP - Cannot verify user type. Do not call any other tools."
            }
        
        # Extract user type from response
        user_info = results[0]
        location_user_type = user_info.get("LocationUserType", {})
        
        # Get the StringValue (human-readable user type)
        user_type = location_user_type.get("StringValue", "Unknown")
        
        print(f"[AUTHORIZATION] User type: {user_type}")
        
        # Normalize intent to uppercase for comparison
        intent_upper = intent.upper()
        
        # Handle HELP intent - allow all users to ask for help
        if intent_upper == "HELP":
            return {
                "authorized": True,
                "user_type": user_type,
                "intent": intent_upper,
                "message": f"User is authorized to request HELP",
                "instruction": "User is authorized. Proceed with the help request.",
                "next_step": "Call 'generate_action_plan' tool with the user_query and intent."
            }
        
        # Get allowed operations for this user type
        allowed_operations = AUTHORIZATION_MAP.get(user_type, [])
        
        print(f"[AUTHORIZATION] Allowed operations for {user_type}: {allowed_operations}")
        
        # Check if intent is in allowed operations
        if intent_upper in allowed_operations:
            print(f"[AUTHORIZATION] SUCCESS: User authorized for {intent_upper}")
            return {
                "authorized": True,
                "user_type": user_type,
                "intent": intent_upper,
                "message": f"User is authorized to perform {intent_upper}",
                "instruction": "User is authorized. Proceed with the operation.",
                "next_step": "Call 'generate_action_plan' tool with the user_query and intent."
            }
        else:
            print(f"[AUTHORIZATION] DENIED: User not authorized for {intent_upper}")
            return {
                "authorized": False,
                "user_type": user_type,
                "intent": intent_upper,
                "error": f"User with type '{user_type}' is not authorized to perform {intent_upper}",
                "allowed_operations": allowed_operations,
                "instruction": f"STOP - This user can only perform: {', '.join(allowed_operations) if allowed_operations else 'no operations'}. Do not call any other tools."
            }
            
    except requests.exceptions.HTTPError as e:
        #print(f"[AUTHORIZATION] ERROR: HTTP error: {str(e)}")
        return {
            "authorized": False,
            "error": f"Content Manager API error: {str(e)}",
            "instruction": "STOP - Cannot verify authorization. Do not call any other tools."
        }
    except Exception as e:
        #print(f"[AUTHORIZATION] ERROR: {str(e)}")
        return {
            "authorized": False,
            "error": f"Authorization check failed: {str(e)}",
            "instruction": "STOP - Cannot verify authorization. Do not call any other tools."
        }
