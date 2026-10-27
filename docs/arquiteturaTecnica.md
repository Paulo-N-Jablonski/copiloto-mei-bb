# SYSTEM SPECIFICATION: AGENTE COPILOTO DE SAÚDE FINANCEIRA MEI (BANCO DO BRASIL)
**Target Execution Agent:** IBM Bob (IDE / SDLC Code & MCP Generator)  
**Target Platforms:** IBM watsonx Orchestrate, IBM watsonx.ai (Granite 3.x), IBM Watson Discovery, IBM watsonx.governance  
**Objective:** Geração determinística de microsserviços, esquemas OpenAPI 3.0, servidores MCP e lógica de decisão para o Copiloto MEI.

---

## 1. TOPOLOGIA MULTIAGENTE E PAPÉIS

```
[ Canais: App BB / WhatsApp / Cron ]
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Agente 1: Orquestrador & Roteador                          │
│ (watsonx Orchestrate + watsonx.ai Granite)                 │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
       ▼              ▼              │              ▼
┌──────────────┐┌──────────────┐     │      ┌──────────────┐
│ Agente 2:    ││ Agente 3:    │     │      │ Agente 5:    │
│ Agregador    ││ Estrategista │     │      │ Guardião     │
│ (Open Fin. / ││ (Reasoning / │     │      │ (Gov / Disc /│
│ Core BB)     ││ Decisão BB)  │     │      │ Biometria)   │
└──────────────┘└──────┬───────┘     │      └──────┬───────┘
                       │             │             │
                       └─────────────┼─────────────┘
                                     ▼ (Token Biométrico Válido)
                              ┌──────────────┐
                              │ Agente 4:    │
                              │ Execução     │
                              │ (Saga Core)  │
                              └──────────────┘
```

1. **Agente 1 (Orquestrador & Roteador):** Gestão de estado conversacional no watsonx Orchestrate; roteamento de intenções com modelos IBM Granite; formatação para App BB e WhatsApp.
2. **Agente 2 (Agregador de Dados):** Consome Open Finance Brasil (`OpenBanking-Brasil/openapi`) e APIs Core BB; normaliza saldos PF/PJ, DDA, cartões e Pix num payload JSON canónico.
3. **Agente 3 (Estrategista Financeiro):** Motor matemático determinístico no watsonx.ai; projeta caixa de 7 a 30 dias; executa cascata de minimização de custo financeiro (Reserva $\to$ Antecipação $\to$ Microcrédito).
4. **Agente 4 (Execução & Transação):** Execução atómica encadeada via Saga Pattern (Resgate $\to$ Antecipação $\to$ Liquidação) com rollback automático e emissão de recibo único.
5. **Agente 5 (Guardião & Conformidade):** Guardrails no watsonx.governance (anti-alucinação numérica); auditoria antifraude de CNPJ/chaves de boletos; análise documental PDF no Watson Discovery; acionamento obrigatório de biometria (Human-in-the-Loop).

---

## 2. MAPEAMENTO DE INTERFACE E ESTADO DE DADOS (UI/UX BINDINGS)

### 2.1. Tela 1: Dashboard / Início (`Screen_Dashboard`)
* **Header:**
  * Identificação: `user.trade_name` ("AI Solutions!")
  * Notificações e busca rápida global.
* **Cards Superiores (Resumo Financeiro):**
  * `saldo_atual_consolidado`: Soma de saldos líquidos em contas vinculadas (Ex.: `R$ 12.456,78`).
  * `contas_conectadas_count`: Total de instituições sincronizadas via Open Finance (Ex.: `3 Bancos e Carteiras`).
  * `saldo_disponivel_livre`: Saldo passível de movimentação imediata (Ex.: `R$ 7.985,32`).
* **Seção "A Vencer Nesta Semana":**
  * `total_saidas_semana`: Totalizador acumulado de 7 dias (Ex.: `R$ 7.750,00`).
  * Lista de compromissos DDA / cartões / despesas:
    * `cartao_credito`: Valor (Ex.: `R$ 1.250,00`), Vencimento: `hoje + 3 dias`.
    * `aluguel`: Valor (Ex.: `R$ 1.800,00`), Vencimento: `hoje + 5 dias`.
    * `conta_energia`: Valor (Ex.: `R$ 650,00`), Vencimento: `hoje + 6 dias`.
* **Seção "Receita Prevista (Próximos 7 Dias)":**
  * `total_entradas_semana`: Totalizador de recebíveis confirmados (Ex.: `R$ 4.950,00`).
  * Histograma diário: `[Hoje: 900, Sexta: 1200, Sábado: 1100, Domingo: 0, Segunda: 400, Terça: 500, Quarta: 850]`.
