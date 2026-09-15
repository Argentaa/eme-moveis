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
} from 'lucide-react';
import { purchaseService, supplierService, stockService, getApiErrorMessage } from '../services/api';
import { PurchaseOrder, Supplier, StockItem } from '../types';

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

  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [filterStatus, setFilterStatus] = useState<string>('TODOS');
  const [searchQuery, setSearchQuery] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>(emptyFormData());
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [detailOrder, setDetailOrder] = useState<PurchaseOrder | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [o, s, st] = await Promise.all([
        purchaseService.list(),
        supplierService.getAll().catch(() => [] as Supplier[]),
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

  const handleOpenCreate = () => {
    setEditingId(null);
    setFormData(emptyFormData());
    setSubmitError('');
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
      handleItemChange(idx, 'stock_item_id', '' as any);
      // keep material_name as is for free material
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

  const totalGeral = useMemo(() => {
    return formData.items.reduce((acc, it) => {
      const q = Number(it.quantity) || 0;
      const p = Number(it.unit_price) || 0;
      return acc + q * p;
    }, 0);
  }, [formData.items]);

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
          <p className="text-sm text-zinc-400 font-mono mt-1">Pedidos de compra e recebimento no estoque.</p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold px-4 py-2.5 rounded shadow flex items-center gap-2 transition active:scale-95 cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Novo Pedido
        </button>
      </div>

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

      {/* Modal Novo/Editar */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-2xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col bg-zinc-900">
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5" />
                  {editingId ? `Editar ${orders.find((o) => o.id === editingId)?.number || 'Pedido'}` : 'Novo Pedido'}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">Preencha os dados do pedido de compra</p>
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
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider">Fornecedor</label>
                  <select
                    value={formData.supplier_id}
                    onChange={(e) => setFormData((p) => ({ ...p, supplier_id: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700"
                  >
                    <option value="">Selecione (opcional)</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
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

                      <div className="grid grid-cols-3 gap-3 items-end">
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

      {/* Modal Detalhe */}
      {detailOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-2xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col bg-zinc-900">
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
