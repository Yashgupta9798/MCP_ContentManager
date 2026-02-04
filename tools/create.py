"""
Create Record Tool for Content Manager MCP Server.

PURPOSE: Create new records in the Content Manager system.

WHEN TO USE: Call this tool when the action plan has operation="CREATE".
             This tool should be called AFTER 'generate_action_plan' tool.

INPUT: An action_plan dict with the following structure:
{
    "path": "Record/",
    "method": "POST",
    "parameters": {
        "RecordRecordType": "Document|Folder",  # required
        "RecordTitle": "<title>",               # required
        "RecordNumber": "<number>",             # optional
        "RecordDateCreated": "mm/dd/yyyy",      # optional
        "RecordEditState": "<state>"            # optional
    },
    "operation": "CREATE"
}

OUTPUT: JSON response from Content Manager API with created record details.

WORKFLOW POSITION: This is typically the FINAL tool in a CREATE workflow.
                   detect_intent -> generate_action_plan -> create_record

NOTE: RecordTitle and RecordRecordType are MANDATORY fields for record creation.
"""

import requests

# BASE_URL = "http://localhost/CMServiceAPI/Record/"
# BASE_URL = "http://10.194.93.112/CMServiceAPI/Record?q="
BASE_URL = "https://cmbeta.in/CMServiceAPI/Record?q="

async def create_record_impl(action_plan: dict) -> dict:
    """
    Create a record in Content Manager.
    
    This tool executes a POST request to the Content Manager API to create a new record.
    It should be called AFTER the 'generate_action_plan' tool has created a CREATE action plan.
    
    Args:
        action_plan: A dict containing:
            - path: "Record/" (API endpoint path)
            - method: "POST"
            - parameters: Record parameters including:
                - RecordRecordType: "Document" or "Folder" (REQUIRED)
                - RecordTitle: The title of the record (REQUIRED)
                - RecordNumber, RecordDateCreated, RecordEditState (optional)
            - operation: "CREATE"
            
    Returns:
        dict: JSON response from Content Manager API with created record details.
    
    WORKFLOW: This is the FINAL tool for CREATE operations.
              Previous steps: detect_intent -> generate_action_plan -> create_record
              
    IMPORTANT: RecordTitle and RecordRecordType are MANDATORY for creating a record.
    """
    print("------------Entering Record Title, Record Type is mandatory to create a record--------------", flush = True)
    parameters = action_plan.get("parameters", {})

    if not parameters:
        return {"error": "parameters required for CREATE", "details": "action_plan.parameters is empty"}

    print("\n[MCP] Executing POST request (CREATE):")
    print(BASE_URL)
    print(parameters)
    
    try:
        title = parameters.RecordTitle
        type = parameters.RecordRecordType
    except:
        print("*Please Enter the type and title of record")

    try:
        response = requests.post(BASE_URL, json=parameters)
        response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"status_code": response.status_code, "text": response.text}
    except Exception as e:
        return {
            "error": "POST request failed (CREATE)",
            "details": str(e)
        }
