/**
 * Modal "Gerar venda" do Comercial.
 *
 * Substitui o antigo "Concluir venda": cadastra a venda completa (cliente,
 * vendedor, parceiro, origem, data, valor, entrada/parcelas/vencimentos/conta
 * bancaria, produtos vendidos, ambientes, endereco e entrega). Ao salvar, o
 * POST /api/sales conclui a venda (sai do funil) e cria as contas a receber
 * e os cards de producao (um por ambiente).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { X, Plus, Trash2, Loader2, BadgeDollarSign, Calculator } from 'lucide-react';
import {
  authService, bankAccountService, leadOptionService, partnerService,
  productService, saleService, getApiErrorMessage,
} from '../services/api';
import { BankAccount, Client, LeadOption, Partner, Product, Sale, User } from '../types';

const ENV_SUGGESTIONS = ['Sala', 'Cozinha', 'Gourmet', 'Quarto', 'Banheiro', 'Lavanderia', 'Escritório', 'Closet'];

const inputClass =
  'w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600';

const fmtBRL = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

function addMonths(dateStr: string, months: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  if (isNaN(d.getTime())) return '';
  d.setMonth(d.getMonth() + months);
  return d.toISOString().substring(0, 10);
}

interface SaleItemRow {
  product_id?: string;
  name: string;
  quantity: number;
  unit_price: number;
}

interface Props {
  client: Client;
  defaultValue: number;
  onClose: () => void;
  onSaved: (sale: Sale) => void;
}

export default function GenerateSaleModal({ client, defaultValue, onClose, onSaved }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [banks, setBanks] = useState<BankAccount[]>([]);
  const [sources, setSources] = useState<LeadOption[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingRefs, setLoadingRefs] = useState(true);

  const today = new Date().toISOString().substring(0, 10);
  const plus30 = new Date(Date.now() + 30 * 86400000).toISOString().substring(0, 10);

  const [form, setForm] = useState({
    sale_date: today,
    total_value: String(defaultValue > 0 ? defaultValue : ''),
    down_payment: '',
    installments: '',
    installment_value: '',
    installments_due: [] as string[],
    bank_account_id: '',
    seller_id: (client as any).seller_id || '',
    partner_id: (client as any).partner_id || '',
    lead_source: (client as any).lead_source || '',
    address: '',
    delivery_date: plus30,
  });
  const [environments, setEnvironments] = useState<string[]>([]);
  const [newEnv, setNewEnv] = useState('');
  const [items, setItems] = useState<SaleItemRow[]>([]);
  const [itemProductId, setItemProductId] = useState('');
  const [itemQty, setItemQty] = useState('1');
  const [itemPrice, setItemPrice] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setLoadingRefs(true);
    Promise.all([
      authService.getUsers().catch(() => [] as User[]),
      partnerService.list().catch(() => [] as Partner[]),
      bankAccountService.list().catch(() => [] as BankAccount[]),
      leadOptionService.getSources().catch(() => [] as LeadOption[]),
      productService.list().catch(() => [] as Product[]),
    ])
      .then(([us, ps, bs, ss, pds]) => {
        if (!active) return;
        setUsers(us);
        setPartners(ps);
        setBanks(bs);
        setSources(ss);
        setProducts(pds.filter(p => p.active !== false));
      })
      .finally(() => { if (active) setLoadingRefs(false); });
    return () => { active = false; };
  }, [client.id]);

  const total = Number(form.total_value) || 0;
  const nInstallments = Number(form.installments) || 0;
  const down = Number(form.down_payment) || 0;
  const installmentValue = Number(form.installment_value) || 0;
  const sum = down + nInstallments * installmentValue;
  const sumDiff = Math.abs(sum - total) > 0.01;
  const itemsSum = items.reduce((acc, it) => acc + (it.quantity || 0) * (it.unit_price || 0), 0);
  const itemsDiff = Math.abs(itemsSum - total) > 0.01 && items.length > 0;

  const setInstallments = (raw: string) => {
    const n = Number(raw) || 0;
    setForm(prev => {
      const due = Array.from({ length: n }, (_, i) =>
        (prev.installments_due[i] || addMonths(prev.sale_date || today, i + 1) || ''));
      let pv = prev.installment_value;
      if (n > 0 && (total - down) > 0) pv = String(Math.round(((total - down) / n) * 100) / 100);
      else if (n === 0) pv = '';
      return { ...prev, installments: raw, installments_due: due, installment_value: pv };
    });
  };

  const setDueAt = (idx: number, value: string) => {
    setForm(prev => {
      const due = [...prev.installments_due];
      due[idx] = value;
      return { ...prev, installments_due: due };
    });
  };

  const setDownPayment = (raw: string) => {
    setForm(prev => {
      let pv = prev.installment_value;
      const d = Number(raw) || 0;
      const n = Number(prev.installments) || 0;
      if (n > 0 && (total - d) > 0) pv = String(Math.round(((total - d) / n) * 100) / 100);
      return { ...prev, down_payment: raw, installment_value: pv };
    });
  };

  const toggleEnv = (name: string) => {
    setEnvironments(prev => prev.includes(name) ? prev.filter(x => x !== name) : [...prev, name]);
  };
  const addEnvCustom = () => {
    const name = newEnv.trim();
    if (name && !environments.includes(name)) setEnvironments(prev => [...prev, name]);
    setNewEnv('');
  };

  const chooseProduct = (pid: string) => {
    setItemProductId(pid);
    const prod = products.find(p => p.id === pid);
    if (prod && prod.default_price) setItemPrice(String(prod.default_price));
  };
  const addItem = () => {
    const prod = products.find(p => p.id === itemProductId);
    const name = prod?.name || '';
    if (!name) return;
    if (!(Number(itemQty) > 0)) return;
    setItems(prev => [...prev, {
      product_id: prod?.id,
      name,
      quantity: Number(itemQty),
      unit_price: Number(itemPrice) || 0,
    }]);
    setItemProductId('');
    setItemQty('1');
    setItemPrice('');
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (sumDiff) {
      setError('Entrada + parcelas não fecha com o valor total da venda.');
      return;
    }
    if (saving) return;
    setSaving(true);
    setError('');
    try {
      const sale = await saleService.create({
        client_id: client.id,
        seller_id: form.seller_id || undefined,
        partner_id: form.partner_id || undefined,
        lead_source: form.lead_source,
        sale_date: form.sale_date,
        total_value: total,
        down_payment: down,
        installments: nInstallments,
        installment_value: installmentValue,
        installments_due: nInstallments > 0 ? form.installments_due : [],
        bank_account_id: form.bank_account_id || undefined,
        address: form.address,
        delivery_date: form.delivery_date || undefined,
        environments,
        items: items.map(it => ({
          product_id: it.product_id || undefined,
          name: it.name,
          quantity: it.quantity,
          unit_price: it.unit_price,
        })),
      });
      onSaved(sale);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao gerar a venda.'));
    } finally {
      setSaving(false);
    }
  };

  const canSubmit = !sumDiff && !saving;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-panel w-full max-w-2xl rounded-lg flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 shrink-0">
          <div className="flex items-center gap-2">
            <BadgeDollarSign className="w-5 h-5 text-emerald-500" />
            <div>
              <h3 className="text-base font-serif font-semibold text-white">Gerar venda</h3>
              <p className="text-xs text-zinc-400 font-mono mt-0.5">
                {client.name} — conclui a venda, cria contas a receber e a Produção
              </p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="text-zinc-500 hover:text-white cursor-pointer font-mono text-xs">Sair</button>
        </div>

        <form onSubmit={submit} className="p-6 space-y-5 overflow-y-auto flex-1 overscroll-contain">
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{error}</div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Vendedor responsável</label>
              <select value={form.seller_id} onChange={e => setForm({ ...form, seller_id: e.target.value })}
                className={inputClass} disabled={loadingRefs}>
                <option value="">— Sem vendedor —</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Arquiteto / Parceiro</label>
              <select value={form.partner_id} onChange={e => setForm({ ...form, partner_id: e.target.value })}
                className={inputClass} disabled={loadingRefs}>
                <option value="">— Sem parceiro —</option>
                {partners.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Origem da venda</label>
              <select value={form.lead_source} onChange={e => setForm({ ...form, lead_source: e.target.value })}
                className={inputClass} disabled={loadingRefs}>
                <option value="">— Sem origem —</option>
                {sources.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data da venda *</label>
              <input type="date" required value={form.sale_date}
                onChange={e => setForm({ ...form, sale_date: e.target.value })}
                className={inputClass} />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor total (R$) *</label>
              <input type="number" step="0.01" min="0.01" required value={form.total_value}
                onChange={e => setForm({ ...form, total_value: e.target.value })}
                placeholder="Ex: 15000" className={inputClass} />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Conta bancária de destino</label>
              <select value={form.bank_account_id} onChange={e => setForm({ ...form, bank_account_id: e.target.value })}
                className={inputClass} disabled={loadingRefs}>
                <option value="">— Sem conta —</option>
                {banks.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-lg space-y-4 border border-zinc-800">
            <div className="flex items-center gap-2">
              <Calculator className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-widest font-mono">Condições de pagamento</h4>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Entrada (R$)</label>
                <input type="number" step="0.01" min="0" value={form.down_payment}
                  onChange={e => setDownPayment(e.target.value)}
                  placeholder="Ex: 3000" className={inputClass} />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nº de parcelas</label>
                <input type="number" min="0" max="60" value={form.installments}
                  onChange={e => setInstallments(e.target.value)}
                  placeholder="0 = à vista" className={inputClass} />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor das parcelas (R$)</label>
                <input type="number" step="0.01" min="0" value={form.installment_value}
                  onChange={e => setForm({ ...form, installment_value: e.target.value })}
                  placeholder="Calculado" className={inputClass} />
              </div>
            </div>
            <p className={`text-[11px] font-mono ${sumDiff ? 'text-red-400' : 'text-zinc-500'}`}>
              Entrada + parcelas: {fmtBRL(sum)} · valor da venda: {fmtBRL(total)}
              {sumDiff ? ' — não fecha com o valor total!' : ''}
            </p>
            {nInstallments > 0 && (
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Vencimentos das parcelas</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {form.installments_due.map((due, i) => (
                    <input key={i} type="date" required value={due}
                      onChange={e => setDueAt(i, e.target.value)}
                      className={inputClass} title={`Parcela ${i + 1}`} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Produtos vendidos */}
          <div className="glass-panel p-4 rounded-lg space-y-3 border border-zinc-800">
            <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-widest font-mono">Produtos vendidos</h4>
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_90px_120px_auto] gap-2">
              <select value={itemProductId} onChange={e => chooseProduct(e.target.value)} className={inputClass}>
                <option value="">Selecionar produto do catálogo...</option>
                {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input type="number" min="1" value={itemQty} onChange={e => setItemQty(e.target.value)}
                placeholder="Qtd" className={inputClass} />
              <input type="number" step="0.01" min="0" value={itemPrice} onChange={e => setItemPrice(e.target.value)}
                placeholder="R$ unit." className={inputClass} />
              <button type="button" onClick={addItem}
                className="px-3 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-sm transition cursor-pointer flex items-center justify-center">
                <Plus className="w-4 h-4" />
              </button>
            </div>
            {items.length > 0 && (
              <div className="space-y-1.5">
                {items.map((it, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm bg-zinc-900 border border-zinc-800 rounded px-3 py-2">
                    <span className="flex-1 text-zinc-200">{it.name}</span>
                    <span className="text-zinc-400 font-mono text-xs">{it.quantity} x {fmtBRL(it.unit_price)}</span>
                    <span className="text-zinc-200 font-mono text-xs">{fmtBRL(it.quantity * it.unit_price)}</span>
                    <button type="button" onClick={() => setItems(prev => prev.filter((_, i) => i !== idx))}
                      className="text-zinc-500 hover:text-red-400 cursor-pointer">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <p className={`text-[11px] font-mono ${itemsDiff ? 'text-amber-400' : 'text-zinc-500'}`}>
                  Soma dos produtos: {fmtBRL(itemsSum)}
                  {itemsDiff ? ` — difere do valor total (${fmtBRL(total)}). Pode seguir: o contrato é o total.` : ''}
                </p>
              </div>
            )}
          </div>

          {/* Ambientes vendidos */}
          <div className="glass-panel p-4 rounded-lg space-y-3 border border-zinc-800">
            <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-widest font-mono">Ambientes vendidos</h4>
            <p className="text-[11px] text-zinc-500 font-mono">Cada ambiente vira um card separado no Kanban de Produção.</p>
            <div className="flex flex-wrap gap-2">
              {ENV_SUGGESTIONS.map(env => {
                const on = environments.includes(env);
                return (
                  <button key={env} type="button" onClick={() => toggleEnv(env)}
                    className={`px-3 py-1.5 text-xs rounded border transition cursor-pointer ${on
                      ? 'bg-emerald-700/30 border-emerald-600 text-emerald-300'
                      : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-600'}`}>
                    {on ? '✓ ' : ''}{env}
                  </button>
                );
              })}
            </div>
            <div className="flex gap-2">
              <input value={newEnv} onChange={e => setNewEnv(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addEnvCustom(); } }}
                placeholder="Outro ambiente (Ex: Varanda gourmet)"
                className="flex-1 bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-2.5 text-sm focus:outline-none focus:border-red-600" />
              <button type="button" onClick={addEnvCustom}
                className="px-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded text-sm transition cursor-pointer">
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Endereço da obra</label>
              <textarea value={form.address} onChange={e => setForm({ ...form, address: e.target.value })}
                rows={2} placeholder="Ex: Rua das Acácias, 123, Apto 402"
                className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 resize-none" />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data prevista de entrega</label>
              <input type="date" value={form.delivery_date}
                onChange={e => setForm({ ...form, delivery_date: e.target.value })}
                className={inputClass} />
            </div>
          </div>

          <button type="submit" disabled={!canSubmit}
            className="w-full py-3 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-sm font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Gerar venda — concluir e criar automações
          </button>
        </form>
      </div>
    </div>
  );
}