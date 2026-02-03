import requests
from urllib.parse import urlencode

# BASE_URL = "http://localhost/CMServiceAPI/Record?q="
BASE_URL = "http://10.194.93.112/CMServiceAPI/Record?q="


async def search_records_impl(action_plan: dict) -> dict:
    """
    Search records in Content Manager.
    MCP-style implementation: accepts action_plan dict.
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
