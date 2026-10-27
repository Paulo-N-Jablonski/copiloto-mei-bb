# Plano de Implementação — Copiloto MEI Banco do Brasil (Fase 1)

## Visão Geral

**Objetivo:** Implementar os contratos de integração da Fase 1 do Copiloto MEI: especificação OpenAPI 3.0 completa, JSON Schema canônico e servidor MCP em TypeScript (transporte stdio) expondo as 4 tools ao watsonx Orchestrate.

**Escopo deste sprint:** Fase 1 apenas — sem lógica de negócio dos agentes, sem integração real com Core BB, sem BFF mobile.

**Fora do escopo:** Agentes Python (Fase 2), orquestração watsonx e endpoints BFF (Fase 3).

**Referências de documentação:**
- `docs/arquiteturaTecnica.md` — topologia multiagente, schemas JSON, contratos OpenAPI e protocolo Saga
- `docs/contextoNegocioBB.md` — contexto de negócio, fluxos Open Finance e casos de uso MEI
- `docs/telaInicio.jpeg` / `docs/telaCopiloto.jpeg` — telas de referência com os valores R$ 7.985,32 / R$ 7.750,00 / R$ 4.950,00 / R$ 2.150,00

---

## Estrutura de Diretórios Esperada

```
src/
  mcp-server/
    index.ts                  ← ponto de entrada stdio transport
    tools/
      validate-cpf-cnpj.ts   ← tool 1: onboarding BrasilAPI
      get-dashboard-state.ts  ← tool 2: estado financeiro consolidado
      audit-output.ts         ← tool 3: guardrail watsonx.governance
      execute-saga.ts         ← tool 4: disparo Saga Engine
    schemas/
      canonical-financial-state.ts  ← type definitions compartilhadas
openapi.yaml                  ← especificação OpenAPI 3.0 completa
schemas/
  canonical-financial-state.json  ← JSON Schema draft-07 standalone
package.json
tsconfig.json
```

---

## Sub-Tarefas

### Sub-Tarefa 1 — JSON Schema Canônico (`CanonicalFinancialState`)

**Status:** [x] done

**Intent:**
Criar o JSON Schema draft-07 standalone que define o contrato de dados central do sistema. Este schema é a única fonte de verdade para todos os agentes e ferramentas — qualquer payload que trafega entre agentes deve ser validável contra ele.

**Expected Outcomes:**
- Arquivo `schemas/canonical-financial-state.json` gerado e válido contra o meta-schema draft-07
- Todos os campos obrigatórios documentados: `mei_id`, `resumo_saldos`, `a_vencer_semana`, `receita_prevista_7d`, `diagnostico_risco`
- Valores de exemplo alinhados com os dados das telas: `disponivel: 7985.32`, `total saídas: 7750.00`, `total entradas: 4950.00`, `defice_semana: 2150.00`
- Enum de tipos de compromisso: `["CARTAO", "BOLETO_DDA", "DAS_MEI", "CONTA_CONSUMO"]`
- Enum de rótulos do histograma: `["Hoje", "Sexta", "Sábado", "Domingo", "Segunda", "Terça", "Quarta"]`

**Todo List:**
1. Criar o arquivo `schemas/canonical-financial-state.json` com o schema completo conforme seção 3.1 de `docs/arquiteturaTecnica.md`
2. Adicionar `description` em cada campo para documentação automática
3. Adicionar `example` com os valores reais das telas (R$ 7.985,32, R$ 7.750,00 etc.)
4. Validar o JSON manualmente quanto à sintaxe correta

**Relevant Context:**
- Schema completo definido em `docs/arquiteturaTecnica.md` seção 3.1
- Valores de exemplo confirmados pelas imagens `docs/telaInicio.jpeg` e `docs/telaCopiloto.jpeg`

---

### Sub-Tarefa 2 — Especificação OpenAPI 3.0 (`openapi.yaml`)

**Status:** [x] done

**Intent:**  
Produzir a especificação OpenAPI 3.0.3 completa que será importada como Skills no watsonx Orchestrate. Este arquivo define os 4 contratos de API que o servidor MCP implementará, incluindo referências ao schema canônico.

