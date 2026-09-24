/**
 * Orcamentos/Propostas — o documento que o vendedor manda ao cliente.
 *
 * O total mostrado e sempre o dos itens (o backend recalcula a cada gravacao),
 * entao nao existe proposta cujo valor nao bate com o que esta escrito nela.
 *
 * Envio: se a Evolution API estiver configurada, a mensagem sai direto e a
 * proposta vira ENVIADA. Se nao estiver, o botao abre o wa.me com a mensagem
 * pronta — e a proposta continua RASCUNHO, porque abrir o link nao prova que a
 * mensagem foi enviada.
 */
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Check, FileText, Loader2, MessageCircle, Pencil, Plus, Trash2, X,
} from 'lucide-react';
import { proposalService, clientService, getApiErrorMessage } from '../services/api';
import { Client, Proposal, ProposalStatus } from '../types';

const fmt = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const STATUS_TONE: Record<string, string> = {
  RASCUNHO: 'text-zinc-400 border-zinc-700',
  ENVIADA: 'text-sky-400 border-sky-900/50',
  ACEITA: 'text-emerald-400 border-emerald-900/50',
  RECUSADA: 'text-rose-400 border-rose-900/50',
};

const STATUSES: ProposalStatus[] = ['RASCUNHO', 'ENVIADA', 'ACEITA', 'RECUSADA'];

interface ItemForm { description: string; quantity: string; unit_price: string }

const itemVazio = (): ItemForm => ({ description: '', quantity: '1', unit_price: '' });

