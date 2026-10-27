#!/usr/bin/env node
/**
 * Servidor MCP do Copiloto MEI — Banco do Brasil
 * Transporte: stdio (processo filho do IBM watsonx Orchestrate / Bob)
 *
 * Expõe 4 tools ao Agente 1 (Orquestrador):
 *   1. validateCpfCnpjBinding  — onboarding via BrasilAPI
 *   2. getDashboardState       — estado financeiro consolidado (CanonicalFinancialState)
 *   3. auditModelOutput        — guardrail anti-alucinação numérica (watsonx.governance)
 *   4. executeFinancialSaga    — execução atômica Saga sob token biométrico FIDO2
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// Tools — importadas individualmente para manter cada handler isolado e testável
import { registerValidateCpfCnpj } from "./tools/validate-cpf-cnpj.js";
import { registerGetDashboardState } from "./tools/get-dashboard-state.js";
import { registerAuditOutput } from "./tools/audit-output.js";
import { registerExecuteSaga } from "./tools/execute-saga.js";

const server = new McpServer({
  name: "bb-copiloto-mei-mcp-server",
  version: "1.0.0",
});

// Registra as 4 tools — cada função recebe a instância do server e chama registerTool()
registerValidateCpfCnpj(server);
registerGetDashboardState(server);
registerAuditOutput(server);
registerExecuteSaga(server);

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // ATENÇÃO: use sempre console.error para logs — console.log escreve no canal MCP (stdout)
  // e corrompe o protocolo.
  console.error("[BB Copiloto MEI MCP] Servidor iniciado via stdio.");
}

main().catch((error: unknown) => {
  console.error("[BB Copiloto MEI MCP] Erro fatal:", error);
  process.exit(1);
});
