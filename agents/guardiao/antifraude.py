"""
Agente 5 — Guardião: Módulo Antifraude de Boletos DDA.

Valida o `cnpj_beneficiario` de cada compromisso do tipo BOLETO_DDA presente
no CanonicalFinancialState contra a base pública da Receita Federal via BrasilAPI.

Regras de negócio (docs/arquiteturaTecnica.md seção 6.2):
  - CNPJ deve estar com situacao_cadastral == 2 (ATIVA).
  - Boletos cujo CNPJ emissor diverge do padrão esperado ou está inativo/suspenso
    geram bloqueio preventivo e alerta de possível adulteração.

Modo de operação — controlado por BRASIL_API_MODE (alinhado com a Fase 1):
  "mock" (padrão): retorna resultado determinístico sem chamada de rede.
  "real"          : chama GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}

Referência: docs/arquiteturaTecnica.md seções 2.3, 6.2; docs/contextoNegocioBB.md seção 3.1.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

load_dotenv()

BRASIL_API_BASE = "https://brasilapi.com.br/api/cnpj/v1"
SITUACAO_ATIVA = 2  # Código Receita Federal para CNPJ ativo
REQUEST_TIMEOUT = 8.0  # segundos


# ──────────────────────────────────────────────────────────────────────────────
# Resultado da validação de um único CNPJ
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ResultadoValidacaoCnpj:
    cnpj: str
    valido: bool
    situacao_cadastral: int | None = None
    descricao_situacao: str | None = None
    razao_social: str | None = None
    motivo: str = ""
    bloqueado: bool = False  # True = boleto bloqueado preventivamente


@dataclass
class ResultadoAntifraude:
    """Resultado consolidado da validação antifraude de todos os boletos."""
    total_boletos_validados: int = 0
    total_bloqueados: int = 0
    alertas: list[str] = field(default_factory=list)
    detalhes: list[ResultadoValidacaoCnpj] = field(default_factory=list)

    @property
    def aprovado(self) -> bool:
        """True se nenhum boleto foi bloqueado."""
        return self.total_bloqueados == 0


# ──────────────────────────────────────────────────────────────────────────────
# Modo MOCK
# ──────────────────────────────────────────────────────────────────────────────


def _validar_cnpj_mock(cnpj: str) -> ResultadoValidacaoCnpj:
    """
    Resposta determinística para desenvolvimento e CI.
    Todos os CNPJs são considerados válidos no mock.
    """
    return ResultadoValidacaoCnpj(
        cnpj=cnpj,
        valido=True,
        situacao_cadastral=SITUACAO_ATIVA,
        descricao_situacao="ATIVA",
        razao_social=f"EMPRESA MOCK LTDA ({cnpj})",
        motivo="CNPJ validado em modo mock (BRASIL_API_MODE=mock).",
        bloqueado=False,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Modo REAL
# ──────────────────────────────────────────────────────────────────────────────


def _validar_cnpj_real(cnpj: str) -> ResultadoValidacaoCnpj:
    """
    Consulta a BrasilAPI e valida situacao_cadastral == 2.
    Usa httpx com timeout explícito para evitar travamentos em produção.
    """
    url = f"{BRASIL_API_BASE}/{cnpj}"
    try:
        resp = httpx.get(url, timeout=REQUEST_TIMEOUT)
    except httpx.TimeoutException:
        return ResultadoValidacaoCnpj(
            cnpj=cnpj,
            valido=False,
            motivo="Timeout ao consultar BrasilAPI. Boleto bloqueado preventivamente.",
            bloqueado=True,
        )
    except httpx.RequestError as exc:
        return ResultadoValidacaoCnpj(
            cnpj=cnpj,
            valido=False,
            motivo=f"Erro de conexão com BrasilAPI: {exc}. Boleto bloqueado preventivamente.",
            bloqueado=True,
        )

    if resp.status_code == 404:
        return ResultadoValidacaoCnpj(
            cnpj=cnpj,
            valido=False,
            motivo="CNPJ não encontrado na base da Receita Federal. Boleto bloqueado.",
            bloqueado=True,
        )

    if resp.status_code != 200:
        return ResultadoValidacaoCnpj(
            cnpj=cnpj,
            valido=False,
            motivo=f"BrasilAPI retornou HTTP {resp.status_code}. Boleto bloqueado preventivamente.",
            bloqueado=True,
        )

    data = resp.json()
    situacao = data.get("situacao_cadastral")
    descricao = data.get("descricao_situacao_cadastral", "")
    razao = data.get("razao_social", "")

    if situacao != SITUACAO_ATIVA:
        return ResultadoValidacaoCnpj(
            cnpj=cnpj,
            valido=False,
            situacao_cadastral=situacao,
            descricao_situacao=descricao,
            razao_social=razao,
            motivo=(
                f"CNPJ com situação '{descricao}' (código {situacao}). "
                "Apenas CNPJs ATIVOS são aceitos. Boleto bloqueado preventivamente."
            ),
            bloqueado=True,
        )

    return ResultadoValidacaoCnpj(
        cnpj=cnpj,
        valido=True,
        situacao_cadastral=situacao,
        descricao_situacao=descricao,
        razao_social=razao,
        motivo=f"CNPJ ativo: {razao}.",
        bloqueado=False,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Interface pública
# ──────────────────────────────────────────────────────────────────────────────


def validar_cnpj(cnpj: str) -> ResultadoValidacaoCnpj:
    """
    Valida um único CNPJ. O modo é determinado por BRASIL_API_MODE.
    """
    modo = os.getenv("BRASIL_API_MODE", "mock").lower()
    if modo == "real":
        return _validar_cnpj_real(cnpj)
    return _validar_cnpj_mock(cnpj)


def auditar_boletos(itens_a_vencer: list[dict]) -> ResultadoAntifraude:
    """
    Audita antifraude de todos os boletos DDA presentes na lista de compromissos.

    Filtra apenas itens do tipo BOLETO_DDA e valida o cnpj_beneficiario de cada um.
    Boletos de outros tipos (CARTAO, DAS_MEI, CONTA_CONSUMO) não são auditados aqui.

    Args:
        itens_a_vencer: lista de itens do campo `a_vencer_semana.itens`
                        do CanonicalFinancialState (dicts).

    Returns:
        ResultadoAntifraude consolidado.
    """
    resultado = ResultadoAntifraude()

    boletos_dda = [
        item for item in itens_a_vencer if item.get("tipo") == "BOLETO_DDA"
    ]

    for boleto in boletos_dda:
        cnpj = boleto.get("cnpj_beneficiario", "")
        res = validar_cnpj(cnpj)
        resultado.total_boletos_validados += 1
        resultado.detalhes.append(res)

        if res.bloqueado:
            resultado.total_bloqueados += 1
            resultado.alertas.append(
                f"[BLOQUEADO] {boleto.get('descricao', 'sem descrição')} "
                f"| CNPJ {cnpj} | Motivo: {res.motivo}"
            )

    return resultado
