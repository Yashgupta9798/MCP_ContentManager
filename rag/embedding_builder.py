from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


BASE_DIR = Path(__file__).resolve().parents[1]
API_DOCS_PATH = BASE_DIR / "data" / "api_docs.md"
VECTORSTORE_DIR = BASE_DIR / "rag" / "vectorstore" / "tools"


def load_tool_docs() -> List[Document]:
    if not API_DOCS_PATH.exists():
        raise FileNotFoundError(f"api_docs.md not found at {API_DOCS_PATH}")

    raw_text = API_DOCS_PATH.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise ValueError("api_docs.md is empty")

    docs: List[Document] = []

    # Expecting markdown like:
    # ## create
    # description...
    sections = raw_text.split("## ")[1:]

    for section in sections:
        lines = section.splitlines()
        tool_name = lines[0].strip()
        description = "\n".join(lines[1:]).strip()

        if not description:
            continue

        docs.append(
            Document(
                page_content=description,
                metadata={"tool": tool_name}
            )
        )

    return docs


def build_tool_embeddings():
    docs = load_tool_docs()
    print(f"🛠 Tool docs loaded: {len(docs)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30,
    )
    chunks = splitter.split_documents(docs)
    print(f"🧩 Tool chunks created: {len(chunks)}")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(chunks, embeddings)

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_DIR))

    print(f"✅ Tool embeddings stored at {VECTORSTORE_DIR}")


if __name__ == "__main__":
    build_tool_embeddings()
