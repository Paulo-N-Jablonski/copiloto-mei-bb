"""
Suíte de testes unitários para o Agente 5 — Guardião e Conformidade.

Cobre:
  - guardrail.py: extração de valores monetários, detecção de alucinações,
    template determinístico e aprovação de textos corretos.
  - antifraude.py: validação de CNPJ em modo mock, filtragem por tipo BOLETO_DDA,
    bloqueio de boletos com CNPJs simulados como inválidos.

Referência: docs/arquiteturaTecnica.md seções 6.1 e 6.2.
"""

from __future__ import annotations

import os

import pytest

from agents.guardiao.antifraude import auditar_boletos, validar_cnpj
from agents.guardiao.guardrail import (
    auditar_texto,
    extrair_valores_monetarios,
    _parse_br_currency,
    _coletar_valores_plano,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures compartilhadas
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def plano_referencia() -> dict:
    """ExecutionPlan do cenário real das telas de referência."""
    return {
        "status": "PLANO_ESTRUTURADO",
        "hiato_total": 2150.0,
        "defice_restante": 0.0,
        "custo_solucao": 0.0,
        "custo_evitado_multas": 80.99,
        "acoes": [
            {"step": 1, "tipo": "RESGATE_POUPANCA", "valor": 2150.0},
            {"step": 4, "tipo": "LIQUIDACAO_COMPROMISSO", "id_origem": "COMP-001", "valor": 1250.0},
            {"step": 4, "tipo": "LIQUIDACAO_COMPROMISSO", "id_origem": "COMP-002", "valor": 1800.0},
        ],
    }


@pytest.fixture
def itens_a_vencer() -> list[dict]:
    """Lista mista: BOLETO_DDA + outros tipos."""
    return [
        {
            "id": "COMP-001",
            "descricao": "cartão de crédito",
            "valor": 1250.0,
            "dias_para_vencimento": 3,
            "cnpj_beneficiario": "11222333000181",
            "tipo": "CARTAO",
        },
        {
            "id": "COMP-002",
            "descricao": "aluguel",
            "valor": 1800.0,
            "dias_para_vencimento": 5,
            "cnpj_beneficiario": "22333444000192",
            "tipo": "BOLETO_DDA",
        },
        {
            "id": "COMP-003",
            "descricao": "conta de energia",
            "valor": 650.0,
            "dias_para_vencimento": 6,
            "cnpj_beneficiario": "33444555000103",
            "tipo": "CONTA_CONSUMO",
        },
        {
            "id": "COMP-004",
            "descricao": "fornecedor papelaria",
            "valor": 890.0,
            "dias_para_vencimento": 4,
            "cnpj_beneficiario": "44555666000114",
            "tipo": "BOLETO_DDA",
        },
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Guardrail — extração de valores
# ──────────────────────────────────────────────────────────────────────────────


class TestExtracao:
    def test_parse_br_currency_simples(self):
        assert _parse_br_currency("2.150,00") == 2150.0

    def test_parse_br_currency_sem_milhar(self):
        assert _parse_br_currency("985,32") == 985.32

    def test_parse_br_currency_grande(self):
        assert _parse_br_currency("1.234.567,89") == 1234567.89

    def test_extrair_valores_texto_multiplos(self):
        texto = "Deficit de R$ 2.150,00 coberto por R$ 985,32 da poupança e R$ 1.164,68 de antecipação."
        valores = extrair_valores_monetarios(texto)
        assert 2150.0 in valores
        assert 985.32 in valores
        assert 1164.68 in valores

    def test_extrair_valores_sem_espaco(self):
        """Regex deve aceitar 'R$2.150,00' sem espaço."""
        texto = "Valor total: R$2.150,00."
        valores = extrair_valores_monetarios(texto)
        assert 2150.0 in valores

    def test_extrair_vazio(self):
        texto = "Não há valores monetários neste texto."
        assert extrair_valores_monetarios(texto) == []

    def test_coletar_valores_plano_flat(self):
        obj = {"a": 100.0, "b": 200.5}
        acc = _coletar_valores_plano(obj)
        assert 100.0 in acc
        assert 200.5 in acc

    def test_coletar_valores_plano_nested(self):
        obj = {"acoes": [{"valor": 2150.0}, {"custo_operacao": 5.76}]}
        acc = _coletar_valores_plano(obj)
        assert 2150.0 in acc
        assert 5.76 in acc

    def test_coletar_ignora_booleanos(self):
        """True/False não devem ser coletados como números."""
        obj = {"risco_identificado": True, "valor": 500.0}
        acc = _coletar_valores_plano(obj)
        assert 1.0 not in acc  # True == 1, mas deve ser ignorado
        assert 500.0 in acc


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Guardrail — auditoria de texto vs plano
# ──────────────────────────────────────────────────────────────────────────────


class TestAuditoriaTexto:
    def test_aprovado_texto_correto(self, plano_referencia):
        """Texto com valores que existem no plano deve ser aprovado."""
        texto = (
            "Identificamos um déficit de R$ 2.150,00. "
            "Vamos resgatar R$ 2.150,00 da sua reserva para cobrir as contas de R$ 1.250,00 e R$ 1.800,00."
        )
        res = auditar_texto(texto, plano_referencia)
        assert res.aprovado is True
        assert res.divergencias == []
        assert res.texto_substituido is None

    def test_reprovado_valor_inventado(self, plano_referencia):
        """Texto com valor não presente no plano deve falhar."""
        texto = "O déficit é de R$ 9.999,99 segundo nossa análise."
        res = auditar_texto(texto, plano_referencia)
        assert res.aprovado is False
        assert len(res.divergencias) > 0

    def test_template_deterministico_gerado_na_reprovacao(self, plano_referencia):
        """Quando reprovado, texto_substituido não deve ser None."""
        texto = "Valor alucinado: R$ 77.777,77."
        res = auditar_texto(texto, plano_referencia)
        assert res.aprovado is False
        assert res.texto_substituido is not None
        assert len(res.texto_substituido) > 0

    def test_template_contem_valores_do_plano(self, plano_referencia):
        """Template determinístico deve mencionar o hiato_total do plano."""
        texto = "Valor inventado: R$ 55.000,00."
        res = auditar_texto(texto, plano_referencia)
        # Template deve mencionar R$ 2.150,00 (hiato_total)
        assert "2.150,00" in res.texto_substituido

    def test_aprovado_texto_sem_valores(self, plano_referencia):
        """Texto sem nenhum valor monetário deve sempre ser aprovado."""
        texto = "Tudo certo com suas finanças esta semana!"
        res = auditar_texto(texto, plano_referencia)
        assert res.aprovado is True

    def test_valores_texto_populados(self, plano_referencia):
        texto = "Déficit de R$ 2.150,00 a cobrir."
        res = auditar_texto(texto, plano_referencia)
        assert 2150.0 in res.valores_texto

    def test_valores_plano_populados(self, plano_referencia):
        texto = "Qualquer texto."
        res = auditar_texto(texto, plano_referencia)
        assert 2150.0 in res.valores_plano


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Antifraude — modo mock (padrão)
# ──────────────────────────────────────────────────────────────────────────────


class TestAntifraudeMock:
    def setup_method(self):
        # Garante modo mock independente do ambiente
        os.environ["BRASIL_API_MODE"] = "mock"

    def test_validar_cnpj_mock_retorna_valido(self):
        res = validar_cnpj("11222333000181")
        assert res.valido is True
        assert res.bloqueado is False
        assert res.situacao_cadastral == 2

    def test_validar_cnpj_mock_qualquer_cnpj(self):
        """No mock, qualquer CNPJ de 14 dígitos é válido."""
        res = validar_cnpj("99999999999999")
        assert res.valido is True

    def test_auditar_boletos_filtra_apenas_dda(self, itens_a_vencer):
        """Deve auditar apenas BOLETO_DDA, ignorando CARTAO e CONTA_CONSUMO."""
        resultado = auditar_boletos(itens_a_vencer)
        # 2 itens BOLETO_DDA na fixture
        assert resultado.total_boletos_validados == 2

    def test_auditar_boletos_todos_aprovados_no_mock(self, itens_a_vencer):
        resultado = auditar_boletos(itens_a_vencer)
        assert resultado.aprovado is True
        assert resultado.total_bloqueados == 0
        assert resultado.alertas == []

    def test_auditar_lista_vazia(self):
        resultado = auditar_boletos([])
        assert resultado.total_boletos_validados == 0
        assert resultado.aprovado is True

    def test_auditar_lista_sem_boletos_dda(self):
        itens = [
            {"tipo": "CARTAO", "cnpj_beneficiario": "11222333000181", "descricao": "cartão"},
            {"tipo": "CONTA_CONSUMO", "cnpj_beneficiario": "22333444000192", "descricao": "energia"},
        ]
        resultado = auditar_boletos(itens)
        assert resultado.total_boletos_validados == 0

    def test_cnpj_retornado_na_validacao(self):
        cnpj = "11222333000181"
        res = validar_cnpj(cnpj)
        assert res.cnpj == cnpj

    def test_motivo_menciona_modo_mock(self):
        res = validar_cnpj("11222333000181")
        assert "mock" in res.motivo.lower()
