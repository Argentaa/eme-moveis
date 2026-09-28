import axios from 'axios';
import { User, Client, Project, FinancialRecord, StockItem, StockMovement, StockLoss, StockLossKind, StockLossSummary, Category, ReportResult, ReportArea, Interaction, Attachment, LeadOption, Product, NegotiationItem, ClientDetail, Recurrence, CrmReport, ChangelogEntry, Supplier, Vendor, BudgetGoal, BudgetAnalysis, Funnel, FunnelColumn, PurchaseOrder, ServiceTicket, ProjectEnvironment, Worker, Machine, TimeEntry, ProductionIssue, BankAccount, BankBalance, BankOverview, ChecklistItem, Partner, GoalScope, SalesGoal, SalesGoalSummary, AttentionResult, AgingResult, FinancialType, ProductionPending,
  PurchaseQuotation,
  Proposal, CommissionRule, CommissionReport, AppSetting, SatisfactionSurvey, SatisfactionSummary, PosvendaCheckin, FollowupEvent } from '../types';

// Same-origin by default: the frontend server proxies /api to FastAPI.
const API_URL = (import.meta as any).env?.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically inject JWT token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('eme_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;

    if (typeof data?.detail === 'string') {
      return data.detail;
    }

    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((item: any) => item?.msg || item?.message)
        .filter(Boolean)
        .join(' | ') || fallback;
    }

    if (typeof data?.error === 'string') {
      return data.error;
    }

    if (error.code === 'ERR_NETWORK') {
      return 'Não foi possível conectar ao servidor da API.';
    }
  }

  return fallback;
}

