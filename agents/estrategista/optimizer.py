"""
Agente 3 — Estrategista Financeiro: Motor de Otimização de Fluxo de Caixa.

Implementa a formulação matemática completa definida em docs/arquiteturaTecnica.md seção 4:

  Projeção móvel discreta no horizonte T ∈ [7, 30] dias:
      P(d) = B_cc + Σ(E_t, t=1..d) - Σ(S_t, t=1..d)

  Condição de Ruptura de Caixa: ∃ d tal que P(d) < 0
  Hiato Financeiro Crítico: G = |min P(d)| quando P(d) < 0

Cascata de Minimização de Custo Financeiro:
  Nível 1 — Reserva/Poupança        (custo zero, preserva colchão de R$ 1.000)
  Nível 2 — Antecipação de Recebíveis (taxa diária BB; ordena por menor prazo)
  Nível 3 — Microcrédito Emergencial  (apenas saldo remanescente, taxa mensal BB)

Referência: docs/arquiteturaTecnica.md seções 4.1 e 4.2.
"""

from __future__ import annotations

import math
from typing import Any

from agents.estrategista.models import (
    CanonicalFinancialState,
    ExecutionPlan,
    OperacaoAntecipacao,
    OperacaoLiquidacao,
    OperacaoMicrocredito,
    OperacaoResgate,
    ProjecaoCaixa,
    StatusPlano,
    TaxasBB,
)


# ──────────────────────────────────────────────────────────────────────────────
# Projeção Móvel Discreta
# ──────────────────────────────────────────────────────────────────────────────


