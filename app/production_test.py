#!/usr/bin/env python3
"""
Production Test for Legal RAG Agent
Full end-to-end test with real legal document and Groq API
"""

import os
import asyncio
import tempfile
from pathlib import Path
import json
from datetime import datetime

# API key setup
os.environ['GROQ_API_KEY'] = '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'

from core.ingest.extractors import TXTExtractor, DocumentExtractorFactory
from core.ingest.chunkers import LegalClauseChunker, DocumentChunkerFactory
from core.ingest.processors import DocumentProcessor
from core.chat.llm_client import LLMClientFactory, ChatMessage


# Example of real legal document
SAMPLE_LEGAL_CONTRACT = """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into on January 15, 2024, 
between TechCorp Industries, Inc., a Delaware corporation ("Company"), and 
John Smith ("Employee").

SECTION 1. POSITION AND DUTIES
Employee shall serve as Senior Software Engineer. Employee shall report to 
the Chief Technology Officer and shall perform such duties as are customarily 
associated with such position.

SECTION 2. TERM OF EMPLOYMENT
The term of this Agreement shall commence on February 1, 2024, and shall 
continue for a period of two (2) years, unless earlier terminated in 
accordance with the provisions hereof.

SECTION 3. COMPENSATION
3.1 Base Salary: Company shall pay Employee an annual base salary of One 
Hundred Twenty Thousand Dollars ($120,000), payable in accordance with 
Company's standard payroll practices.

3.2 Bonus: Employee may be eligible for an annual performance bonus of up 
to twenty percent (20%) of base salary, based on achievement of performance 
goals to be established by Company.

SECTION 4. BENEFITS
Employee shall be entitled to participate in all employee benefit plans 
maintained by Company, including health insurance, dental insurance, and 
retirement plans, subject to the terms and conditions of such plans.

SECTION 5. CONFIDENTIALITY
Employee acknowledges that Employee will have access to confidential and 
proprietary information of Company. Employee agrees to maintain the 
confidentiality of such information both during and after employment.

SECTION 6. TERMINATION
6.1 Termination for Cause: Company may terminate Employee's employment 
immediately for cause, including but not limited to misconduct, breach of 
this Agreement, or conviction of a felony.

6.2 Termination without Cause: Either party may terminate this Agreement 
with thirty (30) days written notice.

6.3 Severance: If Company terminates Employee without cause, Employee shall 
receive severance pay equal to three (3) months of base salary.

SECTION 7. NON-COMPETE
During employment and for a period of twelve (12) months thereafter, Employee 
shall not engage in any business that competes with Company within a 
fifty-mile radius of Company's headquarters.

SECTION 8. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date 
first written above.

TechCorp Industries, Inc.               John Smith
By: /s/ Sarah Johnson                   /s/ John Smith
Name: Sarah Johnson                     Employee
Title: CEO
"""


async def test_document_processing_pipeline():
    """Test full document processing pipeline"""
    print("🔄 Testing document processing pipeline...")
    
    # Create temporary file with contract
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(SAMPLE_LEGAL_CONTRACT)
        temp_file_path = f.name
    
    try:
        # 1. Text extraction
        extractor = TXTExtractor()
        extraction_result = extractor.extract(temp_file_path)
        
        print(f"✅ Text extracted: {extraction_result['char_count']} characters")
        
        # 2. Document chunking
        chunker = LegalClauseChunker()
        chunks = chunker.chunk(extraction_result['text'])
        
        print(f"✅ Chunks created: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):  # Show first 3
            print(f"   Chunk {i+1} ({chunk.chunk_type}): {chunk.text[:100]}...")
        
        # 3. Full pipeline through DocumentProcessor
        processor = DocumentProcessor()
        result = processor.process_document(temp_file_path)
        
        print(f"✅ Full pipeline completed:")
        print(f"   - Status: {result['success']}")
        print(f"   - Chunks created: {result['processing_stats']['total_chunks']}")
        print(f"   - Chunking strategy: {result['processing_stats']['chunking_strategy']}")
        
        return result
        
    finally:
        # Delete temporary file
        Path(temp_file_path).unlink()


async def test_llm_integration():
    """Test integration with Groq LLM"""
    print("\n🤖 Testing Groq LLM integration...")
    
    # Create LLM client
    llm_client = LLMClientFactory.get_default_client()
    print(f"✅ LLM client created: {type(llm_client).__name__}")
    
    # Test messages
    messages = [
        ChatMessage(
            role="system",
            content="You are a legal AI assistant. Answer briefly and to the point."
        ),
        ChatMessage(
            role="user", 
            content="Explain what an employment contract term is and why it's important?"
        )
    ]
    
    try:
        # Send request to LLM
        response = await llm_client.chat(messages, max_tokens=200)
        
        print(f"✅ LLM response received:")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage.get('total_tokens', 'N/A')}")
        print(f"   Response: {response.content[:200]}...")
        
        return response
        
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return None


