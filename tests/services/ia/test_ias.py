#! /usr/bin/env python3
"""
Script de teste para as IAs.
Uso: uv run python scripts/test_ias.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Ajuste de sys.path (import do pacote `app`)
# -----------------------------------------------------------------------------
# Este script fica em `backend/scripts/`, mas os módulos da aplicação ficam em
# `backend/app/`. Para conseguir importar `app.services...` de forma consistente,
# adicionamos o diretório `backend/` ao sys.path antes de importar `app`.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

async def testar_ias() -> None:
    """
    Testa todos os provedores de IA e também as estratégias do IAManager.

    O que é testado:
    - **Por provedor**: para cada texto de teste, chama `provider.extrair_despesa(texto)`
      e imprime os campos extraídos + tempo de execução.
    - **Por estratégia**: para cada estratégia (`EstrategiaSelecao`), configura o
      `IAManager` e executa uma extração, para validar o fluxo (principal, fallback,
      paralelo, votação, rápido, preciso).

    Saída:
    - Logs no console (print) para inspeção rápida
    - Arquivo `Teste_IAS_Resultados.json` com um resumo serializado em JSON
    """

    # Importações do projeto (após ajustar sys.path acima).
    # Mantemos aqui dentro para evitar problemas de import quando o script é
    # executado a partir de diretórios diferentes e para não disparar regras
    # de lint relacionadas a imports após código.
    from app.services.ia.factory import IAProviderFactory
    from app.services.ia.manager import EstrategiaSelecao, IAManager

    print("Testando IAs...")
    print("=" * 50)

    # -------------------------------------------------------------------------
    # Textos de teste
    # -------------------------------------------------------------------------
    # Cada item tenta cobrir padrões comuns: valor em reais, data implícita,
    # compras online, assinatura/recorrência etc.
    textos_teste = [
        "Gastei 50 reais com almoço hoje",
        "Uber de 25 reais ontem",
        "Comprei um livro de 89,90 na Amazon",
        "Pagamento da academia 120 reais",
        "Ifood 35 reais ontem à noite"
    ]

    # -------------------------------------------------------------------------
    # 1) Provedores disponíveis (configurados) e status
    # -------------------------------------------------------------------------
    # `listar_provedores_disponiveis()` tenta instanciar cada provedor configurado
    # e informa se está "disponivel" ou "indisponivel" (com erro).
    provedores_info = IAProviderFactory.listar_provedores_disponiveis()
    provedores_ok = [p for p in provedores_info if p.get("status") == "disponivel"]

    print("Provedores configurados:")
    for p in provedores_info:
        status = p.get("status")
        tipo = p.get("tipo")
        nome = p.get("nome")
        erro = p.get("erro")
        if status == "disponivel":
            print(f"- {tipo} ({nome}): disponivel")
        else:
            print(f"- {tipo} ({nome}): indisponivel | erro={erro}")

    print("-"*50)

    resultados: dict[str, Any] = {
        "provedores": {},
        "estrategias": {},
        "timestamp": datetime.now().isoformat(),
    }

    for texto in textos_teste:
        print(f"Testando texto: {texto}")
        print("-"*50)

        for p in provedores_ok:
            tipo = p.get("tipo")
            try:
                provider = IAProviderFactory.get_provider(tipo)
                inicio = datetime.now()
                resultado = await provider.extrair_despesa(texto)
                tempo = (datetime.now() - inicio).total_seconds()

                print(f"Provedor: {provider.nome} ({provider.tipo}):")
                print(f"Valor: {resultado.valor:.2f}")
                print(f"Categoria: {resultado.categoria}")
                print(f"Data: {resultado.data.strftime('%d/%m/%Y')}")
                print(f"Descrição: {resultado.descricao}")
                print(f"Confiança: {resultado.confianca:.2f}")
                print(f"Tempo: {tempo:.2f} segundos")

                resultados["provedores"].setdefault(provider.tipo, []).append({
                    "texto": texto,
                    "tempo_s": tempo,
                    "resultado": resultado.model_dump(),
                })
            
            except Exception as e:
                print(f"\n {tipo} - Erro: {e}")
                
    print("\nResultados:")
    print("-"*50)
    print("Testando estratégia:")
    print("-"*50)

    manager = IAManager()

    # -------------------------------------------------------------------------
    # 2) Teste por estratégia (IAManager)
    # -------------------------------------------------------------------------
    # Iteramos sobre o Enum `EstrategiaSelecao` que define os modos suportados.
    for estrategia in EstrategiaSelecao:
        print(f"Testando estratégia: {estrategia.value}")
        manager.estrategia = estrategia

        try:
            inicio = datetime.now()
            resultado = await manager.extrair_despesa("Gastei 50 reais com almoço hoje")
            tempo = (datetime.now() - inicio).total_seconds()

            print(f"Resultado: R$ {resultado.valor:.2f} - {resultado.categoria}")
            print(f"Tempo: {tempo:.2f} segundos")
            print(f"Descrição: {resultado.descricao}")
            print(f"Usou: {resultado.provedor}")

            resultados["estrategias"][estrategia.value] = {
                "tempo_s": tempo,
                "resultado": resultado.model_dump(),
            }

        except Exception as e:
            print(f"Erro: {e}")
            resultados["estrategias"][estrategia.value] = {"erro": str(e)}


    # -------------------------------------------------------------------------
    # 3) Persistir resultados em JSON (para comparação e histórico)
    # -------------------------------------------------------------------------
    with open("Teste_IAS_Resultados.json", "w") as f:
        json.dump(resultados, f, indent=2, default=str)

    print("\n Resultados salvos em Teste_IAS_Resultados.json")

async def main():
    """
    Entry-point assíncrono do script.

    Mantém o padrão:
    - `main()` é async
    - `asyncio.run(main())` no bloco `if __name__ == "__main__"`
    """
    await testar_ias()

if __name__ == "__main__":
    # Executa o loop assíncrono e roda os testes.
    asyncio.run(main())
        

    
