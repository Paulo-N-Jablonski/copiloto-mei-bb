# Copiloto MEI — Banco do Brasil × IBM

> **IA Agêntica para Saúde Financeira de Microempreendedores Individuais**
> Desafio IBM Experiential Learning Lab — Banco do Brasil
> **Release Candidate v1.2 · 226 testes automatizados · Hardening Bank-Grade + Evidências de IA Agêntica**

---

## Visão Executiva

O Banco do Brasil serve mais de **15 milhões de MEIs** no Brasil — microempreendedores que enfrentam um problema estrutural: a mistura de finanças pessoais e empresariais, falta de previsibilidade de caixa e o recurso a crédito caro em momentos de aperto financeiro.

Esta solução implementa um **Copiloto de Saúde Financeira** baseado em IA Agêntica sobre a stack IBM:

| Desafio do MEI | Resposta da Solução |
|---|---|
| Mistura PF/PJ e descontrole de caixa | Agregação via Open Finance com separação automática |
| Surpresas com contas a vencer | Monitoramento proativo — alerta antes do vencimento |
| Crédito caro como primeira opção | Cascata de menor custo: reserva → antecipação → microcrédito |
| Boletos fraudulentos / adulterados | Guardrail antifraude com validação CNPJ em tempo real |
| Desconfiança em ações autônomas | Human-in-the-Loop: 100% das transações exigem biometria |

> **Nota:** O hiato financeiro calculado pelo Agente 3 é **R$ 2.800,00** (R$ 7.750,00 − R$ 4.950,00), valor que prevalece sobre R$ 2.150,00 mencionado nas telas de mockup de referência.

---

## Topologia Multiagente

```
[ Canais: App BB / WhatsApp / Cron ]
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Agente 1: Orquestrador & Roteador          │
│  watsonx Orchestrate + IBM Granite 3.x      │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
       ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│ Agente 2:  │ │ Agente 3:  │ │ Agente 5:  │
│ Agregador  │ │ Estrategis-│ │ Guardião   │
│ Open Fin.  │ │ ta (Python)│ │ Gov + Disc │
└────────────┘ └─────┬──────┘ └─────┬──────┘
                     │               │
                     └───────┬───────┘
                             ▼ (Token Biométrico FIDO2)
                      ┌────────────┐
                      │ Agente 4:  │
                      │ Execução   │
                      │ Saga Core  │
                      └────────────┘
```

| Agente | Papel | Tecnologia |
|---|---|---|
| **1 — Orquestrador** | Roteamento de intenção, gestão de sessão, formatação | watsonx Orchestrate + Granite |
| **2 — Agregador** | Normaliza saldos PF/PJ, DDA, Pix → `CanonicalFinancialState` | Open Finance Brasil + Core BB |
| **3 — Estrategista** | Projeta caixa 7-30 dias; cascata Reserva → Antecipação → Microcrédito | watsonx.ai Granite (reasoning) |
| **4 — Execução** | Saga atômico: Resgate → Antecipação → Liquidação com rollback | Core BB transacional |
| **5 — Guardião** | Anti-alucinação numérica, antifraude CNPJ, RAG normativo, HITL | watsonx.governance + Discovery |

---

## Motor Cognitivo de Chat — LLM Adapter Pattern

O endpoint de chat do BFF implementa um **LLM Adapter Pattern** com resiliência em 3 camadas. Devido a instabilidades de provisionamento na infraestrutura do watsonx Orchestrate durante o Hackathon, o BFF adota um adaptador de LLM priorizando a estabilidade da demonstração, sob **autorização formal da mentoria técnica IBM**.

```
┌─────────────────────────────────────────────────────────────────┐
│              LLM Adapter — Cadeia de Prioridade                 │
├─────┬───────────────────────────────────────────────────────────┤
│  P1 │ Google Gemini (gemini-flash-lite-latest)                  │
│     │ Via REST · header x-goog-api-key · System Prompt injetado │
│     │ → ATIVO (Google AI Studio · plano Pro)                    │
├─────┼───────────────────────────────────────────────────────────┤
│  P2 │ IBM Granite (watsonx.ai SDK)                              │
│     │ WATSONX_API_KEY + WATSONX_URL + WATSONX_PROJECT_ID        │
│     │ → Retomada automática quando o cluster for restabelecido  │
├─────┼───────────────────────────────────────────────────────────┤
│  P3 │ Motor Semântico Local (Fallback determinístico offline)   │
│     │ Responde sem dependência de rede — sempre disponível      │
│     │ Valores parametrizados via otimizar_fluxo_caixa()         │
└─────┴───────────────────────────────────────────────────────────┘
```

