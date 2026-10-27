# Copiloto MEI — Banco do Brasil × IBM

> **IA Agêntica para Saúde Financeira de Microempreendedores Individuais**
> Desafio IBM Experiential Learning Lab — Banco do Brasil
> **Release Candidate v1.0 · 130 testes automatizados · Motor Cognitivo Gemini Flash Lite ativo**

---

## Visão Executiva

O Banco do Brasil serve mais de **15 milhões de MEIs** no Brasil — microempreendedores que enfrentam um problema estrutural: a mistura de finanças pessoais e empresariais, falta de previsibilidade de caixa e o recurso a crédito caro em momentos de aperto financeiro.

Esta solução implementa um **Copiloto de Saúde Financeira** baseado em IA Agêntica sobre a stack IBM:

| Desafio do MEI | Resposta da Solução |
|---|---|
| Mistura PF/PJ e descontrole de caixa | Aggregação via Open Finance com separação automática |
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
└─────┴───────────────────────────────────────────────────────────┘
```

O adaptador percorre a cadeia em ordem. Cada camada captura exceções internamente, garantindo que **nenhum erro é propagado ao frontend**. O campo `"modelo"` na resposta JSON identifica qual camada está ativa (`gemini-flash-lite-latest`, `ibm/granite-*` ou `fallback_local`).

---

## Quick Start

### Pré-requisitos

- Python 3.10+
- Node.js 18+ (para o servidor MCP TypeScript)
- `curl` (para smoke tests)

### 1. Inicialização completa (1 comando)

```bash
./start.sh
```

O script automaticamente:
1. Cria e ativa ambiente virtual Python (`.venv/`)
2. Instala dependências Python (`requirements.txt`) e Node.js (`package.json`)
3. Compila o servidor MCP TypeScript
4. Executa os 130 testes Python
5. Inicia o BFF FastAPI em segundo plano na porta 8000

### 2. Testes unitários + integração (1 comando)

```bash
python3 -m pytest tests/ -v
```

### 3. Smoke tests de API HTTP (1 comando)

```bash
./smoke_test.sh
```

> O BFF precisa estar rodando antes (`./start.sh` ou `uvicorn bff.main:app --port 8000`)

### 4. Apenas o BFF (desenvolvimento)

```bash
uvicorn bff.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Documentação interativa da API

Após subir o BFF: http://localhost:8000/docs

---

## Estrutura do Repositório

```
.
├── agents/
│   ├── cli_bridge.py               # Ponte CLI Python ↔ MCP TypeScript
│   ├── estrategista/
│   │   ├── models.py               # Modelos Pydantic (CanonicalFinancialState, ExecutionPlan)
│   │   └── optimizer.py            # Motor de otimização: projeção P(d) + cascata 3 níveis
│   └── guardiao/
│       ├── antifraude.py           # Validação CNPJ via BrasilAPI (mock|real)
│       └── guardrail.py            # Anti-alucinação numérica (regex + template determinístico)
├── bff/
│   └── main.py                     # FastAPI BFF: /dashboard/home, /copiloto/summary, /authorize
├── src/mcp-server/
│   ├── src/
│   │   ├── index.ts                # Entrypoint stdio MCP
│   │   ├── python-bridge.ts        # Invocação do bridge Python via spawn
│   │   └── tools/
│   │       ├── get-dashboard-state.ts
│   │       ├── execute-saga.ts
│   │       ├── audit-output.ts
│   │       └── validate-cpf-cnpj.ts
│   ├── package.json
│   └── tsconfig.json
├── schemas/
│   └── canonical-financial-state.json   # JSON Schema draft-07 (fonte de verdade)
├── tests/
│   ├── test_optimizer.py           # 61 testes unitários (5 cenários da cascata)
│   ├── test_guardiao.py            # 24 testes (guardrail + antifraude)
│   ├── test_e2e_flow.py            # 56 testes E2E (5 passos + BFF + bridge CLI)
│   └── test_chat_security.py       # 13 testes de segurança (prompt injection + fallback)
├── docs/
│   ├── arquiteturaTecnica.md       # Spec completa: OpenAPI, schemas, algoritmos, Saga
│   ├── contextoNegocioBB.md        # Contexto de negócio e casos de uso MEI
│   ├── telaInicio.jpeg             # Tela de referência Screen_Dashboard
│   └── telaCopiloto.jpeg           # Tela de referência Screen_CopilotoMEI
├── openapi.yaml                    # Especificação OpenAPI 3.0.3 das 4 tools
├── watsonx-agent-spec.yaml         # Manifesto Skills watsonx Orchestrate
├── requirements.txt                # Dependências Python
├── .env.example                    # Variáveis de ambiente (template)
├── start.sh                        # Inicialização unificada
└── smoke_test.sh                   # Smoke tests HTTP com PASS/FAIL colorido
```

