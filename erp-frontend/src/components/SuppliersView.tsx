import React, { useEffect, useMemo, useState } from 'react';
import { Truck, Plus, Search, Edit3, Trash2, RefreshCw, ShieldAlert, Building2, Package, CreditCard, Clock, Mail, Phone, X } from 'lucide-react';
import { supplierService, purchaseService, clientService, getApiErrorMessage } from '../services/api';
import { Supplier, Client, PurchaseOrder } from '../types';

interface SuppliersViewProps {
  userRole: string;
}

const emptyForm = {
  name: '',
  cnpj: '',
  contact: '',
  phone: '',
  email: '',
  address: '',
  category: '',
  payment_terms: '',
  avg_delivery_days: '',
};

export default function SuppliersView({ userRole }: SuppliersViewProps) {
  const canManage = ['ADMIN', 'GERENTE', 'ESTOQUE'].includes(userRole);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('TODOS');
  // Abas do cadastro central: todos os clientes, fornecedores e clientes-fornecedores
  const [activeTab, setActiveTab] = useState<'ALL' | 'SUPPLIERS' | 'CLIENTS'>('ALL');
  const [clientSuppliers, setClientSuppliers] = useState<Client[]>([]);
  const [allClients, setAllClients] = useState<Client[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [submitError, setSubmitError] = useState('');
  const [saving, setSaving] = useState(false);
  // CRUD de clientes no cadastro central (todo cadastro nasce aqui, fora do funil)
  const emptyClientForm = {
    name: '',
    cpf_cnpj: '',
    email: '',
    phone: '',
    address: '',
    contact: '',
    category: '',
    is_supplier: false,
  };
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [editingClientId, setEditingClientId] = useState<string | null>(null);
  const [clientForm, setClientForm] = useState(emptyClientForm);
  const [clientSubmitError, setClientSubmitError] = useState('');
  const [clientSaving, setClientSaving] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sups, ords, cliSups, allCli] = await Promise.all([
        supplierService.getAll().catch(() => [] as Supplier[]),
        purchaseService.list().catch(() => [] as PurchaseOrder[]),
        clientService.getAll({ is_supplier: '1' }).catch(() => [] as Client[]),
        clientService.getAll().catch(() => [] as Client[]),
      ]);
      setSuppliers(sups);
      setOrders(ords as PurchaseOrder[]);
      setClientSuppliers(cliSups);
      setAllClients(allCli);
    } finally { setLoading(false); }
  };

  useEffect(() => { loadData(); }, []);

  const categories = useMemo(() => {
    const cats = Array.from(new Set(suppliers.map(s => s.category).filter(Boolean) as string[]));
    return cats.sort();
  }, [suppliers]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return suppliers.filter(s => {
      const matchesCat = categoryFilter === 'TODOS' || s.category === categoryFilter;
      if (!q) return matchesCat;
      const matchesSearch = s.name.toLowerCase().includes(q) || (s.cnpj || '').toLowerCase().includes(q) || (s.contact || '').toLowerCase().includes(q) || (s.email || '').toLowerCase().includes(q);
      return matchesCat && matchesSearch;
    });
  }, [suppliers, search, categoryFilter]);

  const filteredClients = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return clientSuppliers;
    return clientSuppliers.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.cpf_cnpj || '').toLowerCase().includes(q) ||
      (c.email || '').toLowerCase().includes(q) ||
      (c.phone || '').toLowerCase().includes(q)
    );
  }, [clientSuppliers, search]);

  const filteredAllClients = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return allClients;
    return allClients.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.cpf_cnpj || '').toLowerCase().includes(q) ||
      (c.email || '').toLowerCase().includes(q) ||
      (c.phone || '').toLowerCase().includes(q)
    );
  }, [allClients, search]);

  const handleOpenCreateClient = () => {
    setEditingClientId(null);
    setClientForm(emptyClientForm);
    setClientSubmitError('');
    setIsClientModalOpen(true);
  };

  const handleOpenEditClient = (c: Client) => {
    setEditingClientId(c.id);
    setClientForm({
      name: c.name || '',
      cpf_cnpj: c.cpf_cnpj || '',
      email: c.email || '',
      phone: c.phone || '',
      address: c.address || '',
      contact: (c as any).contact || '',
      category: (c as any).category || '',
      is_supplier: !!(c as any).is_supplier,
    });
    setClientSubmitError('');
    setIsClientModalOpen(true);
  };

  const handleClientDelete = async (c: Client) => {
    if (!confirm(`Excluir cliente "${c.name}" do cadastro central?`)) return;
    try {
      await clientService.delete(c.id);
      await loadData();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Falha ao remover cliente.'));
    }
  };

  const handleClientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientSubmitError('');
    if (!clientForm.name.trim()) {
      setClientSubmitError('Nome é obrigatório.');
      return;
    }
    if (clientForm.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(clientForm.email.trim())) {
      setClientSubmitError('E-mail inválido.');
      return;
    }
    setClientSaving(true);
    try {
      if (editingClientId) {
        await clientService.update(editingClientId, {
          name: clientForm.name.trim(),
          cpf_cnpj: clientForm.cpf_cnpj.trim() || undefined,
          email: clientForm.email.trim(),
          phone: clientForm.phone.trim(),
          address: clientForm.address.trim(),
          contact: clientForm.contact.trim(),
          category: clientForm.category.trim(),
          is_supplier: clientForm.is_supplier,
        } as any);
      } else {
        // Cadastro central nasce FORA do funil (funnel_id null explicito);
        // o Comercial importa depois via "Vincular Cliente".
        await clientService.create({
          name: clientForm.name.trim(),
          cpf_cnpj: clientForm.cpf_cnpj.trim() || undefined,
          email: clientForm.email.trim(),
          phone: clientForm.phone.trim(),
          address: clientForm.address.trim(),
          contact: clientForm.contact.trim(),
          category: clientForm.category.trim(),
          is_supplier: clientForm.is_supplier,
          funnel_id: null,
        } as any);
      }
      setIsClientModalOpen(false);
      setEditingClientId(null);
      await loadData();
    } catch (err) {
      setClientSubmitError(getApiErrorMessage(err, 'Erro ao salvar cliente.'));
    } finally { setClientSaving(false); }
  };

  const stats = useMemo(() => {
    const totalOrdersBySupplier = new Map<string, number>();
    orders.forEach(o => {
      if (o.supplier_id) totalOrdersBySupplier.set(o.supplier_id, (totalOrdersBySupplier.get(o.supplier_id) || 0) + 1);
    });
    return { totalOrdersBySupplier };
  }, [orders]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (s: Supplier) => {
    setEditingId(s.id);
    setForm({
      name: s.name || '',
      cnpj: s.cnpj || '',
      contact: s.contact || '',
      phone: s.phone || '',
      email: s.email || '',
      address: s.address || '',
      category: s.category || '',
      payment_terms: s.payment_terms || '',
      avg_delivery_days: s.avg_delivery_days != null ? String(s.avg_delivery_days) : '',
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleDelete = async (s: Supplier) => {
    if (!canManage) return;
    const linked = stats.totalOrdersBySupplier.get(s.id) || 0;
    if (linked > 0 && !confirm(`Fornecedor "${s.name}" possui ${linked} pedido(s) vinculado(s). Excluir mesmo assim? Os pedidos ficarão sem fornecedor.`)) return;
    if (linked === 0 && !confirm(`Excluir fornecedor "${s.name}"?`)) return;
    try {
      await supplierService.remove(s.id);
      await loadData();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir fornecedor.'));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    if (!form.name.trim()) {
      setSubmitError('Nome é obrigatório.');
      return;
    }
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      setSubmitError('E-mail inválido.');
      return;
    }
    let avg: number | null = null;
    if (form.avg_delivery_days.trim() !== '') {
      const n = Number(form.avg_delivery_days);
      if (!Number.isFinite(n) || n < 0) { setSubmitError('Prazo médio de entrega deve ser número >= 0'); return; }
      avg = Math.floor(n);
    }
    setSaving(true);
    try {
      const payload: any = {
        name: form.name.trim(),
        cnpj: form.cnpj.trim(),
        contact: form.contact.trim(),
        phone: form.phone.trim(),
        email: form.email.trim(),
        address: form.address.trim(),
        category: form.category.trim(),
        payment_terms: form.payment_terms.trim(),
      };
      if (avg !== null) payload.avg_delivery_days = avg;
      else if (editingId) payload.avg_delivery_days = null;

      if (editingId) await supplierService.update(editingId, payload);
      else await supplierService.create(payload);
      setIsModalOpen(false);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setSubmitError(getApiErrorMessage(err, 'Erro ao salvar fornecedor.'));
    } finally { setSaving(false); }
  };

  if (!canManage) {
    return (
      <div className="glass-panel p-8 rounded-lg text-center border border-zinc-800">
        <ShieldAlert className="w-10 h-10 text-zinc-500 mx-auto mb-3" />
        <p className="text-zinc-400 font-mono text-sm">Sem acesso a Clientes/Fornecedores.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide flex items-center gap-3">
            <Truck className="w-7 h-7 text-zinc-400" /> Clientes/Fornecedores
          </h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Cadastro centralizado de clientes e fornecedores — usado no Comercial, Compras, Produção e Financeiro. Cadastre aqui para selecionar nos outros módulos.</p>
        </div>
        <button
          onClick={activeTab === 'ALL' ? handleOpenCreateClient : handleOpenCreate}
          className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2.5 rounded shadow-lg flex items-center gap-1.5 transition active:scale-95 cursor-pointer font-sans"
        >
          <Plus className="w-4 h-4" /> {activeTab === 'ALL' ? 'Novo Cliente' : 'Novo Fornecedor'}
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-zinc-600">
          <div>
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Total de Fornecedores</span>
            <p className="text-xl font-bold font-sans text-white mt-1">{suppliers.length}</p>
            <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">{categories.length} categoria(s)</span>
          </div>
          <div className="p-3 bg-zinc-950 rounded text-zinc-400 border border-zinc-900"><Building2 className="w-5 h-5" /></div>
        </div>
        <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-sky-600">
          <div>
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Com Pedidos Vinculados</span>
            <p className="text-xl font-bold font-sans text-sky-400 mt-1">{Array.from(stats.totalOrdersBySupplier.keys()).length}</p>
            <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">{orders.length} pedidos totais</span>
          </div>
          <div className="p-3 bg-zinc-950 rounded text-sky-500 border border-zinc-900"><Package className="w-5 h-5" /></div>
        </div>
        <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-emerald-600">
          <div>
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Prazo Médio Entrega</span>
            <p className="text-xl font-bold font-sans text-emerald-400 mt-1">
              {(() => {
                const vals = suppliers.map(s => s.avg_delivery_days).filter(v => v != null) as number[];
                if (vals.length === 0) return '—';
                const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
                return `${avg.toFixed(1)} dias`;
              })()}
            </p>
            <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Média dos cadastrados</span>
          </div>
          <div className="p-3 bg-zinc-950 rounded text-emerald-500 border border-zinc-900"><Clock className="w-5 h-5" /></div>
        </div>
      </div>

      {/* Abas do cadastro central */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab('ALL')}
          className={`px-4 py-2 rounded text-xs font-mono transition cursor-pointer ${activeTab === 'ALL' ? 'bg-red-600 text-white font-bold' : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'}`}
        >
          Clientes ({allClients.length})
        </button>
        <button
          onClick={() => setActiveTab('SUPPLIERS')}
          className={`px-4 py-2 rounded text-xs font-mono transition cursor-pointer ${activeTab === 'SUPPLIERS' ? 'bg-red-600 text-white font-bold' : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'}`}
        >
          Fornecedores ({suppliers.length})
        </button>
        <button
          onClick={() => setActiveTab('CLIENTS')}
          className={`px-4 py-2 rounded text-xs font-mono transition cursor-pointer ${activeTab === 'CLIENTS' ? 'bg-red-600 text-white font-bold' : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'}`}
        >
          Clientes fornecedores ({clientSuppliers.length})
        </button>
      </div>

      {activeTab === 'ALL' ? (
        <div className="glass-panel p-4 rounded-lg">
          <p className="text-[11px] text-zinc-500 font-mono mb-3">Todo cliente nasce aqui — inclusive quem nunca comprou. O Comercial vincula ao funil via "Vincular Cliente"; Compras, Produção e Financeiro selecionam deste cadastro.</p>
          {filteredAllClients.length === 0 ? (
            <p className="text-zinc-500 font-mono text-sm text-center py-8">{allClients.length === 0 ? 'Nenhum cliente cadastrado. Clique em "Novo Cliente".' : 'Nenhum cliente corresponde à busca.'}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-zinc-500 bg-zinc-950/60 border-b border-zinc-800 font-mono">
                  <tr>
                    <th className="py-3 px-4 font-normal">Nome</th>
                    <th className="py-3 px-4 font-normal">CPF/CNPJ</th>
                    <th className="py-3 px-4 font-normal">Contato</th>
                    <th className="py-3 px-4 font-normal">Telefone</th>
                    <th className="py-3 px-4 font-normal">No funil</th>
                    <th className="py-3 px-4 font-normal text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-sm">
                  {filteredAllClients.map(c => (
                    <tr key={c.id} className="hover:bg-zinc-800/30">
                      <td className="py-3 px-4 font-sans font-semibold text-white">{c.name}
                        {(c as any).is_supplier && <span className="inline-block ml-2 px-1.5 py-0.5 text-[10px] font-mono rounded bg-sky-500/10 text-sky-300 border border-sky-500/30">🏭 Fornecedor</span>}
                        <span className="block text-[10px] font-mono text-zinc-500 truncate max-w-[220px]">{c.email || '—'}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{c.cpf_cnpj || '—'}</td>
                      <td className="py-3 px-4 text-zinc-300 text-xs">{(c as any).contact || '—'}</td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{c.phone || '—'}</td>
                      <td className="py-3 px-4 text-xs font-mono">{(c as any).funnel_id ? <span className="text-emerald-400">Sim</span> : <span className="text-zinc-500">Não</span>}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => handleOpenEditClient(c)} className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 transition cursor-pointer" title="Editar"><Edit3 className="w-3.5 h-3.5" /></button>
                          <button onClick={() => handleClientDelete(c)} className="p-1.5 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 transition cursor-pointer" title="Excluir"><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : activeTab === 'CLIENTS' ? (
        <div className="glass-panel p-4 rounded-lg">
          <p className="text-[11px] text-zinc-500 font-mono mb-3">Clientes marcados como fornecedor — aparecem em Compras e Financeiro. Para editar, use a aba Clientes ou o Comercial.</p>
          {filteredClients.length === 0 ? (
            <p className="text-zinc-500 font-mono text-sm text-center py-8">{clientSuppliers.length === 0 ? 'Nenhum cliente marcado como fornecedor. Marque "Também é fornecedor" no cadastro do cliente, no Comercial.' : 'Nenhum cliente corresponde à busca.'}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-zinc-500 bg-zinc-950/60 border-b border-zinc-800 font-mono">
                  <tr>
                    <th className="py-3 px-4 font-normal">Nome</th>
                    <th className="py-3 px-4 font-normal">CPF/CNPJ</th>
                    <th className="py-3 px-4 font-normal">Contato</th>
                    <th className="py-3 px-4 font-normal">Telefone</th>
                    <th className="py-3 px-4 font-normal">Categoria</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-sm">
                  {filteredClients.map(c => (
                    <tr key={c.id} className="hover:bg-zinc-800/30">
                      <td className="py-3 px-4 font-sans font-semibold text-white">{c.name}<span className="block text-[10px] font-mono text-zinc-500 truncate max-w-[220px]">{c.email || '—'}</span></td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{c.cpf_cnpj || '—'}</td>
                      <td className="py-3 px-4 text-zinc-300 text-xs">{(c as any).contact || '—'}</td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{c.phone || '—'}</td>
                      <td className="py-3 px-4"><span className="inline-block px-2 py-0.5 text-[11px] font-mono rounded bg-sky-500/10 text-sky-300 border border-sky-500/30">{(c as any).category || '—'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
      <>
      {/* Filters */}
      <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center">
        <div className="relative w-full md:flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
          <input
            type="text"
            placeholder="Buscar por nome, CNPJ, contato ou e-mail..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-800 text-white pl-10 pr-4 py-2 text-sm rounded focus:outline-none focus:border-red-600 font-sans"
          />
        </div>
        <div className="w-full md:w-auto flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-mono whitespace-nowrap">Categoria:</span>
          <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} className="bg-zinc-900 border border-zinc-800 text-white text-xs rounded px-3 py-2 focus:outline-none focus:border-red-600 font-mono">
            <option value="TODOS">Todas</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando fornecedores...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel p-12 rounded-lg text-center border border-zinc-800 bg-zinc-900">
          <Truck className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <p className="text-zinc-500 font-mono text-sm">{suppliers.length === 0 ? 'Nenhum fornecedor cadastrado.' : 'Nenhum fornecedor corresponde aos filtros.'}</p>
          {suppliers.length === 0 && <p className="text-zinc-600 font-mono text-xs mt-1">Cadastre fornecedores aqui para usar no Novo Pedido.</p>}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block glass-panel rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-zinc-500 bg-zinc-950/60 border-b border-zinc-800 font-mono">
                  <tr>
                    <th className="py-3 px-4 font-normal">Nome</th>
                    <th className="py-3 px-4 font-normal">CNPJ</th>
                    <th className="py-3 px-4 font-normal">Contato</th>
                    <th className="py-3 px-4 font-normal">Telefone</th>
                    <th className="py-3 px-4 font-normal">Categoria</th>
                    <th className="py-3 px-4 font-normal">Pedidos</th>
                    <th className="py-3 px-4 font-normal">Prazo</th>
                    <th className="py-3 px-4 font-normal text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-sm">
                  {filtered.map(s => (
                    <tr key={s.id} className="hover:bg-zinc-800/30">
                      <td className="py-3 px-4 font-sans font-semibold text-white">{s.name}<span className="block text-[10px] font-mono text-zinc-500 truncate max-w-[220px]">{s.email || '—'}</span></td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{s.cnpj || '—'}</td>
                      <td className="py-3 px-4 text-zinc-300 text-xs">{s.contact || '—'}</td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{s.phone || '—'}</td>
                      <td className="py-3 px-4"><span className="inline-block px-2 py-0.5 text-[11px] font-mono rounded bg-zinc-800 text-zinc-300 border border-zinc-700">{s.category || '—'}</span></td>
                      <td className="py-3 px-4 text-center text-zinc-300 font-mono text-xs">{stats.totalOrdersBySupplier.get(s.id) || 0}</td>
                      <td className="py-3 px-4 font-mono text-xs text-zinc-400">{s.avg_delivery_days != null ? `${s.avg_delivery_days}d` : '—'}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => handleOpenEdit(s)} className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white rounded border border-zinc-700 transition cursor-pointer" title="Editar"><Edit3 className="w-3.5 h-3.5" /></button>
                          <button onClick={() => handleDelete(s)} className="p-1.5 bg-zinc-800 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 transition cursor-pointer" title="Excluir"><Trash2 className="w-3.5 h-3.5" /></button>
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
            {filtered.map(s => (
              <div key={s.id} className="glass-panel p-4 rounded-lg border border-zinc-800 bg-zinc-900">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-white text-sm">{s.name}</p>
                    <p className="text-[11px] font-mono text-zinc-500">{s.cnpj || 'Sem CNPJ'} {s.category ? `· ${s.category}` : ''}</p>
                    {s.email && <p className="text-xs text-zinc-400 flex items-center gap-1 mt-1"><Mail className="w-3 h-3" />{s.email}</p>}
                    {s.phone && <p className="text-xs text-zinc-400 flex items-center gap-1"><Phone className="w-3 h-3" />{s.phone}</p>}
                  </div>
                  <span className="text-xs font-mono bg-zinc-800 text-zinc-300 px-2 py-1 rounded border border-zinc-700">{stats.totalOrdersBySupplier.get(s.id) || 0} pedido(s)</span>
                </div>
                <div className="mt-3 flex justify-between items-center">
                  <span className="text-[11px] font-mono text-zinc-500">Prazo: {s.avg_delivery_days != null ? `${s.avg_delivery_days} dias` : '—'}</span>
                  <div className="flex gap-1">
                    <button onClick={() => handleOpenEdit(s)} className="p-2 bg-zinc-800 text-zinc-300 rounded border border-zinc-700 cursor-pointer"><Edit3 className="w-4 h-4" /></button>
                    <button onClick={() => handleDelete(s)} className="p-2 bg-zinc-800 text-zinc-500 hover:text-red-400 rounded border border-zinc-700 cursor-pointer"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
      </>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setIsModalOpen(false)}>
          <div className="glass-panel w-full max-w-xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[92vh] flex flex-col bg-zinc-900" onClick={e => e.stopPropagation()}>
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2"><Truck className="w-5 h-5" />{editingId ? 'Editar Fornecedor' : 'Novo Fornecedor'}</h3>
                <p className="text-xs text-zinc-400 font-mono">Cadastro usado em Compras/Financeiro.</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="p-2 text-zinc-500 hover:text-white rounded cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1 overscroll-contain">
              {submitError && <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{submitError}</div>}
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase">Nome *</label>
                <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Ex: Madeireira Sul" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">CNPJ</label>
                  <input value={form.cnpj} onChange={e => setForm(p => ({ ...p, cnpj: e.target.value }))} placeholder="00.000.000/0000-00" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-mono" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">Categoria</label>
                  <input value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} placeholder="Ex: Madeira, Ferragens" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">Pessoa de contato</label>
                  <input value={form.contact} onChange={e => setForm(p => ({ ...p, contact: e.target.value }))} placeholder="Ex: João da Silva" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">Telefone</label>
                  <input value={form.phone} onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} placeholder="(55) 99999-9999" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-mono" />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase">E-mail</label>
                <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} placeholder="contato@fornecedor.com" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase">Endereço</label>
                <textarea value={form.address} onChange={e => setForm(p => ({ ...p, address: e.target.value }))} rows={2} placeholder="Rua, número, bairro, cidade/UF" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 resize-none" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase flex items-center gap-1"><CreditCard className="w-3 h-3" /> Condições pagamento</label>
                  <input value={form.payment_terms} onChange={e => setForm(p => ({ ...p, payment_terms: e.target.value }))} placeholder="Ex: 30/60 dias, À vista 5%" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase flex items-center gap-1"><Clock className="w-3 h-3" /> Prazo médio entrega (dias)</label>
                  <input type="number" min={0} value={form.avg_delivery_days} onChange={e => setForm(p => ({ ...p, avg_delivery_days: e.target.value }))} placeholder="Ex: 7" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-mono" />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 cursor-pointer">Cancelar</button>
                <button type="submit" disabled={saving} className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded disabled:opacity-50 cursor-pointer flex items-center gap-2">
                  {saving ? <><RefreshCw className="w-4 h-4 animate-spin" /> Salvando...</> : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal cliente (cadastro central) */}
      {isClientModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setIsClientModalOpen(false)}>
          <div className="glass-panel w-full max-w-xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[92vh] flex flex-col bg-zinc-900" onClick={e => e.stopPropagation()}>
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-bold text-white flex items-center gap-2"><Building2 className="w-5 h-5" />{editingClientId ? 'Editar Cliente' : 'Novo Cliente'}</h3>
                <p className="text-xs text-zinc-400 font-mono">Cadastro central — nasce fora do funil; o Comercial vincula depois.</p>
              </div>
              <button onClick={() => setIsClientModalOpen(false)} className="p-2 text-zinc-500 hover:text-white rounded cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleClientSubmit} className="p-6 space-y-4 overflow-y-auto flex-1 overscroll-contain">
              {clientSubmitError && <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{clientSubmitError}</div>}
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase">Nome *</label>
                <input value={clientForm.name} onChange={e => setClientForm(p => ({ ...p, name: e.target.value }))} placeholder="Ex: Roberto de Oliveira Menezes" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">CPF / CNPJ</label>
                  <input value={clientForm.cpf_cnpj} onChange={e => setClientForm(p => ({ ...p, cpf_cnpj: e.target.value }))} placeholder="000.000.000-00" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-mono" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">Telefone</label>
                  <input value={clientForm.phone} onChange={e => setClientForm(p => ({ ...p, phone: e.target.value }))} placeholder="(55) 99999-9999" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-mono" />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase">E-mail</label>
                <input type="email" value={clientForm.email} onChange={e => setClientForm(p => ({ ...p, email: e.target.value }))} placeholder="contato@empresa.com.br" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase">Endereço</label>
                <textarea value={clientForm.address} onChange={e => setClientForm(p => ({ ...p, address: e.target.value }))} rows={2} placeholder="Rua, número, bairro, cidade/UF" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 resize-none" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">Pessoa de contato</label>
                  <input value={clientForm.contact} onChange={e => setClientForm(p => ({ ...p, contact: e.target.value }))} placeholder="Ex: João da Silva" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-300 font-mono uppercase">Categoria</label>
                  <input value={clientForm.category} onChange={e => setClientForm(p => ({ ...p, category: e.target.value }))} placeholder="Ex: Residencial, MDF" className="w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700" />
                </div>
              </div>
              <label className="flex items-start gap-3 bg-zinc-950 border border-zinc-800 rounded px-4 py-3 cursor-pointer">
                <input type="checkbox" checked={clientForm.is_supplier} onChange={e => setClientForm(p => ({ ...p, is_supplier: e.target.checked }))} className="mt-0.5 w-4 h-4 accent-red-600" />
                <span className="text-xs text-zinc-300 font-sans"><span className="font-semibold text-white">Também é fornecedor</span><span className="block text-zinc-500 font-mono text-[11px] mt-0.5">Aparece em Compras e Financeiro via cadastro central.</span></span>
              </label>
              <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800">
                <button type="button" onClick={() => setIsClientModalOpen(false)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 cursor-pointer">Cancelar</button>
                <button type="submit" disabled={clientSaving} className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded disabled:opacity-50 cursor-pointer flex items-center gap-2">
                  {clientSaving ? <><RefreshCw className="w-4 h-4 animate-spin" /> Salvando...</> : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
