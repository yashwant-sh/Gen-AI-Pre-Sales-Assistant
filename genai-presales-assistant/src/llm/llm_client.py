"""
LLM Client for GenAI Pre-Sales Assistant

Provides a unified interface to Groq (cloud) and Ollama (local) LLM providers.
"""

from typing import Optional, List, Dict
from loguru import logger


class LLMClient:
    """Unified LLM client supporting Groq and Ollama backends."""

    def __init__(self, provider: str = "groq", groq_api_key: Optional[str] = None,
                 ollama_base_url: str = "http://localhost:11434",
                 model: Optional[str] = None):
        self.provider = provider
        self._client = None
        self.model = model

        if provider == "groq":
            self._init_groq(groq_api_key, model)
        elif provider == "ollama":
            self._init_ollama(ollama_base_url, model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _init_groq(self, api_key: Optional[str], model: Optional[str]):
        if not api_key:
            raise ValueError("GROQ_API_KEY is required when using the groq provider")
        try:
            from groq import Groq
            self._client = Groq(api_key=api_key)
            self.model = model or "llama-3.1-8b-instant"
            logger.info(f"Groq LLM client initialized with model {self.model}")
        except ImportError:
            raise ImportError("Install the groq package: pip install groq")

    def _init_ollama(self, base_url: str, model: Optional[str]):
        self.ollama_base_url = base_url
        self.model = model or "llama3"
        logger.info(f"Ollama LLM client initialized with model {self.model} at {base_url}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 1024,
                 conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate a completion from the LLM.

        Args:
            conversation_history: Prior turns [{"role": "user"/"assistant", "content": "..."}]
                                  injected between the system prompt and the current prompt.

        Returns the assistant's text response, or an empty string on failure.
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        try:
            if self.provider == "groq":
                return self._generate_groq(messages, temperature, max_tokens)
            else:
                return self._generate_ollama(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""

    def _generate_groq(self, messages: List[Dict[str, str]],
                       temperature: float, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    def _generate_ollama(self, messages: List[Dict[str, str]],
                         temperature: float, max_tokens: int) -> str:
        import requests
        resp = requests.post(
            f"{self.ollama_base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def generate_response(self, query: str) -> str:
        """Convenience wrapper used by the orchestrator's general-query handler."""
        return self.generate(
            prompt=query,
            system_prompt=(
                "You are a helpful pre-sales assistant for a B2B software company. "
                "Answer concisely and professionally."
            ),
        )
