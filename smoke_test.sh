#!/usr/bin/env bash
# smoke_test.sh — Wrapper POSIX que repassa para smoke_test.py.
#
# Compatibilidade retroativa: qualquer chamada a ./smoke_test.sh [args]
# é redirecionada ao smoke_test.py (Python puro, sem curl/jq).
#
# Referência: docs/RELATORIO_TECNICO_BOB.md seção 2.2.
set -euo pipefail

PORT="${1:-8011}"

if ! command -v python3 &>/dev/null; then
    echo "[ERRO] python3 não encontrado." >&2
    exit 1
fi

exec python3 "$(dirname "$0")/smoke_test.py" --port "$PORT" "${@:2}"
