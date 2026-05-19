"""
Configuration management for the GenAI Pre-Sales Assistant
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # LLM Configuration
    groq_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    default_llm_provider: str = "groq"
    
    # Database Configuration
    database_path: str = "data/crm_database.db"
    
    # RAG Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_store_path: str = "models/faiss_index.bin"
    documents_path: str = "docs/sales_documents"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
