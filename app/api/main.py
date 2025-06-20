from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os

from app.utils.config import settings
from app.api.routers import documents, chat, history, conflicts
from app.db.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Application shutdown")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Legal RAG Agent with Change History Tracking",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"]  # Configure for production
    )
    
    # Include routers
    app.include_router(
        documents.router,
        prefix=f"{settings.api_v1_prefix}/documents",
        tags=["documents"]
    )
    
    app.include_router(
        chat.router,
        prefix=f"{settings.api_v1_prefix}/chat",
        tags=["chat"]
    )
    
    app.include_router(
        history.router,
        prefix=f"{settings.api_v1_prefix}/history",
        tags=["history"]
    )
    
    app.include_router(
        conflicts.router,
        prefix=f"{settings.api_v1_prefix}/conflicts",
        tags=["conflicts"]
    )
    
    # Serve static files
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        """Serve the main frontend page."""
        static_file = os.path.join(static_dir, "index.html")
        if os.path.exists(static_file):
            return FileResponse(static_file)
        return {
            "message": "Legal RAG Agent API",
            "version": settings.app_version,
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    ) 