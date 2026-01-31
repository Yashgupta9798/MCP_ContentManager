from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS

BASE_DIR = Path(__file__).resolve().parents[1]
VECTORSTORE_DIR = BASE_DIR / "rag" / "vectorstore"


class RAGRetriever:
    def __init__(self):
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vectorstore = FAISS.load_local(
            str(VECTORSTORE_DIR),
            self.embedding_model,
            allow_dangerous_deserialization=True
        )

    def search(self, query: str, k: int = 4):
        results = self.vectorstore.similarity_search(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]


if __name__ == "__main__":
    retriever = RAGRetriever()
    res = retriever.search("leave policy")
    print(res)