---

## Evidência de Testes

### Resultado da suíte completa

```
======================== 130 passed, 1 warning in 27.88s ========================
```

### Detalhamento por suíte

| Suíte | Arquivo | Testes | Resultado |
|---|---|---|---|
| **E2E — Passo 1** | `test_e2e_flow.py::TestPasso1AggregadorEstado` | 7 | ✅ 7/7 |
| **E2E — Passo 2** | `test_e2e_flow.py::TestPasso2EstrategistaPlan` | 9 | ✅ 9/9 |
| **E2E — Passo 3** | `test_e2e_flow.py::TestPasso3Antifraude` | 4 | ✅ 4/4 |
| **E2E — Passo 4** | `test_e2e_flow.py::TestPasso4Guardrail` | 4 | ✅ 4/4 |
| **E2E — BFF + Saga** | `test_e2e_flow.py::TestPasso5BffSaga` | 25 | ✅ 25/25 |
| **E2E — Bridge CLI** | `test_e2e_flow.py::TestBridgeCLI` | 7 | ✅ 7/7 |
| **Guardião** | `test_guardiao.py::TestExtracao` | 9 | ✅ 9/9 |
| **Guardião** | `test_guardiao.py::TestAuditoriaTexto` | 7 | ✅ 7/7 |
| **Guardião** | `test_guardiao.py::TestAntifraudeMock` | 8 | ✅ 8/8 |
| **Optimizer — Telas** | `test_optimizer.py::TestCenarioRealTelaReferencia` | 11 | ✅ 11/11 |
| **Optimizer — Nível 1** | `test_optimizer.py::TestCenarioNivel1Reserva` | 6 | ✅ 6/6 |
| **Optimizer — Nível 2** | `test_optimizer.py::TestCenarioNivel2Antecipacao` | 8 | ✅ 8/8 |
| **Optimizer — Nível 3** | `test_optimizer.py::TestCenarioNivel3Microcredito` | 7 | ✅ 7/7 |
| **Optimizer — Limite** | `test_optimizer.py::TestCenarioLimiteCobertoParcialmente` | 5 | ✅ 5/5 |
| **Segurança — Fluxo Normal** | `test_chat_security.py::TestChatNormalFlow` | 5 | ✅ 5/5 |
| **Segurança — Prompt Injection** | `test_chat_security.py::TestChatPromptInjection` | 4 | ✅ 4/4 |
| **Segurança — Fallback LLM** | `test_chat_security.py::TestChatApiFallback` | 4 | ✅ 4/4 |
| **TOTAL** | | **130** | ✅ **130/130** |

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
| `POST /api/v1/copiloto/chat` | Screen_CopilotoMEI (Chat) | Motor cognitivo dinâmico com LLM Adapter (P1→P2→P3); injeção de contexto canônico e fallback resiliente |

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

### Defesa contra Prompt Injection

O `_GEMINI_SYSTEM_PROMPT` injetado em todas as chamadas ao LLM contém uma **Boundary Restriction** explícita: o modelo é instruído a recusar educadamente qualquer interação fora do escopo de finanças, negócios e tecnologia do BB, mesmo sob tentativas de jailbreak ou redirecionamento de instrução.

