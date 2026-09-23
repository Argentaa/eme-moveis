import React, { useEffect, useMemo, useState } from 'react';
import {
  Wrench,
  Plus,
  Trash2,
  Edit3,
  Search,
  Eye,
  X,
  RefreshCw,
  ShieldAlert,
  Calendar,
  DollarSign,
  Check,
  Download,
  Upload,
  Image as ImageIcon,
} from 'lucide-react';
import { ticketService, clientService, projectService, getApiErrorMessage, api } from '../services/api';
import { ServiceTicket, Client, Project, User as UserType } from '../types';

import ModuleTabs, { ModuleTab, ActiveTabPlaceholder, useModuleTab } from './ModuleTabs';

/** Abas do módulo Pós-venda, conforme a spec do cliente (17/09). */
const TICKETS_TABS: ModuleTab[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'schedule', label: 'Agenda de pós-venda' },
  { id: 'checkins', label: 'Check-ins' },
  { id: 'satisfaction', label: 'Pesquisa de satisfação' },
  { id: 'tickets', label: 'Solicitações/Ocorrências', ready: true },
  { id: 'warranties', label: 'Garantias' },
  { id: 'pending', label: 'Pendências' },
];

interface TicketsViewProps {
  userRole: string;
}

const STATUS_OPTIONS = ['ABERTO', 'EM_ANALISE', 'AGENDADO', 'EM_ATENDIMENTO', 'RESOLVIDO', 'ENCERRADO'] as const;
const FILTER_OPTIONS = ['TODOS', ...STATUS_OPTIONS] as const;

function getStatusBadge(status: string): string {
  switch (status) {
    case 'ABERTO':
      return 'bg-zinc-800 text-zinc-300 border-zinc-700';
    case 'EM_ANALISE':
      return 'bg-amber-950/40 text-amber-400 border-amber-900/40';
    case 'AGENDADO':
      return 'bg-sky-950/40 text-sky-400 border-sky-900/40';
    case 'EM_ATENDIMENTO':
      return 'bg-violet-950/40 text-violet-400 border-violet-900/40';
    case 'RESOLVIDO':
      return 'bg-emerald-950/40 text-emerald-400 border-emerald-900/40';
    case 'ENCERRADO':
      return 'bg-zinc-800 text-zinc-500 border-zinc-800';
    default:
      return 'bg-zinc-800 text-zinc-300 border-zinc-700';
  }
}

function formatBRL(value: number | null | undefined): string {
  if (value == null) return '-';
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleDateString('pt-BR');
  } catch {
    return value;
  }
}

function formatDateTime(value: string | null): string {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString('pt-BR');
  } catch {
    return value;
  }
}

type FormData = {
  client_id: string;
  project_id: string;
  description: string;
  status: string;
  cost: string;
  cause: string;
  solution: string;
  in_warranty: string;
  assigned_user_id: string;
  scheduled_at: string;
  notes: string;
};

const emptyFormData = (): FormData => ({
  client_id: '',
  project_id: '',
  description: '',
  status: 'ABERTO',
  cost: '',
  cause: '',
  solution: '',
  in_warranty: '',
  assigned_user_id: '',
  scheduled_at: '',
  notes: '',
});

