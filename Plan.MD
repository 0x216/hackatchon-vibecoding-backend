# Legal RAG Agent with Change History - Technical Implementation Plan

## Overview

This document outlines the technical implementation plan for building a legal RAG (Retrieval-Augmented Generation) agent with change history tracking capabilities. The system will enable legal professionals to upload documents, track clause changes over time, detect conflicts, and interact with their legal corpus through an intelligent chat interface.

## System Architecture

### Core Components
- **Document Ingestion Service**: Multi-format document processing and text extraction
- **Embedding Service**: Vector representation generation for semantic search
- **Vector Database**: Efficient similarity search and retrieval
- **Change History Engine**: Clause tracking and version comparison
- **Conflict Detection System**: Rule-based and semantic conflict identification
- **RAG Chat API**: Context-aware question answering
- **Metadata Database**: Document metadata, change history, and relationships

## 1. Document Ingestion and Upload

### 1.1 File Upload API
```
POST /api/documents/upload
- Support: PDF, DOCX, TXT, RTF
- Multi-file upload with batch processing
- File validation and size limits (max 50MB per file)
- Async processing with task queues (Celery + Redis)
```

### 1.2 Text Extraction Pipeline
**Libraries & Tools:**
- `pdfplumber`: PDF text extraction with layout preservation
- `python-docx`: DOCX document processing
- `python-rtf`: RTF file support
- `chardet`: Character encoding detection

**Processing Steps:**
1. File type detection and validation
2. Text extraction with metadata preservation
3. OCR fallback for scanned documents (Tesseract)
4. Text cleaning and normalization
5. Document structure analysis (headers, sections, clauses)

### 1.3 Document Metadata Storage
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    file_type VARCHAR(10),
    upload_date TIMESTAMP,
    file_size BIGINT,
    extracted_text TEXT,
    document_hash VARCHAR(64),
    user_id UUID,
    processing_status VARCHAR(20)
);
```

## 2. Text Preprocessing and Segmentation

### 2.1 Intelligent Chunking Strategy
**Approach:**
- **Clause-level chunking**: Identify legal clauses using pattern matching
- **Semantic chunking**: Use sentence transformers to maintain context
- **Overlapping windows**: 10-20% overlap between chunks for context preservation
- **Size optimization**: 200-500 tokens per chunk for optimal embedding performance

**Implementation:**
```python
class LegalDocumentChunker:
    def __init__(self):
        self.clause_patterns = [
            r"Section \d+\.",
            r"Article \d+\.",
            r"Clause \d+\.",
            r"\d+\.\s+[A-Z]"
        ]
    
    def chunk_by_clauses(self, text: str) -> List[Chunk]:
        # Implementation for clause-based chunking
        pass
```

### 2.2 Text Normalization
- Remove excessive whitespace and formatting artifacts
- Standardize legal terminology
- Preserve important formatting (lists, numbering)
- Language detection and handling

## 3. Embedding and Vector Search

### 3.1 Embedding Model Selection
**Primary Options:**
- `all-MiniLM-L6-v2`: Lightweight, good performance
- `legal-bert-base-uncased`: Legal domain-specific model
- `e5-large`: High-quality general embeddings

### 3.2 Vector Database Implementation
**Option A: FAISS (File-based)**
```python
import faiss
import numpy as np

class FAISSVectorStore:
    def __init__(self, dimension: int = 384):
        self.index = faiss.IndexFlatIP(dimension)
        self.id_mapping = {}
    
    def add_embeddings(self, embeddings: np.ndarray, ids: List[str]):
        self.index.add(embeddings)
```

**Option B: Weaviate (Recommended for production)**
```yaml
# docker-compose.yml
weaviate:
  image: semitechnologies/weaviate:1.21.8
  environment:
    ENABLE_MODULES: text2vec-transformers
    DEFAULT_VECTORIZER_MODULE: text2vec-transformers
```

### 3.3 Embedding Storage Schema
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    chunk_id VARCHAR(50),
    chunk_text TEXT,
    embedding VECTOR(384),
    chunk_type VARCHAR(20), -- 'clause', 'paragraph', 'section'
    created_at TIMESTAMP
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

## 4. Legal Clause Change History Tracking

### 4.1 Clause Classification
**Clause Types:**
- Liability clauses
- Termination clauses
- Payment terms
- Deadlines and timelines
- Confidentiality provisions
- Indemnification clauses
- Force majeure
- Governing law

### 4.2 Semantic Matching Algorithm
```python
class ClauseMatchingEngine:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold
        self.embedding_model = SentenceTransformer('legal-bert-base-uncased')
    
    def find_similar_clauses(self, new_clause: str, existing_clauses: List[str]) -> List[Match]:
        # Semantic similarity matching implementation
        pass
```

### 4.3 Change History Database Schema
```sql
CREATE TABLE clause_versions (
    id UUID PRIMARY KEY,
    clause_id UUID,
    document_id UUID REFERENCES documents(id),
    clause_text TEXT,
    clause_type VARCHAR(50),
    version_number INTEGER,
    change_type VARCHAR(20), -- 'added', 'modified', 'deleted'
    change_description TEXT,
    confidence_score FLOAT,
    created_at TIMESTAMP,
    previous_version_id UUID REFERENCES clause_versions(id)
);

