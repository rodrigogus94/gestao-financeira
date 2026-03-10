"""
Clientes de IA para cada provedor (OpenAI, Gemini, Ollama).

Este módulo concentra a criação dos clientes que falam com as APIs externas:
- OpenAI: usa openai.AsyncOpenAI com api_key e model vindos de settings.
- Gemini: configura google.generativeai e retorna um GenerativeModel.
- Ollama: não usa SDK oficial com cliente único; retorna um dicionário com
  base_url e model, e as chamadas são feitas via chamar_ollama() usando
  aiohttp contra a API REST do Ollama (/api/generate).

O provider.py usa ClienteFactory.criar_cliente(tipo) para obter o cliente
e, no caso do Ollama, passa self.cliente para chamar_ollama() junto com
o prompt e a temperatura.
"""

import openai
import google.generativeai as genai
import ollama
import aiohttp
from typing import Any, Dict
from app.core.config import settings
from .config import get_config


class ClienteFactory:
    """
    Fábrica que cria o cliente correto para cada tipo de provedor de IA.

    Para OpenAI e Gemini retorna uma instância do SDK (AsyncOpenAI ou
    GenerativeModel). Para Ollama retorna um dict com base_url e model,
    pois a chamada é feita manualmente em chamar_ollama() via HTTP.
    """

    @staticmethod
    def criar_cliente(tipo: str) -> Any:
        """
        Cria e retorna o cliente de IA para o tipo informado.

        Args:
            tipo: "openai", "gemini" ou "ollama".

        Returns:
            - openai: instância de openai.AsyncOpenAI (usa settings.OPENAI_API_KEY e OPENAI_MODEL).
            - gemini: instância de genai.GenerativeModel (usa GEMINI_API_KEY e GEMINI_MODEL).
            - ollama: dict com chaves "base_url" e "model" (valores de settings.OLLAMA_*).

        Raises:
            ValueError: Se o tipo não for um dos suportados.
        """
        if tipo == "openai":
            return openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
            )

        elif tipo == "gemini":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            return genai.GenerativeModel(model=settings.GEMINI_MODEL)

        elif tipo == "ollama":
            # Ollama não tem cliente SDK único; retornamos config para usar em chamar_ollama
            return {
                "base_url": settings.OLLAMA_BASE_URL,
                "model": settings.OLLAMA_MODEL,
            }

        else:
            raise ValueError(f"Provider de IA '{tipo}' não suportado ou desconhecido.")

    @staticmethod
    async def chamar_ollama(prompt: str, config: Dict, temperatura: float = 0.0) -> str:
        """
        Envia o prompt para a API do Ollama (POST /api/generate) e retorna o texto gerado.

        O Ollama roda localmente (ou em um servidor) e expõe uma API REST. Este método
        monta o payload com model, prompt, stream=False e options.temperature,
        faz a requisição com aiohttp e devolve o campo "response" do JSON de resposta.
        Em caso de status HTTP diferente de 200, levanta exceção com a mensagem de erro.

        Args:
            prompt: Texto do prompt enviado ao modelo.
            config: Dicionário com "base_url" e "model" (o mesmo retornado por criar_cliente("ollama")).
            temperatura: Valor de 0 a 1 para controlar aleatoriedade (0 = mais determinístico).

        Returns:
            String com o texto gerado pelo modelo (campo "response" da resposta JSON).

        Raises:
            Exception: Se response.status != 200, com detalhes do status e corpo da resposta.
        """
        payload = {
            "model": config["model"],
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperatura},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config['base_url']}/api/generate",
                json=payload,
            ) as response:
                if response.status != 200:
                    raise Exception(
                        f"Erro ao chamar Ollama: {response.status} {await response.text()}"
                    )
                data = await response.json()
                return data["response"]
