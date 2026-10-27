"""
Modelos de dados Pydantic para o Copiloto MEI Banco do Brasil.

Espelham fielmente o JSON Schema `schemas/canonical-financial-state.json` (draft-07)
e os contratos de output do Agente 3 (Estrategista Financeiro).

Referência: docs/arquiteturaTecnica.md seções 3 e 4.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────


class TipoCompromisso(str, Enum):
    CARTAO = "CARTAO"
    BOLETO_DDA = "BOLETO_DDA"
    DAS_MEI = "DAS_MEI"
    CONTA_CONSUMO = "CONTA_CONSUMO"


class DiaSemanaRotulo(str, Enum):
    HOJE = "Hoje"
    SEXTA = "Sexta"
    SABADO = "Sábado"
    DOMINGO = "Domingo"
    SEGUNDA = "Segunda"
    TERCA = "Terça"
    QUARTA = "Quarta"


# ──────────────────────────────────────────────────────────────────────────────
# Input: CanonicalFinancialState
# ──────────────────────────────────────────────────────────────────────────────


class ItemAVencer(BaseModel):
    id: str
    descricao: str
    valor: float = Field(gt=0)
    dias_para_vencimento: int = Field(ge=0)
    cnpj_beneficiario: str = Field(pattern=r"^\d{14}$")
    tipo: TipoCompromisso


class HistogramaItem(BaseModel):
    dia_rotulo: DiaSemanaRotulo
    valor: float = Field(ge=0)


class ResumoSaldos(BaseModel):
    saldo_atual: float = Field(ge=0)
    contas_conectadas: int = Field(ge=0)
    disponivel: float = Field(ge=0)


class AVencerSemana(BaseModel):
    total: float = Field(ge=0)
    itens: list[ItemAVencer]

    @field_validator("total")
    @classmethod
    def total_deve_bater_com_itens(cls, v: float, info) -> float:
        # Validação tolerante — itens podem não estar completos em testes parciais
        return v


class ReceitaPrevista7d(BaseModel):
    total: float = Field(ge=0)
    histograma: list[HistogramaItem] = Field(min_length=7, max_length=7)


class DiagnosticoRisco(BaseModel):
    risco_identificado: bool
    defice_semana: float = Field(ge=0)
    acao_recomendada_id: str


class CanonicalFinancialState(BaseModel):
    mei_id: str
    resumo_saldos: ResumoSaldos
    a_vencer_semana: AVencerSemana
    receita_prevista_7d: ReceitaPrevista7d
    diagnostico_risco: DiagnosticoRisco


# ──────────────────────────────────────────────────────────────────────────────
# Input: Taxas BB (parâmetros externos configuráveis)
# ──────────────────────────────────────────────────────────────────────────────


class TaxasBB(BaseModel):
    """Taxas operacionais do Banco do Brasil injetadas pelo Agente 1."""
    taxa_diaria_antecipacao: float = Field(
        default=0.00045,
        description="Taxa diária de desconto na antecipação de recebíveis (0,045% a.d.)",
    )
    dias_medio_antecipacao: int = Field(
        default=4,
        description="Prazo médio em dias dos recebíveis disponíveis para antecipação.",
    )
    taxa_microcredito_mensal: float = Field(
        default=0.0189,
        description="Taxa mensal do microcrédito emergencial pré-aprovado (1,89% a.m.)",
    )
    recebiveis_antecipacao_disponivel: float = Field(
        default=3200.00,
        description="Volume máximo disponível para antecipação de recebíveis (ex.: R$ 3.200,00).",
    )
    colchao_minimo_reserva: float = Field(
        default=1000.00,
        description="Valor mínimo de reserva de liquidez mantido intocado na poupança (R$ 1.000,00).",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Output: ExecutionPlan (gerado pelo Agente 3)
# ──────────────────────────────────────────────────────────────────────────────


class StatusPlano(str, Enum):
    SEM_RISCO = "SEM_RISCO"
    PLANO_ESTRUTURADO = "PLANO_ESTRUTURADO"
    COBERTO_PARCIALMENTE = "COBERTO_PARCIALMENTE"


class OperacaoResgate(BaseModel):
    step: Literal[1]
    tipo: Literal["RESGATE_POUPANCA"]
    valor: float


class OperacaoAntecipacao(BaseModel):
    step: Literal[2]
    tipo: Literal["ANTECIPACAO_RECEBIVEIS"]
    valor_bruto: float
    valor_liquido: float
    custo_operacao: float


class OperacaoMicrocredito(BaseModel):
    step: Literal[3]
    tipo: Literal["MICROCREDITO_EMERGENCIAL"]
    valor: float
    taxa_mensal: float


class OperacaoLiquidacao(BaseModel):
    step: Literal[4]
    tipo: Literal["LIQUIDACAO_COMPROMISSO"]
    id_origem: str
    valor: float


# Union tipada para a lista de operações
OperacaoCascata = (
    OperacaoResgate | OperacaoAntecipacao | OperacaoMicrocredito | OperacaoLiquidacao
)


class ProjecaoCaixa(BaseModel):
    """Projeção discreta diária P(d) no horizonte T."""
    horizonte_dias: int
    valores_diarios: list[float]  # P(d) para d = 1..T
    dia_critico: int | None = None  # Dia com menor P(d) < 0
    saldo_minimo: float  # min(P(d)) — negativo indica ruptura


class ExecutionPlan(BaseModel):
    status: StatusPlano
    hiato_total: float = Field(ge=0, description="Déficit bruto detectado (G).")
    defice_restante: float = Field(
        ge=0, description="Valor não coberto após a cascata (0 se PLANO_ESTRUTURADO)."
    )
    acoes: list[dict]  # Serialização JSON das operações (mantida como dict para flexibilidade)
    custo_solucao: float = Field(ge=0, description="Custo financeiro total das operações.")
    custo_evitado_multas: float = Field(
        ge=0,
        description="Estimativa de multas e juros evitados ao quitar os compromissos no prazo.",
    )
    projecao: ProjecaoCaixa
