import requests
from urllib.parse import urlencode

# BASE URLs
# SEARCH (GET)
SEARCH_BASE_URL = "http://10.194.93.112/CMServiceAPI/Record?q="

# UPDATE (POST)
UPDATE_BASE_URL = "http://10.194.93.112/CMServiceAPI/Record"

async def update_record_impl(action_plan: dict) -> dict:
    """
    Update a Content Manager record using an action plan.

    Flow:
    1. GET record using parameters_to_search
    2. Extract Uri from search response
    3. POST update using parameters_to_update
    """

    print("-------------------------------- Inside update_record_impl --------------------------------", flush=True)

    # ------------------------------------------------
    # STEP 1: GET (SEARCH)
    # ------------------------------------------------
    search_params = action_plan.get("parameters_to_search", {})

    if not search_params:
        return {
            "error": "UPDATE failed",
            "details": "parameters_to_search missing in action plan"
        }

    search_query = urlencode(search_params)
    search_url = f"{SEARCH_BASE_URL}{search_query}"

    print("\n[MCP] Executing SEARCH (GET):")
    print(search_url)

    try:
        search_response = requests.get(search_url)
        search_response.raise_for_status()
        search_data = search_response.json()
    except Exception as e:
        return {
            "error": "GET search failed",
            "details": str(e)
        }

    # ------------------------------------------------
    # STEP 2: EXTRACT URI
    # ------------------------------------------------
    results = search_data.get("Results", [])

    if not results:
        return {
            "error": "UPDATE failed",
            "details": "No records found for given search criteria"
        }

    uri = results[0].get("Uri")
    print("----------------------------------------------------------------------------", flush=True)
    print(uri, flush=True)

    if not uri:
        return {
            "error": "UPDATE failed",
            "details": "Uri not found in search response"
        }

    print(f"\n[MCP] Found record Uri: {uri}")

    # ------------------------------------------------
    # STEP 3: BUILD UPDATE BODY
    # ------------------------------------------------
    update_params = action_plan.get("parameters_to_update", {})

    if not update_params:
        return {
            "error": "UPDATE failed",
            "details": "parameters_to_update missing in action plan"
        }

    # Remove empty / placeholder values
    update_body = {
        "Uri": uri
    }

    for key, value in update_params.items():
        if value not in ("", None, "<value_if_provided>"):
            update_body[key] = value

    print("\n[MCP] Executing UPDATE (POST) with body:", flush=True)
    print(update_body, flush=True)

    # ------------------------------------------------
    # STEP 4: POST (UPDATE)
    # ------------------------------------------------
    try:
        update_response = requests.post(UPDATE_BASE_URL, json=update_body)
        update_response.raise_for_status()
        return update_response.json()

    except Exception as e:
        return {
            "error": "POST update failed",
            "details": str(e)
        }
