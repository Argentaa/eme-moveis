/**
 * Dashboard comercial — resumo do CRM (conversao, ticket medio e negociacoes).
 *
 * Le /api/reports/crm, que tem formato proprio (nao segue {summary, columns,
 * rows}) — por isso o resumo e montado aqui, campo a campo, em vez de passar
 * pelo ReportPanel generico.
 *
 * O ticket medio usa projetos concluidos pelo botao "Concluir" (concluded_at);
 * quando nao ha nenhum, usa as vendas fechadas no CRM (negotiation_value ou
 * valor estimado) — o campo `origem` diz qual base foi usada.
 */
import { useEffect, useState } from 'react';
import { Loader2, Percent, Target, TrendingDown, Users } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
  PieChart, Pie, Legend,
} from 'recharts';
import { dashboardService, getApiErrorMessage } from '../services/api';
import { chartTooltipProps, shortTick } from './FinancialView';
import { CrmReport } from '../types';

const fmt = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const ETAPA_COLORS = ['#7f1d1d', '#b91c1c', '#dc2626', '#ef4444', '#f87171', '#fca5a5'];

const TRENDING_COLORS = ['#059669', '#10b981', '#34d399', '#6ee7b7', '#f59e0b', '#fbbf24', '#ef4444', '#f87171', '#3b82f6', '#60a5fa'];

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
  const totalEtapas = etapas.reduce((acc, e) => acc + e.total, 0);
  const etapasData = [...etapas]
    .sort((a, b) => b.total - a.total)
    .map(e => ({
      etapa: e.funnel_status,
      total: e.total,
      share: totalEtapas > 0 ? (e.total / totalEtapas) * 100 : 0,
    }));

  const fontes = rel.fontes_lead || [];
  const totalFontes = fontes.reduce((acc, f) => acc + f.total, 0);
  const fontesData = [...fontes]
    .sort((a, b) => b.total - a.total)
    .slice(0, 8)
    .map(f => ({
      fonte: f.fonte || 'Não informado',
      total: f.total,
      share: totalFontes > 0 ? (f.total / totalFontes) * 100 : 0,
    }));

  const ticket = rel.ticket_medio;

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
            {fmt(ticket?.media ?? 0)}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            {fmt(ticket?.minimo ?? 0)} a {fmt(ticket?.maximo ?? 0)}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            {ticket?.total_projetos ?? 0} venda(s) · {fmt(ticket?.total_faturado ?? 0)} faturado
          </p>
          <p className="text-[10px] text-zinc-600 font-mono mt-0.5">
            base: {ticket?.origem || 'projetos concluídos'}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
            Produtos mais vendidos
          </span>
          <p className="text-[11px] text-zinc-500 font-mono mt-0.5 mb-3">
            Vendas concluídas · passe o mouse para ver quantidade e receita
          </p>
          {(rel.top_products || []).length === 0 ? (
            <p className="text-xs text-zinc-500 font-mono">Nenhuma venda concluída ainda.</p>
          ) : (
            <div className="h-64 text-xs font-mono">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={rel.top_products as any[]}
                    dataKey="qty"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, share }: any) => `${name} (${share}%)`}
                  >
                    {(rel.top_products || []).map((_, i) => (
                      <Cell key={i} fill={TRENDING_COLORS[i % TRENDING_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    {...chartTooltipProps}
                    formatter={(v: number, _n: string, entry: any) => [
                      `${v} unidade(s) · ${fmt(entry.payload.receita || 0)}`,
                      'Produto',
                    ]}
                  />
                  <Legend formatter={(value: string) => <span style={{ color: '#d4d4d8', fontSize: 11 }}>{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
            Negociações por etapa
          </span>
          <p className="text-[11px] text-zinc-500 font-mono mt-0.5 mb-3">
            Passe o mouse para ver a contagem e a participação de cada etapa
          </p>
          {etapasData.length === 0 ? (
            <p className="text-xs text-zinc-500 font-mono">Nenhuma negociação em aberto.</p>
          ) : (
            <div className="h-64 text-xs font-mono">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={etapasData} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#52525b" hide />
                  <YAxis dataKey="etapa" type="category" stroke="#a1a1aa" width={150} tickLine={false} axisLine={false} tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={(v: string) => shortTick(v)} />
                  <Tooltip
                    {...chartTooltipProps}
                    formatter={(v: number, _n: string, entry: any) => [
                      `${v} negociação(ões) · ${entry.payload.share.toFixed(1)}% do funil`,
                      'Total',
                    ]}
                  />
                  <Bar dataKey="total" name="Negociações" radius={[0, 4, 4, 0]} barSize={14}>
                    {etapasData.map((d, i) => (
                      <Cell key={d.etapa} fill={ETAPA_COLORS[i % ETAPA_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
            Origem dos leads
          </span>
          <p className="text-[11px] text-zinc-500 font-mono mt-0.5 mb-3">
            De onde vêm os clientes · passe o mouse para ver a participação
          </p>
          {fontesData.length === 0 ? (
            <p className="text-xs text-zinc-500 font-mono">Nenhuma origem registrada.</p>
          ) : (
            <div className="h-64 text-xs font-mono">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={fontesData} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#52525b" hide />
                  <YAxis dataKey="fonte" type="category" stroke="#a1a1aa" width={150} tickLine={false} axisLine={false} tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={(v: string) => shortTick(v)} />
                  <Tooltip
                    {...chartTooltipProps}
                    formatter={(v: number, _n: string, entry: any) => [
                      `${v} lead(s) · ${entry.payload.share.toFixed(1)}% dos leads`,
                      'Total',
                    ]}
                  />
                  <Bar dataKey="total" name="Leads" radius={[0, 4, 4, 0]} barSize={14} fill="#b91c1c">
                    {fontesData.map((d, i) => (
                      <Cell key={d.fonte} fill="#b91c1c" fillOpacity={0.55 + (0.45 * (fontesData.length - i)) / fontesData.length} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
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
