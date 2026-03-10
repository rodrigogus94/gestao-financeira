"""
Base para provedores de IA e modelo de extração de despesas.

Este módulo define:
1. ExtracaoDespesa: modelo Pydantic que representa o resultado da extração de uma
   despesa a partir de texto natural (valor, categoria, data, descrição, fonte,
   status, provedor, confiança e timestamps).
2. IAProvider: interface abstrata (ABC) que declara os métodos que qualquer provedor
   de IA deve implementar: extrair_despesa, classificar_categoria, gerar_relatorio,
   perguntar. Inclui helpers opcionais _extrair_json, _extrair_valor, _extrair_data
   para parsear respostas da IA ou texto do usuário.

A implementação concreta que usa essa base está em provider.py (classe IAProvider
que recebe o tipo "openai"|"gemini"|"ollama" e delega para a API correspondente).
"""

import json
import re
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone

from pydantic import BaseModel, Field


# =============================================================================
# Modelo de dados: resultado da extração de despesa
# =============================================================================


class ExtracaoDespesa(BaseModel):
    """
    Resultado da extração de uma despesa a partir de texto natural ou da IA.

    Usado quando o usuário descreve uma despesa em linguagem natural (ex.: "Gastei
    50 reais em Uber ontem") ou quando a IA processa um documento e devolve campos
    estruturados. Os campos valor, categoria, data e descricao são os dados principais
    da despesa; fonte indica a origem do registro (manual, textual_natural, ocr);
    status (pendente, confirmada); provedor indica qual IA fez a extração; confianca
    reflete a certeza da extração (0.0 a 1.0). created_at e updated_at são
    preenchidos automaticamente se não fornecidos (default_factory com UTC).
    """

    valor: float = Field(..., description="Valor monetário da despesa em reais.")
    categoria: str = Field(
        ...,
        description=(
            "Categoria da despesa (ex.: alimentacao, transporte); "
            "deve ser uma das chaves de CATEGORIA_VALIDAS em config."
        ),
    )
    data: date = Field(..., description="Data em que a despesa ocorreu (YYYY-MM-DD).")
    descricao: str = Field(..., description="Descrição curta da despesa.")
    fonte: str = Field(
        ...,
        description="Origem do registro: manual, textual_natural, ocr.",
    )
    status: str = Field(
        ...,
        description="Status da despesa: pendente, confirmada, etc.",
    )
    provedor: str = Field(
        ...,
        description="Nome do provedor de IA que fez a extração (ex.: OpenAI, Ollama).",
    )
    confianca: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Grau de confiança da extração entre 0 e 1 (score da IA ou heurística).",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data e hora de criação do registro ou da extração (UTC).",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data e hora da última atualização (UTC).",
    )

    class Config:
        """Configuração do modelo para documentação OpenAPI e serialização."""

        json_schema_extra = {
            "examples": [
                {
                    "valor": 100.00,
                    "categoria": "alimentacao",
                    "data": "2026-01-01",
                    "descricao": "Compra de alimentos",
                    "fonte": "manual",
                    "status": "pendente",
                    "provedor": "openai",
                    "confianca": 0.95,
                    "created_at": "2026-01-01T12:00:00",
                    "updated_at": "2026-01-01T12:00:00",
                }
            ]
        }


# =============================================================================
# Interface abstrata do provedor de IA
# =============================================================================


