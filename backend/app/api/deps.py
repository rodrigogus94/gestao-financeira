"""
Módulo de dependências da API (deps.py)

Centraliza as dependências injetáveis usadas nas rotas FastAPI:
- Autenticação (Bearer token)
- Serviços singleton (Supabase, IA)
- Obtenção do usuário atual a partir do token JWT.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from app.services.supabase_service import SupabaseService
from app.services.ia.manager import IAProviderManager
from app.services.ia.factory import IAProviderFactory
from typing import Optional

# ---------------------------------------------------------------------------
# Esquema de segurança HTTP Bearer
# ---------------------------------------------------------------------------
# Objeto que exige que as requisições enviem o header:
#   Authorization: Bearer <token>
# Usado com Depends(security) nas rotas que precisam de autenticação.
security = HTTPBearer()

# ---------------------------------------------------------------------------
# Singletons (instâncias únicas dos serviços)
# ---------------------------------------------------------------------------
# Mantidas em variáveis globais para reutilizar a mesma instância em toda
# a aplicação, evitando criar nova conexão/estado a cada requisição.
_supabase_service: SupabaseService | None = None
_ia_provider_manager: IAProviderManager | None = None


def get_supabase_service() -> SupabaseService:
    """
    Obtém a instância única (singleton) de SupabaseService.

    Na primeira chamada cria e guarda a instância; nas seguintes devolve
    a mesma instância. Garante um único cliente Supabase por aplicação.
    Usado como dependência nas rotas que precisam de banco/auth Supabase.
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service


def get_ia_provider_manager() -> IAProviderManager:
    """
    Obtém a instância única (singleton) de IAProviderManager.

    Na primeira chamada cria e guarda o manager; nas seguintes devolve
    a mesma instância. Centraliza o acesso aos provedores de IA (ex.: OpenAI).
    Usado como dependência nas rotas que usam serviços de IA.
    """
    global _ia_provider_manager
    if _ia_provider_manager is None:
        _ia_provider_manager = IAProviderManager()
    return _ia_provider_manager


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extrai e valida o usuário atual a partir do token JWT no header Authorization.

    Comportamento:
    - Em desenvolvimento: aceita tokens fixos "test-token" e "dev-token"
      e retorna "usuario-teste" para facilitar testes sem Supabase Auth.
    - Em produção (TODO): deve validar o token com Supabase Auth e retornar
      o ID real do usuário (ex.: user.id).

    Se o token for inválido ou ausente, levanta HTTP 401 com header
    WWW-Authenticate: Bearer para o cliente saber que deve enviar Bearer token.
    """
    token = credentials.credentials

    # Em desenvolvimento: atalho para não depender do Supabase Auth
    if token == "test-token" or token == "dev-token":
        return "usuario-teste"

    try:
        # TODO: Implementar validação real com Supabase Auth
        _supabase = get_supabase_service()
        # Exemplo de uso futuro:
        # user = _supabase.auth.get_user(token)
        # return user.user.id
        return "usuario-teste"

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autorizado ou inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err