from mcp.server.fastmcp import FastMCP
import requests

mcp =  FastMCP()

BASE_URL = "http://localhost/CMServiceAPI"


@mcp.tool()
async def create_record(action_plan: dict) -> dict:
    """
    Create a record in Content Manager.

    Args:
        action_plan: Action plan with API path and parameters.
    """

    path = action_plan.get("path")
    parameters = action_plan.get("parameters", {})

    # ----------------------------
    # VALIDATION
    # ----------------------------
    if not path:
        return {"error": "Missing API path in action plan"}

    if not parameters:
        return {"error": "Missing parameters for CREATE operation"}

    record_type = parameters.get("RecordRecordType")
    record_title = parameters.get("RecordTitle")

    if not record_type or not record_title:
        return {
            "error": "Missing required fields",
            "required": ["RecordRecordType", "RecordTitle"],
        }

    # ----------------------------
    # BUILD PAYLOAD
    # ----------------------------
    payload = {
        "RecordRecordType": record_type,
        "RecordTitle": record_title,
    }

    # ----------------------------
    # FINAL URL
    # ----------------------------
    url = f"{BASE_URL}/{path}"

    print("\n[MCP] Executing POST request:")
    print(url)
    print("Payload:", payload)

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {
            "error": "POST request failed",
            "details": str(e),
        }
