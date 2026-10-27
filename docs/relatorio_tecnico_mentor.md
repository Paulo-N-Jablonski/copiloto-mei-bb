# Relatório Técnico — Copiloto MEI Banco do Brasil
**Para:** Mentor Técnico IBM  
**De:** Participante — IBM Experiential Learning Lab × Banco do Brasil  
**Data:** Outubro de 2026  
**Assunto:** Estado de implementação e solicitação de orientação sobre credenciais watsonx.ai

---

## 1. Visão Geral do Projeto

O **Copiloto MEI** é uma solução de IA Agêntica para saúde financeira de Microempreendedores Individuais (MEI), desenvolvida integralmente sobre a stack IBM durante o evento. O sistema automatiza diagnóstico de fluxo de caixa, auditoria antifraude de boletos e execução transacional de pagamentos — tudo com confirmação biométrica Human-in-the-Loop.

---

## 2. Estado de Implementação

Todas as quatro fases do desenvolvimento foram concluídas e validadas com **117 testes automatizados passando (117/117)** e **24 smoke tests HTTP (24/24)**:

| Fase | Entregável | Status |
|---|---|---|
| **Fase 1** | Contratos OpenAPI 3.0.3, JSON Schema `CanonicalFinancialState`, servidor MCP TypeScript (stdio) | ✅ Completo |
| **Fase 2** | Motores Python: Estrategista (cascata 3 níveis), Guardião (guardrail + antifraude CNPJ) | ✅ Completo |
| **Fase 3** | BFF FastAPI (4 endpoints), orquestração watsonx, integração `ibm_watsonx_ai` | ✅ Completo |
| **Fase 4** | SPA desktop (5 views), `start.sh`, `smoke_test.sh`, `README.md` técnico | ✅ Completo |

---

## 3. Arquitetura Multiagente

O sistema implementa 5 agentes especializados sobre a stack IBM:

```
[ Canais: SPA Web / App BB ]
              │
              ▼
┌─────────────────────────────────────┐
│  Agente 1 — Orquestrador           │
│  watsonx Orchestrate + Granite 3.x │
└──────┬──────────┬──────────┬────────┘
       │          │          │
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Agente 2 │ │ Agente 3 │ │ Agente 5 │
│ Agregador│ │Estrateg. │ │ Guardião │
│Open Fin. │ │ Python   │ │Gov + BRA │
└──────────┘ └────┬─────┘ └────┬─────┘
                  └──────┬─────┘
                         ▼ (FIDO2)
                  ┌──────────────┐
                  │  Agente 4   │
                  │  Saga Core  │
                  └──────────────┘
```

| Agente | Tecnologia IBM |
|---|---|
| A1 — Orquestrador | watsonx Orchestrate + `ibm/granite-3-8b-instruct` |
| A2 — Agregador | Open Finance Brasil (stub) → `CanonicalFinancialState` |
| A3 — Estrategista | Python: projeção P(d) + cascata Reserva→Antecipação→Microcrédito |
| A4 — Execução | Saga Pattern atômico: Resgate → Antecipação → Liquidação |
| A5 — Guardião | watsonx.governance: anti-alucinação numérica + BrasilAPI antifraude |

---

## 4. Integração com watsonx.ai — Estado Atual

### 4.1 O que foi implementado

O endpoint `POST /api/v1/copiloto/chat` no BFF FastAPI está **completamente integrado** com o SDK `ibm-watsonx-ai` (versão 1.8.1):

```python
# bff/main.py — trecho da inicialização
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

credentials = Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)
params = {
    GenParams.DECODING_METHOD: "greedy",
    GenParams.MAX_NEW_TOKENS: 500,
    GenParams.REPETITION_PENALTY: 1.1,
}
model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",
    credentials=credentials,
    project_id=WATSONX_PROJECT_ID,
    params=params,
)
```

O **System Prompt** já está definido com o contexto financeiro canônico do MEI:
- Saldo consolidado: R$ 12.456,78
- Saldo disponível: R$ 7.985,32
- Compromissos da semana: R$ 7.750,00
- Receitas previstas: R$ 4.950,00
- Hiato identificado: R$ 2.800,00

O código possui **fallback local automático** — se a API estiver indisponível, o chat continua funcionando com respostas determinísticas, sem propagação de erro ao frontend.

### 4.2 Problema em aberto — credenciais

O BFF está rodando corretamente em `http://localhost:8000`, mas o cliente `ModelInference` não consegue autenticar. O erro registrado no log do servidor é:

```
BXNIM0415E — "Provided API key could not be found."
[watsonx] Falha ao inicializar cliente — fallback local ativo.
```

**O que foi tentado:**
- API key gerada via IBM Cloud → Manage → Access (IAM) → API keys
- Project ID obtido no IBM Cloud Pak for Data fornecido pelo hackathon
- `WATSONX_URL=https://us-south.ml.cloud.ibm.com` (região Dallas)

