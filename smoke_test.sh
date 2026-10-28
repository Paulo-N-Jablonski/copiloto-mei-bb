#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# smoke_test.sh — Bateria de Smoke Tests HTTP para o BFF do Copiloto MEI
# Uso: ./smoke_test.sh [--port 8000]
# ─────────────────────────────────────────────────────────────────────────────
# Não usar set -e: os testes precisam continuar mesmo quando assertions falham
set -uo pipefail

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${NC} $*"; PASSED=$((PASSED+1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $*"; FAILED=$((FAILED+1)); }
info() { echo -e "${CYAN}[INFO]${NC} $*"; }

PASSED=0
FAILED=0
BFF_PORT="${1:-8000}"
BASE="http://localhost:${BFF_PORT}"
MEI_ID="smoke-test-mei-001"

# ── Helper: HTTP check ────────────────────────────────────────────────────────
# check_http <description> <expected_status> <curl_args...>
check_http() {
  local desc="$1"; shift
  local expected_status="$1"; shift
  local response
  local http_code

  http_code=$(curl -s -o /tmp/smoke_resp.json -w "%{http_code}" "$@") || {
    fail "$desc — curl falhou"
    return
  }

  if [ "$http_code" -eq "$expected_status" ]; then
    pass "$desc (HTTP $http_code)"
  else
    fail "$desc — esperado HTTP $expected_status, obtido $http_code"
    echo -e "    ${YELLOW}Resposta:${NC} $(cat /tmp/smoke_resp.json | head -c 300)"
  fi
}

# ── Helper: jq assert ─────────────────────────────────────────────────────────
assert_json() {
  local desc="$1"
  local jq_filter="$2"
  local expected="$3"
  local actual

  actual=$(cat /tmp/smoke_resp.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
# navegação segura por múltiplos níveis separados por '.'
keys = '$jq_filter'.lstrip('.').split('.')
val = data
for k in keys:
    if isinstance(val, list):
        val = val[int(k)]
    else:
        val = val.get(k, None)
    if val is None:
        break
print(val)
" 2>/dev/null || echo "__ERROR__")

  if [ "$actual" = "$expected" ]; then
    pass "$desc → $actual"
  else
    fail "$desc — esperado '$expected', obtido '$actual'"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Smoke Tests — Copiloto MEI BFF             ║${NC}"
echo -e "${BOLD}║   Alvo: ${BASE}          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Verificar se o BFF está acessível ────────────────────────────────────────
info "Verificando conectividade com o BFF..."
if ! curl -sf "${BASE}/api/v1/dashboard/home" \
     -H "x-mei-id: ping" -o /dev/null 2>/dev/null; then
  echo -e "${RED}[ERRO]${NC} BFF não acessível em ${BASE}."
  echo -e "       Execute ${BOLD}./start.sh${NC} primeiro ou especifique a porta: ${BOLD}./smoke_test.sh 8000${NC}"
  exit 1
fi
info "BFF acessível. Iniciando testes...\n"

# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}── TESTE 1: GET /api/v1/dashboard/home ──────────────────${NC}"
# ─────────────────────────────────────────────────────────────────────────────

check_http "Endpoint retorna HTTP 200" 200 \
  "${BASE}/api/v1/dashboard/home" \
  -H "x-mei-id: ${MEI_ID}"

assert_json "screen = Screen_Dashboard" \
  ".screen" "Screen_Dashboard"

assert_json "saldo_atual = 12456.78" \
  ".cards_superiores.saldo_atual.valor" "12456.78"

assert_json "saldo_disponivel = 7985.32" \
  ".cards_superiores.saldo_disponivel.valor" "7985.32"

assert_json "contas_conectadas = 3" \
  ".cards_superiores.contas_conectadas.count" "3"

assert_json "total_saidas_semana = 7750.0" \
  ".a_vencer_semana.total" "7750.0"

assert_json "total_receita_prevista = 4950.0" \
  ".receita_prevista.total" "4950.0"

assert_json "alerta exibido = True" \
  ".alerta_saude_financeira.exibir" "True"

assert_json "plano status = PLANO_ESTRUTURADO" \
  ".execution_plan_summary.status" "PLANO_ESTRUTURADO"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}── TESTE 2: GET /api/v1/copiloto/summary ────────────────${NC}"
# ─────────────────────────────────────────────────────────────────────────────

check_http "Endpoint retorna HTTP 200" 200 \
  "${BASE}/api/v1/copiloto/summary" \
  -H "x-mei-id: ${MEI_ID}"

assert_json "screen = Screen_CopilotoMEI" \
  ".screen" "Screen_CopilotoMEI"

assert_json "risco de caixa exibido = True" \
  ".card_risco_caixa.exibir" "True"

assert_json "defice identificado > 0" \
  ".card_risco_caixa.defice" "2800.0"

assert_json "acao pagar contas = 7750.0" \
  ".acoes_recomendadas.0.valor" "7750.0"

assert_json "acao antecipar recebíveis = 3200.0" \
  ".acoes_recomendadas.1.valor" "3200.0"

assert_json "acao aplicar saldo = 7985.32" \
  ".acoes_recomendadas.2.valor" "7985.32"

assert_json "trava de segurança presente" \
  ".trava_seguranca.icone" "lock"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}── TESTE 3: POST /api/v1/copiloto/authorize-biometrics ──${NC}"
# ─────────────────────────────────────────────────────────────────────────────

check_http "Autorização com token válido retorna HTTP 200" 200 \
  "${BASE}/api/v1/copiloto/authorize-biometrics" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"biometric_token\":\"FIDO2-SMOKE-TEST-TOKEN\",\"execution_plan_id\":\"ACT-2026-W43-01\",\"mei_id\":\"${MEI_ID}\"}"

assert_json "sucesso = True" \
  ".sucesso" "True"

RECIBO=$(python3 -c "import json,sys; d=json.load(open('/tmp/smoke_resp.json')); print(d.get('recibo_consolidado_id',''))" 2>/dev/null || echo "")
if [[ "$RECIBO" == REC-* ]]; then
  pass "recibo_consolidado_id gerado → $RECIBO"
else
  fail "recibo_consolidado_id inválido → '$RECIBO'"
fi

assert_json "antifraude aprovado = True" \
  ".antifraude.aprovado" "True"

# Token vazio deve retornar 422
check_http "Token vazio retorna HTTP 422" 422 \
  "${BASE}/api/v1/copiloto/authorize-biometrics" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"biometric_token\":\"\",\"execution_plan_id\":\"ACT-2026-W43-01\",\"mei_id\":\"${MEI_ID}\"}"

# Texto com alucinação deve retornar 422
check_http "Guardrail bloqueia texto com valor inventado (HTTP 422)" 422 \
  "${BASE}/api/v1/copiloto/authorize-biometrics" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"biometric_token\":\"FIDO2-VALID-TOKEN\",\"execution_plan_id\":\"ACT-2026-W43-01\",\"mei_id\":\"${MEI_ID}\",\"texto_gerado\":\"Valor alucinado: R\$ 99.999,99.\"}"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}── RESULTADO FINAL ───────────────────────────────────────${NC}"
TOTAL=$((PASSED+FAILED))
if [ "$FAILED" -eq 0 ]; then
  echo -e "\n  ${BOLD}${GREEN}✓ $PASSED/$TOTAL testes passaram${NC}\n"
  exit 0
else
  echo -e "\n  ${RED}✗ $FAILED/$TOTAL testes falharam${NC}"
  echo -e "  ${YELLOW}Verifique os itens [FAIL] acima e o log em logs/bff.log${NC}\n"
  exit 1
fi
