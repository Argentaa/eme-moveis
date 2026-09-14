import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Download,
  Edit2,
  File,
  FileText,
  History,
  Image,
  Info,
  ListTodo,
  Package,
  Paperclip,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react';
import {
  attachmentService,
  authService,
  calendarService,
  clientService,
  getApiErrorMessage,
  itemService,
  productService,
} from '../services/api';
import { Attachment, Client, ClientDetail, FunnelStatus, NegotiationItem, Product } from '../types';

interface ClientDetailModalProps {
  client: Client;
  userRole: string;
  onClose: () => void;
  onChanged?: () => void;
}

// ── Funil de vendas (6 etapas) ─────────────────────────────────
const FUNNEL_ORDER: FunnelStatus[] = [
  'PROSPECCAO',
  'ORCAMENTO',
  'APRESENTACAO',
  'NEGOCIACAO',
  'FECHAMENTO',
  'PERDIDO',
];

const FUNNEL_META: Record<FunnelStatus, { label: string; chip: string }> = {
  PROSPECCAO: { label: 'Prospecção', chip: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30' },
  ORCAMENTO: { label: 'Orçamento', chip: 'text-blue-300 bg-blue-500/10 border border-blue-500/30' },
  APRESENTACAO: { label: 'Apresentação', chip: 'text-purple-300 bg-purple-500/10 border border-purple-500/30' },
  NEGOCIACAO: { label: 'Negociação', chip: 'text-amber-300 bg-amber-500/10 border border-amber-500/30' },
  FECHAMENTO: { label: 'Fechamento', chip: 'text-emerald-300 bg-emerald-500/10 border border-emerald-500/30' },
  PERDIDO: { label: 'Perdido', chip: 'text-red-300 bg-red-500/10 border border-red-500/30' },
};

// ── Projetos ──────────────────────────────────────────────────
const PROJECT_STATUS_META: Record<string, { label: string; chip: string }> = {
  ORCAMENTO: { label: 'Orçamento', chip: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30' },
  PROJETADO: { label: 'Aprovado', chip: 'text-amber-300 bg-amber-500/10 border border-amber-500/30' },
  PRODUCAO: { label: 'Corte e Produção', chip: 'text-red-300 bg-red-500/10 border border-red-500/30' },
  MONTAGEM: { label: 'Instalação', chip: 'text-rose-300 bg-rose-500/10 border border-rose-500/30' },
  CONCLUIDO: { label: 'Concluído', chip: 'text-emerald-300 bg-emerald-500/10 border border-emerald-500/30' },
};

// ── Histórico (interações) ────────────────────────────────────
const INTERACTION_META: Record<string, { label: string; badge: string }> = {
  CONVERSA: { label: 'Conversa', badge: 'text-blue-300 bg-blue-500/10 border border-blue-500/30' },
  PROPOSTA: { label: 'Proposta', badge: 'text-purple-300 bg-purple-500/10 border border-purple-500/30' },
  ORCAMENTO: { label: 'Orçamento', badge: 'text-amber-300 bg-amber-500/10 border border-amber-500/30' },
  ALTERACAO_PROJETO: { label: 'Alteração de Projeto', badge: 'text-orange-300 bg-orange-500/10 border border-orange-500/30' },
  OBSERVACAO: { label: 'Observação', badge: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30' },
  SISTEMA: { label: 'sistema', badge: 'text-zinc-500 bg-zinc-800 border border-zinc-700' },
};

// ── Tarefas (eventos) ─────────────────────────────────────────
const TASK_TYPE_META: Record<string, { label: string; chip: string }> = {
  MEDICAO: { label: 'Medição', chip: 'text-blue-300 bg-blue-500/10 border border-blue-500/30' },
  REUNIAO_CLIENTE: { label: 'Reunião', chip: 'text-purple-300 bg-purple-500/10 border border-purple-500/30' },
  APROVACAO_PROJETO: { label: 'Aprovação de Projeto', chip: 'text-amber-300 bg-amber-500/10 border border-amber-500/30' },
  PRODUCAO: { label: 'Produção', chip: 'text-orange-300 bg-orange-500/10 border border-orange-500/30' },
  MONTAGEM: { label: 'Montagem', chip: 'text-red-300 bg-red-500/10 border border-red-500/30' },
  ENTREGA: { label: 'Entrega', chip: 'text-emerald-300 bg-emerald-500/10 border border-emerald-500/30' },
  ASSISTENCIA_TECNICA: { label: 'Assistência Técnica', chip: 'text-cyan-300 bg-cyan-500/10 border border-cyan-500/30' },
  LIGACAO: { label: 'Ligação', chip: 'text-sky-300 bg-sky-500/10 border border-sky-500/30' },
  VISITA: { label: 'Visita', chip: 'text-teal-300 bg-teal-500/10 border border-teal-500/30' },
  WHATSAPP: { label: 'WhatsApp', chip: 'text-green-300 bg-green-500/10 border border-green-500/30' },
  PERSONALIZADO: { label: 'Personalizado', chip: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30' },
};

const TASK_STATUS_META: Record<string, { label: string; chip: string }> = {
  AGENDADO: { label: 'Agendado', chip: 'text-blue-300 bg-blue-500/10 border border-blue-500/30' },
  CONFIRMADO: { label: 'Confirmado', chip: 'text-emerald-300 bg-emerald-500/10 border border-emerald-500/30' },
  EM_ANDAMENTO: { label: 'Em Andamento', chip: 'text-amber-300 bg-amber-500/10 border border-amber-500/30' },
  CONCLUIDO: { label: 'Concluído', chip: 'text-zinc-400 bg-zinc-500/10 border border-zinc-500/30' },
  CANCELADO: { label: 'Cancelado', chip: 'text-red-300 bg-red-500/10 border border-red-500/30' },
};

const TASK_FORM_TYPES: Array<{ value: string; label: string }> = [
  { value: 'LIGACAO', label: 'Ligação' },
  { value: 'REUNIAO_CLIENTE', label: 'Reunião' },
  { value: 'VISITA', label: 'Visita' },
  { value: 'WHATSAPP', label: 'WhatsApp' },
  { value: 'PERSONALIZADO', label: 'Personalizado' },
];

const INTERACTION_FORM_TYPES: Array<{ value: string; label: string }> = [
  { value: 'CONVERSA', label: 'Conversa' },
  { value: 'PROPOSTA', label: 'Proposta' },
  { value: 'ORCAMENTO', label: 'Orçamento' },
  { value: 'OBSERVACAO', label: 'Observação' },
];

// ── Abas ──────────────────────────────────────────────────────
const TABS: Array<{
  id: 'overview' | 'history' | 'tasks' | 'attachments' | 'produtos';
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { id: 'overview', label: 'Visão Geral', icon: Info },
  { id: 'history', label: 'Histórico', icon: History },
  { id: 'tasks', label: 'Tarefas', icon: ListTodo },
  { id: 'produtos', label: 'Produtos', icon: Package },
  { id: 'attachments', label: 'Anexos', icon: Paperclip },
];

// ── Produtos / serviços (negociação) ─────────────────────────
const RECURRENCE_LABELS: Record<string, string> = {
  UNICO: 'Único',
  MENSAL: 'Mensal',
  TRIMESTRAL: 'Trimestral',
  ANUAL: 'Anual',
};

const RECURRENCE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'UNICO', label: 'Único' },
  { value: 'MENSAL', label: 'Mensal' },
  { value: 'TRIMESTRAL', label: 'Trimestral' },
  { value: 'ANUAL', label: 'Anual' },
];

// ── Helpers de formatação ─────────────────────────────────────
function formatDateBR(iso?: string | null): string {
  if (!iso) return '—';
  const parts = iso.substring(0, 10).split('-');
  if (parts.length !== 3) return iso;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function formatDateTimeBR(iso?: string | null): string {
  if (!iso) return '—';
  const date = formatDateBR(iso);
  const time = iso.length >= 16 ? iso.substring(11, 16) : '';
  return time ? `${date} ${time}` : date;
}

function formatBRL(value?: number | null): string {
  if (value === null || value === undefined) return '—';
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B';
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} KB`;
  return `${(kb / 1024).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} MB`;
}

function attachmentIcon(mime: string): React.ComponentType<{ className?: string }> {
  if (mime === 'application/pdf') return FileText;
  if (mime.startsWith('image/')) return Image;
  return File;
}

export default function ClientDetailModal({ client, userRole, onClose, onChanged }: ClientDetailModalProps) {
  const canEdit = ['ADMIN', 'GERENTE'].includes(userRole);
  const todayStr = new Date().toISOString().substring(0, 10);

  const [activeTab, setActiveTab] = useState('overview');
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  // Histórico
  const [interactionType, setInteractionType] = useState('CONVERSA');
  const [interactionContent, setInteractionContent] = useState('');
  const [interactionError, setInteractionError] = useState('');
  const [savingInteraction, setSavingInteraction] = useState(false);

  // Tarefas
  const [users, setUsers] = useState<Array<{ id: string; name: string }>>([]);
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    type: 'LIGACAO',
    start_date: todayStr,
    start_time: '',
    assigned_user_id: '',
  });
  const [taskError, setTaskError] = useState('');
  const [savingTask, setSavingTask] = useState(false);

  // Anexos
  const [file, setFile] = useState<File | null>(null);
  const [uploadKey, setUploadKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  // Produtos / serviços
  const [products, setProducts] = useState<Product[]>([]);
  const [editingItem, setEditingItem] = useState<NegotiationItem | null>(null);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [creatingProduct, setCreatingProduct] = useState(false);
  const [newProductName, setNewProductName] = useState('');
  const [newProductPrice, setNewProductPrice] = useState('');
  const [itemForm, setItemForm] = useState({
    name: '',
    quantity: '1',
    unit_price: '',
    recurrence: 'UNICO',
  });
  const [itemError, setItemError] = useState('');
  const [savingItem, setSavingItem] = useState(false);
  const [creatingProductSaving, setCreatingProductSaving] = useState(false);

  const [shiftingFunnel, setShiftingFunnel] = useState(false);

  const notifyChanged = () => {
    if (onChanged) onChanged();
  };

  const loadDetail = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await clientService.getDetail(client.id);
      setDetail(data);
    } catch (err) {
      setErrorMsg(getApiErrorMessage(err, 'Erro ao carregar o detalhamento do cliente.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [client.id]);

  useEffect(() => {
    if (canEdit) {
      authService
        .getUsers()
        .then(setUsers)
        .catch(() => {
          setUsers([]);
        });
    }
  }, [canEdit]);

  useEffect(() => {
    if (canEdit && activeTab === 'produtos') {
      productService
        .list()
        .then(setProducts)
        .catch(() => {
          setProducts([]);
        });
    }
  }, [canEdit, activeTab]);

  const currentClient = detail?.client || client;
  const stageIdx = FUNNEL_ORDER.indexOf(currentClient.funnel_status);
  const funnelMeta = FUNNEL_META[currentClient.funnel_status] || { label: currentClient.funnel_status, chip: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30' };

  const interactions = detail
    ? [...detail.interactions].sort((a, b) => b.created_at.localeCompare(a.created_at))
    : [];

  const tasks = detail?.events?.filter((ev: any) => ev.client_id === client.id) || [];

  // ── Ações: funil ────────────────────────────────────────────
  const shiftFunnel = async (direction: 'prev' | 'next') => {
    const idx = FUNNEL_ORDER.indexOf(currentClient.funnel_status);
    const next = direction === 'prev' ? FUNNEL_ORDER[idx - 1] : FUNNEL_ORDER[idx + 1];
    if (!next) return;
    setShiftingFunnel(true);
    try {
      await clientService.updateFunnel(client.id, next);
      await loadDetail();
      notifyChanged();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao mover cliente no funil.'));
    } finally {
      setShiftingFunnel(false);
    }
  };

  // ── Ações: histórico ────────────────────────────────────────
  const handleAddInteraction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interactionContent.trim()) {
      setInteractionError('Preencha o conteúdo da interação.');
      return;
    }
    setInteractionError('');
    setSavingInteraction(true);
    try {
      await clientService.createInteraction(client.id, {
        type: interactionType,
        content: interactionContent.trim(),
      });
      await loadDetail();
      notifyChanged();
      setInteractionContent('');
    } catch (err) {
      setInteractionError(getApiErrorMessage(err, 'Erro ao registrar interação.'));
    } finally {
      setSavingInteraction(false);
    }
  };

  const handleDeleteInteraction = async (interaction: any) => {
    if (!confirm('Deseja mesmo remover esta interação do histórico?')) return;
    try {
      await clientService.deleteInteraction(interaction.id);
      await loadDetail();
      notifyChanged();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao remover interação.'));
    }
  };

  // ── Ações: tarefas ──────────────────────────────────────────
  const handleCompleteTask = async (event: any) => {
    try {
      await calendarService.update(event.id, { status: 'CONCLUIDO' });
      await loadDetail();
      notifyChanged();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao concluir tarefa.'));
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskForm.title.trim()) {
      setTaskError('O assunto da tarefa é obrigatório.');
      return;
    }
    if (!taskForm.start_date) {
      setTaskError('A data da tarefa é obrigatória.');
      return;
    }
    setTaskError('');
    setSavingTask(true);
    try {
      await calendarService.create({
        title: taskForm.title.trim(),
        description: taskForm.description.trim(),
        type: taskForm.type,
        status: 'AGENDADO',
        start_date: taskForm.start_date,
        start_time: taskForm.start_time || null,
        client_id: client.id,
        assigned_user_id: taskForm.assigned_user_id || null,
      });
      await loadDetail();
      notifyChanged();
      setTaskForm({
        title: '',
        description: '',
        type: 'LIGACAO',
        start_date: todayStr,
        start_time: '',
        assigned_user_id: '',
      });
    } catch (err) {
      setTaskError(getApiErrorMessage(err, 'Erro ao criar tarefa.'));
    } finally {
      setSavingTask(false);
    }
  };

  // ── Ações: anexos ───────────────────────────────────────────
  const handleDownload = async (attachment: Attachment) => {
    try {
      await attachmentService.download(attachment.id);
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao baixar anexo.'));
    }
  };

  const handleDeleteAttachment = async (attachment: Attachment) => {
    if (!confirm(`Deseja mesmo excluir o anexo "${attachment.filename}"?`)) return;
    try {
      await attachmentService.remove(attachment.id);
      await loadDetail();
      notifyChanged();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir anexo.'));
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploadError('');
    setUploading(true);
    try {
      await attachmentService.upload(client.id, file);
      await loadDetail();
      notifyChanged();
      setFile(null);
      setUploadKey(k => k + 1);
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 413 || /request entity too large/i.test(String(err?.message || ''))) {
        setUploadError('Arquivo muito grande para upload. O limite é de 25 MB.');
      } else {
        setUploadError(getApiErrorMessage(err, 'Erro ao enviar anexo.'));
      }
    } finally {
      setUploading(false);
    }
  };

  // ── Ações: produtos / serviços ─────────────────────────────
  const resetItemForm = () => {
    setItemForm({ name: '', quantity: '1', unit_price: '', recurrence: 'UNICO' });
    setSelectedProductId('');
    setEditingItem(null);
    setCreatingProduct(false);
    setNewProductName('');
    setNewProductPrice('');
    setItemError('');
  };

  const handleProductSelect = (productId: string) => {
    setSelectedProductId(productId);
    const product = products.find(p => p.id === productId);
    if (product) {
      setItemForm(prev => ({
        ...prev,
        name: product.name,
        unit_price: product.default_price != null ? String(product.default_price) : prev.unit_price,
      }));
    }
  };

  const handleEditItem = (item: NegotiationItem) => {
    setEditingItem(item);
    setSelectedProductId('');
    setCreatingProduct(false);
    setItemError('');
    setItemForm({
      name: item.name,
      quantity: String(item.quantity),
      unit_price: String(item.unit_price),
      recurrence: item.recurrence,
    });
  };

  const handleCreateProduct = async () => {
    const name = newProductName.trim();
    if (!name) {
      setItemError('Informe o nome do novo produto.');
      return;
    }
    const price = newProductPrice === '' ? null : Number(newProductPrice);
    if (price !== null && (Number.isNaN(price) || price < 0)) {
      setItemError('O preço padrão deve ser um valor maior ou igual a zero.');
      return;
    }
    setItemError('');
    setCreatingProductSaving(true);
    try {
      const created = await productService.create({ name, default_price: price });
      const updated = await productService.list();
      setProducts(updated);
      setCreatingProduct(false);
      setNewProductName('');
      setNewProductPrice('');
      setSelectedProductId(created.id);
      setItemForm(prev => ({
        ...prev,
        name: created.name,
        unit_price: created.default_price != null ? String(created.default_price) : prev.unit_price,
      }));
    } catch (err) {
      setItemError(getApiErrorMessage(err, 'Erro ao criar produto.'));
    } finally {
      setCreatingProductSaving(false);
    }
  };

  const handleItemSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = itemForm.name.trim();
    if (!name) {
      setItemError('O nome do produto/serviço é obrigatório.');
      return;
    }
    const quantity = Number(itemForm.quantity);
    if (!itemForm.quantity || Number.isNaN(quantity) || quantity <= 0) {
      setItemError('A quantidade deve ser maior que zero.');
      return;
    }
    const unitPrice = Number(itemForm.unit_price);
    if (itemForm.unit_price === '' || Number.isNaN(unitPrice) || unitPrice < 0) {
      setItemError('O preço unitário deve ser um valor maior ou igual a zero.');
      return;
    }
    setItemError('');
    setSavingItem(true);
    try {
      if (editingItem) {
        await itemService.update(editingItem.id, {
          name,
          quantity,
          unit_price: unitPrice,
          recurrence: itemForm.recurrence,
        });
      } else {
        await itemService.create(client.id, {
          product_id: selectedProductId || null,
          name,
          quantity,
          unit_price: unitPrice,
          recurrence: itemForm.recurrence,
        });
      }
      await loadDetail();
      notifyChanged();
      resetItemForm();
    } catch (err) {
      setItemError(getApiErrorMessage(err, 'Erro ao salvar produto/serviço.'));
    } finally {
      setSavingItem(false);
    }
  };

  const handleDeleteItem = async (item: NegotiationItem) => {
    if (!confirm(`Deseja mesmo excluir "${item.name}" da negociação?`)) return;
    try {
      await itemService.remove(item.id);
      await loadDetail();
      notifyChanged();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir produto/serviço.'));
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="glass-panel w-full max-w-3xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 p-5 border-b border-zinc-800 shrink-0">
          <div className="flex justify-between items-start gap-4">
            <div className="min-w-0">
              <h3 className="text-lg font-serif font-semibold text-white truncate">{currentClient.name}</h3>
              <p className="text-xs text-zinc-400 font-mono mt-0.5 space-x-3">
                {currentClient.email && <span>✉ {currentClient.email}</span>}
                {currentClient.phone && <span>📞 {currentClient.phone}</span>}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {canEdit && (
                <button
                  onClick={onClose}
                  title="Editar cadastro na tela de clientes"
                  className="p-2 text-zinc-400 hover:text-blue-400 rounded border border-zinc-800 hover:bg-zinc-900 cursor-pointer"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={onClose}
                className="text-zinc-500 hover:text-white transition font-mono text-xs uppercase px-2 py-1 rounded hover:bg-zinc-900 cursor-pointer"
              >
                Sair
              </button>
            </div>
          </div>
          {/* Chips */}
          <div className="flex flex-wrap items-center gap-1.5 mt-3">
            <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${funnelMeta.chip}`}>
              {funnelMeta.label}
            </span>
            {currentClient.lead_source && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded text-zinc-300 bg-zinc-500/10 border border-zinc-500/30">
                Fonte: {currentClient.lead_source}
              </span>
            )}
            {currentClient.campaign && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded text-zinc-300 bg-zinc-500/10 border border-zinc-500/30">
                Campanha: {currentClient.campaign}
              </span>
            )}
            {currentClient.estimated_value != null && (
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded text-emerald-300 bg-emerald-500/10 border border-emerald-500/30">
                {formatBRL(currentClient.estimated_value)}
              </span>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="px-5 pt-4 pb-0 shrink-0">
          <div className="bg-zinc-900 border border-zinc-800 p-1 rounded-md flex">
            {TABS.map(tab => {
              const TabIcon = tab.icon;
              const isActive = activeTab === tab.id;
              const count = tab.id === 'history' ? interactions.length : tab.id === 'tasks' ? tasks.length : tab.id === 'attachments' ? (detail?.attachments.length || 0) : tab.id === 'produtos' ? (detail?.items.length || 0) : 0;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-3 py-1.5 rounded text-xs font-mono transition flex items-center justify-center gap-1.5 cursor-pointer ${
                    isActive ? 'bg-red-600 text-white font-bold' : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  <TabIcon className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{tab.label}</span>
                  {count > 0 && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${isActive ? 'bg-white/20' : 'bg-zinc-800 text-zinc-400'}`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
              <p className="text-zinc-400 font-mono text-xs">Carregando detalhes do cliente...</p>
            </div>
          ) : errorMsg ? (
            <div className="p-4 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
              {errorMsg}
              <button
                onClick={loadDetail}
                className="ml-3 text-red-300 underline cursor-pointer"
              >
                Tentar novamente
              </button>
            </div>
          ) : !detail ? (
            <div className="py-16 text-center text-zinc-500 font-mono text-xs">Nenhum dado disponível.</div>
          ) : (
            <>
              {/* ── ABA 1: Visão Geral ── */}
              {activeTab === 'overview' && (
                <div className="space-y-5">
                  {/* Dados cadastrais */}
                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">Dados Cadastrais</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase block">CPF / CNPJ</span>
                        <span className="text-zinc-200 font-mono text-xs">{currentClient.cpf_cnpj || '—'}</span>
                      </div>
                      <div>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase block">Criado em</span>
                        <span className="text-zinc-200 font-mono text-xs">{formatDateBR(currentClient.created_at)}</span>
                      </div>
                      <div className="sm:col-span-2">
                        <span className="text-[10px] font-mono text-zinc-500 uppercase block">Endereço</span>
                        <span className="text-zinc-200 text-xs">{currentClient.address || 'Não cadastrado'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Negociação */}
                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">Negociação</h4>
                    <div className="flex flex-wrap items-center gap-4">
                      <div>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase block">Valor Estimado</span>
                        <span className="text-sm text-emerald-400 font-mono font-semibold">{formatBRL(currentClient.estimated_value)}</span>
                      </div>
                      <div>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase block">Valor de Itens</span>
                        <span className="text-sm text-emerald-400 font-mono font-semibold">{formatBRL(currentClient.negotiation_value)}</span>
                      </div>
                      <div className="flex items-center gap-2 ml-auto">
                        <button
                          onClick={() => shiftFunnel('prev')}
                          disabled={stageIdx <= 0 || shiftingFunnel}
                          className="p-1.5 text-zinc-400 hover:text-white disabled:opacity-20 border border-zinc-800 rounded hover:bg-zinc-900 cursor-pointer"
                          title="Recuar etapa"
                        >
                          <ArrowLeft className="w-4 h-4" />
                        </button>
                        <span className={`text-[10px] font-mono font-semibold px-2 py-1 rounded ${funnelMeta.chip}`}>
                          {funnelMeta.label}
                        </span>
                        <button
                          onClick={() => shiftFunnel('next')}
                          disabled={stageIdx < 0 || stageIdx >= FUNNEL_ORDER.length - 1 || shiftingFunnel}
                          className="p-1.5 text-zinc-400 hover:text-white disabled:opacity-20 border border-zinc-800 rounded hover:bg-zinc-900 cursor-pointer"
                          title="Avançar etapa"
                        >
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    {currentClient.funnel_status === 'PERDIDO' && (
                      <div className="mt-3 p-3 bg-red-950/40 border border-red-900/60 rounded text-xs text-red-300 font-mono">
                        Motivo da perda: {currentClient.lost_reason || 'Não informado'}
                      </div>
                    )}
                  </div>

                  {/* Projetos vinculados */}
                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">
                      Projetos Vinculados ({detail.projects.length})
                    </h4>
                    {detail.projects.length === 0 ? (
                      <p className="text-xs text-zinc-500 font-mono">Nenhum projeto vinculado a este cliente.</p>
                    ) : (
                      <div className="divide-y divide-zinc-900">
                        {detail.projects.map(project => (
                          <div key={project.id} className="py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-zinc-100 truncate">{project.title}</p>
                              <p className="text-[11px] text-zinc-500 font-mono">Prazo: {formatDateBR(project.deadline)}</p>
                            </div>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${PROJECT_STATUS_META[project.status]?.chip || 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30'}`}>
                              {PROJECT_STATUS_META[project.status]?.label || project.status}
                            </span>
                            <span className="text-xs font-mono text-emerald-400 font-semibold">
                              {formatBRL(project.value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── ABA 2: Histórico ── */}
              {activeTab === 'history' && (
                <div className="space-y-4">
                  {canEdit && (
                    <form onSubmit={handleAddInteraction} className="glass-panel rounded-lg p-4 border border-zinc-900 space-y-3">
                      <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider">Registrar Interação</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Tipo</label>
                          <select
                            value={interactionType}
                            onChange={e => setInteractionType(e.target.value)}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          >
                            {INTERACTION_FORM_TYPES.map(t => (
                              <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                          </select>
                        </div>
                        <div className="sm:col-span-2 space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Conteúdo *</label>
                          <textarea
                            value={interactionContent}
                            onChange={e => setInteractionContent(e.target.value)}
                            rows={2}
                            placeholder="Descreva o contato com o cliente..."
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 resize-none"
                          />
                        </div>
                      </div>
                      {interactionError && <p className="text-xs text-red-400 font-mono">{interactionError}</p>}
                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={savingInteraction}
                          className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold transition active:scale-95 disabled:opacity-50 cursor-pointer"
                        >
                          {savingInteraction ? 'Salvando...' : 'Registrar'}
                        </button>
                      </div>
                    </form>
                  )}

                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">
                      Timeline ({interactions.length})
                    </h4>
                    {interactions.length === 0 ? (
                      <p className="text-xs text-zinc-500 font-mono">Nenhuma interação registrada.</p>
                    ) : (
                      <div className="space-y-3">
                        {interactions.map(interaction => {
                          const meta = INTERACTION_META[interaction.type] || {
                            label: interaction.type,
                            badge: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30',
                          };
                          return (
                            <div key={interaction.id} className="flex gap-3 items-start">
                              <div className="w-px self-stretch bg-zinc-800 shrink-0 ml-1" />
                              <div className="flex-1 min-w-0 bg-zinc-950/60 border border-zinc-900 rounded-lg p-3">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${meta.badge}`}>
                                    {meta.label}
                                  </span>
                                  <span className="text-[11px] text-zinc-500 font-mono ml-auto">
                                    {interaction.created_by || 'sistema'} · {formatDateTimeBR(interaction.created_at)}
                                  </span>
                                  {canEdit && (
                                    <button
                                      onClick={() => handleDeleteInteraction(interaction)}
                                      className="p-1 text-zinc-500 hover:text-red-400 cursor-pointer"
                                      title="Excluir interação"
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                  )}
                                </div>
                                <p className="text-sm text-zinc-200 mt-1.5 leading-relaxed whitespace-pre-wrap">{interaction.content}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── ABA 3: Tarefas ── */}
              {activeTab === 'tasks' && (
                <div className="space-y-4">
                  {canEdit && (
                    <form onSubmit={handleCreateTask} className="glass-panel rounded-lg p-4 border border-zinc-900 space-y-3">
                      <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider">Nova Tarefa</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="space-y-1.5 sm:col-span-2">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Assunto *</label>
                          <input
                            type="text"
                            value={taskForm.title}
                            onChange={e => setTaskForm({ ...taskForm, title: e.target.value })}
                            placeholder="Ex: Ligar para confirmar orçamento"
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Tipo</label>
                          <select
                            value={taskForm.type}
                            onChange={e => setTaskForm({ ...taskForm, type: e.target.value })}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          >
                            {TASK_FORM_TYPES.map(t => (
                              <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Responsável</label>
                          <select
                            value={taskForm.assigned_user_id}
                            onChange={e => setTaskForm({ ...taskForm, assigned_user_id: e.target.value })}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          >
                            <option value="">Não definido</option>
                            {users.map(user => (
                              <option key={user.id} value={user.id}>{user.name}</option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Data *</label>
                          <input
                            type="date"
                            value={taskForm.start_date}
                            onChange={e => setTaskForm({ ...taskForm, start_date: e.target.value })}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 font-mono"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Horário</label>
                          <input
                            type="time"
                            value={taskForm.start_time}
                            onChange={e => setTaskForm({ ...taskForm, start_time: e.target.value })}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 font-mono"
                          />
                        </div>
                        <div className="space-y-1.5 sm:col-span-2">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Descrição</label>
                          <textarea
                            value={taskForm.description}
                            onChange={e => setTaskForm({ ...taskForm, description: e.target.value })}
                            rows={2}
                            placeholder="Detalhes da tarefa (opcional)"
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 resize-none"
                          />
                        </div>
                      </div>
                      {taskError && <p className="text-xs text-red-400 font-mono">{taskError}</p>}
                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={savingTask}
                          className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold transition active:scale-95 disabled:opacity-50 cursor-pointer"
                        >
                          {savingTask ? 'Criando...' : 'Criar Tarefa'}
                        </button>
                      </div>
                    </form>
                  )}

                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">
                      Tarefas ({tasks.length})
                    </h4>
                    {tasks.length === 0 ? (
                      <p className="text-xs text-zinc-500 font-mono">Nenhuma tarefa vinculada a este cliente.</p>
                    ) : (
                      <div className="space-y-2.5">
                        {tasks.map((event: any) => {
                          const typeMeta = TASK_TYPE_META[event.type] || {
                            label: event.type,
                            chip: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30',
                          };
                          const statusMeta = TASK_STATUS_META[event.status] || {
                            label: event.status,
                            chip: 'text-zinc-300 bg-zinc-500/10 border border-zinc-500/30',
                          };
                          const dateStr = event.start_date ? event.start_date.substring(0, 10) : '';
                          const notDone = event.status !== 'CONCLUIDO';
                          const isOverdue = notDone && dateStr < todayStr;
                          const isToday = notDone && dateStr === todayStr;
                          return (
                            <div
                              key={event.id}
                              className={`p-3 bg-zinc-950/60 border rounded-lg transition ${
                                isOverdue
                                  ? 'border-red-900/70 bg-red-950/10'
                                  : isToday
                                    ? 'border-amber-800/60 bg-amber-950/10'
                                    : 'border-zinc-900'
                              }`}
                            >
                              <div className="flex items-start gap-2 flex-wrap">
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-sm font-semibold text-zinc-100">{event.title}</span>
                                    {isOverdue && (
                                      <span className="text-[9px] font-mono font-bold uppercase text-red-400 bg-red-950/60 border border-red-900 px-1.5 py-0.5 rounded">
                                        Atrasada
                                      </span>
                                    )}
                                    {isToday && (
                                      <span className="text-[9px] font-mono font-bold uppercase text-amber-300 bg-amber-950/60 border border-amber-800 px-1.5 py-0.5 rounded">
                                        Hoje
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2 flex-wrap mt-1">
                                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${typeMeta.chip}`}>
                                      {typeMeta.label}
                                    </span>
                                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${statusMeta.chip}`}>
                                      {statusMeta.label}
                                    </span>
                                    <span className="text-[11px] text-zinc-500 font-mono">
                                      {formatDateBR(event.start_date)}
                                      {event.start_time ? ` ${event.start_time.substring(0, 5)}` : ''}
                                    </span>
                                    {event.assigned_user_name && (
                                      <span className="text-[11px] text-zinc-500 font-mono">👷 {event.assigned_user_name}</span>
                                    )}
                                  </div>
                                </div>
                                {notDone && (
                                  <button
                                    onClick={() => handleCompleteTask(event)}
                                    className="text-[11px] font-mono font-semibold px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded transition active:scale-95 cursor-pointer shrink-0"
                                    title="Marcar como concluída"
                                  >
                                    Concluir
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── ABA 4: Anexos ── */}
              {activeTab === 'attachments' && (
                <div className="space-y-4">
                  {canEdit && (
                    <form onSubmit={handleUpload} className="glass-panel rounded-lg p-4 border border-zinc-900 space-y-3">
                      <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider">Enviar Anexo</h4>
                      <div className="flex flex-col sm:flex-row gap-3">
                        <input
                          key={uploadKey}
                          type="file"
                          accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.dwg,.zip"
                          onChange={e => setFile(e.target.files?.[0] || null)}
                          className="flex-1 text-xs text-zinc-400 file:mr-3 file:px-3 file:py-2 file:text-xs file:font-mono file:text-white file:bg-zinc-900 file:border file:border-zinc-800 file:rounded file:cursor-pointer cursor-pointer"
                        />
                        <button
                          type="submit"
                          disabled={!file || uploading}
                          className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold transition active:scale-95 disabled:opacity-50 cursor-pointer flex items-center gap-1.5 justify-center"
                        >
                          <Upload className="w-4 h-4" />
                          {uploading ? 'Enviando...' : 'Enviar'}
                        </button>
                      </div>
                      {uploadError && <p className="text-xs text-red-400 font-mono">{uploadError}</p>}
                      <p className="text-[10px] text-zinc-600 font-mono">
                        Formatos aceitos: PDF, PNG, JPG, DOC, DOCX, XLS, XLSX, DWG, ZIP · limite de 25 MB
                      </p>
                    </form>
                  )}

                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">
                      Anexos ({detail.attachments.length})
                    </h4>
                    {detail.attachments.length === 0 ? (
                      <p className="text-xs text-zinc-500 font-mono">Nenhum anexo enviado.</p>
                    ) : (
                      <div className="divide-y divide-zinc-900">
                        {detail.attachments.map(attachment => {
                          const Icon = attachmentIcon(attachment.mime_type);
                          return (
                            <div key={attachment.id} className="py-3 flex items-center gap-3">
                              <span className="p-2 bg-zinc-900 border border-zinc-800 rounded text-zinc-300 shrink-0">
                                <Icon className="w-4 h-4" />
                              </span>
                              <div className="min-w-0 flex-1">
                                <p className="text-sm text-zinc-100 truncate" title={attachment.filename}>
                                  {attachment.filename}
                                </p>
                                <p className="text-[11px] text-zinc-500 font-mono">
                                  {formatFileSize(attachment.size)} · {attachment.created_by || 'sistema'} ·{' '}
                                  {formatDateBR(attachment.created_at)}
                                </p>
                              </div>
                              <div className="flex gap-1 shrink-0">
                                <button
                                  onClick={() => handleDownload(attachment)}
                                  className="p-1.5 text-zinc-400 hover:text-emerald-400 cursor-pointer"
                                  title="Baixar anexo"
                                >
                                  <Download className="w-4 h-4" />
                                </button>
                                {canEdit && (
                                  <button
                                    onClick={() => handleDeleteAttachment(attachment)}
                                    className="p-1.5 text-zinc-400 hover:text-red-400 cursor-pointer"
                                    title="Excluir anexo"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── ABA 5: Produtos / Serviços ── */}
              {activeTab === 'produtos' && (
                <div className="space-y-4">
                  {canEdit && (
                    <form onSubmit={handleItemSubmit} className="glass-panel rounded-lg p-4 border border-zinc-900 space-y-3">
                      <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider">
                        {editingItem ? 'Editar Produto/Serviço' : 'Adicionar Produto/Serviço'}
                      </h4>

                      {!editingItem && (
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Produto pré-cadastrado</label>
                          <select
                            value={creatingProduct ? '__new__' : selectedProductId}
                            onChange={e => {
                              if (e.target.value === '__new__') {
                                setCreatingProduct(true);
                                setSelectedProductId('');
                              } else {
                                setCreatingProduct(false);
                                handleProductSelect(e.target.value);
                              }
                            }}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          >
                            <option value="">— Nenhum —</option>
                            {products.map(product => (
                              <option key={product.id} value={product.id}>{product.name}</option>
                            ))}
                            <option value="__new__">+ Criar novo produto...</option>
                          </select>
                          {creatingProduct && (
                            <div className="mt-2 p-3 bg-zinc-950/60 border border-zinc-800 rounded space-y-2">
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                <input
                                  type="text"
                                  value={newProductName}
                                  onChange={e => setNewProductName(e.target.value)}
                                  placeholder="Nome do novo produto *"
                                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                                />
                                <input
                                  type="number"
                                  min="0"
                                  step="0.01"
                                  value={newProductPrice}
                                  onChange={e => setNewProductPrice(e.target.value)}
                                  placeholder="Preço padrão (R$)"
                                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 font-mono"
                                />
                              </div>
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={handleCreateProduct}
                                  disabled={creatingProductSaving}
                                  className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded font-semibold transition active:scale-95 disabled:opacity-50 cursor-pointer flex items-center gap-1"
                                >
                                  <Plus className="w-3.5 h-3.5" />
                                  {creatingProductSaving ? 'Criando...' : 'Confirmar'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setCreatingProduct(false);
                                    setNewProductName('');
                                    setNewProductPrice('');
                                    setItemError('');
                                  }}
                                  className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded font-semibold transition active:scale-95 cursor-pointer"
                                >
                                  Cancelar
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="sm:col-span-3 space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Nome *</label>
                          <input
                            type="text"
                            value={itemForm.name}
                            onChange={e => setItemForm({ ...itemForm, name: e.target.value })}
                            placeholder="Ex: Armário planejado 2,40m"
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Quantidade *</label>
                          <input
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={itemForm.quantity}
                            onChange={e => setItemForm({ ...itemForm, quantity: e.target.value })}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 font-mono"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Preço unitário (R$) *</label>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={itemForm.unit_price}
                            onChange={e => setItemForm({ ...itemForm, unit_price: e.target.value })}
                            placeholder="0,00"
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600 font-mono"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] text-zinc-300 font-mono uppercase block">Recorrência</label>
                          <select
                            value={itemForm.recurrence}
                            onChange={e => setItemForm({ ...itemForm, recurrence: e.target.value })}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-red-600"
                          >
                            {RECURRENCE_OPTIONS.map(opt => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {itemError && <p className="text-xs text-red-400 font-mono">{itemError}</p>}

                      <div className="flex justify-end gap-2">
                        {editingItem && (
                          <button
                            type="button"
                            onClick={resetItemForm}
                            className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded font-semibold transition active:scale-95 cursor-pointer"
                          >
                            Cancelar edição
                          </button>
                        )}
                        <button
                          type="submit"
                          disabled={savingItem}
                          className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold transition active:scale-95 disabled:opacity-50 cursor-pointer"
                        >
                          {savingItem ? 'Salvando...' : editingItem ? 'Salvar Alterações' : 'Adicionar'}
                        </button>
                      </div>
                    </form>
                  )}

                  <div className="glass-panel rounded-lg p-4 border border-zinc-900">
                    <h4 className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider mb-3">
                      Produtos/Serviços ({detail.items.length})
                    </h4>
                    {detail.items.length === 0 ? (
                      <p className="text-xs text-zinc-500 font-mono">Nenhum produto ou serviço adicionado à negociação.</p>
                    ) : (
                      <div className="divide-y divide-zinc-900">
                        {detail.items.map(item => (
                          <div key={item.id} className="py-3 flex items-center gap-3">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-zinc-100 truncate">{item.name}</p>
                              <p className="text-[11px] text-zinc-500 font-mono">
                                {item.quantity} x {formatBRL(item.unit_price)}
                              </p>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded text-cyan-300 bg-cyan-500/10 border border-cyan-500/30 shrink-0">
                              {RECURRENCE_LABELS[item.recurrence] || item.recurrence}
                            </span>
                            <span className="text-xs font-mono text-emerald-400 font-semibold shrink-0">
                              {formatBRL(item.subtotal)}
                            </span>
                            {canEdit && (
                              <div className="flex gap-1 shrink-0">
                                <button
                                  onClick={() => handleEditItem(item)}
                                  className="p-1.5 text-zinc-400 hover:text-blue-400 cursor-pointer"
                                  title="Editar"
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleDeleteItem(item)}
                                  className="p-1.5 text-zinc-400 hover:text-red-400 cursor-pointer"
                                  title="Excluir"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="mt-4 pt-3 border-t border-zinc-800 flex items-center justify-between">
                      <span className="text-[11px] uppercase font-mono text-zinc-500 tracking-wider">Total da Negociação</span>
                      <span className="text-lg font-mono font-bold text-emerald-400">
                        {formatBRL(detail.items.reduce((sum, item) => sum + (item.subtotal || 0), 0))}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}