O adaptador percorre a cadeia em ordem. Cada camada captura exceções internamente, garantindo que **nenhum erro é propagado ao frontend**. O campo `"modelo"` na resposta JSON identifica qual camada está ativa (`gemini-flash-lite-latest`, `ibm/granite-*` ou `fallback_local`).

---

## Quick Start

### Pré-requisitos

- Python 3.10+ com módulo `venv` (`python3-venv`)
- Node.js 18+ (para o servidor MCP TypeScript)

> **Nota:** `curl` e `jq` **não** são mais necessários. O smoke test é implementado em Python puro (`smoke_test.py`).

### 1. Inicialização completa (1 comando)

```bash
bash run.sh
```

O script automaticamente:
1. Verifica a disponibilidade do módulo `python3-venv` com mensagem acionável por distro
2. Cria e ativa ambiente virtual Python (`.venv/`)
3. Instala dependências Python (`requirements.txt`) apenas se o hash mudou
4. Inicia o BFF FastAPI na porta **8011**

### 2. Testes unitários + integração

```bash
bash run.sh --test
# ou diretamente:
BRASIL_API_MODE=mock python3 -m pytest tests/ -v
```

### 3. Smoke tests de API HTTP

```bash
bash run.sh --smoke
# (o BFF precisa estar rodando: bash run.sh em outro terminal)
```

### 4. BFF com hot-reload (desenvolvimento)

```bash
bash run.sh --reload
```

### 5. BFF com suporte IBM watsonx.ai (P2)

```bash
bash run.sh --watsonx
# instala ibm-watsonx-ai do requirements-watsonx.txt e inicia o BFF
```

### 6. Documentação interativa da API

Após subir o BFF: http://localhost:8011/docs

---

## Estrutura do Repositório

```
.
├── agents/
│   ├── identificadores.py              # Gerador canônico REC-XXXXXXXX (UUID4, bank-grade)
│   ├── cli_bridge.py                   # Ponte CLI Python ↔ MCP TypeScript
│   ├── estrategista/
│   │   ├── models.py                   # Modelos Pydantic (CanonicalFinancialState, ExecutionPlan)
│   │   └── optimizer.py                # Motor de otimização: projeção P(d) + cascata 3 níveis
│   └── guardiao/
│       ├── antifraude.py               # Validação CNPJ via BrasilAPI (mock|real)
│       └── guardrail.py                # Anti-alucinação numérica (regex + template determinístico)
├── bff/
│   └── main.py                         # FastAPI BFF: /dashboard/home, /copiloto/summary,
│                                       #   /authorize-biometrics, /chat
│                                       #   Inclui: _RedactingFilter, guardrails P0/saída,
│                                       #   LLM Adapter P1→P2→P3, circuit breaker Gemini
├── src/mcp-server/
│   ├── src/
│   │   ├── index.ts                    # Entrypoint stdio MCP
│   │   ├── python-bridge.ts            # Invocação do bridge Python via spawn
│   │   └── tools/
│   │       ├── get-dashboard-state.ts
│   │       ├── execute-saga.ts
│   │       ├── audit-output.ts
│   │       └── validate-cpf-cnpj.ts
│   ├── package.json
│   └── tsconfig.json
├── schemas/
│   └── canonical-financial-state.json  # JSON Schema draft-07 (fonte de verdade)
├── tests/
│   ├── conftest.py                     # Isolamento hermético: anula chaves externas (autouse)
│   ├── test_bff_hardening.py           # 89 testes bank-grade: segurança, guardrails, Pydantic, fallback parametrizado
│   ├── test_chat_security.py           # 13 testes: prompt injection, fallback LLM
│   ├── test_e2e_flow.py                # 56 testes E2E: 5 passos + BFF + bridge CLI
│   ├── test_guardiao.py                # 24 testes: guardrail + antifraude
│   └── test_optimizer.py               # 44 testes unitários: 5 cenários da cascata
├── docs/
│   ├── RELATORIO_TECNICO_BOB.md        # Auditoria bank-grade: diagnóstico, correções, next steps
│   ├── arquiteturaTecnica.md           # Spec completa: OpenAPI, schemas, algoritmos, Saga
│   └── contextoNegocioBB.md            # Contexto de negócio e casos de uso MEI
├── openapi.yaml                        # Especificação OpenAPI 3.0.3 das 4 tools MCP
├── watsonx-agent-spec.yaml             # Manifesto Skills watsonx Orchestrate
├── requirements.txt                    # Dependências Python (completo)
├── requirements-watsonx.txt            # Dependências opcionais IBM watsonx.ai SDK
├── run.sh                              # Script mestre: venv, testes, smoke, --watsonx, --mcp
├── smoke_test.py                       # Smoke tests HTTP em Python puro (sem curl/jq)
├── smoke_test.sh                       # Wrapper POSIX → smoke_test.py (retrocompatibilidade)
├── start.sh                            # Inicialização unificada: venv, testes, BFF na porta 8011 (PORT_OVERRIDE > .env)
└── .env.example                        # Template de variáveis de ambiente
```

