"""
Ponte CLI Python para o servidor MCP TypeScript.

O servidor MCP (Node.js/TypeScript) invoca este script como subprocesso,
passando o nome do comando e o payload JSON via stdin. O script executa
a lógica Python correspondente e retorna o resultado como JSON em stdout.

Protocolo:
  stdin:  {"command": "<nome>", "payload": {...}}
  stdout: {"ok": true,  "result": {...}}
       ou {"ok": false, "error": "<mensagem>"}

Comandos disponíveis:
  get_dashboard_state   → agents/estrategista/optimizer.py (estado + diagnóstico)
  execute_saga          → agente de execução (Saga simulado com guardrail)
  audit_output          → agents/guardiao/guardrail.py
  validate_cpf_cnpj     → agents/guardiao/antifraude.py (BrasilAPI)
"""

from __future__ import annotations

import json
import os
import sys

# Garante que a raiz do projeto está no PYTHONPATH independente de onde o script é chamado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.estrategista.optimizer import otimizar_fluxo_caixa
from agents.guardiao.antifraude import auditar_boletos, validar_cnpj
from agents.guardiao.guardrail import auditar_texto

# ──────────────────────────────────────────────────────────────────────────────
# Payload canônico de referência (stub Agente 2 — substitui chamada Open Finance)
# Valores exatos das telas de referência: docs/telaInicio.jpeg e docs/telaCopiloto.jpeg
# ──────────────────────────────────────────────────────────────────────────────

CANONICAL_STATE_STUB = {
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
        "defice_semana": 2800.0,  # 7750 - 4950
        "acao_recomendada_id": "ACT-2026-W43-01",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Handlers de cada comando
# ──────────────────────────────────────────────────────────────────────────────


def _handle_get_dashboard_state(payload: dict) -> dict:
    mei_id = payload.get("mei_id", "unknown")
    state = {**CANONICAL_STATE_STUB, "mei_id": mei_id}

    # Executa o motor do Estrategista sobre o estado canônico
    plano = otimizar_fluxo_caixa(state)

    # Auditoria antifraude dos boletos DDA
    resultado_antifraude = auditar_boletos(state["a_vencer_semana"]["itens"])

    return {
        "canonical_state": state,
        "execution_plan": plano,
        "antifraude": {
            "aprovado": resultado_antifraude.aprovado,
            "total_boletos_validados": resultado_antifraude.total_boletos_validados,
            "total_bloqueados": resultado_antifraude.total_bloqueados,
            "alertas": resultado_antifraude.alertas,
        },
    }


def _handle_execute_saga(payload: dict) -> dict:
    biometric_token = payload.get("biometric_token", "")
    execution_plan_id = payload.get("execution_plan_id", "")

    if not biometric_token:
        raise ValueError("biometric_token é obrigatório para execução da Saga.")
    if not execution_plan_id:
        raise ValueError("execution_plan_id é obrigatório para execução da Saga.")

    # Recupera o plano atual (em produção viria de um store/cache)
    mei_id = payload.get("mei_id", "unknown")
    state = {**CANONICAL_STATE_STUB, "mei_id": mei_id}
    plano = otimizar_fluxo_caixa(state)

    # Guardrail: valida texto gerado (se fornecido) contra o plano
    texto_gerado = payload.get("texto_gerado", "")
    guardrail_result = None
    if texto_gerado:
        gr = auditar_texto(texto_gerado, plano)
        guardrail_result = {
            "aprovado": gr.aprovado,
            "divergencias": gr.divergencias,
        }
        if not gr.aprovado:
            raise ValueError(
                f"Guardrail rejeitou o texto gerado. Divergências: {gr.divergencias}"
            )

    # Simula execução dos passos Saga
    import time
    recibo_id = f"REC-{execution_plan_id}-{int(time.time())}"
    passos = [
        {"passo": 1, "tipo": "RESGATE_POUPANCA",       "status": "CONCLUIDO", "valor": next((a["valor"] for a in plano["acoes"] if a.get("tipo") == "RESGATE_POUPANCA"), 0.0)},
        {"passo": 2, "tipo": "ANTECIPACAO_RECEBIVEIS", "status": "CONCLUIDO", "valor": next((a.get("valor_liquido", 0.0) for a in plano["acoes"] if a.get("tipo") == "ANTECIPACAO_RECEBIVEIS"), 0.0)},
        {"passo": 3, "tipo": "LIQUIDACAO_COMPROMISSOS","status": "CONCLUIDO", "valor": sum(a["valor"] for a in plano["acoes"] if a.get("tipo") == "LIQUIDACAO_COMPROMISSO")},
    ]

    return {
        "sucesso": True,
        "recibo_consolidado_id": recibo_id,
        "passos_executados": passos,
        "plano_referencia": plano["status"],
        "guardrail": guardrail_result,
    }


def _handle_audit_output(payload: dict) -> dict:
    texto = payload.get("texto_gerado", "")
    plano = payload.get("plano_calculado", {})
    resultado = auditar_texto(texto, plano)
    return {
        "aprovado": resultado.aprovado,
        "divergencias": resultado.divergencias,
        "mensagem": resultado.mensagem,
        "texto_substituido": resultado.texto_substituido,
    }


def _handle_validate_cpf_cnpj(payload: dict) -> dict:
    cnpj = payload.get("cnpj", "")
    cpf  = payload.get("cpf", "")
    # antifraude.validar_cnpj valida o CNPJ; a lógica de CPF fica no handler TS
    res = validar_cnpj(cnpj)
    return {"valido": res.valido, "motivo": res.motivo}


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher e entrypoint
# ──────────────────────────────────────────────────────────────────────────────

HANDLERS = {
    "get_dashboard_state": _handle_get_dashboard_state,
    "execute_saga":        _handle_execute_saga,
    "audit_output":        _handle_audit_output,
    "validate_cpf_cnpj":   _handle_validate_cpf_cnpj,
}


def main() -> None:
    raw = sys.stdin.read()
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stdout.write(json.dumps({"ok": False, "error": f"JSON inválido: {e}"}))
        sys.exit(1)

    command = request.get("command", "")
    payload = request.get("payload", {})

    handler = HANDLERS.get(command)
    if handler is None:
        sys.stdout.write(json.dumps({"ok": False, "error": f"Comando desconhecido: '{command}'"}))
        sys.exit(1)

    try:
        result = handler(payload)
        sys.stdout.write(json.dumps({"ok": True, "result": result}))
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
