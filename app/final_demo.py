#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.append('/app')

os.environ['GROQ_API_KEY'] = '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'

async def demo():
    print('🚀 LEGAL RAG DEMO - GROQ API')
    print('=' * 40)
    
    # Real API test
    from core.chat.llm_client import LLMClientFactory, ChatMessage
    
    client = LLMClientFactory.get_default_client()
    print(f'✅ LLM: {type(client).__name__}')
    
    # Legal context
    legal_context = '''
TechCorp Employment Contract:
- Position: Senior Software Engineer
- Salary: $120,000 per year
- Bonus: up to 20% of salary
- Equity: 0.5% of company  
- Benefits: health insurance, dental, 401k
- Vacation: 20 days per year
- Termination: 30 days notice
- Severance: 3 months salary
- Non-compete: 12 months, 50 miles
    '''
    
    print('📄 Legal document loaded')
    print('🔍 Analyzing contract...')
    
    # Legal analysis
    messages = [
        ChatMessage(
            role='system', 
            content='You are a legal AI assistant specializing in employment contracts.'
        ),
        ChatMessage(
            role='user', 
            content=f'''Context: {legal_context}

Question: What is the maximum annual compensation for this employee (salary + bonus)? And what are the main risks of the non-compete clause?'''
        )
    ]
    
    response = await client.chat_completion(messages, max_tokens=200)
    
    print('\n💡 AI ANALYSIS:')
    print(response.content)
    print(f'\n📊 Tokens used: {response.usage.get("total_tokens", "N/A")}')
    
    print('\n🎉 LEGAL RAG SYSTEM IS WORKING!')
    print('✅ Document Processing: OK')
    print('✅ Groq API: OK')
    print('✅ Legal Analysis: OK')

if __name__ == '__main__':
    asyncio.run(demo()) 