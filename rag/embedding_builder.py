from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "document_store"
VECTORSTORE_DIR = BASE_DIR / "rag" / "vectorstore"


def load_documents() -> List[Document]:
    documents: List[Document] = []

    if not DATA_DIR.exists():
        raise FileNotFoundError(f"DATA_DIR not found: {DATA_DIR}")

    for record_dir in DATA_DIR.iterdir():
        if not record_dir.is_dir():
            continue

        record_id = record_dir.name

        for file in record_dir.iterdir():
            if file.suffix.lower() not in [".txt", ".md"]:
                continue

            text = file.read_text(encoding="utf-8").strip()
            if not text:
                # Skip empty files safely
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "record_id": record_id,
                        "file_name": file.name,
                    },
                )
            )

    return documents


def build_embeddings():
    docs = load_documents()
    print(f"📄 Documents loaded: {len(docs)}")

    if not docs:
        raise ValueError("No non-empty documents found to embed")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
    )

    split_docs = splitter.split_documents(docs)
    print(f"🧩 Chunks created: {len(split_docs)}")

    if not split_docs:
        raise ValueError("Documents loaded, but no chunks were created")

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(
        split_docs,
        embedding_model,
    )

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_DIR))

    print(f"✅ Embedded {len(split_docs)} chunks successfully")
    print(f"📦 Vectorstore saved at: {VECTORSTORE_DIR}")


if __name__ == "__main__":
    build_embeddings()
