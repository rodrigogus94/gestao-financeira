"""
Fábrica de provedores de IA: retorna uma instância de IAProvider por tipo.

Este módulo expõe IAProviderFactory.get_provider(tipo), que devolve sempre
a mesma instância para um dado tipo (singleton por tipo). Se o tipo não
existir em PROVIDER_CONFIGS, é feito fallback para settings.DEFAULT_IA_PROVIDER.
Se a criação do provedor falhar (ex.: falta de API key), tenta criar o
provedor padrão. listar_provedores_disponiveis() tenta criar cada provedor
e retorna uma lista com nome, tipo e status (disponivel/indisponivel) para cada um.
"""

from typing import Dict, Optional, List
from .provider import IAProvider
from .config import PROVIDER_CONFIGS
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class IAProviderFactory:
    """
    Fábrica que mantém uma instância de IAProvider por tipo (singleton por tipo).

    O dicionário de classe _instance guarda as instâncias já criadas. get_provider(tipo)
    retorna a instância existente ou cria uma nova (IAProvider(tipo)) e armazena.
    """

    # Cache de instâncias: chave = tipo ("openai", "gemini", "ollama"), valor = IAProvider.
    _instance: Dict[str, IAProvider] = {}

    @classmethod
    def _get_provider_no_fallback(cls, tipo: str) -> IAProvider:
        """
        Obtém a instância do provider para o tipo informado, sem aplicar fallback.

        Esse método existe especificamente para o endpoint de status/listagem de provedores:
        queremos saber se `openai`, `gemini` ou `claude` falharam na inicialização,
        e então marcá-los como "indisponivel" (em vez de substituir por "ollama").
        """
        if tipo not in PROVIDER_CONFIGS:
            raise ValueError(
                f"Provider de IA '{tipo}' não encontrado em PROVIDER_CONFIGS."
            )

        if tipo not in cls._instance:
            # Se a inicialização falhar, propagamos a exceção para que a listagem
            # consiga marcar como indisponivel o provedor solicitado.
            cls._instance[tipo] = IAProvider(tipo)

        return cls._instance[tipo]

    @classmethod
    def get_provider(cls, tipo: Optional[str] = None) -> IAProvider:
        """
        Retorna o provedor de IA para o tipo informado (ou o padrão se tipo for None).

        Se tipo não estiver em PROVIDER_CONFIGS, emite warning e usa
        settings.DEFAULT_IA_PROVIDER. Se a instância ainda não existir,
        tenta criar IAProvider(tipo); em caso de exceção, tenta criar o
        provedor padrão (se o tipo pedido não for o padrão). Retorna sempre
        a mesma instância para o mesmo tipo (singleton por tipo).

        Args:
            tipo: "openai", "gemini", "ollama" ou None (usa DEFAULT_IA_PROVIDER).

        Returns:
            Instância de IAProvider já inicializada.
        """
        tipo = tipo or settings.DEFAULT_IA_PROVIDER

        if tipo not in PROVIDER_CONFIGS:
            logger.warning(
                f"Provider de IA '{tipo}' não configurado. "
                f"Usando fallback '{settings.DEFAULT_IA_PROVIDER}'."
            )
            tipo = settings.DEFAULT_IA_PROVIDER

        if tipo not in cls._instance:
            try:
                cls._instance[tipo] = IAProvider(tipo)
                logger.info(f"Provider de IA '{tipo}' inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao inicializar Provider de IA '{tipo}': {e}")
                if tipo != settings.DEFAULT_IA_PROVIDER:
                    return cls.get_provider(settings.DEFAULT_IA_PROVIDER)
                raise

        return cls._instance[tipo]

    @classmethod
    def listar_provedores_disponiveis(cls) -> List[Dict]:
        """
        Lista todos os provedores configurados com seu status (disponivel ou indisponivel).

        Para cada tipo em PROVIDER_CONFIGS, tenta obter o provedor com get_provider(tipo).
        Se conseguir, adiciona um dict com nome, tipo e status "disponivel". Se der exceção,
        adiciona nome, tipo, status "indisponivel" e o campo "erro" com a mensagem.
        Útil para a API ou UI mostrarem quais IAs estão configuradas e funcionando.

        Returns:
            Lista de dicts com chaves: nome, tipo, status e opcionalmente erro.
        """
        disponiveis = []
        for tipo in PROVIDER_CONFIGS.keys():
            try:
                # Importante: sem fallback. Assim, se openai/gemini/claude
                # falharem ao inicializar, o status reflete isso corretamente.
                provider = cls._get_provider_no_fallback(tipo)
                disponiveis.append({
                    "nome": provider.nome,
                    "tipo": provider.tipo,
                    "status": "disponivel",
                })
            except Exception as e:
                disponiveis.append({
                    "nome": tipo,
                    "tipo": tipo,
                    "status": "indisponivel",
                    "erro": str(e),
                })
        return disponiveis

    @classmethod
    def recarregar_provedores(cls) -> List[str]:
        """
        Limpa o cache de provedores (_instance) para forçar recriação na próxima chamada.

        Útil após alteração de variáveis de ambiente (ex.: API keys) ou para
        diagnóstico. Retorna a lista de tipos que estavam em cache.
        """
        tipos = list(cls._instance.keys())
        cls._instance.clear()
        return tipos
