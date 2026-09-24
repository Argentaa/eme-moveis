/**
 * Dashboard comercial — resumo do CRM (conversao, ticket medio e negociacoes).
 *
 * Le /api/reports/crm, que tem formato proprio (nao segue {summary, columns,
 * rows}) — por isso o resumo e montado aqui, campo a campo, em vez de passar
 * pelo ReportPanel generico.
 */
import { useEffect, useState } from 'react';
import { Loader2, Percent, Target, TrendingDown, Users } from 'lucide-react';
import { dashboardService, getApiErrorMessage } from '../services/api';
import { CrmReport } from '../types';

const fmt = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export default function CommercialDashboard() {
  const [rel, setRel] = useState<CrmReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardService
      .crmReport()
      .then(setRel)
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar o dashboard comercial.')))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
        <p className="text-zinc-400 font-mono text-xs">Calculando o comercial...</p>
      </div>
    );
  }

  if (error || !rel) {
    return (
      <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
        <p className="text-xs text-red-400 font-mono">{error || 'Sem dados do CRM.'}</p>
      </div>
    );
  }

  const etapas = rel.negociacoes?.por_etapa || [];
  const maiorEtapa = Math.max(1, ...etapas.map(e => e.total));

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
            <Users className="w-3 h-3" /> Clientes no CRM
          </span>
          <p className="text-2xl font-bold font-sans text-white mt-2">
            {rel.conversao?.total_clientes ?? 0}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            {rel.conversao?.total_fechamentos ?? 0} fechamento(s)
          </p>
        </div>
        <div className="glass-panel p-5 rounded-lg border-l-4 border-l-emerald-600">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
            <Percent className="w-3 h-3" /> Conversão
          </span>
          <p className="text-2xl font-bold font-sans text-emerald-400 mt-2">
            {Number(rel.conversao?.taxa ?? 0).toFixed(1)}%
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">fechamentos ÷ clientes</p>
        </div>
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
            <Target className="w-3 h-3" /> Ticket médio
          </span>
          <p className="text-2xl font-bold font-sans text-white mt-2">
            {fmt(rel.ticket_medio?.media ?? 0)}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            {fmt(rel.ticket_medio?.minimo ?? 0)} a {fmt(rel.ticket_medio?.maximo ?? 0)}
          </p>
        </div>
        <div className="glass-panel p-5 rounded-lg border-l-4 border-l-rose-650">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
            <TrendingDown className="w-3 h-3" /> Perdidas
          </span>
          <p className="text-2xl font-bold font-sans text-rose-500 mt-2">
            {rel.negociacoes?.total_perdidas ?? 0}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            de {rel.negociacoes?.total ?? 0} negociação(ões)
          </p>
        </div>
      </div>

      <div className="glass-panel p-5 rounded-lg">
        <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block mb-3">
          Negociações por etapa
        </span>
        <div className="space-y-2">
          {etapas.map(e => (
            <div key={e.funnel_status} className="flex items-center gap-3">
              <span className="w-32 text-[11px] font-mono text-zinc-400 truncate">{e.funnel_status}</span>
              <div className="flex-1 h-4 bg-zinc-950 rounded overflow-hidden border border-zinc-900">
                <div className="h-full bg-red-900/50"
                  style={{ width: `${Math.round((e.total / maiorEtapa) * 100)}%` }} />
              </div>
              <span className="w-10 text-right text-xs font-mono text-white">{e.total}</span>
            </div>
          ))}
          {etapas.length === 0 && (
            <p className="text-xs text-zinc-500 font-mono">Nenhuma negociação em aberto.</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block mb-3">
            Origem dos leads
          </span>
          <div className="space-y-1.5">
            {(rel.fontes_lead || []).slice(0, 8).map(f => (
              <div key={f.fonte} className="flex items-center justify-between text-xs font-mono">
                <span className="text-zinc-400 truncate">{f.fonte || '—'}</span>
                <span className="text-white">{f.total}</span>
              </div>
            ))}
            {!(rel.fontes_lead || []).length && (
              <p className="text-xs text-zinc-500 font-mono">Nenhuma origem registrada.</p>
            )}
          </div>
        </div>
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block mb-3">
            Motivos de perda
          </span>
          <div className="space-y-1.5">
            {(rel.negociacoes?.perdidas || []).slice(0, 6).map((p, i) => (
              <div key={`${p.name}-${i}`} className="text-xs font-mono">
                <span className="text-zinc-300">{p.name}</span>
                <span className="block text-[10px] text-zinc-500">{p.lost_reason || 'sem motivo informado'}</span>
              </div>
            ))}
            {!(rel.negociacoes?.perdidas || []).length && (
              <p className="text-xs text-zinc-500 font-mono">Nenhuma perda registrada.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
