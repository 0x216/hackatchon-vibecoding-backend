from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.db.connection import get_db
from app.db.models import ChatSession, ChatMessage
from app.core.chat.generator import RAGGenerator
from app.core.chat.iterative_rag import IterativeRAGGenerator
from app.core.chat.enhanced_retriever import EnhancedDocumentRetriever
from app.core.chat.llm_client import LLMClientFactory

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    llm_provider: Optional[str] = "groq"
    document_ids: Optional[List[str]] = []
    use_iterative_rag: bool = True
    max_iterations: int = 3


class ChatResponse(BaseModel):
    message: str
    session_id: str
    sources: List[dict] = []
    model_used: Optional[str] = None
    usage: Optional[dict] = None
    rag_approach: str = "traditional"
    iterations_used: Optional[int] = None
    total_chunks_found: Optional[int] = None


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process a chat query using RAG."""
    
    try:
        # Get or create session
        session_id = request.session_id
        if not session_id:
            # Create new session
            session = ChatSession()
            db.add(session)
            await db.commit()
            await db.refresh(session)
            session_id = str(session.id)
        else:
            # Verify session exists
            result = await db.execute(
                text("SELECT id FROM chat_sessions WHERE id = :id"),
                {"id": session_id}
            )
            if not result.scalar():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
        
        # Get conversation history
        history_result = await db.execute(
            text("""
                SELECT message_type, content 
                FROM chat_messages 
                WHERE session_id = :session_id 
                ORDER BY created_at ASC
            """),
            {"session_id": session_id}
        )
        
        conversation_history = []
        for row in history_result.fetchall():
            if row.message_type == "user":
                conversation_history.append({"user_message": row.content})
            elif row.message_type == "assistant" and conversation_history:
                conversation_history[-1]["assistant_message"] = row.content
        
        # Initialize LLM client
        llm_client = LLMClientFactory.create_client(request.llm_provider or "groq")
        
        # Choose RAG approach based on request
        if request.use_iterative_rag:
            # Use Iterative RAG for complex queries
            retriever = EnhancedDocumentRetriever()
            rag_generator = IterativeRAGGenerator(llm_client=llm_client, retriever=retriever)
            
            rag_response = await rag_generator.generate_response(
                query=request.message,
                session_id=session_id,
                max_iterations=request.max_iterations,
                document_ids=request.document_ids or []
            )
        else:
            # Use Traditional RAG for simple queries
            rag_generator = RAGGenerator(llm_client=llm_client)
            
            rag_response = await rag_generator.generate_response(
                query=request.message,
                session_id=session_id,
                conversation_history=conversation_history,
                document_ids=request.document_ids or []
            )
        
        return ChatResponse(
            message=rag_response["content"],
            session_id=session_id,
            sources=rag_response.get("sources", []),
            model_used=rag_response.get("model_used"),
            usage=rag_response.get("usage"),
            rag_approach="iterative" if request.use_iterative_rag else "traditional",
            iterations_used=rag_response.get("iterations_used"),
            total_chunks_found=rag_response.get("total_chunks_found")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat query: {str(e)}"
        )


@router.get("/sessions")
async def list_chat_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List chat sessions."""
    
    try:
        result = await db.execute(
            text("""
                SELECT id, session_name, created_at, updated_at
                FROM chat_sessions 
                ORDER BY updated_at DESC 
                OFFSET :skip LIMIT :limit
            """),
            {"skip": skip, "limit": limit}
        )
        
        sessions = []
        for row in result.fetchall():
            sessions.append({
                "id": str(row.id),
                "session_name": row.session_name,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat()
            })
        
        return {
            "sessions": sessions,
            "total": len(sessions),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages")
async def get_chat_history(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session."""
    
    try:
        result = await db.execute(
            text("""
                SELECT message_type, content, created_at, metadata
                FROM chat_messages 
                WHERE session_id = :session_id
                ORDER BY created_at ASC
                OFFSET :skip LIMIT :limit
            """),
            {"session_id": session_id, "skip": skip, "limit": limit}
        )
        
        messages = []
        for row in result.fetchall():
            messages.append({
                "type": row.message_type,
                "content": row.content,
                "created_at": row.created_at.isoformat(),
                "metadata": row.metadata
            })
        
        return {
            "session_id": session_id,
            "messages": messages,
            "total": len(messages),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session and its messages."""
    
    try:
        # Check if session exists
        result = await db.execute(
            text("SELECT id FROM chat_sessions WHERE id = :id"),
            {"id": session_id}
        )
        
        if not result.scalar():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Delete session (cascade will delete messages)
        await db.execute(
            text("DELETE FROM chat_sessions WHERE id = :id"),
            {"id": session_id}
        )
        await db.commit()
        
        return {"message": "Chat session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {str(e)}"
        )


@router.post("/test-llm")
async def test_llm_connection(llm_provider: str = "groq"):
    """Test LLM connection and response."""
    
    try:
        llm_client = LLMClientFactory.create_client(llm_provider)
        
        # Test with a simple query
        from app.core.chat.llm_client import ChatMessage
        test_messages = [
            ChatMessage(role="user", content="Hello! Please respond with a brief greeting.")
        ]
        
        response = await llm_client.chat_completion(test_messages)
        
        return {
            "status": "success",
            "provider": llm_provider,
            "model": response.model,
            "response": response.content,
            "usage": response.usage
        }
        
    except Exception as e:
        return {
            "status": "error",
            "provider": llm_provider,
            "error": str(e)
        }


class QueryAnalysisRequest(BaseModel):
    query: str


@router.post("/analyze-query")
async def analyze_query(request: QueryAnalysisRequest):
    """Analyze query and recommend RAG approach."""
    
    def classify_query_type(query: str) -> str:
        """Classify the type of query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["what is", "define", "definition", "meaning"]):
            return "definition"
        elif any(word in query_lower for word in ["who are", "parties", "stakeholders"]):
            return "entity_identification"
        elif any(word in query_lower for word in ["obligations", "requirements", "must", "shall"]):
            return "obligation_inquiry"
        elif any(word in query_lower for word in ["rights", "permissions", "allowed", "can"]):
            return "rights_inquiry"
        elif any(word in query_lower for word in ["subject", "topic", "about", "main", "key"]):
            return "conceptual_overview"
        else:
            return "general"
    
    def needs_iterative_approach(query: str) -> bool:
        """Determine if query needs iterative approach."""
        query_type = classify_query_type(query)
        return query_type in ["conceptual_overview", "general", "entity_identification"]
    
    def estimate_iterations(query: str) -> int:
        """Estimate how many iterations might be needed."""
        query_type = classify_query_type(query)
        
        if query_type in ["conceptual_overview", "general"]:
            return 3
        elif query_type in ["entity_identification", "obligation_inquiry"]:
            return 2
        else:
            return 1
    
    query_type = classify_query_type(request.query)
    recommended_approach = "iterative" if needs_iterative_approach(request.query) else "traditional"
    
    return {
        "query": request.query,
        "query_type": query_type,
        "recommended_approach": recommended_approach,
        "estimated_iterations": estimate_iterations(request.query),
        "reasoning": {
            "traditional_rag": "Best for exact definitions, direct quotes, specific clauses",
            "iterative_rag": "Best for conceptual questions, entity analysis, complex topics"
        }
    } 