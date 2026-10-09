/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type UserRole = 'ADMIN' | 'GERENTE' | 'ESTOQUE';

export interface User {
  id: string;
  username: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

export type FunnelStatus = 'PROSPECCAO' | 'ORCAMENTO' | 'APRESENTACAO' | 'NEGOCIACAO' | 'FECHAMENTO' | 'PERDIDO';

export interface Partner {
  id: string;
  name: string;
  office: string;
  phone: string;
  email: string;
  city: string;
  notes: string;
  active: boolean;
  created_at: string;
}

export interface Client {
  id: string;
  name: string;
  email: string;
  phone: string;
  cpf_cnpj: string;
  address: string;
  created_at: string;
  funnel_status: FunnelStatus;
  funnel_id?: string | null;
  partner_id?: string | null;
  partner_name?: string | null;
  lost_reason?: string | null;
  estimated_value?: number | null;
  lead_source?: string | null;
  campaign?: string | null;
  negotiation_value?: number | null;
  // Venda concluida pelo botao "Concluir venda" do Comercial: o card sai do
  // funil de vendas e o projeto nasce na Producao.
  sale_concluded_at?: string | null;
  // Cadastro central: campos de fornecedor (cliente pode ser fornecedor)
  is_supplier?: boolean;
  contact?: string;
  category?: string;
  payment_terms?: string;
  avg_delivery_days?: number | null;
}

export type ProjectStatus = 'ORCAMENTO' | 'PROJETADO' | 'PRODUCAO' | 'MONTAGEM' | 'CONCLUIDO';

export interface ProjectStep {
  id: string;
  label: string;
  completed: boolean;
}

export interface Project {
  id: string;
  title: string;
  client_id: string;
  client_name: string;
  description: string;
  status: ProjectStatus;
  value: number;
  deadline: string;
  steps: ProjectStep[];
  created_at: string;
  funnel_id?: string | null;
  start_date: string | null;
  planned_end_date: string | null;
  actual_end_date: string | null;
  deadline_status: string;
  // Conclusao explicita (botao "Concluir projeto"), independente da coluna do
  // funil — o cliente renomeia as colunas, entao a chave nao serve de regra.
  concluded_at?: string | null;
  is_concluded?: boolean;
  // Garantia (Fase 8): prazo em meses + data-limite derivada na conclusao.
  // in_warranty e calculado no backend (data de hoje <= warranty_until).
  warranty_months?: number;
  warranty_until?: string | null;
  in_warranty?: boolean;
  environments?: ProjectEnvironment[];
  total_area_m2?: number;
  total_environments?: number;
}

export interface ProjectEnvironment {
  id: string;
  project_id: string;
  project_title: string | null;
  name: string;
  env_type: string;
  area_m2: number | null;
  value: number | null;
  status: string;
  created_at: string;
}

export interface Worker {
  id: string;
  name: string;
  active: boolean;
  created_at: string;
}

export interface Machine {
  id: string;
  name: string;
  active: boolean;
  created_at: string;
}

export interface TimeEntry {
  id: string;
  project_id: string;
  project_title: string | null;
  environment_id: string | null;
  environment_name: string | null;
  worker_id: string | null;
  worker_name: string | null;
  machine_id: string | null;
  machine_name: string | null;
  hours: number;
  hours_type: string;
  work_date: string;
  notes: string;
  created_by: string;
  created_at: string;
}

export interface ProductionIssue {
  id: string;
  project_id: string;
  project_title: string | null;
  kind: string;
  worker_id: string | null;
  worker_name: string | null;
  material: string;
  quantity: number | null;
  hours_spent: number | null;
  cost: number | null;
  reason: string;
  issue_date: string;
  notes: string;
  created_at: string;
}

/** Item de checklist ainda em aberto, como /api/production/pending devolve. */
export interface PendingChecklistItem {
  id: string;
  project_id: string;
  project_title: string | null;
  label: string;
  step_id: string;
}

/**
 * Pendencias de producao de TODOS os projetos num periodo: ocorrencias
 * (retrabalho/desperdicio/perda) com custo somado + itens de checklist abertos.
 */
export interface ProductionPending {
  period: { from: string | null; to: string | null };
  issues: ProductionIssue[];
  issues_count: number;
  issues_total_cost: number;
  issues_without_cost: number;
  issues_by_kind: Record<string, { count: number; cost: number }>;
  checklist: PendingChecklistItem[];
  checklist_count: number;
}

export type FinancialType = 'ENTRADA' | 'SAIDA';

/** Bucket do aging: quantos lancamentos e quanto dinheiro ha nele. */
export interface AgingBucket {
  count: number;
  total: number;
}

/**
 * Aging das contas em aberto, devolvido por /api/financial/aging.
 * `no_due_date` existe porque lancamento sem vencimento nao pode entrar em
 * bucket nenhum — sem esse campo o total dos buckets mentiria.
 */
export interface AgingResult {
  type: FinancialType;
  reference_date: string;
  open_count: number;
  open_total: number;
  buckets: {
    vencidas: AgingBucket;
    '0_7': AgingBucket;
    '8_30': AgingBucket;
    acima_30: AgingBucket;
  };
  no_due_date: AgingBucket;
}

export interface FinancialRecord {
  id: string;
  description: string;
  type: FinancialType;
  category: string;
  amount: number;
  date: string;
  due_date: string;
  project_id?: string;
  project_title?: string | null;
  client_id?: string | null;
  client_name?: string | null;
  supplier_id?: string | null;
  supplier_name?: string | null;
  status: 'PAGO' | 'PENDENTE';
  doc_number?: string;
  issue_date?: string | null;
  doc_type?: string;
  bank?: string;
  account_plan?: string;
  item_description?: string;
  installments?: number;
  is_recurring?: boolean;
  bank_account_id?: string | null;
  bank_account_name?: string | null;
}

export interface BankAccount {
  id: string;
  name: string;
  bank: string;
  agency: string;
  account_number: string;
  account_type: string;
  opening_balance: number;
  opening_date: string | null;
  active: boolean;
  low_balance_threshold: number | null;
  notes: string;
  created_at: string;
  current_balance: number;
}

export interface BankBalance {
  id: string;
  name: string;
  current_balance: number;
  projected_balance: number;
  opening_balance: number;
  entradas_pagas: number;
  saidas_pagas: number;
  entradas_pendentes: number;
  saidas_pendentes: number;
}

export interface BankOverview {
  total_balance: number;
  total_projected: number;
  accounts: BankAccount[];
}

export interface Supplier {
  id: string;
  name: string;
  cnpj: string;
  contact: string;
  phone: string;
  email: string;
  created_at: string;
  address: string;
  category: string;
  payment_terms: string;
  avg_delivery_days: number | null;
}

/**
 * Fornecedor unificado para selects (Compras/Financeiro): merge da tabela
 * legada suppliers (source='supplier', id com prefixo 'sup-') com clientes
 * marcados como fornecedor (source='client', id = client id).
 */
export interface Vendor extends Supplier {
  source: 'supplier' | 'client';
  client_id?: string | null;
  is_supplier?: boolean;
  needs_mirror?: boolean;
}

export interface PurchaseItem {
  id: string;
  order_id: string;
  stock_item_id: string | null;
  material_name: string;
  quantity: number;
  unit_price: number;
  received_qty: number;
  position: number;
  total: number;
}

export interface PurchaseOrder {
  id: string;
  number: string;
  status: string;
  supplier_id: string | null;
  supplier_name: string | null;
  request_date: string;
  expected_date: string | null;
  received_at: string | null;
  notes: string;
  carrier?: string | null;
  tracking?: string | null;
  /** Quantas cotacoes o pedido tem (0 = economia estimada, nao medida). */
  quotations_count?: number;
  /** Economia MEDIDA pelas cotacoes; 0 quando nao ha cotacao. */
  saving_real?: number;
  /** Quantos itens tem cotacao — diz se saving_real cobre o pedido todo. */
  saving_real_items?: number;
  created_by: string;
  created_at: string;
  items: PurchaseItem[];
  total: number;
}

/** Preco de um item do pedido dentro de uma cotacao. */
export interface PurchaseQuotationItem {
  id: string;
  quotation_id: string;
  purchase_item_id: string;
  purchase_item_name: string | null;
  unit_price: number;
}

/** Cotacao de um fornecedor para um pedido. Varias por pedido. */
export interface PurchaseQuotation {
  id: string;
  order_id: string;
  supplier_id: string | null;
  supplier_name: string | null;
  delivery_days: number | null;
  payment_terms: string;
  is_winner: boolean;
  notes: string;
  created_at: string;
  items: PurchaseQuotationItem[];
  total: number;
}

// ── Comercial (propostas e comissoes) ────────────────────────────────
export type ProposalStatus = 'RASCUNHO' | 'ENVIADA' | 'ACEITA' | 'RECUSADA';

export interface ProposalItem {
  id: string;
  proposal_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  position: number;
  subtotal: number;
}

export interface Proposal {
  id: string;
  number: string;
  client_id: string;
  client_name: string | null;
  project_id: string | null;
  status: ProposalStatus;
  /** Total gravado — sempre igual a items_total (o backend recalcula). */
  total_value: number;
  items_total: number;
  valid_until: string | null;
  notes: string;
  sent_at: string | null;
  sent_channel: string;
  created_by: string;
  created_at: string;
  items: ProposalItem[];
}

export interface CommissionRule {
  id: string;
  seller_id: string | null;
  seller_name: string | null;
  partner_id: string | null;
  partner_name: string | null;
  percent: number;
  valid_from: string | null;
  valid_until: string | null;
  active: boolean;
  notes: string;
  created_at: string;
}

export interface CommissionRow {
  rule_id: string;
  kind: 'VENDEDOR' | 'PARCEIRO';
  seller_id: string | null;
  partner_id: string | null;
  name: string;
  percent: number;
  sales_count: number;
  sold_value: number;
  commission_value: number;
}

export interface CommissionReport {
  year: number;
  month: number | null;
  total_sold: number;
  closed_count: number;
  total_commission: number;
  rows: CommissionRow[];
  /** Vendas fechadas que nao entram na conta de ninguem — mostradas, nao somadas. */
  sem_atribuicao: { count: number; sold_value: number };
}

export interface AppSetting {
  key: string;
  value: string;
  configured: boolean;
  secret: boolean;
}

export interface BudgetGoal {
  id: string;
  year: number;
  month: number | null;
  category: string;
  target_value: number;
  created_at: string;
}

export interface BudgetAnalysis {
  title: string;
  period: { year: number; month: number | null };
  summary: { label: string; value: string; tone: string }[];
  columns: { key: string; label: string }[];
  rows: {
    category: string;
    budget: string;
    actual: string;
    difference: string;
    percentage: string;
    _budget?: number;
    _actual?: number;
  }[];
}

export interface Category {
  id: string;
  name: string;
  description?: string | null;
  category_type: 'STOCK' | 'FINANCIAL';
}

export interface StockItem {
  id: string;
  name: string;
  sku: string;
  category_id: string;
  category_name: string;
  quantity: number;
  min_quantity: number;
  unit: string; // e.g., 'm²', 'unidade', 'kg', 'par', 'chapa'
  price: number;
  supplier: string;
}

export interface StockMovement {
  id: string;
  item_id: string;
  item_name: string;
  // PERDA entra pelo registro de perda/avaria, nunca pelo formulário de
  // movimentação (que só lança ENTRADA ou SAIDA).
  type: 'ENTRADA' | 'SAIDA' | 'PERDA';
  quantity: number;
  reason: string;
  created_by: string;
  date: string;
}

export type StockLossKind = 'PERDA' | 'AVARIA';

export interface StockLoss {
  id: string;
  stock_item_id: string;
  item_name: string | null;
  item_sku: string | null;
  unit: string | null;
  quantity: number;
  kind: StockLossKind;
  reason: string;
  cost: number;
  loss_date: string;
  created_by: string;
  created_at: string;
}

export interface StockLossSummaryBlock {
  key: string;
  count: number;
  quantity: number;
  cost: number;
}

export interface StockLossSummary {
  count: number;
  total_quantity: number;
  total_cost: number;
  by_kind: StockLossSummaryBlock[];
  by_reason: StockLossSummaryBlock[];
  date_from: string | null;
  date_to: string | null;
}

// ── Relatórios ──────────────────────────────────────────────────

export type ReportArea = 'financial' | 'clients' | 'projects' | 'stock' | 'dre' | 'crm' | 'lead-sources' | 'cash-flow' | 'cash-flow-weekly' | 'tickets' | 'production' | 'partners' | 'best-products';

export interface ReportColumn {
  key: string;
  label: string;
}

export interface ReportSummaryItem {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface ReportResult {
  title: string;
  generated_at: string;
  filters_applied: Record<string, unknown>;
  summary: ReportSummaryItem[];
  columns: ReportColumn[];
  rows: Record<string, string>[];
  produzido_mes?: { year: number; month: number; qtd: number; total: number };
  produzido_ano?: {
    year: number; qtd: number; total: number;
    evolucao: { mes: string; rotulo: string; qtd: number; total: number }[];
  };
  entregas_previstas?: { title: string; client: string; deadline: string | null; value: number }[];
  pendencias?: { checklist_abertos: number; ocorrencias: number };
}

// ── Relatorio comercial (/api/reports/crm) ───────────────────────
// Formato proprio: este endpoint NAO segue o padrao {summary, columns, rows}
// dos outros relatorios. Tipar aqui evita tratar `summary` como se existisse.
export interface FechamentoItem {
  client_id: string | null;
  name: string;
  data: string | null;
  valor: number;
  origem: 'sale' | 'crm';
}

/** Fechado no CRM sem Sale gerada — /api/reports/crm `vendas_pendentes_geracao`. */
export interface VendaPendenteGeracao {
  client_id: string;
  name: string;
  data?: string | null;
  valor?: number;
  closed_at?: string | null;
  negotiation_value?: number | null;
  estimated_value?: number | null;
}

export interface CrmReport {
  conversao: { taxa: number; total_clientes: number; total_fechamentos: number; undated?: number };
  fluxo_caixa: { mes: string; receitas: number; despesas: number; resultado: number }[];
  fontes_lead: { fonte: string; total: number }[];
  negociacoes: {
    perdidas: { name: string; created_at: string; lost_reason: string | null }[];
    por_etapa: { funnel_status: string; total: number }[];
    total: number;
    total_perdidas: number;
  };
  parceiros: unknown[];
  partner_clients_count: number;
  periodo: { date_from: string | null; date_to: string | null; year?: number; month?: number; period?: string; de?: string; ate?: string };
  fechamentos_periodo?: {
    qtd: number; valor_total: number; undated: number; de: string; ate: string;
    itens: FechamentoItem[];
  };
  ticket_medio: {
    maximo: number; media: number; minimo: number;
    total_faturado: number; total_projetos: number;
    origem?: string;
  };
  vendas_por_parceiro: unknown[];
  top_products?: TopProduct[];
  vendas_mes?: { year: number; month: number; qtd: number; total: number; itens?: FechamentoItem[] };
  vendas_ano?: {
    year: number; qtd: number; total: number;
    evolucao: { mes: string; rotulo: string; qtd: number; total: number }[];
    itens?: FechamentoItem[];
  };
  orcamentos?: { qtd: number; valor: number; aceitas: number };
  vendas_por_origem?: { origem: string; qtd: number; valor: number; share: number }[];
  /** Fechados sem venda gerada (ex: Manúcia Piaia) — com ação "Gerar venda".
   * Backend devolve OBJETO {qtd, itens}; o tipo aceita as duas formas por
   * compatibilidade (o painel normaliza com Array.isArray antes do .map). */
  vendas_pendentes_geracao?: VendaPendenteGeracao[] | { qtd: number; itens: VendaPendenteGeracao[] };
}

// ── Painel inicial: meta comercial e pendencias ──────────────────

export type GoalScope = 'GERAL' | 'VENDEDOR' | 'PARCEIRO';

export interface SalesGoal {
  id: string;
  year: number;
  month: number | null;
  scope: GoalScope;
  user_id: string | null;
  partner_id: string | null;
  target_value: number;
  created_at: string;
}

export interface SalesGoalSummary {
  year: number;
  month: number | null;
  scope: GoalScope;
  target: string;
  achieved: string;
  remaining: string;
  percent: string;
  deals_closed: number;
  undated: number;
  target_basis: 'mes' | 'ano';
  basis: string;
  generated_at: string;
}

export interface AttentionItem {
  kind: 'CONTA_VENCIDA' | 'CONTA_A_VENCER' | 'CHAMADO_ABERTO' | 'PROJETO_ATRASADO' | 'ORCAMENTO_SEM_RETORNO';
  label: string;
  detail: string;
  count: number;
  total: string | null;
  tone: 'positive' | 'negative' | 'neutral' | 'warning';
  module: string;
  tab: string;
}

export interface AttentionResult {
  generated_at: string;
  reference_date: string;
  total_items: number;
  items: AttentionItem[];
}

// ── CRM ─────────────────────────────────────────────────────────

export type Recurrence = 'UNICO' | 'MENSAL' | 'TRIMESTRAL' | 'ANUAL';

export interface Interaction {
  id: string;
  client_id: string;
  client_name?: string | null;
  type: 'CONVERSA' | 'PROPOSTA' | 'ORCAMENTO' | 'ALTERACAO_PROJETO' | 'OBSERVACAO' | 'SISTEMA' | 'LIGACAO' | 'VISITA' | 'WHATSAPP';
  content: string;
  created_by: string;
  automatic: boolean;
  created_at: string;
}

export interface Attachment {
  id: string;
  client_id: string;
  project_id?: string | null;
  project_title?: string | null;
  filename: string;
  mime_type: string;
  size: number;
  created_by: string;
  created_at: string;
}

export interface LeadOption {
  id: string;
  name: string;
  active: boolean;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  default_price: number | null;
  unit: string;
  active: boolean;
  created_at: string;
}

export interface NegotiationItem {
  id: string;
  client_id: string;
  product_id?: string | null;
  name: string;
  quantity: number;
  unit_price: number;
  recurrence: Recurrence;
  subtotal: number;
  created_at: string;
}

export interface ClientDetail {
  client: Client;
  projects: Project[];
  events: any[];
  interactions: Interaction[];
  attachments: Attachment[];
  items: NegotiationItem[];
}

export interface ChangelogEntry {
  id: string;
  title: string;
  content: string;
  category: 'GERAL' | 'NOVIDADE' | 'MELHORIA' | 'CORRECAO';
  entry_date: string;
  created_by: string;
  created_at: string;
  /** false/undefined = novidade ainda não lida por este usuário */
  read?: boolean;
}

export interface FunnelColumn {
  id: string;
  column_key: string;
  label: string;
  description?: string | null;
  type: string;
  position: number;
  funnel_id?: string | null;
}

export interface Funnel {
  id: string;
  name: string;
  kind: string;
  is_default: boolean;
  active: boolean;
  created_at: string;
  columns: FunnelColumn[];
}

export interface TicketPhoto {
  id: string;
  ticket_id: string;
  filename: string;
  mime_type: string;
  size: number;
  created_by: string;
  created_at: string;
}

export interface ServiceTicket {
  id: string;
  number: string;
  client_id: string;
  client_name: string | null;
  project_id: string | null;
  project_title: string | null;
  description: string;
  status: string;
  cost: number | null;
  cause: string;
  solution: string;
  in_warranty: boolean | null;
  warranty_until?: string | null;
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  opened_at: string;
  scheduled_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  calendar_event_id: string | null;
  notes: string;
  created_by: string;
  photos: TicketPhoto[];
}

export interface ChecklistItem {
  id: string;
  project_id: string;
  project_title: string | null;
  label: string;
  step_id: string;
  completed: boolean;
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  completed_at: string | null;
  notes: string;
  position: number;
  created_at: string;
}

// ── Pós-venda (Fase 8) ──

export interface SatisfactionSurvey {
  id: string;
  client_id: string;
  client_name: string | null;
  project_id: string | null;
  project_title: string | null;
  ticket_id: string | null;
  ticket_number: string | null;
  score: number | null;
  comment: string;
  sent_at: string;
  answered_at: string | null;
  answered: boolean;
  created_at: string;
}

export interface SatisfactionSummary {
  total: number;
  answered: number;
  response_rate: number;
  average: number;
  distribution: Record<string, number>;
  recent: SatisfactionSurvey[];
}

export interface PosvendaCheckin extends Interaction {
  client_name?: string | null;
}

export interface FollowupEvent {
  id: string;
  title: string;
  description: string | null;
  type: string;
  status: string;
  start_date: string;
  start_time: string | null;
  project_id: string | null;
  client_id: string | null;
}

export interface WhatsappStatus {
  configured: boolean;
  instance: string;
  /** Estado real na Evolution: open | close | connecting | qr | unknown */
  connection: string;
  phone: string;
  webhook?: string;
}

export interface WhatsappConversation {
  id: string;
  instance: string;
  phone: string;
  name: string;
  client_id: string | null;
  client_name: string | null;
  last_message_at: string | null;
  last_body: string;
  last_direction: string;
  unread: number;
  created_at: string;
}

export interface WhatsappMessage {
  id: string;
  conversation_id: string;
  provider_id: string | null;
  direction: 'in' | 'out';
  kind: 'text' | 'image' | 'audio' | 'video' | 'document';
  body: string;
  has_media: boolean;
  media_pending: boolean;
  media_filename: string;
  media_mime: string;
  media_size: number | null;
  status: string;
  created_by: string;
  created_at: string;
}

export interface AccountPlanCategory {
  id: string;
  code: number;
  description: string;
  indicator: 'CREDITO' | 'DEBITO';
  dre_range: string;
  plan_count?: number;
  plans?: AccountPlanItem[];
}

export interface AccountPlanItem {
  id: string;
  code: number;
  structured_code: string;
  description: string;
  label: string;
  category_id: string;
  category_code?: number | null;
  category_description?: string | null;
}

export interface SaleEnvironment {
  id?: string;
  name: string;
}

export interface SaleItem {
  id?: string;
  sale_id?: string;
  product_id?: string | null;
  name: string;
  quantity: number;
  unit_price: number;
  subtotal?: number;
}

export interface SaleInstallment {
  id?: string;
  due_date: string;
  value: number;
  status?: string;
  financial_record_id?: string | null;
}

/** Linha de GET /api/sales (resumo — o financeiro/parcelas vem do detalhe). */
export interface SaleListRow {
  id: string;
  code: string;
  client_id: string;
  client_name: string | null;
  sale_date: string;
  total_value: number;
  seller_name: string | null;
  partner_name: string | null;
  concluded_at: string | null;
  delivery_date: string | null;
}

export interface Sale {
  id: string;
  code: string;
  client_id: string;
  client_name?: string | null;
  seller_id?: string | null;
  seller_name?: string | null;
  partner_id?: string | null;
  partner_name?: string | null;
  lead_source?: string;
  sale_date: string;
  total_value: number;
  down_payment: number;
  installments: number;
  installment_value: number;
  bank_account_id?: string | null;
  bank_account_name?: string | null;
  address?: string;
  delivery_date?: string | null;
  concluded_at?: string | null;
  environments?: SaleEnvironment[];
  items?: SaleItem[];
  installments_list?: SaleInstallment[];
  items_total_diff?: number;
  projects?: string[];
}

export interface TopProduct {
  name: string;
  qty: number;
  receita: number;
  share: number;
}
