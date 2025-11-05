"""
R2R Client Wrapper for Producer AI Agent
Provides high-level interface to R2R RAG system
"""

from typing import List, Dict, Any, Optional, BinaryIO
import httpx
from pydantic import BaseModel, Field
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class Document(BaseModel):
    """Document model for R2R ingestion"""
    id: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    title: Optional[str] = None


class SearchResult(BaseModel):
    """Search result from R2R"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGResponse(BaseModel):
    """RAG response with generated answer and sources"""
    answer: str
    sources: List[SearchResult]
    completion_id: Optional[str] = None


class R2RClient:
    """Client for interacting with R2R API"""

    def __init__(
        self,
        base_url: str = "http://localhost:7272",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize R2R client

        Args:
            base_url: Base URL of R2R API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def health_check(self) -> Dict[str, Any]:
        """Check R2R service health"""
        response = await self.client.get(
            f"{self.base_url}/v2/health",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def ingest_documents(
        self,
        documents: List[Document],
        collection_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest documents into R2R

        Args:
            documents: List of documents to ingest
            collection_id: Optional collection ID for organizing documents

        Returns:
            Ingestion result with document IDs
        """
        payload = {
            "documents": [doc.model_dump() for doc in documents]
        }
        if collection_id:
            payload["collection_id"] = collection_id

        response = await self.client.post(
            f"{self.base_url}/v2/ingest",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        logger.info(f"Ingested {len(documents)} documents")
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def ingest_files(
        self,
        files: List[tuple[str, BinaryIO]],
        collection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest files into R2R (PDF, TXT, JSON, etc.)

        Args:
            files: List of (filename, file_object) tuples
            collection_id: Optional collection ID
            metadata: Optional metadata for files

        Returns:
            Ingestion result
        """
        files_data = [
            ("files", (filename, file_obj))
            for filename, file_obj in files
        ]

        data = {}
        if collection_id:
            data["collection_id"] = collection_id
        if metadata:
            data["metadata"] = metadata

        response = await self.client.post(
            f"{self.base_url}/v2/ingest_files",
            headers={k: v for k, v in self.headers.items() if k != "Content-Type"},
            files=files_data,
            data=data
        )
        response.raise_for_status()
        result = response.json()

        logger.info(f"Ingested {len(files)} files")
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        collection_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search documents using hybrid search (semantic + keyword)

        Args:
            query: Search query
            limit: Maximum number of results
            filters: Optional metadata filters
            collection_id: Optional collection to search in

        Returns:
            List of search results
        """
        payload = {
            "query": query,
            "limit": limit
        }
        if filters:
            payload["filters"] = filters
        if collection_id:
            payload["collection_id"] = collection_id

        response = await self.client.post(
            f"{self.base_url}/v2/search",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        results = response.json()

        search_results = [
            SearchResult(
                id=r.get("id", ""),
                content=r.get("text", ""),
                score=r.get("score", 0.0),
                metadata=r.get("metadata", {})
            )
            for r in results.get("results", [])
        ]

        logger.info(f"Search returned {len(search_results)} results for query: {query}")
        return search_results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def rag(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_id: Optional[str] = None,
        stream: bool = False
    ) -> RAGResponse:
        """
        Perform RAG (Retrieval-Augmented Generation)

        Args:
            query: User query
            limit: Number of context documents to retrieve
            filters: Optional metadata filters
            collection_id: Optional collection to search in
            stream: Whether to stream the response

        Returns:
            RAG response with answer and sources
        """
        payload = {
            "query": query,
            "rag_generation_config": {
                "stream": stream,
                "max_tokens": 1024
            },
            "search_limit": limit
        }
        if filters:
            payload["search_filters"] = filters
        if collection_id:
            payload["collection_id"] = collection_id

        response = await self.client.post(
            f"{self.base_url}/v2/rag",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        # Parse response
        answer = result.get("completion", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        sources = [
            SearchResult(
                id=s.get("id", ""),
                content=s.get("text", ""),
                score=s.get("score", 0.0),
                metadata=s.get("metadata", {})
            )
            for s in result.get("search_results", {}).get("results", [])
        ]

        rag_response = RAGResponse(
            answer=answer,
            sources=sources,
            completion_id=result.get("completion", {}).get("id")
        )

        logger.info(f"RAG query completed: {query}")
        return rag_response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_collection(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new collection

        Args:
            name: Collection name
            description: Optional description

        Returns:
            Collection info
        """
        payload = {
            "name": name
        }
        if description:
            payload["description"] = description

        response = await self.client.post(
            f"{self.base_url}/v2/collections",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        logger.info(f"Created collection: {name}")
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections"""
        response = await self.client.get(
            f"{self.base_url}/v2/collections",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("results", [])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document by ID"""
        response = await self.client.delete(
            f"{self.base_url}/v2/documents/{document_id}",
            headers=self.headers
        )
        response.raise_for_status()
        result = response.json()

        logger.info(f"Deleted document: {document_id}")
        return result

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
