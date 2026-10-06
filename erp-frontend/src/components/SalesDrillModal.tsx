/**
 * Modal de drill-down das vendas do período (pedido do dono, vídeo 2026-10-01):
 * clicar no card ("2 vendas realizadas") abre quais vendas e de qual cliente.
 *
 * Presentational: recebe os itens prontos (fechamentos_periodo.itens,
 * vendas_mes.itens ou vendas_ano.itens do /api/reports/crm) — sem fetch.
 */
import { X, ReceiptText } from 'lucide-react';
import { FechamentoItem } from '../types';

interface SalesDrillModalProps {
  open: boolean;
  onClose: () => void;
  titulo: string;
  subtitulo?: string;
  itens: FechamentoItem[];
  undated?: number;
}

const fmtBRL = (v: number) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtData = (iso: string | null) => {
  if (!iso) return '—';
  const d = iso.slice(0, 10).split('-');
  return d.length === 3 ? `${d[2]}/${d[1]}/${d[0]}` : iso.slice(0, 10);
};

export default function SalesDrillModal({ open, onClose, titulo, subtitulo, itens, undated }: SalesDrillModalProps) {
  if (!open) return null;
  const total = itens.reduce((acc, i) => acc + Number(i.valor || 0), 0);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="glass-panel rounded-lg w-full max-w-lg max-h-[92vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start p-5 border-b border-zinc-900 shrink-0">
          <div>
            <h3 className="text-base font-semibold text-white font-sans flex items-center gap-2">
              <ReceiptText className="w-4 h-4 text-red-500" />
              {titulo}
            </h3>
            {subtitulo && <p className="text-[11px] text-zinc-500 font-mono mt-1">{subtitulo}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded text-zinc-500 hover:text-white hover:bg-zinc-800 transition cursor-pointer"
            aria-label="Fechar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 overscroll-contain p-5">
          {itens.length === 0 ? (
            <p className="text-xs text-zinc-500 font-mono text-center py-8">
              Nenhuma venda fechada neste período.
            </p>
          ) : (
            <ul className="divide-y divide-zinc-900">
              {itens.map((it, idx) => (
                <li key={`${it.client_id || 's'}-${idx}`} className="py-3 flex justify-between items-center gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-white font-sans truncate">{it.name}</p>
                    <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                      {fmtData(it.data)}
                      <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] ${it.origem === 'sale' ? 'bg-emerald-950/60 text-emerald-400' : 'bg-zinc-900 text-zinc-400'}`}>
                        {it.origem === 'sale' ? 'Gerar venda' : 'CRM'}
                      </span>
                    </p>
                  </div>
                  <p className="text-sm font-bold font-mono text-emerald-400 whitespace-nowrap">
                    {fmtBRL(it.valor)}
                  </p>
                </li>
              ))}
            </ul>
          )}
          {undated != null && undated > 0 && (
            <p className="text-[11px] text-amber-400 font-mono mt-3">
              + {undated} fechamento(s) sem data de fechamento (fluxo antigo) — fora da conta do período.
            </p>
          )}
        </div>
        <div className="p-4 border-t border-zinc-900 shrink-0 flex justify-between items-center">
          <span className="text-[11px] text-zinc-500 font-mono uppercase tracking-widest">
            {itens.length} venda(s)
          </span>
          <span className="text-base font-bold font-sans text-white">{fmtBRL(total)}</span>
        </div>
      </div>
    </div>
  );
}
