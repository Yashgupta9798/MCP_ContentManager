import requests
from urllib.parse import urlencode


class SearchTool:

    BASE_URL = "http://localhost/CMServiceAPI"

    def execute(self, action_plan: dict):

        path = action_plan.get("path")
        parameters = action_plan.get("parameters", {})

        # ----------------------------
        # DEFAULT PARAMETERS
        # ----------------------------
        if not parameters:
            parameters = {"q": "all"}

        # ----------------------------
        # BUILD QUERY STRING
        # ----------------------------

        # Convert parameters dict to query string
        # Example:
        # RecordNumber=26/1&format=json&properties=NameString

        query_string = urlencode(parameters)

        # ----------------------------
        # FINAL URL
        # ----------------------------
        url = f"{self.BASE_URL}/{path}?{query_string}"

        print("\nExecuting GET request:")
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
