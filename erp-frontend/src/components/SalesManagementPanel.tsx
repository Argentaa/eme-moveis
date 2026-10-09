/**
 * Gestão de "Vendas realizadas" do Comercial (aba da área comercial).
 *
 * - Lista GET /api/sales com Editar (data da venda, valor, entrada,
 *   parcelas → PUT /api/sales/<id>) e Excluir (confirmação →
 *   DELETE /api/sales/<id>); a lista recarrega após cada ação.
 * - Lista `vendas_pendentes_geracao` do /api/reports/crm (fechados sem Sale
 *   gerada) com ação "Gerar venda" pelo fluxo existente (GenerateSaleModal).
 */
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import {
  BadgeDollarSign, Pencil, Trash2, X, Loader2, RefreshCw,
  AlertTriangle, ReceiptText, UserPlus,
} from 'lucide-react';
import {
  saleService, dashboardService, clientService, getApiErrorMessage,
} from '../services/api';
import { Client, Sale, SaleListRow, VendaPendenteGeracao } from '../types';
import GenerateSaleModal from './GenerateSaleModal';

const fmtBRL = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtData = (iso: string | null | undefined) => {
  if (!iso) return '—';
  const d = iso.slice(0, 10).split('-');
  return d.length === 3 ? `${d[2]}/${d[1]}/${d[0]}` : iso.slice(0, 10);
};

const inputClass =
  'w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600';

function addMonths(dateStr: string, months: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  if (isNaN(d.getTime())) return '';
  d.setMonth(d.getMonth() + months);
  return d.toISOString().substring(0, 10);
}

/* ── Modal Editar venda ─────────────────────────────────────────── */

