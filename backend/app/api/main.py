"""
Módulo principal da API.

Aqui é feita a configuração central da aplicação FastAPI:
- criação da instância da aplicação (`app`)
- configuração de logging
- configuração de CORS (quem pode acessar a API)
- registro das rotas (despesas, IA, relatórios)
- definição de endpoints básicos (`/` e `/health`)
- definição de um handler global para exceções não tratadas
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes import despesas, ia, relatorios

import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DE LOGGING
# ---------------------------------------------------------------------------
# O logging é utilizado para registrar eventos importantes da aplicação,
# como erros, alertas e informações de execução. Isso facilita o diagnóstico
# de problemas e o monitoramento da API em produção.
logging.basicConfig(
    # Define o nível mínimo de log a ser exibido.
    # Em modo DEBUG (desenvolvimento) mostramos logs de nível INFO para cima,
    # em modo produção (DEBUG=False) mostramos apenas WARNING ou níveis mais altos.
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    # Define o formato padrão das mensagens de log:
    # - %(asctime)s : data e hora do evento
    # - %(name)s    : nome do logger (normalmente o módulo)
    # - %(levelname)s : nível do log (INFO, WARNING, ERROR, etc.)
    # - %(message)s : mensagem propriamente dita
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

)

# Cria um logger específico para este módulo, permitindo identificar
# nas mensagens de log de qual parte do código elas se originaram.
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# INSTÂNCIA PRINCIPAL DA APLICAÇÃO FASTAPI
# ---------------------------------------------------------------------------
# Aqui criamos o objeto `app`, que representa a aplicação web.
# Nele configuramos título, versão, modo debug e URLs da documentação.
app = FastAPI(
    # Título da API, utilizado na documentação automática.
    title=settings.API_TITLE,
    # Versão da API, também exibida na documentação.
    version=settings.API_VERSION,
    # Define se a aplicação está em modo debug (útil em desenvolvimento).
    debug=settings.DEBUG,
    # Endereço da interface de documentação Swagger UI.
    # Em produção (DEBUG=False), a doc pode ser ocultada por segurança.
    docs_url="/docs" if settings.DEBUG else None,
    # Endereço da interface de documentação Redoc.
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DE CORS (Cross-Origin Resource Sharing)
# ---------------------------------------------------------------------------
# CORS controla quais origens (domínios/portas) podem acessar esta API.
# Isso é importante porque o navegador bloqueia por padrão requisições
# vindas de outra origem por motivos de segurança.
app.add_middleware(
    CORSMiddleware,
    # Lista de origens permitidas a fazer requisições à API.
    allow_origins=[
        "http://localhost:8501",  # Aplicação Streamlit rodando localmente
        "http://localhost:3000",  # Aplicação React em modo de desenvolvimento
        "http://*.streamlit.app",  # Aplicações hospedadas no Streamlit Cloud
    ],
    # Permite o envio de cookies ou credenciais em requisições cross-origin.
    allow_credentials=True,
    # Permite todos os métodos HTTP (GET, POST, PUT, DELETE, etc.).
    allow_methods=["*"],
    # Permite todos os cabeçalhos customizados nas requisições.
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# REGISTRO DOS MÓDULOS DE ROTAS (ROUTERS)
# ---------------------------------------------------------------------------
# Aqui conectamos os routers específicos (despesas, IA, relatórios)
# na aplicação principal, todos sob o prefixo "/api".
app.include_router(despesas.router, prefix="/api")
app.include_router(ia.router, prefix="/api")
app.include_router(relatorios.router, prefix="/api")


# ---------------------------------------------------------------------------
# ENDPOINT RAIZ ("/")
# ---------------------------------------------------------------------------
# Este endpoint serve como "página inicial" da API, retornando
# informações básicas sobre o serviço, como nome, versão e status.
@app.get("/")
async def root():
    """
    Rota raiz da API.

    Retorna um resumo com:
    - nome e versão da API
    - status de disponibilidade
    - link para a documentação (quando em modo debug)
    - lista de provedores de IA suportados
    """
    return {
        # Nome/título da API, vindo das configurações.
        "name": settings.API_TITLE,
        # Versão atual da API.
        "version": settings.API_VERSION,
        # Indicador simples de que a API está online.
        "status": "online",
        # URL da documentação Swagger. Somente é populada quando o DEBUG está ativo.
        "docs": f"{settings.API_URL}/docs" if settings.DEBUG else None,
        # Lista de provedores de IA que a aplicação suporta integrar.
        "ia_providers": ["openai", "gemini", "ollama", "claude"],
    }


# ---------------------------------------------------------------------------
# ENDPOINT DE HEALTH CHECK ("/health")
# ---------------------------------------------------------------------------
# Este endpoint é usado para verificar se a API está saudável e respondendo.
# Pode ser utilizado por ferramentas de monitoramento, orquestradores
# (como Kubernetes) e testes automatizados.
@app.get("/health")
async def health_check():
    """
    Verifica se a API está online e funcionando.

    Retorna:
    - status: string indicando saúde do serviço
    - timestamp: horário atual do servidor em formato ISO 8601
    """
    return {
        # Indica que a aplicação respondeu com sucesso.
        "status": "healthy",
        # Horário atual do servidor, útil para verificar latência e sincronização.
        "timestamp": datetime.now().isoformat(),  # type: ignore
    }


# ---------------------------------------------------------------------------
# HANDLER GLOBAL DE EXCEÇÕES
# ---------------------------------------------------------------------------
# Este handler captura quaisquer exceções não tratadas que ocorram
# durante o processamento das requisições. Em vez de expor detalhes
# internos do erro ao cliente, registramos o log completo e retornamos
# uma resposta genérica de erro interno.
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """
    Handler de exceções globais.

    Sempre que uma exceção não for capturada em outro lugar, este handler
    será chamado. Ele registra o erro nos logs e retorna uma resposta
    padronizada ao cliente.

    Args:
        request: objeto da requisição que gerou a exceção.
        exc: instância da exceção levantada.
    """
    # Registra um log de erro com a mensagem da exceção e o traceback completo,
    # o que facilita a investigação de problemas em produção.
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        # Código HTTP 500: erro interno do servidor.
        status_code=500,
        # Corpo da resposta em JSON, com mensagem genérica de erro.
        content={"error": "Erro interno do servidor"},
    )