export default function ProposalsPanel() {
  const [propostas, setPropostas] = useState<Proposal[]>([]);
  const [clientes, setClientes] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [filtro, setFiltro] = useState('');
  const [aberto, setAberto] = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [enviandoId, setEnviandoId] = useState<string | null>(null);
  const [form, setForm] = useState({
    client_id: '', valid_until: '', notes: '', items: [itemVazio()],
  });

  const carregar = () => {
    setLoading(true);
    proposalService
      .list(filtro ? { status: filtro } : {})
      .then(setPropostas)
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar as propostas.')))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, [filtro]);
  useEffect(() => {
    clientService.getAll().then(setClientes).catch(() => setClientes([]));
  }, []);

  const totalForm = useMemo(
    () => form.items.reduce(
      (s, i) => s + (Number(i.quantity || 0) * Number(i.unit_price || 0)), 0),
    [form.items],
  );

  const abrirNova = () => {
    setEditandoId(null);
    setForm({ client_id: '', valid_until: '', notes: '', items: [itemVazio()] });
    setAberto(true);
    setError('');
  };

  const abrirEdicao = (p: Proposal) => {
    setEditandoId(p.id);
    setForm({
      client_id: p.client_id,
      valid_until: p.valid_until || '',
      notes: p.notes || '',
      items: p.items.length
        ? p.items.map(i => ({
            description: i.description,
            quantity: String(i.quantity),
            unit_price: String(i.unit_price),
          }))
        : [itemVazio()],
    });
    setAberto(true);
    setError('');
  };

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.client_id) { setError('Escolha o cliente.'); return; }
    const items = form.items
      .filter(i => i.description.trim())
      .map(i => ({
        description: i.description.trim(),
        quantity: Number(i.quantity || 0),
        unit_price: Number(i.unit_price || 0),
      }));
    if (!items.length) { setError('A proposta precisa de pelo menos um item.'); return; }

    setSalvando(true);
    setError('');
    try {
      const payload = {
        client_id: form.client_id, valid_until: form.valid_until || null,
        notes: form.notes, items,
      };
      if (editandoId) await proposalService.update(editandoId, payload);
      else await proposalService.create(payload);
      setAberto(false);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar a proposta.'));
    } finally {
      setSalvando(false);
    }
  };

  const mudarStatus = async (p: Proposal, status: ProposalStatus) => {
    try {
      const atual = await proposalService.update(p.id, { status });
      setPropostas(ps => ps.map(x => (x.id === atual.id ? atual : x)));
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao mudar o status.'));
    }
  };

  const excluir = async (p: Proposal) => {
    if (!window.confirm(`Excluir a proposta ${p.number}?`)) return;
    try {
      await proposalService.remove(p.id);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir a proposta.'));
    }
  };

  const baixarPdf = async (p: Proposal) => {
    try {
      await proposalService.downloadPdf(p.id, p.number);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao gerar o PDF.'));
    }
  };

  const enviar = async (p: Proposal) => {
    setEnviandoId(p.id);
    setError('');
    setAviso('');
    try {
      const r = await proposalService.sendWhatsapp(p.id);
      setPropostas(ps => ps.map(x => (x.id === r.proposal.id ? r.proposal : x)));
      if (r.sent) {
        setAviso(`${p.number} enviada pelo WhatsApp.`);
      } else if (r.fallback_wa_me) {
        window.open(r.fallback_wa_me, '_blank', 'noopener');
        setAviso(`${r.detail}. Abri o WhatsApp com a mensagem pronta — a proposta segue como rascunho até você confirmar o envio.`);
      } else {
        setError(r.detail);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao enviar a proposta.'));
    } finally {
      setEnviandoId(null);
    }
  };

  if (loading && !propostas.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
        <p className="text-zinc-400 font-mono text-xs">Carregando propostas...</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="glass-panel p-4 rounded-lg flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Status</label>
          <select value={filtro} onChange={e => setFiltro(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            <option value="">Todas</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="ml-auto">
          <button onClick={abrirNova}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer">
            <Plus className="w-3.5 h-3.5" /> Nova proposta
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}
      {aviso && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-sky-600 flex items-start gap-2">
          <p className="text-xs text-sky-300 font-mono flex-1">{aviso}</p>
          <button onClick={() => setAviso('')} className="text-zinc-500 hover:text-white cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {aberto && (
        <form onSubmit={salvar} className="glass-panel p-5 rounded-lg space-y-4">
          <h3 className="text-sm font-semibold text-white font-sans">
            {editandoId ? 'Editar proposta' : 'Nova proposta'}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Cliente</label>
              <select value={form.client_id} required
                onChange={e => setForm({ ...form, client_id: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="">Selecione…</option>
                {clientes.filter(c => !c.is_supplier).map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Válida até</label>
              <input type="date" value={form.valid_until}
                onChange={e => setForm({ ...form, valid_until: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Itens</span>
            {form.items.map((it, idx) => (
              <div key={idx} className="flex flex-wrap items-center gap-2">
                <input type="text" placeholder="Descrição do item" value={it.description}
                  onChange={e => setForm({
                    ...form,
                    items: form.items.map((x, i) => i === idx ? { ...x, description: e.target.value } : x),
                  })}
                  className="flex-1 min-w-[180px] bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                <input type="number" step="0.01" min="0" placeholder="Qtd" value={it.quantity}
                  onChange={e => setForm({
                    ...form,
                    items: form.items.map((x, i) => i === idx ? { ...x, quantity: e.target.value } : x),
                  })}
                  className="w-20 bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                <input type="number" step="0.01" min="0" placeholder="Preço" value={it.unit_price}
                  onChange={e => setForm({
                    ...form,
                    items: form.items.map((x, i) => i === idx ? { ...x, unit_price: e.target.value } : x),
                  })}
                  className="w-28 bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                <span className="w-24 text-right text-xs font-mono text-zinc-400">
                  {fmt(Number(it.quantity || 0) * Number(it.unit_price || 0))}
                </span>
                <button type="button" title="Remover item"
                  onClick={() => setForm({
                    ...form,
                    items: form.items.length > 1 ? form.items.filter((_, i) => i !== idx) : [itemVazio()],
                  })}
                  className="p-1.5 text-zinc-500 hover:text-rose-500 transition cursor-pointer">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
            <button type="button"
              onClick={() => setForm({ ...form, items: [...form.items, itemVazio()] })}
              className="flex items-center gap-1 text-[11px] font-mono uppercase text-zinc-400 hover:text-white transition cursor-pointer">
              <Plus className="w-3 h-3" /> Adicionar item
            </button>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Observações</label>
            <textarea rows={2} value={form.notes}
              onChange={e => setForm({ ...form, notes: e.target.value })}
              className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none resize-none" />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-zinc-900">
            <span className="text-sm font-mono text-white">
              Total: <strong>{fmt(totalForm)}</strong>
            </span>
            <div className="flex gap-2">
              <button type="button" onClick={() => setAberto(false)}
                className="px-3.5 py-2 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-xs font-mono uppercase cursor-pointer">
                Cancelar
              </button>
              <button type="submit" disabled={salvando}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60">
                {salvando && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Salvar
              </button>
            </div>
          </div>
        </form>
      )}

      <div className="glass-panel rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
              <tr>
                <th className="py-3 px-5 font-normal">Número</th>
                <th className="py-3 px-5 font-normal">Cliente</th>
                <th className="py-3 px-5 font-normal">Status</th>
                <th className="py-3 px-5 font-normal">Validade</th>
                <th className="py-3 px-5 font-normal">Envio</th>
                <th className="py-3 px-5 font-normal text-right">Total</th>
                <th className="py-3 px-5 font-normal text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {propostas.map(p => (
                <tr key={p.id} className="hover:bg-zinc-900/40">
                  <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">{p.number}</td>
                  <td className="py-3 px-5 font-sans text-xs">{p.client_name || '—'}</td>
                  <td className="py-3 px-5">
                    <select value={p.status} onChange={e => mudarStatus(p, e.target.value as ProposalStatus)}
                      className={`bg-zinc-950 border rounded px-2 py-1 text-[10px] font-mono uppercase focus:outline-none cursor-pointer ${STATUS_TONE[p.status] || ''}`}>
                      {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                    {p.valid_until ? p.valid_until.split('-').reverse().join('/') : '—'}
                  </td>
                  <td className="py-3 px-5 font-mono text-[10px] text-zinc-400 whitespace-nowrap">
                    {p.sent_channel ? `${p.sent_channel}` : 'não enviada'}
                  </td>
                  <td className="py-3 px-5 font-mono text-xs text-right whitespace-nowrap">
                    {fmt(p.total_value)}
                    <span className="block text-[10px] text-zinc-500">{p.items.length} item(ns)</span>
                  </td>
                  <td className="py-3 px-5">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => baixarPdf(p)} title="Baixar PDF"
                        className="p-1.5 text-zinc-500 hover:text-white transition cursor-pointer">
                        <FileText className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => enviar(p)} disabled={enviandoId === p.id}
                        title="Enviar pelo WhatsApp" data-testid="enviar-whatsapp"
                        className="p-1.5 text-zinc-500 hover:text-emerald-400 transition cursor-pointer disabled:opacity-50">
                        {enviandoId === p.id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <MessageCircle className="w-3.5 h-3.5" />}
                      </button>
                      <button onClick={() => abrirEdicao(p)} title="Editar"
                        className="p-1.5 text-zinc-500 hover:text-white transition cursor-pointer">
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => excluir(p)} title="Excluir"
                        className="p-1.5 text-zinc-500 hover:text-rose-500 transition cursor-pointer">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {propostas.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-zinc-500 font-mono">
                    Nenhuma proposta {filtro ? `com status ${filtro}` : 'cadastrada'}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {propostas.length > 0 && (
        <p className="text-[11px] text-zinc-500 font-mono flex items-center gap-1">
          <Check className="w-3 h-3" /> O total de cada proposta é sempre a soma dos itens.
        </p>
      )}
    </div>
  );
}
