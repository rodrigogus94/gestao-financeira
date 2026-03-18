"""
Provedor de IA unificado: uma única classe para OpenAI, Gemini e Ollama.

Este módulo implementa a classe IAProvider que, recebendo um tipo ("openai",
"gemini", "ollama"), usa config (config.py) e o cliente (ClienteFactory em clients.py)
para: extrair despesa de texto natural, classificar categoria, gerar relatório
e responder perguntas com contexto. Toda a lógica específica por API (como
chamar cada uma e como tratar a resposta) está concentrada em _chamar_api()
e _processar_resposta(). Em caso de falha na extração, usa _extrair_simples()
(heurística por palavras-chave) e _extrair_fallback() para devolver uma
ExtracaoDespesa com confiança menor.
"""

import json
import re
import logging
from typing import Any, Dict, Optional
from datetime import date
from abc import ABC, abstractmethod

from app.core.config import settings
from app.services.ia.base import ExtracaoDespesa
from app.services.ia.clients import ClienteFactory
from app.services.ia.config import (
    get_config,
    get_prompt,
    CATEGORIA_VALIDAS,
    ProviderConfig,
)

logger = logging.getLogger(__name__)


class IAProvider(ABC):
    """
    Provedor de IA único parametrizado pelo tipo (openai, gemini, ollama).

    No __init__ carrega a ProviderConfig para o tipo, cria o cliente via
    ClienteFactory e guarda em self.cliente. Os métodos públicos (extrair_despesa,
    classificar_categoria, gerar_relatorio, perguntar) montam o prompt com
    get_prompt(), aplicam prefix/suffix da config, chamam _chamar_api() e,
    quando necessário, _processar_resposta() ou fallbacks.
    """

    def __init__(self, tipo: str) -> None:
        """
        Inicializa o provedor para o tipo informado.

        Carrega a configuração (get_config), cria o cliente (ClienteFactory.criar_cliente)
        e registra em log qual provedor foi inicializado.

        Args:
            tipo: "openai", "gemini" ou "ollama".
        """
        self.tipo = tipo
        self.config = get_config(tipo)
        # ProviderConfig expõe o campo `name` (nome legível) e `tipo` (identificador).
        # O código anterior usava `config.nome`, o que causava AttributeError e
        # deixava todos os provedores como indisponíveis no endpoint de status.
        self.nome = self.config.name
        self.cliente = ClienteFactory.criar_cliente(tipo)
        logger.info(f"Provider de IA inicializado: {self.nome}")

    # -------------------------------------------------------------------------
    # Métodos públicos: extração, classificação, relatório, pergunta
    # -------------------------------------------------------------------------

    async def extrair_despesa(self, texto: str) -> ExtracaoDespesa:
        """
        Extrai os dados da despesa (valor, categoria, data, descrição) a partir de texto natural.

        Monta o prompt "extrair_despesa" com texto, data_hoje e categorias; aplica
        prefix/suffix da config; chama a API via _chamar_api(); parseia a resposta
        com _processar_resposta() e monta um ExtracaoDespesa. Em qualquer exceção,
        usa _extrair_fallback() (que por sua vez usa _extrair_simples() com heurística
        por palavras-chave) e retorna uma extração com confiança 0.7 e provedor "(fallback)".
        """
        try:
            prompt_base = get_prompt(
                "extrair_despesa",
                texto=texto,
                data_hoje=date.today().isoformat(),
                categorias=", ".join(CATEGORIA_VALIDAS),
            )
            prompt = f"{self.config.prompt_prefix}{prompt_base}{self.config.prompt_suffix}"
            resposta = await self._chamar_api(prompt)
            resultado = await self._processar_resposta(resposta, texto)

            return ExtracaoDespesa(
                valor=resultado["valor"],
                categoria=resultado["categoria"],
                data=date.fromisoformat(resultado["data"]),
                descricao=resultado.get("descricao", texto[:100]),
                fonte="textual_natural",
                status="pendente",
                provedor=self.nome,
                confianca=0.95 if self.tipo == "openai" else 0.90,
            )
        except Exception as e:
            logger.error(f"Erro no provedor {self.nome}: {e}")
            return await self._extrair_fallback(texto)

    async def classificar_categoria(self, descricao: str) -> str:
        """
        Classifica a descrição em uma das categorias válidas (alimentacao, transporte, etc.).

        Usa o prompt "classificar_categoria", chama a API com temperatura 0 para
        resposta mais determinística e devolve o texto da resposta em minúsculas e sem espaços extras.
        """
        prompt = get_prompt(
            "classificar_categoria",
            descricao=descricao,
            categorias=", ".join(CATEGORIA_VALIDAS),
        )
        prompt = f"{self.config.prompt_prefix}{prompt}{self.config.prompt_suffix}"
        resposta = await self._chamar_api(prompt, temperatura=0.0)
        return resposta.strip().lower()

    async def gerar_relatorio(self, dados: Dict) -> str:
        """
        Gera um relatório em texto a partir dos dados financeiros (dict).

        Serializa os dados em JSON legível, monta o prompt "gerar_relatorio"
        e chama a API com temperatura 0.3 para um pouco de variedade no texto.
        """
        prompt = get_prompt(
            "gerar_relatorio",
            dados=json.dumps(dados, indent=2, default=str, ensure_ascii=False),
        )
        prompt = f"{self.config.prompt_prefix}{prompt}{self.config.prompt_suffix}"
        return await self._chamar_api(prompt, temperatura=0.3)

    async def perguntar(self, contexto: str, pergunta: str) -> str:
        """
        Responde uma pergunta do usuário com base no contexto (dados financeiros).

        O contexto é truncado a 1000 caracteres para caber no prompt. Usa
        temperatura 0 para respostas mais estáveis.
        """
        prompt = get_prompt(
            "perguntar",
            contexto=contexto[:1000],
            pergunta=pergunta,
        )
        prompt = f"{self.config.prompt_prefix}{prompt}{self.config.prompt_suffix}"
        return await self._chamar_api(prompt, temperatura=0.0)

    # -------------------------------------------------------------------------
    # Métodos protegidos: chamada à API e processamento da resposta
    # -------------------------------------------------------------------------

    async def _chamar_api(self, prompt: str, temperatura: float = 0.0) -> str:
        """
        Envia o prompt para a API do provedor atual e retorna o texto da resposta.

        - OpenAI: client.chat.completions.create com messages, temperature, max_tokens
          e opcionalmente response_format json_object se config.suporta_json.
        - Gemini: client.generate_content(prompt) e response.text.
        - Ollama: ClienteFactory.chamar_ollama(prompt, self.cliente, temperatura).

        Qualquer exceção é logada e re-levantada.
        """
        try:
            if self.tipo == "openai":
                response = await self.cliente.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperatura,
                    max_tokens=self.config.max_tokens_attr,
                    response_format={"type": "json_object"}
                    if self.config.suporta_json
                    else None,
                )
                return response.choices[0].message.content

            elif self.tipo == "gemini":
                response = await self.cliente.generate_content(prompt)
                return response.text

            elif self.tipo == "ollama":
                return await ClienteFactory.chamar_ollama(
                    prompt, self.cliente, temperatura
                )

            elif self.tipo == "claude":
                response = await self.cliente.messages.create(
                    model=settings.CLAUDE_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperatura,
                    max_tokens=self.config.max_tokens_attr,
                )
                return response.choices[0].message.content

            else:
                raise ValueError(
                    f"Tipo de provedor {self.tipo} não suportado ou desconhecido."
                )
        except Exception as e:
            logger.error(f"Erro ao chamar API do provedor {self.nome}: {e}")
            raise e

    async def _processar_resposta(self, resposta: str, texto: str) -> Dict:
        """
        Converte a resposta bruta da API em um dicionário com valor, categoria, data, descricao.

        Se config.precisa_limpeza for True (Gemini/Ollama), remove ```json e ```
        da resposta. Em seguida tenta localizar um objeto JSON na string (regex
        \\{.*\\}) e fazer json.loads. Se falhar, chama _extrair_simples(texto)
        para obter um dict por heurística a partir do texto original.
        """
        try:
            if self.config.precisa_limpeza:
                resposta = resposta.replace("```json", "").replace("```", "")
                resposta = resposta.strip()
            json_match = re.search(r"\{.*\}", resposta, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(resposta)
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return await self._extrair_simples(texto)

    async def _extrair_simples(self, texto: str) -> Dict:
        """
        Extrai valor, categoria, data e descrição por heurística (regex + palavras-chave).

        Valor: primeiro número encontrado (aceita vírgula ou ponto como decimal).
        Categoria: palavras-chave no texto (ex.: comida, restaurante -> alimentacao;
        gasolina, táxi -> transporte; médico, farmácia -> saude; escola, curso -> educacao);
        caso contrário "outros".
        Data: sempre date.today().isoformat().
        Descrição: primeiros 100 caracteres do texto.
        Usado como fallback quando a IA não retorna JSON válido.
        """
        valor_match = re.search(r"(\d+[.,]?\d*)", texto)
        valor = (
            float(valor_match.group(1).replace(",", ".")) if valor_match else 0.0
        )
        texto_lower = texto.lower()
        if any(
            p in texto_lower
            for p in [
                "alimento",
                "comida",
                "restaurante",
                "mercado",
                "supermercado",
                "almoço",
                "janta",
                "café",
                "bebida",
                "refrigerante",
                "suco",
                "água",
            ]
        ):
            categoria = "alimentacao"
        elif any(
            p in texto_lower
            for p in [
                "transporte",
                "gasolina",
                "combustível",
                "táxi",
                "ônibus",
                "metro",
                "estacionamento",
                "pedágio",
                "viagem",
            ]
        ):
            categoria = "transporte"
        elif any(
            p in texto_lower
            for p in [
                "saúde",
                "médico",
                "hospital",
                "clínica",
                "farmácia",
                "medicamento",
                "remédio",
                "vacina",
                "exame",
                "consulta",
            ]
        ):
            categoria = "saude"
        elif any(
            p in texto_lower
            for p in [
                "educação",
                "escola",
                "universidade",
                "faculdade",
                "curso",
                "livro",
                "material de estudo",
                "ensino",
            ]
        ):
            categoria = "educacao"
        else:
            categoria = "outros"
        return {
            "valor": valor,
            "categoria": categoria,
            "data": date.today().isoformat(),
            "descricao": texto[:100],
        }

    async def _extrair_fallback(self, texto: str) -> ExtracaoDespesa:
        """
        Fallback quando a extração via IA falha: usa _extrair_simples e devolve ExtracaoDespesa.

        A confiança é fixada em 0.7 e o provedor é marcado como "{nome} (fallback)"
        para indicar que o resultado veio da heurística e não da IA.
        """
        simples = await self._extrair_simples(texto)
        return ExtracaoDespesa(
            valor=simples["valor"],
            categoria=simples["categoria"],
            data=date.fromisoformat(simples["data"]),
            descricao=simples["descricao"],
            fonte="textual_natural",
            status="pendente",
            confianca=0.7,
            provedor=f"{self.nome} (fallback)",
        )