def projetar_caixa(
    saldo_livre: float,
    entradas_confirmadas: list[float],
    saidas_agendadas: list[float],
    horizonte_dias: int = 7,
) -> ProjecaoCaixa:
    """
    Calcula P(d) = B_cc + Σ(E_t, t=1..d) - Σ(S_t, t=1..d) para d ∈ [1, horizonte_dias].

    Args:
        saldo_livre: B_cc — saldo disponível para movimentação imediata.
        entradas_confirmadas: vetor de recebíveis confirmados por dia (índice 0 = dia 1).
                              Deve ter exatamente `horizonte_dias` elementos.
        saidas_agendadas:    vetor de saídas agendadas por dia (mesmo comprimento).
        horizonte_dias:      janela de projeção T ∈ [7, 30]. Padrão: 7.

    Returns:
        ProjecaoCaixa com os valores diários, dia crítico e saldo mínimo.
    """
    assert 7 <= horizonte_dias <= 30, "Horizonte deve ser de 7 a 30 dias."

    # Garante padding de zeros se os vetores forem menores que o horizonte
    E = list(entradas_confirmadas) + [0.0] * horizonte_dias
    S = list(saidas_agendadas) + [0.0] * horizonte_dias

    valores: list[float] = []
    acumulado_e = 0.0
    acumulado_s = 0.0

    for d in range(1, horizonte_dias + 1):
        acumulado_e += E[d - 1]
        acumulado_s += S[d - 1]
        P_d = round(saldo_livre + acumulado_e - acumulado_s, 2)
        valores.append(P_d)

    saldo_minimo = min(valores)
    dia_critico: int | None = None
    if saldo_minimo < 0:
        # Primeiro dia em que o caixa fica negativo
        dia_critico = next(i + 1 for i, v in enumerate(valores) if v < 0)

    return ProjecaoCaixa(
        horizonte_dias=horizonte_dias,
        valores_diarios=valores,
        dia_critico=dia_critico,
        saldo_minimo=saldo_minimo,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Cascata de Minimização de Custo
# ──────────────────────────────────────────────────────────────────────────────


def _nivel1_reserva(
    defice_restante: float,
    disponivel: float,
    colchao: float,
) -> tuple[float, OperacaoResgate | None]:
    """
    Nível 1 — Alocação de reserva líquida/poupança (custo zero).
    Preserva o colchão mínimo de liquidez (default R$ 1.000,00).
    """
    reserva_utilizavel = max(0.0, disponivel - colchao)
    alocado = min(defice_restante, reserva_utilizavel)

    if alocado <= 0:
        return defice_restante, None

    op = OperacaoResgate(
        step=1,
        tipo="RESGATE_POUPANCA",
        valor=round(alocado, 2),
    )
    return round(defice_restante - alocado, 2), op


def _nivel2_antecipacao(
    defice_restante: float,
    recebiveis_disponiveis: float,
    taxa_diaria: float,
    dias_medio: int,
) -> tuple[float, OperacaoAntecipacao | None, float]:
    """
    Nível 2 — Antecipação seletiva de recebíveis com menor custo efetivo.
    Cobre apenas o déficit remanescente; o custo de desconto é calculado
    sobre o valor líquido necessário.

    Returns:
        (defice_restante_pos_n2, operacao_ou_None, custo_n2)
    """
    if defice_restante <= 0 or recebiveis_disponiveis <= 0:
        return defice_restante, None, 0.0

    valor_liquido = min(defice_restante, recebiveis_disponiveis)
    custo_desconto = round(valor_liquido * (taxa_diaria * dias_medio), 2)
    valor_bruto = round(valor_liquido + custo_desconto, 2)

    op = OperacaoAntecipacao(
        step=2,
        tipo="ANTECIPACAO_RECEBIVEIS",
        valor_bruto=valor_bruto,
        valor_liquido=round(valor_liquido, 2),
        custo_operacao=custo_desconto,
    )
    return round(defice_restante - valor_liquido, 2), op, custo_desconto


def _nivel3_microcredito(
    defice_restante: float,
    taxa_mensal: float,
) -> tuple[float, OperacaoMicrocredito | None]:
    """
    Nível 3 — Microcrédito emergencial pré-aprovado.
    Aciona apenas para saldo não coberto pelos níveis 1 e 2.
    """
    if defice_restante <= 0:
        return 0.0, None

    op = OperacaoMicrocredito(
        step=3,
        tipo="MICROCREDITO_EMERGENCIAL",
        valor=round(defice_restante, 2),
        taxa_mensal=taxa_mensal,
    )
    return 0.0, op


# ──────────────────────────────────────────────────────────────────────────────
# Função Principal: otimizar_fluxo_caixa
# ──────────────────────────────────────────────────────────────────────────────


def otimizar_fluxo_caixa(
    payload: dict[str, Any],
    taxas: dict[str, Any] | None = None,
    horizonte_dias: int = 7,
) -> dict[str, Any]:
    """
    Motor determinístico do Agente 3 (Estrategista Financeiro).

    Executa a cascata de minimização de custo sobre o CanonicalFinancialState
    e retorna um ExecutionPlan serializado (dict) pronto para consumo pelo
    Agente 4 (Saga Engine) e pelo Agente 5 (Guardrail).

    Args:
        payload:        CanonicalFinancialState serializado (dict) — saída do Agente 2.
        taxas:          Taxas operacionais BB. Se None, usa os defaults de TaxasBB.
        horizonte_dias: Janela de projeção T ∈ [7, 30]. Padrão: 7.

    Returns:
        ExecutionPlan serializado como dict.
    """
    # 1. Validação e parsing do payload canônico
    state = CanonicalFinancialState.model_validate(payload)
    tb = TaxasBB.model_validate(taxas or {})

    # 2. Projeção móvel discreta P(d)
    #    Distribui entradas e saídas uniformemente ao longo dos 7 dias
    #    (refinado para distribuição real pelo histograma quando disponível)
    histograma = state.receita_prevista_7d.histograma
    entradas_por_dia = [h.valor for h in histograma[:horizonte_dias]]

    # Saídas: distribui os itens pelo dia de vencimento (dia 0..horizonte_dias-1)
    saidas_por_dia = [0.0] * horizonte_dias
    for item in state.a_vencer_semana.itens:
        idx = min(item.dias_para_vencimento, horizonte_dias - 1)
        saidas_por_dia[idx] += item.valor

    projecao = projetar_caixa(
        saldo_livre=state.resumo_saldos.disponivel,
        entradas_confirmadas=entradas_por_dia,
        saidas_agendadas=saidas_por_dia,
        horizonte_dias=horizonte_dias,
    )

    # 3. Cálculo do hiato financeiro crítico G
    #    Fórmula direta da spec (arquiteturaTecnica.md seção 4.2):
    #      gap = saidas_totais - entradas_totais
    #    O saldo livre NÃO entra no gap — ele é o recurso de cobertura (Nível 1),
    #    não parte do cálculo de ruptura semanal.
    gap = round(
        max(0.0, state.a_vencer_semana.total - state.receita_prevista_7d.total), 2
    )

    # Sem risco de caixa
    if gap == 0.0:
        plano = ExecutionPlan(
            status=StatusPlano.SEM_RISCO,
            hiato_total=0.0,
            defice_restante=0.0,
            acoes=[],
            custo_solucao=0.0,
            custo_evitado_multas=0.0,
            projecao=projecao,
        )
        return plano.model_dump()

    # 4. Cascata de cobertura
    defice = gap
    operacoes: list[dict] = []
    custo_total = 0.0

    # Nível 1 — Reserva
    defice, op_n1 = _nivel1_reserva(
        defice_restante=defice,
        disponivel=state.resumo_saldos.disponivel,
        colchao=tb.colchao_minimo_reserva,
    )
    if op_n1:
        operacoes.append(op_n1.model_dump())

    # Nível 2 — Antecipação de Recebíveis
    defice, op_n2, custo_n2 = _nivel2_antecipacao(
        defice_restante=defice,
        recebiveis_disponiveis=tb.recebiveis_antecipacao_disponivel,
        taxa_diaria=tb.taxa_diaria_antecipacao,
        dias_medio=tb.dias_medio_antecipacao,
    )
    if op_n2:
        operacoes.append(op_n2.model_dump())
        custo_total = round(custo_total + custo_n2, 2)

    # Nível 3 — Microcrédito
    defice_final, op_n3 = _nivel3_microcredito(
        defice_restante=defice,
        taxa_mensal=tb.taxa_microcredito_mensal,
    )
    if op_n3:
        operacoes.append(op_n3.model_dump())

    # 5. Liquidação dos compromissos (encadeada após captação dos recursos)
    for item in state.a_vencer_semana.itens:
        op_liq = OperacaoLiquidacao(
            step=4,
            tipo="LIQUIDACAO_COMPROMISSO",
            id_origem=item.id,
            valor=item.valor,
        )
        operacoes.append(op_liq.model_dump())

    # 6. Status final
    status = (
        StatusPlano.COBERTO_PARCIALMENTE
        if defice_final > 0
        else StatusPlano.PLANO_ESTRUTURADO
    )

    # 7. Estimativa de custo evitado (multas de 2% + mora de 0,26% a.d. por 7 dias)
    custo_evitado = round(gap * 0.02 + (gap * 0.0026 * 7), 2)

    plano = ExecutionPlan(
        status=status,
        hiato_total=gap,
        defice_restante=round(defice_final, 2),
        acoes=operacoes,
        custo_solucao=custo_total,
        custo_evitado_multas=custo_evitado,
        projecao=projecao,
    )
    return plano.model_dump()
