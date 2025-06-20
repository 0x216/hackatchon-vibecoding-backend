from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter()


class ClauseHistoryResponse(BaseModel):
    clause_id: str
    versions: List[dict]


@router.get("/clauses/{clause_id}")
async def get_clause_history(
    clause_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get change history for a specific clause."""
    
    try:
        result = await db.execute(
            """
            SELECT cv.id, cv.clause_text, cv.clause_type, cv.version_number,
                   cv.change_type, cv.change_description, cv.confidence_score,
                   cv.created_at, d.filename
            FROM clause_versions cv
            JOIN documents d ON cv.document_id = d.id
            WHERE cv.clause_id = :clause_id
            ORDER BY cv.version_number ASC
            """,
            {"clause_id": clause_id}
        )
        
        versions = []
        for row in result.fetchall():
            versions.append({
                "id": str(row.id),
                "clause_text": row.clause_text,
                "clause_type": row.clause_type,
                "version_number": row.version_number,
                "change_type": row.change_type,
                "change_description": row.change_description,
                "confidence_score": row.confidence_score,
                "created_at": row.created_at.isoformat(),
                "document_filename": row.filename
            })
        
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clause not found"
            )
        
        return ClauseHistoryResponse(
            clause_id=clause_id,
            versions=versions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch clause history: {str(e)}"
        )


@router.get("/documents/{document_id}/changes")
async def get_document_changes(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all changes detected in a specific document."""
    
    try:
        result = await db.execute(
            """
            SELECT cv.clause_id, cv.clause_type, cv.change_type,
                   cv.change_description, cv.confidence_score, cv.created_at
            FROM clause_versions cv
            WHERE cv.document_id = :document_id
            AND cv.change_type IS NOT NULL
            ORDER BY cv.created_at DESC
            """,
            {"document_id": document_id}
        )
        
        changes = []
        for row in result.fetchall():
            changes.append({
                "clause_id": str(row.clause_id),
                "clause_type": row.clause_type,
                "change_type": row.change_type,
                "change_description": row.change_description,
                "confidence_score": row.confidence_score,
                "detected_at": row.created_at.isoformat()
            })
        
        return {
            "document_id": document_id,
            "changes": changes,
            "total_changes": len(changes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document changes: {str(e)}"
        )


@router.get("/recent")
async def get_recent_changes(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get recent clause changes across all documents."""
    
    try:
        result = await db.execute(
            """
            SELECT cv.clause_id, cv.clause_type, cv.change_type,
                   cv.change_description, cv.confidence_score, cv.created_at,
                   d.filename
            FROM clause_versions cv
            JOIN documents d ON cv.document_id = d.id
            WHERE cv.change_type IS NOT NULL
            ORDER BY cv.created_at DESC
            LIMIT :limit
            """,
            {"limit": limit}
        )
        
        changes = []
        for row in result.fetchall():
            changes.append({
                "clause_id": str(row.clause_id),
                "clause_type": row.clause_type,
                "change_type": row.change_type,
                "change_description": row.change_description,
                "confidence_score": row.confidence_score,
                "detected_at": row.created_at.isoformat(),
                "document_filename": row.filename
            })
        
        return {
            "recent_changes": changes,
            "total": len(changes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recent changes: {str(e)}"
        )


@router.get("/compare/{version1_id}/{version2_id}")
async def compare_clause_versions(
    version1_id: str,
    version2_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Compare two versions of a clause."""
    
    try:
        result = await db.execute(
            """
            SELECT cv.id, cv.clause_text, cv.version_number, cv.created_at,
                   d.filename
            FROM clause_versions cv
            JOIN documents d ON cv.document_id = d.id
            WHERE cv.id IN (:version1, :version2)
            ORDER BY cv.version_number ASC
            """,
            {"version1": version1_id, "version2": version2_id}
        )
        
        versions = []
        for row in result.fetchall():
            versions.append({
                "id": str(row.id),
                "clause_text": row.clause_text,
                "version_number": row.version_number,
                "created_at": row.created_at.isoformat(),
                "document_filename": row.filename
            })
        
        if len(versions) != 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both clause versions not found"
            )
        
        # TODO: Implement detailed diff analysis
        
        return {
            "version1": versions[0],
            "version2": versions[1],
            "differences": "Detailed diff analysis coming soon!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare clause versions: {str(e)}"
        ) 