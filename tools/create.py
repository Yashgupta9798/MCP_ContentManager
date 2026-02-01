import requests

BASE_URL = "http://localhost/CMServiceAPI/Record/"


async def create_record_impl(action_plan: dict) -> dict:
    """
    Create a record in Content Manager.
    MCP-style implementation: accepts action_plan dict with method POST and parameters.
    """
    parameters = action_plan.get("parameters", {})

    if not parameters:
        return {"error": "parameters required for CREATE", "details": "action_plan.parameters is empty"}

    print("\n[MCP] Executing POST request (CREATE):")
    print(BASE_URL)
    print(parameters)

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
