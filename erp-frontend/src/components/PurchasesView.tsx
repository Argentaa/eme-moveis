import React, { useEffect, useMemo, useState } from 'react';
import {
  ShoppingCart,
  Package,
  Plus,
  Trash2,
  Truck,
  Check,
  Edit3,
  Search,
  Eye,
  X,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  CalendarDays,
  DollarSign,
  Award,
  BarChart3,
  Clock,
  BadgePercent,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import { purchaseService, supplierService, vendorService, stockService, getApiErrorMessage } from '../services/api';
import { PurchaseOrder, Vendor, StockItem } from '../types';

import ModuleTabs, { ModuleTab, ActiveTabPlaceholder, useModuleTab } from './ModuleTabs';
import QuotationsPanel from './QuotationsPanel';
import LogisticsPanel from './LogisticsPanel';

/** Abas do módulo Compras, conforme a spec do cliente (17/09). */
const PURCHASES_TABS: ModuleTab[] = [
  { id: 'dashboard', label: 'Dashboard', ready: true },
  { id: 'quotes', label: 'Cotações', ready: true },
  { id: 'orders', label: 'Compras', ready: true },
  { id: 'logistics', label: 'Calendário logístico', ready: true },
];

interface PurchasesViewProps {
  userRole: string;
}

type FormItem = {
  stock_item_id: string | null;
  material_name: string;
  quantity: string;
  unit_price: string;
};

type FormData = {
  supplier_id: string;
  request_date: string;
  expected_date: string;
  notes: string;
  status: string;
  items: FormItem[];
};
const STATUS_OPTIONS_CREATE = ['SOLICITADA', 'COTANDO', 'APROVADA', 'COMPRADA'] as const;
const STATUS_OPTIONS_ALL = ['SOLICITADA', 'COTANDO', 'APROVADA', 'COMPRADA', 'RECEBIDA', 'CANCELADA'] as const;
const FILTER_OPTIONS = ['TODOS', ...STATUS_OPTIONS_ALL] as const;

const STATUS_COLORS: Record<string, string> = {
  SOLICITADA: '#71717a',
  COTANDO: '#f59e0b',
  APROVADA: '#0ea5e9',
  COMPRADA: '#8b5cf6',
  RECEBIDA: '#10b981',
  CANCELADA: '#ef4444',
};

function getStatusBadge(status: string): string {
  switch (status) {
    case 'SOLICITADA':
      return 'bg-zinc-800 text-zinc-300 border-zinc-700';
    case 'COTANDO':
      return 'bg-amber-950/40 text-amber-400 border-amber-900/40';
    case 'APROVADA':
      return 'bg-sky-950/40 text-sky-400 border-sky-900/40';
    case 'COMPRADA':
      return 'bg-violet-950/40 text-violet-400 border-violet-900/40';
    case 'RECEBIDA':
      return 'bg-emerald-950/40 text-emerald-400 border-emerald-900/40';
    case 'CANCELADA':
      return 'bg-red-950/40 text-red-400 border-red-900/40';
    default:
      return 'bg-zinc-800 text-zinc-300 border-zinc-700';
  }
}

function formatBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleDateString('pt-BR');
  } catch {
    return value;
  }
}

const todayISO = () => new Date().toISOString().substring(0, 10);

const emptyFormData = (): FormData => ({
  supplier_id: '',
  request_date: todayISO(),
  expected_date: '',
  notes: '',
  status: 'SOLICITADA',
  items: [{ stock_item_id: null, material_name: '', quantity: '1', unit_price: '0' }],
});

