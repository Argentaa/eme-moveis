/**
 * Seletor de período estilo DRE (mensal/trimestral/semestral/anual).
 *
 * O DRE era a única aba com essa opção; agora Comercial, Produção,
 * Financeiro e a Central de Relatórios reusam este componente e o
 * `quickRange` para converter (ano, período, sub-período) em datas.
 */
export const PERIODS = [
  { value: 'mensal', label: 'Mensal' },
  { value: 'trimestral', label: 'Trimestral' },
  { value: 'semestral', label: 'Semestral' },
  { value: 'anual', label: 'Anual' },
];

export const MESES_LONGOS = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

export const MESES_CURTOS = [
  'jan', 'fev', 'mar', 'abr', 'mai', 'jun',
  'jul', 'ago', 'set', 'out', 'nov', 'dez',
];

const iso = (y: number, m: number, d: number) =>
  `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

/** Converte (ano, período, sub-período) em [data_inicial, data_final]. */
export function quickRange(year: number, period: string, sub: number): [string, string] {
  const last = (m: number) => new Date(year, m, 0).getDate();
  if (period === 'trimestral') {
    const s = Math.min(4, Math.max(1, sub));
    const m0 = (s - 1) * 3 + 1;
    return [iso(year, m0, 1), iso(year, m0 + 2, last(m0 + 2))];
  }
  if (period === 'semestral') {
    const m0 = sub === 2 ? 7 : 1;
    return [iso(year, m0, 1), iso(year, m0 + 5, last(m0 + 5))];
  }
  if (period === 'anual') {
    return [iso(year, 1, 1), iso(year, 12, 31)];
  }
  const m = Math.min(12, Math.max(1, sub));
  return [iso(year, m, 1), iso(year, m, last(m))];
}

/** Opções do sub-período conforme a granularidade. */
export function subOptions(period: string): { value: number; label: string }[] {
  if (period === 'trimestral') {
    return [1, 2, 3, 4].map(t => ({ value: t, label: `T${t}` }));
  }
  if (period === 'semestral') {
    return [
      { value: 1, label: 'S1 (jan–jun)' },
      { value: 2, label: 'S2 (jul–dez)' },
    ];
  }
  if (period === 'anual') return [];
  return MESES_LONGOS.map((m, i) => ({ value: i + 1, label: m }));
}

interface PeriodFilterProps {
  year: number;
  period: string;
  month?: number;
  onYear: (y: number) => void;
  onPeriod: (p: string) => void;
  onMonth?: (m: number) => void;
  showMonth?: boolean;
}

export default function PeriodFilter({
  year, period, month, onYear, onPeriod, onMonth, showMonth = true,
}: PeriodFilterProps) {
  const now = new Date().getFullYear();
  const years = [now - 2, now - 1, now, now + 1];
  if (!years.includes(year)) years.push(year);
  years.sort((a, b) => a - b);

  const selectClass =
    'bg-zinc-900 border border-zinc-800 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-600 font-mono';

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="text-xs text-zinc-400 font-mono">Ano:</label>
      <select value={year} onChange={(e) => onYear(Number(e.target.value))} className={selectClass}>
        {years.map(y => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>
      {showMonth && onMonth && (
        <>
          <label className="text-xs text-zinc-400 font-mono">Mês:</label>
          <select
            value={month ?? new Date().getMonth() + 1}
            onChange={(e) => onMonth(Number(e.target.value))}
            className={selectClass}
          >
            {MESES_LONGOS.map((m, i) => (
              <option key={m} value={i + 1}>{m}</option>
            ))}
          </select>
        </>
      )}
      <div className="flex items-center rounded border border-zinc-800 overflow-hidden">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            type="button"
            onClick={() => onPeriod(p.value)}
            title={`Visualização ${p.label.toLowerCase()}`}
            className={`px-3 py-1.5 text-xs font-mono transition cursor-pointer ${
              period === p.value ? 'bg-red-600 text-white font-semibold' : 'bg-zinc-900 text-zinc-400 hover:text-white'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
