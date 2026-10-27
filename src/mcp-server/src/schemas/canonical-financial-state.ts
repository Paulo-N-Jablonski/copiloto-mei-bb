// Interfaces TypeScript derivadas do JSON Schema canonical-financial-state.json (draft-07)
// Fonte de verdade: schemas/canonical-financial-state.json
// Usadas por todos os handlers de tools do servidor MCP.

export type TipoCompromisso = "CARTAO" | "BOLETO_DDA" | "DAS_MEI" | "CONTA_CONSUMO";

export type DiaSemanaRotulo =
  | "Hoje"
  | "Sexta"
  | "Sábado"
  | "Domingo"
  | "Segunda"
  | "Terça"
  | "Quarta";

export interface ItemAVencer {
  id: string;
  descricao: string;
  valor: number;
  dias_para_vencimento: number;
  cnpj_beneficiario: string;
  tipo: TipoCompromisso;
}

export interface HistogramaItem {
  dia_rotulo: DiaSemanaRotulo;
  valor: number;
}

export interface ResumoSaldos {
  /** Soma de saldos líquidos em todas as contas vinculadas. Ex.: 12456.78 */
  saldo_atual: number;
  /** Total de instituições sincronizadas via Open Finance. Ex.: 3 */
  contas_conectadas: number;
  /** Saldo passível de movimentação imediata. Ex.: 7985.32 */
  disponivel: number;
}

export interface AVencerSemana {
  /** Soma acumulada de compromissos. Gatilho: total > receita_prevista_7d.total */
  total: number;
  itens: ItemAVencer[];
}

export interface ReceitaPrevista7d {
  /** Soma total de recebíveis confirmados nos próximos 7 dias. Ex.: 4950.00 */
  total: number;
  /** Distribuição diária para histograma — sempre 7 itens */
  histograma: HistogramaItem[];
}

export interface DiagnosticoRisco {
  /** True quando a_vencer_semana.total > receita_prevista_7d.total */
  risco_identificado: boolean;
  /** Déficit: max(0, saídas - entradas). Ex.: 2150.00 = 7750.00 - 4950.00 */
  defice_semana: number;
  /** ID do ExecutionPlan do Agente 3 para cobertura do déficit */
  acao_recomendada_id: string;
}

export interface CanonicalFinancialState {
  mei_id: string;
  resumo_saldos: ResumoSaldos;
  a_vencer_semana: AVencerSemana;
  receita_prevista_7d: ReceitaPrevista7d;
  diagnostico_risco: DiagnosticoRisco;
}
