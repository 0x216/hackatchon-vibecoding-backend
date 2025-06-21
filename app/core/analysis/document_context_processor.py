"""
Document Context Processor for Multi-Stage Legal Analysis

This module handles the initial processing stage of the multi-stage legal analysis pipeline.
It retrieves complete document sections and uses lighter models for initial understanding
and relationship mapping.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.chat.llm_client import LLMClient, LLMClientFactory, ChatMessage
from app.db.models import Document, DocumentChunk, DocumentVersion
from app.core.ingest.chunkers import DocumentChunkerFactory

logger = logging.getLogger(__name__)


@dataclass
class DocumentSection:
    """Represents a complete document section with metadata."""
    document_id: str
    document_title: str
    section_title: str
    content: str
    section_type: str  # 'clause', 'paragraph', 'definition', etc.
    start_position: int
    end_position: int
    metadata: Dict[str, Any]
    relationships: List[str] = None  # Related section IDs


@dataclass
class ProcessedContext:
    """Processed document context with extracted relationships and concepts."""
    sections: List[DocumentSection]
    key_concepts: List[str]
    relationships: List[Dict[str, Any]]
    legal_entities: List[str]
    temporal_markers: List[Dict[str, Any]]
    cross_references: List[Dict[str, Any]]
    processing_metadata: Dict[str, Any]


class DocumentContextProcessor:
    """
    Processes complete document sections for comprehensive legal analysis.
    
    This processor:
    1. Retrieves complete document sections instead of just chunks
    2. Uses lighter models (Gemini 2.0 Flash) for initial understanding
    3. Extracts relationships and key concepts
    4. Prepares context for intelligent compression
    """
    
    def __init__(self, db_session: AsyncSession, light_model_client: Optional[LLMClient] = None):
        self.db_session = db_session
        self.light_model_client = light_model_client or self._get_light_model_client()
        
    def _get_light_model_client(self) -> LLMClient:
        """Get a light model client for initial processing."""
        try:
            # Try to get Gemini 2.0 Flash via Vertex AI
            return LLMClientFactory.create_client(
                "vertexai", 
                model_name="gemini-2.5-pro-exp"
            )
        except Exception as e:
            logger.warning(f"Could not initialize Gemini 2.0 Flash: {e}")
            # Fallback to regular Gemini Flash
            try:
                return LLMClientFactory.create_client(
                    "vertexai", 
                    model_name="gemini-2.5-pro"
                )
            except Exception as e2:
                logger.warning(f"Could not initialize Gemini Flash: {e2}")
                # Final fallback to default client
                return LLMClientFactory.get_default_client()
    
    async def process_documents_for_query(
        self, 
        query: str, 
        document_ids: List[str],
        max_sections: int = 50
    ) -> ProcessedContext:
        """
        Process documents for a specific query, retrieving complete sections.
        
        Args:
            query: The user's query
            document_ids: List of document IDs to process
            max_sections: Maximum number of sections to process
            
        Returns:
            ProcessedContext with extracted information
        """
        logger.info(f"Processing {len(document_ids)} documents for query: {query[:100]}...")
        
        # Step 1: Retrieve complete document sections
        sections = await self._retrieve_complete_sections(document_ids, query, max_sections)
        
        # Step 2: Process sections with light model for understanding
        processed_sections = await self._process_sections_with_light_model(sections, query)
        
        # Step 3: Extract relationships and concepts
        relationships = await self._extract_relationships(processed_sections)
        key_concepts = await self._extract_key_concepts(processed_sections, query)
        
        # Step 4: Identify legal entities and temporal markers
        legal_entities = await self._identify_legal_entities(processed_sections)
        temporal_markers = await self._identify_temporal_markers(processed_sections)
        
        # Step 5: Find cross-references
        cross_references = await self._find_cross_references(processed_sections)
        
        processing_metadata = {
            "total_sections_processed": len(processed_sections),
            "light_model_used": getattr(self.light_model_client, 'model_name', 'unknown'),
            "processing_time": None,  # Could add timing
            "query_relevance_scores": [s.metadata.get('relevance_score', 0) for s in processed_sections]
        }
        
        return ProcessedContext(
            sections=processed_sections,
            key_concepts=key_concepts,
            relationships=relationships,
            legal_entities=legal_entities,
            temporal_markers=temporal_markers,
            cross_references=cross_references,
            processing_metadata=processing_metadata
        )
    
    async def _retrieve_complete_sections(
        self, 
        document_ids: List[str], 
        query: str,
        max_sections: int
    ) -> List[DocumentSection]:
        """Retrieve complete document sections instead of just chunks."""
        
        sections = []
        
        for doc_id in document_ids:
            try:
                # Get document info
                doc_result = await self.db_session.execute(
                    select(Document).where(Document.id == doc_id)
                )
                document = doc_result.scalar_one_or_none()
                
                if not document:
                    logger.warning(f"Document {doc_id} not found")
                    continue
                
                # Get document chunks for this document
                chunks_result = await self.db_session.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == doc_id)
                    .order_by(DocumentChunk.chunk_index)
                )
                chunks = chunks_result.scalars().all()
                
                # Group chunks into logical sections
                doc_sections = await self._group_chunks_into_sections(
                    document, chunks, query
                )
                
                sections.extend(doc_sections)
                
            except Exception as e:
                logger.error(f"Error retrieving sections for document {doc_id}: {e}")
                continue
        
        # Sort by relevance and limit
        sections = sorted(
            sections, 
            key=lambda s: s.metadata.get('relevance_score', 0), 
            reverse=True
        )[:max_sections]
        
        return sections
    
    async def _group_chunks_into_sections(
        self, 
        document: Document, 
        chunks: List[DocumentChunk],
        query: str
    ) -> List[DocumentSection]:
        """Group document chunks into logical sections."""
        
        sections = []
        current_section_chunks = []
        current_section_type = None
        
        for chunk in chunks:
            chunk_type = chunk.metadata.get('chunk_type', 'general')
            
            # Start new section if type changes or we have enough content
            if (current_section_type != chunk_type or 
                len(current_section_chunks) >= 5):  # Max 5 chunks per section
                
                if current_section_chunks:
                    section = await self._create_section_from_chunks(
                        document, current_section_chunks, query
                    )
                    if section:
                        sections.append(section)
                
                current_section_chunks = [chunk]
                current_section_type = chunk_type
            else:
                current_section_chunks.append(chunk)
        
        # Handle last section
        if current_section_chunks:
            section = await self._create_section_from_chunks(
                document, current_section_chunks, query
            )
            if section:
                sections.append(section)
        
        return sections
    
    async def _create_section_from_chunks(
        self, 
        document: Document, 
        chunks: List[DocumentChunk],
        query: str
    ) -> Optional[DocumentSection]:
        """Create a DocumentSection from a group of chunks."""
        
        if not chunks:
            return None
        
        # Combine chunk content
        combined_content = "\n\n".join([chunk.content for chunk in chunks])
        
        # Calculate relevance score (simple implementation)
        relevance_score = await self._calculate_relevance_score(combined_content, query)
        
        # Determine section title and type
        section_type = chunks[0].metadata.get('chunk_type', 'general')
        section_title = await self._extract_section_title(combined_content, section_type)
        
        return DocumentSection(
            document_id=str(document.id),
            document_title=document.title or "Untitled Document",
            section_title=section_title,
            content=combined_content,
            section_type=section_type,
            start_position=chunks[0].start_char,
            end_position=chunks[-1].end_char,
            metadata={
                'relevance_score': relevance_score,
                'chunk_count': len(chunks),
                'word_count': len(combined_content.split()),
                'chunk_ids': [str(chunk.id) for chunk in chunks]
            }
        )
    
    async def _calculate_relevance_score(self, content: str, query: str) -> float:
        """Calculate relevance score for content against query."""
        # Simple keyword-based scoring for now
        # Could be enhanced with semantic similarity
        
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        intersection = query_words.intersection(content_words)
        if not query_words:
            return 0.0
        
        return len(intersection) / len(query_words)
    
    async def _extract_section_title(self, content: str, section_type: str) -> str:
        """Extract or generate a title for the section."""

        lines = content.strip().split('\n')
        first_line = lines[0] if lines else ""

        # If first line looks like a title (short, capitalized)
        if len(first_line) < 100 and first_line.isupper():
            return first_line

        # Generate title based on section type
        if section_type == 'definition':
            return "Definitions Section"
        elif section_type == 'obligation':
            return "Obligations and Requirements"
        elif section_type == 'rights':
            return "Rights and Permissions"
        else:
            return f"{section_type.title()} Section"

    async def _process_sections_with_light_model(
        self,
        sections: List[DocumentSection],
        query: str
    ) -> List[DocumentSection]:
        """Process sections with light model for initial understanding."""

        processed_sections = []

        for section in sections:
            try:
                # Create prompt for light model processing
                prompt = f"""Analyze this legal document section and extract key information:

