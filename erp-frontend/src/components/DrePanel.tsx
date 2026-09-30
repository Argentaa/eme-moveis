/**
 * Painel do DRE (Demonstrativo de Resultado do Exercicio).
 *
 * Dono do proprio estado (ano, periodo, carregamento, export); a apresentacao
 * base fica no ReportPanel, compartilhado com o Dashboard da producao. Aqui
 * em cima vao os graficos e o detalhamento por categoria: de onde veio cada
 * real de receita, para onde foi cada real de despesa e o resultado final.
 *
 * Os helpers de apresentacao sao reexportados daqui porque o ReportsView ja
 * os importava deste arquivo.
 */
import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid,
} from 'recharts';
import { reportService, getApiErrorMessage } from '../services/api';
import { ReportResult } from '../types';
import ReportPanel, { TONE_CLASSES, inputClass, FilterField } from './ReportPanel';

export { TONE_CLASSES, inputClass, FilterField };

interface DreCategory {
  tipo: string;
  categoria: string;
  total: number;
  total_fmt: string;
  participacao: number;
}

/** Converte "R$ 1.000,00" / "R$ -300,00" em número, para o gráfico. */
function parseBRL(value: string): number {
  const n = Number(String(value || '').replace(/[^\d,-]/g, '').replace(/\./g, '').replace(',', '.'));
  return Number.isFinite(n) ? n : 0;
}

const fmtBRL = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtBRLshort = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

const tooltipStyle = {
  backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px',
};

export default function DrePanel() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [period, setPeriod] = useState('mensal');
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    reportService
      .getReport('dre', { year: String(year), period })
      .then((r) => { if (ativo) setReport(r); })
      .catch((err) => {
        if (ativo) setError(getApiErrorMessage(err, 'Erro ao carregar o DRE. Tente novamente.'));
      })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, [year, period]);

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setExporting(formato);
    setError('');
    try {
      await reportService.exportReport('dre', formato, { year: String(year), period });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao exportar o DRE.'));
    } finally {
      setExporting(null);
    }
  };

  const chartData = (report?.rows || []).map((row: any) => ({
    periodo: String(row.period || ''),
    Receitas: parseBRL(String(row.income || '')),
    Despesas: parseBRL(String(row.outcome || '')),
    Resultado: parseBRL(String(row.result || '')),
  }));

  const byCategory = (((report as any)?.by_category || []) as DreCategory[]);
  const receitasCat = byCategory.filter(c => c.tipo === 'receita');
  const despesasCat = byCategory.filter(c => c.tipo === 'despesa');
  const maxReceita = Math.max(1, ...receitasCat.map(c => c.total));
  const maxDespesa = Math.max(1, ...despesasCat.map(c => c.total));

  const catRow = (c: DreCategory, max: number, bar: string) => (
    <div key={`${c.tipo}-${c.categoria}`}>
      <div className="flex justify-between items-baseline gap-3 text-xs font-mono">
        <span className="text-zinc-300 truncate">{c.categoria}</span>
        <span className="text-white font-semibold whitespace-nowrap">
          {c.total_fmt} <span className="text-zinc-500 font-normal">· {c.participacao.toFixed(1)}%</span>
        </span>
      </div>
      <div className="h-1.5 bg-zinc-950 rounded mt-1 overflow-hidden border border-zinc-900">
        <div className="h-full rounded" style={{ width: `${Math.min(100, (c.total / max) * 100)}%`, background: bar }} />
      </div>
    </div>
  );

  return (
    <div className="space-y-5">
      <ReportPanel
        report={report}
        loading={loading}
        exporting={exporting}
        onExport={exportar}
        loadingLabel="Calculando DRE..."
        error={error}
      >
        <FilterField label="Ano">
          <select value={year} onChange={e => setYear(Number(e.target.value))} className={inputClass}>
            {[year - 1, year, year + 1].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Período">
          <select value={period} onChange={e => setPeriod(e.target.value)} className={inputClass}>
            <option value="mensal">Mensal</option>
            <option value="trimestral">Trimestral</option>
            <option value="semestral">Semestral</option>
            <option value="anual">Anual</option>
          </select>
        </FilterField>
      </ReportPanel>

      {!loading && report && chartData.length > 0 && (
        <>
          <div className="glass-panel p-5 rounded-lg">
            <h3 className="text-base font-medium text-white">Receitas × Despesas × Resultado</h3>
            <p className="text-xs text-zinc-400 font-mono mb-4">
              Passe o mouse sobre as barras para ver os valores de cada período
            </p>
            <div className="h-64 text-xs font-mono">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="periodo" stroke="#71717a" tickLine={false} fontSize={10} />
                  <YAxis stroke="#71717a" axisLine={false} tickLine={false} tickFormatter={fmtBRLshort} width={85} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v: number, name: string) => [fmtBRL(v), name]}
                  />
                  <Legend iconSize={8} wrapperStyle={{ paddingTop: '10px' }} />
                  <Bar dataKey="Receitas" fill="#10b981" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Despesas" fill="#ef4444" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Resultado" fill="#e4e4e7" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="glass-panel p-5 rounded-lg">
              <h3 className="text-base font-medium text-white">De onde veio o dinheiro</h3>
              <p className="text-xs text-zinc-400 font-mono mb-4">Receitas pagas por categoria no ano</p>
              {receitasCat.length === 0 ? (
                <p className="text-xs text-zinc-500 font-mono">Sem receitas no período.</p>
              ) : (
                <div className="space-y-3">{receitasCat.map(c => catRow(c, maxReceita, '#10b981'))}</div>
              )}
            </div>
            <div className="glass-panel p-5 rounded-lg">
              <h3 className="text-base font-medium text-white">Para onde foi o dinheiro</h3>
              <p className="text-xs text-zinc-400 font-mono mb-4">Despesas pagas por categoria no ano</p>
              {despesasCat.length === 0 ? (
                <p className="text-xs text-zinc-500 font-mono">Sem despesas no período.</p>
              ) : (
                <div className="space-y-3">{despesasCat.map(c => catRow(c, maxDespesa, '#ef4444'))}</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
