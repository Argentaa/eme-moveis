/**
 * Dashboard da producao — cards de resumo + graficos + tabela de /api/reports/production.
 *
 * Nao ha endpoint de dashboard proprio: o relatorio de producao ja traz o
 * `summary` que a spec pede. Reusa o ReportPanel para nao duplicar a tabela.
 * m² e horas produtivas NAO aparecem aqui (o cliente nao mensura por eles).
 */
import { useEffect, useState, type ReactNode } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts';
import { reportService, getApiErrorMessage } from '../services/api';
import { ReportResult } from '../types';
import ReportPanel from './ReportPanel';

function parseBRL(value: string): number {
  const n = Number(String(value || '').replace(/[^\d,-]/g, '').replace(/\./g, '').replace(',', '.'));
  return Number.isFinite(n) ? n : 0;
}

const fmtBRL = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const tooltipStyle = {
  backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px',
};

export default function ProductionDashboard() {
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    reportService
      .getReport('production', {})
      .then(r => { if (ativo) setReport(r); })
      .catch(err => {
        if (ativo) setError(getApiErrorMessage(err, 'Erro ao carregar o dashboard da produção.'));
      })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, []);

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setExporting(formato);
    setError('');
    try {
      await reportService.exportReport('production', formato, {});
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

  // Ocorrências por tipo (contagem) e custo por tipo (R$)
  const ocorrenciasData = [
    { tipo: 'Retrabalhos', total: findNum('retrabalho') },
    { tipo: 'Desperdícios', total: findNum('desperdicio') },
    { tipo: 'Perdas', total: (() => {
      const cand = (report?.summary || []).find(s => /perda/i.test(s.label) && !/custo/i.test(s.label));
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

  const chartBox = (title: string, subtitle: string, children: ReactNode) => (
    <div className="glass-panel p-5 rounded-lg">
      <h3 className="text-base font-medium text-white">{title}</h3>
      <p className="text-xs text-zinc-400 font-mono mb-4">{subtitle}</p>
      {children}
    </div>
  );

  return (
    <div className="space-y-5">
      {!loading && report && (
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
