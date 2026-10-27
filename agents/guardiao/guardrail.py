r"""
Agente 5 — Guardião: Validador Anti-Alucinação Numérica (Guardrail watsonx.governance).

Implementa o guardrail especificado em docs/arquiteturaTecnica.md seção 6.1:

  Regex de extração sobre a resposta textual: R\$\s?(\d{1,3}(\.\d{3})*,\d{2})
  Todo valor encontrado no texto DEVE ter correspondência exata nos nós do ExecutionPlan.
  Se divergir, aborta e emite template determinístico.

Adicionalmente valida:
  - Que o hiato_total textual coincide com o campo `hiato_total` do plano.
  - Que nenhum valor monetário é inventado (alucinação) pelo modelo Granite.

Referência: docs/arquiteturaTecnica.md seção 6.1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────────────────────
# Extração de valores monetários BR do texto
# ──────────────────────────────────────────────────────────────────────────────

# Padrão conforme docs/arquiteturaTecnica.md seção 6.1
_REGEX_MONETARIO = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})")


def extrair_valores_monetarios(texto: str) -> list[float]:
    """
    Extrai todos os valores monetários em formato BR do texto.

    Ex.:
        "Deficit de R$ 2.150,00 coberto por R$ 985,32 da poupança."
        → [2150.0, 985.32]
    """
    matches = _REGEX_MONETARIO.findall(texto)
    return [_parse_br_currency(m) for m in matches]


def _parse_br_currency(valor_str: str) -> float:
    """Converte string monetária BR para float. Ex.: '2.150,00' → 2150.0"""
    return float(valor_str.replace(".", "").replace(",", "."))


# ──────────────────────────────────────────────────────────────────────────────
# Coleta recursiva de valores numéricos do ExecutionPlan
# ──────────────────────────────────────────────────────────────────────────────


def _coletar_valores_plano(obj: object, acc: set[float] | None = None) -> set[float]:
    """
    Percorre recursivamente o ExecutionPlan (dict/list/number) e coleta
    todos os valores numéricos arredondados a 2 casas decimais.
    """
    if acc is None:
        acc = set()

    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.add(round(float(obj), 2))
    elif isinstance(obj, dict):
        for v in obj.values():
            _coletar_valores_plano(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _coletar_valores_plano(v, acc)

    return acc


# ──────────────────────────────────────────────────────────────────────────────
# Resultado da auditoria
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ResultadoGuardrail:
    aprovado: bool
    divergencias: list[str] = field(default_factory=list)
    valores_texto: list[float] = field(default_factory=list)
    valores_plano: list[float] = field(default_factory=list)
    mensagem: str = ""
    texto_substituido: str | None = None  # Template determinístico quando aprovado=False


# ──────────────────────────────────────────────────────────────────────────────
# Template Determinístico (fallback quando há alucinação)
# ──────────────────────────────────────────────────────────────────────────────


def _gerar_template_deterministico(plano: dict) -> str:
    """
    Gera mensagem segura baseada exclusivamente nos valores calculados do plano.
    Usado como fallback quando o texto do modelo contém alucinações numéricas.
    """
    hiato = plano.get("hiato_total", 0.0)
    status = plano.get("status", "DESCONHECIDO")
    custo = plano.get("custo_solucao", 0.0)
    custo_evitado = plano.get("custo_evitado_multas", 0.0)

    def fmt(v: float) -> str:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    linhas = [
        f"Diagnóstico de Caixa — Status: {status}",
        f"Déficit identificado: {fmt(hiato)}",
    ]

    acoes = plano.get("acoes", [])
    for acao in acoes:
        tipo = acao.get("tipo", "")
        if tipo == "RESGATE_POUPANCA":
            linhas.append(f"• Resgate de poupança: {fmt(acao['valor'])}")
        elif tipo == "ANTECIPACAO_RECEBIVEIS":
            linhas.append(
                f"• Antecipação de recebíveis: {fmt(acao['valor_liquido'])} "
                f"(custo: {fmt(acao['custo_operacao'])})"
            )
        elif tipo == "MICROCREDITO_EMERGENCIAL":
            linhas.append(f"• Microcrédito emergencial: {fmt(acao['valor'])}")

    if custo > 0:
        linhas.append(f"Custo total da solução: {fmt(custo)}")
    if custo_evitado > 0:
        linhas.append(f"Multas/mora evitadas estimadas: {fmt(custo_evitado)}")
    linhas.append("Todas as ações exigem sua confirmação biométrica.")

    return "\n".join(linhas)


# ──────────────────────────────────────────────────────────────────────────────
# Interface pública
# ──────────────────────────────────────────────────────────────────────────────


def auditar_texto(texto_gerado: str, plano_calculado: dict) -> ResultadoGuardrail:
    """
    Valida o texto gerado pelo modelo Granite contra o ExecutionPlan calculado.

    Para cada valor monetário encontrado no texto (via regex), verifica se há
    correspondência exata no plano. Se qualquer valor divergir, o guardrail
    reprova e retorna o template determinístico como substituto seguro.

    Args:
        texto_gerado:    Texto em linguagem natural gerado pelo modelo Granite.
        plano_calculado: ExecutionPlan serializado (dict) do Agente 3.

    Returns:
        ResultadoGuardrail com aprovado=True (sem divergências) ou
        aprovado=False com lista de divergências e texto_substituido seguro.
    """
    valores_texto = extrair_valores_monetarios(texto_gerado)
    valores_plano_set = _coletar_valores_plano(plano_calculado)

    divergencias: list[str] = []
    for valor in valores_texto:
        valor_arredondado = round(valor, 2)
        if valor_arredondado not in valores_plano_set:
            divergencias.append(
                f"Valor R$ {valor:,.2f} encontrado no texto não tem "
                "correspondência exata no ExecutionPlan calculado.".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

    aprovado = len(divergencias) == 0

    resultado = ResultadoGuardrail(
        aprovado=aprovado,
        divergencias=divergencias,
        valores_texto=valores_texto,
        valores_plano=sorted(valores_plano_set),
        mensagem=(
            "Todos os valores monetários do texto são consistentes com o ExecutionPlan."
            if aprovado
            else "ALERTA: Divergências detectadas. Template determinístico emitido."
        ),
        texto_substituido=(
            None if aprovado else _gerar_template_deterministico(plano_calculado)
        ),
    )

    return resultado
