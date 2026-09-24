/**
 * Cotacoes — comparativo lado a lado dos fornecedores para um pedido.
 *
 * Linhas = itens do pedido, colunas = cotacoes. O menor preco de cada item fica
 * destacado, que e o que o cliente olha. Aprovar uma cotacao leva os precos
 * dela para o pedido e a marca como vencedora (unica) no backend.
 *
 * A economia exibida e a MEDIDA (maior preco cotado - preco escolhido), a mesma
 * formula da planilha — nao o proxy de catalogo que o dashboard usava antes de
 * existir cotacao.
 */
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Check, Loader2, Plus, Trash2, Trophy } from 'lucide-react';
import { purchaseService, supplierService, getApiErrorMessage } from '../services/api';
import { PurchaseOrder, PurchaseQuotation, Supplier } from '../types';

const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export default function QuotationsPanel() {
  const [pedidos, setPedidos] = useState<PurchaseOrder[]>([]);
  const [fornecedores, setFornecedores] = useState<Supplier[]>([]);
  const [orderId, setOrderId] = useState('');
  const [cotacoes, setCotacoes] = useState<PurchaseQuotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingCot, setLoadingCot] = useState(false);
  const [error, setError] = useState('');
  const [formAberto, setFormAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({
    supplier_id: '', delivery_days: '', payment_terms: '', precos: {} as Record<string, string>,
  });

  useEffect(() => {
    Promise.all([
      purchaseService.list(),
      supplierService.getAll().catch(() => []),
    ])
      .then(([ps, fs]) => {
        setPedidos(ps);
        setFornecedores(fs as Supplier[]);
        if (ps.length && !orderId) setOrderId(ps[0].id);
      })
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar as compras.')))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pedido = useMemo(() => pedidos.find(p => p.id === orderId) || null, [pedidos, orderId]);

  const carregarCotacoes = () => {
    if (!orderId) return;
    setLoadingCot(true);
    setError('');
    purchaseService
      .listQuotations(orderId)
      .then(setCotacoes)
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar as cotações.')))
      .finally(() => setLoadingCot(false));
  };

  useEffect(carregarCotacoes, [orderId]);

  /** Menor preco cotado de um item (entre as cotacoes do pedido). */
  const menorPreco = (itemId: string): number | null => {
    const precos = cotacoes
      .flatMap(q => q.items)
      .filter(i => i.purchase_item_id === itemId)
      .map(i => Number(i.unit_price));
    return precos.length ? Math.min(...precos) : null;
  };

  const precoDe = (q: PurchaseQuotation, itemId: string): number | null => {
    const it = q.items.find(i => i.purchase_item_id === itemId);
    return it ? Number(it.unit_price) : null;
  };

  const abrirNova = () => {
    setForm({ supplier_id: '', delivery_days: '', payment_terms: '', precos: {} });
    setFormAberto(true);
  };

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    if (!pedido) return;
    setSalvando(true);
    setError('');
    const items = pedido.items
      .map(i => ({ purchase_item_id: i.id, unit_price: Number(form.precos[i.id] || 0) }))
      .filter(i => i.unit_price > 0);
    if (!items.length) {
      setError('Informe o preço de pelo menos um item.');
      setSalvando(false);
      return;
    }
    try {
      await purchaseService.createQuotation(pedido.id, {
        supplier_id: form.supplier_id || undefined,
        delivery_days: form.delivery_days === '' ? undefined : Number(form.delivery_days),
        payment_terms: form.payment_terms,
        items,
      });
      setFormAberto(false);
      carregarCotacoes();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar a cotação.'));
    } finally {
      setSalvando(false);
    }
  };

  const aprovar = async (q: PurchaseQuotation) => {
    if (!pedido) return;
    if (!window.confirm(`Aprovar a cotação de ${q.supplier_name || 'fornecedor não informado'}? Os preços dela passam a valer no pedido.`)) return;
    try {
      const atualizado = await purchaseService.approveQuotation(pedido.id, q.id);
      setPedidos(ps => ps.map(p => (p.id === atualizado.id ? atualizado : p)));
      carregarCotacoes();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao aprovar a cotação.'));
    }
  };

  const excluir = async (q: PurchaseQuotation) => {
    if (!window.confirm('Excluir esta cotação?')) return;
    try {
      await purchaseService.deleteQuotation(q.id);
      carregarCotacoes();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir a cotação.'));
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
        <p className="text-zinc-400 font-mono text-xs">Carregando compras...</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="glass-panel p-4 rounded-lg flex flex-wrap items-end gap-3">
        <div className="space-y-1.5 min-w-[260px]">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Pedido de compra</label>
          <select value={orderId} onChange={e => setOrderId(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            {pedidos.map(p => (
              <option key={p.id} value={p.id}>
                {p.number} — {p.supplier_name || 'sem fornecedor'} ({p.items.length} item(ns))
              </option>
            ))}
          </select>
        </div>
        <div className="ml-auto">
          <button onClick={abrirNova} disabled={!pedido}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-50">
            <Plus className="w-3.5 h-3.5" /> Nova cotação
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {!pedido ? (
        <div className="glass-panel p-10 rounded-lg text-center">
          <p className="text-sm text-zinc-300 font-mono">Nenhum pedido de compra cadastrado.</p>
          <p className="text-xs text-zinc-500 font-mono mt-1">Crie um pedido na aba Compras para cotar.</p>
        </div>
      ) : (
        <>
          {/* Formulario de nova cotacao */}
          {formAberto && (
            <form onSubmit={salvar} className="glass-panel p-5 rounded-lg space-y-4">
              <h3 className="text-sm font-semibold text-white font-sans">
                Nova cotação para {pedido.number}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Fornecedor</label>
                  <select value={form.supplier_id}
                    onChange={e => setForm({ ...form, supplier_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                    <option value="">Não informado</option>
                    {fornecedores.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Prazo (dias)</label>
                  <input type="number" min="0" value={form.delivery_days}
                    onChange={e => setForm({ ...form, delivery_days: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Condição de pagamento</label>
                  <input type="text" value={form.payment_terms} placeholder="Ex.: 30/60 dias"
                    onChange={e => setForm({ ...form, payment_terms: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                </div>
              </div>
              <div className="space-y-2">
                <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">
                  Preço unitário por item
                </span>
                {pedido.items.map(i => (
                  <div key={i.id} className="flex items-center gap-3">
                    <span className="text-xs font-sans text-zinc-300 flex-1 min-w-0 truncate">
                      {i.material_name}
                      <span className="text-zinc-500 font-mono"> · {i.quantity}</span>
                    </span>
                    <input type="number" step="0.01" min="0" placeholder="0,00"
                      value={form.precos[i.id] || ''}
                      onChange={e => setForm({ ...form, precos: { ...form.precos, [i.id]: e.target.value } })}
                      className="w-28 bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-900">
                <button type="button" onClick={() => setFormAberto(false)}
                  className="px-3.5 py-2 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-xs font-mono uppercase cursor-pointer">
                  Cancelar
                </button>
                <button type="submit" disabled={salvando}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60">
                  {salvando && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Salvar cotação
                </button>
              </div>
            </form>
          )}

          {loadingCot ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
              <p className="text-zinc-400 font-mono text-xs">Carregando cotações...</p>
            </div>
          ) : cotacoes.length === 0 ? (
            <div className="glass-panel p-10 rounded-lg text-center">
              <p className="text-sm text-zinc-300 font-mono">Nenhuma cotação para este pedido.</p>
              <p className="text-xs text-zinc-500 font-mono mt-1">
                Sem cotação, a economia do dashboard é estimativa por catálogo — não medida.
              </p>
            </div>
          ) : (
            <div className="glass-panel rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-zinc-300">
                  <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                    <tr>
                      <th className="py-3 px-5 font-normal">Item</th>
                      <th className="py-3 px-5 font-normal text-right">Preço no pedido</th>
                      {cotacoes.map(q => (
                        <th key={q.id} className="py-3 px-5 font-normal text-right whitespace-nowrap">
                          {q.supplier_name || 'sem fornecedor'}
                          {q.is_winner && (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-emerald-400">
                              <Trophy className="w-3 h-3" /> vencedora
                            </span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900">
                    {pedido.items.map(item => {
                      const menor = menorPreco(item.id);
                      return (
                        <tr key={item.id} className="hover:bg-zinc-900/40">
                          <td className="py-3 px-5 font-sans text-xs">
                            {item.material_name}
                            <span className="block text-[10px] text-zinc-500 font-mono">
                              qtd. {item.quantity}
                            </span>
                          </td>
                          <td className="py-3 px-5 font-mono text-xs text-right text-zinc-400">
                            {fmt(Number(item.unit_price))}
                          </td>
                          {cotacoes.map(q => {
                            const p = precoDe(q, item.id);
                            const melhor = p !== null && menor !== null && p === menor;
                            return (
                              <td key={q.id} className="py-3 px-5 font-mono text-xs text-right whitespace-nowrap">
                                {p === null ? (
                                  <span className="text-zinc-600">—</span>
                                ) : (
                                  <span className={melhor ? 'text-emerald-400 font-bold' : ''}>
                                    {fmt(p)}
                                    {melhor && <span className="ml-1 text-[9px] uppercase">menor</span>}
                                  </span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                    {/* totais */}
                    <tr className="bg-zinc-950/50">
                      <td className="py-3 px-5 font-mono text-xs uppercase text-zinc-400">Total</td>
                      <td className="py-3 px-5 font-mono text-xs text-right text-zinc-400">
                        {fmt(Number(pedido.total))}
                      </td>
                      {cotacoes.map(q => (
                        <td key={q.id} className="py-3 px-5 font-mono text-xs text-right font-bold text-white whitespace-nowrap">
                          {fmt(Number(q.total))}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3 px-5 font-mono text-xs uppercase text-zinc-400">Prazo</td>
                      <td className="py-3 px-5" />
                      {cotacoes.map(q => (
                        <td key={q.id} className="py-3 px-5 font-mono text-xs text-right text-zinc-400 whitespace-nowrap">
                          {q.delivery_days === null ? '—' : `${q.delivery_days} dia(s)`}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3 px-5 font-mono text-xs uppercase text-zinc-400">Pagamento</td>
                      <td className="py-3 px-5" />
                      {cotacoes.map(q => (
                        <td key={q.id} className="py-3 px-5 font-mono text-xs text-right text-zinc-400 whitespace-nowrap">
                          {q.payment_terms || '—'}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-4 px-5" />
                      <td className="py-4 px-5" />
                      {cotacoes.map(q => (
                        <td key={q.id} className="py-4 px-5 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {!q.is_winner && (
                              <button onClick={() => aprovar(q)} title="Aprovar esta cotação"
                                className="flex items-center gap-1 px-2.5 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-900/40 text-emerald-400 rounded text-[10px] font-mono uppercase transition cursor-pointer">
                                <Check className="w-3 h-3" /> Aprovar
                              </button>
                            )}
                            <button onClick={() => excluir(q)} title="Excluir cotação"
                              className="p-1.5 text-zinc-500 hover:text-rose-500 transition cursor-pointer">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Economia medida deste pedido */}
          {cotacoes.length > 0 && (
            <div className="glass-panel p-4 rounded-lg border-l-4 border-l-emerald-600">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
                Economia medida neste pedido
              </span>
              <p className="text-xl font-bold font-sans text-emerald-400 mt-1">
                {fmt(Number(pedido.saving_real || 0))}
              </p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">
                {pedido.saving_real_items || 0} de {pedido.items.length} item(ns) com cotação —
                diferença entre o maior preço cotado e o escolhido.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
