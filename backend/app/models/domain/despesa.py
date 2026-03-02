"""
Modelos de domínio para Despesa.

Define os schemas Pydantic usados na API e no mapeamento com o banco (Supabase).
Inclui enums para categorias, status e fonte da despesa, além de modelos para
criação, leitura e atualização, com validações e exemplos para documentação OpenAPI.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CategoriaDespesa(str, Enum):
    """
    Categoria da despesa.

    Os valores devem coincidir com o CHECK da tabela `despesas` no Supabase.
    Usado para classificar gastos e para limites em orçamentos mensais.
    """

    ALIMENTACAO = "alimentacao"
    TRANSPORTE = "transporte"
    SAUDE = "saude"
    EDUCACAO = "educacao"
    MORADIA = "moradia"
    LAZER = "lazer"
    OUTROS = "outros"

    @classmethod
    def list_all(cls) -> list[str]:
        """
        Retorna a lista de todos os valores válidos da enum.

        Útil para validação em formulários, dropdowns e mensagens de erro
        que precisam exibir as opções permitidas.
        """
        return [c.value for c in cls]


class StatusDespesa(str, Enum):
    """
    Status do fluxo da despesa.

    - pendente: registrada, ainda não confirmada (ex.: sugestão por IA ou OCR).
    - confirmada: validada e contabilizada.
    - cancelada: desconsiderada (ex.: duplicata ou erro).
    """

    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"


class FonteDespesa(str, Enum):
    """
    Origem do registro da despesa.

    Indica como a despesa entrou no sistema: manual (usuário), texto natural
    (interpretação por IA), OCR (extração de documento) ou importação em lote.
    """

    MANUAL = "manual"
    TEXTUAL_NATURAL = "textual_natural"
    OCR = "ocr"
    IMPORTACAO = "importacao"


class DespesaBase(BaseModel):
    """
    Modelo base com os campos comuns de uma despesa.

    Contém apenas os dados de negócio reutilizados em criação e leitura.
    Não inclui identificador, usuário, fonte nem timestamps; esses ficam
    nos modelos que estendem esta base (DespesaCreate, DespesaInDB).
    """

    valor: float = Field(
        ..., gt=0, description="Valor da despesa em reais; deve ser maior que zero."
    )
    categoria: CategoriaDespesa = Field(
        ..., description="Categoria da despesa (ex.: alimentacao, transporte)."
    )
    data: date = Field(..., description="Data em que a despesa ocorreu.")
    descricao: str | None = Field(None, description="Descrição livre da despesa (opcional).")
    status: StatusDespesa = Field(
        default=StatusDespesa.PENDENTE,
        description="Status atual da despesa; padrão pendente.",
    )

    @field_validator("valor")
    @classmethod
    def valor_nao_negativo(cls, v: float) -> float:
        """
        Garante que o valor seja estritamente positivo.

        Complementa a restrição gt=0 do Field com uma mensagem de erro
        em português. Valores zero ou negativos são rejeitados.
        """
        if v <= 0:
            raise ValueError("Valor da despesa deve ser maior que 0")
        return v

    class Config:
        """Configurações do modelo para serialização e documentação."""

        # Exemplos usados no OpenAPI/Swagger para ilustrar o schema
        json_schema_extra = {
            "examples": [
                {
                    "valor": 100.00,
                    "categoria": "alimentacao",
                    "data": "2026-01-01",
                    "descricao": "Compra de alimentos",
                    "status": "pendente",
                }
            ]
        }


class DespesaCreate(DespesaBase):
    """
    Modelo para criação de uma nova despesa.

    Herda todos os campos de DespesaBase e adiciona usuario_id (obrigatório
    para associar ao dono dos dados), fonte (como foi registrada) e metadata
    (dados extras, ex.: resultado bruto do OCR ou da IA).
    Usado como body nas rotas POST de despesas.
    """

    usuario_id: str = Field(..., description="ID do usuário (ex.: UUID do Supabase Auth).")
    fonte: FonteDespesa = Field(
        default=FonteDespesa.MANUAL,
        description="Origem do registro: manual, textual_natural, ocr ou importacao.",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Metadados extras (ex.: texto original, confiança do OCR).",
    )


class DespesaInDB(DespesaBase):
    """
    Modelo que representa uma despesa tal como está armazenada no banco.

    Inclui id (chave primária), usuario_id, fonte, metadata e os timestamps
    created_at e updated_at. Usado ao ler registros do Supabase e ao
    retornar despesas nas respostas da API.
    """

    id: int = Field(..., description="Identificador único da despesa no banco.")
    usuario_id: str = Field(..., description="ID do usuário dono da despesa.")
    fonte: FonteDespesa = Field(
        default=FonteDespesa.MANUAL,
        description="Origem do registro da despesa.",
    )
    metadata: dict[str, Any] | None = Field(None, description="Metadados adicionais.")
    created_at: datetime = Field(..., description="Data e hora de criação do registro.")
    updated_at: datetime = Field(..., description="Data e hora da última atualização.")

    class Config:
        """
        Permite construir o modelo a partir de atributos de objeto (ORM/row).

        Necessário quando os dados vêm do Supabase ou de um ORM: Pydantic
        aceita kwargs com os nomes dos atributos em vez de um dicionário.
        """

        from_attributes = True


class DespesaUpdate(BaseModel):
    """
    Modelo para atualização parcial de uma despesa.

    Todos os campos são opcionais: apenas os enviados na requisição são
    alterados. Usado como body nas rotas PATCH/PUT de despesas.
    Não inclui usuario_id, fonte nem timestamps (geridos pelo backend).
    """

    valor: float | None = Field(
        None, gt=0, description="Novo valor; se enviado, deve ser maior que zero."
    )
    categoria: CategoriaDespesa | None = Field(None, description="Nova categoria.")
    data: date | None = Field(None, description="Nova data da despesa.")
    descricao: str | None = Field(None, description="Nova descrição.")
    status: StatusDespesa | None = Field(
        None, description="Novo status (ex.: confirmada, cancelada)."
    )
