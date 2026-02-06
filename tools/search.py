"""
Search Records Tool for Content Manager MCP Server.

PURPOSE: Execute search queries against the Content Manager API to find/retrieve records.

WHEN TO USE: Call this tool when the action plan has operation="SEARCH".
             This tool should be called AFTER 'generate_action_plan' tool.

INPUT: An action_plan dict with the following structure:
{
    "path": "Record/",
    "method": "GET", 
    "parameters": {
        "number": "<record_number>",      # optional
        "combinedtitle": "<title>",       # optional
        "type": "Document|Folder",        # optional
        "createdon": "mm/dd/yyyy",        # optional
        "editstatus": "checkin|checkout", # optional
        "format": "json",
        "properties": "NameString"
    },
    "operation": "SEARCH"
}

OUTPUT: JSON response from Content Manager API with search results.

WORKFLOW POSITION: This is typically the FINAL tool in a SEARCH workflow.
                   detect_intent -> generate_action_plan -> search_records
"""

import requests
from urllib.parse import urlencode

# BASE_URL = "http://localhost/CMServiceAPI/Record?q="
BASE_URL = "http://10.194.93.112/CMServiceAPI/Record?q="
# BASE_URL = "https://cmbeta.in/CMServiceAPI/Record?q="


async def search_records_impl(action_plan: dict) -> dict:
    """
    Search records in Content Manager.
    
    This tool executes a GET request to the Content Manager API to search for records.
    It should be called AFTER the 'generate_action_plan' tool has created a SEARCH action plan.
    
    Args:
        action_plan: A dict containing:
            - path: "Record/" (API endpoint path)
            - method: "GET"
            - parameters: Search parameters (number, combinedtitle, type, createdon, editstatus, format, properties)
            - operation: "SEARCH"
            
    Returns:
        dict: JSON response from Content Manager API containing search results.
              Results are in the "Results" array with record details.
    
    WORKFLOW: This is the FINAL tool for SEARCH operations.
              Previous steps: detect_intent -> generate_action_plan -> search_records
    """
    print("-------------------------------- Inside search_records_impl --------------------------------", flush=True)
    parameters = action_plan.get("parameters", {})

    if not parameters:
        query = "all"
    else:
        query = urlencode(parameters)

    url = f"{BASE_URL}{query}"

    print("\n[MCP] Executing GET request:")
    print(url)

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {
            "error": "GET request failed",
            "details": str(e)
        }



# import requests
# from urllib.parse import urlencode


# class SearchTool:

#     BASE_URL = "http://localhost/CMServiceAPI/Record?q="

#     def execute(self, action_plan: dict):

#         path = action_plan.get("path")
#         parameters = action_plan.get("parameters", {})
        
#         to_append = ""
#         # ----------------------------
#         # IF NO PARAMETERS, FETCH ALL
#         # ----------------------------
#         if not parameters:
#             to_append += "all"
#         else:
#             to_append = urlencode(parameters)

#         # ----------------------------
#         # FINAL URL
#         # ----------------------------
#         url = f"{self.BASE_URL}{to_append}"
        
#         print("\nExecuting GET request:")
#         print(url)

#         try:
#             response = requests.get(url)

#             response.raise_for_status()

#             return response.json()

#         except Exception as e:
#             return {
#                 "error": "GET request failed",
#                 "details": str(e)
#             }
