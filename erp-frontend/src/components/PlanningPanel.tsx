/**
 * Planejamento comercial — meta x realizado por período e por responsável.
 *
 * O "realizado" vem da MESMA definição que a comissão usa (cliente com
 * closed_at no período). Vendas fechadas sem data aparecem no aviso `undated`:
 * clientes antigos fecharam antes do campo existir, e esconder isso faria a
 * meta parecer pior do que foi.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, Loader2, Plus, Target, Trash2 } from 'lucide-react';
import { goalService, commissionService, getApiErrorMessage } from '../services/api';
import { GoalScope, SalesGoal, SalesGoalSummary } from '../types';

const fmt = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const SCOPES: GoalScope[] = ['GERAL', 'VENDEDOR', 'PARCEIRO'];

export default function PlanningPanel() {
  const hoje = new Date();
  const [ano, setAno] = useState(hoje.getFullYear());
  const [mes, setMes] = useState(hoje.getMonth() + 1);
  const [resumo, setResumo] = useState<SalesGoalSummary | null>(null);
  const [metas, setMetas] = useState<SalesGoal[]>([]);
  const [opcoes, setOpcoes] = useState<{ sellers: { id: string; name: string }[]; partners: { id: string; name: string }[] }>({ sellers: [], partners: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aberto, setAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({
    scope: 'GERAL' as GoalScope, who: '', target_value: '',
  });

  const carregar = () => {
    setLoading(true);
    setError('');
    Promise.all([
      goalService.summary({ year: ano, month: mes }),
      goalService.list({ year: ano, month: mes }),
      commissionService.ruleOptions(),
    ])
      .then(([r, m, op]) => { setResumo(r); setMetas(m); setOpcoes(op); })
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar o planejamento.')))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, [ano, mes]);

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    if (form.scope !== 'GERAL' && !form.who) {
      setError('Escolha o responsável pela meta.'); return;
    }
    setSalvando(true);
    setError('');
    try {
      await goalService.create({
        year: ano, month: mes, scope: form.scope,
        user_id: form.scope === 'VENDEDOR' ? form.who : undefined,
        partner_id: form.scope === 'PARCEIRO' ? form.who : undefined,
        target_value: Number(form.target_value || 0),
      });
      setAberto(false);
      setForm({ scope: 'GERAL', who: '', target_value: '' });
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar a meta.'));
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (m: SalesGoal) => {
    if (!window.confirm('Excluir esta meta?')) return;
    try {
      await goalService.remove(m.id);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir a meta.'));
    }
  };

  const anos = Array.from({ length: 5 }, (_, i) => hoje.getFullYear() - 2 + i);
  const nomeDe = (m: SalesGoal) => {
    if (m.scope === 'GERAL') return 'Geral';
    const lista = m.scope === 'VENDEDOR' ? opcoes.sellers : opcoes.partners;
    const id = m.scope === 'VENDEDOR' ? m.user_id : m.partner_id;
    return lista.find(o => o.id === id)?.name || (m.scope === 'VENDEDOR' ? 'vendedor' : 'parceiro');
  };

  return (
    <div className="space-y-5">
      <div className="glass-panel p-4 rounded-lg flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Mês</label>
          <select value={mes} onChange={e => setMes(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            {MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Ano</label>
          <select value={ano} onChange={e => setAno(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            {anos.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div className="ml-auto">
          <button onClick={() => setAberto(v => !v)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer">
            <Plus className="w-3.5 h-3.5" /> Nova meta
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {aberto && (
        <form onSubmit={salvar} className="glass-panel p-5 rounded-lg space-y-4">
          <h3 className="text-sm font-semibold text-white font-sans">
            Meta de {MESES[mes - 1]} de {ano}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Escopo</label>
              <select value={form.scope}
                onChange={e => setForm({ ...form, scope: e.target.value as GoalScope, who: '' })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            {form.scope !== 'GERAL' && (
              <div className="space-y-1.5">
                <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Responsável</label>
                <select value={form.who} required
                  onChange={e => setForm({ ...form, who: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                  <option value="">Selecione…</option>
                  {(form.scope === 'VENDEDOR' ? opcoes.sellers : opcoes.partners)
                    .map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Valor da meta (R$)</label>
              <input type="number" step="0.01" min="0" value={form.target_value} required
                onChange={e => setForm({ ...form, target_value: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-zinc-900">
            <button type="button" onClick={() => setAberto(false)}
              className="px-3.5 py-2 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-xs font-mono uppercase cursor-pointer">
              Cancelar
            </button>
            <button type="submit" disabled={salvando}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60">
              {salvando && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Salvar meta
            </button>
          </div>
        </form>
      )}

      {loading && !resumo ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando planejamento...</p>
        </div>
      ) : resumo && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-panel p-5 rounded-lg">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
                <Target className="w-3 h-3" /> Meta
              </span>
              <p className="text-xl font-bold font-sans text-white mt-2">{resumo.target}</p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">
                base: {resumo.target_basis === 'mes' ? 'mês' : 'ano'}
              </p>
            </div>
            <div className="glass-panel p-5 rounded-lg">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Realizado</span>
              <p className="text-xl font-bold font-sans text-emerald-400 mt-2">{resumo.achieved}</p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">{resumo.deals_closed} venda(s) fechada(s)</p>
            </div>
            <div className="glass-panel p-5 rounded-lg">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Falta</span>
              <p className="text-xl font-bold font-sans text-white mt-2">{resumo.remaining}</p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">{resumo.basis}</p>
            </div>
            <div className="glass-panel p-5 rounded-lg border-l-4 border-l-sky-600">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Atingimento</span>
              <p className="text-xl font-bold font-sans text-sky-400 mt-2">{resumo.percent}</p>
            </div>
          </div>

          {resumo.undated > 0 && (
            <div className="glass-panel p-4 rounded-lg border-l-4 border-l-amber-600 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-300 font-mono">
                {resumo.undated} venda(s) em etapa de ganho sem data de fechamento — fechadas antes
                do sistema registrar a data. Elas não entram no realizado, então a meta está
                subestimada.
              </p>
            </div>
          )}

          <div className="glass-panel rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-zinc-300">
                <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                  <tr>
                    <th className="py-3 px-5 font-normal">Escopo</th>
                    <th className="py-3 px-5 font-normal">Responsável</th>
                    <th className="py-3 px-5 font-normal text-right">Meta</th>
                    <th className="py-3 px-5 font-normal text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {metas.map(m => (
                    <tr key={m.id} className="hover:bg-zinc-900/40">
                      <td className="py-3 px-5 font-mono text-[10px] text-zinc-400">{m.scope}</td>
                      <td className="py-3 px-5 font-sans text-xs">{nomeDe(m)}</td>
                      <td className="py-3 px-5 font-mono text-xs text-right">{fmt(m.target_value)}</td>
                      <td className="py-3 px-5 text-right">
                        <button onClick={() => excluir(m)} title="Excluir meta"
                          className="p-1.5 text-zinc-500 hover:text-rose-500 transition cursor-pointer">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {metas.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-12 text-center text-zinc-500 font-mono">
                        Nenhuma meta cadastrada para {MESES[mes - 1]} de {ano}.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