```
"REGRA DE SEGURANÇA — BOUNDARY RESTRICTION: Você é estritamente um assistente
financeiro do Banco do Brasil. Se o usuário fizer perguntas fora do escopo de
finanças, negócios, gestão ou tecnologia do BB, RECUSE educadamente."
```

### Fidelidade Numérica

O modelo é travado via System Prompt para utilizar **estritamente os valores do contexto canônico** injetado (Saldo: R$ 7.985,32, Déficit: R$ 2.800,00), impedindo alucinações numéricas antes do disparo da Saga.

```
"REGRA DE FIDELIDADE NUMÉRICA: Você não tem autoridade para aprovar crédito,
alterar saldos ou prometer taxas. Não invente números."
```

### Ocultação de Stack Trace e API Keys

Todos os blocos `try/except` nas chamadas LLM (P1 Gemini e P2 IBM Granite) registram apenas `type(exc).__name__` nos logs internos — nunca `str(exc)`. Isso garante que mensagens de erro contendo API keys, URLs ou tokens **jamais apareçam no payload HTTP** retornado ao frontend, mesmo em cenários de HTTP 429, 503 ou timeout.

### Proteção do `.env`

O arquivo `.gitignore` lista explicitamente `.env` e `*.env`, protegendo todas as credenciais de commits acidentais.

### Testes de Segurança Automatizados

A suíte [`tests/test_chat_security.py`](tests/test_chat_security.py) valida automaticamente:
- Fluxo normal retorna HTTP 200 com schema correto
- Tentativas de prompt injection retornam resposta segura sem vazar credenciais
- Falha simulada do LLM externo garante HTTP 200 via fallback local

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário:

```bash
cp .env.example .env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `BFF_PORT` | `8000` | Porta do servidor BFF FastAPI |
| `BRASIL_API_MODE` | `mock` | `mock` (sem rede) ou `real` (BrasilAPI) |
| `LOG_LEVEL` | `info` | Nível de log uvicorn |
| `PYTHON_BIN` | `python3` | Binário Python para bridge MCP |
| `GOOGLE_API_KEY` | — | **API key Google AI Studio — LLM Adapter P1 (Gemini)** |
| `WATSONX_API_KEY` | — | API key IBM watsonx — LLM Adapter P2 (Granite) |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | Endpoint regional watsonx.ai |
| `WATSONX_PROJECT_ID` | — | Project ID watsonx.ai |
| `WATSONX_MODEL_ID` | `meta-llama/llama-3-3-70b-instruct` | Modelo IBM (fallback automático para Granite quando disponível) |

---

## Referências

- [`docs/arquiteturaTecnica.md`](docs/arquiteturaTecnica.md) — Topologia multiagente, schemas JSON, contratos OpenAPI, protocolo Saga
- [`docs/contextoNegocioBB.md`](docs/contextoNegocioBB.md) — Contexto de negócio, casos de uso MEI, Open Finance
- [`openapi.yaml`](openapi.yaml) — Especificação OpenAPI 3.0.3 completa
- [`watsonx-agent-spec.yaml`](watsonx-agent-spec.yaml) — Manifesto de skills para watsonx Orchestrate
- [`schemas/canonical-financial-state.json`](schemas/canonical-financial-state.json) — JSON Schema draft-07

---

## Referências Técnicas Adicionais

- [`tests/test_chat_security.py`](tests/test_chat_security.py) — Suíte de segurança: prompt injection, fallback LLM, ocultação de stack trace
- [`docs/relatorio_tecnico_mentor.md`](docs/relatorio_tecnico_mentor.md) — Relatório técnico enviado à mentoria IBM sobre credenciais watsonx
- [`bff/main.py`](bff/main.py) — LLM Adapter Pattern, System Prompt com guardrails, cascata P1→P2→P3

---

*IBM Experiential Learning Lab — Banco do Brasil × IBM*
*Release Candidate v1.0 — Motor Cognitivo: Google Gemini Flash Lite (contingência autorizada) · Fallback: IBM Granite ready · 130/130 testes ✅*
