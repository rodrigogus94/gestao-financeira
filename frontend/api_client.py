"""
Cliente HTTP do frontend (Streamlit) para conversar com o backend (FastAPI).

Este arquivo centraliza toda a comunicação do frontend com a API, para evitar:
- espalhar `requests.get/post` pela interface
- duplicar montagem de headers/autenticação
- repetir URLs/paths de endpoints em vários componentes

Fluxo típico no Streamlit:
1) A UI cria uma instância de `ApiClient(base_url=...)`.
2) A UI chama `set_token(...)` quando existir autenticação (Bearer token).
3) Cada método abaixo faz uma chamada HTTP (GET/POST/PUT/DELETE) e devolve JSON.
4) Em erro, o método mostra `st.error(...)` e devolve um payload padrão com erro.

Observação importante sobre `base_url`:
- Aqui, `base_url` deve apontar para a *base da API* usada pelos endpoints abaixo.
- No seu backend atual, as rotas são registradas com prefixo `/api` (ex.: `/api/ia/...`).
  Então, normalmente você vai usar `base_url="http://localhost:8000/api"` no frontend.
"""

import requests
import streamlit as st
from typing import Any, Dict, Optional
from datetime import date

class ApiClient:
    """
    Cliente para a API do backend.

    Responsabilidades:
    - guardar a URL base do backend (`base_url`)
    - guardar o token Bearer opcional (`token`)
    - gerar headers padronizados (`_headers`)
    - expor métodos por “área” (IA, Despesas, Relatórios), cada um chamando um endpoint

    Observação:
    - Os métodos retornam o JSON do backend (dict/list), ou um dict padrão em caso de erro.
    - O tratamento de erro aqui é “amigável para UI”: mostra `st.error` para o usuário.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Inicializa o cliente.

        Args:
            base_url: URL base da API. Em geral, no seu projeto:
                - backend rodando local: "http://localhost:8000/api"
                Ajuste conforme ambiente (Docker, deploy, etc.).
        """
        self.base_url = base_url
        # Token Bearer opcional (quando existir login/autenticação).
        # Quando definido, é enviado no header Authorization em todas as requisições.
        self.token = None
    
    def set_token(self, token: str):
        """
        Define o token de autenticação.

        Args:
            token: token Bearer (JWT ou token de desenvolvimento) usado pelo backend.
        """
        self.token = token
    
    def _headers(self) -> Dict[str, str]:
        """
        Retorna os headers da requisição.

        Regras:
        - Sempre envia JSON (`Content-Type: application/json`).
        - Se houver `self.token`, envia `Authorization: Bearer <token>`.

        Returns:
            Dict com os headers HTTP.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    # ---------------------------------------------------------------------
    # IA (Inteligência Artificial) — Endpoints
    # ---------------------------------------------------------------------
    def listar_provedores_ia(self) -> Dict[str, Any]:
        """
        Lista todos os provedores de IA disponíveis.

        Endpoint esperado (no backend):
        - GET `/ia/provedores`
          (se sua API estiver sob `/api`, então fica `/api/ia/provedores`)

        Returns:
            Um dict tipicamente no formato:
            {
              "provedores": [...],
              "estrategias": [...],
              "default": "...",
              "fallback": "..."
            }

        Em caso de erro, retorna um payload com listas vazias.
        """
        try:
            response = requests.get(
                f"{self.base_url}/ia/provedores", headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao listar provedores de IA: {e}")
            return {"provedores": [], "estrategias": []}

    
    def extrair_despesa(
        self,
        texto: str,
        provedor: Optional[str] = None,
        estrategia: Optional[str] = None,
        salvar: bool = True,
    ) -> Dict[str, Any]:
        """
        Extrai uma despesa a partir de texto natural.

        Objetivo:
        - enviar um texto (ex.: "Gastei 50 reais com almoço ontem")
        - receber uma extração estruturada (valor, categoria, data, descrição, etc.)
        - opcionalmente mandar o backend salvar a despesa no Supabase

        Endpoint esperado (backend atual):
        - POST `/api/ia/extrair-despesa` (no servidor)
          Como `base_url` costuma já conter `/api`, aqui chamamos `/ia/extrair-despesa`.

        Args:
            texto: texto em linguagem natural descrevendo a despesa.
            provedor: provedor desejado (ex.: "openai", "gemini", "ollama").
            estrategia: estratégia de seleção/agregação (ex.: "principal", "fallback").
            salvar: se True, o backend tenta persistir a despesa no Supabase.

        Returns:
            Dict com o resultado da extração (e eventualmente ID salvo) ou {"error": "..."}.
        """

        try:
            response = requests.post(
                f"{self.base_url}/ia/extrair-despesa",
                json={
                    "texto": texto,
                    "provedor": provedor,
                    "estrategia": estrategia,
                    # IMPORTANTE: o modelo do backend define o campo como `Salvar` (S maiúsculo).
                    "Salvar": salvar,
                },
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao extrair despesa: {e}")
            return {"error": str(e)}

    def comparar_provedores(self, texto: str) -> Dict[str, Any]:
        """
        Compara a extração de uma despesa usando diferentes provedores de IA.

        Endpoint esperado:
        - POST `/ia/comparar`

        Args:
            texto: texto da despesa a ser comparada entre provedores.

        Returns:
            Dict com os resultados por provedor (ou {"error": "..."} em falha).
        """
        try:
            response = requests.post(
                f"{self.base_url}/ia/comparar",
                json={
                    "texto": texto,
                },
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao comparar provedores: {e}")
            return {"error": str(e)}
            
    # ---------------------------------------------------------------------
    # Despesas — Endpoints
    # ---------------------------------------------------------------------

    def listar_despesas(
        self,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        categoria: Optional[str] = None,
        provedor: Optional[str] = None,
        status: Optional[str] = None,
        pagina: int = 1,
        limite: int = 10,
    ) -> Dict[str, Any]:
        """
        Lista todas as despesas com filtros opcionais.

        Endpoint esperado (no backend atual):
        - GET `/despesas/` (no projeto está sob router prefix "/despesas")

        Observação:
        - O backend atual recebe filtros como `data_inicio`, `data_fim`, `categoria` e `limit`.
        - Este cliente também manda `pagina`, `limite`, `provedor` e `status`.
          Se o backend não suportar esses parâmetros, ele tende a ignorá-los.

        Args:
            data_inicio/data_fim: filtro de data (inclusive).
            categoria: categoria da despesa (string/enumeration no backend).
            provedor/status: filtros opcionais (dependem do backend suportar).
            pagina/limite: paginação no frontend (depende do backend suportar).

        Returns:
            JSON do backend. Em caso de erro devolve um dict padrão com metadados de paginação.
        """
        
        # Monta querystring (params) apenas com os filtros definidos.
        params = {
            "pagina": pagina,
            "limite": limite,
        }
        if data_inicio:
            params["data_inicio"] = data_inicio.isoformat()
        if data_fim:
            params["data_fim"] = data_fim.isoformat()
        if categoria:
            params["categoria"] = categoria
        if provedor:
            params["provedor"] = provedor
        if status:
            params["status"] = status
        
        try:
            response = requests.get(
                f"{self.base_url}/despesas", headers=self._headers(), params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao listar despesas: {e}")
            return {"despesas": [], "total": 0, "pagina": pagina, "limite": limite}
            
    def criar_despesa_manual(self, despesa: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova despesa manual.

        Endpoint esperado:
        - POST `/despesas`

        Args:
            despesa: dict com os campos esperados pelo backend (ex.: valor, categoria, data, descricao).

        Returns:
            JSON da despesa criada, ou {"error": "..."} em caso de falha.
        """
        try:
            response = requests.post(
                f"{self.base_url}/despesas", json=despesa, headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao criar despesa manual: {e}")
            return {"error": str(e)}

    # ---------------------------------------------------------------------
    # Relatórios — Endpoints
    # ---------------------------------------------------------------------

    def resumo_mensal(self, ano: int, mes: int) -> Dict[str, float]:
        """
        Gera um resumo mensal das despesas.

        Endpoint esperado (no backend atual):
        - GET `/relatorios/mensal`

        Observação:
        - Este cliente chama `/relatorios/resumo-mensal`, que pode não existir.
          Se estiver diferente no backend, ajuste o path.

        Args:
            ano: ano do relatório (ex.: 2026).
            mes: mês do relatório (1–12).

        Returns:
            Dict com dados agregados (total, categorias, etc.) ou {"error": "..."} em falha.
        """
        try:
            response = requests.get(
                f"{self.base_url}/relatorios/resumo-mensal", 
                headers=self._headers(), params={"ano": ano, "mes": mes}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao gerar resumo mensal: {e}")
            return {"error": str(e)}
            
    def gastos_por_categoria(self, data_inicio: date, data_fim: date) -> Dict[str, float]:
        """
        Gera um relatório de gastos por categoria.

        Endpoint esperado:
        - GET `/relatorios/categoria`

        Args:
            data_inicio: data inicial do período.
            data_fim: data final do período.

        Returns:
            Dict categoria -> total (float) ou {"error": "..."} em falha.
        """
        try:
            response = requests.get(
                f"{self.base_url}/relatorios/categoria", 
                params={
                    "data_inicio": data_inicio.isoformat(),
                    "data_fim": data_fim.isoformat()
                },
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao gerar relatório de gastos por categoria: {e}")
            return {"error": str(e)}
            
    def gerar_insights(self, ano: int, mes: int) -> Dict[str, Any]:
        """
        Gera insights sobre as despesas.

        Endpoint esperado:
        - POST `/relatorios/insights`

        Args:
            ano: ano do relatório.
            mes: mês do relatório.

        Returns:
            Dict com insights e contexto (resumo) ou {"error": "..."} em falha.
        """
        try:
            response = requests.post(
                f"{self.base_url}/relatorios/insights", 
                params={"ano": ano, "mes": mes},
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao gerar insights: {e}")
            return {"error": str(e)}
            
    def gerar_relatorio(self, data_inicio: date, data_fim: date) -> Dict[str, Any]:
        """
        Gera um relatório das despesas.

        Observação:
        - No backend atual, as rotas disponíveis são: mensal, categoria, evolucao e insights.
        - Este método chama `/relatorios/gerar`, que pode ser um endpoint futuro.

        Args:
            data_inicio: data inicial do relatório.
            data_fim: data final do relatório.

        Returns:
            Dict com o relatório ou {"error": "..."} em falha.
        """
        try:
            response = requests.get(
                f"{self.base_url}/relatorios/gerar",
                params={
                    "data_inicio": data_inicio.isoformat(),
                    "data_fim": data_fim.isoformat()
                },
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erro ao gerar relatório: {e}")
            return {"error": str(e)}