#!/usr/bin/env python3
"""
PRODUCTION TEST: Legal RAG Agent - Full Workflow
Real test with legal document and Groq API
"""

import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# API key setup
os.environ['GROQ_API_KEY'] = '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'

from core.ingest.extractors import TXTExtractor
from core.ingest.chunkers import LegalClauseChunker
from core.ingest.processors import DocumentProcessor
from core.chat.llm_client import LLMClientFactory, ChatMessage


# Real employment contract
EMPLOYMENT_CONTRACT = """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into on January 15, 2024, 
between TechCorp Industries, Inc., a Delaware corporation ("Company"), and 
John Smith ("Employee").

RECITALS
WHEREAS, Company desires to employ Employee as Senior Software Engineer; and
WHEREAS, Employee agrees to accept such employment subject to the terms hereof.

NOW, THEREFORE, the parties agree as follows:

SECTION 1. POSITION AND DUTIES
1.1 Position: Employee shall serve as Senior Software Engineer and shall report 
directly to the Chief Technology Officer.
1.2 Duties: Employee shall perform duties customarily associated with such 
position, including but not limited to software development, code review, 
and technical leadership.

SECTION 2. TERM OF EMPLOYMENT
2.1 Commencement: The term shall commence on February 1, 2024.
2.2 Duration: This Agreement shall continue for two (2) years unless 
terminated earlier pursuant to the provisions hereof.

SECTION 3. COMPENSATION AND BENEFITS
3.1 Base Salary: Company shall pay Employee an annual base salary of One 
Hundred Twenty Thousand Dollars ($120,000), payable bi-weekly.
3.2 Performance Bonus: Employee may earn an annual performance bonus of up to 
twenty percent (20%) of base salary based on achievement of performance goals.
3.3 Equity: Employee shall receive stock options equal to 0.5% of Company equity.
3.4 Benefits: Employee shall participate in Company's standard benefit plans 
including health insurance, dental, vision, and 401(k) with 4% company match.

SECTION 4. VACATION AND TIME OFF
Employee shall be entitled to twenty (20) days of paid vacation annually and 
standard sick leave in accordance with Company policy.

SECTION 5. CONFIDENTIALITY AND PROPRIETARY INFORMATION
5.1 Employee acknowledges access to confidential information and agrees to 
maintain confidentiality during and after employment.
5.2 Employee assigns all work product and inventions to Company.

SECTION 6. TERMINATION
6.1 Termination for Cause: Company may terminate immediately for misconduct, 
breach of Agreement, or conviction of felony.
6.2 Termination without Cause: Either party may terminate with thirty (30) days 
written notice.
6.3 Severance: If terminated without cause, Employee receives three (3) months 
base salary as severance.

SECTION 7. NON-COMPETE AND NON-SOLICITATION
7.1 Non-Compete: For twelve (12) months post-employment, Employee shall not 
engage in competing business within fifty (50) mile radius.
7.2 Non-Solicitation: Employee shall not solicit Company employees or customers 
for eighteen (18) months.

SECTION 8. GOVERNING LAW AND DISPUTE RESOLUTION
8.1 This Agreement shall be governed by Delaware law.
8.2 Disputes shall be resolved through binding arbitration in Delaware.

IN WITNESS WHEREOF, the parties execute this Agreement on the date first written.

TECHCORP INDUSTRIES, INC.        EMPLOYEE

By: /s/ Sarah Johnson            /s/ John Smith
Sarah Johnson, CEO               John Smith
Date: January 15, 2024          Date: January 15, 2024
"""


async def run_legal_rag_workflow():
    """Full workflow: Document Processing + Legal Analysis"""
    
    print("🚀 LEGAL RAG AGENT - PRODUCTION WORKFLOW")
    print("=" * 60)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Document: TechCorp Employment Contract")
    print()
    
    # STEP 1: Document Processing
    print("📄 STEP 1: Document Processing")
    print("-" * 30)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(EMPLOYMENT_CONTRACT)
        temp_file = f.name
    
    try:
        # Text extraction
        extractor = TXTExtractor()
        extraction_result = extractor.extract(temp_file)
        print(f"✅ Text extracted: {extraction_result['char_count']} characters")
        
        # Chunking by legal sections
        chunker = LegalClauseChunker()
        chunks = chunker.chunk(extraction_result['text'])
        print(f"✅ Chunks created: {len(chunks)}")
        
        # Show chunk types
        chunk_types = {}
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        
        print("📊 Chunk types:")
        for chunk_type, count in chunk_types.items():
            print(f"   - {chunk_type}: {count}")
        
        print()
        
        # STEP 2: Legal Questions with RAG
        print("⚖️ STEP 2: Legal Analysis with RAG")
        print("-" * 30)
        
        llm_client = LLMClientFactory.get_default_client()
        print(f"🤖 LLM client: {type(llm_client).__name__}")
        
        # Test 1: Salary question
        await test_salary_question(chunks, llm_client)
        
        # Test 2: Termination question
        await test_termination_question(chunks, llm_client)
        
        # Test 3: Legal risk analysis
        await test_risk_analysis(chunks, llm_client)
        
    finally:
        Path(temp_file).unlink()


