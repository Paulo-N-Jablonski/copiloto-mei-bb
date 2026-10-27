# BASE CONCEITUAL E TÉCNICA: IA AGÊNTICA PARA O BANCO DO BRASIL
**Programa:** Desafio Banco do Brasil — IBM Experiential Learning Lab  
**Objetivo:** Conceber experiências digitais seguras, inclusivas, personalizadas e proativas utilizando IA Agêntica integrada à stack IBM (watsonx Orchestrate, watsonx.ai, Watson Discovery, watsonx.governance).

---

## 1. PARADIGMA DA SOLUÇÃO: IA AGÊNTICA VS. CHATBOT TRADICIONAL
Para ser efetiva no ecossistema do Banco do Brasil, a solução supera chatbots baseados em FAQ/recuperação de texto e adota um ciclo agêntico autônomo:
1. **Percepção contínua:** Monitora ativamente dados financeiros heterogêneos (Open Finance, extratos, recebíveis Pix/cartão, DDA e boletos).
2. **Raciocínio e Planejamento:** Avalia regras bancárias do BB, calcula projeções orçamentárias e projeta cenários futuros com antecedência.
3. **Uso de Ferramentas (Tools/Function Calling):** Consulta motores de score de crédito, APIs Open Finance, bases da Receita Federal e sistemas antifraude.
4. **Ação Proativa com Governança:** Toma iniciativa de alertar o cliente, formula planos acionáveis de menor impacto financeiro e executa transações com validação em "1 clique".

---

## 2. CASO DE USO PRINCIPAL: COPILOTO DE SAÚDE FINANCEIRA PARA MEIS
* **Público-Alvo:** Microempreendedores Individuais (MEIs), pequenos comerciantes e autônomos.
* **Problema Central:** Mistura recorrente de finanças de Pessoa Física (PF) e Jurídica (PJ), carência de tempo para gestão de fluxo de caixa, falta de previsibilidade orçamentária e recurso a empréstimos caros/cheque especial em momentos de aperto financeiro.
* **Ciclo Operacional do Agente:**
  1. *Monitoramento Ativo:* Análise em tempo real do fluxo de caixa e agendas de recebíveis via Open Finance sem exigir abertura do app pelo usuário.
  2. *Identificação e Alerta:* Detecção precoce de que as contas da semana seguinte superam as receitas previstas.
  3. *Ação Proativa Estruturada:* Notificação no App BB/WhatsApp com plano de ação de menor custo financeiro. Exemplo: *"Identifiquei um risco de caixa de R$ 1.200 para a próxima terça. Posso aplicar R$ 500 da sua poupança e simular antecipação de recebíveis do Pix com taxa reduzida para cobrir o restante?"*
  4. *Resolução em 1 Clique:* Aprovação biométrica do cliente seguida de execução transacional automática pelo ecossistema do BB.

---

## 3. FUNCIONALIDADES COMPLEMENTARES DE ALTO IMPACTO
1. **Defesa Proativa Antifraude e Detecção de Anomalias:**
   * Monitoramento comportamental: cruzamento de boletos recebidos e chaves Pix com bases de fraude conhecidas.
   * Intervenção em tempo real: bloqueio preventivo de boletos com dados bancários adulterados e conferência cadastral do CNPJ do fornecedor.
2. **Recomendação Dinâmica de Microcrédito e Capital de Giro:**
   * Linhas amortecedoras pré-aprovadas: recálculo contínuo de linhas de baixo custo com base no volume de vendas recente.
   * Disparos contextuais: sugestão de crédito de curto prazo atrelada a retorno comercial claro (ex.: compra de estoque com desconto superior aos juros da linha).
3. **Gestão Tributária e Conformidade Automatizada:**
   * Rastreio do DAS-MEI: cálculo automático, agendamento de guias e emissão de alertas preventivos de vencimento.
   * Categorização para IRPF/DASN-SIMEI: etiquetagem automática de débitos, créditos e Pix para geração de relatórios contábeis consolidados (CSV/PDF).

---

## 4. CASO DE USO SECUNDÁRIO: REORGANIZAÇÃO E RENEGOCIAÇÃO DE DÍVIDAS
* **Público-Alvo:** Consumidores e pessoas físicas endividadas.
* **Problema:** Barreiras psicológicas (vergonha de atendimento presencial) e incompreensão das opções matemáticas nos canais convencionais.
* **Fluxo do Agente:**
  1. *Análise Comportamental:* Mapeamento de receitas reais e gastos essenciais para identificar a capacidade real de pagamento mensal.
  2. *Cenários Personalizados:* Formulação de planos acessíveis (ex.: *"Reduzindo R$ 50 em streaming, quitamos sua pendência em 12x de R$ 80"*).
  3. *Trava de Segurança e Formalização:* Aplicação dos tetos de desconto das políticas BB e formalização contratual via biometria facial no app.

