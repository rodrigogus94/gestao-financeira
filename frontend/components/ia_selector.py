"""
Componente de UI (Streamlit) para seleção de IA.

Este módulo define um componente reutilizável que:
- consulta o backend para descobrir quais provedores de IA estão disponíveis
- permite ao usuário escolher um provedor e uma estratégia de extração
- exibe um “status” visual (disponível/indisponível) para cada provedor

Ele é pensado para ser chamado pela tela principal (`frontend/streamlit_app.py`)
ou por qualquer componente que precise dessas configurações.
"""

import streamlit as st

def render_ia_selector(api_client) -> dict:
    """
    Renderiza o seletor de provedores de IA.

    Como funciona:
    - Envolve as opções em um `st.expander` (não polui a tela principal).
    - Busca provedores/estratégias do backend via `api_client.listar_provedores_ia()`.
    - Monta duas colunas:
      - esquerda: escolha do provedor
      - direita: escolha da estratégia
    - Após a seleção, mostra o status de cada provedor em cards (colunas).

    Args:
        api_client: instância do cliente HTTP do frontend (ex.: `ApiClient`),
            que deve expor `listar_provedores_ia()` e devolver um dict no formato:
            {
              "provedores": [{"nome": "...", "tipo": "...", "status": "disponivel|indisponivel"}, ...],
              "estrategias": ["principal", "fallback", ...]
            }

    Returns:
        Um dict com a configuração escolhida para o restante da UI:
        - provedor: código/tipo do provedor (ex.: "openai")
        - estrategia: estratégia selecionada (ex.: "fallback")
        - provedor_nome: nome exibido para o usuário (ex.: "OpenAI")
    """
    with st.expander("Configuração de IA", expanded=False):

        # -----------------------------------------------------------------
        # 1) Buscar provedores e estratégias a partir do backend
        # -----------------------------------------------------------------
        # A ideia aqui é deixar o backend como “fonte de verdade”:
        # - ele sabe quais provedores estão configurados e saudáveis
        # - ele informa quais estratégias o manager suporta
        try:
            dados = api_client.listar_provedores_ia()
            provedores = dados.get("provedores", [])
            estrategias = dados.get("estrategias", [])
        except Exception:
            # Fallback de UI: se a API estiver fora do ar (ou ocorrer qualquer erro),
            # o componente ainda oferece opções “fixas” para o usuário.
            provedores = []
            estrategias = ["principal", "fallback", "paralelo", "votacao"]
            
        # Divide a área de seleção em duas colunas para ficar mais compacto.
        col1, col2 = st.columns(2)

        with col1:
            # -------------------------------------------------------------
            # 2) Montar lista de provedores (somente os disponíveis)
            # -------------------------------------------------------------
            # `provedores_opcoes`: lista de nomes que o usuário verá no selectbox
            # `provedores_map`: mapeia nome exibido -> código/tipo usado nas requisições
            provedores_opcoes = []
            provedores_map = {}

            for provedor in provedores:
                if provedor.get("status") == "disponivel":
                    nome = provedor.get("nome", provedor.get("tipo"))
                    provedores_opcoes.append(nome)
                    provedores_map[nome] = provedor.get("tipo")
            
            if not provedores_opcoes:
                # Se nada veio do backend (ou tudo indisponível), usamos um conjunto padrão.
                # Isso evita o componente “quebrar” e permite testes/demonstrações.
                provedores_opcoes = ["openai", "gemini", "ollama", "claude"]
                provedores_map = {
                    # IMPORTANTE: aqui o valor deve ser o *código/tipo* do provedor
                    # que o backend entende (ex.: "openai", "gemini"...).
                    "openai": "openai",
                    "gemini": "gemini",
                    "ollama": "ollama",
                    "claude": "claude",
                }

            provedor_selecionado = st.selectbox(
                "Provedor de IA", provedores_opcoes, 
                index=0,
                help = "Selecione o provedor de IA a ser usado para extração de despesas"
            
            )

            # Converte o nome escolhido (exibição) no código usado pela API.
            # Ex.: "OpenAI" -> "openai"
            provedores_codigo = provedores_map.get(provedor_selecionado, "openai")

        with col2:
            # -------------------------------------------------------------
            # 3) Montar lista de estratégias
            # -------------------------------------------------------------
            # Se o backend devolver a lista, usamos ela; senão, caímos no padrão.
            estrategias_opcoes = estrategias or [
                "principal",
                "fallback",
                "paralelo",
                "votacao",
                "rapido",
                "preciso",
            ]
            
            estrategia_selecionada = st.selectbox(
                "Estratégia",
                estrategias_opcoes, 
                index=0,
                help = "Selecione a estratégia de extração de despesas"
            )
    
    # ---------------------------------------------------------------------
    # 4) Status dos provedores (feedback visual)
    # ---------------------------------------------------------------------
    # Mostra uma visão rápida para o usuário entender se algum provider está indisponível.
    st.subheader("Status dos provedores")
    if provedores:
        cols = st.columns(len(provedores))
        for i, p in enumerate(provedores):
            with cols[i]:
                if p.get("status") == "disponivel":
                    st.success(f"Provedor {p.get('nome')} está disponível")
                else:
                    st.error(f"Provedor {p.get('nome')} está indisponível")
    else:
        st.info("Status indisponível: não foi possível obter a lista de provedores da API.")
    
    # ---------------------------------------------------------------------
    # 5) Dicas para o usuário (conteúdo informativo)
    # ---------------------------------------------------------------------
    st.caption(" **Dicas**")
    st.caption(" - OpenAI é o provedor de IA mais popular e confiável.")
    st.caption(" - Gemini é o provedor de IA da Google e é muito poderoso.")
    st.caption(" - Ollama é um provedor de IA de código aberto e é muito rápido.")
    st.caption(" - Claude é o provedor de IA da Anthropic e é muito preciso.")
    st.caption(" - Rapido é a estratégia de extração de despesas mais rápida.")
    st.caption(" - Preciso é a estratégia de extração de despesas mais precisa.")
    st.caption(" - Votação é a estratégia de extração de despesas que usa a votação para decidir a melhor extração.")
    st.caption(" - Fallback é a estratégia de extração de despesas que usa o provedor de IA fallback.")
    st.caption(" - Paralelo é a estratégia de extração de despesas que usa todos os provedores de IA em paralelo.")
    st.caption(" - Principal é a estratégia de extração de despesas que usa o provedor de IA principal.")

    # Retorna a seleção para ser usada por outros componentes/requests do frontend.
    return {
        "provedor": provedores_codigo,
        "estrategia": estrategia_selecionada,
        "provedor_nome": provedor_selecionado,
    }

