"""Knowledge base service for vector store operations."""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from src.core.config import settings
from src.core.exceptions import KnowledgeBaseError, VectorStoreError
from src.core.logging import logger
from src.schemas.agent import RetrievalResult


class KnowledgeBaseService:
    """Service for knowledge base operations using ChromaDB."""

    def __init__(self):
        self._client: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None
        self._settings = settings.chroma
        self._embedding_model = settings.kb

    def _get_client(self) -> chromadb.Client:
        """Get or create ChromaDB client."""
        if self._client is None:
            persist_dir = Path(self._settings.persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
            )
        return self._client

    def get_collection(self) -> chromadb.Collection:
        """Get or create the KB collection."""
        if self._collection is None:
            client = self._get_client()

            sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.kb.embedding_model or "all-MiniLM-L6-v2"
            )

            self._collection = client.get_or_create_collection(
                name=self._settings.collection_name,
                embedding_function=sentence_transformer_ef,
                metadata={"hnsw:space": "cosine"},
            )

        return self._collection

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Search the knowledge base for relevant documents."""
        try:
            collection = self.get_collection()
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            retrieval_results = []
            if results["documents"] and results["documents"][0]:
                for doc, metadata, distance in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    # Convert distance to similarity score (1 - distance for cosine)
                    similarity = 1 - distance
                    retrieval_results.append(
                        RetrievalResult(
                            content=doc,
                            source=metadata.get("source", "unknown"),
                            similarity_score=similarity,
                        )
                    )

            logger.debug(f"Retrieved {len(retrieval_results)} documents for query")
            return retrieval_results

        except Exception as e:
            logger.error(f"KB search failed: {e}")
            raise VectorStoreError(f"Search failed: {e}") from e

    def add_document(
        self,
        content: str,
        source: str,
        doc_id: str | None = None,
        metadata: dict | None = None,
    ) -> bool:
        """Add a document to the knowledge base."""
        try:
            collection = self.get_collection()

            if doc_id is None:
                import uuid

                doc_id = str(uuid.uuid4())

            doc_metadata = metadata or {}
            doc_metadata["source"] = source

            collection.add(
                documents=[content],
                metadatas=[doc_metadata],
                ids=[doc_id],
            )

            logger.info(f"Added document {doc_id} from {source}")
            return True

        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise KnowledgeBaseError(f"Add document failed: {e}") from e

    def index_documents(self, documents_dir: Path) -> int:
        """Index all documents in a directory."""
        # TODO: Implement document loading and chunking
        pass


def get_kb_service() -> KnowledgeBaseService:
    """Get KB service instance."""
    return KnowledgeBaseService()
