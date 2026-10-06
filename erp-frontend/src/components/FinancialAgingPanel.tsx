/**
 * Contas em aberto com aging por vencimento — a pagar (SAIDA) ou a receber (ENTRADA).
 *
 * Um componente parametrizado em vez de dois blocos quase iguais, porque as
 * duas abas do Financeiro so mudam o tipo, os rotulos e a cor.
 *
 * Os numeros NAO sao recalculados aqui: vem de /api/financial/aging. O
 * backend e a unica fonte do aging — se a regra de bucket mudar, muda num
 * lugar so. A lista de lancamentos vem de /api/financial com filtro
 * server-side de tipo + status.
 */
import { useEffect, useState } from 'react';
import { AlertTriangle, Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import { financialService, getApiErrorMessage } from '../services/api';
import { AgingResult, FinancialRecord, FinancialType } from '../types';

interface FinancialAgingPanelProps {
  type: FinancialType;
}

const fmt = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/** Ordem e rotulo dos buckets, espelhando as chaves de /api/financial/aging. */
const BUCKETS: { key: 'vencidas' | '0_7' | '8_30' | 'acima_30'; label: string; tone: string }[] = [
  { key: 'vencidas', label: 'Vencidas', tone: 'text-rose-500 border-l-red-650' },
  { key: '0_7', label: 'Vence em até 7 dias', tone: 'text-amber-400 border-l-amber-600' },
  { key: '8_30', label: 'De 8 a 30 dias', tone: 'text-zinc-300 border-l-zinc-700' },
  { key: 'acima_30', label: 'Acima de 30 dias', tone: 'text-zinc-400 border-l-zinc-800' },
];

/**
 * Dias entre hoje e o vencimento, com o MESMO sinal do backend:
 * positivo = ja venceu (em atraso), 0 = vence hoje, negativo = ainda vai vencer.
 *
 * O sinal importa: invertido, conta vencida apareceria como "em N dia(s)",
 * ou seja, como se ainda fosse vencer.
 */
function diasAte(vencimento: string | null | undefined): number | null {
  if (!vencimento) return null;
  const alvo = new Date(`${vencimento.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(alvo.getTime())) return null;
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  return Math.round((hoje.getTime() - alvo.getTime()) / 86400000);
}

/**
 * Bucket de um lançamento, com a MESMA regra do backend (/api/financial/aging):
 * dias > 0 = vencida; -7..0 = 0_7; -30..-8 = 8_30; resto = acima_30.
 * Sem vencimento ('sem') só aparece sem filtro, como no backend.
 */
function bucketDe(vencimento: string | null | undefined): string {
  const d = diasAte(vencimento);
  if (d === null) return 'sem';
  if (d > 0) return 'vencidas';
  if (d >= -7) return '0_7';
  if (d >= -30) return '8_30';
  return 'acima_30';
}

export default function FinancialAgingPanel({ type }: FinancialAgingPanelProps) {
  const [aging, setAging] = useState<AgingResult | null>(null);
  const [registros, setRegistros] = useState<FinancialRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // Drill-down (pedido do dono, vídeo 2026-10-01): clicar no bucket filtra a
  // lista abaixo p/ mostrar QUAL conta está em cada faixa; clica de novo e limpa.
  const [filtro, setFiltro] = useState<string | null>(null);

  const aPagar = type === 'SAIDA';
  const titulo = aPagar ? 'Contas a Pagar' : 'Contas a Receber';

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    Promise.all([
      financialService.aging(type),
      financialService.getAll({ type, status: 'PENDENTE' }),
    ])
      .then(([a, lista]) => {
        if (!ativo) return;
        setAging(a);
        setRegistros(lista);
      })
      .catch((err) => {
        if (ativo) setError(getApiErrorMessage(err, `Erro ao carregar ${titulo}.`));
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, [type, titulo]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
        <p className="text-zinc-400 font-mono text-xs">Carregando {titulo}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
        <p className="text-xs text-red-400 font-mono">{error}</p>
      </div>
    );
  }

  if (!aging) return null;

  const Icone = aPagar ? TrendingDown : TrendingUp;
  const alternar = (chave: string) => setFiltro((atual) => (atual === chave ? null : chave));
  const visiveis = filtro ? registros.filter((r) => bucketDe(r.due_date) === filtro) : registros;
  const rotuloFiltro = filtro ? BUCKETS.find((b) => b.key === filtro)?.label : null;

  return (
    <div className="space-y-5">
      {/* Total em aberto */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div
          className={`glass-panel p-5 rounded-lg border-l-4 ${
            aPagar ? 'border-l-red-650' : 'border-l-emerald-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <Icone className={`w-4 h-4 ${aPagar ? 'text-rose-500' : 'text-emerald-400'}`} />
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
              {titulo} em aberto
            </span>
          </div>
          <p className="text-2xl font-bold font-sans text-white mt-2">
            {fmt(aging.open_total)}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            {aging.open_count} lançamento(s) pendente(s)
          </p>
        </div>

        <button
          type="button"
          onClick={() => alternar('vencidas')}
          title="Mostrar quais contas estão vencidas"
          className={`text-left glass-panel p-5 rounded-lg border-l-4 border-l-red-650 transition cursor-pointer hover:border hover:border-zinc-700 ${filtro === 'vencidas' ? 'ring-2 ring-red-600' : ''}`}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
              Vencidas
            </span>
          </div>
          <p className="text-2xl font-bold font-sans text-rose-500 mt-2">
            {fmt(aging.buckets.vencidas.total)}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            {aging.buckets.vencidas.count} lançamento(s) em atraso · clique p/ ver
          </p>
        </button>
      </div>

      {/* Aging */}
      <div className="glass-panel rounded-lg p-5 space-y-4">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-white font-sans">Aging por vencimento</h3>
          <span className="text-[10px] text-zinc-500 font-mono">
            referência: {aging.reference_date}
          </span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {BUCKETS.map((b) => (
            <button
              key={b.key}
              type="button"
              onClick={() => alternar(b.key)}
              title={`Mostrar quais contas: ${b.label}`}
              className={`text-left glass-panel p-4 rounded-lg border-l-4 ${b.tone} transition cursor-pointer hover:border hover:border-zinc-700 ${filtro === b.key ? 'ring-2 ring-red-600' : ''}`}
            >
              <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
                {b.label}
              </span>
              <p className={`text-lg font-bold font-sans mt-1 ${b.tone.split(' ')[0]}`}>
                {fmt(aging.buckets[b.key].total)}
              </p>
              <p className="text-[10px] text-zinc-500 font-mono mt-0.5">
                {aging.buckets[b.key].count} lançamento(s)
              </p>
            </button>
          ))}
        </div>

        {/* Lancamentos sem vencimento nao entram em bucket: aparecem a parte
            para a soma dos buckets nao parecer o total. */}
        {aging.no_due_date.count > 0 && (
          <p className="text-[11px] text-amber-400 font-mono">
            + {aging.no_due_date.count} lançamento(s) sem data de vencimento, totalizando{' '}
            {fmt(aging.no_due_date.total)} — fora do aging porque não há vencimento para comparar.
          </p>
        )}
      </div>

      {/* Lista */}
      <div className="glass-panel rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-900 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-white font-sans">
            Lançamentos pendentes
            {rotuloFiltro && (
              <span className="ml-2 text-[11px] font-mono text-zinc-400">· {rotuloFiltro}</span>
            )}
          </h3>
          {filtro && (
            <button
              type="button"
              onClick={() => setFiltro(null)}
              className="text-[11px] font-mono text-zinc-400 hover:text-white border border-zinc-800 rounded px-2.5 py-1 transition cursor-pointer"
            >
              Limpar filtro ✕
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
              <tr>
                <th className="py-3 px-5 font-normal">Descrição</th>
                <th className="py-3 px-5 font-normal">Vencimento</th>
                <th className="py-3 px-5 font-normal">Situação</th>
                <th className="py-3 px-5 font-normal text-right">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {visiveis.map((r) => {
                const dias = diasAte(r.due_date);
                const atrasado = dias !== null && dias > 0;
                return (
                  <tr key={r.id} className="hover:bg-zinc-900/40">
                    <td className="py-3 px-5 font-sans text-xs">
                      {r.description}
                      {r.supplier_name || r.client_name ? (
                        <span className="block text-[10px] text-zinc-500 font-mono">
                          {r.supplier_name || r.client_name}
                        </span>
                      ) : null}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                      {r.due_date ? r.due_date.slice(0, 10).split('-').reverse().join('/') : '—'}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                      {dias === null ? (
                        <span className="text-zinc-500">sem vencimento</span>
                      ) : atrasado ? (
                        <span className="text-rose-500">
                          {dias} dia(s) em atraso
                        </span>
                      ) : (
                        <span className="text-zinc-400">
                          {dias === 0 ? 'vence hoje' : `em ${Math.abs(dias)} dia(s)`}
                        </span>
                      )}
                    </td>
                    <td
                      className={`py-3 px-5 font-mono text-xs text-right whitespace-nowrap ${
                        aPagar ? 'text-rose-500' : 'text-emerald-400'
                      }`}
                    >
                      {fmt(Number(r.amount) || 0)}
                    </td>
                  </tr>
                );
              })}

              {visiveis.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-zinc-500 font-mono">
                    {filtro ? 'Nenhuma conta nesta faixa.' : 'Nenhuma conta em aberto.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
