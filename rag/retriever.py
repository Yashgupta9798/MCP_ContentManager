from pathlib import Path
from typing import List, Dict, Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


BASE_DIR = Path(__file__).resolve().parents[1]
VECTORSTORE_DIR = BASE_DIR / "rag" / "vectorstore" / "tools"


class ToolRetriever:
    def __init__(self):
        if not VECTORSTORE_DIR.exists():
            raise FileNotFoundError(
                "Tool vectorstore not found. Run embedding_builder_tools.py first."
            )

        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vectorstore = FAISS.load_local(
            str(VECTORSTORE_DIR),
            self.embeddings,
            allow_dangerous_deserialization=True
        )

    def match(self, query: str, k: int = 2) -> List[Dict[str, Any]]:
        """
        Embed user query and return top-k matching tools.
        """
        if not query.strip():
            return []

        results = self.vectorstore.similarity_search_with_score(query, k=k)

        return [
            {
                "tool": doc.metadata["tool"],
                "description": doc.page_content,
                "score": score,  # lower = better
            }
            for doc, score in results
        ]


if __name__ == "__main__":
    retriever = ToolRetriever()

    query = "I want to update the status of a record"
    matches = retriever.match(query)

    print("\n🔍 Tool matches:\n")
    for m in matches:
        print(m)
