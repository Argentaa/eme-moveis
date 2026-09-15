import axios from 'axios';
import { User, Client, Project, FinancialRecord, StockItem, StockMovement, Category, ReportResult, ReportArea, Interaction, Attachment, LeadOption, Product, NegotiationItem, ClientDetail, Recurrence, ChangelogEntry } from '../types';

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
  async getAll(): Promise<Client[]> {
    const response = await api.get('/api/clients');
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

// Attachment Services
export const attachmentService = {
  async list(clientId: string): Promise<Attachment[]> {
    const response = await api.get(`/api/clients/${clientId}/attachments`);
    return response.data;
  },

  async upload(clientId: string, file: File): Promise<Attachment> {
    const formData = new FormData();
    formData.append('file', file);
    // Não setamos Content-Type manualmente: o axios define o boundary do multipart.
    const response = await api.post(`/api/clients/${clientId}/attachments`, formData);
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

  async getAll(): Promise<Project[]> {
    const response = await api.get('/api/projects');
    return response.data;
  },

  async getById(id: string): Promise<Project> {
    const response = await api.get(`/api/projects/${id}`);
    return response.data;
  },

  async create(data: Omit<Project, 'id' | 'created_at' | 'client_name'>): Promise<Project> {
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
};

// Financial Services
export const financialService = {
  async getAll(): Promise<FinancialRecord[]> {
    const response = await api.get('/api/financial');
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

  async getDRE(month?: number, year?: number): Promise<any> {
    const params: Record<string, number> = {};
    if (month) params.month = month;
    if (year) params.year = year;
    const response = await api.get('/api/reports/dre', { params });
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
  async getAll(month?: number, year?: number, clientId?: string): Promise<any[]> {
    const params: Record<string, number | string> = {};
    if (month) params.month = month;
    if (year) params.year = year;
    if (clientId) params.client_id = clientId;
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
