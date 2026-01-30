import os
import json
import re
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace


class IntentRouter:

    def __init__(self):
        endpoint = HuggingFaceEndpoint(
            repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
            huggingfacehub_api_token=os.getenv("HF_TOKEN"),
            temperature=0,
            max_new_tokens=100
        )

        self.llm = ChatHuggingFace(llm=endpoint)

    def _extract_json(self, text: str):
        match = re.search(r"\{[\s\S]*?\}", text)
        return match.group() if match else None

    def detect_intent(self, user_query: str):

        prompt = open("prompts/intent_prompt.md").read()
        prompt = prompt + f"\n\nUser query:\n{user_query}"

        response = self.llm.invoke(prompt)
        text = response.content.strip()

        json_text = self._extract_json(text)

        if not json_text:
            return "UNKNOWN"

        try:
            data = json.loads(json_text)
            return data.get("intent", "UNKNOWN")
        except:
            return "UNKNOWN"
