/**
 * Pendencias de producao: ocorrencias (retrabalho / desperdicio / perda) e
 * itens de checklist ainda em aberto, com o custo do periodo somado.
 *
 * Os dois CRUDs existem em outros lugares (ocorrencia e por projeto, checklist
 * fica no projeto). Esta aba e a visao cruzada que a spec pede — o que esta
 * pendente hoje, em todos os projetos, e quanto isso custou.
 */
import { useEffect, useState } from 'react';
import { AlertTriangle, ClipboardList, Loader2, TrendingDown } from 'lucide-react';
import { productionService, getApiErrorMessage } from '../services/api';
import { ProductionPending } from '../types';

const KIND_LABEL: Record<string, string> = {
  RETRABALHO: 'Retrabalho',
  DESPERDICIO: 'Desperdício',
  PERDA: 'Perda',
};

const KIND_TONE: Record<string, string> = {
  RETRABALHO: 'text-amber-400 border-l-amber-600',
  DESPERDICIO: 'text-zinc-300 border-l-zinc-700',
  PERDA: 'text-rose-500 border-l-red-650',
};

const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const dataBR = (iso: string | null | undefined) =>
  iso ? iso.slice(0, 10).split('-').reverse().join('/') : '—';

/** Primeiro e ultimo dia do mes corrente, para o filtro abrir util. */
function mesCorrente() {
  const h = new Date();
  const primeiro = new Date(h.getFullYear(), h.getMonth(), 1);
  const ultimo = new Date(h.getFullYear(), h.getMonth() + 1, 0);
  const iso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  return { de: iso(primeiro), ate: iso(ultimo) };
}

export default function ProductionPendingPanel() {
  const inicial = mesCorrente();
  const [de, setDe] = useState(inicial.de);
  const [ate, setAte] = useState(inicial.ate);
  const [dados, setDados] = useState<ProductionPending | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    productionService
      .getPending({ from: de, to: ate })
      .then((d) => { if (ativo) setDados(d); })
      .catch((err) => {
        if (ativo) setError(getApiErrorMessage(err, 'Erro ao carregar as pendências.'));
      })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, [de, ate]);

  return (
    <div className="space-y-5">
      <div className="glass-panel p-4 rounded-lg flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">De</label>
          <input type="date" value={de} onChange={e => setDe(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Até</label>
          <input type="date" value={ate} onChange={e => setAte(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando pendências...</p>
        </div>
      ) : dados ? (
        <>
          {/* Resumo */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass-panel p-5 rounded-lg border-l-4 border-l-red-650">
              <div className="flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-rose-500" />
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
                  Custo das ocorrências
                </span>
              </div>
              <p className="text-2xl font-bold font-sans text-rose-500 mt-2">
                {fmt(dados.issues_total_cost)}
              </p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">
                {dados.issues_count} ocorrência(s) no período
              </p>
            </div>
            <div className="glass-panel p-5 rounded-lg border-l-4 border-l-amber-600">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
                  Checklist em aberto
                </span>
              </div>
              <p className="text-2xl font-bold font-sans text-white mt-2">
                {dados.checklist_count}
              </p>
              <p className="text-[11px] text-zinc-500 font-mono mt-1">item(ns) não concluído(s)</p>
            </div>
            <div className="glass-panel p-5 rounded-lg">
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
                Por tipo de ocorrência
              </span>
              <div className="mt-2 space-y-1">
                {Object.entries(dados.issues_by_kind)
                  .map(([k, v]) => [k, v as { count: number; cost: number }] as const)
                  .map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-zinc-400">{KIND_LABEL[k] || k}</span>
                    <span className="text-zinc-300">{v.count} · {fmt(v.cost)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Ocorrencia sem custo lancada: o total nao pode fingir que ela nao existe */}
          {dados.issues_without_cost > 0 && (
            <p className="text-[11px] text-amber-400 font-mono">
              {dados.issues_without_cost} ocorrência(s) sem valor lançado — contam no total como zero.
            </p>
          )}

          {/* Ocorrencias */}
          <div className="glass-panel rounded-lg overflow-hidden">
            <div className="p-4 border-b border-zinc-900">
              <h3 className="text-sm font-semibold text-white font-sans">Ocorrências do período</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-zinc-300">
                <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                  <tr>
                    <th className="py-3 px-5 font-normal">Data</th>
                    <th className="py-3 px-5 font-normal">Projeto</th>
                    <th className="py-3 px-5 font-normal">Tipo</th>
                    <th className="py-3 px-5 font-normal">Motivo</th>
                    <th className="py-3 px-5 font-normal text-right">Custo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {dados.issues.map(i => (
                    <tr key={i.id} className="hover:bg-zinc-900/40">
                      <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">{dataBR(i.issue_date)}</td>
                      <td className="py-3 px-5 font-sans text-xs">{i.project_title || '—'}</td>
                      <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded border ${KIND_TONE[i.kind] || 'text-zinc-300 border-zinc-700'}`}>
                          {KIND_LABEL[i.kind] || i.kind}
                        </span>
                      </td>
                      <td className="py-3 px-5 font-sans text-xs">{i.reason || '—'}</td>
                      <td className="py-3 px-5 font-mono text-xs text-right whitespace-nowrap text-rose-500">
                        {i.cost == null ? 'sem valor' : fmt(Number(i.cost))}
                      </td>
                    </tr>
                  ))}
                  {dados.issues.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-zinc-500 font-mono">
                        Nenhuma ocorrência no período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Checklist em aberto */}
          <div className="glass-panel rounded-lg overflow-hidden">
            <div className="p-4 border-b border-zinc-900 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white font-sans">Checklist em aberto</h3>
              <span className="text-[10px] text-zinc-500 font-mono">
                todos os projetos
              </span>
            </div>
            <div className="divide-y divide-zinc-900">
              {dados.checklist.map(c => (
                <div key={c.id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <span className="text-xs font-sans text-zinc-300 min-w-0">{c.label}</span>
                  <span className="text-[10px] text-zinc-500 font-mono shrink-0">
                    {c.project_title || 'projeto removido'}
                  </span>
                </div>
              ))}
              {dados.checklist.length === 0 && (
                <p className="px-5 py-10 text-center text-zinc-500 font-mono text-xs">
                  Nenhum item de checklist em aberto.
                </p>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
