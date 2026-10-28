#!/usr/bin/env bash
# run.sh — Script mestre de onboarding e execução do Copiloto MEI BB.
#
# Uso:
#   bash run.sh             # inicia o BFF (porta padrão 8011)
#   bash run.sh --test      # executa a suíte pytest completa
#   bash run.sh --smoke     # executa o smoke_test.py
#   bash run.sh --reload    # inicia com hot-reload (uvicorn --reload)
#   bash run.sh --port 8080 # inicia na porta especificada
#   bash run.sh --mcp       # compila e inicia o servidor MCP TypeScript
#
# Idempotente: recria o venv apenas se necessário (hash de requirements.txt).
# Referência: docs/RELATORIO_TECNICO_BOB.md seção 2.2.

set -euo pipefail

# ── Constantes ────────────────────────────────────────────────────────────────
VENV_DIR=".venv"
REQ_FILE="requirements.txt"
REQ_HASH_FILE=".venv/.req_hash"
BFF_PORT=8011
BFF_HOST="0.0.0.0"
MCP_DIR="src/mcp-server"

# ── Cores ─────────────────────────────────────────────────────────────────────
_GREEN='\033[0;32m'
_YELLOW='\033[1;33m'
_RED='\033[0;31m'
_NC='\033[0m'

info()  { echo -e "${_GREEN}[INFO]${_NC} $*"; }
warn()  { echo -e "${_YELLOW}[WARN]${_NC} $*"; }
error() { echo -e "${_RED}[ERRO]${_NC} $*" >&2; }

# ── Verifica Python ───────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    error "python3 não encontrado. Instale Python 3.11+ antes de continuar."
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VERSION detectado."

# ── Verifica disponibilidade do módulo venv ───────────────────────────────────
# Em imagens distroless/Alpine/Debian-slim, o pacote python3-venv pode estar
# ausente. Verificar aqui garante falha rápida com mensagem acionável para
# operadores de CI/CD antes de qualquer operação de I/O no filesystem.
if ! python3 -m venv --help &>/dev/null; then
    error "Módulo 'venv' não encontrado no Python $PYTHON_VERSION."
    error "Em Debian/Ubuntu: sudo apt install python3-venv"
    error "Em RHEL/CentOS:   sudo dnf install python3"
    error "Em Alpine:        apk add python3 py3-pip"
    exit 1
fi

# ── Cria / atualiza o venv ────────────────────────────────────────────────────
_setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "Criando ambiente virtual em $VENV_DIR ..."
        python3 -m venv "$VENV_DIR"
    fi

    # Detecta o caminho de ativação do venv:
    #   Linux / macOS          → .venv/bin/activate
    #   Windows Git Bash / WSL → .venv/Scripts/activate
    # shellcheck disable=SC1091
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        error "Não foi possível encontrar o script de ativação do venv em $VENV_DIR/bin/ ou $VENV_DIR/Scripts/."
        exit 1
    fi

    # Calcula hash do requirements.txt
    if command -v sha256sum &>/dev/null; then
        CURRENT_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
    elif command -v shasum &>/dev/null; then
        CURRENT_HASH=$(shasum -a 256 "$REQ_FILE" | awk '{print $1}')
    else
        CURRENT_HASH="no-hash-tool"
    fi

    SAVED_HASH=""
    [ -f "$REQ_HASH_FILE" ] && SAVED_HASH=$(cat "$REQ_HASH_FILE")

    if [ "$CURRENT_HASH" != "$SAVED_HASH" ]; then
        info "Dependências desatualizadas — executando pip install ..."
        pip install --quiet --upgrade pip
        pip install --quiet -r "$REQ_FILE"
        echo "$CURRENT_HASH" > "$REQ_HASH_FILE"
        info "Dependências instaladas com sucesso."
    else
        info "Dependências já atualizadas (hash ok)."
    fi
}

