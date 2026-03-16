"""
Testes do módulo app.services.ia.config.

Cobre:
- get_config(tipo): retorno da ProviderConfig para openai, gemini, ollama
  e exceção para tipo inexistente.
- get_prompt(nome, **kwargs): preenchimento correto dos placeholders para
  extrair_despesa, classificar_categoria, gerar_relatorio e perguntar,
  e exceção para nome de prompt inexistente.
- Constantes PROVIDER_CONFIGS e CATEGORIA_VALIDAS: presença dos provedores
  e das categorias esperadas.
"""

import pytest
from datetime import date

from app.services.ia.config import (
    get_config,
    get_prompt,
    PROVIDER_CONFIGS,
    CATEGORIA_VALIDAS,
    ProviderConfig,
)


# -----------------------------------------------------------------------------
# Testes de get_config
# -----------------------------------------------------------------------------


class TestGetConfig:
    """
    Garante que get_config retorna a configuração correta para cada tipo
    e que rejeita tipos não configurados.
    """

    def test_get_config_openai(self) -> None:
        """OpenAI deve ter nome OpenAI, tipo openai, api_key_attr e suporta_json True."""
        cfg = get_config("openai")
        assert cfg.name == "OpenAI"
        assert cfg.tipo == "openai"
        assert cfg.api_key_attr == "OPENAI_API_KEY"
        assert cfg.suporta_json is True

    def test_get_config_gemini(self) -> None:
        """Gemini deve ter precisa_limpeza True e sufixo de prompt pedindo JSON."""
        cfg = get_config("gemini")
        assert cfg.name == "Google Gemini"
        assert cfg.precisa_limpeza is True
        assert "JSON" in cfg.prompt_suffix

    def test_get_config_ollama(self) -> None:
        """Ollama deve ter base_url_attr e prefix [INST] no prompt."""
        cfg = get_config("ollama")
        assert cfg.name == "Ollama"
        assert cfg.base_url_attr == "OLLAMA_BASE_URL"
        assert "[INST]" in cfg.prompt_prefix

    def test_get_config_tipo_invalido_levanta(self) -> None:
        """Tipo não existente em PROVIDER_CONFIGS deve levantar ValueError."""
        with pytest.raises(ValueError, match="não encontrado"):
            get_config("provider_inexistente")


# -----------------------------------------------------------------------------
# Testes de get_prompt
# -----------------------------------------------------------------------------


class TestGetPrompt:
    """
    Garante que cada prompt é preenchido com os kwargs corretos e que
    o texto resultante contém os valores passados e trechos esperados (ex.: JSON).
    """

    def test_extrair_despesa_preenche_placeholders(self) -> None:
        """Prompt extrair_despesa deve conter texto, data_hoje, categorias e menção a JSON."""
        texto = "Almoço 30 reais"
        data_hoje = date.today().isoformat()
        categorias = "alimentacao, transporte, outros"
        prompt = get_prompt(
            "extrair_despesa",
            texto=texto,
            data_hoje=data_hoje,
            categorias=categorias,
        )
        assert texto in prompt
        assert data_hoje in prompt
        assert categorias in prompt
        assert "JSON" in prompt

    def test_classificar_categoria_preenche_placeholders(self) -> None:
        """Prompt classificar_categoria deve conter descricao e categorias."""
        descricao = "Gasolina no posto"
        categorias = "alimentacao, transporte, outros"
        prompt = get_prompt(
            "classificar_categoria",
            descricao=descricao,
            categorias=categorias,
        )
        assert descricao in prompt
        assert categorias in prompt

    def test_gerar_relatorio_preenche_dados(self) -> None:
        """Prompt gerar_relatorio deve conter o JSON de dados passado."""
        dados = '{"receitas": 5000, "despesas": 3000}'
        prompt = get_prompt("gerar_relatorio", dados=dados)
        assert dados in prompt

    def test_perguntar_preenche_contexto_e_pergunta(self) -> None:
        """Prompt perguntar deve conter contexto e pergunta."""
        contexto = "Receita: 5000, Despesas: 3000"
        pergunta = "Qual o saldo?"
        prompt = get_prompt("perguntar", contexto=contexto, pergunta=pergunta)
        assert contexto in prompt
        assert pergunta in prompt

    def test_prompt_inexistente_levanta(self) -> None:
        """Nome de prompt que não existe em PROMPT deve levantar ValueError."""
        with pytest.raises(ValueError, match="Prompt .* não encontrado"):
            get_prompt("nome_que_nao_existe", texto="x")


# -----------------------------------------------------------------------------
# Testes das constantes (categorias e provedores)
# -----------------------------------------------------------------------------


class TestCategoriasEProviders:
    """
    Verifica que as constantes globais têm o conteúdo esperado:
    categorias válidas e os três provedores (openai, gemini, ollama).
    """

    def test_categorias_validas_contem_esperadas(self) -> None:
        """CATEGORIA_VALIDAS deve ter exatamente as sete categorias padrão."""
        esperadas = {
            "alimentacao",
            "transporte",
            "saude",
            "educacao",
            "moradia",
            "lazer",
            "outros",
        }
        assert set(CATEGORIA_VALIDAS.keys()) == esperadas

    def test_provider_configs_tem_openai_gemini_ollama(self) -> None:
        """PROVIDER_CONFIGS deve conter as chaves openai, gemini e ollama."""
        assert "openai" in PROVIDER_CONFIGS
        assert "gemini" in PROVIDER_CONFIGS
        assert "ollama" in PROVIDER_CONFIGS

