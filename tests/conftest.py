"""
conftest.py — Isolamento hermético do ambiente de testes.

Anula todas as chaves externas para garantir que nenhum teste
faça chamadas reais a Gemini, watsonx.ai ou BrasilAPI,
independentemente do que estiver no .env local.

Referência: docs/RELATORIO_TECNICO_BOB.md seção 2.2.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Fixture automática (autouse) que cobre toda a suíte.

    Anula variáveis de ambiente de provedores externos para garantir
    execução 100% hermética sem chamadas de rede reais.
    """
    keys_to_clear = [
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "WATSONX_API_KEY",
        "WATSONX_URL",
        "WATSONX_PROJECT_ID",
        "WATSONX_MODEL_ID",
    ]
    for key in keys_to_clear:
        monkeypatch.delenv(key, raising=False)

    # Garante modo mock para BrasilAPI
    monkeypatch.setenv("BRASIL_API_MODE", "mock")
