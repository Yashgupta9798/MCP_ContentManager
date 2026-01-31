import os
import json
from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "document_store"
VECTORSTORE_DIR = BASE_DIR / "rag" / "vectorstore"


def load_documents() -> List[Document]:
    documents = []

    for record_dir in DATA_DIR.iterdir():
        if not record_dir.is_dir():
            continue

        record_id = record_dir.name

        for file in record_dir.iterdir():
            if file.suffix not in [".txt", ".md"]:
                continue

            text = file.read_text(encoding="utf-8")

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "record_id": record_id,
                        "file_name": file.name
                    }
                )
            )

    return documents


def build_embeddings():
    docs = load_documents()

    if not docs:
        raise ValueError("No documents found to embed")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    split_docs = splitter.split_documents(docs)

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(
        split_docs,
        embedding_model
    )

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_DIR))

    print(f"✅ Embedded {len(split_docs)} chunks successfully")


if __name__ == "__main__":
    build_embeddings()
