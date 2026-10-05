/**
 * Dashboard da producao — indicadores do dono + graficos + tabela.
 *
 * Le /api/reports/production (?year=&month=&period=). Resumo SEM horas
 * (o cliente nao mensura por elas): em producao, atrasados (qtd + valor),
 * entregas previstas, produzido mes/ano com evolucao, retrabalho (qtd +
 * horas perdidas), desperdicio (qtd + material), perdas financeiras em R$
 * e pendencias (checklist em aberto). Reusa o ReportPanel na tabela.
 */
import { useEffect, useState, type ReactNode } from 'react';
import {
  AlertTriangle, BadgeDollarSign, CalendarCheck, ClipboardList,
  Hammer, TrendingDown,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts';
import { reportService, getApiErrorMessage } from '../services/api';
import { ReportResult } from '../types';
import ReportPanel from './ReportPanel';
import PeriodFilter, { MESES_LONGOS } from './PeriodFilter';

function parseBRL(value: string): number {
  const n = Number(String(value || '').replace(/[^\d,-]/g, '').replace(/\./g, '').replace(',', '.'));
  return Number.isFinite(n) ? n : 0;
}

const fmtBRL = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const dataBR = (iso: string | null | undefined) =>
  iso ? iso.slice(0, 10).split('-').reverse().join('/') : '—';

const tooltipStyle = {
  backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px',
};

const tooltipItemStyle = { color: '#f4f4f5' };

const tooltipLabelStyle = { color: '#fff', fontWeight: 700 };

export default function ProductionDashboard() {
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState('');
  const hoje = new Date();
  const [year, setYear] = useState(hoje.getFullYear());
  const [month, setMonth] = useState(hoje.getMonth() + 1);
  const [period, setPeriod] = useState('mensal');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    reportService
      .getReport('production', {
        year: String(year), month: String(month), period,
      })
      .then(r => { if (ativo) setReport(r); })
      .catch(err => {
        if (ativo) setError(getApiErrorMessage(err, 'Erro ao carregar o dashboard da produção.'));
      })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, [year, month, period]);

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setExporting(formato);
    setError('');
    try {
      await reportService.exportReport('production', formato, {
        year: String(year), month: String(month), period,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao exportar o relatório de produção.'));
    } finally {
      setExporting(null);
    }
  };

  const findVal = (labelPart: string) => {
    const it = (report?.summary || []).find(s => s.label.toLowerCase().includes(labelPart.toLowerCase()));
    return it ? it.value : '-';
  };
  const findNum = (labelPart: string) => {
    const it = (report?.summary || []).find(s => s.label.toLowerCase().includes(labelPart.toLowerCase()));
    if (!it) return 0;
    const n = parseInt(String(it.value).replace(/\D/g, ''), 10);
    return Number.isFinite(n) ? n : 0;
  };

  const produzidoMes = report?.produzido_mes;
  const produzidoAno = report?.produzido_ano;
  const entregas = report?.entregas_previstas || [];
  const pend = report?.pendencias;
  const nomeMes = MESES_LONGOS[(produzidoMes?.month ?? month) - 1] || '';
  const evolucao = produzidoAno?.evolucao || [];

  // Ocorrências por tipo (contagem) e custo por tipo (R$)
  const ocorrenciasData = [
    { tipo: 'Retrabalhos', total: findNum('retrabalho') },
    { tipo: 'Desperdícios', total: findNum('desperdicio') },
    { tipo: 'Perdas', total: (() => {
      const cand = (report?.summary || []).find(s => /perda/i.test(s.label) && !/custo/i.test(s.label) && !/financeira/i.test(s.label));
      if (!cand) return 0;
      const n = parseInt(String(cand.value).replace(/\D/g, ''), 10);
      return Number.isFinite(n) ? n : 0;
    })() },
  ];
  const custosData = [
    { tipo: 'Retrabalho', total: parseBRL(String(findVal('custo retrabalho'))) },
    { tipo: 'Desperdício', total: parseBRL(String(findVal('custo desperdicio'))) },
    { tipo: 'Perdas', total: parseBRL(String(findVal('custo perdas'))) },
  ];
  const hasOcorrencias = ocorrenciasData.some(d => d.total > 0);
  const hasCustos = custosData.some(d => d.total > 0);
  const hasEvolucao = evolucao.some(e => (e.total || 0) > 0);

  const card = (
    icon: ReactNode, titulo: string, valor: string, detalhe: string, destaque?: string,
  ) => (
    <div className={`glass-panel p-5 rounded-lg ${destaque || ''}`}>
      <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
        {icon} {titulo}
      </span>
      <p className="text-2xl font-bold font-sans text-white mt-2">{valor}</p>
      <p className="text-[11px] text-zinc-500 font-mono mt-1">{detalhe}</p>
    </div>
  );

  const chartBox = (title: string, subtitle: string, children: ReactNode) => (
    <div className="glass-panel p-5 rounded-lg">
      <h3 className="text-base font-medium text-white">{title}</h3>
      <p className="text-xs text-zinc-400 font-mono mb-4">{subtitle}</p>
      {children}
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="glass-panel px-4 py-3 rounded-lg flex flex-wrap items-center justify-between gap-3">
        <span className="text-[11px] text-zinc-500 font-mono">Período do painel</span>
        <PeriodFilter
          year={year} period={period} month={month}
          onYear={setYear} onPeriod={setPeriod} onMonth={setMonth}
        />
      </div>

      {!loading && report && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {card(
              <Hammer className="w-3 h-3" />,
              'Projetos em produção',
              String(findNum('em produção')),
              'aguardando conclusão',
            )}
            {card(
              <AlertTriangle className="w-3 h-3" />,
              'Projetos atrasados',
              String(findVal('projetos atrasados')).split('·')[0].trim(),
              String(findVal('projetos atrasados')).includes('·')
                ? `valor em atraso: ${String(findVal('projetos atrasados')).split('·')[1].trim()}`
                : 'prazo vencido, sem conclusão',
              'border-l-4 border-l-red-600',
            )}
            {card(
              <CalendarCheck className="w-3 h-3" />,
              'Entregas previstas',
              String(findVal('entregas previstas')),
              entregas.length > 0
                ? `próxima: ${entregas[0].title} · ${dataBR(entregas[0].deadline)}`
                : 'nenhum prazo futuro',
            )}
            {card(
              <ClipboardList className="w-3 h-3" />,
              'Pendências de produção',
              String(pend?.checklist_abertos ?? findVal('pendências de produção')),
              'itens de checklist em aberto',
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {card(
              <BadgeDollarSign className="w-3 h-3" />,
              `Produzido em ${nomeMes}`,
              fmtBRL(produzidoMes?.total ?? parseBRL(String(findVal('produzido no mês')))),
              `${produzidoMes?.qtd ?? 0} projeto(s) concluído(s)`,
              'border-l-4 border-l-emerald-600',
            )}
            {card(
              <BadgeDollarSign className="w-3 h-3" />,
              `Produzido em ${produzidoAno?.year ?? year}`,
              fmtBRL(produzidoAno?.total ?? parseBRL(String(findVal('produzido no ano')))),
              `${produzidoAno?.qtd ?? 0} projeto(s) concluído(s)`,
              'border-l-4 border-l-emerald-600',
            )}
            {card(
              <TrendingDown className="w-3 h-3" />,
              'Retrabalho',
              `${findNum('retrabalho')} · ${String(findVal('horas perdidas'))}`,
              `custo: ${String(findVal('custo retrabalho'))}`,
            )}
            {card(
              <TrendingDown className="w-3 h-3" />,
              'Perdas financeiras',
              String(findVal('perdas financeiras')),
              `desperdício: ${String(findVal('desperdicios'))} · material: ${String(findVal('material desperdiçado'))}`,
            )}
          </div>

          {chartBox(
            'Evolução da capacidade produtiva',
            `Valor concluído por período em ${produzidoAno?.year ?? year} · passe o mouse para ver valores`,
            hasEvolucao ? (
              <div className="h-64 text-xs font-mono">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={evolucao} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="rotulo" stroke="#a1a1aa" tickLine={false} fontSize={11} />
                    <YAxis
                      stroke="#71717a" axisLine={false} tickLine={false}
                      tickFormatter={(v: number) => Number(v || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}
                      width={70}
                    />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      itemStyle={tooltipItemStyle}
                      labelStyle={tooltipLabelStyle}
                      formatter={(v: number, _n: string, entry: any) => [
                        `${fmtBRL(Number(v || 0))} · ${entry.payload.qtd ?? 0} projeto(s)`,
                        'Produzido',
                      ]}
                    />
                    <Bar dataKey="total" name="Produzido" radius={[4, 4, 0, 0]} maxBarSize={28} fill="#b91c1c" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-xs text-zinc-500 font-mono py-8 text-center">Nenhum projeto concluído no ano ainda.</p>
            ),
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {chartBox(
              'Ocorrências por tipo',
              'Retrabalhos, desperdícios e perdas · passe o mouse para ver a contagem',
              hasOcorrencias ? (
                <div className="h-56 text-xs font-mono">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={ocorrenciasData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                      <XAxis dataKey="tipo" stroke="#71717a" tickLine={false} fontSize={11} />
                      <YAxis stroke="#71717a" axisLine={false} tickLine={false} allowDecimals={false} />
                      <Tooltip
                        contentStyle={tooltipStyle}
                        itemStyle={tooltipItemStyle}
                        labelStyle={tooltipLabelStyle}
                        formatter={(v: number) => [`${v} ocorrência(s)`, 'Total']}
                      />
                      <Bar dataKey="total" name="Ocorrências" radius={[4, 4, 0, 0]} maxBarSize={56}>
                        {ocorrenciasData.map((d, i) => (
                          <Cell key={i} fill={['#f59e0b', '#f97316', '#ef4444'][i % 3]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-xs text-zinc-500 font-mono py-8 text-center">Nenhuma ocorrência registrada.</p>
              ),
            )}
            {chartBox(
              'Custo das ocorrências',
              'Quanto cada tipo de ocorrência custou · passe o mouse para ver os valores',
              hasCustos ? (
                <div className="h-56 text-xs font-mono">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={custosData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                      <XAxis dataKey="tipo" stroke="#71717a" tickLine={false} fontSize={11} />
                      <YAxis
                        stroke="#71717a" axisLine={false} tickLine={false}
                        tickFormatter={(v: number) => Number(v || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}
                        width={70}
                      />
                      <Tooltip
                        contentStyle={tooltipStyle}
                        itemStyle={tooltipItemStyle}
                        labelStyle={tooltipLabelStyle}
                        formatter={(v: number) => [fmtBRL(v), 'Custo']}
                      />
                      <Bar dataKey="total" name="Custo" radius={[4, 4, 0, 0]} maxBarSize={56}>
                        {custosData.map((d, i) => (
                          <Cell key={i} fill={['#f59e0b', '#f97316', '#ef4444'][i % 3]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-xs text-zinc-500 font-mono py-8 text-center">Nenhum custo de ocorrência registrado.</p>
              ),
            )}
          </div>

          {entregas.length > 0 && (
            <div className="glass-panel p-5 rounded-lg">
              <h3 className="text-base font-medium text-white">Próximas entregas</h3>
              <p className="text-xs text-zinc-400 font-mono mb-3">Prazo futuro, sem conclusão · por data</p>
              <div className="divide-y divide-zinc-900">
                {entregas.map((e, i) => (
                  <div key={`${e.title}-${i}`} className="py-2.5 flex flex-wrap items-baseline justify-between gap-2 text-xs font-mono">
                    <span className="text-zinc-200 font-sans font-medium">{e.title}
                      <span className="text-zinc-500 font-mono"> · {e.client}</span>
                    </span>
                    <span className="text-zinc-400">{dataBR(e.deadline)}
                      <span className="text-emerald-400 font-semibold"> · {fmtBRL(e.value)}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <ReportPanel
        report={report}
        loading={loading}
        exporting={exporting}
        onExport={exportar}
        loadingLabel="Calculando indicadores..."
        error={error}
      />
    </div>
  );
}