// Auth Services
export const authService = {
  async login(username: string, password: string) {
    const response = await api.post('/api/auth/login', { username, password });
    if (response.data.token) {
      localStorage.setItem('eme_token', response.data.token);
      localStorage.setItem('eme_user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  logout() {
    localStorage.removeItem('eme_token');
    localStorage.removeItem('eme_user');
  },

  async me() {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  async getUsers(): Promise<User[]> {
    const response = await api.get('/api/auth/users');
    return response.data;
  },

  async createUser(data: Omit<User, 'id'> & { password?: string }): Promise<User> {
    const response = await api.post('/api/auth/users', data);
    return response.data;
  },

  async updateUserRole(id: string, role: string): Promise<User> {
    const response = await api.put(`/api/auth/users/${id}/role`, { role });
    return response.data;
  },

  async deleteUser(id: string): Promise<any> {
    const response = await api.delete(`/api/auth/users/${id}`);
    return response.data;
  },
};

// Client Services
export const clientService = {
  async getAll(params?: { is_supplier?: string; q?: string }): Promise<Client[]> {
    const response = await api.get('/api/clients', { params });
    return response.data;
  },

  async getById(id: string): Promise<Client> {
    const response = await api.get(`/api/clients/${id}`);
    return response.data;
  },

  async create(data: Omit<Client, 'id' | 'created_at'>): Promise<Client> {
    const response = await api.post('/api/clients', data);
    return response.data;
  },

  async update(id: string, data: Partial<Client>): Promise<Client> {
    const response = await api.put(`/api/clients/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<any> {
    const response = await api.delete(`/api/clients/${id}`);
    return response.data;
  },

  async updateFunnel(id: string, funnel_status: string): Promise<any> {
    const response = await api.put(`/api/clients/${id}`, { funnel_status });
    return response.data;
  },

  // Botao "Concluir venda" do Comercial: marca a venda como concluida (o card
  // sai do funil) e cria o projeto na Producao, numa chamada so.
  async concludeSale(
    id: string,
    data: { title?: string; value?: number; description?: string; steps?: unknown[] } = {}
  ): Promise<Project> {
    const response = await api.post(`/api/clients/${id}/conclude-sale`, data);
    return response.data;
  },

  async getDetail(id: string): Promise<ClientDetail> {
    const response = await api.get(`/api/clients/${id}/detail`);
    return response.data;
  },

  async getInteractions(id: string): Promise<Interaction[]> {
    const response = await api.get(`/api/clients/${id}/interactions`);
    return response.data;
  },

  async createInteraction(id: string, data: { type: string; content: string }): Promise<Interaction> {
    const response = await api.post(`/api/clients/${id}/interactions`, data);
    return response.data;
  },

  async deleteInteraction(interactionId: string): Promise<any> {
    const response = await api.delete(`/api/interactions/${interactionId}`);
    return response.data;
  },
};

// Partner Services
export const partnerService = {
  async list(): Promise<Partner[]> {
    const response = await api.get('/api/partners');
    return response.data;
  },
  async get(id: string): Promise<Partner> {
    const response = await api.get('/api/partners/' + id);
    return response.data;
  },
  async create(data: { name: string; office?: string; phone?: string; email?: string; city?: string; notes?: string; active?: boolean }): Promise<Partner> {
    const response = await api.post('/api/partners', data);
    return response.data;
  },
  async update(id: string, data: Partial<Partner>): Promise<Partner> {
    const response = await api.put('/api/partners/' + id, data);
    return response.data;
  },
  async remove(id: string): Promise<any> {
    const response = await api.delete('/api/partners/' + id);
    return response.data;
  },
};

// Attachment Services
export const systemService = {
  // Limite de upload vigente, vindo do backend. A tela usa isto em vez de um
  // numero escrito na mao, que sai de sincronia quando o limite muda.
  async health(): Promise<{ ok: boolean; max_upload_mb?: number }> {
    const response = await api.get('/api/health');
    return response.data;
  },
};

export const attachmentService = {
  async list(clientId: string): Promise<Attachment[]> {
    const response = await api.get(`/api/clients/${clientId}/attachments`);
    return response.data;
  },

  async upload(clientId: string, file: File): Promise<Attachment> {
    const formData = new FormData();
    formData.append('file', file);
    // A instância axios tem Content-Type 'application/json' por padrão, e o
    // axios converte FormData em JSON quando o content-type é JSON (o arquivo
    // se perde: vira {"file":{}}). Para multipart o header DEVE ser sobrescrito
    // nesta requisição; o browser então define o boundary sozinho.
    const response = await api.post(`/api/clients/${clientId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async download(attachmentId: string): Promise<void> {
    try {
      const response = await api.get(`/api/attachments/${attachmentId}/download`, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = ''; // Nome real vem do servidor (Content-Disposition: download_name).
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      await parseBlobError(err);
    }
  },

  async remove(attachmentId: string): Promise<any> {
    const response = await api.delete(`/api/attachments/${attachmentId}`);
    return response.data;
  },

  async getProjectAttachments(projectId: string): Promise<Attachment[]> {
    const response = await api.get(`/api/projects/${projectId}/attachments`);
    return response.data;
  },

  async uploadProjectAttachment(projectId: string, file: File): Promise<Attachment> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/api/projects/${projectId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

// Lead Option Services
export const leadOptionService = {
  async getSources(): Promise<LeadOption[]> {
    const response = await api.get('/api/lead-sources');
    return response.data;
  },

  async createSource(name: string): Promise<LeadOption> {
    const response = await api.post('/api/lead-sources', { name });
    return response.data;
  },

  async removeSource(id: string): Promise<any> {
    const response = await api.delete(`/api/lead-sources/${id}`);
    return response.data;
  },

  async getCampaigns(): Promise<LeadOption[]> {
    const response = await api.get('/api/campaigns');
    return response.data;
  },

  async createCampaign(name: string): Promise<LeadOption> {
    const response = await api.post('/api/campaigns', { name });
    return response.data;
  },

  async removeCampaign(id: string): Promise<any> {
    const response = await api.delete(`/api/campaigns/${id}`);
    return response.data;
  },
};

// Product Services
export const productService = {
  async list(): Promise<Product[]> {
    const response = await api.get('/api/products');
    return response.data;
  },

  async create(data: { name: string; default_price?: number | null; unit?: string }): Promise<Product> {
    const response = await api.post('/api/products', data);
    return response.data;
  },

  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/products/${id}`);
    return response.data;
  },
};

// Negotiation Item Services
export const itemService = {
  async list(clientId: string): Promise<NegotiationItem[]> {
    const response = await api.get(`/api/clients/${clientId}/items`);
    return response.data;
  },

  async create(
    clientId: string,
    data: { product_id?: string | null; name?: string; quantity?: number; unit_price?: number; recurrence?: Recurrence }
  ): Promise<NegotiationItem> {
    const response = await api.post(`/api/clients/${clientId}/items`, data);
    return response.data;
  },

  async update(id: string, data: Partial<Pick<NegotiationItem, 'name' | 'quantity' | 'unit_price' | 'recurrence'>>): Promise<NegotiationItem> {
    const response = await api.put(`/api/items/${id}`, data);
    return response.data;
  },

  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/items/${id}`);
    return response.data;
  },
};

// Project Services
export const projectService = {
  async getOverdue(): Promise<any[]> {
    const response = await api.get('/api/projects/overdue');
    return response.data;
  },

  // Projetos concluidos — alimenta a aba "Projetos entregues" do Pos-venda.
  // Filtra pela flag explicita no backend, nao pela coluna do funil.
  async getConcluded(): Promise<Project[]> {
    const response = await api.get('/api/projects/concluded');
    return response.data;
  },

  // Botao "Concluir projeto": tira da Producao e poe no Pos-venda.
  async conclude(id: string): Promise<Project> {
    const response = await api.post(`/api/projects/${id}/conclude`);
    return response.data;
  },

  // Desfaz a conclusao: o projeto volta para a Producao.
  async reopen(id: string): Promise<Project> {
    const response = await api.post(`/api/projects/${id}/reopen`);
    return response.data;
  },

  // Garantia (Fase 8): edita os meses; o backend recalcula warranty_until.
  async setWarranty(id: string, warranty_months: number): Promise<Project> {
    const response = await api.patch(`/api/projects/${id}/warranty`, { warranty_months });
    return response.data;
  },

  async getAll(): Promise<Project[]> {
    const response = await api.get('/api/projects');
    return response.data;
  },

  async getById(id: string): Promise<Project> {
    const response = await api.get(`/api/projects/${id}`);
    return response.data;
  },

  async create(data: Partial<Project> & Pick<Project, 'title' | 'client_id' | 'status' | 'value' | 'deadline' | 'steps'>): Promise<Project> {
    const response = await api.post('/api/projects', data);
    return response.data;
  },

  async update(id: string, data: Partial<Project>): Promise<Project> {
    const response = await api.put(`/api/projects/${id}`, data);
    return response.data;
  },

  async updateSteps(id: string, steps: Project['steps']): Promise<Project> {
    const response = await api.put(`/api/projects/${id}/steps`, { steps });
    return response.data;
  },

  async delete(id: string): Promise<any> {
    const response = await api.delete(`/api/projects/${id}`);
    return response.data;
  },

  // ── Checklists por etapa ──
  async getChecklists(projectId: string): Promise<ChecklistItem[]> {
    const response = await api.get('/api/projects/' + projectId + '/checklists');
    return response.data;
  },
  async createChecklist(projectId: string, data: { step_id: string; label: string; notes?: string; assigned_user_id?: string | null; completed?: boolean }): Promise<ChecklistItem> {
    const response = await api.post('/api/projects/' + projectId + '/checklists', data);
    return response.data;
  },
  async updateChecklist(itemId: string, data: Partial<ChecklistItem> & { label?: string; step_id?: string; completed?: boolean; notes?: string; assigned_user_id?: string | null }): Promise<ChecklistItem> {
    const response = await api.put('/api/checklist-items/' + itemId, data);
    return response.data;
  },
  async deleteChecklist(itemId: string): Promise<any> {
    const response = await api.delete('/api/checklist-items/' + itemId);
    return response.data;
  },
};

export const checklistService = {
  getChecklists: (projectId: string): Promise<ChecklistItem[]> => api.get('/api/projects/' + projectId + '/checklists').then(r => r.data),
  createChecklist: (projectId: string, data: { step_id: string; label: string; notes?: string; assigned_user_id?: string | null; completed?: boolean }): Promise<ChecklistItem> => api.post('/api/projects/' + projectId + '/checklists', data).then(r => r.data),
  updateChecklist: (itemId: string, data: any): Promise<ChecklistItem> => api.put('/api/checklist-items/' + itemId, data).then(r => r.data),
  deleteChecklist: (itemId: string): Promise<any> => api.delete('/api/checklist-items/' + itemId).then(r => r.data),
};

// ── Production Services ─────────────────────────────────────────

export const workerService = {
  async getAll(): Promise<Worker[]> {
    const response = await api.get('/api/workers');
    return response.data;
  },
  async create(data: { name: string }): Promise<Worker> {
    const response = await api.post('/api/workers', data);
    return response.data;
  },
  async update(id: string, data: Partial<Worker>): Promise<Worker> {
    const response = await api.put('/api/workers/' + id, data);
    return response.data;
  },
  async remove(id: string): Promise<any> {
    const response = await api.delete('/api/workers/' + id);
    return response.data;
  },
};

export const machineService = {
  async getAll(): Promise<Machine[]> {
    const response = await api.get('/api/machines');
    return response.data;
  },
  async create(data: { name: string }): Promise<Machine> {
    const response = await api.post('/api/machines', data);
    return response.data;
  },
  async update(id: string, data: Partial<Machine>): Promise<Machine> {
    const response = await api.put('/api/machines/' + id, data);
    return response.data;
  },
  async remove(id: string): Promise<any> {
    const response = await api.delete('/api/machines/' + id);
    return response.data;
  },
};

export const productionService = {
  /** Pendencias de producao de todos os projetos (ocorrencias + checklist). */
  async getPending(params?: { from?: string; to?: string }): Promise<ProductionPending> {
    const response = await api.get('/api/production/pending', { params });
    return response.data;
  },
  async getEnvironments(projectId: string): Promise<ProjectEnvironment[]> {
    const response = await api.get('/api/projects/' + projectId + '/environments');
    return response.data;
  },
  async createEnvironment(projectId: string, data: any): Promise<ProjectEnvironment> {
    const response = await api.post('/api/projects/' + projectId + '/environments', data);
    return response.data;
  },
  async updateEnvironment(envId: string, data: any): Promise<ProjectEnvironment> {
    const response = await api.put('/api/environments/' + envId, data);
    return response.data;
  },
  async deleteEnvironment(envId: string): Promise<any> {
    const response = await api.delete('/api/environments/' + envId);
    return response.data;
  },
  async getTime(projectId: string): Promise<TimeEntry[]> {
    const response = await api.get('/api/projects/' + projectId + '/time');
    return response.data;
  },
  async createTime(projectId: string, data: any): Promise<TimeEntry> {
    const response = await api.post('/api/projects/' + projectId + '/time', data);
    return response.data;
  },
  async updateTime(entryId: string, data: any): Promise<TimeEntry> {
    const response = await api.put('/api/time-entries/' + entryId, data);
    return response.data;
  },
  async deleteTime(entryId: string): Promise<any> {
    const response = await api.delete('/api/time-entries/' + entryId);
    return response.data;
  },
  async getIssues(projectId: string): Promise<ProductionIssue[]> {
    const response = await api.get('/api/projects/' + projectId + '/issues');
    return response.data;
  },
  async createIssue(projectId: string, data: any): Promise<ProductionIssue> {
    const response = await api.post('/api/projects/' + projectId + '/issues', data);
    return response.data;
  },
  async updateIssue(issueId: string, data: any): Promise<ProductionIssue> {
    const response = await api.put('/api/issues/' + issueId, data);
    return response.data;
  },
  async deleteIssue(issueId: string): Promise<any> {
    const response = await api.delete('/api/issues/' + issueId);
    return response.data;
  },
};

// Financial Services
export const bankAccountService = {
  list: (): Promise<BankAccount[]> => api.get('/api/bank-accounts').then(r => r.data),
  get: (id: string): Promise<BankAccount> => api.get('/api/bank-accounts/' + id).then(r => r.data),
  create: (data: any): Promise<BankAccount> => api.post('/api/bank-accounts', data).then(r => r.data),
  update: (id: string, data: any): Promise<BankAccount> => api.put('/api/bank-accounts/' + id, data).then(r => r.data),
  remove: (id: string): Promise<any> => api.delete('/api/bank-accounts/' + id).then(r => r.data),
  balance: (id: string): Promise<BankBalance> => api.get('/api/bank-accounts/' + id + '/balance').then(r => r.data),
  overview: (): Promise<BankOverview> => api.get('/api/bank-accounts/overview').then(r => r.data),
};

export const financialService = {
  async getAll(params?: {
    type?: FinancialType;
    status?: 'PAGO' | 'PENDENTE';
    due_from?: string;
    due_to?: string;
    overdue?: string;
  }): Promise<FinancialRecord[]> {
    const response = await api.get('/api/financial', { params });
    return response.data;
  },

  /** Aging das contas em aberto (vencidas / 0-7 / 8-30 / +30). */
  async aging(type: FinancialType): Promise<AgingResult> {
    const response = await api.get('/api/financial/aging', { params: { type } });
    return response.data;
  },

  async create(data: Omit<FinancialRecord, 'id'>): Promise<FinancialRecord> {
    const response = await api.post('/api/financial', data);
    return response.data;
  },

  async update(id: string, data: Partial<FinancialRecord>): Promise<FinancialRecord> {
    const response = await api.put(`/api/financial/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<any> {
    const response = await api.delete(`/api/financial/${id}`);
    return response.data;
  },

  async downloadReceipt(id: string, format: 'pdf' | 'docx'): Promise<void> {
    try {
      const response = await api.get(`/api/financial/${id}/receipt`, {
        params: { format },
        responseType: 'blob',
      });

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `recibo-${id.substring(0, 8)}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      // Quando responseType é 'blob', o corpo de erro do backend também vem
      // como Blob. Convertemos de volta para JSON para que getApiErrorMessage
      // consiga ler a mensagem normalmente.
      if (axios.isAxiosError(err) && err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          err.response.data = JSON.parse(text);
        } catch {
          // Se não for JSON, mantemos o erro original.
        }
      }
      throw err;
    }
  },

  async getUpcoming(days: number = 7): Promise<any> {
    const response = await api.get('/api/financial/upcoming', { params: { days } });
    return response.data;
  },

  async getOverdue(): Promise<any> {
    const response = await api.get('/api/financial/overdue');
    return response.data;
  },
};

// Stock Services
export const stockService = {
  async getAll(): Promise<StockItem[]> {
    const response = await api.get('/api/stock');
    return response.data;
  },

  async create(data: Omit<StockItem, 'id' | 'category_name'>): Promise<StockItem> {
    const response = await api.post('/api/stock', data);
    return response.data;
  },

  async update(id: string, data: Partial<StockItem>): Promise<StockItem> {
    const response = await api.put(`/api/stock/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<any> {
    const response = await api.delete(`/api/stock/${id}`);
    return response.data;
  },

  async getMovements(): Promise<StockMovement[]> {
    const response = await api.get('/api/stock/movements/history');
    return response.data;
  },

  async createMovement(data: { item_id: string; type: 'ENTRADA' | 'SAIDA'; quantity: number; reason: string }): Promise<StockMovement> {
    const response = await api.post('/api/stock/movements', data);
    return response.data;
  },

  async getLosses(params?: { kind?: StockLossKind; date_from?: string; date_to?: string }): Promise<StockLoss[]> {
    const response = await api.get('/api/stock/losses', { params });
    return response.data;
  },

  async createLoss(data: {
    stock_item_id: string; quantity: number; kind: StockLossKind;
    reason?: string; cost?: number | null; loss_date?: string;
  }): Promise<StockLoss> {
    const response = await api.post('/api/stock/losses', data);
    return response.data;
  },

  async getLossSummary(params?: { kind?: StockLossKind; date_from?: string; date_to?: string }): Promise<StockLossSummary> {
    const response = await api.get('/api/stock/losses/summary', { params });
    return response.data;
  },

  async getCategories(categoryType?: 'STOCK' | 'FINANCIAL'): Promise<Category[]> {
    const response = await api.get('/api/stock/categories/all', {
      params: categoryType ? { category_type: categoryType } : {},
    });
    return response.data;
  },

  async createCategory(data: { name: string; description?: string; category_type?: 'STOCK' | 'FINANCIAL' }): Promise<Category> {
    const response = await api.post('/api/stock/categories', data);
    return response.data;
  },

  async updateCategory(id: string, data: { name?: string; description?: string }): Promise<Category> {
    const response = await api.put(`/api/stock/categories/${id}`, data);
    return response.data;
  },

  async deleteCategory(id: string): Promise<any> {
    const response = await api.delete(`/api/stock/categories/${id}`);
    return response.data;
  },
};

// Report Services

async function parseBlobError(err: unknown): Promise<never> {
  if (axios.isAxiosError(err) && err.response?.data instanceof Blob) {
    try {
      const text = await err.response.data.text();
      err.response.data = JSON.parse(text);
    } catch {
      // Se não for JSON, mantemos o erro original.
    }
  }
  throw err;
}

export const reportService = {
  async getReport(area: ReportArea, filters: Record<string, string | boolean | undefined>): Promise<ReportResult> {
    const params: Record<string, string> = {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params[key] = String(value);
      }
    });
    const response = await api.get(`/api/reports/${area}`, { params });
    return response.data;
  },

  async exportReport(
    area: ReportArea,
    format: 'pdf' | 'xlsx',
    filters: Record<string, string | boolean | undefined>
  ): Promise<void> {
    const params: Record<string, string> = { export: format };
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params[key] = String(value);
      }
    });

    try {
      const response = await api.get(`/api/reports/${area}/export`, {
        params,
        responseType: 'blob',
      });

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `relatorio-${area}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      await parseBlobError(err);
    }
  },

  async getCRMReport(dateFrom?: string, dateTo?: string): Promise<any> {
    const params: Record<string, string> = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    const response = await api.get('/api/reports/crm', { params });
    return response.data;
  },
};

// Ticket Services
export const ticketService = {
  async list(params?: { status?: string; client_id?: string }): Promise<ServiceTicket[]> {
    const response = await api.get('/api/tickets', { params });
    return response.data;
  },
  async get(id: string): Promise<ServiceTicket> {
    const response = await api.get('/api/tickets/' + id);
    return response.data;
  },
  async create(data: any): Promise<ServiceTicket> {
    const response = await api.post('/api/tickets', data);
    return response.data;
  },
  async update(id: string, data: any): Promise<ServiceTicket> {
    const response = await api.put('/api/tickets/' + id, data);
    return response.data;
  },
  async remove(id: string): Promise<any> {
    const response = await api.delete('/api/tickets/' + id);
    return response.data;
  },
  async uploadPhoto(ticketId: string, file: File): Promise<any> {
    const fd = new FormData();
    fd.append('file', file);
    const response = await api.post('/api/tickets/' + ticketId + '/photos', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  async deletePhoto(photoId: string): Promise<any> {
    const response = await api.delete('/api/tickets/photos/' + photoId);
    return response.data;
  },
  async downloadPhoto(photoId: string): Promise<any> {
    const response = await api.get('/api/tickets/photos/' + photoId + '/download', { responseType: 'blob' });
    return response;
  },
};

// Supplier Services
export const supplierService = {
  async getAll(): Promise<Supplier[]> {
    const response = await api.get('/api/suppliers');
    return response.data;
  },

  async create(data: { name: string; cnpj?: string; contact?: string; phone?: string; email?: string }): Promise<Supplier> {
    const response = await api.post('/api/suppliers', data);
    return response.data;
  },

  async update(id: string, data: Partial<Supplier>): Promise<Supplier> {
    const response = await api.put(`/api/suppliers/${id}`, data);
    return response.data;
  },

  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/suppliers/${id}`);
    return response.data;
  },
};

// Vendor Services — unifica fornecedores legados + clientes marcados como
// fornecedor, para uso nos selects de Compras/Financeiro.
export const vendorService = {
  async list(): Promise<Vendor[]> {
    const response = await api.get('/api/vendors');
    return response.data;
  },
};

// Purchase Services
export const purchaseService = {
  async list(params?: { status?: string; supplier_id?: string }): Promise<PurchaseOrder[]> {
    const response = await api.get('/api/purchases', { params });
    return response.data;
  },

  // ── cotacoes (comparativo entre fornecedores) ──────────────────
  async listQuotations(orderId: string): Promise<PurchaseQuotation[]> {
    const response = await api.get(`/api/purchases/${orderId}/quotations`);
    return response.data;
  },
  async createQuotation(orderId: string, data: any): Promise<PurchaseQuotation> {
    const response = await api.post(`/api/purchases/${orderId}/quotations`, data);
    return response.data;
  },
  async updateQuotation(quotationId: string, data: any): Promise<PurchaseQuotation> {
    const response = await api.put(`/api/quotations/${quotationId}`, data);
    return response.data;
  },
  async deleteQuotation(quotationId: string): Promise<any> {
    const response = await api.delete(`/api/quotations/${quotationId}`);
    return response.data;
  },
  /** Marca a vencedora: leva os precos dela para o pedido e o poe em APROVADA. */
  async approveQuotation(orderId: string, quotationId: string): Promise<PurchaseOrder> {
    const response = await api.post(`/api/purchases/${orderId}/quotations/${quotationId}/approve`);
    return response.data;
  },

  async get(id: string): Promise<PurchaseOrder> {
    const response = await api.get(`/api/purchases/${id}`);
    return response.data;
  },

  async create(data: any): Promise<PurchaseOrder> {
    const response = await api.post('/api/purchases', data);
    return response.data;
  },

  async update(id: string, data: any): Promise<PurchaseOrder> {
    const response = await api.put(`/api/purchases/${id}`, data);
    return response.data;
  },

  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/purchases/${id}`);
    return response.data;
  },

  async receive(id: string): Promise<PurchaseOrder> {
    const response = await api.post(`/api/purchases/${id}/receive`);
    return response.data;
  },
};

// Budget Services
export const budgetService = {
  async getGoals(year?: number, month?: number): Promise<BudgetGoal[]> {
    const params: Record<string, string> = {};
    if (year) params.year = String(year);
    if (month) params.month = String(month);
    const response = await api.get('/api/budget/goals', { params });
    return response.data;
  },

  async createGoal(data: { year: number; month?: number | null; category: string; target_value: number }): Promise<BudgetGoal> {
    const response = await api.post('/api/budget/goals', data);
    return response.data;
  },

  async updateGoal(id: string, data: Partial<BudgetGoal>): Promise<BudgetGoal> {
    const response = await api.put(`/api/budget/goals/${id}`, data);
    return response.data;
  },

  async removeGoal(id: string): Promise<any> {
    const response = await api.delete(`/api/budget/goals/${id}`);
    return response.data;
  },

  async getAnalysis(year: number, month?: number | ''): Promise<BudgetAnalysis> {
    const params: Record<string, string> = { year: String(year) };
    if (month) params.month = String(month);
    const response = await api.get('/api/budget/analysis', { params });
    return response.data;
  },
};

// Funnel Columns Service
export const funnelService = {
  async getAll(type: 'CRM' | 'PROJECTS' = 'CRM'): Promise<any[]> {
    const response = await api.get('/api/funnel-columns', { params: { type } });
    return response.data;
  },

  async update(columnKey: string, data: { label: string; description?: string }, type: 'CRM' | 'PROJECTS' = 'CRM'): Promise<any> {
    const response = await api.put(`/api/funnel-columns/${columnKey}`, data, { params: { type } });
    return response.data;
  },

  async getFunnels(kind?: string): Promise<Funnel[]> {
    const response = await api.get('/api/funnels', { params: kind ? { kind } : {} });
    return response.data;
  },

  async createFunnel(data: { name: string; kind: string }): Promise<Funnel> {
    const response = await api.post('/api/funnels', data);
    return response.data;
  },

  async updateFunnel(id: string, data: { name?: string; active?: boolean }): Promise<Funnel> {
    const response = await api.put(`/api/funnels/${id}`, data);
    return response.data;
  },

  async removeFunnel(id: string): Promise<any> {
    const response = await api.delete(`/api/funnels/${id}`);
    return response.data;
  },

  async addFunnelColumn(funnelId: string, data: { label: string }): Promise<FunnelColumn> {
    const response = await api.post(`/api/funnels/${funnelId}/columns`, data);
    return response.data;
  },

  async updateFunnelColumn(funnelId: string, columnKey: string, data: { label?: string; description?: string; position?: number }): Promise<FunnelColumn> {
    const response = await api.put(`/api/funnels/${funnelId}/columns/${columnKey}`, data);
    return response.data;
  },

  async removeFunnelColumn(funnelId: string, columnKey: string): Promise<any> {
    const response = await api.delete(`/api/funnels/${funnelId}/columns/${columnKey}`);
    return response.data;
  },
};

// Recurring Financial Services
export const recurringService = {
  async createExtended(data: any): Promise<any> {
    const response = await api.post('/api/financial/recurring', data);
    return response.data;
  },

  async getAll(): Promise<any[]> {
    const response = await api.get('/api/financial/recurring');
    return response.data;
  },

  async deactivate(id: string): Promise<any> {
    const response = await api.delete(`/api/financial/recurring/${id}`);
    return response.data;
  },

  async processDue(): Promise<any> {
    const response = await api.post('/api/financial/recurring/process-due');
    return response.data;
  },
};

// Calendar Services
export const calendarService = {
  async getAll(month?: number, year?: number, clientId?: string, eventType?: string): Promise<any[]> {
    const params: Record<string, number | string> = {};
    if (month) params.month = month;
    if (year) params.year = year;
    if (clientId) params.client_id = clientId;
    if (eventType) params.type = eventType;
    const response = await api.get('/api/calendar', { params });
    return response.data;
  },

  async getToday(): Promise<any[]> {
    const response = await api.get('/api/calendar/today');
    return response.data;
  },

  async getWeek(): Promise<any[]> {
    const response = await api.get('/api/calendar/week');
    return response.data;
  },

  async create(data: any): Promise<any> {
    const response = await api.post('/api/calendar', data);
    return response.data;
  },

  async update(id: string, data: any): Promise<any> {
    const response = await api.put(`/api/calendar/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<any> {
    const response = await api.delete(`/api/calendar/${id}`);
    return response.data;
  },

  async getNotifications(unreadOnly?: boolean): Promise<any[]> {
    const response = await api.get('/api/calendar/notifications', {
      params: unreadOnly ? { unread_only: true } : {},
    });
    return response.data;
  },

  async countUnread(): Promise<{ unread: number }> {
    const response = await api.get('/api/calendar/notifications/count');
    return response.data;
  },

  async markRead(id: string): Promise<any> {
    const response = await api.put(`/api/calendar/notifications/${id}/read`);
    return response.data;
  },

  async markAllRead(): Promise<any> {
    const response = await api.put('/api/calendar/notifications/read-all');
    return response.data;
  },

  async generateAlerts(): Promise<any> {
    const response = await api.post('/api/calendar/notifications/generate-alerts');
    return response.data;
  },
};

// Changelog Services
export const changelogService = {
  async list(): Promise<ChangelogEntry[]> {
    const response = await api.get('/api/changelog');
    return response.data;
  },

  /** Quantas novidades este usuário ainda não leu (badge do menu). */
  async unreadCount(): Promise<{ unread: number; count: number }> {
    const response = await api.get('/api/changelog/unread-count');
    return response.data;
  },

  async markAllRead(): Promise<{ ok: boolean; marked: number; unread: number; count: number }> {
    const response = await api.post('/api/changelog/read-all');
    return response.data;
  },

  async markRead(id: string): Promise<{ ok: boolean; unread: number; count: number }> {
    const response = await api.put(`/api/changelog/${id}/read`);
    return response.data;
  },

  async create(data: { title: string; content?: string; category?: string; entry_date?: string }): Promise<ChangelogEntry> {
    const response = await api.post('/api/changelog', data);
    return response.data;
  },

  async update(id: string, data: { title?: string; content?: string; category?: string; entry_date?: string }): Promise<ChangelogEntry> {
    const response = await api.put(`/api/changelog/${id}`, data);
    return response.data;
  },

  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/changelog/${id}`);
    return response.data;
  },
};

// ── Painel inicial: metas comerciais e pendências ────────────────

export const goalService = {
  async list(filters: { year?: number; month?: number; scope?: GoalScope } = {}): Promise<SalesGoal[]> {
    const params: Record<string, string> = {};
    if (filters.year) params.year = String(filters.year);
    if (filters.month) params.month = String(filters.month);
    if (filters.scope) params.scope = filters.scope;
    const response = await api.get('/api/goals', { params });
    return response.data;
  },

  /** Meta x realizado do período (percentual, restante e base de cálculo). */
  async summary(filters: { year?: number; month?: number; scope?: GoalScope } = {}): Promise<SalesGoalSummary> {
    const params: Record<string, string> = {};
    if (filters.year) params.year = String(filters.year);
    if (filters.month) params.month = String(filters.month);
    if (filters.scope) params.scope = filters.scope;
    const response = await api.get('/api/goals/summary', { params });
    return response.data;
  },

  async create(data: any): Promise<SalesGoal> {
    const response = await api.post('/api/goals', data);
    return response.data;
  },

  async update(id: string, data: any): Promise<SalesGoal> {
    const response = await api.put(`/api/goals/${id}`, data);
    return response.data;
  },

  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/goals/${id}`);
    return response.data;
  },
};

export const proposalService = {
  async list(params: { status?: string; client_id?: string } = {}): Promise<Proposal[]> {
    const response = await api.get('/api/proposals', { params });
    return response.data;
  },
  async get(id: string): Promise<Proposal> {
    const response = await api.get(`/api/proposals/${id}`);
    return response.data;
  },
  async create(data: any): Promise<Proposal> {
    const response = await api.post('/api/proposals', data);
    return response.data;
  },
  async update(id: string, data: any): Promise<Proposal> {
    const response = await api.put(`/api/proposals/${id}`, data);
    return response.data;
  },
  async remove(id: string): Promise<any> {
    const response = await api.delete(`/api/proposals/${id}`);
    return response.data;
  },
  /** URL do PDF (aberta em nova aba; o token vai no header, então baixamos via blob). */
  async downloadPdf(id: string, numero: string): Promise<void> {
    const response = await api.get(`/api/proposals/${id}/pdf`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${numero}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
  /** Envia pelo WhatsApp. Sem Evolution configurada volta 200 com fallback_wa_me. */
  async sendWhatsapp(id: string): Promise<{
    sent: boolean; channel: string | null; detail: string;
    fallback_wa_me: string | null; proposal: Proposal;
  }> {
    const response = await api.post(`/api/proposals/${id}/send-whatsapp`);
    return response.data;
  },
};

export const commissionService = {
  async report(params: { year?: number; month?: number } = {}): Promise<CommissionReport> {
    const q: Record<string, string> = {};
    if (params.year) q.year = String(params.year);
    if (params.month) q.month = String(params.month);
    const response = await api.get('/api/commissions', { params: q });
    return response.data;
  },
  async listRules(): Promise<CommissionRule[]> {
    const response = await api.get('/api/commission-rules');
    return response.data;
  },
  /** Quem pode receber comissao (so id e nome) para o seletor da regra. */
  async ruleOptions(): Promise<{ sellers: { id: string; name: string }[]; partners: { id: string; name: string }[] }> {
    const response = await api.get('/api/commission-rules/options');
    return response.data;
  },
  async createRule(data: any): Promise<CommissionRule> {
    const response = await api.post('/api/commission-rules', data);
    return response.data;
  },
  async updateRule(id: string, data: any): Promise<CommissionRule> {
    const response = await api.put(`/api/commission-rules/${id}`, data);
    return response.data;
  },
  async removeRule(id: string): Promise<any> {
    const response = await api.delete(`/api/commission-rules/${id}`);
    return response.data;
  },
};

export const settingsService = {
  async list(): Promise<AppSetting[]> {
    const response = await api.get('/api/settings');
    return response.data;
  },
  async update(data: Record<string, string>): Promise<{ saved: string[] }> {
    const response = await api.put('/api/settings', data);
    return response.data;
  },
};

export const dashboardService = {
  /** Pendencias agregadas do painel inicial. */
  async attention(): Promise<AttentionResult> {
    const response = await api.get('/api/dashboard/attention');
    return response.data;
  },

  /**
   * Relatorio comercial. Endpoint com formato proprio (nao segue
   * {summary, columns, rows}) — por isso tem metodo e tipo dedicados.
   */
  async crmReport(filters: { date_from?: string; date_to?: string } = {}): Promise<CrmReport> {
    const params: Record<string, string> = {};
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    const response = await api.get('/api/reports/crm', { params });
    return response.data;
  },
};

// ── Pós-venda (Fase 8) ──

export const satisfactionService = {
  async list(): Promise<SatisfactionSurvey[]> {
    const response = await api.get('/api/satisfaction');
    return response.data;
  },
  async create(data: { client_id: string; project_id?: string | null; ticket_id?: string | null; score?: number | null; comment?: string }): Promise<SatisfactionSurvey> {
    const response = await api.post('/api/satisfaction', data);
    return response.data;
  },
  async answer(id: string, data: { score: number; comment?: string }): Promise<SatisfactionSurvey> {
    const response = await api.post(`/api/satisfaction/${id}/answer`, data);
    return response.data;
  },
  async summary(): Promise<SatisfactionSummary> {
    const response = await api.get('/api/satisfaction/summary');
    return response.data;
  },
  // Envia por WhatsApp (Evolution) com fallback wa.me — mesmo contrato da proposta.
  async sendWhatsapp(id: string): Promise<{ sent: boolean; channel: string | null; detail: string; fallback_wa_me: string | null; survey: SatisfactionSurvey }> {
    const response = await api.post(`/api/satisfaction/${id}/send-whatsapp`);
    return response.data;
  },
};

export const posvendaService = {
  async listCheckins(): Promise<PosvendaCheckin[]> {
    const response = await api.get('/api/posvenda/checkins');
    return response.data;
  },
  async createCheckin(data: { client_id: string; type: string; content: string; project_id?: string | null }): Promise<PosvendaCheckin> {
    const response = await api.post('/api/posvenda/checkins', data);
    return response.data;
  },
  async listFollowups(): Promise<FollowupEvent[]> {
    const response = await api.get('/api/calendar', { params: { type: 'POS_VENDA' } });
    return response.data;
  },
  async generateFollowups(project_id?: string): Promise<{ created: number; projects: number; days: number[] }> {
    const response = await api.post('/api/posvenda/followups/generate', project_id ? { project_id } : {});
    return response.data;
  },
};