CREATE TABLE clause_changes (
    id UUID PRIMARY KEY,
    from_version_id UUID REFERENCES clause_versions(id),
    to_version_id UUID REFERENCES clause_versions(id),
    change_summary TEXT,
    semantic_similarity FLOAT,
    detected_at TIMESTAMP
);
```

### 4.4 Change Detection Pipeline
1. **New document ingestion**
2. **Clause extraction and classification**
3. **Semantic similarity comparison** with existing clauses
4. **Change type identification** (addition, modification, deletion)
5. **Confidence scoring** and manual review flagging
6. **Change history record creation**

## 5. Conflict and Inconsistency Detection

### 5.1 Rule-Based Detection
```python
class ConflictDetectionRules:
    def __init__(self):
        self.rules = [
            {
                'name': 'Payment Terms Conflict',
                'pattern': r'payment.*(\d+)\s*days?',
                'conflict_check': self.check_payment_terms_conflict
            },
            {
                'name': 'Termination Notice Conflict',
                'pattern': r'termination.*notice.*(\d+)\s*days?',
                'conflict_check': self.check_termination_notice_conflict
            }
        ]
```

### 5.2 Semantic Conflict Detection
- **Contradiction detection**: Using NLI models to identify contradictory statements
- **Temporal conflict analysis**: Detecting overlapping or conflicting timelines
- **Legal precedence analysis**: Identifying clauses that override others

### 5.3 Conflict Resolution Suggestions
```sql
CREATE TABLE detected_conflicts (
    id UUID PRIMARY KEY,
    clause_1_id UUID REFERENCES clause_versions(id),
    clause_2_id UUID REFERENCES clause_versions(id),
    conflict_type VARCHAR(50),
    severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    description TEXT,
    suggested_resolution TEXT,
    status VARCHAR(20), -- 'open', 'resolved', 'dismissed'
    detected_at TIMESTAMP
);
```

## 6. Interactive RAG Chat API

### 6.1 Query Processing Pipeline
```python
class RAGQueryProcessor:
    def __init__(self):
        self.retriever = VectorRetriever()
        self.llm_client = OpenAIClient()
        self.context_builder = ContextBuilder()
    
    async def process_query(self, query: str, user_context: Dict) -> ChatResponse:
        # 1. Query embedding and retrieval
        # 2. Context assembly with change history
        # 3. LLM prompt construction
        # 4. Response generation and post-processing
        pass
```

### 6.2 Context Assembly Strategy
**Context Sources:**
- **Relevant document chunks** (top-k similarity search)
- **Related clause history** (if query involves changes)
- **Conflict information** (if conflicts detected in relevant sections)
- **Document metadata** (dates, authors, document types)

### 6.3 Prompt Engineering
```python
LEGAL_RAG_PROMPT = """
You are a legal AI assistant with access to a document corpus and change history.

Context from relevant documents:
{document_context}

Change history for relevant clauses:
{change_history}

Detected conflicts (if any):
{conflicts}

User question: {user_query}

Please provide a comprehensive answer based on the context provided. 
If referencing specific clauses or changes, include document names and dates.
If conflicts exist, highlight them and suggest resolution approaches.
"""
```

### 6.4 Chat API Endpoints
```
POST /api/chat/query
GET /api/chat/history/{session_id}
POST /api/chat/feedback
GET /api/chat/suggested-questions
```

## 7. Docker Compose Infrastructure

### 7.1 Service Architecture
```yaml
version: '3.8'
services:
  api:
    build: ./app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/legalrag
      - REDIS_URL=redis://redis:6379
      - WEAVIATE_URL=http://weaviate:8080
    depends_on:
      - postgres
      - redis
      - weaviate

  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: legalrag
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  weaviate:
    image: semitechnologies/weaviate:1.21.8
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'text2vec-transformers'
      ENABLE_MODULES: 'text2vec-transformers'
    volumes:
      - weaviate_data:/var/lib/weaviate

  worker:
    build: ./app
    command: celery -A app.worker worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/legalrag
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
  weaviate_data:
