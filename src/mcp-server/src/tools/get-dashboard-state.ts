/**
 * Tool: getDashboardState
 * operationId: getDashboardState
 * GET /tools/finance/get-dashboard-state
 *
 * Invoca o motor Python (agents/cli_bridge.py → agents/estrategista/optimizer.py)
 * via subprocesso para obter o CanonicalFinancialState com ExecutionPlan calculado
 * e resultado de antifraude dos boletos DDA.
 *
 * Fallback: se o subprocesso falhar, retorna o stub determinístico das telas de referência.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { invokePythonBridge } from "../python-bridge.js";

/** Stub determinístico com valores das telas de referência (fallback offline). */
function buildFallbackState(mei_id: string): Record<string, unknown> {
  return {
    canonical_state: {
      mei_id,
      resumo_saldos: { saldo_atual: 12456.78, contas_conectadas: 3, disponivel: 7985.32 },
      a_vencer_semana: {
        total: 7750.0,
        itens: [
          { id: "COMP-001", descricao: "cartão de crédito",    valor: 1250.0, dias_para_vencimento: 3, cnpj_beneficiario: "11222333000181", tipo: "CARTAO" },
          { id: "COMP-002", descricao: "aluguel",              valor: 1800.0, dias_para_vencimento: 5, cnpj_beneficiario: "22333444000192", tipo: "BOLETO_DDA" },
          { id: "COMP-003", descricao: "conta de energia",     valor: 650.0,  dias_para_vencimento: 6, cnpj_beneficiario: "33444555000103", tipo: "CONTA_CONSUMO" },
        ],
      },
      receita_prevista_7d: {
        total: 4950.0,
        histograma: [
          { dia_rotulo: "Hoje",    valor: 900  },
          { dia_rotulo: "Sexta",   valor: 1200 },
          { dia_rotulo: "Sábado",  valor: 1100 },
          { dia_rotulo: "Domingo", valor: 0    },
          { dia_rotulo: "Segunda", valor: 400  },
          { dia_rotulo: "Terça",   valor: 500  },
          { dia_rotulo: "Quarta",  valor: 850  },
        ],
      },
      diagnostico_risco: { risco_identificado: true, defice_semana: 2800.0, acao_recomendada_id: "ACT-2026-W43-01" },
    },
    execution_plan: { status: "STUB_FALLBACK", hiato_total: 2800.0, acoes: [] },
    antifraude: { aprovado: true, total_boletos_validados: 0, total_bloqueados: 0, alertas: [] },
  };
}

export function registerGetDashboardState(server: McpServer): void {
  server.registerTool(
    "getDashboardState",
    {
      description:
        "Obtém o estado financeiro consolidado do MEI, o ExecutionPlan calculado pelo " +
        "Estrategista Financeiro e o resultado de antifraude dos boletos DDA. " +
        "Invoca o motor Python via bridge CLI; retorna fallback determinístico se offline.",
      inputSchema: z.object({
        mei_id: z.string().describe("Identificador único do MEI no sistema BB. Formato UUID v4."),
      }),
    },
    async ({ mei_id }) => {
      let data: Record<string, unknown>;
      try {
        data = await invokePythonBridge("get_dashboard_state", { mei_id });
      } catch (bridgeErr) {
        console.error("[getDashboardState] Bridge indisponível, usando fallback:", bridgeErr);
        data = buildFallbackState(mei_id);
      }

      return {
        content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
