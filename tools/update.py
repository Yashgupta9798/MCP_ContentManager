"""
Update Record Tool for Content Manager MCP Server.

PURPOSE: Update existing records in the Content Manager system.

WHEN TO USE: Call this tool when the action plan has operation="UPDATE".
             This tool should be called AFTER 'generate_action_plan' tool.

INPUT: An action_plan dict with the following structure:
{
    "path": "Record/",
    "method": "POST",
    "parameters_to_search": {
        "number": "<record_number>",      # optional - to identify record
        "combinedtitle": "<title>",       # optional - to identify record
        "type": "Document|Folder",        # optional
        "createdon": "mm/dd/yyyy",        # optional
        "editstatus": "checkin|checkout", # optional
        "format": "json",
        "properties": "NameString"
    },
    "parameters_to_update": {
        "RecordNumber": "<new_number>",       # optional
        "RecordTitle": "<new_title>",         # optional
        "RecordRecordType": "Document|Folder",# optional
        "RecordDateCreated": "mm/dd/yyyy",    # optional
        "RecordEditState": "<state>"          # optional
    },
    "operation": "UPDATE"
}

OUTPUT: JSON response from Content Manager API with updated record details.

WORKFLOW POSITION: This is typically the FINAL tool in an UPDATE workflow.
                   validateSession -> detect_intent -> generate_action_plan -> update_record

NOTE: The tool first searches for the record using parameters_to_search,
      then updates it with parameters_to_update.
"""

import requests
from urllib.parse import urlencode

# BASE URLs
# SEARCH (GET)
SEARCH_BASE_URL = "http://10.194.93.112/CMServiceAPI/Record?q="
# SEARCH_BASE_URL = "https://cmbeta.in/CMServiceAPI/Record?q="

# UPDATE (POST)
UPDATE_BASE_URL = "http://10.194.93.112/CMServiceAPI/Record"
# UPDATE_BASE_URL = "https://cmbeta.in/CMServiceAPI/Record"


async def update_record_impl(
    action_plan: dict,

) -> dict:
    """
    Update a Content Manager record using an action plan.
    
    This tool first searches for a record, then updates it with new values.
    It should be called AFTER the 'generate_action_plan' tool has created an UPDATE action plan.

  
    Flow:
    1. GET record using parameters_to_search
    2. Extract Uri from search response
    3. POST update using parameters_to_update
    
    Args:
        action_plan: A dict containing:
            - path: "Record/" (API endpoint path)
            - method: "POST"
            - parameters_to_search: Search criteria to find the record to update
            - parameters_to_update: New values to apply to the record
            - operation: "UPDATE"
     
    Returns:
        dict: JSON response from Content Manager API with updated record details.
    
    WORKFLOW: This is the FINAL tool for UPDATE operations.
              Previous steps: validateSession -> detect_intent -> 
                             check_authorization -> generate_action_plan -> update_record
     
    """
    
    # ------------------------------------------------
    # STEP 1: GET (SEARCH)
    # ------------------------------------------------
    search_params = action_plan.get("parameters_to_search", {})

    if not search_params:
        return {
            "error": "UPDATE failed",
            "details": "parameters_to_search missing in action plan",
            "operation": "UPDATE"
        }

    search_query = urlencode(search_params)
    search_url = f"{SEARCH_BASE_URL}{search_query}"

    print(search_url)

    try:
        search_response = requests.get(search_url)
        search_response.raise_for_status()
        search_data = search_response.json()
    except Exception as e:
        return {
            "error": "GET search failed",
            "details": str(e),
            "operation": "UPDATE"
        }

    # ------------------------------------------------
    # STEP 2: EXTRACT URI
    # ------------------------------------------------
    results = search_data.get("Results", [])

    if not results:
        return {
            "error": "UPDATE failed",
            "details": "No records found for given search criteria",
            "operation": "UPDATE"
        }

    uri = results[0].get("Uri")
    print("----------------------------------------------------------------------------", flush=True)

    if not uri:
        return {
            "error": "UPDATE failed",
            "details": "Uri not found in search response",
            "operation": "UPDATE"
        }

    # ------------------------------------------------
    # STEP 3: BUILD UPDATE BODY
    # ------------------------------------------------
    update_params = action_plan.get("parameters_to_update", {})

    if not update_params:
        return {
            "error": "UPDATE failed",
            "details": "parameters_to_update missing in action plan",
            "operation": "UPDATE"
        }

    # Remove empty / placeholder values
    update_body = {
        "Uri": uri
    }

    for key, value in update_params.items():
        if value not in ("", None, "<value_if_provided>"):
            update_body[key] = value

    # ------------------------------------------------
    # STEP 4: POST (UPDATE)
    # ------------------------------------------------
    try:
        update_response = requests.post(UPDATE_BASE_URL, json=update_body)
        update_response.raise_for_status()
        result = update_response.json()
       
        result["operation"] = "UPDATE"
        
        return result

    except Exception as e:
        return {
            "error": "POST update failed",
            "details": str(e),
            "operation": "UPDATE"
        }