---

## 5. TOPOLOGIA MULTIAGENTE E MAPEAMENTO DE TECNOLOGIAS IBM

### 5.1. Camada Maestrina e Orquestração
* **IBM watsonx Orchestrate:**
  * Gestão de sessão, controle de estado do diálogo e catálogo de Skills externas via OpenAPI 3.0 / MCP.
* **IBM watsonx.ai (Modelos Foundation IBM Granite):**
  * Motor cognitivo de roteamento de intenção, reasoning deliberativo e Function Calling multi-etapa.

### 5.2. Agentes Especialistas
1. **Agente Orquestrador & Roteador (Orchestrator & Router):**
   * Recebe gatilhos síncronos (usuário) ou assíncronos (rotinas noturnas de monitoramento).
   * Determina a cadeia de execução entre agentes especialistas e formata respostas para App BB / WhatsApp.
2. **Agente Agregador de Dados (Data Ingestion & Open Finance):**
   * Consulta extratos, poupança, DDA (boletos) e recebíveis (POS/Pix) via APIs do Open Finance Brasil (`https://github.com/OpenBanking-Brasil/openapi`) e APIs Core BB.
   * Normaliza dados brutos heterogêneos num payload JSON unificado e indexa histórico em base vetorial.
3. **Agente Estrategista Financeiro (Financial Planner & Logic):**
   * Projeta caixa diário em janela móvel de 7 a 30 dias: $\text{Projeção} = \text{Receitas Previstas} - \text{Despesas Agendadas}$.
   * Identifica déficits e prioriza resolução pelo Menor Custo Financeiro Efetivo:
     * *Nível 1:* Reserva de liquidez/poupança (Custo Zero).
     * *Nível 2:* Antecipação seletiva de recebíveis de cartão/Pix com taxa reduzida BB.
     * *Nível 3:* Microcrédito pré-aprovado emergencial (apenas para saldo remanescente).
4. **Agente de Execução e Transação (Execution Engine):**
   * Dispara chamadas de escrita no Core Bancário BB (resgate $\to$ antecipação $\to$ liquidação DDA/Pix).
   * Implementa padrão transacional atômico (Saga Pattern): reversão imediata de etapas anteriores caso haja falha intermediária. Emite recibos consolidados.
5. **Agente Guardião e de Conformidade (Safety & Governance Guardrail):**
   * Auditoria anti-alucinação em tempo real via **watsonx.governance** (bloqueio de valores divergentes).
   * Conferência documental e RAG normativo via **IBM Watson Discovery**: validação de PDFs (contratos sociais, notas fiscais) e atualização dinâmica de taxas e regras do BB sem necessidade de retreinar a LLM.
   * Ponto de checagem obrigatório **Human-in-the-Loop** através de autenticação biométrica (FaceID/Digital) antes de qualquer movimentação de recursos.

---

## 6. FLUXO TÉCNICO DAS INTERFACES DO USUÁRIO

### 6.1. Ecrã de Cadastro (Onboarding)
* **Entradas:** Nome Completo, Data de Nascimento, E-mail, Telefone, CNPJ, CPF e Senha.
* **Validação Pré-Persistência:** Consulta à API pública da Receita Federal (BrasilAPI).
  * Verifica se `situacao_cadastral == ATIVA`.
  * Valida vínculo societário comparando o Nome Completo e a máscara de CPF retornada (`***NNNNNN**`) com os dados fornecidos.

### 6.2. Ecrã de Login
* Autenticação via `E-mail/Senha` ou `CPF/Senha` gerando token de sessão seguro (JWT).

### 6.3. Ecrã de Integração Open Finance ("Add New Bank")
* **Passo 1:** Seleção de instituição homologada no Open Finance (ex.: Itaú).
* **Passo 2:** Seleção do perfil da conta a conectar (Pessoa Física ou Pessoa Jurídica).
* **Passo 3:** Consentimento explícito de escopos via checkbox.
* **Passo 4 (Redirecionamento Seguro):** App BB dispara deep-link para o App/Web do banco de origem.
* **Passo 5 (Autenticação Remota):** Usuário autentica com biometria no banco de origem e confirma a partilha.
* **Passo 6 (Retorno e Sincronização):** Retorno automático ao App BB com importação e normalização imediata de saldos e transações.