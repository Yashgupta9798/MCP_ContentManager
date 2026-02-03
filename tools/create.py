import requests

# BASE_URL = "http://localhost/CMServiceAPI/Record/"
BASE_URL = "http://10.194.93.112/CMServiceAPI/Record?q="

async def create_record_impl(action_plan: dict) -> dict:
    """
    Create a record in Content Manager.
    MCP-style implementation: accepts action_plan dict with method POST and parameters.
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