* **Alerta Crítico de Risco de Caixa (Card Amarelo):**
  * Gatilho: `total_saidas_semana > total_entradas_semana`.
  * Mensagem dinâmica: `"Suas saídas previstas superam as entradas em R$ 2.150,00 na próxima semana."`
  * Cálculo: $7.750,00 - 4.950,00 = 2.150,00$.
* **Barra de Navegação Inferior:** `[Início, Contas, Agenda, Copiloto (Badge ativo), Perfil]`.

### 2.2. Tela 2: CopilotoMEI (`Screen_Copiloto`)
* **Header:** `"CopilotoMEI - Sua saúde financeira em dia."`
* **Seção "Ações Recomendadas":**
  * Item 1: `Pagar contas a vencer` $\to$ Subtexto: `"7 contas nos próximos 7 dias"` | Valor: `R$ 7.750,00`.
  * Item 2: `Antecipar recebíveis` $\to$ Subtexto: `"Você tem R$ 3.200,00 disponíveis"` | Valor: `R$ 3.200,00`.
  * Item 3: `Aplicar saldo disponível` $\to$ Subtexto: `"Rendimento estimado de 120% do CDI"` | Valor: `R$ 7.985,32`.
* **Card Operacional "Risco de Caixa Identificado" (Ação 1-Clique):**
  * Diagnóstico: `"Na próxima semana, suas saídas previstas podem superar suas entradas em R$ 2.150,00."`
  * Botão Secundário: `Ver solução` (Exibe composição analítica do Agente Estrategista).
  * Botão Primário de Ação: `Autorizar com biometria` (Dispara biometria local e executa Agente 4).
* **Capacidades em Destaque:**
  * Consolidar contas via Open Finance.
  * Projetar fluxo de caixa.
  * Detectar cobranças suspeitas (Antifraude).
  * Executar pagamentos autorizados.
* **Trava de Segurança:** Banner fixo `"Todas as ações exigem sua confirmação."`
* **Floating CTA:** `"Converse com CopilotoMEI"`.

### 2.3. Telas de Suporte (Autenticação e Open Finance)
1. **Cadastro (`Screen_Register`):** Campos: Nome Completo, Data Nasc., E-mail, Telefone, CNPJ, CPF, Senha.
   * *Pré-validação:* Invoca `BrasilAPI` (`GET /api/cnpj/v1/{cnpj}`). Rejeita se `situacao_cadastral != 2` ou se a máscara do CPF `***{cpf[3:9]}**` não coincidir com o quadro societário / razão social.
2. **Login (`Screen_Login`):** Autenticação por E-mail/Senha ou CPF/Senha com emissão de token JWT.
3. **Add New Bank (`Screen_OpenFinance`):** Seleção de instituição cadastrada; seleção de perfil (PF ou PJ); checkbox de consentimento de escopos (`BALANCES_READ`, `TRANSACTIONS_READ`, `RECEIVABLES_READ`); redirecionamento deep-link para o app bancário de origem e sincronização via callback OAuth2.

---

## 3. ESQUEMA DE DADOS CANÓNICO (JSON SCHEMAS)

