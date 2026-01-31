import requests


class CreateTool:

    BASE_URL = "http://localhost/CMServiceAPI"

    def execute(self, action_plan: dict):
        """
        Execute CREATE Record operation using CMServiceAPI.
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
        # BUILD PAYLOAD (JSON BODY)
        # ----------------------------
        payload = {
            "RecordRecordType": record_type,
            "RecordTitle": record_title,
        }

        # ----------------------------
        # FINAL URL
        # ----------------------------
        url = f"{self.BASE_URL}/{path}"

        print("\nExecuting POST request:")
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
