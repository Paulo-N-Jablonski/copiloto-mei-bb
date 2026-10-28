#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Inicialização Unificada do Copiloto MEI Banco do Brasil
# Uso: ./start.sh [--no-bff] [--port 8011]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()    { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ── Parâmetros ────────────────────────────────────────────────────────────────
START_BFF=true
BFF_PORT=8011
PORT_OVERRIDE=""   # guarda --port explícito para ter precedência sobre .env

for arg in "$@"; do
  case $arg in
    --no-bff)  START_BFF=false ;;
    --port)    shift; PORT_OVERRIDE="$1" ;;
  esac
done

# ── Diretório raiz ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "\n${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Copiloto MEI — Banco do Brasil / IBM       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}\n"

# ── 1. Verificar Python ───────────────────────────────────────────────────────
info "Verificando Python..."
PYTHON=$(command -v python3 || command -v python || fail "Python 3 não encontrado.")
PYTHON_VERSION=$("$PYTHON" --version 2>&1)
success "$PYTHON_VERSION encontrado em $(command -v "$PYTHON")"

# ── Garante existência do diretório de logs ───────────────────────────────────
mkdir -p logs

# ── 2. Ambiente Virtual (opcional mas recomendado) ────────────────────────────
if [ ! -d ".venv" ]; then
  info "Criando ambiente virtual Python em .venv/ ..."
  "$PYTHON" -m venv .venv
  success "Ambiente virtual criado."
fi

# Activar venv se disponível
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PYTHON=python
  success "Ambiente virtual ativado."
fi

# ── 3. Variáveis de ambiente ───────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    success ".env criado a partir de .env.example"
  else
    warn ".env.example não encontrado; continuando sem .env"
  fi
fi

# Carrega .env se existir (sem override de vars já definidas)
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  success "Variáveis de ambiente carregadas de .env"
fi

# Argumento --port tem precedência sobre .env
[ -n "$PORT_OVERRIDE" ] && BFF_PORT="$PORT_OVERRIDE"

export BRASIL_API_MODE="${BRASIL_API_MODE:-mock}"
export BFF_PORT="${BFF_PORT}"

# ── 4. Dependências Python ────────────────────────────────────────────────────
info "Instalando dependências Python (requirements.txt)..."
"$PYTHON" -m pip install -q -r requirements.txt
success "Dependências Python instaladas."

# ── 5. Dependências Node.js (MCP Server) ──────────────────────────────────────
if command -v node &>/dev/null; then
  info "Instalando dependências Node.js e compilando servidor MCP..."
  (cd src/mcp-server && npm install --silent && npm run build)
  success "Servidor MCP TypeScript compilado em src/mcp-server/build/"
else
  warn "Node.js não encontrado — servidor MCP TypeScript não compilado."
fi

# ── 6. Suíte de testes Python ─────────────────────────────────────────────────
info "Executando suíte de testes Python (226 testes)..."
if BRASIL_API_MODE=mock "$PYTHON" -m pytest tests/ -q --tb=short 2>&1; then
  success "Todos os testes passaram ✓"
else
  fail "Falha nos testes Python. Corrija antes de iniciar o servidor."
fi

# ── 7. Iniciar BFF FastAPI ────────────────────────────────────────────────────
if [ "$START_BFF" = true ]; then
  # Mata processo anterior na porta se existir
  PREV_PID=$(lsof -ti :"$BFF_PORT" 2>/dev/null || true)
  if [ -n "$PREV_PID" ]; then
    warn "Porta $BFF_PORT em uso (PID $PREV_PID). Encerrando processo anterior..."
    kill "$PREV_PID" 2>/dev/null || true
    sleep 1
  fi

  LOG_FILE="logs/bff.log"
  mkdir -p logs

  info "Iniciando BFF FastAPI na porta $BFF_PORT (log: $LOG_FILE)..."
  nohup "$PYTHON" -m uvicorn bff.main:app \
    --host 0.0.0.0 \
    --port "$BFF_PORT" \
    --log-level info \
    > "$LOG_FILE" 2>&1 &
  BFF_PID=$!
  echo "$BFF_PID" > logs/bff.pid

  # Aguarda o servidor subir — health check com Python puro (sem dependência de curl)
  RETRIES=15
  info "Aguardando servidor responder na porta $BFF_PORT..."
  for i in $(seq 1 $RETRIES); do
    if "$PYTHON" -c "
import urllib.request, sys
try:
    urllib.request.urlopen('http://localhost:${BFF_PORT}/api/v1/dashboard/home', timeout=2)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
      success "Servidor BFF pronto!"
      success "  → Interface web:    http://localhost:${BFF_PORT}"
      success "  → Documentação API: http://localhost:${BFF_PORT}/docs"
      break
    fi
    if [ "$i" -eq "$RETRIES" ]; then
      warn "Servidor demorou mais que o esperado. Verifique logs/bff.log"
    else
      sleep 1
    fi
  done
fi

echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  Ambiente iniciado com sucesso!        ${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Interface web:${NC}  http://localhost:${BFF_PORT}"
echo -e "  ${CYAN}Swagger UI:${NC}     http://localhost:${BFF_PORT}/docs"
echo -e "  ${CYAN}Testes:${NC}         bash run.sh --test"
echo -e "  ${CYAN}Smoke tests:${NC}    bash run.sh --smoke"
echo -e "  ${CYAN}Parar BFF:${NC}      kill \$(cat logs/bff.pid)"
echo ""