export default function PurchasesView({ userRole }: PurchasesViewProps) {
  const allowedRoles = ['ADMIN', 'GERENTE', 'ESTOQUE'];
  const canManage = allowedRoles.includes(userRole);

  const [activeTab, setActiveTab] = useModuleTab('purchases', PURCHASES_TABS, 'dashboard');
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Vendor[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [filterStatus, setFilterStatus] = useState<string>('TODOS');
  const [searchQuery, setSearchQuery] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>(emptyFormData());
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [supplierFilter, setSupplierFilter] = useState('');

  const [detailOrder, setDetailOrder] = useState<PurchaseOrder | null>(null);

  // supplier inline creation
  const [isSupplierModalOpen, setIsSupplierModalOpen] = useState(false);
  const [newSupplierName, setNewSupplierName] = useState('');
  const [newSupplierCnpj, setNewSupplierCnpj] = useState('');
  const [supplierError, setSupplierError] = useState('');
  const [supplierSaving, setSupplierSaving] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [o, s, st] = await Promise.all([
        purchaseService.list(),
        vendorService.list().catch(() => [] as Vendor[]),
        stockService.getAll().catch(() => [] as StockItem[]),
      ]);
      setOrders(o);
      setSuppliers(s);
      setStockItems(st);
    } catch (err) {
      console.error('Erro ao carregar compras:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      const matchesStatus = filterStatus === 'TODOS' || o.status === filterStatus;
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        o.number.toLowerCase().includes(q) ||
        (o.supplier_name && o.supplier_name.toLowerCase().includes(q)) ||
        (o.notes && o.notes.toLowerCase().includes(q));
      return matchesStatus && matchesSearch;
    });
  }, [orders, filterStatus, searchQuery]);

  // ── Dashboard metrics (fiel ao DASHBOARD do Sheets) ───────────────
  const dashboard = useMemo(() => {
    const now = new Date();
    const curMonth = now.getMonth();
    const curYear = now.getFullYear();
    const monthStr = `${curYear}-${String(curMonth + 1).padStart(2, '0')}`;

    const ordersMonth = orders.filter(o => o.request_date && o.request_date.startsWith(monthStr));
    const ordersYear = orders.filter(o => o.request_date && o.request_date.startsWith(String(curYear)));
    // Sheets: Cotações Aprovadas = COUNTIF(L="Aprovada") → no ERP = status APROVADA
    const cotacoesAprovadas = orders.filter(o => o.status === 'APROVADA');
    // Sheets: Em aberto + Recebida → no ERP = COTANDO + SOLICITADA
    const cotacoesAndamento = orders.filter(o => ['COTANDO','SOLICITADA'].includes(o.status));
    const quotations = orders.filter(o => o.status === 'COTANDO');

    const totalMonth = ordersMonth.reduce((a, o) => a + (o.total || 0), 0);
    const totalYear = ordersYear.reduce((a, o) => a + (o.total || 0), 0);
    const totalAll = orders.reduce((a, o) => a + (o.total || 0), 0);

    const ticketMedioMonth = ordersMonth.length ? totalMonth / ordersMonth.length : 0;
    const ticketMedioAll = orders.length ? totalAll / orders.length : 0;

    // Sheets: Pedidos em Aberto = COUNTA(H) - Recebido - Cancelado → no ERP = não RECEBIDA/CANCELADA
    const pedidosAbertos = orders.filter(o => !['RECEBIDA','CANCELADA'].includes(o.status));
    // Sheets: Pedidos Atrasados = COUNTIF(H="Atrasado") → no ERP = expected_date < hoje e não recebido/cancelado
    const today = todayISO();
    const pedidosAtrasados = orders.filter(o => {
      if (['RECEBIDA','CANCELADA'].includes(o.status)) return false;
      if (!o.expected_date) return false;
      return o.expected_date < today;
    });

    // Valor Economizado — Sheets: SUM(O) onde O = MAX(grupo)-J quando K=🏆
    // Agora existe tabela de cotacoes: onde o pedido TEM cotacao, a economia e
    // MEDIDA (saving_real do backend, mesma formula da planilha). Onde nao tem,
    // cai no proxy de catalogo (stock.price) e fica contado como estimativa.
    // Nunca somar os dois no mesmo pedido — seria contar a mesma compra duas vezes.
    const stockMap = new Map<string, number>();
    stockItems.forEach(s => stockMap.set(s.id, Number(s.price || 0)));

    let totalSaving = 0;      // medida + estimada
    let savingReal = 0;       // so a medida por cotacao
    let savingEstimado = 0;   // so o proxy de catalogo
    let savingCount = 0;
    let sumRecommended = 0; // para Economia % = SUM(O)/SUMIFS(J,K=🏆)
    orders.forEach(o => {
      if (['APROVADA', 'COMPRADA', 'RECEBIDA'].includes(o.status)) {
        if ((o.quotations_count || 0) > 0) {
          const medida = Number(o.saving_real || 0);
          totalSaving += medida;
          savingReal += medida;
          savingCount += Number(o.saving_real_items || 0);
          if (medida > 0) sumRecommended += (o.total || 0);
          return;
        }
        let orderSaving = 0;
        o.items.forEach(it => {
          if (it.stock_item_id && stockMap.has(it.stock_item_id)) {
            const catalog = stockMap.get(it.stock_item_id)!;
            const diff = (catalog - Number(it.unit_price || 0)) * Number(it.quantity || 0);
            if (diff > 0) { orderSaving += diff; savingCount += 1; }
          }
        });
        totalSaving += orderSaving;
        savingEstimado += orderSaving;
        if (orderSaving > 0) sumRecommended += (o.total || 0);
      }
    });
    const economiaPercent = sumRecommended ? (totalSaving / sumRecommended) * 100 : 0;

    // Fornecedores Ativos — Sheets: COUNTIF(O="Ativo") → no ERP por ora = todos (status ainda não existe)
    const fornecedoresAtivos = suppliers.length;
    // Fornecedores Críticos — Sheets: COUNTIF(AD="*Crítico*") (classificação D) → ERP sem avaliação, proxy 0
    const fornecedoresCriticos = 0;
    // Prazo Médio Entrega — Sheets: AVERAGE('CALENDÁRIO'!N) → proxy = AVG(avg_delivery_days)
    const prazos = suppliers.map(s => s.avg_delivery_days).filter(v => v != null) as number[];
    const prazoMedioEntrega = prazos.length ? prazos.reduce((a,b)=>a+b,0)/prazos.length : 0;
    // % Entregas no Prazo — Sheets: COUNTIF(H="Recebido") → no ERP = RECEBIDA / total
    const recebidos = orders.filter(o => o.status === 'RECEBIDA').length;
    const percEntregasNoPrazo = orders.length ? (recebidos / orders.length) * 100 : 0;
    // Ticket Médio — Sheets: AVERAGEIF(A<>"",E)
    const ticketMedio = ticketMedioAll;
    // Prazo Real de Entrega — Sheets: AVG(F-D) onde F=Data Real Entrega
    const withDelivery = orders.filter(o => o.received_at && o.request_date);
    const prazoRealEntrega = withDelivery.length ? (
      withDelivery.reduce((acc,o) => {
        const d1 = new Date(o.request_date).getTime();
        const d2 = new Date(o.received_at!).getTime();
        return acc + (d2 - d1) / (1000*60*60*24);
      }, 0) / withDelivery.length
    ) : 0;
    // Fornecedores sem Avaliação — Sheets: COUNTIFS(O=Ativo, AC="") → proxy = ativos sem avg_delivery_days
    const fornecedoresSemAvaliacao = suppliers.filter(s => s.avg_delivery_days == null).length;

    // Compras por Fornecedor (top 5)
    const bySupplier = new Map<string, { name: string; total: number; count: number }>();
    orders.forEach(o => {
      const key = o.supplier_id || '__sem__';
      const name = o.supplier_name || 'Sem fornecedor';
      const entry = bySupplier.get(key) || { name, total: 0, count: 0 };
      entry.total += (o.total || 0);
      entry.count += 1;
      entry.name = name;
      bySupplier.set(key, entry);
    });
    const supplierRanking = Array.from(bySupplier.values()).sort((a,b) => b.total - a.total).slice(0, 5);

    // Compras por Status
    const byStatus = STATUS_OPTIONS_ALL.map(s => ({
      status: s,
      count: orders.filter(o => o.status === s).length,
      total: orders.filter(o => o.status === s).reduce((a,o) => a + (o.total||0), 0),
    }));

    // Compras por mês no ano (12 meses)
    const months = Array.from({ length: 12 }, (_, i) => {
      const m = String(i + 1).padStart(2, '0');
      const prefix = `${curYear}-${m}`;
      const list = orders.filter(o => o.request_date && o.request_date.startsWith(prefix));
      return {
        mes: new Date(curYear, i, 1).toLocaleDateString('pt-BR', { month: 'short' }),
        total: list.reduce((a,o) => a + (o.total||0), 0),
        qtd: list.length,
      };
    });

    return {
      ordersMonth, ordersYear, quotations, cotacoesAprovadas, cotacoesAndamento,
      totalMonth, totalYear, totalAll,
      ticketMedioMonth, ticketMedioAll, ticketMedio,
      totalSaving, economiaPercent, savingCount, sumRecommended,
      savingReal, savingEstimado,
      pedidosAbertos, pedidosAtrasados,
      fornecedoresAtivos, fornecedoresCriticos, prazoMedioEntrega, percEntregasNoPrazo, prazoRealEntrega, fornecedoresSemAvaliacao,
      recebidos,
      supplierRanking, byStatus, months,
      curMonth, curYear
    };
  }, [orders, suppliers, stockItems]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setFormData(emptyFormData());
    setSubmitError('');
    setSupplierFilter('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (order: PurchaseOrder) => {
    setEditingId(order.id);
    setFormData({
      supplier_id: order.supplier_id || '',
      request_date: order.request_date ? order.request_date.substring(0, 10) : todayISO(),
      expected_date: order.expected_date ? order.expected_date.substring(0, 10) : '',
      notes: order.notes || '',
      status: order.status,
      items:
        order.items.length > 0
          ? order.items.map((it) => ({
              stock_item_id: it.stock_item_id,
              material_name: it.material_name,
              quantity: String(it.quantity),
              unit_price: String(it.unit_price),
            }))
          : [{ stock_item_id: null, material_name: '', quantity: '1', unit_price: '0' }],
    });
    setSubmitError('');
    setIsModalOpen(true);
    setDetailOrder(null);
  };

  const handleOpenDetail = (order: PurchaseOrder) => {
    setDetailOrder(order);
  };

  const handleDelete = async (order: PurchaseOrder) => {
    if (order.status === 'RECEBIDA') {
      alert('Pedidos recebidos não podem ser excluídos.');
      return;
    }
    if (!confirm(`Excluir o pedido ${order.number}?`)) return;
    try {
      await purchaseService.remove(order.id);
      await loadData();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir pedido.'));
    }
  };

  const handleReceive = async (order: PurchaseOrder) => {
    if (!['APROVADA', 'COMPRADA'].includes(order.status)) {
      alert('Apenas pedidos APROVADA ou COMPRADA podem ser recebidos.');
      return;
    }
    if (!confirm(`Confirmar recebimento do pedido ${order.number}? O estoque será atualizado.`)) return;
    try {
      await purchaseService.receive(order.id);
      await loadData();
      if (detailOrder && detailOrder.id === order.id) {
        try {
          const updated = await purchaseService.get(order.id);
          setDetailOrder(updated);
        } catch {
          setDetailOrder(null);
        }
      }
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao receber pedido.'));
    }
  };

  const handleAddItem = () => {
    setFormData((prev) => ({
      ...prev,
      items: [...prev.items, { stock_item_id: null, material_name: '', quantity: '1', unit_price: '0' }],
    }));
  };

  const handleRemoveItem = (idx: number) => {
    setFormData((prev) => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== idx),
    }));
  };

  const handleItemChange = (idx: number, field: keyof FormItem, value: string) => {
    setFormData((prev) => {
      const items = [...prev.items];
      (items[idx] as any)[field] = value;
      return { ...prev, items };
    });
  };

  const handleStockSelect = (idx: number, stockId: string) => {
    if (!stockId) {
      setFormData((prev) => {
        const items = [...prev.items];
        items[idx] = { ...items[idx], stock_item_id: null };
        return { ...prev, items };
      });
      return;
    }
    const found = stockItems.find((s) => s.id === stockId);
    if (found) {
      setFormData((prev) => {
        const items = [...prev.items];
        items[idx] = {
          ...items[idx],
          stock_item_id: found.id,
          material_name: found.name,
          unit_price: String(found.price ?? 0),
        };
        return { ...prev, items };
      });
    }
  };

  const handleCreateSupplierInline = async (e: React.FormEvent) => {
    e.preventDefault();
    setSupplierError('');
    if (!newSupplierName.trim()) { setSupplierError('Nome é obrigatório.'); return; }
    setSupplierSaving(true);
    try {
      const sup = await supplierService.create({ name: newSupplierName.trim(), cnpj: newSupplierCnpj.trim() || undefined });
      // Recarrega a lista unificada (inclui espelhos de clientes-fornecedores)
      vendorService.list().then(v => setSuppliers(v)).catch(() => {
        setSuppliers(prev => [...prev, { ...sup, source: 'supplier' as const }].sort((a,b) => a.name.localeCompare(b.name)));
      });
      setFormData(prev => ({ ...prev, supplier_id: sup.id }));
      setIsSupplierModalOpen(false);
      setNewSupplierName('');
      setNewSupplierCnpj('');
    } catch (err) {
      setSupplierError(getApiErrorMessage(err, 'Erro ao criar fornecedor.'));
    } finally { setSupplierSaving(false); }
  };

  const totalGeral = useMemo(() => {
    return formData.items.reduce((acc, it) => {
      const q = Number(it.quantity) || 0;
      const p = Number(it.unit_price) || 0;
      return acc + q * p;
    }, 0);
  }, [formData.items]);

  const filteredSuppliersForSelect = useMemo(() => {
    const q = supplierFilter.trim().toLowerCase();
    if (!q) return suppliers;
    return suppliers.filter(s => s.name.toLowerCase().includes(q) || (s.cnpj||'').toLowerCase().includes(q));
  }, [suppliers, supplierFilter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    if (formData.items.length === 0) {
      setSubmitError('Adicione pelo menos 1 item ao pedido.');
      return;
    }
    for (const it of formData.items) {
      if (!it.material_name.trim()) {
        setSubmitError('Informe o nome do material em todos os itens.');
        return;
      }
      const q = Number(it.quantity);
      if (!q || q <= 0) {
        setSubmitError('Quantidade deve ser maior que 0 em todos os itens.');
        return;
      }
    }

    const payload = {
      supplier_id: formData.supplier_id || null,
      request_date: formData.request_date,
      expected_date: formData.expected_date || null,
      notes: formData.notes || '',
      status: formData.status,
      items: formData.items.map((it) => ({
        stock_item_id: it.stock_item_id || null,
        material_name: it.material_name.trim(),
        quantity: Number(it.quantity) || 0,
        unit_price: Number(it.unit_price) || 0,
      })),
    };

    setSubmitting(true);
    try {
      if (editingId) {
        await purchaseService.update(editingId, payload);
      } else {
        await purchaseService.create(payload);
      }
      setIsModalOpen(false);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setSubmitError(getApiErrorMessage(err, editingId ? 'Erro ao atualizar pedido.' : 'Erro ao criar pedido.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (!canManage) {
    return (
      <div className="glass-panel p-8 rounded-lg text-center border border-zinc-800">
        <ShieldAlert className="w-10 h-10 text-zinc-500 mx-auto mb-3" />
        <p className="text-zinc-400 font-mono text-sm">Sem acesso a Compras.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide flex items-center gap-3">
            <ShoppingCart className="w-7 h-7 text-zinc-400" /> Compras
          </h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Pedidos de compra, cotações e recebimento no estoque.</p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold px-4 py-2.5 rounded shadow flex items-center gap-2 transition active:scale-95 cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Novo Pedido
        </button>
      </div>

      {/* Sub-tabs do módulo — lista completa da spec do cliente (17/09) */}
      <ModuleTabs tabs={PURCHASES_TABS} active={activeTab} onChange={setActiveTab} />
      <ActiveTabPlaceholder tabs={PURCHASES_TABS} active={activeTab} />

      {activeTab === 'dashboard' && (<>

      {/* ── Dashboard de Compras (fiel ao DASHBOARD do Sheets) ─────────── */}
      <div className="space-y-4">
        {/* Linha 1 — DASHBOARD A7/M7: Compras Mês/Ano + Cotações */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-white">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">💵 Compras do Mês</span>
              <p className="text-xl font-bold font-sans text-white mt-1">{dashboard.ordersMonth.length} pedidos</p>
              <p className="text-sm font-bold font-mono text-emerald-400">{formatBRL(dashboard.totalMonth)}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Ticket médio: {formatBRL(dashboard.ticketMedioMonth)}</span>
              <span className="text-[10px] text-zinc-600 font-mono">Sheets: SUMIFS mês atual</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-zinc-300 border border-zinc-900"><CalendarDays className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-sky-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">💰 Compras no Ano {dashboard.curYear}</span>
              <p className="text-xl font-bold font-sans text-sky-400 mt-1">{dashboard.ordersYear.length} pedidos</p>
              <p className="text-sm font-bold font-mono text-white">{formatBRL(dashboard.totalYear)}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Total acumulado: {formatBRL(dashboard.totalAll)}</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-sky-500 border border-zinc-900"><BarChart3 className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-emerald-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">✅ Cotações Aprovadas</span>
              <p className="text-xl font-bold font-sans text-emerald-400 mt-1">{dashboard.cotacoesAprovadas.length}</p>
              <p className="text-xs font-mono text-zinc-400 mt-1">Sheets: COUNTIF COTAÇÕES=L Aprovada</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">ERP: status APROVADA</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-emerald-500 border border-zinc-900"><Check className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-amber-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">💬 Cotações em Andamento</span>
              <p className="text-xl font-bold font-sans text-amber-400 mt-1">{dashboard.cotacoesAndamento.length}</p>
              <p className="text-xs font-mono text-zinc-400 mt-1">Sheets: Em aberto + Recebida</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">ERP: COTANDO+SOLICITADA</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-amber-500 border border-zinc-900"><BadgePercent className="w-5 h-5" /></div>
          </div>
        </div>

        {/* Linha 2 — DASHBOARD A11/M11: Pedidos + Economia */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-zinc-500">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">🧾 Pedidos em Aberto</span>
              <p className="text-xl font-bold font-sans text-white mt-1">{dashboard.pedidosAbertos.length}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: -Recebido -Cancelado</span>
              <p className="text-[10px] text-zinc-600 font-mono">ERP: ≠ RECEBIDA/CANCELADA</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-zinc-400 border border-zinc-900"><Package className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-red-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">🔴 Pedidos Atrasados</span>
              <p className="text-xl font-bold font-sans text-red-400 mt-1">{dashboard.pedidosAtrasados.length}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: COUNTIF Atrasado</span>
              <p className="text-[10px] text-zinc-600 font-mono">ERP: expected_date &lt; hoje</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-red-500 border border-zinc-900"><Clock className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-violet-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1"><Award className="w-3 h-3" /> 📉 Valor Economizado</span>
              <p className="text-xl font-bold font-sans text-violet-400 mt-1">{formatBRL(dashboard.totalSaving)}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">
                {dashboard.savingReal > 0 && (
                  <>{formatBRL(dashboard.savingReal)} medidos por cotação</>
                )}
                {dashboard.savingReal > 0 && dashboard.savingEstimado > 0 && ' + '}
                {dashboard.savingEstimado > 0 && (
                  <>{formatBRL(dashboard.savingEstimado)} estimados vs catálogo</>
                )}
                {dashboard.savingReal === 0 && dashboard.savingEstimado === 0 && 'sem compras comparáveis ainda'}
              </span>
              <p className="text-[10px] text-zinc-600 font-mono">Sheets: SUM(O) cotação máx-mín</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-violet-400 border border-zinc-900"><TrendingUp className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-emerald-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">📊 Economia %</span>
              <p className="text-xl font-bold font-sans text-emerald-400 mt-1">{dashboard.economiaPercent.toFixed(1)}%</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: SUM(O)/SUMIFS(J,🏆)</span>
              <p className="text-[10px] text-zinc-600 font-mono">ERP proxy: vs catálogo</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-emerald-500 border border-zinc-900"><BadgePercent className="w-5 h-5" /></div>
          </div>
        </div>

        {/* Linha 3 — DASHBOARD A15/M15 + A19/I19 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-sky-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">🏭 Fornecedores Ativos</span>
              <p className="text-xl font-bold font-sans text-sky-400 mt-1">{dashboard.fornecedoresAtivos}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: COUNTIF Ativo</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-sky-500 border border-zinc-900"><Truck className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-zinc-400">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">⚠ Fornecedores Críticos</span>
              <p className="text-xl font-bold font-sans text-zinc-300 mt-1">{dashboard.fornecedoresCriticos}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: AD=*Crítico*</span>
              <p className="text-[10px] text-zinc-600 font-mono">* Requer avaliação</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-zinc-400 border border-zinc-900"><ShieldAlert className="w-3 h-3" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-amber-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">🚚 Prazo Médio Entrega</span>
              <p className="text-xl font-bold font-sans text-amber-400 mt-1">{dashboard.prazoMedioEntrega ? `${dashboard.prazoMedioEntrega.toFixed(1)} dias` : '—'}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: AVG CAL!N</span>
              <p className="text-[10px] text-zinc-600 font-mono">ERP: AVG avg_delivery_days</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-amber-500 border border-zinc-900"><Clock className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-emerald-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">✅ % Entregas no Prazo</span>
              <p className="text-xl font-bold font-sans text-emerald-400 mt-1">{dashboard.percEntregasNoPrazo.toFixed(0)}%</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">{dashboard.recebidos} Recebidos / {orders.length}</span>
              <p className="text-[10px] text-zinc-600 font-mono">Sheets: COUNTIF Recebido</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-emerald-500 border border-zinc-900"><Check className="w-5 h-5" /></div>
          </div>
        </div>

        {/* Linha 4 — DASHBOARD A19/I19: Ticket Médio, Prazo Real, Sem Avaliação */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-white">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">🎟️ Ticket Médio por Compra</span>
              <p className="text-xl font-bold font-sans text-white mt-1">{formatBRL(dashboard.ticketMedio)}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: AVERAGEIF(A&lt;&gt;"",E)</span>
              <p className="text-[10px] text-zinc-600 font-mono">Média de {orders.length} pedidos</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-zinc-300 border border-zinc-900"><DollarSign className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-zinc-500">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">⏱️ Prazo Real Entrega</span>
              <p className="text-xl font-bold font-sans text-white mt-1">{dashboard.prazoRealEntrega ? `${dashboard.prazoRealEntrega.toFixed(1)} dias` : '—'}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: AVG(F-D)</span>
              <p className="text-[10px] text-zinc-600 font-mono">{dashboard.recebidos} entregas com data</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-zinc-400 border border-zinc-900"><Clock className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-amber-600">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">🧑‍🔧 Fornecedores sem Avaliação</span>
              <p className="text-xl font-bold font-sans text-amber-400 mt-1">{dashboard.fornecedoresSemAvaliacao}</p>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Sheets: COUNTIFS Ativo+AC=""</span>
              <p className="text-[10px] text-zinc-600 font-mono">ERP proxy: sem prazo</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-amber-500 border border-zinc-900"><Truck className="w-5 h-5" /></div>
          </div>
          <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-zinc-500">
            <div>
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1"><Clock className="w-3 h-3" /> Status dos Pedidos</span>
              <div className="flex flex-wrap gap-1 mt-2">
                {dashboard.byStatus.map(s => s.count > 0 && (
                  <span key={s.status} className={`inline-flex px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${getStatusBadge(s.status)}`}>{s.status}: {s.count}</span>
                ))}
              </div>
              <span className="text-[10px] text-zinc-500 font-mono block mt-1">{orders.length} pedidos no total</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded text-zinc-400 border border-zinc-900"><Package className="w-5 h-5" /></div>
          </div>
        </div>

        {/* Gráficos */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Compras por mês no ano */}
          <div className="glass-panel p-5 rounded-lg border border-zinc-800 lg:col-span-2">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2"><BarChart3 className="w-4 h-4 text-zinc-400" /> Compras por Mês — {dashboard.curYear}</h3>
            <p className="text-[11px] font-mono text-zinc-500 mb-3">Valor total (R$) e quantidade por mês</p>
            <div className="h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dashboard.months}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="mes" tick={{ fill: '#a1a1aa', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={(v) => `R$${(v/1000).toFixed(0)}k`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                    labelStyle={{ color: '#fff' }}
                    formatter={(value: any, name: string) => [name === 'total' ? formatBRL(value as number) : value, name === 'total' ? 'Valor' : 'Qtd']}
                  />
                  <Legend />
                  <Bar dataKey="total" name="Valor" fill="#e4e4e7" radius={[4,4,0,0]} />
                  <Bar dataKey="qtd" name="Qtd pedidos" fill="#71717a" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Compras por Fornecedor */}
          <div className="glass-panel p-5 rounded-lg border border-zinc-800">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2"><Truck className="w-4 h-4 text-zinc-400" /> Compras por Fornecedor</h3>
            <p className="text-[11px] font-mono text-zinc-500 mb-3">Top 5 por valor total</p>
            {dashboard.supplierRanking.length === 0 ? (
              <p className="text-xs text-zinc-500 font-mono py-8 text-center">Sem dados de fornecedor.</p>
            ) : (
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dashboard.supplierRanking} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis type="number" tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={(v)=>`R$${(v/1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="name" width={110} tick={{ fill: '#e4e4e7', fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={(v:any)=>formatBRL(v as number)} />
                    <Bar dataKey="total" fill="#38bdf8" radius={[0,4,4,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-3 space-y-1">
              {dashboard.supplierRanking.map(s => (
                <div key={s.name} className="flex justify-between text-[11px] font-mono text-zinc-400">
                  <span className="truncate pr-2">{s.name}</span>
                  <span className="text-white font-bold">{formatBRL(s.total)} <span className="text-zinc-500 font-normal">({s.count})</span></span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Status pizza */}
          <div className="glass-panel p-5 rounded-lg border border-zinc-800">
            <h3 className="text-sm font-semibold text-white">Distribuição por Status</h3>
            <p className="text-[11px] font-mono text-zinc-500 mb-2">Quantidade de pedidos por status</p>
            <div className="h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dashboard.byStatus.filter(d=>d.count>0)} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={80} label={({ status, count }) => `${status} ${count}`}>
                    {dashboard.byStatus.filter(d=>d.count>0).map(entry => (
                      <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || '#52525b'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Ticket médio linha? reuse line chart for total per supplier? or status totals */}
          <div className="glass-panel p-5 rounded-lg border border-zinc-800">
            <h3 className="text-sm font-semibold text-white">Valor por Status</h3>
            <p className="text-[11px] font-mono text-zinc-500 mb-3">Soma em R$ por status</p>
            <div className="h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dashboard.byStatus}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="status" tick={{ fill: '#a1a1aa', fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={50} />
                  <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={(v)=>`R$${(v/1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={(v:any)=>formatBRL(v as number)} />
                  <Bar dataKey="total" radius={[4,4,0,0]}>
                    {dashboard.byStatus.map(entry => (
                      <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || '#52525b'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      </>)}

      {activeTab === 'quotes' && (<QuotationsPanel />)}

      {activeTab === 'logistics' && (<LogisticsPanel />)}

      {activeTab === 'orders' && (<>

      {/* Filters */}
      <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center bg-zinc-900 border border-zinc-800">
        <div className="relative w-full md:flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
          <input
            type="text"
            placeholder="Buscar por número, fornecedor ou observação..."
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
          <p className="text-zinc-400 font-mono text-xs">Carregando pedidos...</p>
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="glass-panel p-12 rounded-lg text-center border border-zinc-800 bg-zinc-900">
          <Package className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <p className="text-zinc-500 font-mono text-sm">Nenhum pedido encontrado.</p>
          {orders.length === 0 && <p className="text-zinc-600 font-mono text-xs mt-1">Crie seu primeiro pedido de compra.</p>}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block glass-panel rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-zinc-500 bg-zinc-950/60 border-b border-zinc-800 font-mono">
                  <tr>
                    <th className="py-3 px-4 font-normal">Número</th>
                    <th className="py-3 px-4 font-normal">Fornecedor</th>
                    <th className="py-3 px-4 font-normal">Status</th>
                    <th className="py-3 px-4 font-normal">Solicitação</th>
                    <th className="py-3 px-4 font-normal text-right">Total</th>
                    <th className="py-3 px-4 font-normal text-center">Itens</th>
                    <th className="py-3 px-4 font-normal text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-sm">
                  {filteredOrders.map((order) => (
                    <tr key={order.id} className="hover:bg-zinc-800/30">
                      <td className="py-3 px-4 font-mono font-semibold text-white">{order.number}</td>
                      <td className="py-3 px-4 text-zinc-300">{order.supplier_name || '-'}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex px-2.5 py-0.5 text-[10px] font-bold uppercase rounded-full border ${getStatusBadge(order.status)}`}>
                          {order.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-zinc-400 font-mono text-xs">{formatDate(order.request_date)}</td>
                      <td className="py-3 px-4 text-right font-mono text-white">{formatBRL(order.total ?? 0)}</td>
                      <td className="py-3 px-4 text-center text-zinc-400">{order.items.length}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleOpenDetail(order)}
                            className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 transition cursor-pointer"
                            title="Ver detalhes"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleOpenEdit(order)}
                            className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 transition cursor-pointer"
                            title="Editar"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          {order.status !== 'RECEBIDA' && (
                            <button
                              onClick={() => handleDelete(order)}
                              className="p-1.5 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 transition cursor-pointer"
                              title="Excluir"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {['APROVADA', 'COMPRADA'].includes(order.status) && (
                            <button
                              onClick={() => handleReceive(order)}
                              className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold flex items-center gap-1 transition cursor-pointer"
                              title="Receber pedido"
                            >
                              <Truck className="w-3.5 h-3.5" /> Receber
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
            {filteredOrders.map((order) => (
              <div key={order.id} className="glass-panel p-4 rounded-lg border border-zinc-800 bg-zinc-900">
                <div className="flex justify-between items-start">
                  <span className="font-mono font-bold text-white text-sm">{order.number}</span>
                  <span className={`inline-flex px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${getStatusBadge(order.status)}`}>
                    {order.status}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">{order.supplier_name || 'Sem fornecedor'}</p>
                <div className="mt-3 flex justify-between items-end">
                  <div>
                    <span className="text-[10px] font-mono text-zinc-500 uppercase block">Solicitação</span>
                    <span className="text-xs font-mono text-zinc-300">{formatDate(order.request_date)}</span>
                    <span className="text-[10px] font-mono text-zinc-500 uppercase block mt-1">Total</span>
                    <span className="text-sm font-bold text-white font-mono">{formatBRL(order.total ?? 0)}</span>
                    <span className="text-xs text-zinc-500 font-mono"> · {order.items.length} {order.items.length === 1 ? 'item' : 'itens'}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 justify-end max-w-[55%]">
                    <button
                      onClick={() => handleOpenDetail(order)}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 cursor-pointer"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleOpenEdit(order)}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 cursor-pointer"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    {order.status !== 'RECEBIDA' && (
                      <button
                        onClick={() => handleDelete(order)}
                        className="p-2 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    {['APROVADA', 'COMPRADA'].includes(order.status) && (
                      <button
                        onClick={() => handleReceive(order)}
                        className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold flex items-center gap-1 cursor-pointer"
                      >
                        <Truck className="w-4 h-4" /> Receber
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      </>)}

      {/* Modal Novo/Editar */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setIsModalOpen(false)}>
          <div className="glass-panel w-full max-w-2xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[92vh] flex flex-col bg-zinc-900" onClick={e => e.stopPropagation()}>
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5" />
                  {editingId ? `Editar ${orders.find((o) => o.id === editingId)?.number || 'Pedido'}` : 'Novo Pedido'}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">Fornecedor deve estar pré-cadastrado em Clientes/Fornecedores · Use a busca</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="p-2 text-zinc-500 hover:text-white rounded cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1 overscroll-contain">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{submitError}</div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider flex items-center gap-2">Fornecedor <span className="text-[10px] text-zinc-500 normal-case">(pré-cadastro)</span></label>
                  <div className="flex gap-2">
                    <div className="flex-1 space-y-1">
                      <input
                        type="text"
                        value={supplierFilter}
                        onChange={e => setSupplierFilter(e.target.value)}
                        placeholder="Buscar fornecedor... (digite para filtrar)"
                        className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-1.5 text-xs rounded focus:outline-none focus:border-zinc-600 font-sans"
                      />
                      <select
                        value={formData.supplier_id}
                        onChange={(e) => setFormData((p) => ({ ...p, supplier_id: e.target.value }))}
                        className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                      >
                        <option value="">Selecione (opcional) — {filteredSuppliersForSelect.length} encontrado(s)</option>
                        {filteredSuppliersForSelect.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name} {s.cnpj ? `· ${s.cnpj}` : ''}
                          </option>
                        ))}
                      </select>
                      {suppliers.length === 0 && <p className="text-[11px] text-amber-500 font-mono">Nenhum fornecedor cadastrado. Cadastre em Clientes/Fornecedores ou use o botão +.</p>}
                    </div>
                    <button
                      type="button"
                      onClick={() => { setNewSupplierName(supplierFilter); setNewSupplierCnpj(''); setSupplierError(''); setIsSupplierModalOpen(true); }}
                      className="h-fit mt-[26px] p-2.5 bg-zinc-800 hover:bg-emerald-950/40 text-zinc-400 hover:text-emerald-400 rounded border border-zinc-700 transition cursor-pointer"
                      title="Cadastrar fornecedor rápido"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-[11px] text-zinc-500 font-mono">Dica: Gerencie fornecedores em Clientes/Fornecedores.</p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData((p) => ({ ...p, status: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    {(editingId ? STATUS_OPTIONS_ALL : STATUS_OPTIONS_CREATE).map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Data solicitação</label>
                  <input
                    type="date"
                    value={formData.request_date}
                    onChange={(e) => setFormData((p) => ({ ...p, request_date: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Previsão entrega</label>
                  <input
                    type="date"
                    value={formData.expected_date}
                    onChange={(e) => setFormData((p) => ({ ...p, expected_date: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Observações</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData((p) => ({ ...p, notes: e.target.value }))}
                  rows={2}
                  placeholder="Observações do pedido..."
                  className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 resize-none"
                />
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Itens do pedido</label>
                  <button
                    type="button"
                    onClick={handleAddItem}
                    className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-white text-xs rounded flex items-center gap-1 border border-zinc-700 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Adicionar Item
                  </button>
                </div>

                {formData.items.map((item, idx) => {
                  const lineTotal = (Number(item.quantity) || 0) * (Number(item.unit_price) || 0);
                  return (
                    <div key={idx} className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[10px] text-zinc-500 font-mono uppercase">Material do estoque</label>
                          <select
                            value={item.stock_item_id || ''}
                            onChange={(e) => handleStockSelect(idx, e.target.value)}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white px-2 py-1.5 text-xs rounded focus:outline-none focus:border-zinc-700"
                          >
                            <option value="">Material livre / digitar abaixo</option>
                            {stockItems.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.name} — {s.sku}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-zinc-500 font-mono uppercase">Nome do material *</label>
                          <input
                            type="text"
                            value={item.material_name}
                            onChange={(e) => handleItemChange(idx, 'material_name', e.target.value)}
                            placeholder="Ex: MDF 15mm branco"
                            className="w-full bg-zinc-900 border border-zinc-800 text-white px-2 py-1.5 text-xs rounded focus:outline-none focus:border-zinc-700"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 items-end">
                        <div className="space-y-1">
                          <label className="text-[10px] text-zinc-500 font-mono uppercase">Qtd *</label>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={item.quantity}
                            onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white px-2 py-1.5 text-xs rounded focus:outline-none focus:border-zinc-700"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-zinc-500 font-mono uppercase">Preço unit.</label>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={item.unit_price}
                            onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white px-2 py-1.5 text-xs rounded focus:outline-none focus:border-zinc-700"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-2">
                          <div className="text-xs font-mono text-zinc-300">
                            <span className="text-[10px] text-zinc-500 uppercase block">Total</span>
                            {formatBRL(lineTotal)}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(idx)}
                            disabled={formData.items.length <= 1}
                            className="p-1.5 bg-zinc-900 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                            title="Remover item"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}

                <div className="flex justify-end pt-2 border-t border-zinc-800">
                  <div className="text-right">
                    <span className="text-xs font-mono text-zinc-500 uppercase">Total geral</span>
                    <p className="text-lg font-bold text-white font-mono">{formatBRL(totalGeral)}</p>
                  </div>
                </div>
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

      {/* Modal fornecedor inline */}
      {isSupplierModalOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" onClick={() => setIsSupplierModalOpen(false)}>
          <div className="glass-panel w-full max-w-sm rounded-xl overflow-hidden border border-zinc-800 shadow-2xl bg-zinc-900" onClick={e => e.stopPropagation()}>
            <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 p-5 border-b border-zinc-800 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Truck className="w-5 h-5 text-emerald-500" />
                <h3 className="text-base font-serif font-semibold text-white">Novo Fornecedor</h3>
              </div>
              <button onClick={() => setIsSupplierModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateSupplierInline} className="p-6 space-y-4">
              {supplierError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{supplierError}</div>
              )}
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nome do Fornecedor *</label>
                <input
                  type="text"
                  required
                  value={newSupplierName}
                  onChange={(e) => setNewSupplierName(e.target.value)}
                  placeholder="Ex: Madeireira Sul"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">CNPJ (opcional)</label>
                <input
                  type="text"
                  value={newSupplierCnpj}
                  onChange={(e) => setNewSupplierCnpj(e.target.value)}
                  placeholder="00.000.000/0000-00"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                />
              </div>
              <p className="text-[11px] text-zinc-500 font-mono">Você poderá completar dados em Clientes/Fornecedores.</p>
              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button type="button" onClick={() => setIsSupplierModalOpen(false)} className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono">
                  Cancelar
                </button>
                <button type="submit" disabled={supplierSaving} className="px-5 py-2 text-sm bg-emerald-700 hover:bg-emerald-600 text-white rounded font-semibold cursor-pointer disabled:opacity-50 flex items-center gap-2">
                  {supplierSaving ? <><RefreshCw className="w-4 h-4 animate-spin" /> Criando...</> : 'Criar Fornecedor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Detalhe */}
      {detailOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setDetailOrder(null)}>
          <div className="glass-panel w-full max-w-2xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col bg-zinc-900" onClick={e => e.stopPropagation()}>
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2">
                  <Package className="w-5 h-5" /> {detailOrder.number}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">
                  {detailOrder.supplier_name || 'Sem fornecedor'} · Solicitado em {formatDate(detailOrder.request_date)}
                  {detailOrder.expected_date ? ` · Previsão ${formatDate(detailOrder.expected_date)}` : ''}
                  {detailOrder.received_at ? ` · Recebido em ${formatDate(detailOrder.received_at)}` : ''}
                </p>
              </div>
              <button onClick={() => setDetailOrder(null)} className="p-2 text-zinc-500 hover:text-white rounded cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto">
              <div className="flex flex-wrap gap-2 items-center">
                <span className={`inline-flex px-2.5 py-1 text-xs font-bold uppercase rounded-full border ${getStatusBadge(detailOrder.status)}`}>
                  {detailOrder.status}
                </span>
                <span className="text-xs font-mono text-zinc-400">Total: <span className="text-white font-bold">{formatBRL(detailOrder.total ?? 0)}</span></span>
                <span className="text-xs font-mono text-zinc-400">{detailOrder.items.length} {detailOrder.items.length === 1 ? 'item' : 'itens'}</span>
              </div>

              {detailOrder.notes && (
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-300 font-mono">
                  <span className="text-zinc-500 uppercase text-[10px] block mb-1">Observações</span>
                  {detailOrder.notes}
                </div>
              )}

              <div className="border border-zinc-800 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-950 text-zinc-500 font-mono uppercase">
                    <tr>
                      <th className="py-2 px-3 font-normal">#</th>
                      <th className="py-2 px-3 font-normal">Material</th>
                      <th className="py-2 px-3 font-normal text-right">Qtd</th>
                      <th className="py-2 px-3 font-normal text-right">Recebido</th>
                      <th className="py-2 px-3 font-normal text-right">Unit.</th>
                      <th className="py-2 px-3 font-normal text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {detailOrder.items.map((it) => (
                      <tr key={it.id} className="hover:bg-zinc-800/20">
                        <td className="py-2 px-3 text-zinc-500 font-mono">{it.position}</td>
                        <td className="py-2 px-3 text-white font-medium">{it.material_name}</td>
                        <td className="py-2 px-3 text-right font-mono text-zinc-300">{it.quantity}</td>
                        <td className="py-2 px-3 text-right font-mono text-emerald-400">{it.received_qty}</td>
                        <td className="py-2 px-3 text-right font-mono text-zinc-300">{formatBRL(it.unit_price)}</td>
                        <td className="py-2 px-3 text-right font-mono text-white">{formatBRL(it.total ?? it.quantity * it.unit_price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <button
                  onClick={() => {
                    const o = detailOrder;
                    setDetailOrder(null);
                    handleOpenEdit(o);
                  }}
                  className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 flex items-center gap-2 cursor-pointer"
                >
                  <Edit3 className="w-4 h-4" /> Editar
                </button>
                {['APROVADA', 'COMPRADA'].includes(detailOrder.status) && (
                  <button
                    onClick={() => handleReceive(detailOrder)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded flex items-center gap-2 cursor-pointer"
                  >
                    <Truck className="w-4 h-4" /> Receber pedido
                  </button>
                )}
                <button
                  onClick={() => setDetailOrder(null)}
                  className="px-4 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded cursor-pointer"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
