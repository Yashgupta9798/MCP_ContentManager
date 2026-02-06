"""
Email Validator Tool for MCP Server.

This tool validates that an authenticated user's email exists in Content Manager.

WORKFLOW: This is the SECOND tool to be called after 'authenticate_user'.
NEXT STEP: If validation succeeds, proceed to 'detect_intent' tool.
           If validation fails, STOP - do not call any other tools.
"""

import requests

# Content Manager API endpoint
# CM_API_BASE = "https://cmbeta.in/CMServiceAPI"
CM_API_BASE = "http://10.194.93.112/CMServiceAPI"


async def validate_email_impl(email: str) -> dict:
    """
    Validate that the user's email exists in Content Manager.
    
    This function makes a GET request to the Content Manager API to verify
    the email exists as a Location (user) in the system.
    
    Args:
        email: The email address to validate (from authentication).
        
    Returns:
        dict: Contains validation result.
              If valid:
              {
                  "valid": True,
                  "message": "Sign in successfully",
                  "user_name": "User Name",
                  "user_uri": 123,
                  "next_step": "Call 'detect_intent' tool..."
              }
              If invalid:
              {
                  "valid": False,
                  "error": "No user exists with this email",
                  "instruction": "STOP - Do not call any other tools"
              }
              
    NEXT STEP: If valid, call 'detect_intent' tool with the user's query.
               If invalid, STOP - do not proceed with any other tools.
    """
    url = f"{CM_API_BASE}/Location?"
    
    params = {
        "q": f"email={email}",
        "format": "json",
        "properties": "NameString"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    
    print(f"\n[EMAIL_VALIDATOR] Checking if email exists in Content Manager: {email}")

    # response = requests.get(url, params=params, headers=headers)
    # if(len(response.get("Results")) == 0):
    #     return "No user found with this email"
    # return "User Found now call intent"
    response = requests.get(url, params=params, headers=headers)
    try:
        response.raise_for_status()
        data = response.json()
        results = data.get("Results", [])
        if len(results) == 0:
            return {
                "valid": False,
                "error": f"No user exists with this email: {email}",
                "instruction": "STOP - Do not call any other tools."
            }

        user_info = results[0]
        return {
            "valid": True,
            "message": "Sign in successfully",
            "user_name": user_info.get("NameString", "Unknown"),
            "user_uri": user_info.get("Uri"),
            "next_step": "Call 'detect_intent' tool with the user's query."
        }

    except requests.exceptions.HTTPError as e:
        return {"valid": False, "error": f"HTTP error: {e}", "instruction": "STOP"}
    except Exception as e:
        return {"valid": False, "error": str(e), "instruction": "STOP"}
    
    # try:
    #     response = requests.get(url, params=params, headers=headers)
    #     print(f"[EMAIL_VALIDATOR] Response status: {response.status_code}")
        
    #     if response.status_code == 401:
    #         return {
    #             "valid": False,
    #             "error": "Unauthorized access to Content Manager API",
    #             "instruction": "STOP - Authentication with Content Manager failed. Do not call any other tools."
    #         }
        
    #     response.raise_for_status()
    #     data = response.json()
        
    #     # Check if user exists in results
    #     results = data.get("Results", [])
        
    #     if results and len(results) > 0:
    #         user_info = results[0]
    #         user_name = user_info.get("NameString", "Unknown")
    #         user_uri = user_info.get("Uri")
            
    #         print(f"[EMAIL_VALIDATOR] SUCCESS: User found: {user_name} (URI: {user_uri})")
            
    #         return {
    #             "valid": True,
    #             "message": "Sign in successfully",
    #             "user_name": user_name,
    #             "user_uri": user_uri,
    #             "email": email,
    #             "instruction": "User is validated. You may now proceed with the user's query.",
    #             "next_step": "Call 'detect_intent' tool with the user's original query."
    #         }
    #     else:
    #         print(f"[EMAIL_VALIDATOR] ERROR: No user found with email: {email}")
            
    #         return {
    #             "valid": False,
    #             "error": f"No user exists with this email: {email}",
    #             "instruction": "STOP - This user is not registered in Content Manager. Do not call any other tools."
    #         }
            
    # except requests.exceptions.HTTPError as e:
    #     print(f"[EMAIL_VALIDATOR] ERROR: HTTP error: {str(e)}")
    #     return {
    #         "valid": False,
    #         "error": f"Content Manager API error: {str(e)}",
    #         "instruction": "STOP - Cannot validate user. Do not call any other tools."
    #     }
    # except Exception as e:
    #     print(f"[EMAIL_VALIDATOR] ERROR: {str(e)}")
    #     return {
    #         "valid": False,
    #         "error": f"Email validation failed: {str(e)}",
    #         "instruction": "STOP - Cannot validate user. Do not call any other tools."
    #     }
