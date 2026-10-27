/**
 * Tool: executeFinancialSaga
 * operationId: executeFinancialSaga
 * POST /tools/execution/execute-saga
 *
 * Invoca o motor Python via bridge CLI para executar a Saga transacional completa:
 *   Resgate → Antecipação → Liquidação
 *
 * Requer token biométrico FIDO2 (TTL 120s). O bridge Python aplica guardrail
 * antes de executar os passos, garantindo consistência com o ExecutionPlan calculado.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { invokePythonBridge } from "../python-bridge.js";

const BIOMETRIC_TOKEN_TTL_SECONDS = 120;

export function registerExecuteSaga(server: McpServer): void {
  server.registerTool(
    "executeFinancialSaga",
    {
      description:
        "Executa o encadeamento atômico Saga (Resgate → Antecipação → Liquidação) sob " +
        "token biométrico FIDO2. Invoca o motor Python via bridge CLI que aplica o guardrail " +
        "anti-alucinação antes de executar os passos. " +
        `TTL do token: ${BIOMETRIC_TOKEN_TTL_SECONDS} segundos.`,
      inputSchema: z.object({
        biometric_token: z
          .string()
          .min(1)
          .describe(
            `Token criptográfico FIDO2 (TTL ${BIOMETRIC_TOKEN_TTL_SECONDS}s). Obrigatório.`
          ),
        execution_plan_id: z
          .string()
          .min(1)
          .describe("ID do ExecutionPlan gerado pelo Agente 3."),
        mei_id: z
          .string()
          .optional()
          .describe("MEI ID para recuperação do estado. Opcional — usa estado de sessão se omitido."),
        texto_gerado: z
          .string()
          .optional()
          .describe("Texto gerado pelo modelo Granite para validação pelo guardrail antes da execução."),
      }),
    },
    async ({ biometric_token, execution_plan_id, mei_id, texto_gerado }) => {
      if (!biometric_token.trim()) {
        return {
          content: [{ type: "text", text: JSON.stringify({ sucesso: false, erro: "BIOMETRIC_TOKEN_REQUIRED" }) }],
          isError: true,
        };
      }

      try {
        const result = await invokePythonBridge("execute_saga", {
          biometric_token,
          execution_plan_id,
          mei_id: mei_id ?? "unknown",
          ...(texto_gerado ? { texto_gerado } : {}),
        });

        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          content: [{ type: "text", text: JSON.stringify({ sucesso: false, erro: msg }) }],
          isError: true,
        };
      }
    }
  );
}