```

## 8. Project Structure

```
/app
├── /api                    # FastAPI application
│   ├── __init__.py
│   ├── main.py            # FastAPI app instance
│   ├── /routers           # API route handlers
│   │   ├── documents.py   # Document upload/management
│   │   ├── chat.py        # RAG chat endpoints
│   │   ├── history.py     # Change history queries
│   │   └── conflicts.py   # Conflict detection endpoints
│   │
│   ├── /core                   # Core business logic
│   │   ├── /ingest            # Document processing
│   │   │   ├── extractors.py  # Text extraction utilities
│   │   │   ├── chunkers.py    # Text segmentation
│   │   │   └── processors.py  # Document processing pipeline
│   │   │
│   │   ├── /embedding         # Vector operations
│   │   │   ├── models.py      # Embedding model interfaces
│   │   │   ├── storage.py     # Vector database operations
│   │   │   └── retrieval.py   # Similarity search
│   │   │
│   │   ├── /history           # Change tracking
│   │   │   ├── matcher.py     # Clause matching algorithms
│   │   │   ├── tracker.py     # Change detection logic
│   │   │   └── analyzer.py    # Change analysis and comparison
│   │   │
│   │   ├── /conflict          # Conflict detection
│   │   │   ├── rules.py       # Rule-based detection
│   │   │   ├── semantic.py    # Semantic conflict detection
│   │   │   └── resolver.py    # Conflict resolution suggestions
│   │   │
│   │   └── /chat              # RAG implementation
│   │       ├── retriever.py   # Context retrieval
│   │       ├── generator.py   # Response generation
│   │       └── context.py     # Context assembly
│   │
│   ├── /db                     # Database modules
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── migrations/        # Database migrations
│   │   └── connection.py      # Database connection setup
│   │
│   ├── /utils                  # Utility functions
│   │   ├── logging.py         # Logging configuration
│   │   ├── config.py          # Application configuration
│   │   └── exceptions.py      # Custom exceptions
│   │
│   ├── /workers               # Background tasks
│   │   ├── __init__.py
│   │   ├── document_worker.py # Document processing tasks
│   │   └── analysis_worker.py # Change analysis tasks
│   │
│   ├── /tests                 # Test suite
│   │   ├── /unit             # Unit tests
│   │   ├── /integration      # Integration tests
│   │   └── /fixtures         # Test data
│   │
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container configuration
│   └── docker-compose.yml   # Multi-service orchestration
│
└── /tests                 # Test suite
    ├── /unit             # Unit tests
    ├── /integration      # Integration tests
    └── /fixtures         # Test data
```

## 9. MVP Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Project setup and Docker environment
- [ ] Basic FastAPI application structure
- [ ] Document upload API with text extraction
- [ ] PostgreSQL database setup with basic schemas
- [ ] Simple text chunking and preprocessing

### Phase 2: Core RAG (Weeks 3-4)
- [ ] Embedding generation pipeline
- [ ] Vector database integration (FAISS/Weaviate)
- [ ] Basic similarity search functionality
- [ ] Simple chat API for document Q&A
- [ ] Basic retrieval and response generation

### Phase 3: Change History (Weeks 5-6)
- [ ] Clause classification and extraction
- [ ] Semantic similarity matching for clauses
- [ ] Change detection algorithm implementation
- [ ] Change history database schema and API
- [ ] Basic change timeline visualization

### Phase 4: Enhancement (Weeks 7-8)
- [ ] Conflict detection rules implementation
- [ ] Advanced context assembly for RAG
- [ ] Response quality improvements
- [ ] Performance optimization
- [ ] Basic testing and documentation

## 10. Technical Considerations

### 10.1 Performance Optimization
- **Async processing**: Use async/await for I/O operations
- **Caching**: Redis for frequently accessed embeddings and results
- **Batch processing**: Process multiple documents simultaneously
- **Index optimization**: Regular vector index maintenance

### 10.2 Scalability
- **Horizontal scaling**: Stateless API design for load balancing
- **Database partitioning**: Partition by document age or user
- **Queue management**: Celery for background task distribution
- **Vector database sharding**: Distribute embeddings across nodes

### 10.3 Security & Privacy
- **Document encryption**: Encrypt documents at rest
- **Access controls**: User-based document access
- **Audit logging**: Track all document access and modifications
- **Data anonymization**: Options for sensitive data handling

### 10.4 Monitoring & Observability
- **Application metrics**: Response times, error rates
- **Business metrics**: Document processing success rates
- **Quality metrics**: RAG response relevance scores
- **Infrastructure monitoring**: Resource usage and health checks

## 11. Future Enhancements

### 11.1 Advanced Features
- **Multi-language support**: Process documents in multiple languages
- **Advanced conflict resolution**: ML-based resolution suggestions
- **Legal citation extraction**: Identify and link legal references
- **Contract risk scoring**: Automated risk assessment

### 11.2 Integration Capabilities
- **CRM integration**: Connect with legal case management systems
- **Email integration**: Process emails and attachments
- **API ecosystem**: Expose APIs for third-party integrations
- **Export capabilities**: Generate reports and summaries

### 11.3 User Experience
- **Web interface**: React-based frontend for document management
- **Mobile support**: Mobile-optimized chat interface
- **Collaboration features**: Multi-user document annotation
- **Advanced search**: Complex query support with filters

## 12. Success Metrics

### 12.1 Technical Metrics
- **Response time**: < 2 seconds for chat queries
- **Accuracy**: > 85% relevance in document retrieval
- **Availability**: 99.5% uptime
- **Processing speed**: < 5 minutes for document ingestion

### 12.2 Business Metrics
- **Change detection accuracy**: > 90% for similar clauses
- **Conflict identification**: > 80% precision, > 70% recall
- **User satisfaction**: Based on feedback scores
- **Document processing volume**: Support for 1000+ documents

---

This technical plan provides a comprehensive foundation for building a production-ready legal RAG agent with change history tracking capabilities. The modular architecture allows for incremental development and future enhancements while maintaining system reliability and performance. 