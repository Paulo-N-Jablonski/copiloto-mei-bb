"""
Teste de Integração E2E — Fluxo Ponta a Ponta do Copiloto MEI BB.

Exercita o fluxo completo dos 5 agentes sem dependências externas (modo mock):

  Passo 1: Agente 2 (Agregador) — Leitura do estado financeiro consolidado
  Passo 2: Agente 3 (Estrategista) — Identificação do risco e geração do ExecutionPlan
  Passo 3: Agente 5 (Guardião / Antifraude) — Auditoria dos boletos DDA
  Passo 4: Agente 5 (Guardião / Guardrail) — Validação anti-alucinação do texto gerado
  Passo 5: Agente 4 via BFF — Aprovação biométrica e emissão de recibo consolidado

Também testa o bridge CLI Python diretamente e os 3 endpoints do BFF via TestClient.

Referência: docs/arquiteturaTecnica.md seções 1, 4, 5 e 6.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

# Garante que a raiz do projeto está no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("BRASIL_API_MODE", "mock")

from agents.estrategista.optimizer import otimizar_fluxo_caixa
from agents.guardiao.antifraude import auditar_boletos
from agents.guardiao.guardrail import auditar_texto
from bff.main import app

client = TestClient(app)

# ──────────────────────────────────────────────────────────────────────────────
# Fixture: payload canônico das telas de referência
# ──────────────────────────────────────────────────────────────────────────────

MEI_ID = "e2e-test-mei-001"

CANONICAL_STATE = {
    "mei_id": MEI_ID,
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
        "defice_semana": 2800.0,
        "acao_recomendada_id": "ACT-2026-W43-01",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# PASSO 1: Agente 2 — Leitura do Estado Financeiro Consolidado
# ──────────────────────────────────────────────────────────────────────────────


class TestPasso1AggregadorEstado:
    """Simula o Agente 2 retornando o CanonicalFinancialState."""

    def test_estado_contem_campos_obrigatorios(self):
        state = CANONICAL_STATE
        assert "mei_id" in state
        assert "resumo_saldos" in state
        assert "a_vencer_semana" in state
        assert "receita_prevista_7d" in state
        assert "diagnostico_risco" in state

    def test_saldo_disponivel_correto(self):
        assert CANONICAL_STATE["resumo_saldos"]["disponivel"] == 7985.32

    def test_total_saidas_correto(self):
        assert CANONICAL_STATE["a_vencer_semana"]["total"] == 7750.0

    def test_total_receita_correto(self):
        assert CANONICAL_STATE["receita_prevista_7d"]["total"] == 4950.0

    def test_histograma_7_dias(self):
        assert len(CANONICAL_STATE["receita_prevista_7d"]["histograma"]) == 7

    def test_soma_histograma_igual_total(self):
        soma = sum(h["valor"] for h in CANONICAL_STATE["receita_prevista_7d"]["histograma"])
        assert soma == pytest.approx(CANONICAL_STATE["receita_prevista_7d"]["total"])

    def test_risco_identificado_verdadeiro(self):
        assert CANONICAL_STATE["diagnostico_risco"]["risco_identificado"] is True


# ──────────────────────────────────────────────────────────────────────────────
# PASSO 2: Agente 3 — Identificação de Risco e ExecutionPlan
# ──────────────────────────────────────────────────────────────────────────────


class TestPasso2EstrategistaPlan:
    """Executa o motor do Estrategista e verifica o ExecutionPlan produzido."""

    def setup_method(self):
        self.plano = otimizar_fluxo_caixa(CANONICAL_STATE)

    def test_plano_estruturado(self):
        assert self.plano["status"] == "PLANO_ESTRUTURADO"

    def test_hiato_calculado(self):
        """Gap = 7750 - 4950 = 2800."""
        assert self.plano["hiato_total"] == pytest.approx(2800.0)

    def test_defice_zerado_apos_cascata(self):
        assert self.plano["defice_restante"] == 0.0

    def test_nivel1_cobre_gap(self):
        """Disponível=7985.32, colchão=1000 → reserva=6985.32 > gap(2800). N1 cobre tudo."""
        resgates = [a for a in self.plano["acoes"] if a.get("tipo") == "RESGATE_POUPANCA"]
        assert len(resgates) == 1
        assert resgates[0]["valor"] == pytest.approx(2800.0)

    def test_sem_antecipacao_quando_reserva_suficiente(self):
        antecipacoes = [a for a in self.plano["acoes"] if a.get("tipo") == "ANTECIPACAO_RECEBIVEIS"]
        assert len(antecipacoes) == 0

    def test_liquidacoes_para_todos_compromissos(self):
        liquidacoes = [a for a in self.plano["acoes"] if a.get("tipo") == "LIQUIDACAO_COMPROMISSO"]
        assert len(liquidacoes) == 7

    def test_custo_solucao_zero(self):
        assert self.plano["custo_solucao"] == 0.0

    def test_custo_evitado_positivo(self):
        assert self.plano["custo_evitado_multas"] > 0

    def test_projecao_presente(self):
        assert "projecao" in self.plano
        assert self.plano["projecao"]["horizonte_dias"] == 7


# ──────────────────────────────────────────────────────────────────────────────
# PASSO 3: Agente 5 — Auditoria Antifraude dos Boletos DDA
# ──────────────────────────────────────────────────────────────────────────────


class TestPasso3Antifraude:
    """Valida que o Guardião audita corretamente os boletos DDA."""

    def setup_method(self):
        self.resultado = auditar_boletos(CANONICAL_STATE["a_vencer_semana"]["itens"])

    def test_aprovado_no_modo_mock(self):
        assert self.resultado.aprovado is True

    def test_apenas_boletos_dda_auditados(self):
        """3 itens BOLETO_DDA na fixture de referência."""
        assert self.resultado.total_boletos_validados == 3

    def test_zero_bloqueados(self):
        assert self.resultado.total_bloqueados == 0

    def test_sem_alertas(self):
        assert self.resultado.alertas == []


# ──────────────────────────────────────────────────────────────────────────────
# PASSO 4: Agente 5 — Guardrail Anti-Alucinação
# ──────────────────────────────────────────────────────────────────────────────


class TestPasso4Guardrail:
    """Valida que o Guardião aprova textos consistentes e rejeita alucinações."""

    def setup_method(self):
        self.plano = otimizar_fluxo_caixa(CANONICAL_STATE)

    def test_texto_correto_aprovado(self):
        """Texto com valores do plano deve ser aprovado."""
        texto = (
            "Identifiquei um risco de caixa de R$ 2.800,00. "
            "Recomendo resgatar R$ 2.800,00 da sua reserva para cobrir os compromissos."
        )
        resultado = auditar_texto(texto, self.plano)
        assert resultado.aprovado is True
        assert resultado.divergencias == []

    def test_valor_alucinado_reprovado(self):
        """Valor inventado pelo modelo deve ser detectado."""
        texto = "O déficit é de R$ 99.999,99 segundo análise avançada."
        resultado = auditar_texto(texto, self.plano)
        assert resultado.aprovado is False
        assert len(resultado.divergencias) > 0

    def test_template_deterministico_gerado(self):
        texto = "Valor inventado: R$ 55.000,00."
        resultado = auditar_texto(texto, self.plano)
        assert resultado.texto_substituido is not None
        # Template seguro deve mencionar o hiato real
        assert "2.800,00" in resultado.texto_substituido

    def test_texto_sem_valores_aprovado(self):
        texto = "Tudo certo! Seu fluxo está equilibrado."
        resultado = auditar_texto(texto, self.plano)
        assert resultado.aprovado is True


# ──────────────────────────────────────────────────────────────────────────────
# PASSO 5: BFF + Saga — Aprovação Biométrica e Recibo Consolidado
# ──────────────────────────────────────────────────────────────────────────────


class TestPasso5BffSaga:
    """Testa os 3 endpoints do BFF FastAPI ponta a ponta."""

    # ── Endpoint 1: GET /api/v1/dashboard/home ──

    def test_dashboard_home_200(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        assert resp.status_code == 200

    def test_dashboard_screen_label(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert data["screen"] == "Screen_Dashboard"

    def test_dashboard_saldo_atual(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert data["cards_superiores"]["saldo_atual"]["valor"] == 12456.78

    def test_dashboard_disponivel(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert data["cards_superiores"]["saldo_disponivel"]["valor"] == 7985.32

    def test_dashboard_total_saidas(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert data["a_vencer_semana"]["total"] == 7750.0

    def test_dashboard_histograma_7_dias(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert len(data["receita_prevista"]["histograma"]) == 7

    def test_dashboard_alerta_exibido(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert data["alerta_saude_financeira"]["exibir"] is True
        assert data["alerta_saude_financeira"]["defice"] > 0

    def test_dashboard_execution_plan_presente(self):
        resp = client.get("/api/v1/dashboard/home", headers={"x-mei-id": MEI_ID})
        data = resp.json()
        assert "execution_plan_summary" in data
        assert data["execution_plan_summary"]["status"] == "PLANO_ESTRUTURADO"

    # ── Endpoint 2: GET /api/v1/copiloto/summary ──

    def test_copiloto_summary_200(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        assert resp.status_code == 200

    def test_copiloto_screen_label(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        assert resp.json()["screen"] == "Screen_CopilotoMEI"

    def test_copiloto_3_acoes_recomendadas(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        acoes = resp.json()["acoes_recomendadas"]
        assert len(acoes) == 3

    def test_copiloto_acao_pagar_contas(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        acoes = resp.json()["acoes_recomendadas"]
        pagar = next(a for a in acoes if a["id"] == "ACTION_PAGAR_CONTAS")
        assert pagar["valor"] == 7750.0

    def test_copiloto_acao_antecipar_recebiveis(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        acoes = resp.json()["acoes_recomendadas"]
        antecipar = next(a for a in acoes if a["id"] == "ACTION_ANTECIPAR")
        assert antecipar["valor"] == 3200.0

    def test_copiloto_acao_aplicar_saldo(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        acoes = resp.json()["acoes_recomendadas"]
        aplicar = next(a for a in acoes if a["id"] == "ACTION_APLICAR")
        assert aplicar["valor"] == 7985.32

    def test_copiloto_card_risco_exibido(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        card = resp.json()["card_risco_caixa"]
        assert card["exibir"] is True
        assert card["defice"] > 0

    def test_copiloto_botoes_presentes(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        botoes = resp.json()["card_risco_caixa"]["botoes"]
        assert "ver_solucao" in botoes
        assert "autorizar" in botoes

    def test_copiloto_4_capacidades(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        assert len(resp.json()["capacidades"]) == 4

    def test_copiloto_trava_seguranca(self):
        resp = client.get("/api/v1/copiloto/summary", headers={"x-mei-id": MEI_ID})
        trava = resp.json()["trava_seguranca"]
        assert "confirmação" in trava["mensagem"].lower()

    # ── Endpoint 3: POST /api/v1/copiloto/authorize-biometrics ──

    def test_authorize_200_com_token_valido(self):
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "FIDO2-MOCK-TOKEN-12345",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
            },
        )
        assert resp.status_code == 200

    def test_authorize_recibo_emitido(self):
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "FIDO2-MOCK-TOKEN-12345",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
            },
        )
        data = resp.json()
        assert data["sucesso"] is True
        assert data["recibo_consolidado_id"].startswith("REC-ACT-2026-W43-01")

    def test_authorize_passos_executados(self):
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "FIDO2-MOCK-TOKEN-12345",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
            },
        )
        passos = resp.json()["passos_executados"]
        tipos = [p["tipo"] for p in passos]
        assert "RESGATE_POUPANCA" in tipos
        assert "LIQUIDACAO_COMPROMISSOS" in tipos

    def test_authorize_422_sem_token(self):
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
            },
        )
        assert resp.status_code == 422

    def test_authorize_guardrail_aprovado_texto_correto(self):
        """Texto com valores do plano não deve ser bloqueado pelo guardrail."""
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "FIDO2-MOCK-TOKEN-12345",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
                "texto_gerado": "Vamos resgatar R$ 2.800,00 da reserva para cobrir o déficit.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["guardrail"]["aprovado"] is True

    def test_authorize_guardrail_reprovado_valor_inventado(self):
        """Texto com valor alucinado deve retornar 422."""
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "FIDO2-MOCK-TOKEN-12345",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
                "texto_gerado": "Valor inventado: R$ 99.999,99.",
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["erro"] == "GUARDRAIL_REPROVADO"

    def test_authorize_antifraude_aprovado(self):
        """Resultado antifraude deve estar presente e aprovado no mock."""
        resp = client.post(
            "/api/v1/copiloto/authorize-biometrics",
            json={
                "biometric_token": "FIDO2-MOCK-TOKEN-12345",
                "execution_plan_id": "ACT-2026-W43-01",
                "mei_id": MEI_ID,
            },
        )
        data = resp.json()
        assert data["antifraude"]["aprovado"] is True


# ──────────────────────────────────────────────────────────────────────────────
# PASSO EXTRA: Bridge CLI Python
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgeCLI:
    """Testa o bridge CLI Python diretamente via subprocesso."""

    BRIDGE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents", "cli_bridge.py")

    def _call_bridge(self, command: str, payload: dict) -> dict:
        """
        Invoca o bridge e retorna o dict JSON do stdout.
        Não valida returncode — o bridge retorna exit(1) para erros de negócio
        mas ainda escreve um JSON válido em stdout (ok=false).
        """
        request = json.dumps({"command": command, "payload": payload})
        result = subprocess.run(
            [sys.executable, self.BRIDGE],
            input=request,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.stdout.strip(), f"Bridge sem output. stderr: {result.stderr}"
        return json.loads(result.stdout)

    def test_get_dashboard_state_ok(self):
        resp = self._call_bridge("get_dashboard_state", {"mei_id": MEI_ID})
        assert resp["ok"] is True
        assert "canonical_state" in resp["result"]
        assert "execution_plan" in resp["result"]

    def test_get_dashboard_state_plano_estruturado(self):
        resp = self._call_bridge("get_dashboard_state", {"mei_id": MEI_ID})
        plano = resp["result"]["execution_plan"]
        assert plano["status"] == "PLANO_ESTRUTURADO"

    def test_execute_saga_ok(self):
        resp = self._call_bridge("execute_saga", {
            "biometric_token": "FIDO2-MOCK-12345",
            "execution_plan_id": "ACT-2026-W43-01",
            "mei_id": MEI_ID,
        })
        assert resp["ok"] is True
        assert resp["result"]["sucesso"] is True
        assert "recibo_consolidado_id" in resp["result"]

    def test_execute_saga_sem_token_retorna_erro(self):
        """Bridge retorna ok=false com mensagem de erro de negócio."""
        resp = self._call_bridge("execute_saga", {
            "biometric_token": "",
            "execution_plan_id": "ACT-2026-W43-01",
            "mei_id": MEI_ID,
        })
        assert resp["ok"] is False
        assert "biometric_token" in resp["error"].lower()

    def test_audit_output_aprovado(self):
        resp = self._call_bridge("audit_output", {
            "texto_gerado": "Déficit de R$ 2.800,00 a cobrir.",
            "plano_calculado": {"hiato_total": 2800.0, "status": "PLANO_ESTRUTURADO"},
        })
        assert resp["ok"] is True
        assert resp["result"]["aprovado"] is True

    def test_audit_output_reprovado(self):
        resp = self._call_bridge("audit_output", {
            "texto_gerado": "Valor alucinado: R$ 99.000,00.",
            "plano_calculado": {"hiato_total": 2800.0},
        })
        assert resp["ok"] is True
        assert resp["result"]["aprovado"] is False

    def test_comando_desconhecido(self):
        request = json.dumps({"command": "comando_inexistente", "payload": {}})
        result = subprocess.run(
            [sys.executable, self.BRIDGE],
            input=request,
            capture_output=True,
            text=True,
            timeout=10,
        )
        resp = json.loads(result.stdout)
        assert resp["ok"] is False
        assert "desconhecido" in resp["error"].lower()
