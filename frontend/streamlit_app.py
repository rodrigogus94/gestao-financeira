"""
Aplicação principal do frontend (Streamlit).

Este arquivo monta a interface do usuário para o projeto “Gestão Financeira Multi‑IA”.
Ele não contém a lógica de negócio (isso fica no backend FastAPI). Em vez disso, ele:

- configura a página Streamlit (título, layout, sidebar)
- inicializa estado de sessão (`st.session_state`) para manter objetos e dados entre reruns
- usa o `ApiClient` para chamar o backend (listar despesas, extrair via IA, relatórios, etc.)
- renderiza componentes de UI (ex.: seletor de IA) e telas em abas

Estrutura do app:
- Sidebar: configurações e ações globais (seleção de IA, recarregar cache, info do usuário)
- Abas (tabs):
  1) Entrada por texto (extração via IA)
  2) Documentos (placeholder)
  3) Dashboard (gráficos e tabela)
  4) Comparar IA (comparar provedores)
  5) Chat IA (assistente com base em despesas)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from api_client import ApiClient
from components.ia_selector import render_ia_selector


# -----------------------------------------------------------------------------
# 1) Configuração da página (deve vir antes de qualquer renderização relevante)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão Financeira Multi-IA",
    page_icon=":money_with_wings:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2) Inicialização de estado (session_state)
# -----------------------------------------------------------------------------
# Em Streamlit, o script “re-executa” a cada interação do usuário.
# Para manter objetos (ex.: ApiClient) e escolhas (ex.: provedor/estratégia),
# usamos `st.session_state` como armazenamento persistente por sessão.
if "api_client" not in st.session_state:
    # Cliente HTTP para conversar com o backend.
    # Observação: no backend atual, as rotas estão sob o prefixo `/api`,
    # então o base_url mais comum aqui é "http://localhost:8000/api".
    st.session_state.api_client = ApiClient(base_url="http://localhost:8000/api")

    # Token Bearer usado no backend em modo de desenvolvimento.
    # Em `backend/app/api/deps.py` o token "test-token" é aceito e retorna "usuario-teste".
    st.session_state.api_client.set_token("test-token")

# Configuração escolhida da IA (provedor + estratégia).
# IMPORTANTE: mantemos a chave do session_state como "config_ia" (usada abaixo).
if "config_ia" not in st.session_state:
    st.session_state.config_ia = {
        "provedor": "openai",
        "estrategia": "rapido",
        "provedor_nome": "OpenAI",
    }

# -----------------------------------------------------------------------------
# 3) Sidebar (configurações globais e ações gerais)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("Gestão Financeira Multi-IA")
    st.caption("Gerencie suas despesas com IA")
    st.divider()

    # Seletor de IA
    # Esse componente consulta o backend e devolve um dict com:
    # {"provedor": "...", "estrategia": "...", "provedor_nome": "..."}
    st.session_state.config_ia = render_ia_selector(st.session_state.api_client)
    st.divider()

    # Informações do usuário
    st.subheader("Informações do usuário")
    st.info("Modo demo")

    # Data de extração
    st.caption(f"Data de extração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Botão para recarregar
    if st.button("Recarregar dados"):
        # Limpa caches do Streamlit (dados cacheados em @st.cache_data, se existirem)
        st.cache_data.clear()
        # Força reexecução completa do app
        st.rerun()

# -----------------------------------------------------------------------------
# 4) Abas (telas principais)
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Entrada por texto", 
    "Documentos",
    "Dashboard",
    "Comparar IA",
    "Chat IA"
])

# -----------------------------------------------------------------------------
# 5) Aba 1: Entrada por texto (extração via IA)
# -----------------------------------------------------------------------------
with tab1:
    st.header("Registro rápido com IA")
    st.caption("Digite o texto da despesa e a IA extrairá os dados")

    col1, col2 = st.columns([2,1])

    with col1:
        texto = st.text_area(
            "Descreva a despesa:",
            placeholder="Ex: Gastei 100 reais em alimentação ontem",
             height=150
        )

    with col2:
        st.subheader("Configuração atual")
        st.info(f"Provedor: {st.session_state.config_ia['provedor_nome']}")
        st.info(f"Estratégia: {st.session_state.config_ia['estrategia']}")

        salvar = st.checkbox("Salvar despesa", value=True)

        if st.button("Processar", type = "primary", use_container_width = True):
            # `resultado` precisa sempre existir para o fluxo abaixo.
            resultado = {}

            if texto:
                with st.spinner("Processando..."):
                    # Chamar a API: extrair a despesa a partir do texto natural.
                    resultado = st.session_state.api_client.extrair_despesa(
                        texto=texto,
                        provedor=st.session_state.config_ia["provedor"],
                        estrategia=st.session_state.config_ia["estrategia"],
                        salvar=salvar,
                    )
            else:
                st.warning("Digite um texto para processar.")
            
            if resultado.get("sucesso"):
                extraido = resultado["extraido"]

                st.success("Despesa extraída com sucesso!")

                # Mostrar resultados em cards
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric(
                        "Valor",
                        f"R$ {extraido['valor']:.2f}",
                        delta = None
                    )
                with col_b:
                    st.metric(
                        "Categoria",
                        extraido['categoria'],
                        delta = None
                    )
                with col_c:
                    st.metric(
                        "Data",
                        extraido['data'],
                        delta = None
                    )

                st.info(f"Despesa extraída com {extraido['descricao']}")

                if extraido.get("confianca"):
                    st.progress(
                        extraido['confianca'],
                        # Percentual mostrado para o usuário (0–100%)
                        text=f"Confiança: {extraido['confianca'] * 100:.0f}%"

                    )
                
                # Metadados de execução (se o backend devolver)
                if resultado.get("provedor_usado") or resultado.get("estrategia"):
                    st.caption(
                        f"Usou: {resultado.get('provedor_usado', '-')}"
                        f" | Estratégia: {resultado.get('estrategia', '-')}"
                    )

                if resultado.get("despesa_id"):
                    st.success(f"Despesa salva com ID: {resultado['despesa_id']}")
                    st.balloons()
            
            else:
                # `st.erro` não existe; usamos `st.error`.
                st.error("Erro ao processar a despesa, tente novamente.")

    # Histórico de extrações
    with st.expander("Exemplos de extração"):
        st.markdown("""
        ### Exemplos de extração
        - "Gastei 100 reais em alimentação ontem"
        - "Gastei 100 reais em transporte ontem"
        - "Uber 25 reais ontem"
        
        Dicas:
        - Inclua o valor numérico
        - Mencione a categoria se possível
        - A data é opcional (Usa hoje se não especificado)
        
        """)

# -----------------------------------------------------------------------------
# 6) Aba 2: Documentos (placeholder)
# -----------------------------------------------------------------------------
with tab2:
    st.header("Registro de despesas com documentos")
    st.caption("Envie um documento de despesa e a IA extrairá os dados")

    st.info("""
        - Envie um documento de despesa (PDF, JPG, PNG)
        - A IA extrairá os dados da despesa
        - O documento será salvo no banco de dados
        - Você poderá visualizar o documento e os dados extraídos
        - Você poderá editar os dados extraídos
        - Você poderá salvar a despesa
        - Você poderá excluir a despesa
    """)

    # Placeholder para upload de documento
    arquivo = st.file_uploader(
        "Envie um documento de despesa", type=["pdf", "jpg", "png"], disabled = True )

    if arquivo:
        st.warning("Upload de documento não implementado ainda")
        st.info("Por favor, envie um documento de despesa")
        st.info("O documento será salvo no banco de dados")
        st.info("Você poderá visualizar o documento e os dados extraídos")
        st.info("Você poderá editar os dados extraídos")
        st.info("Você poderá salvar a despesa")
        st.info("Você poderá excluir a despesa")

# -----------------------------------------------------------------------------
# 7) Aba 3: Dashboard (relatórios + gráficos)
# -----------------------------------------------------------------------------
with tab3:
    st.header("Dashboard Financeiro")
    st.caption("Visualize suas despesas e orçamentos")

    # Seleção de período
    col1, col2, col3 = st.columns(3)
    with col1:
        mes = st.selectbox(
            "Mês:",
            range(1, 13),
            index = datetime.now().month - 1,
            key = "mes_dashboard"
        )
    
    with col2:
        # O parâmetro `index` do selectbox é a POSIÇÃO (0..N-1), não o valor do ano.
        # Como as opções começam em 2020, o índice do ano atual é (ano_atual - 2020).
        ano_atual = datetime.now().year
        ano_inicial = 2020
        opcoes_anos = list(range(ano_inicial, ano_atual + 1))
        index_ano = max(0, min(len(opcoes_anos) - 1, ano_atual - ano_inicial))

        ano = st.selectbox(
            "Ano:",
            opcoes_anos,
            index=index_ano,
            key = "ano_dashboard"
        )
    
    with col3:
       if st.button("Carregar dados",type = "primary", use_container_width = True):
            st.session_state.dados_carregados = True

    # A flag `dados_carregados` evita recomputar dados automaticamente a cada rerun.
    if st.session_state.get("dados_carregados"):
        with st.spinner("Carregando dados..."):
            # Buscar resumo mensal
            # (o método do ApiClient precisa existir/estar alinhado com o backend)
            resumo = st.session_state.api_client.resumo_mensal(ano, mes)

            # O backend atual retorna um dict com campos como: total, categorias, quantidade...
            if resumo and "total" in resumo:
                # Métricas principais
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Gasto",
                        f"R$ {resumo['total']:.2f}",

                    )
                with col2:
                    st.metric(
                        "Quantidade",
                        resumo.get("quantidade", 0)
                    )

                with col3:
                    st.metric(
                        "Média",
                        f"R$ {resumo['total']/resumo['quantidade']:.2f}"
                        if resumo.get("quantidade", 0) > 0
                        else "0.00"
                    )
                with col4:
                    st.metric(
                        "Média/Dia",
                        f"R$ {resumo.get('media_por_dia', 0):.2f}"
                    )
                
                # Gráficos
                col1, col2 = st.columns(2)

                with col1:
                    if resumo['categorias']:
                        # Gráfico de barras de categorias
                        df_categorias = pd.DataFrame(resumo['categorias'].items(), columns=['Categoria', 'Total'])
                        fig = px.bar(df_categorias, x='Categoria', y='Total', color='Categoria',
                                     title='Gastos por Categoria', text='Total')
                        st.plotly_chart(fig)

                with col2:
                    if resumo['categorias']:
                        # Gráfico de pizza de categorias
                        df_categorias = pd.DataFrame(resumo['categorias'].items(), columns=['Categoria', 'Total'])
                        fig = px.pie(df_categorias, values='Total', names='Categoria', title='Gastos por Categoria')
                        st.plotly_chart(fig)

                # Últimas despesas
                st.subheader("Últimas despesas")
                despesas_payload = st.session_state.api_client.listar_despesas(limite=10)
                despesas = despesas_payload.get("despesas", []) if isinstance(despesas_payload, dict) else despesas_payload

                if despesas:
                    df = pd.DataFrame(despesas)
                    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
                    df['valor'] = df['valor'].apply(lambda x: f"R$ {x:.2f}")

                    st.dataframe(
                        df[['data', 'valor', 'categoria', 'descricao', 'fonte']],
                        hide_index = True,
                        use_container_width = True
                    )
                else:
                    st.info("Nenhuma despesa encontrada")
            else:
                st.info(f"Sem dados para {mes:02d}/{ano}")

# -----------------------------------------------------------------------------
# 8) Aba 4: Comparar IAs (comparação entre provedores)
# -----------------------------------------------------------------------------
with tab4:
    st.header("Comparar desempenho de IAs")
    st.caption("Compare o desempenho de diferentes IAs")

    texto_comparar = st.text_input(
        "Digite o texto a ser comparado:",
        value = "Gastei 100 reais em alimentação ontem",
        key = "texto_comparar"

    )

    if st.button("Comparar agora", type = "primary"):
        with st.spinner("Consultando todos os provedores..."):
            # Chama o endpoint de comparação do backend via ApiClient.
            resultado = st.session_state.api_client.comparar_provedores(texto_comparar)

            if resultado and resultado.get("resultados"):
                # Tabela comparativa
                dados_tabela = []

                for provedor, dados in resultado["resultados"].items():
                    if "erro" in dados:
                        dados_tabela.append({
                            "Provedor": provedor.capitalize(),
                            "Status": "Erro",
                            "Valor": "-",
                            "Categoria": "-",
                            "Data": "-",
                            "Confiança": "-"
                        })
                    else:
                        dados_tabela.append({
                            "Provedor": provedor.capitalize(),
                            "Status": "Sucesso",
                            "Valor": f"R$ {dados['valor']:.2f}",
                            "Categoria": dados['categoria'],
                            "Data": dados['data'],
                            "Confiança": f"{dados['confianca']*100:.0f}%"
                        })
                st.subheader("Resultados por Provedor")
                df_tabela = pd.DataFrame(dados_tabela)
                st.dataframe(
                    df_tabela,
                    hide_index = True,
                    use_container_width = True
                )

                # Gráfico compartivo de valores
                valores = []
                for provedor, dados in resultado["resultados"].items():
                    if "valor" in dados:
                        valores.append({
                            "Provedor": provedor.capitalize(),
                            "Valor": f"R$ {dados['valor']:.2f}"
                        })
                
                if valores:
                    df_valores = pd.DataFrame(valores)
                    fig = px.bar(df_valores, x='Provedor', y='Valor', color='Provedor',
                                 title='Comparação de valores por Provedor', text='Valor', text_auto=True)
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig, use_container_with = True)
                
                # Mostrar Json Completo
                with st.expander("Ver json detalhado"):
                    st.json(resultado)
            else:
                st.error("Erro ao comparar IAs, tente novamente.")

# -----------------------------------------------------------------------------
# 9) Aba 5: Chat IA (assistente)
# -----------------------------------------------------------------------------
with tab5:
    st.header("Assistente Financeiro ")
    st.caption("Fale com a IA sobre suas despesas")

    # Inicialização histórico
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = [{
            "role": "assistant",
            "content": "Olá, sou a assistente financeira. Como posso ajudar você hoje?"
        }]

    # Exibir histórico
    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["role"]):
            st.write(mensagem["content"])

    # Input do usuário
    pergunta = st.chat_input("Ex: Quanto gastei em alimentação esse mês?")

    if pergunta:
        # Adicionar pergunta ao histórico
        st.session_state.mensagens.append({
            "role": "user",
            "content": pergunta
        })

        with st.chat_message("user"):
            st.write(pergunta)

        # O role padrão esperado é "assistant".
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                # Buscando contexto (últimas despesas)
                despesas_payload = st.session_state.api_client.listar_despesas(limite=50)
                despesas = despesas_payload.get("despesas", []) if isinstance(despesas_payload, dict) else despesas_payload
                
                if despesas:
                    # Criar contexto simples
                    # Soma valores das despesas; cada item deve ter a chave "valor".
                    total = sum(despesa.get("valor", 0) for despesa in despesas)
                    contexto = f"Total de despesas: R$ {total:.2f}. {len(despesas)} registros."

                    # TODO: Implementar pergunta real com IA
                    resposta = f"Com base nos seus dados, você tem {len(despesas)}\
                     despesas no total de R$ {total:.2f}. Para perguntas mais especificas, aguarde a implementação completa do chat."
                
                else:
                    resposta = "Você ainda não tem despesas registradas. Comece registrando uma despesa na aba\
                    Entradas por Texto."

                st.write(resposta)
                st.session_state.mensagens.append({"role": "assistant", "content": resposta})

# -----------------------------------------------------------------------------
# 10) Rodapé
# -----------------------------------------------------------------------------
st.divider()
st.caption("© 2025 - Gestão Financeira Multi-IA | Desenvolvido com Streamlit | FastAPI | Multi-IA")
        
        
        