# ── Compila MCP TypeScript ────────────────────────────────────────────────────
_build_mcp() {
    if [ ! -d "$MCP_DIR" ]; then
        warn "Diretório $MCP_DIR não encontrado — pulando compilação MCP."
        return
    fi
    if ! command -v node &>/dev/null; then
        warn "Node.js não encontrado — pulando compilação MCP TypeScript."
        return
    fi
    info "Compilando servidor MCP TypeScript ..."
    (cd "$MCP_DIR" && npm install --silent && npm run build --silent)
    info "MCP compilado com sucesso."
}

# ── Parse de argumentos ───────────────────────────────────────────────────────
MODE="server"
for arg in "$@"; do
    case "$arg" in
        --test)    MODE="test" ;;
        --smoke)   MODE="smoke" ;;
        --reload)  MODE="reload" ;;
        --mcp)     MODE="mcp" ;;
        --watsonx) MODE="watsonx" ;;
        --port)    shift; BFF_PORT="$1" ;;
        --port=*)  BFF_PORT="${arg#--port=}" ;;
    esac
done

# ── Setup ─────────────────────────────────────────────────────────────────────
_setup_venv

# ── Execução por modo ─────────────────────────────────────────────────────────
case "$MODE" in
    test)
        info "Executando suíte pytest completa ..."
        # Exit code propagado explicitamente para pipelines CI/CD (GitHub Actions,
        # GitLab CI, Jenkins) detectarem falha sem depender de set -e.
        BRASIL_API_MODE=mock python3 -m pytest tests/ -v --tb=short
        exit $?
        ;;

    smoke)
        info "Executando smoke tests HTTP ..."
        python3 smoke_test.py --host 127.0.0.1 --port "$BFF_PORT"
        exit $?
        ;;

    reload)
        info "Iniciando BFF com hot-reload na porta $BFF_PORT ..."
        uvicorn bff.main:app --host "$BFF_HOST" --port "$BFF_PORT" --reload
        ;;

    mcp)
        _build_mcp
        info "Iniciando BFF + MCP na porta $BFF_PORT ..."
        uvicorn bff.main:app --host "$BFF_HOST" --port "$BFF_PORT"
        ;;

    watsonx)
        # Next Step 2: instala dependências opcionais do IBM watsonx.ai SDK e
        # inicia o BFF com suporte P2 ativo — útil em ambientes de homologação
        # onde o requirements.txt principal foi trocado pela versão slim.
        info "Instalando dependências IBM watsonx.ai (requirements-watsonx.txt) ..."
        pip install --quiet -r requirements-watsonx.txt
        info "Iniciando BFF com suporte watsonx na porta $BFF_PORT ..."
        uvicorn bff.main:app --host "$BFF_HOST" --port "$BFF_PORT"
        ;;

    server)
        info "Iniciando BFF na porta $BFF_PORT ..."
        uvicorn bff.main:app --host "$BFF_HOST" --port "$BFF_PORT"
        ;;
esac

# ──────────────────────────────────────────────────────────────────────────────
# Next Step 4 — Governança de API (docs/RELATORIO_TECNICO_BOB.md §5 item 4)
# ──────────────────────────────────────────────────────────────────────────────
# Em ambiente produtivo, posicione um API Gateway à frente do BFF para aplicar:
#
#   • mTLS (mutual TLS) — autenticação de cliente via certificado X.509
#   • JWT / OAuth 2.0  — validação de tokens de sessão do App BB
#   • Rate Limiting     — por MEI ID (ex.: 60 req/min) para mitigar DDoS/brute-force
#
# Opções homologadas no ecossistema IBM/BB:
#   - IBM API Connect  : https://www.ibm.com/products/api-connect
#   - Kong Gateway OSS : kubectl apply -f kong-ingress.yaml
#   - Apigee (Google)  : apigee.google.com (compatível com GKE / hybrid)
#
# Exemplo de configuração mTLS para uvicorn em homologação:
#   uvicorn bff.main:app --ssl-keyfile ./certs/server.key \
#                        --ssl-certfile ./certs/server.crt \
#                        --ssl-ca-certs ./certs/ca.crt
# ──────────────────────────────────────────────────────────────────────────────
