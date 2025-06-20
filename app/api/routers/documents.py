from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os
import hashlib
import aiofiles
from pathlib import Path

from app.db.connection import get_db
from app.db.models import Document, ProcessingTask
from app.utils.config import settings
from app.core.ingest.extractors import DocumentExtractor
from app.core.ingest.processors import DocumentProcessor

router = APIRouter()


async def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file."""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        return False
    
    # Check file size
    if file.size > settings.max_file_size:
        return False
    
    return True


async def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of file."""
    hash_sha256 = hashlib.sha256()
    async with aiofiles.open(file_path, 'rb') as f:
        async for chunk in f:
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a legal document for processing."""
    
    # Validate file
    if not await validate_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type or size"
        )
    
    # Create upload directory if not exists
    upload_dir = Path(settings.upload_path)
    upload_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{file.filename}_{hash(file.filename)}_{file.size}{file_ext}"
    file_path = upload_dir / unique_filename
    
    try:
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Calculate file hash
        file_hash = await calculate_file_hash(str(file_path))
        
        # Check if document already exists
        existing_doc = await db.execute(
            "SELECT id FROM documents WHERE document_hash = :hash",
            {"hash": file_hash}
        )
        if existing_doc.scalar():
            # Remove duplicate file
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document already exists"
            )
        
        # Create document record
        document = Document(
            filename=file.filename,
            file_type=file_ext,
            file_size=file.size,
            document_hash=file_hash,
            processing_status="pending"
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Create processing task
        task = ProcessingTask(
            task_type="document_processing",
            document_id=document.id,
            status="pending"
        )
        
        db.add(task)
        await db.commit()
        
        # TODO: Trigger background processing task
        
        return {
            "message": "Document uploaded successfully",
            "document_id": str(document.id),
            "filename": file.filename,
            "status": "processing"
        }
        
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            os.remove(file_path)
        
        # Rollback database changes
        await db.rollback()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/")
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List uploaded documents."""
    
    try:
        result = await db.execute(
            """
            SELECT id, filename, file_type, upload_date, file_size, processing_status
            FROM documents 
            ORDER BY upload_date DESC 
            OFFSET :skip LIMIT :limit
            """,
            {"skip": skip, "limit": limit}
        )
        
        documents = []
        for row in result.fetchall():
            documents.append({
                "id": str(row.id),
                "filename": row.filename,
                "file_type": row.file_type,
                "upload_date": row.upload_date.isoformat(),
                "file_size": row.file_size,
                "processing_status": row.processing_status
            })
        
        return {
            "documents": documents,
            "total": len(documents),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(e)}"
        )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get document details by ID."""
    
    try:
        result = await db.execute(
            "SELECT * FROM documents WHERE id = :id",
            {"id": document_id}
        )
        
        document = result.fetchone()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {
            "id": str(document.id),
            "filename": document.filename,
            "file_type": document.file_type,
            "upload_date": document.upload_date.isoformat(),
            "file_size": document.file_size,
            "processing_status": document.processing_status,
            "document_hash": document.document_hash,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document."""
    
    try:
        # Get document details
        result = await db.execute(
            "SELECT * FROM documents WHERE id = :id",
            {"id": document_id}
        )
        
        document = result.fetchone()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete from database (cascade will handle related records)
        await db.execute(
            "DELETE FROM documents WHERE id = :id",
            {"id": document_id}
        )
        await db.commit()
        
        # TODO: Delete file from storage
        # TODO: Remove embeddings from vector database
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/{document_id}/status")
async def get_processing_status(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get document processing status."""
    
    try:
        result = await db.execute(
            """
            SELECT d.processing_status, t.status as task_status, t.progress, t.error_message
            FROM documents d
            LEFT JOIN processing_tasks t ON d.id = t.document_id
            WHERE d.id = :id
            ORDER BY t.created_at DESC
            LIMIT 1
            """,
            {"id": document_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {
            "document_id": document_id,
            "processing_status": row.processing_status,
            "task_status": row.task_status,
            "progress": row.progress or 0.0,
            "error_message": row.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch processing status: {str(e)}"
        ) 