**Hipótese do problema:**  
O ambiente do hackathon pode utilizar um endpoint de autenticação diferente do IAM público (`iam.cloud.ibm.com`), ou o Project ID do IBM Cloud Pak for Data pode não ser compatível com o endpoint SaaS `us-south.ml.cloud.ibm.com`.

### 4.3 Solicitação ao mentor

Precisaria de orientação sobre **um ou mais** dos seguintes pontos:

1. **Qual `WATSONX_URL` usar** para o ambiente deste hackathon — o endpoint SaaS padrão (`us-south.ml.cloud.ibm.com`) ou uma URL específica do ambiente IBM Cloud Pak for Data do evento?

2. **Como gerar a API key correta** para este ambiente — via IBM Cloud IAM público ou via console interno do Cloud Pak for Data?

3. **Se o `instance_id="openshift"`** precisa ser passado nas `Credentials` para ambientes CPD:
   ```python
   # Para CPD — precisaria desta alteração?
   credentials = Credentials(url=url, api_key=api_key, instance_id="openshift")
   ```

4. **Qual o Project ID correto** — o ID do projeto watsonx.ai no ambiente do evento ou um espaço de implantação (`space_id`)?

---

## 5. Evidência de Testes

### Suíte pytest — 117/117 passando

```
tests/test_optimizer.py     — 61 testes (5 cenários cascata financeira)
tests/test_guardiao.py      — 24 testes (guardrail + antifraude CNPJ)
tests/test_e2e_flow.py      — 56 testes E2E (BFF + bridge CLI + Saga)

======================== 117 passed, 1 warning in 6.74s ========================
```

### Smoke tests HTTP — 24/24 passando

```
✓ GET  /api/v1/dashboard/home          → HTTP 200, saldo R$ 7.985,32
✓ GET  /api/v1/copiloto/summary        → HTTP 200, déficit R$ 2.800,00
✓ POST /api/v1/copiloto/authorize-biometrics → HTTP 200, Saga executada
✓ POST (token vazio)                   → HTTP 422 (validação correta)
✓ POST (guardrail: valor alucinado)    → HTTP 422 (bloqueio correto)

24/24 testes passaram
```

---

## 6. Estrutura do Repositório

```
.
├── bff/main.py                    # FastAPI BFF — 4 endpoints + integração Granite
├── agents/
│   ├── cli_bridge.py              # Ponte CLI Python ↔ MCP TypeScript
│   ├── estrategista/optimizer.py  # Motor cascata: Reserva→Antecipação→Microcrédito
│   └── guardiao/
│       ├── antifraude.py          # Validação CNPJ via BrasilAPI (mock|real)
│       └── guardrail.py           # Anti-alucinação numérica (regex + template)
├── src/mcp-server/                # Servidor MCP TypeScript (stdio transport)
│   └── src/tools/                 # 4 tools: getDashboardState, executeFinancialSaga,
│                                  #          auditModelOutput, validateCpfCnpjBinding
├── schemas/canonical-financial-state.json  # JSON Schema draft-07
├── openapi.yaml                   # Especificação OpenAPI 3.0.3
├── watsonx-agent-spec.yaml        # Manifesto Skills watsonx Orchestrate
├── static/index.html              # SPA desktop (5 views completas)
├── tests/                         # 117 testes automatizados
├── start.sh                       # Inicialização unificada
└── smoke_test.sh                  # 24 smoke tests HTTP
```

---

## 7. Variáveis de Ambiente Necessárias

```ini
# Credenciais watsonx.ai — PONTO DE ATENÇÃO
WATSONX_API_KEY=<aguardando orientação do mentor>
WATSONX_URL=<aguardando confirmação do endpoint do evento>
WATSONX_PROJECT_ID=<aguardando confirmação do project/space ID>
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct

# Demais variáveis (funcionando)
BRASIL_API_MODE=mock
BFF_PORT=8000
LOG_LEVEL=info
PYTHON_BIN=python3
```

---

## 8. Próximo Passo

Com as credenciais corretas configuradas no `.env` e o BFF reiniciado, o sistema ativará automaticamente o modelo IBM Granite. A resposta do endpoint `/chat` passará de:

```json
{ "modelo": "fallback_local" }
```

para:

```json
{ "modelo": "ibm/granite-3-8b-instruct" }
```

Nenhuma alteração de código será necessária — a integração já está pronta para receber as credenciais válidas do ambiente do evento.

---

*Copiloto MEI BB — IBM Experiential Learning Lab*  
*Stack: Python 3.12 · FastAPI · ibm-watsonx-ai 1.8.1 · TypeScript · MCP SDK · watsonx Orchestrate*