---

## Evidência de Testes

### Resultado da suíte completa

```
======================== 226 passed, 22 warnings in 127.42s ========================
```

> Os 22 warnings são deprecações do SDK `ibm-watsonx-ai` (endpoints `/ml/v1/text/generation` e `/ml/v1/text/chat`) — pré-existentes e sem impacto funcional.

### Detalhamento por suíte

| Suíte | Arquivo | Testes | Resultado |
|---|---|---|---|
| **Hardening — Identificadores** | `test_bff_hardening.py::TestIdentificadores` | 13 | ✅ 13/13 |
| **Hardening — Triagem Entrada** | `test_bff_hardening.py::TestTriagemEntrada` | 12 | ✅ 12/12 |
| **Hardening — Validar Saída LLM** | `test_bff_hardening.py::TestValidarSaidaLLM` | 10 | ✅ 10/10 |
| **Hardening — RedactingFilter** | `test_bff_hardening.py::TestRedactingFilter` | 8 | ✅ 8/8 |
| **Hardening — AuthorizeBiometrics** | `test_bff_hardening.py::TestAuthorizeBiometrics` | 14 | ✅ 14/14 |
| **Hardening — Chat** | `test_bff_hardening.py::TestChatHardening` | 15 | ✅ 15/15 |
| **Hardening — InitProviders** | `test_bff_hardening.py::TestInitProviders` | 5 | ✅ 5/5 |
| **Hardening — Fallback Parametrizado** | `test_bff_hardening.py::TestFallbackLocalParametrizado` | 12 | ✅ 12/12 |
| **Segurança — Fluxo Normal** | `test_chat_security.py::TestChatNormalFlow` | 5 | ✅ 5/5 |
| **Segurança — Prompt Injection** | `test_chat_security.py::TestChatPromptInjection` | 4 | ✅ 4/4 |
| **Segurança — Fallback LLM** | `test_chat_security.py::TestChatApiFallback` | 4 | ✅ 4/4 |
| **E2E — Passo 1** | `test_e2e_flow.py::TestPasso1AggregadorEstado` | 7 | ✅ 7/7 |
| **E2E — Passo 2** | `test_e2e_flow.py::TestPasso2EstrategistaPlan` | 9 | ✅ 9/9 |
| **E2E — Passo 3** | `test_e2e_flow.py::TestPasso3Antifraude` | 4 | ✅ 4/4 |
| **E2E — Passo 4** | `test_e2e_flow.py::TestPasso4Guardrail` | 4 | ✅ 4/4 |
| **E2E — BFF + Saga** | `test_e2e_flow.py::TestPasso5BffSaga` | 25 | ✅ 25/25 |
| **E2E — Bridge CLI** | `test_e2e_flow.py::TestBridgeCLI` | 7 | ✅ 7/7 |
| **Guardião — Extração** | `test_guardiao.py::TestExtracao` | 9 | ✅ 9/9 |
| **Guardião — Auditoria Texto** | `test_guardiao.py::TestAuditoriaTexto` | 7 | ✅ 7/7 |
| **Guardião — Antifraude Mock** | `test_guardiao.py::TestAntifraudeMock` | 8 | ✅ 8/8 |
| **Optimizer — Telas Referência** | `test_optimizer.py::TestCenarioRealTelaReferencia` | 11 | ✅ 11/11 |
| **Optimizer — Nível 1** | `test_optimizer.py::TestCenarioNivel1Reserva` | 6 | ✅ 6/6 |
| **Optimizer — Nível 2** | `test_optimizer.py::TestCenarioNivel2Antecipacao` | 8 | ✅ 8/8 |
| **Optimizer — Nível 3** | `test_optimizer.py::TestCenarioNivel3Microcredito` | 7 | ✅ 7/7 |
| **Optimizer — Limite** | `test_optimizer.py::TestCenarioLimiteCobertoParcialmente` | 5 | ✅ 5/5 |
| **TOTAL** | | **226** | ✅ **226/226** |

