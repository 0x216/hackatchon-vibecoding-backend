from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import httpx
import json
import logging
from pydantic import BaseModel

from app.utils.config import settings

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str  # 'system', 'user', 'assistant'
    content: str


class LLMResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, Any]] = None  # Changed from int to Any to handle floats
    model: Optional[str] = None
    finish_reason: Optional[str] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate chat completion."""
        pass


class GroqClient(LLMClient):
    """Groq API client for fast language model inference."""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.groq.com/openai/v1"):
        self.api_key = api_key or getattr(settings, 'groq_api_key', None)
        self.base_url = base_url
        self.default_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        
        if not self.api_key:
            logger.warning("Groq API key not provided. Set GROQ_API_KEY environment variable.")
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate chat completion using Groq API."""
        
        if not self.api_key:
            raise ValueError("Groq API key is required")
        
        model = model or self.default_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [msg.dict() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                if 'choices' not in data or not data['choices']:
                    raise ValueError("No response choices returned from Groq API")
                
                choice = data['choices'][0]
                message = choice.get('message', {})
                
                return LLMResponse(
                    content=message.get('content', ''),
                    usage=data.get('usage'),
                    model=data.get('model'),
                    finish_reason=choice.get('finish_reason')
                )
                
        except httpx.RequestError as e:
            logger.error(f"Request error calling Groq API: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Groq API: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            raise


class OpenAIClient(LLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key or getattr(settings, 'openai_api_key', None)
        self.base_url = base_url
        self.default_model = "gpt-3.5-turbo"
        
        if not self.api_key:
            logger.warning("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate chat completion using OpenAI API."""
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        model = model or self.default_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [msg.dict() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                if 'choices' not in data or not data['choices']:
                    raise ValueError("No response choices returned from OpenAI API")
                
                choice = data['choices'][0]
                message = choice.get('message', {})
                
                return LLMResponse(
                    content=message.get('content', ''),
                    usage=data.get('usage'),
                    model=data.get('model'),
                    finish_reason=choice.get('finish_reason')
                )
                
        except httpx.RequestError as e:
            logger.error(f"Request error calling OpenAI API: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from OpenAI API: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {e}")
            raise


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self):
        self.default_model = "mock-model"
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate mock chat completion."""
        
        # Generate a simple mock response based on the last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_message = msg.content
                break
        
        mock_content = f"This is a mock response to your query: '{last_user_message[:100]}...'. In a real implementation, this would be generated by an AI model."
        
        return LLMResponse(
            content=mock_content,
            usage={"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            model=model or self.default_model,
            finish_reason="stop"
        )


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    @staticmethod
    def create_client(provider: str = "groq", **kwargs) -> LLMClient:
        """Create LLM client based on provider."""
        
        if provider.lower() == "groq":
            return GroqClient(**kwargs)
        elif provider.lower() == "openai":
            return OpenAIClient(**kwargs)
        elif provider.lower() == "mock":
            return MockLLMClient()
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    @staticmethod
    def get_default_client() -> LLMClient:
        """Get default LLM client based on configuration."""
        
        # Try to determine the best available client
        provider = getattr(settings, 'llm_provider', 'groq')
        
        if provider == 'groq' and getattr(settings, 'groq_api_key', None):
            return GroqClient()
        elif provider == 'openai' and getattr(settings, 'openai_api_key', None):
            return OpenAIClient()
        else:
            logger.warning("No LLM API key configured. Using mock client.")
            return MockLLMClient()


# Test function for the Groq client
async def test_groq_client():
    """Test function for Groq client."""
    
    # Use the provided API key
    api_key = "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"
    client = GroqClient(api_key=api_key)
    
    messages = [
        ChatMessage(role="user", content="Explain the importance of fast language models")
    ]
    
    try:
        response = await client.chat_completion(messages)
        print(f"Response: {response.content}")
        print(f"Usage: {response.usage}")
        return response
    except Exception as e:
        print(f"Error testing Groq client: {e}")
        return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_groq_client()) 