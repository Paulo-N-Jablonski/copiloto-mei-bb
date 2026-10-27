/**
 * Tool: auditModelOutput
 * operationId: auditModelOutput
 * POST /tools/governance/audit-output
 *
 * Guardrail anti-alucinação numérica do watsonx.governance.
 * Extrai valores monetários do texto gerado pelo modelo Granite via regex
 * e verifica correspondência exata com os nós do ExecutionPlan calculado.
 *
 * Regex de extração: R\$\s?(\d{1,3}(\.\d{3})*,\d{2})
 * Ex.: "R$ 2.150,00" → 2150.00
 *
 * Fase 2 integrará este handler com o watsonx.governance SDK para auditorias
 * em tempo real. Nesta fase (stub), valida somente a estrutura dos inputs.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

// Regex conforme especificado em docs/arquiteturaTecnica.md seção 6
const REGEX_VALOR_MONETARIO = /R\$\s?(\d{1,3}(\.\d{3})*,\d{2})/g;

/**
 * Converte string monetária BR para número float.
 * Ex.: "2.150,00" → 2150.00
 */
function parseBRCurrency(valor: string): number {
  return parseFloat(valor.replace(/\./g, "").replace(",", "."));
}

/**
 * Extrai todos os valores monetários de um texto em linguagem natural.
 * Retorna array de numbers com os valores encontrados.
 */
function extrairValoresMonetarios(texto: string): number[] {
  const matches = [...texto.matchAll(REGEX_VALOR_MONETARIO)];
  return matches.map((m) => parseBRCurrency(m[1]));
}

export function registerAuditOutput(server: McpServer): void {
  server.registerTool(
    "auditModelOutput",
    {
      description:
        "Valida o output do modelo Granite contra guardrails anti-alucinação numérica. " +
        "Extrai valores monetários do texto gerado (R$ X.XXX,XX) e verifica correspondência " +
        "exata com os valores presentes no ExecutionPlan calculado. Invocado pelo Agente 5 " +
        "(Guardião) antes de qualquer resposta ser exibida ao usuário.",
      inputSchema: z.object({
        texto_gerado: z
          .string()
          .describe(
            "Texto em linguagem natural gerado pelo modelo Granite para exibição ao usuário."
          ),
        plano_calculado: z
          .record(z.unknown())
          .describe(
            "ExecutionPlan serializado gerado pelo Agente 3 (Estrategista Financeiro)."
          ),
      }),
    },
    async ({ texto_gerado, plano_calculado }) => {
      const valoresNoTexto = extrairValoresMonetarios(texto_gerado);

      // Extrai recursivamente todos os valores numéricos do plano calculado
      // para verificação de correspondência
      const valoresNoPlano = new Set<number>();
      function coletarNumeros(obj: unknown): void {
        if (typeof obj === "number") {
          valoresNoPlano.add(Math.round(obj * 100) / 100);
        } else if (Array.isArray(obj)) {
          obj.forEach(coletarNumeros);
        } else if (obj !== null && typeof obj === "object") {
          Object.values(obj).forEach(coletarNumeros);
        }
      }
      coletarNumeros(plano_calculado);

      // Verifica se cada valor encontrado no texto tem correspondência no plano
      const divergencias: string[] = [];
      for (const valor of valoresNoTexto) {
        const valorArredondado = Math.round(valor * 100) / 100;
        if (!valoresNoPlano.has(valorArredondado)) {
          divergencias.push(
            `Valor R$ ${valor.toFixed(2).replace(".", ",")} encontrado no texto não tem correspondência no ExecutionPlan.`
          );
        }
      }

      const aprovado = divergencias.length === 0;

      const resultado = {
        aprovado,
        divergencias,
        ...(aprovado
          ? { mensagem: "Todos os valores monetários do texto são consistentes com o ExecutionPlan." }
          : { mensagem: "ALERTA: Divergências detectadas. Template determinístico será emitido." }),
      };

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(resultado, null, 2),
          },
        ],
      };
    }
  );
}