---

## Contratos de API (OpenAPI 3.0 → MCP → watsonx Skills)

### Os 4 endpoints MCP

| `operationId` | Método + Path | Agente | Descrição |
|---|---|---|---|
| `validateCpfCnpjBinding` | `POST /tools/onboarding/validate-cpf-cnpj` | A1 | Onboarding MEI via BrasilAPI |
| `getDashboardState` | `GET /tools/finance/get-dashboard-state` | A2→A3 | Estado financeiro + ExecutionPlan |
| `auditModelOutput` | `POST /tools/governance/audit-output` | A5 | Guardrail anti-alucinação |
| `executeFinancialSaga` | `POST /tools/execution/execute-saga` | A4 | Saga transacional (requer biometria) |

### BFF Mobile (4 endpoints)

| Endpoint | Tela | Dados retornados |
|---|---|---|
| `GET /api/v1/dashboard/home` | Screen_Dashboard | Saldos, contas a vencer, histograma 7d, alerta déficit |
| `GET /api/v1/copiloto/summary` | Screen_CopilotoMEI | Ações recomendadas, card risco, capacidades do Copiloto |
| `POST /api/v1/copiloto/authorize-biometrics` | Autorização 1-clique | Antifraude + guardrail + recibo Saga consolidado |
| `POST /api/v1/copiloto/chat` | Screen_CopilotoMEI (Chat) | Motor cognitivo dinâmico com LLM Adapter (P1→P2→P3); contexto canônico injetado; fallback resiliente |

### Fluxo de integração

```
openapi.yaml
    └─► watsonx-agent-spec.yaml (Skills catalog)
            └─► watsonx Orchestrate (Agente 1)
                    └─► src/mcp-server/ (stdio transport)
                            └─► agents/cli_bridge.py
                                    ├─► agents/estrategista/optimizer.py (Agente 3)
                                    └─► agents/guardiao/ (Agente 5)
```

---

## Algoritmo do Estrategista (Agente 3)

**Projeção móvel discreta:**

```
P(d) = B_cc + Σ(E_t, t=1..d) − Σ(S_t, t=1..d)   para d ∈ [1, T]
G    = max(0, saidas_total − entradas_total)         (hiato financeiro)
```

**Cascata de minimização de custo:**

```
G > 0?
  Nível 1: Reserva/Poupança    — custo = R$ 0,00
           (preserva colchão de R$ 1.000)
  Nível 2: Antecipação Recebíveis — custo = valor × taxa_diária × dias
           (taxa padrão BB: 0,045% a.d.)
  Nível 3: Microcrédito Emergencial — taxa mensal = 1,89%
           (apenas saldo remanescente)
```

---

## Segurança, Governança e Hardening

Auditoria completa documentada em [`docs/RELATORIO_TECNICO_BOB.md`](docs/RELATORIO_TECNICO_BOB.md).

### Defesa em Profundidade — 4 camadas

| Camada | Mecanismo | Onde |
|---|---|---|
| **P0 — Triagem** | `_triagem_entrada()`: bloqueia jailbreak, DAN, exfiltração antes do LLM | `bff/main.py` |
| **P1 — Anti-alucinação** | `_validar_saida_llm()`: rejeita valores monetários não canônicos na saída | `bff/main.py` |
| **P2 — Antifraude** | Validação CNPJ de todos os boletos DDA via BrasilAPI antes da Saga | `agents/guardiao/antifraude.py` |
| **P3 — Recibo** | ID canônico `REC-[0-9A-F]{8}` com entropia UUID4 no servidor | `agents/identificadores.py` |

### Proteção de Credenciais

- **`_RedactingFilter`** ativo em todos os loggers: ofusca padrões `AIza...`, `Bearer`, `x-goog-api-key`, `WATSONX_API_KEY` antes de qualquer handler de log registrar a mensagem.
- Exceções de provedores externos registram apenas `type(exc).__name__` — nunca payloads ou tracebacks com tokens.
- `load_dotenv(override=False)`: segredos injetados por CI/CD (K8s Secrets, Vault) nunca são sobrescritos por `.env` locais.

### Circuit Breaker Gemini

Cooldown de **30 segundos** após erros 429, 503 ou timeout: tráfego desviado automaticamente para IBM Granite (P2) ou fallback local (P3) sem penalizar o usuário.