### 3.1. Estado Financeiro Consolidado (`CanonicalFinancialState`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["mei_id", "resumo_saldos", "a_vencer_semana", "receita_prevista_7d", "diagnostico_risco"],
  "properties": {
    "mei_id": { "type": "string" },
    "resumo_saldos": {
      "type": "object",
      "required": ["saldo_atual", "contas_conectadas", "disponivel"],
      "properties": {
        "saldo_atual": { "type": "number", "example": 12456.78 },
        "contas_conectadas": { "type": "integer", "example": 3 },
        "disponivel": { "type": "number", "example": 7985.32 }
      }
    },
    "a_vencer_semana": {
      "type": "object",
      "required": ["total", "itens"],
      "properties": {
        "total": { "type": "number", "example": 7750.00 },
        "itens": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "descricao", "valor", "dias_para_vencimento", "cnpj_beneficiario", "tipo"],
            "properties": {
              "id": { "type": "string" },
              "descricao": { "type": "string", "example": "cartão de crédito" },
              "valor": { "type": "number", "example": 1250.00 },
              "dias_para_vencimento": { "type": "integer", "example": 3 },
              "cnpj_beneficiario": { "type": "string" },
              "tipo": { "type": "string", "enum": ["CARTAO", "BOLETO_DDA", "DAS_MEI", "CONTA_CONSUMO"] }
            }
          }
        }
      }
    },
    "receita_prevista_7d": {
      "type": "object",
      "required": ["total", "histograma"],
      "properties": {
        "total": { "type": "number", "example": 4950.00 },
        "histograma": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["dia_rotulo", "valor"],
            "properties": {
              "dia_rotulo": { "type": "string", "enum": ["Hoje", "Sexta", "Sábado", "Domingo", "Segunda", "Terça", "Quarta"] },
              "valor": { "type": "number" }
            }
          }
        }
      }
    },
    "diagnostico_risco": {
      "type": "object",
      "required": ["risco_identificado", "defice_semana", "acao_recomendada_id"],
      "properties": {
        "risco_identificado": { "type": "boolean", "example": true },
        "defice_semana": { "type": "number", "example": 2150.00 },
        "acao_recomendada_id": { "type": "string", "example": "ACT-2026-W43-01" }
      }
    }
  }
}
```

---

## 4. ESPECIFICAÇÃO DE ALGORITMO: ESTRATEGISTA FINANCEIRO (AGENTE 3)

### 4.1. Formulação Matemática
* Projeção móvel para horizonte $T \in [7, 30]$ dias:
  $$P(d) = B_{\text{cc}} + \sum_{t=1}^{d} E_t - \sum_{t=1}^{d} S_t$$
  Onde $B_{\text{cc}}$ é o saldo livre, $E_t$ entradas confirmadas e $S_t$ saídas agendadas até o dia $d$.
* Condição de Rutura de Caixa: Existe $d$ tal que $P(d) < 0$.
* Hiato Financeiro Crítico:
  $$G = \left| \min_{d \in [1, T]} P(d) \right| \quad (\text{se } P(d) < 0)$$

### 4.2. Algoritmo em Pseudocódigo Rígido
```python
def otimizar_fluxo_caixa(state: CanonicalFinancialState, taxas_bb: dict) -> ExecutionPlan:
    saidas_totais = state.a_vencer_semana.total
    entradas_totais = state.receita_prevista_7d.total
    gap = round(saidas_totais - entradas_totais, 2)
    
    if gap <= 0:
        return ExecutionPlan(status="SEM_RISCO", deficit=0.0)

    # Inicializa variáveis da cascata
    defice_restante = gap
    operacoes = []
    
    # NÍVEL 1: Alocação de Reserva Líquida / Poupança (Custo Zero)
    reserva_livre = max(0.0, state.resumo_saldos.disponivel - 1000.00) # Mantém R$ 1.000 de colchão
    n1_alocado = min(defice_restante, reserva_livre)
    if n1_alocado > 0:
        operacoes.append({
            "step": 1,
            "tipo": "RESGATE_POUPANCA",
            "valor": n1_alocado
        })
        defice_restante = round(defice_restante - n1_alocado, 2)
        
    # NÍVEL 2: Antecipação Seletiva de Recebíveis (Menor Custo Efetivo)
    n2_antecipado = 0.0
    if defice_restante > 0:
        # Consulta recebíveis antecipáveis disponíveis (ex.: R$ 3.200,00 da UI)
        recebiveis_disp = 3200.00
        n2_alocado = min(defice_restante, recebiveis_disp)
        taxa_diaria = taxas_bb.get("taxa_diaria_antecipacao", 0.00045)
        dias_medio = 4
        custo_desconto = round(n2_alocado * (taxa_diaria * dias_medio), 2)
        
        operacoes.append({
            "step": 2,
            "tipo": "ANTECIPACAO_RECEBIVEIS",
            "valor_bruto": n2_alocado + custo_desconto,
            "valor_liquido": n2_alocado,
            "custo_operacao": custo_desconto
        })
        defice_restante = round(defice_restante - n2_alocado, 2)

    # NÍVEL 3: Microcrédito Emergencial Pré-Aprovado
    if defice_restante > 0:
        operacoes.append({
            "step": 3,
            "tipo": "MICROCREDITO_EMERGENCIAL",
            "valor": defice_restante,
            "taxa_mensal": taxas_bb.get("taxa_microcredito", 0.0189)
        })
        defice_restante = 0.0

    # Adiciona a liquidação das saídas autorizadas no final da esteira
    for item in state.a_vencer_semana.itens:
        operacoes.append({
            "step": 4,
            "tipo": "LIQUIDACAO_COMPROMISSO",
            "id_origem": item.id,
            "valor": item.valor
        })

    return ExecutionPlan(
        status="PLANO_ESTRUTURADO",
        hiato_total=gap,
        acoes=operacoes,
        custo_solucao=sum(op.get("custo_operacao", 0.0) for op in operacoes),
        custo_evitado_multas=round(gap * 0.02 + (gap * 0.0026 * 7), 2)
    )
