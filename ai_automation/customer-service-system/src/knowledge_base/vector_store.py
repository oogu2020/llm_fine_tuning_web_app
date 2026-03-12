"""ChromaDB vector store wrapper."""

from pathlib import Path
from typing import Iterator

import chromadb
from chromadb.utils import embedding_functions

from src.core.config import settings
from src.core.exceptions import VectorStoreError
from src.core.logging import logger
from src.schemas.agent import RetrievalResult


class ChromaVectorStore:
    """Wrapper for ChromaDB vector store operations."""

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
    ):
        self.persist_dir = Path(persist_dir or settings.chroma.persist_dir)
        self.collection_name = collection_name or settings.chroma.collection_name
        self.embedding_model = embedding_model or settings.kb.embedding_model

        self._client: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None

    def _init_client(self) -> chromadb.Client:
        """Initialize ChromaDB client."""
        if self._client is None:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
            )
        return self._client

    def get_collection(self) -> chromadb.Collection:
        """Get or create collection."""
        if self._collection is None:
            client = self._init_client()

            # Use sentence transformers embedding function
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model or "all-MiniLM-L6-v2"
            )

            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )

        return self._collection

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: dict | None = None,
    ) -> list[RetrievalResult]:
        """Search for similar documents."""
        try:
            collection = self.get_collection()
            results = collection.query(
                query_texts=[query],
                n_results=k,
                where=filter_dict,
                include=["documents", "metadatas", "distances"],
            )

            retrieval_results = []
            if results["documents"] and results["documents"][0]:
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    retrieval_results.append(
                        RetrievalResult(
                            content=doc,
                            source=meta.get("source", "unknown"),
                            similarity_score=1 - dist,  # Convert distance to similarity
                        )
                    )

            logger.debug(f"Retrieved {len(retrieval_results)} documents")
            return retrieval_results

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise VectorStoreError(f"Search failed: {e}") from e

    def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str] | None = None,
    ) -> None:
        """Add texts to the vector store."""
        try:
            collection = self.get_collection()

            if ids is None:
                import uuid

                ids = [str(uuid.uuid4()) for _ in texts]

            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"Added {len(texts)} documents to collection")

        except Exception as e:
            logger.error(f"Failed to add texts: {e}")
            raise VectorStoreError(f"Add texts failed: {e}") from e

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        try:
            client = self._init_client()
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise VectorStoreError(f"Delete failed: {e}") from e

    def count(self) -> int:
        """Get number of documents in collection."""
        try:
            collection = self.get_collection()
            return collection.count()
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0


def get_vector_store() -> ChromaVectorStore:
    """Get vector store instance."""
    return ChromaVectorStore()
