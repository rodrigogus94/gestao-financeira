"""
Testes do módulo app.services.ia.base.

Focam no modelo ExtracaoDespesa:
- Criação com campos mínimos e preenchimento automático de confiança (1.0),
  created_at e updated_at.
- Serialização para dict (model_dump) com todos os campos esperados.
- Validação: confiança fora do intervalo [0, 1] deve levantar ValidationError
  do Pydantic.
"""

import pytest
from datetime import date
from pydantic import ValidationError

from app.services.ia.base import ExtracaoDespesa


# -----------------------------------------------------------------------------
# Testes do modelo ExtracaoDespesa
# -----------------------------------------------------------------------------


class TestExtracaoDespesa:
    """
    Garante que ExtracaoDespesa valida e serializa corretamente e que
    os defaults (confianca, created_at, updated_at) são aplicados quando
    não fornecidos.
    """

    def test_criacao_minima_com_defaults(self) -> None:
        """
        Sem passar confianca, created_at e updated_at, o modelo deve
        usar confianca=1.0 e preencher created_at/updated_at com default_factory.
        """
        e = ExtracaoDespesa(
            valor=100.0,
            categoria="outros",
            data=date(2026, 1, 15),
            descricao="Teste",
            fonte="manual",
            status="pendente",
            provedor="openai",
        )
        assert e.valor == 100.0
        assert e.categoria == "outros"
        assert e.confianca == 1.0
        assert e.created_at is not None
        assert e.updated_at is not None

    def test_serializacao_json(self) -> None:
        """
        model_dump() deve produzir um dict com valor, categoria e os campos
        de timestamp (created_at, updated_at) para serialização JSON/API.
        """
        e = ExtracaoDespesa(
            valor=25.5,
            categoria="alimentacao",
            data=date(2026, 3, 10),
            descricao="Lanche",
            fonte="textual_natural",
            status="pendente",
            provedor="gemini",
            confianca=0.9,
        )
        d = e.model_dump()
        assert d["valor"] == 25.5
        assert d["categoria"] == "alimentacao"
        assert "created_at" in d
        assert "updated_at" in d

    def test_confianca_fora_do_intervalo_levanta(self) -> None:
        """
        confianca com valor > 1.0 (ou < 0) deve falhar na validação Pydantic
        (Field com ge=0, le=1) e levantar ValidationError.
        """
        with pytest.raises(ValidationError):
            ExtracaoDespesa(
                valor=10.0,
                categoria="outros",
                data=date.today(),
                descricao="x",
                fonte="manual",
                status="pendente",
                provedor="x",
                confianca=1.5,
            )

