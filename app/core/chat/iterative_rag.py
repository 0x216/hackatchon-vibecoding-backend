from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import asyncio

from app.core.chat.llm_client import LLMClient, LLMClientFactory, ChatMessage, LLMResponse
from app.core.chat.enhanced_retriever import EnhancedDocumentRetriever
from app.db.connection import async_session
from app.db.models import ChatSession, ChatMessage as DBChatMessage

logger = logging.getLogger(__name__)


class IterativeRAGGenerator:
    """
    Advanced RAG system with iterative retrieval and query rewriting.
    
    Pipeline:
    1. Query Analysis & Rewriting - Convert user question to search queries
    2. Initial Retrieval - Find relevant documents
    3. Self-Assessment - Evaluate if enough information found
    4. Iterative Search - Additional searches if needed
    5. Response Generation - Generate final answer
    """
    
    def __init__(self, llm_client: LLMClient = None, retriever: EnhancedDocumentRetriever = None):
        self.llm_client = llm_client or LLMClientFactory.get_default_client()
        self.retriever = retriever or EnhancedDocumentRetriever()
        
        # System prompts for different tasks
        self.query_rewriter_prompt = """You are an expert at converting user questions into effective search queries for legal documents.

Your task: Convert the user's question into 1-3 specific search queries that will help find relevant information.

Guidelines:
1. Extract key concepts, entities, and legal terms
2. Consider synonyms and related terms
3. Think about what document sections would contain this information
4. Generate queries of different specificity levels

User Question: {question}

Respond with a JSON array of search queries, ordered by priority:
```json
[
  "specific search query 1",
  "broader search query 2", 
  "alternative angle query 3"
]
```"""

        self.assessment_prompt = """You are evaluating whether retrieved document chunks contain sufficient information to answer a user's question.

User Question: {question}

Retrieved Information:
{context}

Evaluate:
1. Is there enough information to provide a complete answer?
2. What specific information is missing (if any)?
3. What additional search terms might find missing information?

Respond with JSON:
```json
{{
  "sufficient": true/false,
  "confidence": 0.0-1.0,
  "missing_info": "description of missing information",
  "additional_queries": ["query1", "query2"]
}}
```"""

        self.response_prompt = """You are a specialized legal AI assistant. Answer the user's question based on the provided document context.

Key Instructions:
1. Provide a comprehensive answer based on the document context
2. If information is incomplete, clearly state what's missing
3. Cite specific documents and sections when possible
4. For legal matters, recommend consulting qualified legal counsel
5. Be precise about legal terms, dates, and requirements

User Question: {question}

Document Context:
{context}

Provide a clear, detailed answer based on the available information."""

    async def generate_response(
        self, 
        query: str, 
        session_id: str = None,
        max_iterations: int = 3,
        max_chunks_per_iteration: int = 5,
        document_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Generate response using iterative RAG approach."""
        
        try:
            logger.info(f"Starting iterative RAG for query: {query[:100]}...")
            
            # Step 1: Query Analysis & Rewriting
            search_queries = await self._rewrite_query(query)
            logger.info(f"Generated {len(search_queries)} search queries")
            
            # Step 2: Iterative Retrieval
            all_chunks = []
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Iteration {iteration}: Searching with {len(search_queries)} queries")
                
                # Retrieve chunks for current queries
                new_chunks = await self._retrieve_chunks(
                    search_queries, 
                    max_chunks_per_iteration,
                    document_ids,
                    exclude_chunk_ids=[chunk.get('chunk', {}).get('id') for chunk in all_chunks]
                )
                
                all_chunks.extend(new_chunks)
                
                # Step 3: Self-Assessment
                assessment = await self._assess_information_sufficiency(query, all_chunks)
                
                logger.info(f"Assessment: sufficient={assessment['sufficient']}, confidence={assessment['confidence']}")
                
                # If we have sufficient information or no additional queries, break
                if (assessment['sufficient'] and assessment['confidence'] > 0.7) or not assessment.get('additional_queries'):
                    break
                
                # Update search queries for next iteration
                search_queries = assessment.get('additional_queries', [])
            
            # Step 4: Generate Final Response
            context = self._build_context(all_chunks)
            final_response = await self._generate_final_response(query, context)
            
            # Step 5: Format and save response
            formatted_response = self._format_response(
                final_response, 
                all_chunks, 
                query,
                iterations_used=iteration
            )
            
            if session_id:
                await self._save_conversation(session_id, query, formatted_response)
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error in iterative RAG: {e}")
            return {
                "content": f"I apologize, but I encountered an error while processing your query: {str(e)}",
                "sources": [],
                "error": True,
                "query": query
            }
    
    async def _rewrite_query(self, query: str) -> List[str]:
        """Convert user question into effective search queries."""
        
        try:
            prompt = self.query_rewriter_prompt.format(question=query)
            
            response = await self.llm_client.chat_completion(
                [ChatMessage(role="user", content=prompt)],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            
            search_queries = json.loads(content)
            
            # Ensure we have a list of strings
            if isinstance(search_queries, list):
                return [str(q) for q in search_queries if q.strip()]
            else:
                return [query]  # Fallback to original query
                
        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            return [query]  # Fallback to original query
    
    async def _retrieve_chunks(
        self, 
        queries: List[str], 
        max_chunks: int,
        document_ids: List[str] = None,
        exclude_chunk_ids: List[str] = None
    ) -> List[Dict]:
        """Retrieve chunks for multiple queries."""
        
        all_chunks = []
        chunks_per_query = max(1, max_chunks // len(queries))
        
        # Execute searches in parallel
        tasks = []
        for query in queries:
            task = self.retriever.retrieve_relevant_chunks(
                query,
                limit=chunks_per_query,
                document_ids=document_ids
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results and deduplicate
        seen_chunk_ids = set(exclude_chunk_ids or [])
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in retrieval: {result}")
                continue
                
            for chunk in result:
                chunk_id = chunk.get('chunk', {}).get('id')
                if chunk_id and chunk_id not in seen_chunk_ids:
                    all_chunks.append(chunk)
                    seen_chunk_ids.add(chunk_id)
        
        # Sort by relevance and limit
        all_chunks.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        return all_chunks[:max_chunks]
    
    async def _assess_information_sufficiency(
        self, 
        query: str, 
        chunks: List[Dict]
    ) -> Dict[str, Any]:
        """Assess if retrieved information is sufficient to answer the question."""
        
        try:
            context = self._build_context(chunks)
            prompt = self.assessment_prompt.format(question=query, context=context)
            
            response = await self.llm_client.chat_completion(
                [ChatMessage(role="user", content=prompt)],
                temperature=0.2,
                max_tokens=300
            )
            
            # Parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            
            assessment = json.loads(content)
            
            # Validate response structure
            return {
                "sufficient": assessment.get("sufficient", False),
                "confidence": float(assessment.get("confidence", 0.0)),
                "missing_info": assessment.get("missing_info", ""),
                "additional_queries": assessment.get("additional_queries", [])
            }
            
        except Exception as e:
            logger.error(f"Error in assessment: {e}")
            # Conservative fallback
            return {
                "sufficient": len(chunks) > 0,
                "confidence": 0.5 if chunks else 0.0,
                "missing_info": "Could not assess information sufficiency",
                "additional_queries": []
            }
    
    async def _generate_final_response(self, query: str, context: str) -> LLMResponse:
        """Generate the final response based on all retrieved information."""
        
        prompt = self.response_prompt.format(question=query, context=context)
        
        return await self.llm_client.chat_completion(
            [ChatMessage(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=1500
        )
    
    def _build_context(self, retrieval_results: List[Dict]) -> str:
        """Build context string from retrieved document chunks."""
        
        if not retrieval_results:
            return "No relevant documents found in the corpus."
        
        context_parts = ["RELEVANT DOCUMENT INFORMATION:\n"]
        
        for i, result in enumerate(retrieval_results, 1):
            chunk = result.get('chunk', {})
            document = result.get('document', {})
            similarity = result.get('similarity_score', 0.0)
            
            context_part = f"""
Document {i}:
- Source: {document.get('filename', 'Unknown')}
- Section: {chunk.get('chunk_type', 'general')}
- Relevance: {similarity:.3f}
- Content: {chunk.get('text', '')}
---
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _format_response(
        self, 
        llm_response: LLMResponse, 
        retrieval_results: List[Dict],
        original_query: str,
        iterations_used: int = 1
    ) -> Dict[str, Any]:
        """Format the final response with sources and metadata."""
        
        # Extract source information
        sources = []
        for result in retrieval_results:
            chunk = result.get('chunk', {})
            document = result.get('document', {})
            
            source = {
                "document_name": document.get('filename', 'Unknown'),
                "document_id": document.get('id'),
                "chunk_type": chunk.get('chunk_type', 'general'),
                "similarity_score": result.get('similarity_score', 0.0),
                "chunk_preview": chunk.get('text', '')[:200] + "..." if len(chunk.get('text', '')) > 200 else chunk.get('text', '')
            }
            sources.append(source)
        
        return {
            "content": llm_response.content,
            "sources": sources,
            "query": original_query,
            "model_used": llm_response.model,
            "usage": llm_response.usage,
            "iterations_used": iterations_used,
            "total_chunks_found": len(retrieval_results),
            "timestamp": datetime.utcnow().isoformat(),
            "error": False
        }
    
    async def _save_conversation(
        self, 
        session_id: str, 
        user_query: str, 
        response: Dict[str, Any]
    ):
        """Save conversation to database."""
        
        try:
            async with async_session() as session:
                # Save user message
                user_message = DBChatMessage(
                    session_id=session_id,
                    message_type="user",
                    content=user_query,
                    timestamp=datetime.utcnow()
                )
                session.add(user_message)
                
                # Save assistant response
                assistant_message = DBChatMessage(
                    session_id=session_id,
                    message_type="assistant",
                    content=response["content"],
                    metadata={
                        "sources": response["sources"],
                        "iterations_used": response["iterations_used"],
                        "total_chunks": response["total_chunks_found"]
                    },
                    timestamp=datetime.utcnow()
                )
                session.add(assistant_message)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")


class QueryExpansionStrategy:
    """Different strategies for expanding queries."""
    
    @staticmethod
    def legal_domain_expansion(query: str) -> List[str]:
        """Expand query with legal domain knowledge."""
        
        # Legal synonyms and related terms
        legal_expansions = {
            "definition": ["define", "meaning", "term", "definition", "what is", "what does", "refers to"],
            "rights": ["rights", "privileges", "entitlements", "permissions", "authority"],
            "obligations": ["obligations", "duties", "responsibilities", "requirements", "must"],
            "liability": ["liability", "responsibility", "damages", "compensation", "penalties"],
            "termination": ["termination", "end", "conclude", "expire", "cancel", "dissolve"],
            "agreement": ["agreement", "contract", "document", "terms", "conditions"],
            "parties": ["parties", "participant", "entity", "organization", "individual"]
        }
        
        expanded_queries = [query]
        query_lower = query.lower()
        
        for concept, terms in legal_expansions.items():
            if concept in query_lower:
                for term in terms:
                    if term not in query_lower:
                        expanded_queries.append(query.replace(concept, term))
        
        return expanded_queries[:3]  # Limit to top 3 expansions 