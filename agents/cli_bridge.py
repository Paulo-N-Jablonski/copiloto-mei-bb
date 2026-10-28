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
from agents.state import CANONICAL_STATE

# Alias de retrocompatibilidade — mantém o nome CANONICAL_STATE_STUB usado
# internamente neste módulo sem duplicar os dados.
# Fonte única de verdade: agents/state.py
CANONICAL_STATE_STUB = CANONICAL_STATE


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

    # Simula execução dos passos Saga — ID canônico gerado no servidor
    from agents.identificadores import gerar_recibo_id
    recibo_id = gerar_recibo_id()
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
