import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { 
  TrendingUp, TrendingDown, Users, Hammer, Package, AlertTriangle, 
  Calendar, FileText, ArrowUpRight, ArrowDownRight, RefreshCw, Layers,
  ChevronLeft, ChevronRight
} from 'lucide-react';
import { 
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import {
  clientService, projectService, financialService, stockService, reportService, bankAccountService
} from '../services/api';
import { Client, Project, FinancialRecord, StockItem, StockMovement, ReportResult, BankOverview } from '../types';
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
        const [cls, projs, fins, st, movs, prod, overview] = await Promise.all([
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
        ]);
        setClients(cls);
        setProjects(projs);
        setFinancials(fins);
        setStock(st);
        setMovements(movs);
        if (prod) setProductionReport(prod);
        if (overview) setBankOverview(overview);
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

  // Demonstrativo mensal do ano selecionado, mês a mês.
  // Realizado = só o que foi pago/recebido; Projetado = inclui o que está em aberto.
  const timeChartData = Array.from({ length: 12 }, (_, i) => ({
    name: new Date(selectedYear, i, 1).toLocaleDateString('pt-BR', { month: 'short' }),
    entradas: 0,
    saidas: 0,
  }));

  financials
    .filter(f => {
      if (cfMode === 'realizado' && f.status !== 'PAGO') return false;
      const ref = f.due_date || f.date;
      const d = new Date(`${ref}T00:00:00`);
      return !Number.isNaN(d.getTime()) && d.getFullYear() === selectedYear;
    })
    .forEach(f => {
      const ref = f.due_date || f.date;
      const slot = timeChartData[new Date(`${ref}T00:00:00`).getMonth()];
      if (!slot) return;
      if (f.type === 'ENTRADA') {
        slot.entradas += f.amount;
      } else {
        slot.saidas += f.amount;
      }
    });

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

      {/* Bento Layout: Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Area Chart: Entries vs Exits over time */}
        <div className="glass-panel p-5 rounded-lg lg:col-span-2">
          <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
            <div>
              <h3 className="text-base font-medium text-white">Demonstrativo de Fluxo de Caixa</h3>
              <p className="text-xs text-zinc-400 font-mono">
                {cfMode === 'projetado' ? 'Projetado' : 'Realizado'} · mensal ({selectedYear}) · BRL (R$)
              </p>
            </div>
            <div className="flex items-center rounded border border-zinc-800 overflow-hidden">
              {(['realizado', 'projetado'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setCfMode(m)}
                  title={m === 'realizado'
                    ? 'Somente o que já foi pago/recebido'
                    : 'Inclui os lançamentos em aberto (previstos)'}
                  className={`px-3 py-1.5 text-xs font-mono transition cursor-pointer ${
                    cfMode === m ? 'bg-red-600 text-white font-semibold' : 'bg-zinc-900 text-zinc-400 hover:text-white'
                  }`}
                >
                  {m === 'realizado' ? 'Realizado' : 'Projetado'}
                </button>
              ))}
            </div>
          </div>
          
          <div className="h-64 mt-4 text-xs font-mono">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeChartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorEntradas" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorSaidas" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#52525b" tickLine={false} />
                <YAxis stroke="#52525b" axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px' }} 
                  itemStyle={{ fontSize: '11px' }}
                />
                <Legend iconSize={8} wrapperStyle={{ paddingTop: '10px' }} />
                <Area type="monotone" dataKey="entradas" name={cfMode === 'projetado' ? 'Entradas (Previstas)' : 'Entradas (Realizadas)'} stroke="#10b981" fillOpacity={1} fill="url(#colorEntradas)" strokeWidth={2} />
                <Area type="monotone" dataKey="saidas" name={cfMode === 'projetado' ? 'Saídas (Previstas)' : 'Saídas (Realizadas)'} stroke="#ef4444" fillOpacity={1} fill="url(#colorSaidas)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Expenses distribution bar chart */}
        <div className="glass-panel p-5 rounded-lg flex flex-col justify-between">
          <div>
            <h3 className="text-base font-medium text-white">Consumo por Categoria</h3>
            <p className="text-xs text-zinc-400 font-mono mb-4">Análise em R$ do caixa geral</p>
          </div>

          <div className="h-48 text-xs font-mono">
            {categoryChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-500">Sem dados financeiros</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryChartData.slice(0, 4)} layout="vertical">
                  <XAxis type="number" stroke="#52525b" hide />
                  <YAxis dataKey="name" type="category" stroke="#a1a1aa" width={110} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', color: '#fff', borderRadius: '6px' }}
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
          <span className="text-xs text-zinc-500 font-mono">{productionReport ? productionReport.title : 'm², ambientes, horas e ocorrências'}</span>
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
              const cards = [
                { label: 'Total m²', value: findVal('m2') || findVal('m²') || findVal('area'), tone: 'text-white' },
                { label: 'Ambientes', value: findVal('ambiente'), tone: 'text-white' },
                { label: 'Horas produtivas', value: findVal('hora') || findVal('produtiva'), tone: 'text-emerald-400' },
                { label: 'Ocorrências', value: ocorrenciasVal, tone: 'text-amber-400' },
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
              <p className="text-[10px] text-zinc-500 font-mono">Total m²</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Ambientes</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Horas produtivas</p><div className="h-6 bg-zinc-800 rounded mt-2" />
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <p className="text-[10px] text-zinc-500 font-mono">Ocorrências</p><div className="h-6 bg-zinc-800 rounded mt-2" />
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