Query Context: {query}

Document: {section.document_title}
Section: {section.section_title}
Content: {section.content[:2000]}...

Please identify:
1. Key legal concepts and terms
2. Important dates, deadlines, or time periods
3. Legal entities (parties, organizations)
4. Obligations and rights mentioned
5. Cross-references to other sections/documents

Respond in JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "legal_entities": ["entity1", "entity2"],
    "temporal_markers": [
        {{"type": "deadline", "date": "date", "description": "desc"}}
    ],
    "obligations": ["obligation1", "obligation2"],
    "rights": ["right1", "right2"],
    "cross_references": ["ref1", "ref2"],
    "relevance_to_query": 0.8
}}"""

                messages = [ChatMessage(role="user", content=prompt)]

                response = await self.light_model_client.chat_completion(
                    messages=messages,
                    temperature=0.1,  # Low temperature for factual extraction
                    max_tokens=1000
                )

                # Parse response and update section metadata
                try:
                    import json
                    analysis = json.loads(response.content)
                    section.metadata.update({
                        'light_model_analysis': analysis,
                        'processed': True
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse light model response for section {section.section_title}")
                    section.metadata['processed'] = False

                processed_sections.append(section)

            except Exception as e:
                logger.error(f"Error processing section {section.section_title}: {e}")
                section.metadata['processed'] = False
                processed_sections.append(section)

        return processed_sections

    async def _extract_relationships(self, sections: List[DocumentSection]) -> List[Dict[str, Any]]:
        """Extract relationships between sections."""

        relationships = []

        for i, section1 in enumerate(sections):
            for j, section2 in enumerate(sections[i+1:], i+1):
                # Check for relationships between sections
                relationship = await self._analyze_section_relationship(section1, section2)
                if relationship:
                    relationships.append(relationship)

        return relationships

    async def _analyze_section_relationship(
        self,
        section1: DocumentSection,
        section2: DocumentSection
    ) -> Optional[Dict[str, Any]]:
        """Analyze relationship between two sections."""

        # Simple relationship detection based on content overlap and references
        content1_words = set(section1.content.lower().split())
        content2_words = set(section2.content.lower().split())

        overlap = content1_words.intersection(content2_words)
        overlap_ratio = len(overlap) / min(len(content1_words), len(content2_words))

        if overlap_ratio > 0.3:  # Significant overlap
            return {
                'section1_id': f"{section1.document_id}:{section1.section_title}",
                'section2_id': f"{section2.document_id}:{section2.section_title}",
                'relationship_type': 'content_overlap',
                'strength': overlap_ratio,
                'common_terms': list(overlap)[:10]  # Top 10 common terms
            }

        return None

    async def _extract_key_concepts(
        self,
        sections: List[DocumentSection],
        query: str
    ) -> List[str]:
        """Extract key concepts from all sections."""

        all_concepts = set()

        for section in sections:
            analysis = section.metadata.get('light_model_analysis', {})
            concepts = analysis.get('key_concepts', [])
            all_concepts.update(concepts)

        # Sort by frequency and relevance to query
        concept_scores = {}
        query_words = set(query.lower().split())

        for concept in all_concepts:
            # Score based on query relevance
            concept_words = set(concept.lower().split())
            relevance = len(concept_words.intersection(query_words)) / max(len(concept_words), 1)
            concept_scores[concept] = relevance

        # Return top concepts sorted by relevance
        sorted_concepts = sorted(concept_scores.items(), key=lambda x: x[1], reverse=True)
        return [concept for concept, score in sorted_concepts[:20]]  # Top 20 concepts

    async def _identify_legal_entities(self, sections: List[DocumentSection]) -> List[str]:
        """Identify legal entities across all sections."""

        all_entities = set()

        for section in sections:
            analysis = section.metadata.get('light_model_analysis', {})
            entities = analysis.get('legal_entities', [])
            all_entities.update(entities)

        return list(all_entities)

    async def _identify_temporal_markers(self, sections: List[DocumentSection]) -> List[Dict[str, Any]]:
        """Identify temporal markers (dates, deadlines) across sections."""

        all_temporal_markers = []

        for section in sections:
            analysis = section.metadata.get('light_model_analysis', {})
            temporal_markers = analysis.get('temporal_markers', [])

            # Add section context to each marker
            for marker in temporal_markers:
                marker['source_section'] = section.section_title
                marker['source_document'] = section.document_title
                all_temporal_markers.append(marker)

        return all_temporal_markers

    async def _find_cross_references(self, sections: List[DocumentSection]) -> List[Dict[str, Any]]:
        """Find cross-references between sections and documents."""

        all_cross_references = []

        for section in sections:
            analysis = section.metadata.get('light_model_analysis', {})
            cross_refs = analysis.get('cross_references', [])

            for ref in cross_refs:
                all_cross_references.append({
                    'source_section': section.section_title,
                    'source_document': section.document_title,
                    'reference': ref,
                    'reference_type': 'explicit'  # Could be enhanced to detect types
                })

        return all_cross_references
