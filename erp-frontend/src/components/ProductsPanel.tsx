/**
 * Aba Produtos/Móveis do Comercial: cadastro do catalogo usado na venda.
 *
 * CRUD sobre products_bp (GET list com inativos, POST, PUT, DELETE soft).
 * Escrita ADMIN/GERENTE; leitura para todos. Itens de venda guardam snapshot,
 * entao inativar/editar aqui nao quebra historico.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, X, Loader2, Package } from 'lucide-react';
import { productService, getApiErrorMessage } from '../services/api';
import { Product } from '../types';

const inputClass =
  'w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600';

const fmtBRL = (v: number | null | undefined) =>
  (Number(v || 0)).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export default function ProductsPanel({ userRole }: { userRole: string }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState({ name: '', description: '', default_price: '', unit: 'un', active: true });

  const canEdit = ['ADMIN', 'GERENTE'].includes(userRole);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setProducts(await productService.listWithInactive());
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao carregar produtos.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    if (!canEdit) return;
    setEditing(null);
    setForm({ name: '', description: '', default_price: '', unit: 'un', active: true });
    setModalOpen(true);
  };

  const openEdit = (p: Product) => {
    if (!canEdit) return;
    setEditing(p);
    setForm({
      name: p.name,
      description: p.description || '',
      default_price: p.default_price != null ? String(p.default_price) : '',
      unit: p.unit || 'un',
      active: p.active,
    });
    setModalOpen(true);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: form.name,
        description: form.description,
        default_price: form.default_price === '' ? null : Number(form.default_price),
        unit: form.unit,
        active: form.active,
      };
      if (editing) {
        await productService.update(editing.id, payload);
      } else {
        await productService.create(payload);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar produto.'));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p: Product) => {
    if (!window.confirm(`Inativar "${p.name}"? Ele sai da lista de venda, mas o histórico das vendas já feitas continua intacto.`)) return;
    setError('');
    try {
      await productService.remove(p.id);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao inativar produto.'));
    }
  };

  const reactivate = async (p: Product) => {
    setError('');
    try {
      await productService.update(p.id, { active: true });
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao reativar produto.'));
    }
  };

  const filtered = products.filter(p =>
    !search.trim() || p.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-5">
      <div className="glass-panel p-5 rounded-lg flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
            <Package className="w-4 h-4 text-red-400" /> Produtos / Móveis
          </h3>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            {products.filter(p => p.active).length} ativos · {products.length} no total
          </p>
        </div>
        <div className="flex gap-2">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar produto..."
            className="bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-2 text-sm focus:outline-none focus:border-red-600 w-56"
          />
          {canEdit && (
            <button onClick={openNew}
              className="px-3 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs transition cursor-pointer flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5" /> Novo produto
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{error}</div>
      )}

      <div className="glass-panel rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-10 flex items-center justify-center text-zinc-400">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Carregando catálogo...
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[62vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-zinc-950/95 z-10">
                <tr className="text-left text-[10px] text-zinc-500 uppercase tracking-wider font-mono">
                  <th className="px-4 py-2">Nome</th>
                  <th className="px-4 py-2">Descrição</th>
                  <th className="px-4 py-2 text-right">Preço padrão</th>
                  <th className="px-4 py-2">Unidade</th>
                  <th className="px-4 py-2">Status</th>
                  {canEdit && <th className="px-4 py-2 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.id} className={`border-t border-zinc-900 hover:bg-zinc-900/40 ${p.active ? '' : 'opacity-60'}`}>
                    <td className="px-4 py-2.5 text-zinc-200">{p.name}</td>
                    <td className="px-4 py-2.5 text-xs text-zinc-500 max-w-[280px] truncate">{p.description || '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-zinc-300">{fmtBRL(p.default_price)}</td>
                    <td className="px-4 py-2.5 text-xs text-zinc-400">{p.unit}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${p.active
                        ? 'text-emerald-400 border-emerald-900 bg-emerald-950/40'
                        : 'text-zinc-500 border-zinc-800 bg-zinc-900/60'}`}>
                        {p.active ? 'ATIVO' : 'INATIVO'}
                      </span>
                    </td>
                    {canEdit && (
                      <td className="px-4 py-2.5 text-right whitespace-nowrap">
                        <button type="button" onClick={() => openEdit(p)} className="text-zinc-500 hover:text-emerald-400 p-1 cursor-pointer" title="Editar">
                          <Pencil className="w-4 h-4" />
                        </button>
                        {p.active ? (
                          <button type="button" onClick={() => remove(p)} className="text-zinc-500 hover:text-red-400 p-1 cursor-pointer" title="Inativar">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        ) : (
                          <button type="button" onClick={() => reactivate(p)} className="text-zinc-500 hover:text-emerald-400 p-1 cursor-pointer text-[10px] font-mono" title="Reativar">
                            REATIVAR
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-10 text-center text-xs text-zinc-600 font-mono">Nenhum produto cadastrado.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setModalOpen(false)}>
          <div className="glass-panel w-full max-w-lg rounded-lg flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 shrink-0">
              <div>
                <h3 className="text-sm font-bold text-zinc-200">{editing ? 'Editar produto' : 'Novo produto'}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-0.5">Catálogo usado na tela de Gerar venda</p>
              </div>
              <button type="button" onClick={() => setModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={submit} className="p-6 space-y-4 overflow-y-auto flex-1 overscroll-contain">
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nome *</label>
                <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="Ex: Cozinha planejada, Painel TV, Closet..." className={inputClass} />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Descrição</label>
                <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                  rows={2} placeholder="Ex: MDF 15mm, acabamento branco fosco"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 resize-none" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Preço padrão (R$)</label>
                  <input type="number" step="0.01" min="0" value={form.default_price}
                    onChange={e => setForm({ ...form, default_price: e.target.value })}
                    placeholder="Ex: 4500" className={inputClass} />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Unidade</label>
                  <input type="text" value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })}
                    placeholder="un" className={inputClass} />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                <input type="checkbox" checked={form.active}
                  onChange={e => setForm({ ...form, active: e.target.checked })} />
                Produto ativo (aparece na venda)
              </label>
              <button type="submit" disabled={saving}
                className="w-full py-3 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-sm font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2">
                {saving && <Loader2 className="w-4 h-4 animate-spin" />} {editing ? 'Salvar alterações' : 'Cadastrar produto'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}