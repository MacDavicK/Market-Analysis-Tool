from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenRouterSettings(BaseModel):
    OPENROUTER_API_KEY: str = ""


class SupabaseSettings(BaseModel):
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""


class PineconeSettings(BaseModel):
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "bloomberg-terminal"


class OpenAISettings(BaseModel):
    OPENAI_API_KEY: str = ""


class APISettings(BaseModel):
    COINGECKO_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    GOLDAPI_KEY: str = ""

    # Phase 2 (optional for Phase 1)
    CASPARSER_API_KEY: Optional[str] = None
    PLAID_CLIENT_ID: Optional[str] = None
    PLAID_SECRET: Optional[str] = None
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET: Optional[str] = None


class AppSettings(BaseModel):
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    N8N_WEBHOOK_SECRET: str = ""


class Settings(BaseSettings):
    """
    Environment loader. The fields mirror `.env.example` so runtime config stays consistent.
    """

    # OpenRouter
    OPENROUTER_API_KEY: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "bloomberg-terminal"

    # OpenAI (Whisper + TTS)
    OPENAI_API_KEY: str = ""

    # Market Data APIs
    COINGECKO_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    GOLDAPI_KEY: str = ""

    # Phase 2 (not required for Phase 1)
    CASPARSER_API_KEY: Optional[str] = None
    PLAID_CLIENT_ID: Optional[str] = None
    PLAID_SECRET: Optional[str] = None
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET: Optional[str] = None

    # n8n webhook security
    N8N_WEBHOOK_SECRET: str = ""

    # Environment
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def openrouter(self) -> OpenRouterSettings:
        return OpenRouterSettings(OPENROUTER_API_KEY=self.OPENROUTER_API_KEY)

    @property
    def supabase(self) -> SupabaseSettings:
        return SupabaseSettings(
            SUPABASE_URL=self.SUPABASE_URL,
            SUPABASE_SERVICE_KEY=self.SUPABASE_SERVICE_KEY,
            SUPABASE_ANON_KEY=self.SUPABASE_ANON_KEY,
        )

    @property
    def pinecone(self) -> PineconeSettings:
        return PineconeSettings(
            PINECONE_API_KEY=self.PINECONE_API_KEY,
            PINECONE_INDEX_NAME=self.PINECONE_INDEX_NAME,
        )

    @property
    def openai(self) -> OpenAISettings:
        return OpenAISettings(OPENAI_API_KEY=self.OPENAI_API_KEY)

    @property
    def apis(self) -> APISettings:
        return APISettings(
            COINGECKO_API_KEY=self.COINGECKO_API_KEY,
            ALPHA_VANTAGE_API_KEY=self.ALPHA_VANTAGE_API_KEY,
            GOLDAPI_KEY=self.GOLDAPI_KEY,
            CASPARSER_API_KEY=self.CASPARSER_API_KEY,
            PLAID_CLIENT_ID=self.PLAID_CLIENT_ID,
            PLAID_SECRET=self.PLAID_SECRET,
            BINANCE_API_KEY=self.BINANCE_API_KEY,
            BINANCE_SECRET=self.BINANCE_SECRET,
        )

    @property
    def app(self) -> AppSettings:
        return AppSettings(
            ENVIRONMENT=self.ENVIRONMENT,
            FRONTEND_URL=self.FRONTEND_URL,
            N8N_WEBHOOK_SECRET=self.N8N_WEBHOOK_SECRET,
        )


settings = Settings()

