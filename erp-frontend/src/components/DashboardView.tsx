import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { 
  TrendingUp, TrendingDown, Users, Hammer, Package, AlertTriangle, 
  Calendar, FileText, ArrowUpRight, ArrowDownRight, RefreshCw, Layers,
  ChevronLeft, ChevronRight
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid
} from 'recharts';
import {
  clientService, projectService, financialService, stockService, reportService, bankAccountService,
  goalService, dashboardService
} from '../services/api';
import { Client, Project, FinancialRecord, StockItem, StockMovement, ReportResult, BankOverview, SalesGoalSummary, AttentionResult, CrmReport } from '../types';
import OverdueProjectsCard from './OverdueProjectsCard';
import UpcomingEventsCard from './UpcomingEventsCard';
import UpcomingPaymentsCard from './UpcomingPaymentsCard';

interface DashboardViewProps {
  userRole: string;
}

export default function DashboardView({ userRole }: DashboardViewProps) {
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [financials, setFinancials] = useState<FinancialRecord[]>([]);
  const [stock, setStock] = useState<StockItem[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [productionReport, setProductionReport] = useState<ReportResult | null>(null);
  const [bankOverview, setBankOverview] = useState<BankOverview | null>(null);
  // Blocos novos do painel (spec do cliente 17/09)
  const [crmReport, setCrmReport] = useState<CrmReport | null>(null);
  const [attention, setAttention] = useState<AttentionResult | null>(null);
  const [goalSummary, setGoalSummary] = useState<SalesGoalSummary | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<ReportResult | null>(null);

  const today = new Date();
  const [selectedMonth, setSelectedMonth] = useState(today.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(today.getFullYear());
  // Visualização do demonstrativo de fluxo de caixa: realizado x projetado
  const [cfMode, setCfMode] = useState<'realizado' | 'projetado'>('realizado');

  const MONTH_NAMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                       'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

  const prevMonth = () => {
    if (selectedMonth === 1) { setSelectedMonth(12); setSelectedYear(y => y - 1); }
    else setSelectedMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (selectedMonth === 12) { setSelectedMonth(1); setSelectedYear(y => y + 1); }
    else setSelectedMonth(m => m + 1);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      if (userRole === 'ESTOQUE') {
        const [st, movs] = await Promise.all([
          stockService.getAll(),
          stockService.getMovements()
        ]);
        setStock(st);
        setMovements(movs);
      } else {
        const [cls, projs, fins, st, movs, prod, overview, crm, att] = await Promise.all([
          clientService.getAll(),
          projectService.getAll(),
          financialService.getAll(),
          stockService.getAll(),
          stockService.getMovements(),
          // Extras silenciosos: entram no MESMO lote. Antes eram 2 idas ao servidor
          // em sequencia depois do primeiro lote, o que somava o tempo de resposta
          // ao carregamento do painel inteiro.
          reportService.getReport('production', {}).catch(() => null),
          bankAccountService.overview().catch(() => null),
          // Formato proprio do CRM (nao segue {summary, columns, rows}).
          dashboardService.crmReport().catch(() => null),
          dashboardService.attention().catch(() => null),
        ]);
        setClients(cls);
        setProjects(projs);
        setFinancials(fins);
        setStock(st);
        setMovements(movs);
        if (prod) setProductionReport(prod);
        if (overview) setBankOverview(overview);
        if (crm) setCrmReport(crm);
        if (att) setAttention(att);
      }
    } catch (err) {
      console.error('Error fetching dashboard statistics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [userRole]);

  // Blocos que dependem do mês/ano selecionado: fluxo de caixa semanal e meta.
  // Separado do loadData para não recarregar clientes/projetos a cada troca de mês.
  useEffect(() => {
    if (userRole === 'ESTOQUE') return;
    let active = true;
    Promise.all([
      reportService.getReport('cash-flow-weekly', {
        year: selectedYear, month: selectedMonth, mode: cfMode,
      }).catch(() => null),
      goalService.summary({ year: selectedYear, month: selectedMonth }).catch(() => null),
    ]).then(([weekly, goal]) => {
      if (!active) return;
      if (weekly) setWeeklyReport(weekly);
      if (goal) setGoalSummary(goal);
    });
    return () => { active = false; };
  }, [selectedYear, selectedMonth, cfMode, userRole]);

  /** Converte "R$ 1.000,00" / "R$ -300,00" em número, para o gráfico. */
  const parseBRL = (value: string): number => {
    const n = Number(String(value).replace(/[^\d,-]/g, '').replace(/\./g, '').replace(',', '.'));
    return Number.isFinite(n) ? n : 0;
  };

  const weeklyData = (weeklyReport?.rows || []).map((row) => ({
    week: String(row.week || ''),
    Entradas: parseBRL(String(row.income || '')),
    'Saídas': parseBRL(String(row.outcome || '')),
    Acumulado: parseBRL(String(row.accumulated || '')),
  }));

  const ATTENTION_TONES: Record<string, string> = {
    negative: 'border-l-red-600 text-red-400',
    warning: 'border-l-amber-500 text-amber-400',
    positive: 'border-l-emerald-600 text-emerald-400',
    neutral: 'border-l-zinc-600 text-zinc-300',
  };

  const MODULE_LABELS: Record<string, string> = {
    financial: 'Financeiro',
    commercial: 'Comercial',
    production: 'Produção',
    tickets: 'Pós-venda',
    purchases: 'Compras',
    stock: 'Estoque',
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
        <p className="text-zinc-400 font-mono text-xs">Carregando métricas de controle...</p>
      </div>
    );
  }

  // Stock calculations
  const lowStockCount = stock.filter(item => item.quantity <= item.min_quantity).length;
  const totalStockItems = stock.reduce((acc, item) => acc + item.quantity, 0);

  // If role is strictly ESTOQUE, return optimized warehouse dashboard
  if (userRole === 'ESTOQUE') {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Painel de Estoque</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Status operacional do estoque e movimentações de carga</p>
        </div>

        {/* 2 Critical Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="glass-panel p-6 rounded-lg relative overflow-hidden">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Total de Insumos Estocados</p>
                <p className="text-4xl font-bold mt-2 text-white">{totalStockItems}</p>
                <p className="text-xs text-zinc-400 mt-2 font-mono">{stock.length} especificações cadastradas</p>
              </div>
              <div className="p-3 bg-zinc-900 rounded-lg text-red-600 border border-zinc-800">
                <Package className="w-6 h-6" />
              </div>
            </div>
          </div>

          <div className={`glass-panel p-6 rounded-lg relative overflow-hidden border ${lowStockCount > 0 ? 'border-red-900/40 bg-red-950/5' : ''}`}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Alertas de Estoque Baixo</p>
                <p className={`text-4xl font-bold mt-2 ${lowStockCount > 0 ? 'text-red-500 animate-pulse' : 'text-emerald-500'}`}>
                  {lowStockCount}
                </p>
                <p className="text-xs text-zinc-400 mt-2 font-mono">
                  {lowStockCount > 0 ? 'Reposição urgente recomendada' : 'Níveis seguros operacionais'}
                </p>
              </div>
              <div className={`p-3 rounded-lg border ${lowStockCount > 0 ? 'bg-red-900/20 text-red-500 border-red-800/30' : 'bg-zinc-900 text-emerald-500 border-zinc-800'}`}>
                <AlertTriangle className="w-6 h-6" />
              </div>
            </div>
          </div>
        </div>

        {/* Stock status table for Stock Team */}
        <div className="glass-panel p-6 rounded-lg">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-red-600" /> Itens sob Alerta crítico
            </h3>
            <span className="text-xs font-mono px-3 py-1 rounded bg-red-950/50 text-red-400 border border-red-900/30">
              Ação Requerida
            </span>
          </div>

          {lowStockCount === 0 ? (
            <p className="text-zinc-400 text-sm py-4 text-center font-mono">✓ Excelente! Nenhum material abaixo do estoque mínimo.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm font-mono text-zinc-300">
                <thead className="text-xs uppercase text-zinc-500 bg-zinc-900/50">
                  <tr>
                    <th className="py-2.5 px-4 font-normal">Componente</th>
                    <th className="py-2.5 px-4 font-normal">Mínimo</th>
                    <th className="py-2.5 px-4 font-normal text-right">Atual</th>
                    <th className="py-2.5 px-4 font-normal text-center">Aviso</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {stock.filter(item => item.quantity <= item.min_quantity).map(item => (
                    <tr key={item.id} className="hover:bg-zinc-900/30">
                      <td className="py-3 px-4 font-sans font-medium text-white">{item.name}</td>
                      <td className="py-3 px-4 text-zinc-400">{item.min_quantity} {item.unit}</td>
                      <td className="py-3 px-4 text-right text-red-400 font-bold">{item.quantity} {item.unit}</td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-600 animate-ping"></span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Executive/Admin Calculations — filtrados pelo mês/ano selecionado
  const financialsByMonth = financials.filter(f => {
    const d = new Date(`${f.date}T00:00:00`);
    return d.getMonth() + 1 === selectedMonth && d.getFullYear() === selectedYear;
  });
  const activeProjects = projects.filter(p => p.status !== 'CONCLUIDO');
  const finishedProjects = projects.filter(p => p.status === 'CONCLUIDO');
  const projectQueueValue = activeProjects.reduce((acc, p) => acc + p.value, 0);

  const entriesTotal = financialsByMonth
    .filter(f => f.type === 'ENTRADA' && f.status === 'PAGO')
    .reduce((acc, f) => acc + f.amount, 0);

  const exitsTotal = financialsByMonth
    .filter(f => f.type === 'SAIDA' && f.status === 'PAGO')
    .reduce((acc, f) => acc + f.amount, 0);

  const netBalance = entriesTotal - exitsTotal;

  // Resumo principal (bloco 1 do painel): valores em aberto e projetos ativos.
  const pendingReceivable = financials
    .filter(f => f.type === 'ENTRADA' && f.status === 'PENDENTE')
    .reduce((acc, f) => acc + f.amount, 0);
  const pendingPayable = financials
    .filter(f => f.type === 'SAIDA' && f.status === 'PENDENTE')
    .reduce((acc, f) => acc + f.amount, 0);
  const projectsInProduction = projects.filter(p => p.status !== 'CONCLUIDO').length;
  const monthLabel = `${MONTH_NAMES[selectedMonth - 1]} ${selectedYear}`;

  // Resumo comercial: o /api/reports/crm tem formato proprio (nao tem
  // `summary`), entao os KPIs sao montados a partir dos campos reais.
  const money = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const crmStage = (key: string) =>
    (crmReport?.negociacoes?.por_etapa || []).find((e) => e.funnel_status === key)?.total ?? 0;

  // Chart Mapping Groups (By Category)
  const categoryChartData = financialsByMonth
    .filter(f => f.status === 'PAGO')
    .reduce((acc: any[], f) => {
      const existing = acc.find(item => item.name === f.category);
      if (existing) {
        existing.amount += f.amount;
      } else {
        acc.push({ name: f.category, amount: f.amount });
      }
      return acc;
    }, []);

  const currentCompetence = new Date(selectedYear, selectedMonth - 1, 1).toLocaleDateString('pt-BR', {
    month: 'long',
    year: 'numeric',
  });

  // Resultado mês a mês dos últimos 12 meses (vem do /api/reports/crm).
  const yearResultData = (crmReport?.fluxo_caixa || []).map((m) => ({
    name: m.mes.slice(5),
    Receitas: m.receitas,
    Despesas: m.despesas,
    Resultado: m.resultado,
  }));

  const brlTick = (v: number) =>
    Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

  return (
    <div className="space-y-6">
      {/* Dynamic Header */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide font-medium">Dashboard Executivo</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Resultados e acompanhamento comercial da marcenaria.</p>
        </div>
        <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 text-zinc-300 font-mono text-xs rounded-md overflow-hidden">
          <button onClick={prevMonth} className="px-2 py-2 hover:bg-zinc-800 transition cursor-pointer">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2 px-2">
            <Calendar className="w-4 h-4 text-red-600 shrink-0" />
            <select
              value={`${selectedYear}-${String(selectedMonth).padStart(2,'0')}`}
              onChange={e => {
                const [y, m] = e.target.value.split('-');
                setSelectedYear(Number(y));
                setSelectedMonth(Number(m));
              }}
              className="bg-transparent text-zinc-300 font-mono text-xs focus:outline-none cursor-pointer"
            >
              {Array.from({ length: 24 }, (_, i) => {
                const d = new Date();
                d.setMonth(d.getMonth() - 12 + i);
                const y = d.getFullYear();
                const m = d.getMonth() + 1;
                const val = `${y}-${String(m).padStart(2,'0')}`;
                const label = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
                return <option key={val} value={val}>{label}</option>;
              })}
            </select>
          </div>
          <button onClick={nextMonth} className="px-2 py-2 hover:bg-zinc-800 transition cursor-pointer">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Projetos atrasados */}
      <OverdueProjectsCard compact={true} />

      {/* Grid of 4 Premium Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Metric 1 */}
        <div className="glass-panel p-5 rounded-lg relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Receitas</p>
              <p className="text-2xl font-bold mt-2 text-white font-sans">
                {entriesTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </p>
              <div className="flex items-center gap-1 text-emerald-500 text-xs mt-2 font-mono">
                <ArrowUpRight className="w-3.5 h-3.5" />
                <span>Entradas pagas</span>
              </div>
            </div>
            <div className="p-3 bg-zinc-950 rounded-lg text-emerald-500 border border-zinc-900">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel p-5 rounded-lg relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Insumos e despesas</p>
              <p className="text-2xl font-bold mt-2 text-white font-sans">
                {exitsTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </p>
              <div className="flex items-center gap-1 text-red-500 text-xs mt-2 font-mono">
                <ArrowDownRight className="w-3.5 h-3.5" />
                <span>Saídas pagas</span>
              </div>
            </div>
            <div className="p-3 bg-zinc-950 rounded-lg text-red-500 border border-zinc-900">
              <TrendingDown className="w-5 h-5" />
            </div>
          </div>
        </div>

         {/* Metric 3 — Saldo Consolidado ou fallback */}
        <div className="glass-panel p-5 rounded-lg relative overflow-hidden">
          {bankOverview && bankOverview.accounts && bankOverview.accounts.length > 0 ? (
            <div>
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Saldo Consolidado</p>
                  <p className={`text-2xl font-bold mt-2 font-sans ${bankOverview.total_balance >= 0 ? 'text-white' : 'text-red-500'}`}>
                    {bankOverview.total_balance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                  <div className="flex items-center gap-1 text-zinc-400 text-xs mt-2 font-mono">
                    <span>{bankOverview.accounts.length} conta(s) · Projetado {bankOverview.total_projected.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}</span>
                  </div>
                </div>
                <div className="p-3 bg-zinc-950 rounded-lg text-emerald-500 border border-zinc-900">
                  <Layers className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-3 grid grid-cols-1 gap-1.5">
                {bankOverview.accounts.slice(0, 3).map((acc) => (
                  <div key={acc.id} className="flex justify-between items-center text-xs font-mono">
                    <span className="text-zinc-400 truncate pr-2">{acc.name}</span>
                    <span className={`font-bold ${(acc.current_balance ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {Number(acc.current_balance ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                    </span>
                  </div>
                ))}
                {bankOverview.accounts.length > 3 && (
                  <span className="text-[11px] text-zinc-500 font-mono">+{bankOverview.accounts.length - 3} outra(s) conta(s)</span>
                )}
              </div>
            </div>
          ) : (
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Saldo em Caixa</p>
                <p className={`text-2xl font-bold mt-2 font-sans ${netBalance >= 0 ? 'text-white' : 'text-red-500'}`}>
                  {netBalance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
                <div className="flex items-center gap-1 text-zinc-400 text-xs mt-2 font-mono">
                  <span>Resultado Operacional Liquido</span>
                </div>
              </div>
              <div className="p-3 bg-zinc-950 rounded-lg text-red-600 border border-zinc-900">
                <Layers className="w-5 h-5" />
              </div>
            </div>
          )}
        </div>

        {/* Metric 4 */}
        <div className="glass-panel p-5 rounded-lg relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Projetos Ativos</p>
              <p className="text-2xl font-bold mt-2 text-white font-sans">
                {activeProjects.length}
              </p>
              <div className="flex items-center gap-1 text-zinc-400 text-xs mt-2 font-mono">
                <span>Total em carteira: {projectQueueValue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}</span>
              </div>
            </div>
            <div className="p-3 bg-zinc-950 rounded-lg text-amber-500 border border-zinc-900">
              <Hammer className="w-5 h-5" />
            </div>
          </div>
        </div>

      </div>

      {/* ── Resumo principal (bloco 1 da spec) ────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { label: 'Saldo bancário', value: bankOverview ? bankOverview.total_balance : netBalance, tone: 'text-white' },
          { label: 'Contas a receber (aberto)', value: pendingReceivable, tone: 'text-emerald-400' },
          { label: 'Contas a pagar (aberto)', value: pendingPayable, tone: 'text-red-400' },
          { label: 'Faturamento do mês', value: entriesTotal, tone: 'text-white' },
          { label: 'Projetos em produção', value: projectsInProduction, tone: 'text-white', raw: true },
        ].map((kpi) => (
          <div key={kpi.label} className="glass-panel p-4 rounded-lg">
            <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">{kpi.label}</p>
            <p className={`text-lg font-bold mt-1.5 font-sans ${kpi.tone}`}>
              {kpi.raw
                ? kpi.value
                : kpi.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </p>
          </div>
        ))}
      </div>

      {/* ── Fluxo de Caixa do Mês, por semana (bloco 2 da spec) ───── */}
      <div className="glass-panel p-5 rounded-lg">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
          <div>
            <h3 className="text-lg font-serif text-white tracking-wide">Fluxo de Caixa do Mês — por semana</h3>
            <p className="text-xs text-zinc-400 font-mono mt-0.5">
              {monthLabel} · entradas, saídas, saldo semanal e saldo acumulado
            </p>
          </div>
          <div className="flex bg-zinc-950 border border-zinc-800 rounded p-1">
            {(['realizado', 'projetado'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setCfMode(m)}
                className={`px-3 py-1.5 text-xs font-mono uppercase rounded transition cursor-pointer ${
                  cfMode === m ? 'bg-red-600 text-white font-semibold' : 'text-zinc-400 hover:text-white'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {weeklyData.length > 0 ? (
          <>
            <div className="h-52 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyData}>
                  <XAxis dataKey="week" stroke="#71717a" fontSize={11} />
                  <YAxis stroke="#71717a" fontSize={11} />
                  <Tooltip
                    contentStyle={{ background: '#09090b', border: '1px solid #27272a', borderRadius: 6, fontSize: 12 }}
                    formatter={(v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="Entradas" fill="#10b981" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Saídas" fill="#ef4444" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <p className="text-[10px] text-zinc-500 font-mono mt-4 sm:hidden">
              arraste a tabela para o lado para ver todas as colunas →
            </p>

            <div className="overflow-x-auto mt-2 sm:mt-4">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-zinc-500 uppercase tracking-wider text-[10px]">
                    {(weeklyReport?.columns || []).map((col) => (
                      <th key={col.key} className="text-left py-2 pr-4 whitespace-nowrap">{col.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(weeklyReport?.rows || []).map((row) => (
                    <tr key={String(row.week)} className="border-t border-zinc-900 text-zinc-300">
                      {(weeklyReport?.columns || []).map((col) => (
                        <td key={col.key} className="py-2 pr-4 whitespace-nowrap">{String(row[col.key] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-xs text-zinc-500 font-mono mt-4">Sem lançamentos no mês selecionado.</p>
        )}
      </div>

      {/* ── Meta Comercial e Resumo Comercial (blocos 3 e 4 da spec) ─ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <h3 className="text-lg font-serif text-white tracking-wide">Meta Comercial</h3>
          {goalSummary ? (
            <>
              <div className="flex justify-between items-end mt-3 gap-3">
                <p className="text-2xl font-bold text-white font-sans">{goalSummary.percent}</p>
                <p className="text-xs text-zinc-400 font-mono text-right">
                  {goalSummary.achieved} de {goalSummary.target}
                  <br />meta {goalSummary.target_basis === 'mes' ? 'do mês' : 'do ano'}
                </p>
              </div>
              <div className="h-2 bg-zinc-950 rounded mt-3 overflow-hidden border border-zinc-900">
                <div
                  className="h-full bg-red-600 transition-all"
                  style={{ width: `${Math.min(parseBRL(goalSummary.percent), 100)}%` }}
                />
              </div>
              <p className="text-xs text-zinc-500 font-mono mt-2">
                Faltam {goalSummary.remaining} · {goalSummary.deals_closed} venda(s) fechada(s)
                {goalSummary.undated > 0 && ` · ${goalSummary.undated} sem data de fechamento`}
              </p>
            </>
          ) : (
            <p className="text-xs text-zinc-500 font-mono mt-3">Sem meta cadastrada para o período.</p>
          )}
        </div>

        <div className="glass-panel p-5 rounded-lg">
          <h3 className="text-lg font-serif text-white tracking-wide">Resumo Comercial</h3>
          {crmReport ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
              {[
                { label: 'Vendas realizadas', value: String(crmReport.conversao?.total_fechamentos ?? 0) },
                { label: 'Taxa de conversão', value: `${Number(crmReport.conversao?.taxa ?? 0).toFixed(1)}%` },
                { label: 'Em orçamento', value: String(crmStage('ORCAMENTO')) },
                { label: 'Em negociação', value: String(crmStage('NEGOCIACAO')) },
                { label: 'Ticket médio', value: money(crmReport.ticket_medio?.media ?? 0) },
                { label: 'Perdidos', value: String(crmReport.negociacoes?.total_perdidas ?? 0) },
              ].map((kpi) => (
                <div key={kpi.label}>
                  <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">{kpi.label}</p>
                  <p className="text-base font-bold font-sans mt-0.5 text-white">{kpi.value}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-500 font-mono mt-3">Resumo indisponível.</p>
          )}
        </div>
      </div>

      {/* ── O que precisa da minha atenção (bloco 6 da spec) ──────── */}
      <div className="glass-panel p-5 rounded-lg">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-serif text-white tracking-wide">O que precisa da minha atenção</h3>
          {attention && (
            <span className="text-xs font-mono text-zinc-400">{attention.total_items} pendência(s)</span>
          )}
        </div>
        {attention && attention.items.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
            {attention.items.map((item) => (
              <div key={item.kind}
                   className={`glass-panel p-4 rounded border-l-4 ${ATTENTION_TONES[item.tone] || ATTENTION_TONES.neutral}`}>
                <div className="flex justify-between items-start gap-3">
                  <div>
                    <p className="text-sm text-white font-sans">{item.label}</p>
                    <p className="text-[11px] text-zinc-500 font-mono mt-0.5">{item.detail}</p>
                    <p className="text-[10px] text-zinc-600 font-mono mt-1.5">
                      {MODULE_LABELS[item.module] || item.module} › {item.tab}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xl font-bold font-sans">{item.count}</p>
                    {item.total && <p className="text-[11px] font-mono text-zinc-400">{item.total}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-500 font-mono mt-3">Nada pendente. Tudo em ordem.</p>
        )}
      </div>

      {/* Resultado 12 meses + consumo por categoria */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Resultado mês a mês (receitas x despesas x resultado) */}
        <div className="glass-panel p-5 rounded-lg lg:col-span-2">
          <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
            <div>
              <h3 className="text-base font-medium text-white">Resultado dos últimos 12 meses</h3>
              <p className="text-xs text-zinc-400 font-mono">
                Receitas, despesas e resultado mês a mês · valores pagos em BRL (R$)
              </p>
            </div>
          </div>

          <div className="h-64 mt-4 text-xs font-mono">
            {yearResultData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-500">Sem dados financeiros</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={yearResultData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="name" stroke="#52525b" tickLine={false} />
                  <YAxis stroke="#52525b" axisLine={false} tickLine={false} tickFormatter={brlTick} width={80} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px' }}
                    formatter={(v: number, name: string) => [v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }), name]}
                    labelFormatter={(label: string) => `Mês ${label}`}
                  />
                  <Legend iconSize={8} wrapperStyle={{ paddingTop: '10px' }} />
                  <Bar dataKey="Receitas" fill="#10b981" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Despesas" fill="#ef4444" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Resultado" fill="#e4e4e7" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Expenses distribution bar chart */}
        <div className="glass-panel p-5 rounded-lg flex flex-col justify-between">
          <div>
            <h3 className="text-base font-medium text-white">Consumo por Categoria</h3>
            <p className="text-xs text-zinc-400 font-mono mb-4">Top categorias pagas em {currentCompetence}</p>
          </div>

          <div className="h-56 text-xs font-mono">
            {categoryChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-500">Sem dados financeiros</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[...categoryChartData].sort((a, b) => b.amount - a.amount).slice(0, 8)}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#52525b" hide />
                  <YAxis dataKey="name" type="category" stroke="#a1a1aa" width={110} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px' }}
                    formatter={(v: number) => [v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }), 'Total']}
                  />
                  <Bar dataKey="amount" name="Total (R$)" fill="#7f1d1d" radius={[0, 4, 4, 0]} barSize={12} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <p className="text-[11px] text-zinc-500 text-center font-mono pt-3 border-t border-zinc-800">
            Focado em gastos fixos e insumos da marcenaria
          </p>
        </div>

      </div>

      {/* Grid of details: Projects Pipeline, Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Project summary */}
        <div className="glass-panel p-5 rounded-lg flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-medium text-white flex items-center gap-2">
              <Hammer className="w-5 h-5 text-red-600" /> Andamento da Produção
            </h3>
            <span className="text-xs text-zinc-400 font-mono">Projetos em progresso ({activeProjects.length})</span>
          </div>

          <div className="space-y-4 flex-1">
            {activeProjects.slice(0, 3).map((p) => {
              // Calculate completion %
              const completedSteps = p.steps.filter(s => s.completed).length;
              const totalSteps = p.steps.length;
              const pct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

              return (
                <div key={p.id} className="p-3.5 bg-zinc-900/30 rounded border border-zinc-800/40">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="text-sm font-medium text-white line-clamp-1">{p.title}</h4>
                      <p className="text-xs text-zinc-400 font-mono mt-0.5">{p.client_name}</p>
                    </div>
                    <span className="text-xs font-semibold font-mono text-red-400 bg-red-950/40 border border-red-900/30 px-2 py-0.5 rounded">
                      {p.status}
                    </span>
                  </div>

                  <div className="mt-3.5">
                    <div className="flex justify-between items-center text-[11px] font-mono text-zinc-400 mb-1">
                      <span>Cronograma: {completedSteps} de {totalSteps} termos</span>
                      <span className="font-bold text-red-500">{pct}%</span>
                    </div>
                    <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                      <div 
                        className="bg-red-600 h-full transition-all duration-500" 
                        style={{ width: `${pct}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Latest Log events / Client history */}
        <div className="glass-panel p-5 rounded-lg">
          <h3 className="text-base font-medium text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-red-600" /> Clientes & Atividades Recentes
          </h3>

          <div className="space-y-3.5">
            {clients.slice(0, 3).map((c) => (
              <div key={c.id} className="flex justify-between items-center py-2.5 border-b border-zinc-900 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-zinc-900 text-red-500 flex items-center justify-center font-bold text-sm rounded border border-zinc-800">
                    {c.name.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h4 className="text-xs font-medium text-white">{c.name}</h4>
                    <p className="text-[11px] text-zinc-400 font-mono mt-0.5">{c.email}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[11px] text-zinc-500 font-mono block">Data de cadastro</span>
                  <span className="text-xs text-zinc-400 font-mono">{new Date(c.created_at).toLocaleDateString('pt-BR')}</span>
                </div>
              </div>
            ))}

            {clients.length === 0 && (
              <p className="text-zinc-500 text-sm font-mono text-center py-8">Nenhum cliente cadastrado recentemente.</p>
            )}
          </div>
        </div>

      </div>

      {/* Produção Industrial */}
      <div className="glass-panel p-5 rounded-lg">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-base font-medium text-white flex items-center gap-2">
            <Hammer className="w-5 h-5 text-red-600" /> Produção Industrial
          </h3>
          <span className="text-xs text-zinc-500 font-mono">{productionReport ? productionReport.title : 'projetos, ambientes e ocorrências'}</span>
        </div>
        {productionReport ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {(() => {
              const findVal = (labelPart: string) => {
                const it = productionReport.summary.find(s => s.label.toLowerCase().includes(labelPart.toLowerCase()));
                return it ? it.value : '-';
              };
              // Ocorrências = soma retrabalhos+perdas se disponível, senão busca item que contenha ocorrência/retrabalho
              const ocorrenciasItem = productionReport.summary.find(s => /ocorr/i.test(s.label));
              const retrabItem = productionReport.summary.find(s => /retrabalho/i.test(s.label));
              const perdaItem = productionReport.summary.find(s => /perda/i.test(s.label));
              let ocorrenciasVal = '-';
              if (ocorrenciasItem) ocorrenciasVal = ocorrenciasItem.value;
              else if (retrabItem || perdaItem) {
                const r = retrabItem ? parseInt(String(retrabItem.value).replace(/\D/g,'')) || 0 : 0;
                const p = perdaItem ? parseInt(String(perdaItem.value).replace(/\D/g,'')) || 0 : 0;
                ocorrenciasVal = String(r + p);
              }
              // Custo total das ocorrências = soma dos custos de retrabalho, perdas e desperdícios
              const custoOcorrencias = (productionReport.summary || [])
                .filter(s => /custo/i.test(s.label))
                .reduce((acc, s) => acc + parseBRL(String(s.value)), 0);
              const cards = [
                { label: 'Projetos', value: findVal('total projetos') || findVal('projeto'), tone: 'text-white' },
                { label: 'Ambientes', value: findVal('ambiente'), tone: 'text-white' },
                { label: 'Ocorrências', value: ocorrenciasVal, tone: 'text-amber-400' },
                { label: 'Custo ocorrências', value: money(custoOcorrencias), tone: 'text-red-400' },
              ];
              return cards.map((c, idx) => (
                <div key={idx} className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4">
                  <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">{c.label}</p>
                  <p className={`text-2xl font-bold mt-1 font-sans ${c.tone}`}>{c.value}</p>
                </div>
              ));
            })()}
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 opacity-60">
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Projetos</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Ambientes</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Ocorrências</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Custo ocorrências</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
          </div>
        )}
      </div>

      {/* Próximos Vencimentos */}
      <UpcomingPaymentsCard />

      {/* Próximos Compromissos */}
      <UpcomingEventsCard />

    </div>
  );
}