**Expected Outcomes:**
- Arquivo `openapi.yaml` válido OpenAPI 3.0.3
- 4 paths especificados com `operationId`, request/response schemas completos:
  - `POST /tools/onboarding/validate-cpf-cnpj` → `validateCpfCnpjBinding`
  - `GET /tools/finance/get-dashboard-state` → `getDashboardState`
  - `POST /tools/governance/audit-output` → `auditModelOutput`
  - `POST /tools/execution/execute-saga` → `executeFinancialSaga`
- `CanonicalFinancialState` definido em `components/schemas` e referenciado via `$ref`
- Respostas de erro (400, 401, 500) padronizadas em todos os endpoints

**Todo List:**
1. Criar `openapi.yaml` com o bloco `info` (título, versão 1.0.0, description do projeto)
2. Adicionar `components/schemas/CanonicalFinancialState` referenciando o schema da sub-tarefa 1
3. Implementar o path `POST /tools/onboarding/validate-cpf-cnpj` com validação de patterns (CPF `^\d{11}$`, CNPJ `^\d{14}$`)
4. Implementar o path `GET /tools/finance/get-dashboard-state` com parâmetro `mei_id` obrigatório
5. Implementar o path `POST /tools/governance/audit-output` com campos `texto_gerado` e `plano_calculado`
6. Implementar o path `POST /tools/execution/execute-saga` com campos `biometric_token` e `execution_plan_id`
7. Adicionar respostas de erro padronizadas via `$ref` em todos os paths

**Relevant Context:**
- Contratos de API definidos em `docs/arquiteturaTecnica.md` seção 5
- Padrão de patterns CPF/CNPJ definido na seção 2.3 (Screen_Register) do mesmo documento

---

### Sub-Tarefa 3 — Setup do Projeto TypeScript MCP Server

**Status:** [x] done

**Intent:**  
Scaffoldar o projeto Node.js/TypeScript que hospedará o servidor MCP com transporte stdio. Estabelece a infraestrutura de build que as sub-tarefas 4 e 5 irão popular.

**Expected Outcomes:**
- `package.json` configurado com dependências: `@ibm-generative-ai/node-sdk` ou SDK MCP equivalente, `typescript`, `zod` para validação de schemas em runtime
- `tsconfig.json` configurado para compilação em `dist/`, `strict: true`, target ES2022
- Script `build` e `start` configurados no `package.json`
- Type definitions de `CanonicalFinancialState` em `src/mcp-server/schemas/canonical-financial-state.ts` derivadas do JSON Schema
- Arquivo `src/mcp-server/index.ts` com ponto de entrada stdio funcional (server up, sem tools ainda)

**Todo List:**
1. Criar `package.json` com dependências necessárias para servidor MCP stdio
2. Criar `tsconfig.json` com configurações `strict`, `outDir: dist`, `module: commonjs`
3. Criar `src/mcp-server/schemas/canonical-financial-state.ts` com interfaces TypeScript do schema canônico
4. Criar `src/mcp-server/index.ts` com inicialização do servidor MCP stdio (sem tools registradas ainda)
5. Verificar que `npm run build` compila sem erros de TypeScript

**Relevant Context:**
- Transporte escolhido: stdio (local, executado pelo Bob/watsonx Orchestrate via processo Node.js)
- SDK de referência: skill `build-mcp-server` disponível no Bob para padrões da API `registerTool`

---

### Sub-Tarefa 4 — Implementação das Tools MCP (Handlers)

**Status:** [x] done

**Intent:**  
Implementar os 4 handlers de tools no servidor MCP, cada um registrado via `registerTool()`. Nesta fase, os handlers contêm stubs que retornam dados determinísticos compatíveis com os schemas — sem chamadas reais ao Core BB ou watsonx.

