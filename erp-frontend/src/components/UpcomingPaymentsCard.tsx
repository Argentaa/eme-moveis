import React, { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, ChevronDown, ChevronUp, Calendar } from 'lucide-react';
import { financialService } from '../services/api';

export default function UpcomingPaymentsCard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [expandedSection, setExpandedSection] = useState<'receivables' | 'payables' | null>(null);

  useEffect(() => {
    setLoading(true);
    financialService.getUpcoming(days)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading || !data) return null;
  if (data.receivables.length === 0 && data.payables.length === 0) return null;

  const formatCurrency = (v: number) =>
    v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  const formatDate = (d: string) =>
    new Date(d + 'T12:00:00').toLocaleDateString('pt-BR');

  return (
    <div className="glass-panel rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-zinc-900 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-red-500" />
          <h3 className="text-sm font-semibold font-sans text-zinc-800 dark:text-white">Próximos Vencimentos</h3>
        </div>
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          className="bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 font-mono text-xs rounded px-2 py-1 focus:outline-none cursor-pointer"
        >
          <option value={3}>3 dias</option>
          <option value={7}>7 dias</option>
          <option value={15}>15 dias</option>
          <option value={30}>30 dias</option>
        </select>
      </div>

      <div className="divide-y divide-zinc-100 dark:divide-zinc-900">
        {/* Contas a Receber */}
        {data.receivables.length > 0 && (
          <div>
            <button
              onClick={() => setExpandedSection(expandedSection === 'receivables' ? null : 'receivables')}
              className="w-full flex items-center justify-between p-4 hover:bg-zinc-50 dark:hover:bg-zinc-900/40 transition cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <ArrowUpRight className="w-4 h-4 text-emerald-500" />
                <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 font-sans">A Receber</span>
                <span className="text-[10px] font-mono text-zinc-400 bg-zinc-100 dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-800">
                  {data.receivables.length}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  {formatCurrency(data.total_receivables)}
                </span>
                {expandedSection === 'receivables' ? <ChevronUp className="w-3.5 h-3.5 text-zinc-400" /> : <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />}
              </div>
            </button>
            {expandedSection === 'receivables' && (
              <div className="divide-y divide-zinc-100 dark:divide-zinc-900 border-t border-zinc-100 dark:border-zinc-900">
                {data.receivables.map((r: any) => (
                  <div key={r.id} className="flex justify-between items-start px-4 py-2.5 pl-10">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-200 font-sans truncate">{r.description}</p>
                      <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                        Vence: {formatDate(r.due_date)}
                        {r.client_name && ` · ${r.client_name}`}
                      </p>
                    </div>
                    <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 ml-3 shrink-0">
                      {formatCurrency(Number(r.amount))}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Contas a Pagar */}
        {data.payables.length > 0 && (
          <div>
            <button
              onClick={() => setExpandedSection(expandedSection === 'payables' ? null : 'payables')}
              className="w-full flex items-center justify-between p-4 hover:bg-zinc-50 dark:hover:bg-zinc-900/40 transition cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <ArrowDownRight className="w-4 h-4 text-red-500" />
                <span className="text-sm font-semibold text-red-600 dark:text-red-400 font-sans">A Pagar</span>
                <span className="text-[10px] font-mono text-zinc-400 bg-zinc-100 dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-800">
                  {data.payables.length}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold font-mono text-red-600 dark:text-red-400">
                  {formatCurrency(data.total_payables)}
                </span>
                {expandedSection === 'payables' ? <ChevronUp className="w-3.5 h-3.5 text-zinc-400" /> : <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />}
              </div>
            </button>
            {expandedSection === 'payables' && (
              <div className="divide-y divide-zinc-100 dark:divide-zinc-900 border-t border-zinc-100 dark:border-zinc-900">
                {data.payables.map((r: any) => (
                  <div key={r.id} className="flex justify-between items-start px-4 py-2.5 pl-10">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-200 font-sans truncate">{r.description}</p>
                      <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                        Vence: {formatDate(r.due_date)}
                        {r.project_title && ` · ${r.project_title}`}
                      </p>
                    </div>
                    <span className="text-xs font-mono font-bold text-red-600 dark:text-red-400 ml-3 shrink-0">
                      {formatCurrency(Number(r.amount))}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
