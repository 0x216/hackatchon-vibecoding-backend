from typing import Dict, Any, List
import logging
from pathlib import Path

from app.core.ingest.extractors import DocumentExtractorFactory
from app.core.ingest.chunkers import DocumentChunkerFactory, TextChunk
from app.utils.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main document processor that coordinates text extraction and chunking."""
    
    def __init__(self):
        self.extractor_factory = DocumentExtractorFactory()
        self.chunker_factory = DocumentChunkerFactory()
    
    def process_document(self, file_path: str, chunking_strategy: str = "hybrid") -> Dict[str, Any]:
        """Process a document: extract text and create chunks."""
        
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Step 1: Extract text from document
            extraction_result = self.extractor_factory.extract_text(file_path)
            
            if not extraction_result.get('text'):
                raise ValueError("No text extracted from document")
            
            # Step 2: Clean and preprocess text
            cleaned_text = self._clean_text(extraction_result['text'])
            
            # Step 3: Create chunks
            chunks = self.chunker_factory.chunk_document(cleaned_text, chunking_strategy)
            
            # Step 4: Post-process chunks
            processed_chunks = self._post_process_chunks(chunks)
            
            # Step 5: Generate document summary
            document_summary = self._generate_document_summary(
                cleaned_text, 
                processed_chunks, 
                extraction_result.get('metadata', {})
            )
            
            logger.info(f"Successfully processed document: {len(processed_chunks)} chunks created")
            
            return {
                'success': True,
                'original_text': extraction_result['text'],
                'cleaned_text': cleaned_text,
                'chunks': processed_chunks,
                'extraction_metadata': extraction_result.get('metadata', {}),
                'document_summary': document_summary,
                'processing_stats': {
                    'total_chunks': len(processed_chunks),
                    'original_char_count': extraction_result.get('char_count', 0),
                    'cleaned_char_count': len(cleaned_text),
                    'original_word_count': extraction_result.get('word_count', 0),
                    'chunking_strategy': chunking_strategy
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        
        # Remove excessive whitespace
        import re
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix common OCR issues
        text = text.replace('`', "'")  # Fix backticks
        text = text.replace('"', '"').replace('"', '"')  # Normalize quotes
        text = text.replace(''', "'").replace(''', "'")  # Normalize apostrophes
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    def _post_process_chunks(self, chunks: List[TextChunk]) -> List[Dict[str, Any]]:
        """Post-process chunks and convert to serializable format."""
        
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            # Additional cleaning for chunk text
            cleaned_chunk_text = self._clean_text(chunk.text)
            
            # Skip very short chunks
            if len(cleaned_chunk_text.split()) < 10:
                continue
            
            # Calculate additional metrics
            word_count = len(cleaned_chunk_text.split())
            sentence_count = len([s for s in cleaned_chunk_text.split('.') if s.strip()])
            
            processed_chunk = {
                'chunk_id': f"chunk_{i:04d}",
                'text': cleaned_chunk_text,
                'start_char': chunk.start_char,
                'end_char': chunk.end_char,
                'chunk_type': chunk.chunk_type,
                'word_count': word_count,
                'char_count': len(cleaned_chunk_text),
                'sentence_count': sentence_count,
                'metadata': {
                    **chunk.metadata,
                    'chunk_index': i,
                    'density_score': word_count / len(cleaned_chunk_text) if cleaned_chunk_text else 0
                }
            }
            
            processed_chunks.append(processed_chunk)
        
        return processed_chunks
    
    def _generate_document_summary(self, text: str, chunks: List[Dict], metadata: Dict) -> Dict[str, Any]:
        """Generate summary statistics for the document."""
        
        # Basic text statistics
        word_count = len(text.split())
        char_count = len(text)
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
        
        # Chunk type distribution
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        # Legal clause detection
        legal_indicators = self._detect_legal_indicators(text)
        
        return {
            'word_count': word_count,
            'char_count': char_count,
            'paragraph_count': paragraph_count,
            'chunk_count': len(chunks),
            'chunk_type_distribution': chunk_types,
            'legal_indicators': legal_indicators,
            'estimated_reading_time_minutes': word_count / 250,  # Avg 250 words per minute
            'complexity_score': self._calculate_complexity_score(text),
            'metadata': metadata
        }
    
    def _detect_legal_indicators(self, text: str) -> Dict[str, Any]:
        """Detect legal document indicators."""
        
        text_lower = text.lower()
        
        legal_keywords = {
            'contract_terms': ['whereas', 'therefore', 'party', 'agreement', 'contract'],
            'legal_entities': ['corporation', 'llc', 'inc', 'ltd', 'company'],
            'legal_actions': ['hereby', 'covenant', 'warrant', 'represent', 'indemnify'],
            'time_terms': ['effective date', 'term', 'expiration', 'renewal'],
            'financial_terms': ['payment', 'compensation', 'fee', 'penalty', 'damages'],
            'governance': ['governing law', 'jurisdiction', 'dispute resolution', 'arbitration']
        }
        
        detected_indicators = {}
        
        for category, keywords in legal_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            detected_indicators[category] = {
                'count': count,
                'keywords_found': [kw for kw in keywords if kw in text_lower]
            }
        
        # Overall legal document confidence score
        total_indicators = sum(ind['count'] for ind in detected_indicators.values())
        confidence_score = min(total_indicators / 20, 1.0)  # Cap at 1.0
        
        return {
            'categories': detected_indicators,
            'total_indicators': total_indicators,
            'legal_confidence_score': confidence_score,
            'likely_legal_document': confidence_score > 0.3
        }
    
    def _calculate_complexity_score(self, text: str) -> float:
        """Calculate document complexity score based on various factors."""
        
        words = text.split()
        sentences = [s for s in text.split('.') if s.strip()]
        
        if not words or not sentences:
            return 0.0
        
        # Average words per sentence
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Average characters per word
        avg_chars_per_word = sum(len(word) for word in words) / len(words)
        
        # Unique word ratio
        unique_words = set(word.lower() for word in words)
        unique_ratio = len(unique_words) / len(words)
        
        # Combine factors into complexity score (0-1)
        complexity = (
            min(avg_words_per_sentence / 25, 1.0) * 0.4 +  # Sentence length factor
            min(avg_chars_per_word / 8, 1.0) * 0.3 +       # Word length factor
            unique_ratio * 0.3                              # Vocabulary diversity factor
        )
        
        return round(complexity, 3) 