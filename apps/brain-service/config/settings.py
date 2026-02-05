"""
Configuration settings for Identra Brain-Service.

Handles environment variables, API keys, and service configuration
following Pydantic settings pattern for type safety.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Brain-Service configuration with environment variable support.
    """
    
    # =============================================================================
    # SERVICE CONFIGURATION
    # =============================================================================
    
    service_name: str = "identra-brain-service"
    service_version: str = "0.1.0"
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8001, description="Server port")
    
    # =============================================================================
    # AI PROVIDER API KEYS
    # =============================================================================
    
    # Anthropic Claude
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic Claude API key")
    
    # OpenAI GPT
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    
    # Google Gemini  
    google_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    
    # =============================================================================
    # GRPC & IDENTRA INTEGRATION
    # =============================================================================
    
    # Tunnel Gateway connection
    tunnel_gateway_host: str = Field(default="localhost", description="Tunnel gateway gRPC host")
    tunnel_gateway_port: int = Field(default=50051, description="Tunnel gateway gRPC port")
    
    # Vault Daemon integration (via tunnel gateway)
    vault_encryption_enabled: bool = Field(default=True, description="Enable vault encryption for memories")
    
    # =============================================================================
    # CUSTOM MODEL CONFIGURATION
    # =============================================================================
    
    # Fine-tuned summarization model
    custom_summarizer_model_path: str = Field(
        default="models/identra-context-summarizer-v1",
        description="Path to custom fine-tuned summarization model"
    )
    
    # Model inference settings
    max_input_tokens: int = Field(default=2048, description="Maximum input tokens for summarization")
    max_output_tokens: int = Field(default=512, description="Maximum output tokens for summarization")
    
    # =============================================================================
    # MEMORY & RAG SETTINGS
    # =============================================================================
    
    # Context selection limits
    max_context_packs: int = Field(default=5, description="Maximum context packs to retrieve")
    context_similarity_threshold: float = Field(default=0.7, description="Minimum similarity for context retrieval")
    
    # Vector store configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model for semantic similarity"
    )
    vector_store_cache_size: int = Field(default=1000, description="Vector store cache size")
    
    # =============================================================================
    # DEVELOPMENT & TESTING
    # =============================================================================
    
    debug_mode: bool = Field(default=True, description="Enable debug logging and features")
    mock_ai_responses: bool = Field(default=False, description="Use mock AI responses for testing")
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    structured_logging: bool = Field(default=True, description="Enable structured JSON logging")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get settings instance (singleton pattern).
    Creates instance on first call, returns cached instance on subsequent calls.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from environment.
    Useful for testing or configuration changes.
    """
    global _settings
    _settings = Settings()
    return _settings