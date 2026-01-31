from pathlib import Path
from typing import List, Dict, Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


BASE_DIR = Path(__file__).resolve().parents[1]
VECTORSTORE_DIR = BASE_DIR / "rag" / "vectorstore"


class RAGRetriever:
    def __init__(self):
        if not VECTORSTORE_DIR.exists():
            raise FileNotFoundError(
                f"Vectorstore not found at {VECTORSTORE_DIR}. "
                "Run embedding_builder.py first."
            )

        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vectorstore = FAISS.load_local(
            str(VECTORSTORE_DIR),
            self.embedding_model,
            allow_dangerous_deserialization=True,
        )

    def search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """
        Perform semantic search over embedded documents.
        """
        if not query.strip():
            return []

        results = self.vectorstore.similarity_search(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in results
        ]

    def search_with_score(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """
        Perform semantic search and include similarity score.
        Lower score = better match.
        """
        if not query.strip():
            return []

        results = self.vectorstore.similarity_search_with_score(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
            }
            for doc, score in results
        ]


if __name__ == "__main__":
    retriever = RAGRetriever()

    print("\n🔍 Semantic search test\n")
    results = retriever.search("leave policy", k=2)

    for i, r in enumerate(results, start=1):
        print(f"Result {i}")
        print("Metadata:", r["metadata"])
        print("Content:", r["content"][:200])
        print("-" * 40)
