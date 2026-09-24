/**
 * Apresentacao de um relatorio (cards de resumo + tabela + exportacao).
 *
 * Puramente visual: nao busca nada. Quem monta e dono do estado e dos
 * filtros, e passa `report`/`loading`/`exporting`/`onExport`. Existe para o
 * DRE e o Dashboard da producao nao duplicarem a mesma tabela.
 */
import React from 'react';
import { FileSpreadsheet, FileText, Loader2, RefreshCw } from 'lucide-react';
import { ReportResult } from '../types';

export const TONE_CLASSES: Record<string, string> = {
  positive: 'text-emerald-400 border-l-emerald-600',
  negative: 'text-rose-500 border-l-red-650',
  neutral: 'text-white border-l-zinc-700',
};

export const inputClass = "w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs focus:outline-none focus:border-red-656 font-mono";

export function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      {label && <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">{label}</label>}
      {children}
    </div>
  );
}

interface ReportPanelProps {
  report: ReportResult | null;
  loading?: boolean;
  exporting?: string | null;
  onExport?: (formato: 'pdf' | 'xlsx') => void;
  /** Texto do estado de carregamento, ex.: "Calculando DRE...". */
  loadingLabel?: string;
  error?: string;
  /** Filtros extras (selects de periodo etc.) renderizados acima do resumo. */
  children?: React.ReactNode;
}

export default function ReportPanel({
  report, loading, exporting, onExport, loadingLabel = 'Carregando relatório...', error, children,
}: ReportPanelProps) {
  return (
    <div className="space-y-5">
      {children && (
        <div className="glass-panel p-5 rounded-lg flex flex-wrap items-end gap-4">
          {children}
        </div>
      )}

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">{loadingLabel}</p>
        </div>
      ) : report ? (
        <div className="space-y-5">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div>
              <h2 className="text-lg font-serif text-white">{report.title}</h2>
              <p className="text-[11px] text-zinc-500 font-mono">
                Gerado em {report.generated_at} — {report.rows.length} registro(s)
              </p>
            </div>
            {onExport && (
              <div className="flex gap-2">
                <button
                  onClick={() => onExport('pdf')}
                  disabled={exporting != null}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-red-950/40 border border-zinc-800 hover:border-red-900/40 text-zinc-300 hover:text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                >
                  {exporting === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                  PDF
                </button>
                <button
                  onClick={() => onExport('xlsx')}
                  disabled={exporting != null}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-emerald-950/40 border border-zinc-800 hover:border-emerald-900/40 text-zinc-300 hover:text-emerald-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                >
                  {exporting === 'xlsx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                  Excel
                </button>
              </div>
            )}
          </div>

          {report.summary.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {report.summary.map((item, idx) => (
                <div key={idx} className={`glass-panel p-4 rounded-lg border-l-4 ${TONE_CLASSES[item.tone || 'neutral']}`}>
                  <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">{item.label}</span>
                  <p className={`text-lg font-bold font-sans mt-1 ${TONE_CLASSES[item.tone || 'neutral'].split(' ')[0]}`}>
                    {item.value}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="glass-panel rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-zinc-300">
                <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                  <tr>
                    {report.columns.map(col => (
                      <th key={col.key} className="py-3.5 px-5 font-normal whitespace-nowrap">{col.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {report.rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-zinc-900/40">
                      {report.columns.map(col => (
                        <td key={col.key} className="py-3 px-5 font-sans text-xs whitespace-nowrap">
                          {row[col.key] ?? '-'}
                        </td>
                      ))}
                    </tr>
                  ))}

                  {report.rows.length === 0 && (
                    <tr>
                      <td colSpan={report.columns.length} className="py-12 text-center text-zinc-500 font-mono">
                        Nenhum registro encontrado para os filtros selecionados.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
