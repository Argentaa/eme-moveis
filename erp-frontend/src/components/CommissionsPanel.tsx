/**
 * Comissoes — regras (percentual + vigencia) e o que elas dao no periodo.
 *
 * A comissao e recalculada das vendas fechadas do periodo a cada consulta, nao
 * e um valor congelado: mudar o percentual hoje nao reescreve o mes passado.
 *
 * Vendas fechadas sem vendedor atribuido aparecem num aviso proprio. Elas
 * existem (clientes antigos nasceram antes do campo), e mostra-las e melhor do
 * que ratear entre todos e apresentar um total que ninguem consegue conferir.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, Loader2, Percent, Plus, Trash2 } from 'lucide-react';
import { commissionService, getApiErrorMessage } from '../services/api';
import { CommissionReport, CommissionRule } from '../types';

const fmt = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

export default function CommissionsPanel() {
  const hoje = new Date();
  const [ano, setAno] = useState(hoje.getFullYear());
  const [mes, setMes] = useState(hoje.getMonth() + 1);
  const [rel, setRel] = useState<CommissionReport | null>(null);
  const [regras, setRegras] = useState<CommissionRule[]>([]);
  const [opcoes, setOpcoes] = useState<{ sellers: { id: string; name: string }[]; partners: { id: string; name: string }[] }>({ sellers: [], partners: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aberto, setAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({
    kind: 'VENDEDOR' as 'VENDEDOR' | 'PARCEIRO',
    who: '', percent: '', valid_from: '', valid_until: '', notes: '',
  });

  const carregar = () => {
    setLoading(true);
    setError('');
    Promise.all([
      commissionService.report({ year: ano, month: mes }),
      commissionService.listRules(),
      commissionService.ruleOptions(),
    ])
      .then(([r, rs, op]) => { setRel(r); setRegras(rs); setOpcoes(op); })
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar as comissões.')))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, [ano, mes]);

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.who) { setError('Escolha quem recebe a comissão.'); return; }
    setSalvando(true);
    setError('');
    try {
      await commissionService.createRule({
        seller_id: form.kind === 'VENDEDOR' ? form.who : undefined,
        partner_id: form.kind === 'PARCEIRO' ? form.who : undefined,
        percent: Number(form.percent || 0),
        valid_from: form.valid_from || undefined,
        valid_until: form.valid_until || undefined,
        notes: form.notes,
      });
      setAberto(false);
      setForm({ kind: 'VENDEDOR', who: '', percent: '', valid_from: '', valid_until: '', notes: '' });
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar a regra.'));
    } finally {
      setSalvando(false);
    }
  };

  const alternarAtiva = async (r: CommissionRule) => {
    try {
      await commissionService.updateRule(r.id, { active: !r.active });
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao alterar a regra.'));
    }
  };

  const excluir = async (r: CommissionRule) => {
    if (!window.confirm('Excluir esta regra de comissão?')) return;
    try {
      await commissionService.removeRule(r.id);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir a regra.'));
    }
  };

  const anos = Array.from({ length: 5 }, (_, i) => hoje.getFullYear() - 2 + i);

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
            <Plus className="w-3.5 h-3.5" /> Nova regra
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
          <h3 className="text-sm font-semibold text-white font-sans">Nova regra de comissão</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Tipo</label>
              <select value={form.kind}
                onChange={e => setForm({ ...form, kind: e.target.value as 'VENDEDOR' | 'PARCEIRO', who: '' })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="VENDEDOR">Vendedor</option>
                <option value="PARCEIRO">Parceiro/Arquiteto</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">
                {form.kind === 'VENDEDOR' ? 'Vendedor' : 'Parceiro'}
              </label>
              <select value={form.who} required
                onChange={e => setForm({ ...form, who: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="">Selecione…</option>
                {(form.kind === 'VENDEDOR' ? opcoes.sellers : opcoes.partners)
                  .map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Percentual (%)</label>
              <input type="number" step="0.01" min="0" max="100" value={form.percent} required
                onChange={e => setForm({ ...form, percent: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Vigente a partir de</label>
              <input type="date" value={form.valid_from}
                onChange={e => setForm({ ...form, valid_from: e.target.value })}
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
              Salvar regra
            </button>
          </div>
        </form>
      )}

      {loading && !rel ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando comissões...</p>
        </div>
      ) : rel && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass-panel p-5 rounded-lg">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Vendido no período</span>
              <p className="text-2xl font-bold font-sans text-white mt-2">{fmt(rel.total_sold)}</p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">{rel.closed_count} venda(s) fechada(s)</p>
            </div>
            <div className="glass-panel p-5 rounded-lg border-l-4 border-l-emerald-600">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Comissão a pagar</span>
              <p className="text-2xl font-bold font-sans text-emerald-400 mt-2">{fmt(rel.total_commission)}</p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">soma das regras vigentes</p>
            </div>
            <div className={`glass-panel p-5 rounded-lg ${rel.sem_atribuicao.count ? 'border-l-4 border-l-amber-600' : ''}`}>
              <div className="flex items-center gap-2">
                <AlertTriangle className={`w-4 h-4 ${rel.sem_atribuicao.count ? 'text-amber-500' : 'text-zinc-600'}`} />
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Sem vendedor</span>
              </div>
              <p className="text-2xl font-bold font-sans text-amber-400 mt-2">{fmt(rel.sem_atribuicao.sold_value)}</p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">
                {rel.sem_atribuicao.count} venda(s) que não entram na conta de ninguém
              </p>
            </div>
          </div>

          <div className="glass-panel rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-zinc-300">
                <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                  <tr>
                    <th className="py-3 px-5 font-normal">Quem recebe</th>
                    <th className="py-3 px-5 font-normal">Tipo</th>
                    <th className="py-3 px-5 font-normal text-right">%</th>
                    <th className="py-3 px-5 font-normal text-right">Vendas</th>
                    <th className="py-3 px-5 font-normal text-right">Vendido</th>
                    <th className="py-3 px-5 font-normal text-right">Comissão</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {rel.rows.map(r => (
                    <tr key={r.rule_id} className="hover:bg-zinc-900/40">
                      <td className="py-3 px-5 font-sans text-xs">{r.name}</td>
                      <td className="py-3 px-5 font-mono text-[10px] text-zinc-400">{r.kind}</td>
                      <td className="py-3 px-5 font-mono text-xs text-right">{r.percent}%</td>
                      <td className="py-3 px-5 font-mono text-xs text-right">{r.sales_count}</td>
                      <td className="py-3 px-5 font-mono text-xs text-right">{fmt(r.sold_value)}</td>
                      <td className="py-3 px-5 font-mono text-xs text-right text-emerald-400 font-bold">
                        {fmt(r.commission_value)}
                      </td>
                    </tr>
                  ))}
                  {rel.rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-500 font-mono">
                        Nenhuma regra vigente neste período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="glass-panel rounded-lg overflow-hidden">
            <div className="px-5 py-3 border-b border-zinc-905 bg-zinc-950/70">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
                <Percent className="w-3 h-3" /> Regras cadastradas
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-zinc-300">
                <tbody className="divide-y divide-zinc-900">
                  {regras.map(r => (
                    <tr key={r.id} className={r.active ? '' : 'opacity-50'}>
                      <td className="py-3 px-5 font-sans text-xs">
                        {r.seller_name || r.partner_name || '—'}
                        <span className="block text-[10px] text-zinc-500 font-mono">
                          {r.seller_id ? 'VENDEDOR' : 'PARCEIRO'}
                        </span>
                      </td>
                      <td className="py-3 px-5 font-mono text-xs">{r.percent}%</td>
                      <td className="py-3 px-5 font-mono text-[10px] text-zinc-500">
                        {r.valid_from || r.valid_until
                          ? `${r.valid_from || '—'} até ${r.valid_until || '—'}`
                          : 'sem vigência'}
                      </td>
                      <td className="py-3 px-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button onClick={() => alternarAtiva(r)}
                            className="px-2 py-1 bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white rounded text-[10px] font-mono uppercase cursor-pointer">
                            {r.active ? 'Desativar' : 'Ativar'}
                          </button>
                          <button onClick={() => excluir(r)} title="Excluir regra"
                            className="p-1.5 text-zinc-500 hover:text-rose-500 transition cursor-pointer">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {regras.length === 0 && (
                    <tr>
                      <td className="py-8 text-center text-zinc-500 font-mono">
                        Nenhuma regra cadastrada ainda.
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
