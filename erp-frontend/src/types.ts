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

export type ReportArea = 'financial' | 'clients' | 'projects' | 'stock' | 'dre' | 'crm';

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
