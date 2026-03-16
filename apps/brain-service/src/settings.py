"""
Identra Brain Service - Central Settings
All configuration in one place!
"""
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

class Settings:
    # ── AI API Keys ──────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY:    str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY:    str = os.getenv("GEMINI_API_KEY", "")
    HF_API_KEY:        str = os.getenv("HUGGINGFACE_API_KEY", "")

    # ── AI Models ────────────────────────────────────────────────
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    OPENAI_MODEL:    str = os.getenv("OPENAI_MODEL",    "gpt-4o-mini")
    GEMINI_MODEL:    str = os.getenv("GEMINI_MODEL",    "gemini-2.0-flash")
    HF_MODEL:        str = os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-7B-Instruct")

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL:  str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL:  str = os.getenv("SUPABASE_URL", "")

    # ── App Config ───────────────────────────────────────────────
    APP_VERSION:   str = "2.0"
    APP_TITLE:     str = "Identra Brain Service"
    DB_PATH:       str = "conversations.db"

    def is_configured(self, provider: str) -> bool:
        """Check if a provider has a valid API key."""
        keys = {
            "claude":       self.ANTHROPIC_API_KEY,
            "openai":       self.OPENAI_API_KEY,
            "gemini":       self.GEMINI_API_KEY,
            "huggingface":  self.HF_API_KEY,
        }
        key = keys.get(provider, "")
        return bool(key and not key.startswith("your_"))

# Single instance to use everywhere
settings = Settings()
