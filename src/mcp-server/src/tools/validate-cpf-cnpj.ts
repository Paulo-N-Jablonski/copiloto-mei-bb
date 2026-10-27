/**
 * Tool: validateCpfCnpjBinding
 * operationId: validateCpfCnpjBinding
 * POST /tools/onboarding/validate-cpf-cnpj
 *
 * Valida o vínculo entre CNPJ ativo e CPF mascarado durante o onboarding (Screen_Register).
 *
 * Regras (docs/arquiteturaTecnica.md seção 2.3 e docs/contextoNegocioBB.md seção 6.1):
 *   1. CNPJ deve ter situacao_cadastral == 2 (ATIVA) na BrasilAPI / Receita Federal.
 *   2. A máscara de CPF extraída dos dados do MEI ("***NNNNNN**") deve coincidir com
 *      os dígitos 3 a 8 (índice 3..9) do CPF fornecido pelo usuário.
 *
 * Modo de operação — controlado por variável de ambiente BRASIL_API_MODE:
 *   "mock" (padrão de desenvolvimento/CI): retorna resposta determinística sem chamada de rede.
 *   "real"  (staging/produção): chama GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}
 *
 * BRASIL_API_MODE não definida equivale a "mock".
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

// ──────────────────────────────────────────────────────────────────────────────
// Tipos para o retorno da BrasilAPI /api/cnpj/v1/{cnpj}
// ──────────────────────────────────────────────────────────────────────────────

interface BrasilApiCnpjResponse {
  cnpj: string;
  /** 2 = ATIVA, outros valores indicam situação irregular */
  codigo_natureza_juridica: number;
  situacao_cadastral: number;
  descricao_situacao_cadastral: string;
  razao_social: string;
  nome_fantasia: string | null;
  qsa?: Array<{
    nome_socio: string;
    cpf_representante_legal: string;
  }>;
}

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Gera a máscara de CPF no formato "***NNNNNN**" a partir do CPF completo (11 dígitos).
 * Extrai os dígitos de índice 3 a 8 (6 dígitos centrais) para comparação.
 * Ex.: CPF "12345678901" → "***456789**" (dígitos [3..8] = "456789")
 */
function mascaraCpf(cpf: string): string {
  const digitos = cpf.replace(/\D/g, "");
  const central = digitos.slice(3, 9);
  return `***${central}**`;
}

/**
 * Verifica se a máscara gerada a partir do CPF fornecido pelo usuário aparece
 * nos dados retornados pela BrasilAPI (razão social ou representante legal).
 * A BrasilAPI retorna CPFs do quadro societário mascarados como "***NNNNNN**".
 */
function cpfMatchesBrasilApiData(cpf: string, data: BrasilApiCnpjResponse): boolean {
  const mascara = mascaraCpf(cpf);

  // Verifica nos sócios (QSA) quando disponível
  if (data.qsa && data.qsa.length > 0) {
    return data.qsa.some((socio) => socio.cpf_representante_legal === mascara);
  }

  // Fallback: verifica na razão social (MEIs frequentemente não têm QSA detalhado)
  return data.razao_social.includes(mascara);
}

// ──────────────────────────────────────────────────────────────────────────────
// Modo MOCK — resposta determinística para desenvolvimento e CI
// ──────────────────────────────────────────────────────────────────────────────

function validarMock(_cnpj: string, _cpf: string): { valido: boolean; motivo: string } {
  return {
    valido: true,
    motivo: "CNPJ ativo e CPF vinculado confirmados (modo mock — BRASIL_API_MODE=mock).",
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// Modo REAL — chamada à BrasilAPI
// ──────────────────────────────────────────────────────────────────────────────

async function validarReal(
  cnpj: string,
  cpf: string
): Promise<{ valido: boolean; motivo: string }> {
  const url = `https://brasilapi.com.br/api/cnpj/v1/${cnpj}`;

  let data: BrasilApiCnpjResponse;
  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(8000), // timeout de 8s
    });

    if (!response.ok) {
      return {
        valido: false,
        motivo: `BrasilAPI retornou HTTP ${response.status} para o CNPJ informado. Verifique o número e tente novamente.`,
      };
    }

    data = (await response.json()) as BrasilApiCnpjResponse;
  } catch (err) {
    const mensagem = err instanceof Error ? err.message : String(err);
    return {
      valido: false,
      motivo: `Falha ao consultar BrasilAPI: ${mensagem}. Tente novamente em instantes.`,
    };
  }

  // Regra 1: situacao_cadastral deve ser 2 (ATIVA)
  if (data.situacao_cadastral !== 2) {
    return {
      valido: false,
      motivo: `CNPJ com situação cadastral "${data.descricao_situacao_cadastral}" (código ${data.situacao_cadastral}). Apenas CNPJs com situação ATIVA (código 2) são aceitos.`,
    };
  }

  // Regra 2: máscara do CPF deve coincidir com os dados do quadro societário
  if (!cpfMatchesBrasilApiData(cpf, data)) {
    return {
      valido: false,
      motivo:
        "O CPF informado não coincide com o representante legal ou sócio registrado para este CNPJ na Receita Federal.",
    };
  }

  return {
    valido: true,
    motivo: `CNPJ ativo (${data.razao_social}) e CPF vinculado ao quadro societário confirmados.`,
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// Registro da tool no servidor MCP
// ──────────────────────────────────────────────────────────────────────────────

export function registerValidateCpfCnpj(server: McpServer): void {
  server.registerTool(
    "validateCpfCnpjBinding",
    {
      description:
        "Valida o vínculo entre CNPJ ativo e CPF mascarado durante o onboarding do MEI. " +
        "Consulta a BrasilAPI (Receita Federal) e verifica: " +
        "(1) CNPJ com situação cadastral ATIVA (código 2); " +
        "(2) CPF do titular compatível com o quadro societário registrado. " +
        "Controlado por BRASIL_API_MODE=mock|real (padrão: mock).",
      inputSchema: z.object({
        nome_completo: z
          .string()
          .min(1)
          .describe("Nome completo do titular conforme cadastro."),
        cpf: z
          .string()
          .regex(/^\d{11}$/, "CPF deve conter exatamente 11 dígitos numéricos sem formatação.")
          .describe("CPF do titular sem formatação (apenas dígitos)."),
        cnpj: z
          .string()
          .regex(/^\d{14}$/, "CNPJ deve conter exatamente 14 dígitos numéricos sem formatação.")
          .describe("CNPJ da empresa MEI sem formatação (apenas dígitos)."),
      }),
    },
    async ({ cpf, cnpj }) => {
      const modo = (process.env["BRASIL_API_MODE"] ?? "mock").toLowerCase();

      let resultado: { valido: boolean; motivo: string };

      if (modo === "real") {
        resultado = await validarReal(cnpj, cpf);
      } else {
        // "mock" ou qualquer valor não reconhecido — default seguro para desenvolvimento
        resultado = validarMock(cnpj, cpf);
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(resultado, null, 2),
          },
        ],
        // Marca como erro recuperável se inválido, para que o Agente 1 possa
        // solicitar correção dos dados ao usuário
        ...(resultado.valido ? {} : { isError: true }),
      };
    }
  );
}