**Expected Outcomes:**
- `src/mcp-server/tools/get-dashboard-state.ts` retorna um `CanonicalFinancialState` stub com os valores exatos das telas (R$ 7.985,32 disponível, déficit de R$ 2.150,00)
- `src/mcp-server/tools/audit-output.ts` retorna `{ aprovado: true, divergencias: [] }` (stub pass-through para a Fase 2)
- `src/mcp-server/tools/execute-saga.ts` valida presença de `biometric_token` e `execution_plan_id` e retorna `{ sucesso: true, recibo_consolidado_id: "REC-STUB-001" }`
- `src/mcp-server/tools/validate-cpf-cnpj.ts` implementado com suporte a mock/real via env var (sub-tarefa 5)
- Todas as 4 tools registradas no `index.ts` e acessíveis pelo protocolo MCP

**Todo List:**
1. Implementar `get-dashboard-state.ts` com stub do `CanonicalFinancialState` usando os valores das telas
2. Implementar `audit-output.ts` com stub pass-through (aprovado: true)
3. Implementar `execute-saga.ts` com validação de campos obrigatórios e resposta stub
4. Registrar as 3 tools acima no `index.ts` via `registerTool()`
5. Verificar que o servidor MCP responde corretamente ao protocolo de listagem de tools

**Relevant Context:**
- Input/output schemas de cada tool definidos em `docs/arquiteturaTecnica.md` seção 5
- Stub do `CanonicalFinancialState` deve usar exatamente: `disponivel: 7985.32`, `a_vencer_semana.total: 7750.00`, `receita_prevista_7d.total: 4950.00`, `diagnostico_risco.defice_semana: 2150.00`

---

### Sub-Tarefa 5 — Tool `validateCpfCnpjBinding` com Modo Mock/Real

**Status:** [x] done

**Intent:**  
Implementar a tool de validação de CPF/CNPJ com suporte a dois modos controlados por variável de ambiente: mock local (desenvolvimento/CI) e chamada real à BrasilAPI (produção/staging). Esta separação garante testes determinísticos sem dependência de rede.

**Expected Outcomes:**
- `src/mcp-server/tools/validate-cpf-cnpj.ts` implementado
- Variável de ambiente `BRASIL_API_MODE=mock|real` controla o comportamento
- Modo `mock`: retorna `{ valido: true, motivo: "CNPJ ativo - validação mock" }` para qualquer entrada válida
- Modo `real`: chama `GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}`, verifica `situacao_cadastral == 2` (ATIVA) e valida a máscara de CPF (`***NNNNNN**`) contra o quadro societário retornado
- Rejeição explícita quando `situacao_cadastral != 2` com `motivo` descritivo
- Tool registrada no `index.ts`

**Todo List:**
1. Criar `src/mcp-server/tools/validate-cpf-cnpj.ts` com estrutura condicional por env var
2. Implementar branch `mock` com resposta determinística
3. Implementar branch `real` com chamada fetch à BrasilAPI e lógica de validação de `situacao_cadastral`
4. Implementar lógica de comparação da máscara de CPF com o retorno da BrasilAPI
5. Registrar a tool no `index.ts`
6. Adicionar `BRASIL_API_MODE` ao `.env.example` com documentação do comportamento esperado

**Relevant Context:**
- Regra de validação definida em `docs/arquiteturaTecnica.md` seção 2.3: `situacao_cadastral != 2` → rejeita; máscara CPF `***{cpf[3:9]}**` deve coincidir com o quadro societário
- Regra também detalhada em `docs/contextoNegocioBB.md` seção 6.1

---

## Contexto para o Agente de Implementação

- O servidor MCP usa **transporte stdio** — não requer porta HTTP, é iniciado como processo filho pelo watsonx Orchestrate ou pelo Bob
- Os valores numéricos dos stubs são **fixos e derivados das telas de referência** — não gerar valores aleatórios
- A ordem de implementação das sub-tarefas deve ser respeitada: 1 → 2 → 3 → 4 → 5 (cada uma tem dependência da anterior)
- Usar `zod` para validação de inputs em runtime nos handlers das tools
- O arquivo `openapi.yaml` deve ser co-localizado na raiz do projeto (não dentro de `src/`) para facilitar importação no watsonx Orchestrate
