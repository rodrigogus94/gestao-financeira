"""
Configuração centralizada para todos os providers de IA.

Este módulo é o único lugar onde se definem as diferenças entre os provedores
(OpenAI, Google Gemini, Ollama): chaves de API, modelos, URLs, se suportam
resposta em JSON nativo, prefixos/sufixos de prompt, etc. Também concentra
os textos dos prompts usados pela IA (extração de despesa, classificação,
relatório, perguntas) e a lista de categorias válidas para despesas.

Uso típico: get_config("openai") para obter a config de um provedor;
get_prompt("extrair_despesa", texto=..., data_hoje=..., categorias=...)
para obter o prompt já com os placeholders preenchidos.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.core.config import settings
from datetime import date


# -----------------------------------------------------------------------------
# Modelo de configuração por provedor
# -----------------------------------------------------------------------------


class ProviderConfig(BaseModel):
    """
    Configuração específica de um provedor de IA (OpenAI, Gemini ou Ollama).

    Cada provedor tem um nome legível, um tipo (identificador interno), e
    atributos que indicam onde buscar no settings: api_key_attr (ex.: OPENAI_API_KEY),
    model_attr (ex.: OPENAI_MODEL), base_url_attr (usado pelo Ollama). Também
    define se a API suporta resposta em JSON nativo (suporta_json), se a resposta
    precisa de limpeza de markdown (precisa_limpeza), e prefixo/sufixo de prompt
    para adaptar o texto ao formato esperado por cada modelo (ex.: [INST]...[/INST] no Ollama).
    """

    name: str  # Nome legível (ex.: "OpenAI", "Google Gemini")
    tipo: str  # Identificador interno: "openai", "gemini", "ollama"
    api_key_attr: Optional[str] = None  # Nome do atributo em settings para API key (None no Ollama)
    model_attr: str  # Nome do atributo em settings para o modelo (ex.: OPENAI_MODEL)
    base_url_attr: Optional[str] = None  # Para Ollama: OLLAMA_BASE_URL
    temperatura_attr: float = 0.0  # Temperatura padrão (0 = mais determinístico)
    max_tokens_attr: int = 1000  # Limite de tokens na resposta
    suporta_json: bool = True  # Se a API aceita response_format json_object (OpenAI sim; Gemini/Ollama não)
    precisa_limpeza: bool = False  # Se a resposta pode vir com ```json ... ``` e precisa ser limpa
    prompt_prefix: str = ""  # Texto colado antes do prompt (ex.: "[INST]" no Ollama)
    prompt_suffix: str = ""  # Texto colado depois (ex.: "Responda apenas com JSON..." no Gemini)


# -----------------------------------------------------------------------------
# Configurações por provedor (openai, gemini, ollama)
# -----------------------------------------------------------------------------

# Dicionário que mapeia o identificador do provedor ("openai", "gemini", "ollama")
# para sua ProviderConfig. Usado pela factory e pelo provider para saber como
# chamar a API e tratar a resposta.
PROVIDER_CONFIGS = {
    "openai": ProviderConfig(
        name="OpenAI",
        tipo="openai",
        api_key_attr="OPENAI_API_KEY",
        model_attr="OPENAI_MODEL",
        suporta_json=True,  # OpenAI aceita response_format={"type": "json_object"}
        prompt_prefix="",
        prompt_suffix="",
    ),
    "gemini": ProviderConfig(
        name="Google Gemini",
        tipo="gemini",
        api_key_attr="GEMINI_API_KEY",
        model_attr="GEMINI_MODEL",
        suporta_json=False,
        precisa_limpeza=True,  # Resposta pode vir com markdown; extraímos o JSON
        prompt_prefix="",
        prompt_suffix="\n Responda apenas com o JSON válido e sem nenhum outro texto.",
    ),
    "ollama": ProviderConfig(
        name="Ollama",
        tipo="ollama",
        model_attr="OLLAMA_MODEL",
        base_url_attr="OLLAMA_BASE_URL",
        suporta_json=False,
        precisa_limpeza=True,
        temperatura_attr=0.1,
        prompt_prefix="[INST]",  # Formato instrução para modelos Llama/etc.
        prompt_suffix="[/INST]",
    ),

    "claude": ProviderConfig(
        name="Anthropic Claude",
        tipo="claude",
        api_key_attr="CLAUDE_API_KEY",
        model_attr="CLAUDE_MODEL",
        suporta_json=True,
        precisa_limpeza=True,
        temperatura_attr=0.1,
        prompt_prefix="\n\nHuman",
        prompt_suffix="\n\nAssistant",
    ),
}


# -----------------------------------------------------------------------------
# Categorias válidas para despesas
# -----------------------------------------------------------------------------

# Conjunto de categorias aceitas no sistema. Usado nos prompts para a IA
# e para validar a categoria retornada. Chave e valor iguais para facilitar
# uso em listas (join) e checagem de pertencimento.
CATEGORIA_VALIDAS = {
    "alimentacao": "alimentacao",
    "transporte": "transporte",
    "saude": "saude",
    "educacao": "educacao",
    "moradia": "moradia",
    "lazer": "lazer",
    "outros": "outros",
}


# -----------------------------------------------------------------------------
# Prompts padronizados (templates com placeholders)
# -----------------------------------------------------------------------------

# Os prompts são strings com placeholders no formato {nome}. Eles NÃO usam
# f-string para não serem avaliados na carga do módulo. O preenchimento é
# feito em get_prompt(nome, **kwargs), que chama .format(**kwargs).
# Placeholders comuns: {texto}, {data_hoje}, {categorias}, {dados}, {contexto}, {pergunta}, {descricao}.
PROMPT = {
    # Prompt para extrair de um texto natural os campos: valor, categoria, data, descrição.
    # A IA deve devolver apenas um JSON válido. Usado em extrair_despesa() no provider.
    "extrair_despesa": """
        Você é um assistente financeiro especializado em extrair informações de despesas.

        Você receberá um texto que contém uma despesa.

        Texto do usuário: "{texto}"
        Data atual: {data_hoje}

        Categorias válidas: {categorias}

        Extraia as informações e retorne APENAS um JSON válido no formato:
        {{
            "valor": 0.0,
            "categoria": "categoria",
            "data": "YYYY-MM-DD",
            "descricao": "descricao curta"
        }}

        Regras:
        - Se a data não for informada, use a data atual.
        - Se a categoria não for informada, use a categoria "outros".
        - Valor deve ser em reais, sem símbolo de moeda.
        - Se a descrição não for informada, use uma descrição curta.
        - Descrição deve ser concisa e direta, sem texto adicional.

        Retorne APENAS o JSON válido, sem nenhum texto adicional.
    """,

    # Prompt para classificar uma descrição em uma das categorias válidas.
    # Resposta esperada: apenas o nome da categoria em minúsculas.
    "classificar_categoria": """
        Classifique a seguinte despesa em uma das categorias válidas:
        {categorias}

        Despesa: "{descricao}"

        Responda apenas com o nome da categoria, em minúsculas, sem ponto ou texto extra.
    """,

    # Prompt para gerar um relatório em texto a partir de dados financeiros (JSON).
    # Usado em gerar_relatorio() no provider. O relatório deve incluir resumo,
    # categorias, sugestões de economia e alertas.
    "gerar_relatorio": """
        Com base nos dados financeiros abaixo, gere um relatório detalhado e conciso
        de gastos e receitas, com insights e sugestões de economia.

        Dados: {dados}

        O relatório deve ser em português brasileiro, com um estilo claro e objetivo.
        1. Resumo mensal
        2. Resumo dos gastos totais
        3. Categorias de gastos
        4. Despesas mais caras
        5. Despesas mais baratas
        6. Despesas mais frequentes
        7. Despesas menos frequentes
        8. Despesas mais recentes
        9. Despesas menos recentes
        10. Despesas mais antigas
        11. Despesas menos antigas
        12. Principais categorias
        13. Padrões identificados
        14. Sugestões de economia
        15. Alertas importantes

        O relatório deve ser em português brasileiro, com estilo claro e objetivo.
        Inclua: resumo mensal, gastos totais, categorias, despesas mais altas e mais
        baixas, padrões identificados, sugestões de economia e alertas importantes.
        Tom profissional e útil.
    """,

    # Prompt para responder uma pergunta do usuário com base em um contexto (dados financeiros).
    # Usado em perguntar(). A IA deve basear-se apenas no contexto fornecido.
    "perguntar": """
        Contexto (dados financeiros do usuário):
        {contexto}

        Pergunta: "{pergunta}"

        Responda de forma clara e objetiva, no mesmo idioma do contexto.
        Baseie-se apenas nos dados fornecidos. Seja específico e use números quando possível.
    """,
}


# -----------------------------------------------------------------------------
# Funções de acesso à configuração e aos prompts
# -----------------------------------------------------------------------------


def get_config(tipo: str) -> ProviderConfig:
    """
    Retorna a configuração do provedor de IA para o tipo informado.

    Args:
        tipo: Identificador do provedor ("openai", "gemini" ou "ollama").

    Returns:
        ProviderConfig com todos os parâmetros daquele provedor.

    Raises:
        ValueError: Se o tipo não existir em PROVIDER_CONFIGS.
    """
    if tipo not in PROVIDER_CONFIGS:
        raise ValueError(f"Provider de IA '{tipo}' não encontrado.")
    return PROVIDER_CONFIGS[tipo]


def get_prompt(nome: str, **kwargs) -> str:
    """
    Retorna o prompt com o nome dado, com os placeholders substituídos pelos kwargs.

    Os templates em PROMPT usam placeholders como {texto}, {data_hoje}, {categorias},
    {dados}, {contexto}, {pergunta}, {descricao}. Todos os nomes passados em kwargs
    são aplicados com .format(**kwargs). Qualquer placeholder não preenchido
    causará KeyError.

    Args:
        nome: Chave do prompt em PROMPT ("extrair_despesa", "classificar_categoria",
              "gerar_relatorio", "perguntar").
        **kwargs: Parâmetros para preencher o template (ex.: texto="...", data_hoje="...").

    Returns:
        String do prompt já formatada.

    Raises:
        ValueError: Se o nome não existir em PROMPT.
    """
    if nome not in PROMPT:
        raise ValueError(f"Prompt '{nome}' não encontrado.")
    prompt = PROMPT[nome]
    return prompt.format(**kwargs)
