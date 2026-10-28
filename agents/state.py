"""
agents/state.py — Fonte única de verdade para o estado financeiro canônico (stub).

O `CANONICAL_STATE` representa o `CanonicalFinancialState` do MEI de demonstração,
espelhando exatamente os valores das telas de referência do Banco do Brasil:
  - docs/arquiteturaTecnica.md seção 2
  - Valores confirmados pelo Agente 3 (Estrategista): hiato = R$ 2.800,00

Importado por:
  - bff/main.py       → _CANONICAL_STATE (fallback P3 e endpoints)
  - agents/cli_bridge.py → CANONICAL_STATE_STUB (bridge MCP TypeScript)

Manter este arquivo como única fonte evita divergências numéricas entre
o BFF e o servidor MCP quando os valores de referência forem atualizados.
"""

from __future__ import annotations

from typing import Any

CANONICAL_STATE: dict[str, Any] = {
    "mei_id": "",  # preenchido dinamicamente com o mei_id recebido
    "resumo_saldos": {
        "saldo_atual": 12456.78,
        "contas_conectadas": 3,
        "disponivel": 7985.32,
    },
    "a_vencer_semana": {
        "total": 7750.0,
        "itens": [
            {"id": "COMP-001", "descricao": "cartão de crédito",    "valor": 1250.0, "dias_para_vencimento": 3, "cnpj_beneficiario": "11222333000181", "tipo": "CARTAO"},
            {"id": "COMP-002", "descricao": "aluguel",              "valor": 1800.0, "dias_para_vencimento": 5, "cnpj_beneficiario": "22333444000192", "tipo": "BOLETO_DDA"},
            {"id": "COMP-003", "descricao": "conta de energia",     "valor": 650.0,  "dias_para_vencimento": 6, "cnpj_beneficiario": "33444555000103", "tipo": "CONTA_CONSUMO"},
            {"id": "COMP-004", "descricao": "DAS-MEI",              "valor": 75.9,   "dias_para_vencimento": 7, "cnpj_beneficiario": "00394460034273", "tipo": "DAS_MEI"},
            {"id": "COMP-005", "descricao": "fornecedor papelaria", "valor": 890.0,  "dias_para_vencimento": 4, "cnpj_beneficiario": "44555666000114", "tipo": "BOLETO_DDA"},
            {"id": "COMP-006", "descricao": "plano de saúde",       "valor": 534.1,  "dias_para_vencimento": 2, "cnpj_beneficiario": "55666777000125", "tipo": "BOLETO_DDA"},
            {"id": "COMP-007", "descricao": "internet empresarial", "valor": 2550.0, "dias_para_vencimento": 1, "cnpj_beneficiario": "66777888000136", "tipo": "CONTA_CONSUMO"},
        ],
    },
    "receita_prevista_7d": {
        "total": 4950.0,
        "histograma": [
            {"dia_rotulo": "Hoje",    "valor": 900.0},
            {"dia_rotulo": "Sexta",   "valor": 1200.0},
            {"dia_rotulo": "Sábado",  "valor": 1100.0},
            {"dia_rotulo": "Domingo", "valor": 0.0},
            {"dia_rotulo": "Segunda", "valor": 400.0},
            {"dia_rotulo": "Terça",   "valor": 500.0},
            {"dia_rotulo": "Quarta",  "valor": 850.0},
        ],
    },
    "diagnostico_risco": {
        "risco_identificado": True,
        "defice_semana": 2800.0,  # 7750.0 - 4950.0
        "acao_recomendada_id": "ACT-2026-W43-01",
    },
}