### Testes de Segurança Automatizados

A suíte [`tests/test_bff_hardening.py`](tests/test_bff_hardening.py) valida automaticamente (89 testes):
- Geração e validação de recibos canônicos
- Bloqueio de jailbreak, DAN, prompt injection, exfiltração de segredos
- Guardrail de saída: rejeição de valores monetários inventados
- RedactingFilter: ofuscação em mensagens e args de log
- Inicialização independente P1+P2 (sem `return` precoce)
- Circuit breaker: cooldown e desvio de tráfego
- Fallback local parametrizado via `otimizar_fluxo_caixa()` (12 cenários)

---

## Evidências de IA Agêntica no Frontend

O arquivo [`static/index.html`](static/index.html) expõe visualmente onde cada agente IBM está atuando, usando uma paleta de cores dedicada (`#7C3AED` — violeta watsonx):

| Componente | Agente | Indicador visual |
|---|---|---|
| Sidebar — painel "Agentes IA Ativos" | Ag.1–5 | Dots verdes + rótulos `watsonx.ai` (Ag.3) e `gov ✓` (Ag.5) · rodapé `watsonx Orchestrate · 5/5` |
| Card "Ações recomendadas" | **Ag.3 · Estrategista** | Badge roxo `⚡ Agente 3 · watsonx.ai` |
| Card "Risco de caixa" | **Ag.3 + Ag.5** | Badge verde `watsonx.governance` · botão "Ver solução" em violeta watsonx |
| Banner de alerta financeiro | **Ag.3 · Estrategista** | Badge âmbar `Agente 3 · Estrategista` |
| Tabela de boletos (aba Contas) | **Ag.5 · Guardião** | Header `Ag.5 · watsonx.governance` · coluna `Ag.5 · Antifraude` |
| Modal Biometria — fase Saga | **Ag.4 · Executor** | Label inline `Agente 4 · Saga Pattern` |
| Bolha de resposta do chat | **LLM Adapter P1/P2/P3** | Chip `⚡ Gemini Flash · P1` / `🧱 IBM Granite · P2` / `🔁 Fallback Local · P3` |

> O chip de sugestão rápida `'Como economizar R$ 55,20?'` (valor hardcoded desatualizado) foi corrigido para `'Como resolver o risco de caixa?'`.

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário:

```bash
cp .env.example .env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `BFF_PORT` | `8011` | Porta do servidor BFF FastAPI |
| `BRASIL_API_MODE` | `mock` | `mock` (sem rede) ou `real` (BrasilAPI) |
| `LOG_LEVEL` | `info` | Nível de log uvicorn |
| `PYTHON_BIN` | `python3` | Binário Python para bridge MCP |
| `GOOGLE_API_KEY` | — | **API key Google AI Studio — LLM Adapter P1 (Gemini)** |
| `WATSONX_API_KEY` | — | API key IBM watsonx — LLM Adapter P2 (Granite) |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | Endpoint regional watsonx.ai |
| `WATSONX_PROJECT_ID` | — | Project ID watsonx.ai |
| `WATSONX_MODEL_ID` | `meta-llama/llama-3-3-70b-instruct` | Modelo IBM (Granite quando disponível) |

---

## Referências

- [`docs/RELATORIO_TECNICO_BOB.md`](docs/RELATORIO_TECNICO_BOB.md) — Auditoria bank-grade: diagnóstico, vulnerabilidades saneadas, evidências de testes, next steps
- [`docs/arquiteturaTecnica.md`](docs/arquiteturaTecnica.md) — Topologia multiagente, schemas JSON, contratos OpenAPI, protocolo Saga
- [`docs/contextoNegocioBB.md`](docs/contextoNegocioBB.md) — Contexto de negócio, casos de uso MEI, Open Finance
- [`openapi.yaml`](openapi.yaml) — Especificação OpenAPI 3.0.3 completa
- [`watsonx-agent-spec.yaml`](watsonx-agent-spec.yaml) — Manifesto de skills para watsonx Orchestrate
- [`schemas/canonical-financial-state.json`](schemas/canonical-financial-state.json) — JSON Schema draft-07

---

*IBM Experiential Learning Lab — Banco do Brasil × IBM*
*Release Candidate v1.2 — 226/226 testes ✅ · Hardening Bank-Grade · Evidências IA Agêntica no Frontend · Motor Cognitivo: Gemini Flash Lite (contingência autorizada) · IBM Granite ready*