class IAProvider(ABC):
    """
    Interface base para todos os provedores de IA do sistema.

    Cada implementação (OpenAI, Gemini, Ollama) deve definir nome/tipo e
    implementar: extração de despesa a partir de texto, classificação de
    categoria, geração de relatório e perguntas com contexto. Os métodos
    _extrair_json, _extrair_valor e _extrair_data são helpers opcionais
    para parsear respostas da IA ou texto do usuário.
    """

    @property
    @abstractmethod
    def nome(self) -> str:
        """Nome legível do provedor para logs e respostas (ex.: OpenAI, Ollama)."""
        ...

    @property
    @abstractmethod
    def tipo(self) -> str:
        """Identificador do tipo para configuração (ex.: openai, gemini, ollama)."""
        ...

    @abstractmethod
    async def extrair_despesa(self, texto: str) -> ExtracaoDespesa:
        """
        Interpreta texto natural e devolve uma despesa estruturada.

        Args:
            texto: Frase descrevendo a despesa (ex.: "Gastei 50 reais em transporte ontem").

        Returns:
            ExtracaoDespesa com valor, categoria, data, descrição preenchidos.

        Raises:
            ValueError: Se o texto não puder ser interpretado ou a resposta da IA for inválida.
        """
        ...

    @abstractmethod
    async def classificar_categoria(self, texto: str) -> str:
        """
        Sugere a categoria da despesa com base na descrição.

        Args:
            texto: Descrição da despesa a classificar.

        Returns:
            Código da categoria (ex.: alimentacao, transporte).
        """
        ...

    @abstractmethod
    async def gerar_relatorio(self, despesas: dict) -> str:
        """
        Gera um relatório em texto a partir de uma estrutura de despesas.

        Args:
            despesas: Dict ou estrutura com despesas para sumarizar.

        Returns:
            Texto do relatório gerado pela IA.
        """
        ...

    @abstractmethod
    async def perguntar(self, pergunta: str, contexto: str) -> str:
        """
        Responde uma pergunta usando um contexto (ex.: despesas do mês).

        Args:
            pergunta: Pergunta em linguagem natural.
            contexto: Dados que a IA deve usar como base.

        Returns:
            Resposta em texto gerada pela IA.
        """
        ...

    # -------------------------------------------------------------------------
    # Helpers opcionais para parsear respostas da IA ou texto do usuário
    # -------------------------------------------------------------------------

    async def _extrair_json(self, texto: str) -> dict:
        """
        Extrai um objeto JSON de uma string que pode conter markdown ou texto em volta.

        Remove blocos ```json ... ``` se existirem e localiza o primeiro {...}
        na string para fazer o parse. Útil quando a IA devolve JSON embutido
        em markdown ou com texto antes/depois.

        Args:
            texto: String que contém JSON (possivelmente dentro de ```json ... ```).

        Returns:
            Dicionário resultante do json.loads.

        Raises:
            ValueError: Se não houver JSON válido ou o parse falhar.
        """
        try:
            texto = texto.strip()
            if texto.startswith("```json"):
                texto = texto[7:]
            elif texto.startswith("```"):
                texto = texto[3:]
            if texto.endswith("```"):
                texto = texto[:-3].strip()
            json_match = re.search(r"\{.*\}", texto, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(texto)
        except Exception as e:
            raise ValueError(f"Erro ao extrair JSON: {e}\nTexto: {texto}") from e

    async def _extrair_valor(self, texto: str) -> float:
        """
        Extrai um valor numérico de uma string (ex.: "R$ 50,00" ou "100.50").

        Remove "R$", aceita vírgula ou ponto como decimal. Útil para tratar
        respostas da IA ou entrada do usuário.

        Args:
            texto: String contendo um valor monetário ou numérico.

        Returns:
            Valor como float.

        Raises:
            ValueError: Se nenhum número for encontrado.
        """
        texto_limpo = texto.replace("R$", "").strip()
        padrao = r"(\d+[.,]?\d*)"
        match = re.search(padrao, texto_limpo)
        if match:
            valor_str = match.group(1).replace(",", ".")
            return float(valor_str)
        raise ValueError(f"Erro ao extrair valor: {texto}")

    async def _extrair_data(self, texto: str) -> date:
        """
        Extrai uma data no formato dd/mm/aaaa a partir de uma string.

        Procura a primeira ocorrência do padrão 00/00/0000 no texto.
        Útil para parsear respostas da IA ou entradas como "Paguei em 15/01/2026".

        Args:
            texto: String que contém uma data em dd/mm/aaaa.

        Returns:
            Objeto date correspondente.

        Raises:
            ValueError: Se nenhuma data no formato esperado for encontrada.
        """
        padrao = r"\d{2}/\d{2}/\d{4}"
        match = re.search(padrao, texto)
        if match:
            return datetime.strptime(match.group(), "%d/%m/%Y").date()
        raise ValueError(f"Erro ao extrair data no formato dd/mm/aaaa: {texto}")
