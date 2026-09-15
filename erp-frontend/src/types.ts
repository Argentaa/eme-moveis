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

export interface Client {
  id: string;
  name: string;
  email: string;
  phone: string;
  cpf_cnpj: string;
  address: string;
  created_at: string;
  funnel_status: FunnelStatus;
  lost_reason?: string | null;
  estimated_value?: number | null;
  lead_source?: string | null;
  campaign?: string | null;
  negotiation_value?: number | null;
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
}

export type FinancialType = 'ENTRADA' | 'SAIDA';

export interface FinancialRecord {
  id: string;
  description: string;
  type: FinancialType;
  category: string;
  amount: number;
  date: string;
  due_date: string;
  project_id?: string;
  status: 'PAGO' | 'PENDENTE';
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
  type: 'ENTRADA' | 'SAIDA';
  quantity: number;
  reason: string;
  created_by: string;
  date: string;
}

// ── Relatórios ──────────────────────────────────────────────────

export type ReportArea = 'financial' | 'clients' | 'projects' | 'stock' | 'dre' | 'crm' | 'lead-sources';

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
}

// ── CRM ─────────────────────────────────────────────────────────

export type Recurrence = 'UNICO' | 'MENSAL' | 'TRIMESTRAL' | 'ANUAL';

export interface Interaction {
  id: string;
  client_id: string;
  type: 'CONVERSA' | 'PROPOSTA' | 'ORCAMENTO' | 'ALTERACAO_PROJETO' | 'OBSERVACAO' | 'SISTEMA';
  content: string;
  created_by: string;
  automatic: boolean;
  created_at: string;
}

export interface Attachment {
  id: string;
  client_id: string;
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
}
