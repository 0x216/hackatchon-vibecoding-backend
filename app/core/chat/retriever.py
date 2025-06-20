from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.connection import async_session

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Document retrieval system for finding relevant chunks."""
    
    def __init__(self):
        self.similarity_threshold = 0.7
    
    async def retrieve_relevant_chunks(
        self, 
        query: str, 
        limit: int = 5,
        document_ids: Optional[List[str]] = None,
        chunk_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks for a query."""
        
        try:
            # For now, use simple text-based similarity until we have embeddings
            results = await self._text_based_search(
                query, limit, document_ids, chunk_types
            )
            
            logger.info(f"Retrieved {len(results)} relevant chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {e}")
            return []
    
    async def _text_based_search(
        self, 
        query: str, 
        limit: int,
        document_ids: Optional[List[str]] = None,
        chunk_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Simple text-based search using PostgreSQL text search."""
        
        async with async_session() as session:
            # Build search query
            where_conditions = ["e.chunk_text ILIKE :search_pattern"]
            params = {"search_pattern": f"%{query}%", "limit": limit}
            
            if document_ids:
                where_conditions.append("d.id = ANY(:document_ids)")
                params["document_ids"] = document_ids
            
            if chunk_types:
                where_conditions.append("e.chunk_type = ANY(:chunk_types)")
                params["chunk_types"] = chunk_types
            
            # Simple text similarity search
            query_sql = f"""
                SELECT 
                    e.id as embedding_id,
                    e.chunk_id,
                    e.chunk_text,
                    e.chunk_type,
                    e.start_char,
                    e.end_char,
                    d.id as document_id,
                    d.filename,
                    d.file_type,
                    d.upload_date,
                    -- Simple similarity score based on keyword matches
                    (
                        CASE 
                            WHEN LOWER(e.chunk_text) LIKE LOWER(:search_pattern) THEN 0.9
                            WHEN LOWER(e.chunk_text) LIKE LOWER(:loose_pattern) THEN 0.7
                            ELSE 0.5
                        END
                    ) as similarity_score
                FROM embeddings e
                JOIN documents d ON e.document_id = d.id
                WHERE {' AND '.join(where_conditions)}
                ORDER BY similarity_score DESC, e.created_at DESC
                LIMIT :limit
            """
            
            # Add loose pattern for broader matching
            params["loose_pattern"] = f"%{' '.join(query.split()[:3])}%"
            
            result = await session.execute(text(query_sql), params)
            rows = result.fetchall()
            
            # Format results
            results = []
            for row in rows:
                chunk_data = {
                    "id": str(row.embedding_id),
                    "chunk_id": row.chunk_id,
                    "text": row.chunk_text,
                    "chunk_type": row.chunk_type,
                    "start_char": row.start_char,
                    "end_char": row.end_char
                }
                
                document_data = {
                    "id": str(row.document_id),
                    "filename": row.filename,
                    "file_type": row.file_type,
                    "upload_date": row.upload_date.isoformat() if row.upload_date else None
                }
                
                results.append({
                    "chunk": chunk_data,
                    "document": document_data,
                    "similarity_score": float(row.similarity_score)
                })
            
            return results
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        
        async with async_session() as session:
            query_sql = """
                SELECT 
                    e.id as embedding_id,
                    e.chunk_id,
                    e.chunk_text,
                    e.chunk_type,
                    e.start_char,
                    e.end_char,
                    d.filename,
                    d.file_type
                FROM embeddings e
                JOIN documents d ON e.document_id = d.id
                WHERE d.id = :document_id
                ORDER BY e.start_char ASC
            """
            
            result = await session.execute(text(query_sql), {"document_id": document_id})
            rows = result.fetchall()
            
            chunks = []
            for row in rows:
                chunk = {
                    "id": str(row.embedding_id),
                    "chunk_id": row.chunk_id,
                    "text": row.chunk_text,
                    "chunk_type": row.chunk_type,
                    "start_char": row.start_char,
                    "end_char": row.end_char,
                    "document_filename": row.filename,
                    "document_type": row.file_type
                }
                chunks.append(chunk)
            
            return chunks
    
    async def find_similar_clauses(
        self, 
        clause_text: str, 
        clause_type: str = None,
        exclude_document_id: str = None,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Find similar clauses across documents."""
        
        # Extract key terms from clause text for matching
        key_terms = self._extract_key_terms(clause_text)
        
        if not key_terms:
            return []
        
        async with async_session() as session:
            where_conditions = []
            params = {"limit": 10}
            
            # Build search pattern from key terms
            search_patterns = []
            for i, term in enumerate(key_terms[:3]):  # Use top 3 terms
                pattern_key = f"term_{i}"
                search_patterns.append(f"LOWER(e.chunk_text) LIKE LOWER(:{pattern_key})")
                params[pattern_key] = f"%{term}%"
            
            if search_patterns:
                where_conditions.append(f"({' OR '.join(search_patterns)})")
            
            if clause_type:
                where_conditions.append("e.chunk_type = :clause_type")
                params["clause_type"] = clause_type
            
            if exclude_document_id:
                where_conditions.append("d.id != :exclude_document_id")
                params["exclude_document_id"] = exclude_document_id
            
            query_sql = f"""
                SELECT 
                    e.chunk_text,
                    e.chunk_type,
                    d.id as document_id,
                    d.filename,
                    -- Simple similarity calculation
                    (
                        LENGTH(e.chunk_text) - LENGTH(REPLACE(LOWER(e.chunk_text), LOWER(:main_term), ''))
                    ) / LENGTH(:main_term)::float as similarity_score
                FROM embeddings e
                JOIN documents d ON e.document_id = d.id
                WHERE {' AND '.join(where_conditions)}
                ORDER BY similarity_score DESC
                LIMIT :limit
            """
            
            params["main_term"] = key_terms[0] if key_terms else ""
            
            result = await session.execute(text(query_sql), params)
            rows = result.fetchall()
            
            similar_clauses = []
            for row in rows:
                if row.similarity_score >= similarity_threshold:
                    similar_clauses.append({
                        "clause_text": row.chunk_text,
                        "clause_type": row.chunk_type,
                        "document_id": str(row.document_id),
                        "document_filename": row.filename,
                        "similarity_score": float(row.similarity_score)
                    })
            
            return similar_clauses
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for similarity matching."""
        
        # Simple keyword extraction (in production, use more sophisticated NLP)
        import re
        
        # Common legal stopwords to exclude
        stopwords = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'this', 'that', 'these', 'those', 'a', 'an', 'is', 'are', 'was',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'must', 'shall'
        }
        
        # Extract words (3+ characters, excluding common stopwords)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        key_terms = [word for word in words if word not in stopwords]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms[:10]  # Return top 10 terms 