function SaleEditModal({ sale, onClose, onSaved }: {
  sale: Sale;
  onClose: () => void;
  onSaved: () => void;
}) {
  const today = new Date().toISOString().substring(0, 10);
  const [form, setForm] = useState({
    sale_date: (sale.sale_date || '').slice(0, 10) || today,
    total_value: String(sale.total_value ?? ''),
    down_payment: String(sale.down_payment ?? ''),
    installments: String(sale.installments ?? ''),
    installment_value: String(sale.installment_value ?? ''),
    installments_due: (sale.installments_list || []).map(i => (i.due_date || '').slice(0, 10)),
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const total = Number(form.total_value) || 0;
  const nParc = Number(form.installments) || 0;
  const down = Number(form.down_payment) || 0;
  const parcVal = Number(form.installment_value) || 0;
  const soma = down + nParc * parcVal;
  const somaOk = Math.abs(soma - total) <= 0.01;

  const recalcParcela = (downRaw: string, nRaw: string, tot: number) => {
    const n = Number(nRaw) || 0;
    const d = Number(downRaw) || 0;
    if (n > 0 && (tot - d) > 0) return String(Math.round(((tot - d) / n) * 100) / 100);
    return n === 0 ? '' : form.installment_value;
  };

  const setDown = (raw: string) =>
    setForm(prev => ({ ...prev, down_payment: raw, installment_value: recalcParcela(raw, prev.installments, total) }));

  const setNParc = (raw: string) => {
    const n = Number(raw) || 0;
    setForm(prev => ({
      ...prev,
      installments: raw,
      installments_due: Array.from({ length: n }, (_, i) =>
        prev.installments_due[i] || addMonths(prev.sale_date || today, i + 1) || ''),
      installment_value: recalcParcela(prev.down_payment, raw, total),
    }));
  };

  const setTotal = (raw: string) => {
    const t = Number(raw) || 0;
    setForm(prev => ({ ...prev, total_value: raw, installment_value: recalcParcela(prev.down_payment, prev.installments, t) }));
  };

  const setDue = (idx: number, value: string) =>
    setForm(prev => {
      const due = [...prev.installments_due];
      due[idx] = value;
      return { ...prev, installments_due: due };
    });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.sale_date) { setError('Informe a data da venda.'); return; }
    if (!(total > 0)) { setError('Informe o valor total da venda.'); return; }
    if (!somaOk) { setError('Entrada + parcelas não fecha com o valor total da venda.'); return; }
    if (saving) return;
    setSaving(true);
    setError('');
    try {
      await saleService.update(sale.id, {
        sale_date: form.sale_date,
        total_value: total,
        down_payment: down,
        installments: nParc,
        installment_value: parcVal,
        installments_due: nParc > 0 ? form.installments_due : [],
      });
      onSaved();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar a venda.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-panel w-full max-w-lg rounded-lg flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 shrink-0">
          <div className="flex items-center gap-2">
            <Pencil className="w-5 h-5 text-amber-400" />
            <div>
              <h3 className="text-base font-serif font-semibold text-white">Editar venda {sale.code}</h3>
              <p className="text-xs text-zinc-400 font-mono mt-0.5">
                {sale.client_name || '—'} · o financeiro vinculado é recalculado
              </p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="text-zinc-500 hover:text-white cursor-pointer font-mono text-xs">Sair</button>
        </div>

        <form onSubmit={submit} className="p-6 space-y-4 overflow-y-auto flex-1 overscroll-contain">
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{error}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data da venda *</label>
              <input type="date" required value={form.sale_date}
                onChange={e => setForm({ ...form, sale_date: e.target.value })}
                className={inputClass} />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor total (R$) *</label>
              <input type="number" step="0.01" min="0.01" required value={form.total_value}
                onChange={e => setTotal(e.target.value)}
                className={inputClass} />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Entrada (R$)</label>
              <input type="number" step="0.01" min="0" value={form.down_payment}
                onChange={e => setDown(e.target.value)}
                className={inputClass} />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nº de parcelas</label>
              <input type="number" min="0" max="60" value={form.installments}
                onChange={e => setNParc(e.target.value)}
                placeholder="0 = à vista" className={inputClass} />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor das parcelas (R$)</label>
              <input type="number" step="0.01" min="0" value={form.installment_value}
                onChange={e => setForm({ ...form, installment_value: e.target.value })}
                className={inputClass} />
            </div>
          </div>
          <p className={`text-[11px] font-mono ${somaOk ? 'text-zinc-500' : 'text-red-400'}`}>
            Entrada + parcelas: {fmtBRL(soma)} · valor da venda: {fmtBRL(total)}
            {somaOk ? '' : ' — não fecha com o valor total!'}
          </p>
          {nParc > 0 && (
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Vencimentos das parcelas</label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {form.installments_due.map((due, i) => (
                  <input key={i} type="date" required value={due}
                    onChange={e => setDue(i, e.target.value)}
                    className={inputClass} title={`Parcela ${i + 1}`} />
                ))}
              </div>
            </div>
          )}
          <button type="submit" disabled={!somaOk || saving}
            className="w-full py-3 bg-amber-600 hover:bg-amber-500 text-white rounded text-sm font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Salvar alterações
          </button>
        </form>
      </div>
    </div>
  );
}

/* ── Modal Excluir venda ────────────────────────────────────────── */

function SaleDeleteModal({ row, onClose, onDeleted }: {
  row: SaleListRow;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await saleService.remove(row.id);
      onDeleted();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir a venda.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="bg-zinc-950 p-5 border-b border-zinc-800 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="text-base font-serif font-semibold text-white">Excluir venda</h3>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white cursor-pointer font-mono text-xs">Sair</button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-zinc-400">
            Excluir a venda <strong className="text-white">{row.code}</strong> de{' '}
            <strong className="text-white">{row.client_name || '—'}</strong>{' '}
            ({fmtBRL(row.total_value)} em {fmtData(row.sale_date)})?
          </p>
          <p className="text-[11px] text-zinc-500 font-mono">Esta ação não pode ser desfeita.</p>
          {error && <p className="text-xs text-red-400 font-mono">{error}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={onClose}
              className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-800 cursor-pointer font-mono">
              Cancelar
            </button>
            <button onClick={confirm} disabled={busy}
              className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer disabled:opacity-50 flex items-center gap-2">
              {busy && <Loader2 className="w-4 h-4 animate-spin" />}
              Excluir venda
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Painel ─────────────────────────────────────────────────────── */

export default function SalesManagementPanel({ userRole }: { userRole: string }) {
  const canWrite = ['ADMIN', 'GERENTE'].includes(userRole);

  const [sales, setSales] = useState<SaleListRow[]>([]);
  const [loadingSales, setLoadingSales] = useState(true);
  const [salesError, setSalesError] = useState('');

  const [pendentes, setPendentes] = useState<VendaPendenteGeracao[]>([]);
  const [loadingPend, setLoadingPend] = useState(true);
  const [pendError, setPendError] = useState('');

  const [editId, setEditId] = useState<string | null>(null);
  const [editing, setEditing] = useState<Sale | null>(null);
  const [deleting, setDeleting] = useState<SaleListRow | null>(null);

  const [genClient, setGenClient] = useState<Client | null>(null);
  const [genValue, setGenValue] = useState(0);
  const [genLoadingId, setGenLoadingId] = useState<string | null>(null);

  const [msg, setMsg] = useState('');

  const loadSales = useCallback(async () => {
    setLoadingSales(true);
    setSalesError('');
    try {
      const rows = await saleService.list();
      setSales(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setSalesError(getApiErrorMessage(err, 'Erro ao carregar as vendas.'));
    } finally {
      setLoadingSales(false);
    }
  }, []);

  const loadPendentes = useCallback(async () => {
    setLoadingPend(true);
    setPendError('');
    try {
      const rel = await dashboardService.crmReport({});
      // Backend devolve OBJETO {qtd, itens} — normaliza p/ array antes do .map
      // (objeto direto aqui derrubava a aba com "m.map is not a function").
      const pend = (rel as any)?.vendas_pendentes_geracao;
      setPendentes(Array.isArray(pend) ? pend : (pend?.itens || []));
    } catch (err) {
      setPendError(getApiErrorMessage(err, 'Erro ao carregar pendências de geração.'));
    } finally {
      setLoadingPend(false);
    }
  }, []);

  useEffect(() => { loadSales(); loadPendentes(); }, [loadSales, loadPendentes]);

  const openEdit = async (row: SaleListRow) => {
    setEditId(row.id);
    setMsg('');
    try {
      setEditing(await saleService.get(row.id));
    } catch (err) {
      setMsg(getApiErrorMessage(err, 'Erro ao abrir a venda para edição.'));
      setEditId(null);
    }
  };

  const openGenerate = async (item: VendaPendenteGeracao) => {
    setGenLoadingId(item.client_id);
    setMsg('');
    try {
      const client = await clientService.getById(item.client_id);
      setGenValue(Number(item.valor ?? item.negotiation_value ?? item.estimated_value ?? 0));
      setGenClient(client);
    } catch (err) {
      setMsg(getApiErrorMessage(err, 'Erro ao abrir o cliente para gerar a venda.'));
    } finally {
      setGenLoadingId(null);
    }
  };

  const totalVendido = sales.reduce((acc, s) => acc + Number(s.total_value || 0), 0);

  return (
    <div className="space-y-5">
      {msg && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-amber-500 flex justify-between items-center gap-3">
          <p className="text-xs text-amber-300 font-mono">{msg}</p>
          <button onClick={() => setMsg('')} className="text-zinc-500 hover:text-white cursor-pointer" aria-label="Fechar aviso">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── Vendas realizadas ── */}
      <div className="glass-panel rounded-lg overflow-hidden">
        <div className="p-4 bg-zinc-950/60 border-b border-zinc-900 flex items-center gap-2">
          <ReceiptText className="w-4 h-4 text-emerald-500" />
          <h3 className="text-sm font-semibold text-white font-sans">Vendas realizadas</h3>
          <span className="text-xs font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 ml-auto">
            {sales.length} venda(s) · {fmtBRL(totalVendido)}
          </span>
          <button onClick={loadSales} title="Recarregar vendas"
            className="p-1.5 rounded text-zinc-500 hover:text-white hover:bg-zinc-800 transition cursor-pointer">
            <RefreshCw className={`w-4 h-4 ${loadingSales ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {loadingSales ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-3" />
            <p className="text-zinc-400 font-mono text-xs">Carregando vendas...</p>
          </div>
        ) : salesError ? (
          <p className="text-xs text-red-400 font-mono p-5">{salesError}</p>
        ) : sales.length === 0 ? (
          <p className="text-xs text-zinc-500 font-mono p-5 text-center">Nenhuma venda realizada ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] text-zinc-500 uppercase tracking-widest font-mono border-b border-zinc-900">
                  <th className="px-4 py-3">Código</th>
                  <th className="px-4 py-3">Cliente</th>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3 text-right">Valor</th>
                  <th className="px-4 py-3">Vendedor</th>
                  {canWrite && <th className="px-4 py-3 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {sales.map(s => (
                  <tr key={s.id} className="hover:bg-zinc-900/40 transition">
                    <td className="px-4 py-3 font-mono text-xs text-zinc-300">{s.code}</td>
                    <td className="px-4 py-3 text-white font-sans">{s.client_name || '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-zinc-400">{fmtData(s.sale_date)}</td>
                    <td className="px-4 py-3 font-mono text-sm font-bold text-emerald-400 text-right whitespace-nowrap">{fmtBRL(s.total_value)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-zinc-400">{s.seller_name || '—'}</td>
                    {canWrite && (
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => openEdit(s)} title="Editar data, valor, entrada e parcelas"
                            className="p-1.5 rounded text-zinc-500 hover:text-amber-400 hover:bg-zinc-800 transition cursor-pointer">
                            {editId === s.id && !editing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pencil className="w-4 h-4" />}
                          </button>
                          <button onClick={() => setDeleting(s)} title="Excluir venda"
                            className="p-1.5 rounded text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition cursor-pointer">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Pendentes de geração ── */}
      <div className="glass-panel rounded-lg overflow-hidden border-l-4 border-l-amber-500">
        <div className="p-4 bg-zinc-950/60 border-b border-zinc-900 flex items-center gap-2">
          <UserPlus className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-white font-sans">Fechados sem venda gerada</h3>
          <span className="text-xs font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 ml-auto">
            {pendentes.length}
          </span>
          <button onClick={loadPendentes} title="Recarregar pendências"
            className="p-1.5 rounded text-zinc-500 hover:text-white hover:bg-zinc-800 transition cursor-pointer">
            <RefreshCw className={`w-4 h-4 ${loadingPend ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {loadingPend ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-3" />
            <p className="text-zinc-400 font-mono text-xs">Verificando fechamentos...</p>
          </div>
        ) : pendError ? (
          <p className="text-xs text-red-400 font-mono p-5">{pendError}</p>
        ) : pendentes.length === 0 ? (
          <p className="text-xs text-zinc-500 font-mono p-5 text-center">
            Nenhum fechamento pendente de geração — todo fechado já tem venda gerada.
          </p>
        ) : (
          <ul className="divide-y divide-zinc-900">
            {pendentes.map(p => (
              <li key={p.client_id} className="p-4 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-white font-sans truncate">{p.name}</p>
                  <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                    fechado em {fmtData(p.data || p.closed_at)}
                    {Number(p.valor || 0) > 0 && <> · {fmtBRL(Number(p.valor))}</>}
                  </p>
                </div>
                {canWrite && (
                  <button onClick={() => openGenerate(p)} disabled={genLoadingId === p.client_id}
                    className="shrink-0 px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-medium transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5">
                    {genLoadingId === p.client_id
                      ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      : <BadgeDollarSign className="w-3.5 h-3.5" />}
                    Gerar venda
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Modal Editar */}
      {editing && (
        <SaleEditModal
          sale={editing}
          onClose={() => { setEditing(null); setEditId(null); }}
          onSaved={() => { setEditing(null); setEditId(null); setMsg('Venda atualizada.'); loadSales(); }}
        />
      )}

      {/* Modal Excluir */}
      {deleting && (
        <SaleDeleteModal
          row={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={() => { setDeleting(null); setMsg('Venda excluída.'); loadSales(); }}
        />
      )}

      {/* Fluxo existente de geração */}
      {genClient && (
        <GenerateSaleModal
          client={genClient}
          defaultValue={genValue}
          onClose={() => { setGenClient(null); setGenValue(0); }}
          onSaved={() => {
            setGenClient(null); setGenValue(0);
            setMsg('Venda gerada — contas a receber e Produção criados.');
            loadSales(); loadPendentes();
          }}
        />
      )}
    </div>
  );
}
