"""
FastAPI server integrating R2R, n8n, Auth0, and Music Generation
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging

from src.r2r_client import R2RClient, Document, SearchResult, RAGResponse
from src.auth0_middleware import (
    Auth0Config,
    Auth0User,
    get_current_user,
    verify_token
)
from src.music_fsm import MusicGenerationFSM
from src.api_client import AIMusicAPIClient
from src.models import MusicGenerationRequest
from src.config import load_config
from src.logger import setup_logging

# Load environment
load_dotenv()

# Setup logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Producer AI Agent API",
    description="Integrated API for Music Generation, RAG, and Workflow Automation",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth0 configuration
auth0_enabled = os.getenv("AUTH0_ENABLED", "false").lower() == "true"
auth0_config = None

if auth0_enabled:
    auth0_config = Auth0Config(
        domain=os.getenv("AUTH0_DOMAIN"),
        audience=os.getenv("AUTH0_AUDIENCE"),
        client_id=os.getenv("AUTH0_CLIENT_ID"),
        client_secret=os.getenv("AUTH0_CLIENT_SECRET")
    )
    logger.info("Auth0 authentication enabled")
else:
    logger.info("Auth0 authentication disabled")

# R2R client
r2r_url = os.getenv("R2R_URL", "http://localhost:7272")
r2r_client = R2RClient(base_url=r2r_url)

# Music API client
music_config = load_config()
music_client = AIMusicAPIClient(api_key=music_config.api_key)
music_fsm = MusicGenerationFSM(
    api_client=music_client,
    poll_interval=music_config.poll_interval,
    max_retries=music_config.max_retries
)


# ==================== Models ====================

class IngestDocumentsRequest(BaseModel):
    documents: List[Dict[str, Any]]
    collection_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    collection_id: Optional[str] = None


class RAGRequest(BaseModel):
    query: str
    limit: int = 5
    filters: Optional[Dict[str, Any]] = None
    collection_id: Optional[str] = None


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of all services"""
    services = {
        "api": "healthy",
        "r2r": "unknown",
        "music_api": "unknown"
    }

    # Check R2R
    try:
        await r2r_client.health_check()
        services["r2r"] = "healthy"
    except Exception as e:
        logger.error(f"R2R health check failed: {e}")
        services["r2r"] = "unhealthy"

    # Check Music API
    try:
        music_client.check_credits()
        services["music_api"] = "healthy"
    except Exception as e:
        logger.error(f"Music API health check failed: {e}")
        services["music_api"] = "unhealthy"

    return HealthResponse(
        status="healthy" if all(s == "healthy" for s in services.values()) else "degraded",
        services=services
    )


# ==================== R2R RAG Endpoints ====================

@app.post("/api/v1/rag/ingest")
async def ingest_documents(
    request: IngestDocumentsRequest,
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Ingest documents into R2R"""
    try:
        documents = [
            Document(
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                title=doc.get("title")
            )
            for doc in request.documents
        ]

        result = await r2r_client.ingest_documents(
            documents=documents,
            collection_id=request.collection_id
        )

        return {
            "status": "success",
            "result": result,
            "user_id": user.sub if user else None
        }
    except Exception as e:
        logger.error(f"Error ingesting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/ingest-files")
async def ingest_files(
    files: List[UploadFile] = File(...),
    collection_id: Optional[str] = Form(None),
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Ingest files (PDF, TXT, etc.) into R2R"""
    try:
        file_tuples = [
            (file.filename, file.file)
            for file in files
        ]

        result = await r2r_client.ingest_files(
            files=file_tuples,
            collection_id=collection_id,
            metadata={"user_id": user.sub} if user else None
        )

        return {
            "status": "success",
            "result": result,
            "user_id": user.sub if user else None
        }
    except Exception as e:
        logger.error(f"Error ingesting files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/search", response_model=List[SearchResult])
async def search_documents(
    request: SearchRequest,
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Search documents using hybrid search"""
    try:
        results = await r2r_client.search(
            query=request.query,
            limit=request.limit,
            filters=request.filters,
            collection_id=request.collection_id
        )
        return results
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/query", response_model=RAGResponse)
async def rag_query(
    request: RAGRequest,
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Perform RAG query with LLM generation"""
    try:
        response = await r2r_client.rag(
            query=request.query,
            limit=request.limit,
            filters=request.filters,
            collection_id=request.collection_id
        )
        return response
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/collections")
async def create_collection(
    request: CollectionCreate,
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Create a new collection"""
    try:
        result = await r2r_client.create_collection(
            name=request.name,
            description=request.description
        )
        return result
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/rag/collections")
async def list_collections(
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """List all collections"""
    try:
        collections = await r2r_client.list_collections()
        return {"collections": collections}
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Music Generation Endpoints ====================

@app.post("/api/v1/music/generate")
async def generate_music(
    request: MusicGenerationRequest,
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Generate music using Suno API"""
    try:
        result = music_fsm.generate_music(
            request=request,
            auto_download=True,
            output_dir=music_config.output_dir
        )

        return {
            "status": "success",
            "task_id": result.task_id,
            "clips": [
                {
                    "id": clip.id,
                    "title": clip.title,
                    "audio_url": clip.audio_url,
                    "image_url": clip.image_url,
                    "duration": clip.duration
                }
                for clip in result.clips
            ],
            "user_id": user.sub if user else None
        }
    except Exception as e:
        logger.error(f"Error generating music: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/music/status")
async def get_music_generation_status():
    """Get current FSM status"""
    return {
        "state": music_fsm.get_current_state(),
        "progress": music_fsm.get_progress()
    }


@app.get("/api/v1/music/credits")
async def check_music_credits(
    user: Optional[Auth0User] = Depends(get_current_user) if auth0_enabled else None
):
    """Check remaining music generation credits"""
    try:
        credits = music_client.check_credits()
        return credits
    except Exception as e:
        logger.error(f"Error checking credits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== User Management (if Auth0 enabled) ====================

if auth0_enabled:
    @app.get("/api/v1/user/profile")
    async def get_user_profile(user: Auth0User = Depends(get_current_user)):
        """Get current user profile"""
        return {
            "user_id": user.sub,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "permissions": user.permissions
        }


# ==================== Cleanup ====================

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await r2r_client.close()
    logger.info("API server shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
