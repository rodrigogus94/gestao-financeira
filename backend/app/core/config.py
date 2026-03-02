"""
Configuração centralizada do backend.

Carrega variáveis de ambiente (e do arquivo `.env`) via pydantic-settings,
validando tipos e expondo uma única instância `settings` para uso em toda
a aplicação (rotas, serviços, clientes de IA e Supabase).
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Configurações do projeto carregadas do ambiente.

    Os campos com `...` (ellipsis) são obrigatórios: a aplicação só sobe
    se estiverem definidos no `.env` ou nas variáveis de ambiente. Campos
    com default podem ser omitidos no `.env` e o valor padrão será usado.
    O parâmetro `env` em cada Field indica o nome exato da variável de ambiente.
    """

    # --- Supabase (obrigatórios para o backend) ---
    SUPABASE_URL: str = Field(
        ...,
        env="SUPABASE_URL",
        description="URL base do projeto no Supabase (ex.: https://xxxx.supabase.co).",
    )
    SUPABASE_KEY: str = Field(
        ...,
        env="SUPABASE_KEY",
        description="Chave anon do Supabase; usada em operações com RLS (frontend/backend).",
    )
    SUPABASE_SERVICE_KEY: str = Field(
        ...,
        env="SUPABASE_SERVICE_KEY",
        description="Chave service role; uso restrito ao backend (operações privilegiadas).",
    )

    # --- OpenAI (chave opcional se não usar OpenAI) ---
    OPENAI_API_KEY: str | None = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="Chave da API OpenAI; obrigatória apenas se DEFAULT_IA_PROVIDER for openai.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4",
        env="OPENAI_MODEL",
        description="Modelo OpenAI usado nas chamadas (ex.: gpt-4, gpt-4o-mini).",
    )

    # --- Google Gemini (chave opcional se não usar Gemini) ---
    GEMINI_API_KEY: str | None = Field(
        default=None,
        env="GEMINI_API_KEY",
        description="Chave da API Google Gemini; obrigatória se usar o provider gemini.",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-pro",
        env="GEMINI_MODEL",
        description="Modelo Gemini usado nas chamadas (ex.: gemini-pro, gemini-1.5-flash).",
    )

    # --- Ollama (modelos locais) ---
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        env="OLLAMA_BASE_URL",
        description="URL do servidor Ollama; padrão localhost na porta 11434.",
    )
    OLLAMA_MODEL: str = Field(
        default="qwen3-coder:30b",
        env="OLLAMA_MODEL",
        description=(
            "Nome do modelo Ollama (ex.: llama3.2, qwen3-coder:30b); deve existir no servidor."
        ),
    )

    # --- Escolha do provider de IA ---
    DEFAULT_IA_PROVIDER: str = Field(
        default="openai",
        env="DEFAULT_IA_PROVIDER",
        description="Provider principal: openai, google-generativeai (gemini) ou ollama.",
    )
    FALLBACK_IA_PROVIDER: str = Field(
        default="ollama",
        env="FALLBACK_IA_PROVIDER",
        description="Provider usado quando o principal falhar ou não estiver configurado.",
    )

    # --- API (documentação e modo debug) ---
    API_TITLE: str = Field(
        default="Gestão Financeira Multi-IA",
        env="API_TITLE",
        description="Título exibido na documentação OpenAPI (Swagger).",
    )
    API_VERSION: str = Field(
        default="1.0.0",
        env="API_VERSION",
        description="Versão da API exibida na documentação.",
    )
    DEBUG: bool = Field(
        default=True,
        env="DEBUG",
        description="Se True, ativa modo debug (ex.: tracebacks detalhados, logs).",
    )

    class Config:
        """
        Configuração do carregamento de variáveis pelo pydantic-settings.
        """

        # Arquivo de onde as variáveis são lidas (além do ambiente).
        # O caminho é relativo ao diretório de trabalho ao subir a aplicação.
        env_file = ".env"

        # Nomes das variáveis de ambiente são case-sensitive (SUPABASE_URL ≠ supabase_url).
        case_sensitive = True


# Instância única usada em toda a aplicação: from app.core.config import settings
settings = Settings()
