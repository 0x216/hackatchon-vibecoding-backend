#!/usr/bin/env python3
"""
Test script for production search system.
This script tests the improved English-only search capabilities.
"""
import asyncio
import json
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.chat.retriever import DocumentRetriever
from app.core.chat.generator import RAGGenerator
from app.db.connection import async_session


async def test_search_queries():
    """Test various search queries to ensure they all return results."""
    
    print("🔍 Testing Production Search System (English-only)")
    print("=" * 60)
    
    # Initialize components
    retriever = DocumentRetriever()
    generator = RAGGenerator()
    
    # Test queries that should find information
    test_queries = [
        "What is the delivery date for goods?",
        "When do goods need to be delivered?",
        "Tell me about the delivery deadline",
        "What are the shipping requirements?",
        "When is the due date?",
        "What is the timeline for delivery?",
        "Supply date information",
        "Provide delivery details",
        "What is the date mentioned?",
        "September delivery",
        "goods delivery",
        "30th September",
        "delivery date",
        "contract terms",
        "agreement details",
        "legal obligations",
        "payment terms",
        "contract clauses",
        "document content",
        "any information"
    ]
    
    # Get document IDs
    async with async_session() as session:
        from sqlalchemy import text
        result = await session.execute(text("SELECT id FROM documents WHERE processing_status = 'completed'"))
        document_ids = [str(row.id) for row in result.fetchall()]
    
    if not document_ids:
        print("❌ No processed documents found!")
        return
    
    print(f"📄 Found {len(document_ids)} processed documents")
    print()
    
    total_queries = len(test_queries)
    successful_queries = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"🔍 Query {i}/{total_queries}: '{query}'")
        
        try:
            # Test retrieval
            chunks = await retriever.retrieve_relevant_chunks(
                query, 
                limit=3, 
                document_ids=document_ids
            )
            
            if chunks:
                print(f"  ✅ Found {len(chunks)} relevant chunks")
                successful_queries += 1
                
                # Show first result
                first_chunk = chunks[0]
                preview = first_chunk['chunk']['text'][:100] + "..." if len(first_chunk['chunk']['text']) > 100 else first_chunk['chunk']['text']
                score = first_chunk['similarity_score']
                source = first_chunk['document']['filename']
                
                print(f"  📖 Best match (score: {score:.3f}): {preview}")
                print(f"  📋 Source: {source}")
                
                # Test full RAG generation
                rag_response = await generator.generate_response(
                    query, 
                    document_ids=document_ids
                )
                
                if not rag_response.get('error', False):
                    print(f"  🤖 RAG Response: {rag_response['content'][:100]}...")
                else:
                    print(f"  ❌ RAG Error: {rag_response['content']}")
                
            else:
                print("  ❌ No relevant chunks found")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    print("=" * 60)
    print(f"📊 RESULTS: {successful_queries}/{total_queries} queries returned results")
    success_rate = (successful_queries / total_queries) * 100
    print(f"🎯 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! The search system is working very well!")
    elif success_rate >= 70:
        print("✅ GOOD! The search system is working well.")
    elif success_rate >= 50:
        print("⚠️  FAIR. The search system needs improvement.")
    else:
        print("❌ POOR. The search system needs significant work.")


async def test_aggressive_search():
    """Test that even very vague queries return something."""
    
    print("\n🔥 Testing ULTRA-AGGRESSIVE Search")
    print("=" * 60)
    
    retriever = DocumentRetriever()
    
    # Get document IDs
    async with async_session() as session:
        from sqlalchemy import text
        result = await session.execute(text("SELECT id FROM documents WHERE processing_status = 'completed'"))
        document_ids = [str(row.id) for row in result.fetchall()]
    
    # Very vague/difficult queries
    vague_queries = [
        "tell me something",
        "what does it say",
        "any information",
        "details",
        "info",
        "what",
        "date",
        "time",
        "when",
        "how",
        "a",
        "the",
        "contract",
        "document",
        "legal"
    ]
    
    print(f"Testing {len(vague_queries)} vague queries...")
    
    for query in vague_queries:
        print(f"🔍 '{query}' -> ", end="")
        
        try:
            chunks = await retriever.retrieve_relevant_chunks(
                query, 
                limit=3, 
                document_ids=document_ids
            )
            
            if chunks:
                print(f"✅ {len(chunks)} results (score: {chunks[0]['similarity_score']:.3f})")
            else:
                print("❌ No results")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎯 Goal: ALL queries should return at least some results!")


async def show_document_contents():
    """Show what documents we have to work with."""
    
    print("\n📚 Available Documents")
    print("=" * 60)
    
    async with async_session() as session:
        from sqlalchemy import text
        
        result = await session.execute(text("""
            SELECT 
                d.id, d.filename, d.processing_status, 
                COUNT(e.id) as chunk_count,
                LENGTH(d.extracted_text) as text_length
            FROM documents d
            LEFT JOIN embeddings e ON d.id = e.document_id
            GROUP BY d.id, d.filename, d.processing_status, d.extracted_text
            ORDER BY d.upload_date DESC
        """))
        
        for row in result.fetchall():
            print(f"📄 {row.filename}")
            print(f"   Status: {row.processing_status}")
            print(f"   Chunks: {row.chunk_count}")
            print(f"   Text length: {row.text_length} characters")
            print()


if __name__ == "__main__":
    async def main():
        await show_document_contents()
        await test_search_queries()
        await test_aggressive_search()
        
        print("\n🚀 Production Search Testing Complete!")
        print("The system should now handle ANY English query and return relevant results.")
    
    asyncio.run(main()) 