async def test_rag_simulation():
    """RAG query simulation with document context"""
    print("\n🔍 Testing RAG with document context...")
    
    # Get processed document
    doc_result = await test_document_processing_pipeline()
    
    if not doc_result['success']:
        print("❌ Failed to process document for RAG")
        return
    
    # Extract relevant chunks (simulate vector search)
    relevant_chunks = []
    for chunk in doc_result['chunks'][:3]:  # Take first 3 chunks
        if any(keyword in chunk['text'].lower() for keyword in ['salary', 'compensation', 'payment']):
            relevant_chunks.append(chunk)
    
    if not relevant_chunks:
        relevant_chunks = doc_result['chunks'][:2]  # Take first 2 if no keywords found
    
    # Form context
    context = "\n\n".join([chunk['text'] for chunk in relevant_chunks])
    
    # RAG query
    llm_client = LLMClientFactory.get_default_client()
    
    rag_messages = [
        ChatMessage(
            role="system",
            content="""You are a legal AI assistant. Answer questions based on the provided context from legal documents. 
If the information in the context is insufficient, please say so."""
        ),
        ChatMessage(
            role="user",
            content=f"""Document context:
{context}

Question: What salary is specified in this employment contract and what additional payments are provided?"""
        )
    ]
    
    try:
        response = await llm_client.chat(rag_messages, max_tokens=300)
        
        print(f"✅ RAG response received:")
        print(f"   Context: {len(context)} characters from {len(relevant_chunks)} chunks")
        print(f"   Response: {response.content}")
        
        return response
        
    except Exception as e:
        print(f"❌ RAG error: {e}")
        return None


async def test_legal_analysis():
    """Test legal document analysis"""
    print("\n⚖️ Testing legal analysis...")
    
    llm_client = LLMClientFactory.get_default_client()
    
    analysis_messages = [
        ChatMessage(
            role="system",
            content="You are an experienced legal analyst. Analyze the legal document and highlight key risks and conditions."
        ),
        ChatMessage(
            role="user",
            content=f"""Analyze this employment contract and highlight:
1. Main financial conditions
2. Termination conditions
3. Potential risks for the employee
4. Non-compete agreement specifics

Document:
{SAMPLE_LEGAL_CONTRACT[:1500]}..."""
        )
    ]
    
    try:
        response = await llm_client.chat(analysis_messages, max_tokens=500)
        
        print(f"✅ Legal analysis completed:")
        print(f"{response.content}")
        
        return response
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return None


async def main():
    """Main production test function"""
    print("🚀 PRODUCTION TEST - Legal RAG Agent")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {os.environ.get('GROQ_API_KEY', 'NOT SET')[:20]}...")
    print()
    
    results = {}
    
    try:
        # 1. Document processing test
        results['document_processing'] = await test_document_processing_pipeline()
        
        # 2. LLM integration test
        results['llm_integration'] = await test_llm_integration()
        
        # 3. RAG simulation test
        results['rag_simulation'] = await test_rag_simulation()
        
        # 4. Legal analysis test
        results['legal_analysis'] = await test_legal_analysis()
        
        # Final report
        print("\n" + "="*50)
        print("📊 FINAL REPORT")
        print("="*50)
        
        success_count = 0
        total_tests = 4
        
        if results['document_processing'] and results['document_processing']['success']:
            print("✅ Document processing: SUCCESS")
            success_count += 1
        else:
            print("❌ Document processing: ERROR")
            
        if results['llm_integration']:
            print("✅ LLM integration: SUCCESS")
            success_count += 1
        else:
            print("❌ LLM integration: ERROR")
            
        if results['rag_simulation']:
            print("✅ RAG simulation: SUCCESS")
            success_count += 1
        else:
            print("❌ RAG simulation: ERROR")
            
        if results['legal_analysis']:
            print("✅ Legal analysis: SUCCESS")
            success_count += 1
        else:
            print("❌ Legal analysis: ERROR")
        
        print(f"\n🎯 Overall result: {success_count}/{total_tests} tests passed successfully")
        
        if success_count == total_tests:
            print("🎉 ALL TESTS PASSED! System ready for production!")
        elif success_count >= 3:
            print("⚠️ System works with minor issues")
        else:
            print("🚨 System requires further development")
            
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 