import os
import json
import re
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from rag.retriever import ToolRetriever

load_dotenv()


class ActionPlanGeneratorWrite:

    def __init__(self):
        endpoint = HuggingFaceEndpoint(
            repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
            huggingfacehub_api_token=os.getenv("HF_TOKEN"),
            temperature=0,
            max_new_tokens=300
        )

        self.llm = ChatHuggingFace(llm=endpoint)

    def _extract_json(self, text: str):
        match = re.search(r"\{[\s\S]*?\}", text)
        return match.group() if match else None

    def run(self, user_query: str, intent: str):
        """
        Generate action plan for SEARCH/HELP operations
        
        Args:
            user_query: The user's request
            intent: The detected intent (SEARCH OR HELP)
            
        Returns:
            dict: The action plan as a JSON object
        """
        
        # retrieved_docs = rag(user_query)
        retrieved_docs = ToolRetriever().match(user_query)
        print(retrieved_docs)
        prompt = open(f"prompts/tool_selection_prompt.md").read()
        prompt = prompt + f"\n\nUser query:\n{user_query}\n\nUser intent:\n{intent}\n\nRetrieved documents:\n{retrieved_docs}"

        response = self.llm.invoke(prompt)
        text = response.content.strip()

        json_text = self._extract_json(text)

        if not json_text:
            return {
                "error": "Failed to generate action plan",
                "operation": intent
            }

        try:
            action_plan = json.loads(json_text)
            return action_plan
        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON in action plan",
                "operation": intent
            }