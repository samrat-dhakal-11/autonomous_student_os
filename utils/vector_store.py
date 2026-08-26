"""Optional ChromaDB vector store for academic documents."""
import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), "data", "chroma_db")


def get_chroma_client() -> chromadb.Client:
    """Initialize and return a persistent ChromaDB client."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return chromadb.Client(
        Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=CHROMA_PERSIST_DIR,
            anonymized_telemetry=False,
        )
    )


def get_or_create_collection(collection_name: str = "academic_docs"):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=collection_name)


def add_documents_to_store(
    texts: List[str],
    ids: List[str],
    metadatas: Optional[List[dict]] = None,
    collection_name: str = "academic_docs",
):
    """Add documents to the vector store."""
    collection = get_or_create_collection(collection_name)
    collection.add(documents=texts, ids=ids, metadatas=metadatas)


def query_store(
    query_text: str,
    n_results: int = 5,
    collection_name: str = "academic_docs",
):
    """Query the vector store for relevant documents."""
    collection = get_or_create_collection(collection_name)
    return collection.query(query_texts=[query_text], n_results=n_results)