```

---

## 5. ESPECIFICAÇÃO DE TOOLS NO PADRÃO OPENAPI 3.0 / MCP (IBM BOB)

O IBM Bob deve compilar este contrato no servidor MCP para consumo do watsonx Orchestrate.

```yaml
openapi: 3.0.3
info:
  title: BB Copiloto MEI - Core Engine Tools
  version: 1.0.0
paths:
  /tools/onboarding/validate-cpf-cnpj:
    post:
      operationId: validateCpfCnpjBinding
      summary: Consulta BrasilAPI e verifica se CNPJ é ativo e compatível com o CPF mascarado.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [nome_completo, cpf, cnpj]
              properties:
                nome_completo: { type: string }
                cpf: { type: string, pattern: '^\d{11}$' }
                cnpj: { type: string, pattern: '^\d{14}$' }
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  valido: { type: boolean }
                  motivo: { type: string }

  /tools/finance/get-dashboard-state:
    get:
      operationId: getDashboardState
      summary: Obtém os dados de saldo, agenda a vencer e histograma de receitas dos 7 dias.
      parameters:
        - name: mei_id
          in: query
          required: true
          schema: { type: string }
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CanonicalFinancialState'

  /tools/governance/audit-output:
    post:
      operationId: auditModelOutput
      summary: Executa validação de guardrail anti-alucinação comparando o texto gerado com os valores calculados.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [texto_gerado, plano_calculado]
              properties:
                texto_gerado: { type: string }
                plano_calculado: { type: object }
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  aprovado: { type: boolean }
                  divergencias: { type: array, items: { type: string } }

  /tools/execution/execute-saga:
    post:
      operationId: executeFinancialSaga
      summary: Executa encadeamento atómico (Resgate -> Antecipação -> Pagamento) sob token biométrico.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [biometric_token, execution_plan_id]
              properties:
                biometric_token: { type: string }
                execution_plan_id: { type: string }
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  sucesso: { type: boolean }
                  recibo_consolidado_id: { type: string }
```

---

## 6. PROTOCOLO DE GOVERNANÇA, HUMAN-IN-THE-LOOP E SAGA TRANSACTIONS

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ watsonx.gov     │       │ Biometria BB    │       │ Agente 4 (Saga) │
│ (Anti-Alucinação│       │ (Human-in-the-  │       │ (Execução       │
│ & Antifraude)   │       │  Loop 1-Clique) │       │  Atómica BB)    │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         │ 1. Valida Entidades     │                         │
         │    Numéricas (R$)       │                         │
         │ 2. Checa CNPJ Boleto    │                         │
         ├────────────────────────>│                         │
         │    Emite Intent         │                         │
         │    Auditada             │                         │
         │                         │ 3. Desafio Biométrico   │
         │                         │    no App (FaceID/Dedo) │
         │                         ├────────────────────────>│
         │                         │    Assina Token JWS     │ 4. Executa Passos:
         │                         │    (TTL = 120s)         │    A. Resgata Poupança
         │                         │                         │    B. Antecipa Cartão
         │                         │                         │    C. Liquida Contas
         │                         │                         │
         │                         │                         │ [Se C falhar:]
         │                         │                         │ 5. Rollback: Desfaz
         │                         │                         │    B e reaplica A.
```

1. **Anti-Alucinação Numérica (`watsonx.governance`):** 
   * Regex de extração sobre a resposta textual: `R\$\s?(\d{1,3}(\.\d{3})*,\d{2})`.
   * Todo valor encontrado no texto **deve** ter correspondência exata nos nós do `ExecutionPlan`. Se divergir, aborta e emite template determinístico.
2. **Defesa Antifraude de Boletos:**
   * O CNPJ emissor de cada boleto em `a_vencer_semana` é validado contra a base de dados de beneficiários frequentes e Receita Federal. Contas correntes alteradas de fornecedores habituais geram bloqueio preventivo.
3. **Conferência Documental Dinâmica (`Watson Discovery`):**
   * Manuais de crédito, contratos de adesão e tabelas tarifárias do BB ficam indexados no Watson Discovery. Qualquer alteração em juros do microcrédito ou normas do MEI é atualizada via RAG sem retreinamento da fundação Granite.
4. **Human-in-the-Loop & Padrão Saga:**
   * Nenhuma transação financeira ocorre sem o clique no botão `Autorizar com biometria` associado a token criptográfico FIDO2 (`biometric_token`).
   * As operações seguem o padrão Saga: caso ocorra timeout ou erro HTTP 5xx no passo de liquidação de contas, o Agente de Execução chama as APIs compensatórias de estorno de antecipação e reaplicação em conta de investimento, garantindo saldo intocado.