export default function TicketsView({ userRole }: TicketsViewProps) {
  const allowedRoles = ['ADMIN', 'GERENTE'];
  const canManage = allowedRoles.includes(userRole);

  const [activeTab, setActiveTab] = useModuleTab('tickets', TICKETS_TABS, 'tickets');
  const [tickets, setTickets] = useState<ServiceTicket[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [users, setUsers] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);

  const [filterStatus, setFilterStatus] = useState<string>('TODOS');
  const [searchQuery, setSearchQuery] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [detailTicket, setDetailTicket] = useState<ServiceTicket | null>(null);
  const [formData, setFormData] = useState<FormData>(emptyFormData());
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // detail photo upload
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [t, c, p, u] = await Promise.all([
        ticketService.list(),
        clientService.getAll().catch(() => [] as Client[]),
        projectService.getAll().catch(() => [] as Project[]),
        api.get('/api/auth/users').then((r) => r.data as UserType[]).catch(() => [] as UserType[]),
      ]);
      setTickets(t);
      setClients(c);
      setProjects(p);
      setUsers(u);
    } catch (err) {
      console.error('Erro ao carregar chamados:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      const matchesStatus = filterStatus === 'TODOS' || t.status === filterStatus;
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        t.number.toLowerCase().includes(q) ||
        (t.client_name && t.client_name.toLowerCase().includes(q)) ||
        t.description.toLowerCase().includes(q) ||
        t.cause.toLowerCase().includes(q);
      return matchesStatus && matchesSearch;
    });
  }, [tickets, filterStatus, searchQuery]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setFormData(emptyFormData());
    setSubmitError('');
    setIsModalOpen(true);
    setDetailTicket(null);
  };

  const handleOpenEdit = (ticket: ServiceTicket) => {
    setEditingId(ticket.id);
    setFormData({
      client_id: ticket.client_id || '',
      project_id: ticket.project_id || '',
      description: ticket.description || '',
      status: ticket.status,
      cost: ticket.cost != null ? String(ticket.cost) : '',
      cause: ticket.cause || '',
      solution: ticket.solution || '',
      in_warranty: ticket.in_warranty == null ? '' : ticket.in_warranty ? 'true' : 'false',
      assigned_user_id: ticket.assigned_user_id || '',
      scheduled_at: ticket.scheduled_at ? ticket.scheduled_at.substring(0, 10) : '',
      notes: ticket.notes || '',
    });
    setSubmitError('');
    setIsModalOpen(true);
    setDetailTicket(null);
  };

  const handleOpenDetail = async (ticket: ServiceTicket) => {
    try {
      const full = await ticketService.get(ticket.id);
      setDetailTicket(full);
    } catch {
      setDetailTicket(ticket);
    }
  };

  const handleDelete = async (ticket: ServiceTicket) => {
    if (!['ABERTO', 'EM_ANALISE'].includes(ticket.status)) {
      alert('Apenas chamados ABERTO ou EM_ANALISE podem ser excluidos.');
      return;
    }
    if (!confirm(`Excluir o chamado ${ticket.number}?`)) return;
    try {
      await ticketService.remove(ticket.id);
      await loadData();
      if (detailTicket && detailTicket.id === ticket.id) setDetailTicket(null);
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir chamado.'));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    if (!formData.client_id) {
      setSubmitError('Cliente e obrigatorio.');
      return;
    }
    if (!formData.description.trim()) {
      setSubmitError('Descricao e obrigatoria.');
      return;
    }
    const payload: any = {
      client_id: formData.client_id,
      project_id: formData.project_id || null,
      description: formData.description.trim(),
      status: formData.status,
      cause: formData.cause || '',
      solution: formData.solution || '',
      notes: formData.notes || '',
      assigned_user_id: formData.assigned_user_id || null,
      scheduled_at: formData.scheduled_at || null,
    };
    if (formData.cost !== '') {
      const n = Number(formData.cost);
      if (!isNaN(n)) payload.cost = n;
    } else {
      payload.cost = null;
    }
    if (formData.in_warranty === 'true') payload.in_warranty = true;
    else if (formData.in_warranty === 'false') payload.in_warranty = false;
    else payload.in_warranty = null;

    setSubmitting(true);
    try {
      if (editingId) {
        await ticketService.update(editingId, payload);
      } else {
        await ticketService.create(payload);
      }
      setIsModalOpen(false);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setSubmitError(getApiErrorMessage(err, editingId ? 'Erro ao atualizar chamado.' : 'Erro ao criar chamado.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleUploadPhoto = async () => {
    if (!detailTicket || !selectedFile) return;
    setUploading(true);
    try {
      await ticketService.uploadPhoto(detailTicket.id, selectedFile);
      setSelectedFile(null);
      const updated = await ticketService.get(detailTicket.id);
      setDetailTicket(updated);
      await loadData();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao enviar foto.'));
    } finally {
      setUploading(false);
    }
  };

  const handleDeletePhoto = async (photoId: string) => {
    if (!confirm('Remover esta foto?')) return;
    try {
      await ticketService.deletePhoto(photoId);
      if (detailTicket) {
        const updated = await ticketService.get(detailTicket.id);
        setDetailTicket(updated);
        await loadData();
      }
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao remover foto.'));
    }
  };

  const handleDownloadPhoto = async (photoId: string, filename: string) => {
    try {
      const res = await ticketService.downloadPhoto(photoId);
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'foto';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      // blob error parsing
      if (err && typeof err === 'object' && 'response' in (err as any)) {
        const r = (err as any).response;
        if (r?.data instanceof Blob) {
          try {
            const text = await r.data.text();
            const j = JSON.parse(text);
            alert(j.detail || j.error || 'Erro ao baixar foto.');
            return;
          } catch { /* fallback */ }
        }
      }
      alert(getApiErrorMessage(err, 'Erro ao baixar foto.'));
    }
  };

  // projects filtered by selected client for form
  const filteredProjects = useMemo(() => {
    if (!formData.client_id) return projects;
    return projects.filter((p) => p.client_id === formData.client_id);
  }, [projects, formData.client_id]);

  if (!canManage) {
    return (
      <div className="glass-panel p-8 rounded-lg text-center border border-zinc-800">
        <ShieldAlert className="w-10 h-10 text-zinc-500 mx-auto mb-3" />
        <p className="text-zinc-400 font-mono text-sm">Sem acesso ao Pos-venda.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide flex items-center gap-3">
            <Wrench className="w-7 h-7 text-zinc-400" /> Pos-venda
          </h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Chamados de assistencia tecnica.</p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold px-4 py-2.5 rounded shadow flex items-center gap-2 transition active:scale-95 cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Novo Chamado
        </button>
      </div>

      {/* Sub-tabs do módulo — lista completa da spec do cliente (17/09) */}
      <ModuleTabs tabs={TICKETS_TABS} active={activeTab} onChange={setActiveTab} />
      <ActiveTabPlaceholder tabs={TICKETS_TABS} active={activeTab} />

      {activeTab === 'tickets' && (<>

      {/* Filters */}
      <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center bg-zinc-900 border border-zinc-800">
        <div className="relative w-full md:flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
          <input
            type="text"
            placeholder="Buscar por numero, cliente, descricao ou causa..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 text-white pl-10 pr-4 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-sans"
          />
        </div>
        <div className="w-full md:w-auto flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-mono whitespace-nowrap">Status:</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-zinc-950 border border-zinc-800 text-white text-xs rounded px-3 py-2 focus:outline-none focus:border-zinc-700 font-mono"
          >
            {FILTER_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-zinc-500 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando chamados...</p>
        </div>
      ) : filteredTickets.length === 0 ? (
        <div className="glass-panel p-12 rounded-lg text-center border border-zinc-800 bg-zinc-900">
          <Wrench className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <p className="text-zinc-500 font-mono text-sm">Nenhum chamado encontrado.</p>
          {tickets.length === 0 && <p className="text-zinc-600 font-mono text-xs mt-1">Crie seu primeiro chamado de assistencia.</p>}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block glass-panel rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-zinc-500 bg-zinc-950/60 border-b border-zinc-800 font-mono">
                  <tr>
                    <th className="py-3 px-4 font-normal">Numero</th>
                    <th className="py-3 px-4 font-normal">Cliente</th>
                    <th className="py-3 px-4 font-normal">Status</th>
                    <th className="py-3 px-4 font-normal text-right">Custo</th>
                    <th className="py-3 px-4 font-normal text-center">Garantia</th>
                    <th className="py-3 px-4 font-normal">Abertura</th>
                    <th className="py-3 px-4 font-normal text-right">Acoes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-sm">
                  {filteredTickets.map((ticket) => (
                    <tr key={ticket.id} className="hover:bg-zinc-800/30">
                      <td className="py-3 px-4 font-mono font-semibold text-white">{ticket.number}</td>
                      <td className="py-3 px-4 text-zinc-300">{ticket.client_name || '-'}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex px-2.5 py-0.5 text-[10px] font-bold uppercase rounded-full border ${getStatusBadge(ticket.status)}`}>
                          {ticket.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-white">{formatBRL(ticket.cost)}</td>
                      <td className="py-3 px-4 text-center text-xs">
                        {ticket.in_warranty == null ? <span className="text-zinc-500">-</span> : ticket.in_warranty ? <span className="text-emerald-400">Sim</span> : <span className="text-amber-400">Nao</span>}
                      </td>
                      <td className="py-3 px-4 text-zinc-400 font-mono text-xs">{formatDate(ticket.opened_at)}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleOpenDetail(ticket)}
                            className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 transition cursor-pointer"
                            title="Ver detalhes"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleOpenEdit(ticket)}
                            className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 transition cursor-pointer"
                            title="Editar"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          {['ABERTO', 'EM_ANALISE'].includes(ticket.status) && (
                            <button
                              onClick={() => handleDelete(ticket)}
                              className="p-1.5 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 transition cursor-pointer"
                              title="Excluir"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile cards */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {filteredTickets.map((ticket) => (
              <div key={ticket.id} className="glass-panel p-4 rounded-lg border border-zinc-800 bg-zinc-900">
                <div className="flex justify-between items-start">
                  <span className="font-mono font-bold text-white text-sm">{ticket.number}</span>
                  <span className={`inline-flex px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${getStatusBadge(ticket.status)}`}>
                    {ticket.status}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">{ticket.client_name || 'Sem cliente'}</p>
                <div className="mt-3 flex justify-between items-end">
                  <div>
                    <span className="text-[10px] font-mono text-zinc-500 uppercase block">Abertura</span>
                    <span className="text-xs font-mono text-zinc-300">{formatDate(ticket.opened_at)}</span>
                    <span className="text-[10px] font-mono text-zinc-500 uppercase block mt-1">Custo</span>
                    <span className="text-sm font-bold text-white font-mono">{formatBRL(ticket.cost)}</span>
                    <span className="text-xs text-zinc-500 font-mono"> · {ticket.in_warranty == null ? '-' : ticket.in_warranty ? 'Garantia Sim' : 'Garantia Nao'}</span>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleOpenDetail(ticket)}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 cursor-pointer"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleOpenEdit(ticket)}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 cursor-pointer"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    {['ABERTO', 'EM_ANALISE'].includes(ticket.status) && (
                      <button
                        onClick={() => handleDelete(ticket)}
                        className="p-2 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Modal Novo/Editar */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-panel w-full max-w-2xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col bg-zinc-900">
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2">
                  <Wrench className="w-5 h-5" />
                  {editingId ? `Editar ${tickets.find((t) => t.id === editingId)?.number || 'Chamado'}` : 'Novo Chamado'}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">Preencha os dados do chamado de assistencia</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="p-2 text-zinc-500 hover:text-white rounded cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{submitError}</div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Cliente *</label>
                  <select
                    value={formData.client_id}
                    onChange={(e) => setFormData((p) => ({ ...p, client_id: e.target.value, project_id: '' }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    <option value="">Selecione</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Projeto</label>
                  <select
                    value={formData.project_id}
                    onChange={(e) => setFormData((p) => ({ ...p, project_id: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    <option value="">Nenhum (opcional)</option>
                    {filteredProjects.map((pr) => (
                      <option key={pr.id} value={pr.id}>
                        {pr.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData((p) => ({ ...p, status: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Garantia</label>
                  <select
                    value={formData.in_warranty}
                    onChange={(e) => setFormData((p) => ({ ...p, in_warranty: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    <option value="">Nao informado</option>
                    <option value="true">Sim</option>
                    <option value="false">Nao</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Custo (R$)</label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      value={formData.cost}
                      onChange={(e) => setFormData((p) => ({ ...p, cost: e.target.value }))}
                      placeholder="0,00"
                      className="w-full bg-zinc-950 border border-zinc-800 text-white pl-9 pr-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Responsavel</label>
                  <select
                    value={formData.assigned_user_id}
                    onChange={(e) => setFormData((p) => ({ ...p, assigned_user_id: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    <option value="">Nenhum</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1 md:col-span-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> Data agendada {formData.status === 'AGENDADO' && <span className="text-amber-400">*</span>}
                  </label>
                  <input
                    type="date"
                    value={formData.scheduled_at}
                    onChange={(e) => setFormData((p) => ({ ...p, scheduled_at: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  />
                  <p className="text-[10px] text-zinc-500 font-mono">Ao salvar como AGENDADO com data, cria evento na Agenda automaticamente.</p>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Descricao *</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
                  rows={3}
                  placeholder="Descreva o problema ou solicitacao do cliente..."
                  className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Causa</label>
                  <input
                    type="text"
                    value={formData.cause}
                    onChange={(e) => setFormData((p) => ({ ...p, cause: e.target.value }))}
                    placeholder="Ex: dobradica com folga"
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Observacoes</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData((p) => ({ ...p, notes: e.target.value }))}
                    rows={1}
                    placeholder="Observacoes internas..."
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 resize-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Solucao</label>
                <textarea
                  value={formData.solution}
                  onChange={(e) => setFormData((p) => ({ ...p, solution: e.target.value }))}
                  rows={2}
                  placeholder="Descreva a solucao aplicada..."
                  className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-6 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Salvando...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" /> Salvar
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Detalhe */}
      {detailTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-panel w-full max-w-3xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col bg-zinc-900">
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2">
                  <Wrench className="w-5 h-5" /> {detailTicket.number}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">
                  {detailTicket.client_name || 'Sem cliente'}
                  {detailTicket.project_title ? ` · ${detailTicket.project_title}` : ''} · Aberto em {formatDateTime(detailTicket.opened_at)}
                </p>
              </div>
              <button onClick={() => setDetailTicket(null)} className="p-2 text-zinc-500 hover:text-white rounded cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 overflow-y-auto">
              <div className="flex flex-wrap gap-2 items-center">
                <span className={`inline-flex px-2.5 py-1 text-xs font-bold uppercase rounded-full border ${getStatusBadge(detailTicket.status)}`}>
                  {detailTicket.status}
                </span>
                <span className="text-xs font-mono text-zinc-400">
                  Garantia: {detailTicket.in_warranty == null ? <span className="text-zinc-500">-</span> : detailTicket.in_warranty ? <span className="text-emerald-400">Sim</span> : <span className="text-amber-400">Nao</span>}
                </span>
                {detailTicket.assigned_user_name && (
                  <span className="text-xs font-mono text-zinc-400">Responsavel: <span className="text-white">{detailTicket.assigned_user_name}</span></span>
                )}
                {detailTicket.cost != null && (
                  <span className="text-xs font-mono text-zinc-400">Custo: <span className="text-white">{formatBRL(detailTicket.cost)}</span></span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block mb-1">Descricao</span>
                  <span className="text-zinc-200 text-sm font-sans">{detailTicket.description || '-'}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block mb-1">Causa</span>
                  <span className="text-zinc-200 text-sm font-sans">{detailTicket.cause || '-'}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block mb-1">Solucao</span>
                  <span className="text-zinc-200 text-sm font-sans">{detailTicket.solution || '-'}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block mb-1">Observacoes</span>
                  <span className="text-zinc-200 text-sm font-sans">{detailTicket.notes || '-'}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block">Agendado</span>
                  <span className="text-zinc-300">{formatDate(detailTicket.scheduled_at)}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block">Resolvido</span>
                  <span className="text-zinc-300">{formatDateTime(detailTicket.resolved_at)}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block">Encerrado</span>
                  <span className="text-zinc-300">{formatDateTime(detailTicket.closed_at)}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-500 uppercase text-[10px] block">Criado por</span>
                  <span className="text-zinc-300">{detailTicket.created_by || '-'}</span>
                </div>
              </div>

              {/* Fotos */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-zinc-300 flex items-center gap-1.5">
                    <ImageIcon className="w-4 h-4" /> Fotos ({detailTicket.photos?.length || 0})
                  </h4>
                </div>

                {detailTicket.photos && detailTicket.photos.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {detailTicket.photos.map((photo) => (
                      <div key={photo.id} className="p-3 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs text-white font-mono truncate" title={photo.filename}>{photo.filename}</p>
                          <p className="text-[10px] text-zinc-500 font-mono">{photo.mime_type} · {(photo.size / 1024).toFixed(1)} KB · {formatDate(photo.created_at)}</p>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          <button
                            onClick={() => handleDownloadPhoto(photo.id, photo.filename)}
                            className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 cursor-pointer"
                            title="Download"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeletePhoto(photo.id)}
                            className="p-1.5 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 cursor-pointer"
                            title="Remover"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-600 font-mono">Nenhuma foto anexada.</p>
                )}

                <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center pt-2 border-t border-zinc-800">
                  <input
                    type="file"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="text-xs text-zinc-400 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border file:border-zinc-700 file:bg-zinc-800 file:text-white file:text-xs file:font-mono hover:file:bg-zinc-700 cursor-pointer"
                  />
                  <button
                    onClick={handleUploadPhoto}
                    disabled={!selectedFile || uploading}
                    className="px-4 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-xs font-semibold rounded flex items-center gap-2 disabled:opacity-40 cursor-pointer shrink-0"
                  >
                    {uploading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                    Enviar
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2 pt-4 border-t border-zinc-800">
                <button
                  onClick={() => {
                    const t = detailTicket;
                    setDetailTicket(null);
                    handleOpenEdit(t);
                  }}
                  className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 flex items-center gap-2 cursor-pointer"
                >
                  <Edit3 className="w-4 h-4" /> Editar
                </button>
                <button
                  onClick={() => setDetailTicket(null)}
                  className="px-4 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded cursor-pointer"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      </>)}
    </div>
  );
}
