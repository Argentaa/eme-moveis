import React, { useEffect, useState } from 'react';
import { 
  Plus, Search, Edit2, Trash2, Mail, Phone, MapPin, 
  ArrowLeft, Send, RefreshCw,
  Layers, ListTodo, ArrowRight, XCircle, AlertTriangle, FolderPlus, Eye
} from 'lucide-react';
import { FunnelStatus } from '../types';
import { clientService, projectService, funnelService, calendarService, leadOptionService, getApiErrorMessage } from '../services/api';
import { Client, Project, LeadOption } from '../types';
import ClientDetailModal from './ClientDetailModal';

interface ClientsViewProps {
  userRole: string;
}

export default function ClientsView({ userRole }: ClientsViewProps) {
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [viewMode, setViewMode] = useState<'LIST' | 'KANBAN'>('KANBAN');
  const [funnelColumns, setFunnelColumns] = useState<any[]>([]);
  const [editingFunnelCol, setEditingFunnelCol] = useState<string | null>(null);
  const [editingFunnelLabel, setEditingFunnelLabel] = useState('');
  const [editingFunnelDesc, setEditingFunnelDesc] = useState('');
  const [convertModalClient, setConvertModalClient] = useState<any | null>(null);
  const [convertTitle, setConvertTitle] = useState('');
  const [convertValue, setConvertValue] = useState('');
  const [convertError, setConvertError] = useState('');
  const [lostModalClient, setLostModalClient] = useState<Client | null>(null);
  const [lostReason, setLostReason] = useState('');
  const [lostError, setLostError] = useState('');

  // Modais Control
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [detailClient, setDetailClient] = useState<Client | null>(null);
  const [events, setEvents] = useState<any[]>([]);

  // Lead Options (fonte e campanha)
  const [campaigns, setCampaigns] = useState<LeadOption[]>([]);
  const [sources, setSources] = useState<LeadOption[]>([]);
  const [addingCampaign, setAddingCampaign] = useState(false);
  const [newCampaignName, setNewCampaignName] = useState('');
  const [addingSource, setAddingSource] = useState(false);
  const [newSourceName, setNewSourceName] = useState('');
  
  // Form States
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    cpf_cnpj: '',
    address: '',
    funnel_status: 'PROSPECCAO' as FunnelStatus,
    estimated_value: '',
    lead_source: '',
    campaign: '',
  });
  const [submitError, setSubmitError] = useState('');

  const loadClients = async () => {
    setLoading(true);
    try {
      const [data, projs, evts] = await Promise.all([
        clientService.getAll(),
        projectService.getAll().catch(() => []),
        calendarService.getAll().catch(() => []),
      ]);
      setClients(data);
      setProjects(projs);
      setEvents(evts);
    } catch (err) {
      console.error('Erro ao carregar clientes:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
    loadFunnelColumns();
    leadOptionService.getSources().then(setSources).catch(() => setSources([]));
    leadOptionService.getCampaigns().then(setCampaigns).catch(() => setCampaigns([]));
  }, []);

  const handleOpenCreateModal = () => {
    setEditingClient(null);
    setFormData({
      name: '',
      email: '',
      phone: '',
      cpf_cnpj: '',
      address: '',
      funnel_status: 'PROSPECCAO' as FunnelStatus,
      estimated_value: '',
      lead_source: '',
      campaign: '',
    });
    setSubmitError('');
    setAddingSource(false);
    setAddingCampaign(false);
    setNewSourceName('');
    setNewCampaignName('');
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (client: Client) => {
    setEditingClient(client);
    setFormData({
      name: client.name,
      email: client.email,
      phone: client.phone,
      cpf_cnpj: client.cpf_cnpj,
      address: client.address,
      funnel_status: client.funnel_status,
      estimated_value: client.estimated_value ? String(client.estimated_value) : '',
      lead_source: client.lead_source || '',
      campaign: client.campaign || '',
    });
    setSubmitError('');
    setAddingSource(false);
    setAddingCampaign(false);
    setNewSourceName('');
    setNewCampaignName('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    if (!formData.name || !formData.cpf_cnpj) {
      setSubmitError('Nome do Cliente e CPF/CNPJ são obrigatórios.');
      return;
    }

    try {
      const payload = {
        ...formData,
        estimated_value: formData.estimated_value !== '' ? Number(formData.estimated_value) : undefined,
      };
      if (editingClient) {
        await clientService.update(editingClient.id, payload);
      } else {
        await clientService.create(payload);
      }
      setIsModalOpen(false);
      loadClients();
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, 'Erro ao salvar informações do cliente.'));
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (userRole !== 'ADMIN') {
      alert('Acesso negado: Apenas administradores podem excluir registros.');
      return;
    }

    if (confirm(`Deseja mesmo remover o cliente "${name}" permanentemente?\nIsso pode afetar projetos ativos dele.`)) {
      try {
        await clientService.delete(id);
        loadClients();
      } catch (err) {
        console.error('Erro ao deletar cliente:', err);
        alert(getApiErrorMessage(err, 'Falha ao remover cliente.'));
      }
    }
  };

  // Filter clients
  const filteredClients = clients.filter(c => 
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.cpf_cnpj.includes(searchQuery)
  );

  const handleMarkLost = async () => {
    if (!lostModalClient) return;
    setLostError('');
    try {
      await clientService.updateFunnel(lostModalClient.id, 'PERDIDO');
      await clientService.update(lostModalClient.id, { lost_reason: lostReason } as any);
      setLostModalClient(null);
      setLostReason('');
      loadClients();
    } catch (err) {
      setLostError(getApiErrorMessage(err, 'Erro ao registrar negócio perdido.'));
    }
  };

  const handleCreateCampaign = async () => {
    const name = newCampaignName.trim();
    if (!name) return;
    try {
      await leadOptionService.createCampaign(name);
      const list = await leadOptionService.getCampaigns();
      setCampaigns(list);
      setFormData(prev => ({ ...prev, campaign: name }));
      setAddingCampaign(false);
      setNewCampaignName('');
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao criar campanha.'));
    }
  };

  const handleCreateSource = async () => {
    const name = newSourceName.trim();
    if (!name) return;
    try {
      await leadOptionService.createSource(name);
      const list = await leadOptionService.getSources();
      setSources(list);
      setFormData(prev => ({ ...prev, lead_source: name }));
      setAddingSource(false);
      setNewSourceName('');
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao criar fonte do lead.'));
    }
  };

  const loadFunnelColumns = async () => {
    try {
      const cols = await funnelService.getAll();
      if (cols && cols.length > 0) setFunnelColumns(cols);
    } catch (err) {
      console.error('Erro ao carregar colunas do funil:', err);
    }
  };

  const handleSaveFunnelCol = async (columnKey: string) => {
    try {
      await funnelService.update(columnKey, { label: editingFunnelLabel, description: editingFunnelDesc });
      setEditingFunnelCol(null);
      loadFunnelColumns();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao salvar coluna.'));
    }
  };

  const handleConvertToProject = async () => {
    if (!convertModalClient || !convertTitle.trim()) {
      setConvertError('O título do projeto é obrigatório.');
      return;
    }
    setConvertError('');
    try {
      await projectService.create({
        title: convertTitle.trim(),
        client_id: convertModalClient.id,
        description: '',
        status: 'ORCAMENTO',
        value: Number(convertValue) || 0,
        deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().substring(0, 10),
        steps: [
          { id: '1', label: 'Medição técnica in loco', completed: false },
          { id: '2', label: 'Apresentação e plano de corte 3D', completed: false },
          { id: '3', label: 'Corte e colagem de fita de borda', completed: false },
          { id: '4', label: 'Usinagem de furos e ferragens', completed: false },
          { id: '5', label: 'Montagem prévia fábrica', completed: false },
          { id: '6', label: 'Instalação final no cliente', completed: false },
        ],
      });
      setConvertModalClient(null);
      setConvertTitle('');
      setConvertValue('');
      alert(`Projeto "${convertTitle}" criado com sucesso! Acesse a aba Projetos para gerenciá-lo.`);
    } catch (err) {
      setConvertError(getApiErrorMessage(err, 'Erro ao criar projeto.'));
    }
  };

  const FUNNEL_DEFAULTS = [
    { id: 'PROSPECCAO' as FunnelStatus, label: 'Prospecção', color: 'border-t-zinc-500', desc: 'Leads identificados' },
    { id: 'ORCAMENTO' as FunnelStatus, label: 'Orçamento', color: 'border-t-blue-500', desc: 'Proposta em elaboração' },
    { id: 'APRESENTACAO' as FunnelStatus, label: 'Apresentação', color: 'border-t-purple-500', desc: 'Apresentando ao cliente' },
    { id: 'NEGOCIACAO' as FunnelStatus, label: 'Negociação', color: 'border-t-amber-500', desc: 'Em processo de negociação' },
    { id: 'FECHAMENTO' as FunnelStatus, label: 'Fechamento', color: 'border-t-emerald-500', desc: 'Contrato assinado' },
  ];
  const FUNNEL_COLUMNS = FUNNEL_DEFAULTS.map(def => {
    const fromDB = funnelColumns.find(c => c.column_key === def.id);
    return fromDB ? { ...def, label: fromDB.label, desc: fromDB.description || def.desc } : def;
  });

  // Opções de campanha e fonte — inclui o valor atual do cliente quando ausente da lista
  const campaignOptions: LeadOption[] = campaigns.some(c => c.name === formData.campaign)
    ? campaigns
    : formData.campaign
      ? [{ id: '__campanha_atual__', name: formData.campaign, active: true, created_at: '' }, ...campaigns]
      : campaigns;

  const sourceOptions: LeadOption[] = sources.some(s => s.name === formData.lead_source)
    ? sources
    : formData.lead_source
      ? [{ id: '__fonte_atual__', name: formData.lead_source, active: true, created_at: '' }, ...sources]
      : sources;

  const handleShiftFunnel = async (client: Client, direction: 'LEFT' | 'RIGHT') => {
    const cols = FUNNEL_COLUMNS.map(c => c.id);
    const idx = cols.indexOf(client.funnel_status);
    let nextIdx = idx;
    if (direction === 'LEFT' && idx > 0) nextIdx = idx - 1;
    if (direction === 'RIGHT' && idx < cols.length - 1) nextIdx = idx + 1;
    if (nextIdx === idx) return;
    const nextStatus = cols[nextIdx];
    try {
      setClients(prev => prev.map(c => c.id === client.id ? { ...c, funnel_status: nextStatus } : c));
      await clientService.updateFunnel(client.id, nextStatus);
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao mover cliente no funil.'));
      loadClients();
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Bar Actions */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Cadastro de Clientes</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Gerenciamento das informações dos clientes da marcenaria.</p>
        </div>
        
        <div className="flex items-center gap-2">
          {/* View mode switcher */}
          <div className="bg-zinc-900 border border-zinc-800 p-1 rounded-md flex">
            <button
              onClick={() => setViewMode('KANBAN')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1 cursor-pointer ${viewMode === 'KANBAN' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'}`}
            >
              <Layers className="w-3.5 h-3.5" /> Funil
            </button>
            <button
              onClick={() => setViewMode('LIST')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1 cursor-pointer ${viewMode === 'LIST' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'}`}
            >
              <ListTodo className="w-3.5 h-3.5" /> Lista Geral
            </button>
          </div>

          {/* Only ADMIN and GERENTE can create/edit clients */}
          {['ADMIN', 'GERENTE'].includes(userRole) && (
            <button 
              id="btn-add-client"
              onClick={handleOpenCreateModal}
              className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded shadow-md flex items-center gap-1.5 transition active:scale-95 cursor-pointer font-sans h-[38px]"
            >
              <Plus className="w-4 h-4" /> Novo Cliente
            </button>
          )}
        </div>
      </div>

      {/* Filter panel */}
      <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center">
        <div className="relative w-full md:flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 w-4 h-4" />
          <input 
            type="text"
            placeholder="Buscar por nome, e-mail ou CPF/CNPJ..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-805 text-white pl-10 pr-4 py-2 text-sm rounded focus:outline-none focus:border-red-600 font-sans"
          />
        </div>
        <div className="text-xs text-zinc-400 font-mono w-full md:w-auto text-right">
          Exibindo {filteredClients.length} de {clients.length} corporativos
        </div>
      </div>

      {/* Table grid layout */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando carteira de clientes...</p>
        </div>
      ) : viewMode === 'KANBAN' ? (
        /* KANBAN FUNIL DE VENDAS */
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 overflow-x-auto min-w-[900px] pb-4">
          {(() => {
            const today = new Date();
            const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
            // Remove do funil clientes cujos projetos estão todos concluídos há mais de 30 dias
            filteredClients.forEach(client => {
              const clientProjects = projects.filter(p => p.client_id === client.id);
              if (clientProjects.length > 0) {
                const allConcluded = clientProjects.every(p => p.status === 'CONCLUIDO');
                const lastProject = clientProjects.sort((a, b) => new Date(b.deadline).getTime() - new Date(a.deadline).getTime())[0];
                if (allConcluded && new Date(lastProject.deadline) < thirtyDaysAgo) {
                  // Move automaticamente para FECHAMENTO se ainda estiver no funil ativo
                  if (client.funnel_status !== 'FECHAMENTO' && client.funnel_status !== 'PERDIDO') {
                    clientService.updateFunnel(client.id, 'FECHAMENTO');
                  }
                }
              }
            });
            return null;
          })()}
          {FUNNEL_COLUMNS.map(col => {
            const colClients = filteredClients.filter(c => c.funnel_status === col.id);
            const colTotal = colClients.reduce((acc, c) => {
              const clientProjects = projects.filter(p => p.client_id === c.id && p.status !== 'CONCLUIDO');
              const realValue = clientProjects.reduce((s, p) => s + p.value, 0);
              return acc + (realValue > 0 ? realValue : (c.estimated_value || 0));
            }, 0);
            return (
              <div key={col.id} className={`glass-panel rounded-xl flex flex-col min-h-[500px] overflow-hidden border-t-2 ${col.color}`}>
                <div className="p-4 bg-zinc-950/60 border-b border-zinc-900">
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      {editingFunnelCol === col.id ? (
                        <div className="space-y-1.5">
                          <input
                            type="text"
                            value={editingFunnelLabel}
                            onChange={e => setEditingFunnelLabel(e.target.value)}
                            className="w-full bg-zinc-950 border border-red-600 text-white rounded px-2 py-1 text-sm focus:outline-none"
                            autoFocus
                          />
                          <input
                            type="text"
                            value={editingFunnelDesc}
                            onChange={e => setEditingFunnelDesc(e.target.value)}
                            placeholder="Descrição (opcional)"
                            className="w-full bg-zinc-950 border border-zinc-700 text-zinc-400 rounded px-2 py-1 text-xs focus:outline-none"
                          />
                          <div className="flex gap-1.5 mt-1">
                            <button onClick={() => handleSaveFunnelCol(col.id)} className="text-[10px] font-mono text-emerald-400 hover:text-emerald-300 cursor-pointer">Salvar</button>
                            <button onClick={() => setEditingFunnelCol(null)} className="text-[10px] font-mono text-zinc-500 hover:text-white cursor-pointer">Cancelar</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-1.5">
                            <h3 className="text-sm font-sans font-bold text-white">{col.label}</h3>
                            {['ADMIN', 'GERENTE'].includes(userRole) && (
                              <button
                                onClick={() => { setEditingFunnelCol(col.id); setEditingFunnelLabel(col.label); setEditingFunnelDesc(col.desc); }}
                                className="p-0.5 text-zinc-600 hover:text-zinc-300 cursor-pointer"
                                title="Editar nome da coluna"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                          <p className="text-[10px] text-zinc-500 font-mono mt-0.5">{col.desc}</p>
                          {colTotal > 0 && (
                            <p className="text-[11px] font-mono text-emerald-600 font-semibold mt-0.5">
                              {colTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                            </p>
                          )}
                        </>
                      )}
                    </div>
                    <span className="text-xs font-bold font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 ml-2 shrink-0">
                      {colClients.length}
                    </span>
                  </div>
                </div>
                <div className="p-3 space-y-3 flex-1 overflow-y-auto max-h-[450px]">
                  {colClients.map(client => {
                      const clientProjects = projects.filter(p => p.client_id === client.id && p.status !== 'CONCLUIDO');
                      const clientTotal = clientProjects.reduce((s, p) => s + p.value, 0);
                      // Prioriza valor real do projeto; cai para estimado se não houver projeto
                      const displayValue = clientTotal > 0 ? clientTotal : (client.estimated_value || 0);
                      const isEstimated = clientTotal === 0 && displayValue > 0;
                      const pendingTasks = events.filter(e => e.client_id === client.id && e.status !== 'CONCLUIDO' && e.status !== 'CANCELADO').length;
                      return (
                      <div key={client.id} onClick={() => setDetailClient(client)} className="p-4 bg-zinc-950/70 hover:bg-zinc-900 border border-zinc-900 hover:border-red-800/40 rounded-lg group transition shadow-lg cursor-pointer">
                        <h4 className="text-sm font-semibold text-zinc-100 group-hover:text-white">{client.name}</h4>
                        {client.email && <p className="text-[11px] text-zinc-500 mt-0.5 truncate">✉ {client.email}</p>}
                        {client.phone && <p className="text-[11px] text-zinc-500 truncate">📞 {client.phone}</p>}
                        {displayValue > 0 && (
                          <p className={`text-[11px] font-mono font-semibold mt-1 ${isEstimated ? 'text-zinc-400' : 'text-emerald-500'}`}>
                            {isEstimated ? '~ ' : ''}{displayValue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                          </p>
                        )}
                        {pendingTasks > 0 && (
                          <span className="inline-flex items-center gap-1 mt-1.5 text-[10px] font-mono text-zinc-400 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
                            <ListTodo className="w-3 h-3" />
                            {pendingTasks}
                          </span>
                        )}
                      <div className="mt-3 flex justify-between items-center border-t border-zinc-900 pt-2.5">
                        <div className="flex gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleShiftFunnel(client, 'LEFT'); }}
                            disabled={client.funnel_status === 'PROSPECCAO'}
                            className="p-1 text-zinc-500 hover:text-white disabled:opacity-20 cursor-pointer"
                            title="Recuar etapa"
                          >
                            <ArrowLeft className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleShiftFunnel(client, 'RIGHT'); }}
                            disabled={client.funnel_status === 'FECHAMENTO'}
                            className="p-1 text-zinc-500 hover:text-white disabled:opacity-20 cursor-pointer"
                            title="Avançar etapa"
                          >
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {['ADMIN', 'GERENTE', 'PROJETISTA'].includes(userRole) && (
                          <div className="flex gap-1">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleOpenEditModal(client); }}
                              className="p-1 text-zinc-500 hover:text-blue-400 cursor-pointer"
                              title="Editar"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            {client.funnel_status !== 'PERDIDO' && (
                              <button
                                onClick={(e) => { e.stopPropagation(); setLostModalClient(client); setLostReason(''); }}
                                className="p-1 text-zinc-500 hover:text-amber-400 cursor-pointer"
                                title="Marcar como negócio perdido"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {client.funnel_status === 'FECHAMENTO' && ['ADMIN', 'GERENTE'].includes(userRole) && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setConvertModalClient(client);
                                  setConvertTitle(`Projeto ${client.name}`);
                                  setConvertValue(client.estimated_value ? String(client.estimated_value) : '');
                                  setConvertError('');
                                }}
                                className="p-1 text-zinc-500 hover:text-emerald-400 cursor-pointer"
                                title="Converter em Projeto"
                              >
                                <FolderPlus className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {userRole === 'ADMIN' && (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleDelete(client.id, client.name); }}
                                className="p-1 text-zinc-500 hover:text-red-400 cursor-pointer"
                                title="Excluir cliente"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                      );
                    })}
                  {colClients.length === 0 && (
                    <div className="py-10 border-2 border-dashed border-zinc-900 rounded-lg flex items-center justify-center">
                      <p className="text-[11px] text-zinc-600 font-mono">Vazio</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                <tr>
                  <th className="py-4 px-6 font-normal">Nome do Cliente</th>
                  <th className="py-4 px-6 font-normal">CPF / CNPJ</th>
                  <th className="py-4 px-6 font-normal">Contatos</th>
                  <th className="py-4 px-6 font-normal">Endereço de Entrega</th>
                  <th className="py-4 px-6 font-normal text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {filteredClients.map((client) => (
                  <tr key={client.id} className="hover:bg-zinc-900/40 transition">
                    <td className="py-4 px-6 font-sans">
                      <div className="font-semibold text-white text-base">{client.name}</div>
                      <span className="text-xs font-mono text-zinc-500 block mt-0.5">ID: {client.id}</span>
                    </td>
                    <td className="py-4 px-6 font-mono text-xs text-zinc-400">
                      {client.cpf_cnpj}
                    </td>
                    <td className="py-4 px-6 space-y-1">
                      {client.email && (
                        <div className="flex items-center gap-1.5 text-xs text-zinc-300">
                          <Mail className="w-3.5 h-3.5 text-red-600" />
                          <span>{client.email}</span>
                        </div>
                      )}
                      {client.phone && (
                        <div className="flex items-center gap-1.5 text-xs text-zinc-300">
                          <Phone className="w-3.5 h-3.5 text-red-600" />
                          <span className="font-mono">{client.phone}</span>
                        </div>
                      )}
                    </td>
                    <td className="py-4 px-6 max-w-sm">
                      <div className="flex items-start gap-1.5 text-xs text-zinc-400">
                        <MapPin className="w-3.5 h-3.5 mt-0.5 text-zinc-500 shrink-0" />
                        <span className="line-clamp-2">{client.address || 'Não cadastrado'}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-right space-x-2 shrink-0">
                      {['ADMIN', 'GERENTE'].includes(userRole) && (
                        <button 
                          onClick={() => handleOpenEditModal(client)}
                          className="p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition shadow inline-flex justify-center items-center cursor-pointer"
                          title="Editar Cadastro"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {['ADMIN', 'GERENTE', 'PROJETISTA'].includes(userRole) && (
                        <button 
                          onClick={() => setDetailClient(client)}
                          className="p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition shadow inline-flex justify-center items-center cursor-pointer"
                          title="Ver Detalhes"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {userRole === 'ADMIN' && (
                        <button 
                          onClick={() => handleDelete(client.id, client.name)}
                          className="p-2 bg-zinc-900 hover:bg-red-950/40 text-zinc-400 hover:text-red-400 rounded border border-zinc-800 transition shadow inline-flex justify-center items-center cursor-pointer"
                          title="Remover Cliente"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}

                {filteredClients.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-zinc-500 font-mono">
                      Nenhum registro de cliente coincide com a pesquisa.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba Negócio Perdido — aparece abaixo do kanban ou da lista */}
      {viewMode === 'KANBAN' && (() => {
        const lostClients = filteredClients.filter(c => c.funnel_status === 'PERDIDO');
        if (lostClients.length === 0) return null;
        return (
          <div className="glass-panel rounded-lg overflow-hidden border-l-4 border-l-red-600">
            <div className="p-4 bg-zinc-950/60 border-b border-zinc-900 flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              <h3 className="text-sm font-semibold text-white font-sans">Negócios Perdidos</h3>
              <span className="text-xs font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 ml-auto">{lostClients.length}</span>
            </div>
            <div className="divide-y divide-zinc-900">
              {lostClients.map(client => (
                <div key={client.id} className="p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-zinc-300 font-sans">{client.name}</p>
                    {client.lost_reason && (
                      <p className="text-[11px] text-zinc-500 font-mono mt-0.5">Motivo: {client.lost_reason}</p>
                    )}
                    {client.email && <p className="text-[11px] text-zinc-500 truncate">✉ {client.email}</p>}
                  </div>
                  {['ADMIN', 'GERENTE'].includes(userRole) && (
                    <button
                      onClick={() => clientService.updateFunnel(client.id, 'PROSPECCAO').then(loadClients)}
                      className="text-[11px] font-mono text-zinc-400 hover:text-emerald-400 cursor-pointer whitespace-nowrap"
                      title="Reativar no funil"
                    >
                      ↩ Reativar
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* Modal Converter em Projeto */}
      {convertModalClient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950 p-5 border-b border-zinc-850 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-emerald-500" />
                <h3 className="text-base font-serif font-semibold text-white">Converter em Projeto</h3>
              </div>
              <button onClick={() => setConvertModalClient(null)} className="text-zinc-500 hover:text-white cursor-pointer font-mono text-xs">Sair</button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-zinc-400">
                Criando projeto para <strong className="text-white">{convertModalClient.name}</strong>. O projeto entrará em <strong className="text-white">Orçamento</strong> no Kanban de Projetos.
              </p>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Título do Projeto *</label>
                <input
                  type="text"
                  value={convertTitle}
                  onChange={e => setConvertTitle(e.target.value)}
                  placeholder="Ex: Cozinha Planejada MDF Branco"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Valor do Projeto (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={convertValue}
                  onChange={e => setConvertValue(e.target.value)}
                  placeholder="Ex: 15000.00"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>
              {convertError && <p className="text-xs text-red-400 font-mono">{convertError}</p>}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setConvertModalClient(null)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-800 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleConvertToProject}
                  className="px-5 py-2 text-sm bg-emerald-600 hover:bg-emerald-700 text-white rounded font-semibold cursor-pointer"
                >
                  Criar Projeto
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Negócio Perdido */}
      {lostModalClient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950 p-5 border-b border-zinc-850 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h3 className="text-base font-serif font-semibold text-white">Negócio Perdido</h3>
              </div>
              <button onClick={() => setLostModalClient(null)} className="text-zinc-500 hover:text-white cursor-pointer font-mono text-xs">Sair</button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-zinc-400">
                Registrando negócio perdido para <strong className="text-white">{lostModalClient.name}</strong>.
              </p>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Motivo da perda</label>
                <textarea
                  value={lostReason}
                  onChange={e => setLostReason(e.target.value)}
                  placeholder="Ex: Preço acima do esperado, cliente optou por outro fornecedor..."
                  rows={3}
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 resize-none"
                />
              </div>
              {lostError && <p className="text-xs text-red-400 font-mono">{lostError}</p>}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setLostModalClient(null)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-800 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleMarkLost}
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer"
                >
                  Confirmar Perda
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Slideout Side Modal for Client Action */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800/80 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-semibold text-white">
                  {editingClient ? 'Atualizar Cliente' : 'Adicionar Novo Cliente'}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">Controle CRM da EME Móveis</p>
              </div>
              <button 
                onClick={() => {
                  setIsModalOpen(false);
                  setAddingSource(false);
                  setAddingCampaign(false);
                  setNewSourceName('');
                  setNewCampaignName('');
                }}
                className="text-zinc-500 hover:text-white transition font-mono text-sm uppercase px-2 py-1 rounded hover:bg-zinc-900"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-7 space-y-6 font-sans">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nome do Cliente *</label>
                <input 
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Roberto de Oliveira Menezes"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">CPF / CNPJ *</label>
                  <input 
                    type="text"
                    required
                    value={formData.cpf_cnpj}
                    onChange={(e) => setFormData({ ...formData, cpf_cnpj: e.target.value })}
                    placeholder="000.000.000-00"
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Telefone Comercial</label>
                  <input 
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="(55) 99999-9999"
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">E-mail</label>
                <input 
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Ex: contato@empresa.com.br"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Endereço de Entrega Completo</label>
                <textarea 
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Ex: Al. Lorena, 1550 - Jardins, São Paulo/SP"
                  rows={2}
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Etapa do Funil de Vendas</label>
                <select
                  value={formData.funnel_status}
                  onChange={(e) => setFormData({ ...formData, funnel_status: e.target.value as FunnelStatus })}
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                >
                  {FUNNEL_COLUMNS.map(col => (
                    <option key={col.id} value={col.id}>{col.label}</option>
                  ))}
                  {formData.funnel_status === 'PERDIDO' && (
                    <option value="PERDIDO">Perdido</option>
                  )}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Campanha</label>
                {addingCampaign ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newCampaignName}
                      onChange={(e) => setNewCampaignName(e.target.value)}
                      placeholder="Nome da nova campanha"
                      className="flex-1 w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                    />
                    <button
                      type="button"
                      onClick={() => { setAddingCampaign(false); setNewCampaignName(''); }}
                      className="px-3 py-2 text-xs bg-zinc-900 text-zinc-400 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono whitespace-nowrap"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      onClick={handleCreateCampaign}
                      className="px-4 py-2 text-xs bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer whitespace-nowrap"
                    >
                      Confirmar
                    </button>
                  </div>
                ) : (
                  <select
                    value={formData.campaign}
                    onChange={(e) => {
                      if (e.target.value === '__nova_campanha__') {
                        setAddingCampaign(true);
                      } else {
                        setFormData({ ...formData, campaign: e.target.value });
                      }
                    }}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="">Não informado</option>
                    {campaignOptions.map(c => (
                      <option key={c.id} value={c.name}>{c.name}</option>
                    ))}
                    <option value="__nova_campanha__">+ Nova campanha...</option>
                  </select>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor Estimado (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.estimated_value}
                  onChange={(e) => setFormData({ ...formData, estimated_value: e.target.value })}
                  placeholder="Ex: 15000.00"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
                <p className="text-[11px] text-zinc-500 font-mono">Valor previsto antes de criar o projeto formal. Se houver projeto vinculado, o valor real do projeto será exibido.</p>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Fonte do Lead</label>
                {addingSource ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newSourceName}
                      onChange={(e) => setNewSourceName(e.target.value)}
                      placeholder="Nome da nova fonte"
                      className="flex-1 w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                    />
                    <button
                      type="button"
                      onClick={() => { setAddingSource(false); setNewSourceName(''); }}
                      className="px-3 py-2 text-xs bg-zinc-900 text-zinc-400 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono whitespace-nowrap"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      onClick={handleCreateSource}
                      className="px-4 py-2 text-xs bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer whitespace-nowrap"
                    >
                      Confirmar
                    </button>
                  </div>
                ) : (
                  <select
                    value={formData.lead_source}
                    onChange={(e) => {
                      if (e.target.value === '__nova_fonte__') {
                        setAddingSource(true);
                      } else {
                        setFormData({ ...formData, lead_source: e.target.value });
                      }
                    }}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="">Não informado</option>
                    {sourceOptions.map(s => (
                      <option key={s.id} value={s.name}>{s.name}</option>
                    ))}
                    <option value="__nova_fonte__">+ Nova fonte...</option>
                  </select>
                )}
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800 mt-6 md:mt-8">
                <button 
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false);
                    setAddingSource(false);
                    setAddingCampaign(false);
                    setNewSourceName('');
                    setNewCampaignName('');
                  }}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 hover:text-white rounded border border-zinc-800 hover:bg-zinc-850 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold flex items-center gap-1.5 transition shadow active:scale-95 cursor-pointer"
                >
                  <Send className="w-4 h-4" /> {editingClient ? 'Salvar Edição' : 'Cadastrar Cliente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Detalhes do Cliente */}
      {detailClient && (
        <ClientDetailModal
          client={detailClient}
          userRole={userRole}
          onClose={() => setDetailClient(null)}
          onChanged={() => {
            setDetailClient(null);
            loadClients();
          }}
        />
      )}

    </div>
  );
}
