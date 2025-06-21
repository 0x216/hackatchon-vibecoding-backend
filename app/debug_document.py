#!/usr/bin/env python3
"""
Debug script to check document processing status and chunks.
"""

import asyncio
import sys
from sqlalchemy import text
from app.db.connection import async_session

async def debug_document(document_id: str):
    """Debug document processing status."""
    
    async with async_session() as session:
        print(f"Checking document: {document_id}")
        print("=" * 50)
        
        # Check if document exists
        doc_result = await session.execute(
            text("SELECT id, filename, processing_status, extracted_text, created_at FROM documents WHERE id = :id"),
            {"id": document_id}
        )
        doc_row = doc_result.fetchone()
        
        if not doc_row:
            print("❌ Document not found in database!")
            return
        
        print(f"✅ Document found: {doc_row.filename}")
        print(f"   Status: {doc_row.processing_status}")
        print(f"   Created: {doc_row.created_at}")
        print(f"   Has extracted text: {bool(doc_row.extracted_text)}")
        
        if doc_row.extracted_text:
            print(f"   Extracted text length: {len(doc_row.extracted_text)} characters")
            print(f"   Sample text: {doc_row.extracted_text[:200]}...")
        
        print("\n" + "=" * 50)
        
        # Check embeddings/chunks
        chunk_result = await session.execute(
            text("SELECT COUNT(*) FROM embeddings WHERE document_id = :id"),
            {"id": document_id}
        )
        chunk_count = chunk_result.scalar()
        print(f"📄 Document has {chunk_count} chunks in embeddings table")
        
        if chunk_count > 0:
            # Show sample chunks
            sample_result = await session.execute(
                text("SELECT chunk_id, chunk_text, chunk_type FROM embeddings WHERE document_id = :id LIMIT 3"),
                {"id": document_id}
            )
            sample_chunks = sample_result.fetchall()
            
            print("\n📋 Sample chunks:")
            for i, chunk in enumerate(sample_chunks, 1):
                print(f"   {i}. ID: {chunk.chunk_id}, Type: {chunk.chunk_type}")
                print(f"      Text: {chunk.chunk_text[:150]}...")
                print()
        
        # Check processing tasks
        task_result = await session.execute(
            text("SELECT status, error_message, created_at FROM processing_tasks WHERE document_id = :id ORDER BY created_at DESC LIMIT 1"),
            {"id": document_id}
        )
        task_row = task_result.fetchone()
        
        if task_row:
            print(f"🔄 Processing task status: {task_row.status}")
            if task_row.error_message:
                print(f"   Error: {task_row.error_message}")
            print(f"   Last updated: {task_row.created_at}")
        else:
            print("❌ No processing task found")

async def search_test(document_id: str, query: str):
    """Test search functionality."""
    
    async with async_session() as session:
        print(f"\n🔍 Testing search for: '{query}' in document {document_id}")
        print("=" * 50)
        
        # Test simple search
        search_result = await session.execute(
            text("""
                SELECT e.chunk_text, e.chunk_type,
                       CASE 
                           WHEN LOWER(e.chunk_text) LIKE LOWER(:pattern) THEN 0.9
                           ELSE 0.5
                       END as similarity_score
                FROM embeddings e
                JOIN documents d ON e.document_id = d.id
                WHERE d.id = :doc_id AND e.chunk_text ILIKE :pattern
                ORDER BY similarity_score DESC
                LIMIT 5
            """),
            {"doc_id": document_id, "pattern": f"%{query}%"}
        )
        
        results = search_result.fetchall()
        
        if results:
            print(f"✅ Found {len(results)} matching chunks:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. Score: {result.similarity_score:.2f}, Type: {result.chunk_type}")
                print(f"      Text: {result.chunk_text[:200]}...")
                print()
        else:
            print("❌ No matching chunks found")
            
            # Check if there are any chunks at all
            all_chunks = await session.execute(
                text("SELECT COUNT(*) FROM embeddings e JOIN documents d ON e.document_id = d.id WHERE d.id = :doc_id"),
                {"doc_id": document_id}
            )
            total_chunks = all_chunks.scalar()
            print(f"   Total chunks in document: {total_chunks}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_document.py <document_id> [search_query]")
        sys.exit(1)
    
    document_id = sys.argv[1]
    search_query = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        await debug_document(document_id)
        
        if search_query:
            await search_test(document_id, search_query)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 