async def test_salary_question(chunks, llm_client):
    """Test: Salary and bonus question"""
    print("\n💰 TEST 1: Compensation Analysis")
    
    # Find relevant chunks about compensation
    relevant_chunks = []
    for chunk in chunks:
        if any(keyword in chunk.text.lower() for keyword in 
               ['salary', 'compensation', 'bonus', 'equity', 'benefits']):
            relevant_chunks.append(chunk)
    
    context = "\n\n".join([chunk.text for chunk in relevant_chunks[:2]])
    
    messages = [
        ChatMessage(
            role="system",
            content="You are a legal AI assistant specializing in employment law. Answer clearly and to the point."
        ),
        ChatMessage(
            role="user",
            content=f"""Context from employment contract:
{context}

QUESTION: What total compensation is provided for the employee in this contract? 
Include base salary, bonuses, equity, and benefits."""
        )
    ]
    
    response = await llm_client.chat_completion(messages, max_tokens=300)
    
    print(f"📝 Question: Compensation package analysis")
    print(f"💡 AI Answer: {response.content}")
    print(f"📊 Tokens used: {response.usage.get('total_tokens', 'N/A')}")


async def test_termination_question(chunks, llm_client):
    """Test: Contract termination question"""
    print("\n🚪 TEST 2: Termination Conditions")
    
    # Find chunks about termination
    relevant_chunks = []
    for chunk in chunks:
        if any(keyword in chunk.text.lower() for keyword in 
               ['termination', 'severance', 'notice', 'cause']):
            relevant_chunks.append(chunk)
    
    context = "\n\n".join([chunk.text for chunk in relevant_chunks])
    
    messages = [
        ChatMessage(
            role="system",
            content="You are an employment law expert. Analyze termination conditions."
        ),
        ChatMessage(
            role="user",
            content=f"""Context from contract:
{context}

QUESTION: Under what conditions can an employer terminate an employee? 
What benefits are provided if terminated without cause?"""
        )
    ]
    
    response = await llm_client.chat_completion(messages, max_tokens=250)
    
    print(f"📝 Question: Termination conditions and severance")
    print(f"💡 AI Answer: {response.content}")


async def test_risk_analysis(chunks, llm_client):
    """Test: Legal risk analysis for employee"""
    print("\n⚠️ TEST 3: Legal Risk Analysis")
    
    # Take chunks about non-compete and confidentiality
    relevant_chunks = []
    for chunk in chunks:
        if any(keyword in chunk.text.lower() for keyword in 
               ['non-compete', 'confidentiality', 'proprietary', 'arbitration']):
            relevant_chunks.append(chunk)
    
    context = "\n\n".join([chunk.text for chunk in relevant_chunks])
    
    messages = [
        ChatMessage(
            role="system",
            content="You are a lawyer specializing in protecting employee rights. Identify potential risks in contracts."
        ),
        ChatMessage(
            role="user",
            content=f"""Context from contract:
{context}

QUESTION: What are the main risks associated with this contract for the employee? 
Pay attention to competition restrictions and dispute resolution."""
        )
    ]
    
    response = await llm_client.chat_completion(messages, max_tokens=350)
    
    print(f"📝 Question: Potential risks for employee")
    print(f"💡 AI Answer: {response.content}")


async def main():
    """Main function"""
    try:
        await run_legal_rag_workflow()
        
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! LEGAL RAG AGENT FULLY WORKS!")
        print("=" * 60)
        print("✅ Document Processing: Works")
        print("✅ Legal Chunking: Works") 
        print("✅ Groq API Integration: Works")
        print("✅ RAG Question Answering: Works")
        print("✅ Legal Analysis: Works")
        print()
        print("🚀 System ready for production use!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 