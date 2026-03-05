"""
Base para provedores de IA e modelo de extração de despesas.

Define a interface abstrata IAProvider (métodos que cada provedor — OpenAI,
Gemini, Ollama — deve implementar) e o schema ExtracaoDespesa, usado quando
a IA interpreta texto natural e devolve dados estruturados de uma despesa.
Inclui helpers para extrair JSON, valor e data de strings (respostas da IA ou
texto do usuário).
"""

import json
import re
from abc import ABC, abstractmethod
from datetime import date, datetime

from pydantic import BaseModel, Field


class ExtracaoDespesa(BaseModel):
    """
    Resultado da extração de uma despesa a partir de texto natural ou da IA.

    Usado quando o usuário descreve uma despesa em linguagem natural ou quando
    a IA processa um documento e devolve campos estruturados. Os campos
    valor, categoria, data e descricao são os dados principais; fonte, status
    e provedor indicam origem e pipeline; confianca reflete a certeza da
    extração (0.0 a 1.0); created_at/updated_at podem vir da IA ou ser
    preenchidos pelo backend.
    """

    valor: float = Field(..., description="Valor monetário da despesa.")
    categoria: str = Field(
        ...,
        description=(
            "Categoria da despesa (ex.: alimentacao, transporte); "
            "idealmente alinhada ao enum CategoriaDespesa."
        ),
    )
    data: date = Field(..., description="Data em que a despesa ocorreu.")
    descricao: str = Field(..., description="Descrição livre da despesa.")
    fonte: str = Field(
        ...,
        description=(
            "Origem do registro (ex.: manual, textual_natural, ocr); alinhado a FonteDespesa."
        ),
    )
    status: str = Field(
        ...,
        description="Status da despesa (ex.: pendente, confirmada); alinhado a StatusDespesa.",
    )
    provedor: str = Field(
        ...,
        description="Nome do provedor de IA que fez a extração (ex.: openai, gemini, ollama).",
    )
    confianca: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Grau de confiança da extração, entre 0 e 1 (ex.: score da IA ou heurística)."
        ),
    )
    created_at: datetime = Field(
        ..., description="Data e hora de criação do registro ou da extração."
    )
    updated_at: datetime = Field(
        ..., description="Data e hora da última atualização."
    )

    class Config:
        """Exemplo usado na documentação do schema (OpenAPI)."""

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
        """
        Nome legível do provedor para logs e respostas da API.

        Ex.: "OpenAI", "Google Gemini", "Ollama".
        """
        ...

    @property
    @abstractmethod
    def tipo(self) -> str:
        """
        Identificador do tipo do provedor para configuração e roteamento.

        Ex.: "openai", "google-generativeai", "ollama" (alinhado a DEFAULT_IA_PROVIDER).
        """
        ...

    @abstractmethod
    async def extrair_despesa(self, texto: str) -> ExtracaoDespesa:
        """
        Interpreta texto natural e devolve uma despesa estruturada.

        Args:
            texto: Frase ou parágrafo descrevendo a despesa
                (ex.: "Gastei 50 reais em transporte ontem").

        Returns:
            ExtracaoDespesa com valor, categoria, data, descrição etc. preenchidos.

        Raises:
            ValueError: Se o texto não puder ser interpretado ou a resposta da IA for inválida.
        """
        ...

    @abstractmethod
    async def classificar_categoria(self, texto: str) -> str:
        """
        Sugere a categoria da despesa com base na descrição ou no texto.

        Args:
            texto: Descrição da despesa ou trecho a classificar.

        Returns:
            Código da categoria (ex.: "alimentacao", "transporte"), alinhado a CategoriaDespesa.
        """
        ...

    @abstractmethod
    async def gerar_relatorio(self, despesas: dict) -> str:
        """
        Gera um relatório em texto (ou markdown) a partir de uma lista/estrutura de despesas.

        Args:
            despesas: Estrutura com despesas (ex.: lista de dicts ou de modelos) para sumarizar.

        Returns:
            Texto do relatório gerado pela IA.
        """
        ...

    @abstractmethod
    async def perguntar(self, pergunta: str, contexto: str) -> str:
        """
        Responde uma pergunta do usuário usando um contexto (ex.: despesas do mês, orçamento).

        Args:
            pergunta: Pergunta em linguagem natural.
            contexto: Texto ou dados estruturados que a IA deve usar como base.

        Returns:
            Resposta em texto gerada pela IA.
        """
        ...

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

            # Remove abertura de bloco markdown (```json ou ```)
            if texto.startswith("```json"):
                texto = texto[7:]
            elif texto.startswith("```"):
                texto = texto[3:]

            # Remove fechamento do bloco (``` no final)
            if texto.endswith("```"):
                texto = texto[:-3].strip()

            # Localiza o primeiro objeto JSON na string (suporta quebras de linha)
            json_match = re.search(r"\{.*\}", texto, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return json.loads(texto)
        except Exception as e:
            raise ValueError(f"Erro ao extrair JSON: {e}\nTexto: {texto}") from e

    async def _extrair_valor(self, texto: str) -> float:
        """
        Extrai um valor numérico de uma string (ex.: "R$ 50,00" ou "100.50").

        Remove "R$", aceita vírgula ou ponto como decimal e retorna um float.
        Útil para tratar respostas da IA ou entrada do usuário.

        Args:
            texto: String contendo um valor (ex.: "R$ 123,45" ou "10.5").

        Returns:
            Valor como float.

        Raises:
            ValueError: Se nenhum número for encontrado no texto.
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
