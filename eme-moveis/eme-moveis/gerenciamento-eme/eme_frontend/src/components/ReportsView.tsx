import React, { useEffect, useState } from 'react';
import {
  FileBarChart, Landmark, Users, Building2, Package, Filter, RefreshCw,
  FileText, FileSpreadsheet, Search, Loader2
} from 'lucide-react';
import { reportService, clientService, projectService, stockService, getApiErrorMessage } from '../services/api';
import { ReportArea, ReportResult, Client, Project, Category } from '../types';

interface ReportsViewProps {
  userRole: string;
}

const PROJECT_STATUSES = [
  { value: 'ORCAMENTO', label: 'Orçamento' },
  { value: 'PROJETADO', label: 'Projetado' },
  { value: 'PRODUCAO', label: 'Produção' },
  { value: 'MONTAGEM', label: 'Montagem' },
  { value: 'CONCLUIDO', label: 'Concluído' },
];

const AREAS: { id: ReportArea; label: string; icon: React.ComponentType<any>; description: string }[] = [
  { id: 'financial', label: 'Financeiro', icon: Landmark, description: 'Entradas, saídas e fluxo de caixa' },
  { id: 'clients', label: 'Clientes', icon: Users, description: 'Cadastro e histórico de clientes' },
  { id: 'projects', label: 'Projetos', icon: Building2, description: 'Ambientes e status de produção' },
  { id: 'stock', label: 'Estoque', icon: Package, description: 'Itens e movimentações de estoque' },
  { id: 'dre', label: 'DRE', icon: Landmark, description: 'Demonstrativo de Resultado do Exercício' },
  { id: 'crm', label: 'CRM', icon: Users, description: 'Negociações, conversão, ticket médio e fluxo de caixa' },
];

const TONE_CLASSES: Record<string, string> = {
  positive: 'text-emerald-400 border-l-emerald-600',
  negative: 'text-rose-500 border-l-red-650',
  neutral: 'text-white border-l-zinc-700',
};

export default function ReportsView({ userRole }: ReportsViewProps) {
  const [activeArea, setActiveArea] = useState<ReportArea>('financial');
  const [dreData, setDreData] = useState<any>(null);
  const [dreLoading, setDreLoading] = useState(false);
  const [dreMonth, setDreMonth] = useState(new Date().getMonth() + 1);
  const [dreYear, setDreYear] = useState(new Date().getFullYear());
  const [crmData, setCrmData] = useState<any>(null);
  const [crmLoading, setCrmLoading] = useState(false);
  const [crmDateFrom, setCrmDateFrom] = useState('');
  const [crmDateTo, setCrmDateTo] = useState('');
  const [filters, setFilters] = useState<Record<string, string | boolean>>({});
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<'pdf' | 'xlsx' | null>(null);
  const [error, setError] = useState('');

  // Dados auxiliares para popular selects de filtro
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [financialCategories, setFinancialCategories] = useState<Category[]>([]);

  useEffect(() => {
    Promise.all([
      clientService.getAll().catch(() => []),
      projectService.getAll().catch(() => []),
      stockService.getCategories('STOCK').catch(() => []),
      stockService.getCategories('FINANCIAL').catch(() => []),
    ]).then(([cls, projs, stockCats, finCats]) => {
      setClients(cls);
      setProjects(projs);
      setCategories(stockCats);
      setFinancialCategories(finCats);
    });
  }, []);

  // Reseta filtros e resultado ao trocar de área
  const handleSelectArea = (area: ReportArea) => {
    setActiveArea(area);
    setFilters(area === 'stock' ? { report_mode: 'items' } : {});
    setReport(null);
    setError('');
  };

  const loadDRE = async () => {
    setDreLoading(true);
    try {
      const data = await reportService.getDRE(dreMonth, dreYear);
      setDreData(data);
    } catch (err) {
      console.error('Erro ao carregar DRE:', err);
    } finally {
      setDreLoading(false);
    }
  };

  useEffect(() => {
    if (activeArea === 'dre') loadDRE();
  }, [activeArea, dreMonth, dreYear]);

  const loadCRM = async () => {
    setCrmLoading(true);
    try {
      const data = await reportService.getCRMReport(crmDateFrom || undefined, crmDateTo || undefined);
      setCrmData(data);
    } catch (err) {
      console.error('Erro ao carregar CRM:', err);
    } finally {
      setCrmLoading(false);
    }
  };

  useEffect(() => {
    if (activeArea === 'crm') loadCRM();
  }, [activeArea]);

  const updateFilter = (key: string, value: string | boolean) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await reportService.getReport(activeArea, filters);
      setReport(result);
    } catch (err) {
      console.error('Erro ao gerar relatório:', err);
      setError(getApiErrorMessage(err, 'Erro ao gerar o relatório. Verifique os filtros e tente novamente.'));
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'xlsx') => {
    setExporting(format);
    setError('');
    try {
      await reportService.exportReport(activeArea, format, filters);
    } catch (err) {
      console.error('Erro ao exportar relatório:', err);
      setError(getApiErrorMessage(err, 'Erro ao exportar o relatório. Tente novamente.'));
    } finally {
      setExporting(null);
    }
  };

  const handleClearFilters = () => {
    setFilters(activeArea === 'stock' ? { report_mode: (filters.report_mode as string) || 'items' } : {});
  };

  return (
    <div className="space-y-6">

      {/* Top Bar Section */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Central de Relatórios</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Filtre, visualize e exporte relatórios de qualquer área do sistema.</p>
        </div>
      </div>

      {/* Area Selector */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {AREAS.map(area => {
          const AreaIcon = area.icon;
          const isSelected = activeArea === area.id;
          return (
            <button
              key={area.id}
              onClick={() => handleSelectArea(area.id)}
              className={`glass-panel p-4 rounded-lg text-left transition cursor-pointer border ${
                isSelected ? 'border-red-650 bg-red-950/10' : 'border-zinc-800 hover:border-zinc-700'
              }`}
            >
              <AreaIcon className={`w-5 h-5 mb-2 ${isSelected ? 'text-red-500' : 'text-zinc-500'}`} />
              <span className={`text-sm font-semibold block font-sans ${isSelected ? 'text-white' : 'text-zinc-300'}`}>
                {area.label}
              </span>
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5 leading-tight">
                {area.description}
              </span>
            </button>
          );
        })}
      </div>

      {/* DRE Panel — só aparece quando aba DRE está ativa */}
      {activeArea === 'dre' && (
        <div className="space-y-5">
          {/* Seletor de período */}
          <div className="glass-panel p-5 rounded-lg flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-xs text-zinc-400 font-mono uppercase">Mês</label>
              <select
                value={dreMonth}
                onChange={e => setDreMonth(Number(e.target.value))}
                className="bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none font-mono"
              >
                {['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'].map((m, i) => (
                  <option key={i+1} value={i+1}>{m}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-zinc-400 font-mono uppercase">Ano</label>
              <select
                value={dreYear}
                onChange={e => setDreYear(Number(e.target.value))}
                className="bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none font-mono"
              >
                {[2024, 2025, 2026, 2027].map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
          </div>

          {dreLoading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
              <p className="text-zinc-400 font-mono text-xs">Calculando DRE...</p>
            </div>
          ) : dreData ? (
            <div className="space-y-4">
              {/* Resultado líquido */}
              <div className={`glass-panel p-5 rounded-lg border-l-4 ${dreData.resultado_liquido >= 0 ? 'border-l-emerald-500' : 'border-l-red-500'}`}>
                <p className="text-xs text-zinc-400 font-mono uppercase tracking-widest">Resultado Líquido</p>
                <p className={`text-3xl font-bold font-sans mt-1 ${dreData.resultado_liquido >= 0 ? 'text-emerald-400' : 'text-red-500'}`}>
                  {dreData.resultado_liquido.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
                <p className="text-xs text-zinc-500 font-mono mt-1">
                  Margem líquida: {dreData.margem_liquida}%
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Receitas */}
                <div className="glass-panel rounded-lg overflow-hidden">
                  <div className="p-4 bg-emerald-950/20 border-b border-zinc-900 flex justify-between items-center">
                    <span className="text-sm font-semibold text-emerald-400 font-sans">Receitas</span>
                    <span className="text-sm font-bold font-mono text-emerald-400">
                      {dreData.receitas.total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </span>
                  </div>
                  <div className="divide-y divide-zinc-900">
                    {dreData.receitas.itens.length === 0 ? (
                      <p className="p-4 text-xs text-zinc-500 font-mono">Nenhuma receita no período.</p>
                    ) : dreData.receitas.itens.map((item: any) => (
                      <div key={item.categoria} className="flex justify-between items-center p-3">
                        <span className="text-xs text-zinc-300 font-sans">{item.categoria}</span>
                        <span className="text-xs font-mono text-zinc-400">
                          {item.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Despesas */}
                <div className="glass-panel rounded-lg overflow-hidden">
                  <div className="p-4 bg-red-950/20 border-b border-zinc-900 flex justify-between items-center">
                    <span className="text-sm font-semibold text-red-400 font-sans">Despesas</span>
                    <span className="text-sm font-bold font-mono text-red-400">
                      {dreData.despesas.total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </span>
                  </div>
                  <div className="divide-y divide-zinc-900">
                    {dreData.despesas.itens.length === 0 ? (
                      <p className="p-4 text-xs text-zinc-500 font-mono">Nenhuma despesa no período.</p>
                    ) : dreData.despesas.itens.map((item: any) => (
                      <div key={item.categoria} className="flex justify-between items-center p-3">
                        <span className="text-xs text-zinc-300 font-sans">{item.categoria}</span>
                        <span className="text-xs font-mono text-zinc-400">
                          {item.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Pendentes */}
              {(dreData.pendentes.receitas > 0 || dreData.pendentes.despesas > 0) && (
                <div className="glass-panel p-4 rounded-lg border border-amber-900/40 bg-amber-950/10">
                  <p className="text-xs text-amber-400 font-mono uppercase tracking-widest mb-3">Pendências no período (vencimento)</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[11px] text-zinc-500 font-mono">A Receber</p>
                      <p className="text-sm font-bold text-emerald-400 font-mono">
                        {dreData.pendentes.receitas.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] text-zinc-500 font-mono">A Pagar</p>
                      <p className="text-sm font-bold text-red-400 font-mono">
                        {dreData.pendentes.despesas.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* CRM Panel */}
      {activeArea === 'crm' && (
        <div className="space-y-5">
          {/* Filtro período */}
          <div className="glass-panel p-4 rounded-lg flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-zinc-400 font-mono uppercase">De</label>
              <input type="date" value={crmDateFrom} onChange={e => setCrmDateFrom(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none font-mono" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-zinc-400 font-mono uppercase">Até</label>
              <input type="date" value={crmDateTo} onChange={e => setCrmDateTo(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-sm focus:outline-none font-mono" />
            </div>
            <button onClick={loadCRM}
              className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded cursor-pointer font-sans">
              Gerar
            </button>
            {(crmDateFrom || crmDateTo) && (
              <button onClick={() => { setCrmDateFrom(''); setCrmDateTo(''); setTimeout(loadCRM, 100); }}
                className="text-xs text-zinc-500 hover:text-white font-mono cursor-pointer">
                Limpar filtro
              </button>
            )}
          </div>

          {crmLoading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
              <p className="text-zinc-400 font-mono text-xs">Carregando relatório CRM...</p>
            </div>
          ) : crmData ? (
            <div className="space-y-4">

              {/* KPIs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="glass-panel p-4 rounded-lg">
                  <p className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Total de Leads</p>
                  <p className="text-2xl font-bold text-white mt-1">{crmData.negociacoes.total}</p>
                </div>
                <div className="glass-panel p-4 rounded-lg">
                  <p className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Perdidos</p>
                  <p className="text-2xl font-bold text-red-500 mt-1">{crmData.negociacoes.total_perdidas}</p>
                </div>
                <div className="glass-panel p-4 rounded-lg">
                  <p className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Taxa de Conversão</p>
                  <p className="text-2xl font-bold text-emerald-400 mt-1">{crmData.conversao.taxa}%</p>
                  <p className="text-[10px] text-zinc-500 font-mono mt-0.5">{crmData.conversao.total_fechamentos} fechamentos</p>
                </div>
                <div className="glass-panel p-4 rounded-lg">
                  <p className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Ticket Médio</p>
                  <p className="text-2xl font-bold text-white mt-1">
                    {crmData.ticket_medio.media.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                  </p>
                  <p className="text-[10px] text-zinc-500 font-mono mt-0.5">{crmData.ticket_medio.total_projetos} projetos concluídos</p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Negociações por etapa */}
                <div className="glass-panel rounded-lg overflow-hidden">
                  <div className="p-4 border-b border-zinc-900">
                    <p className="text-sm font-semibold text-white font-sans">Negociações por Etapa</p>
                  </div>
                  <div className="divide-y divide-zinc-900">
                    {['PROSPECCAO','ORCAMENTO','APRESENTACAO','NEGOCIACAO','FECHAMENTO','PERDIDO'].map(stage => {
                      const found = crmData.negociacoes.por_etapa.find((s: any) => s.funnel_status === stage);
                      const total = found ? found.total : 0;
                      const labels: Record<string,string> = { PROSPECCAO:'Prospecção', ORCAMENTO:'Orçamento', APRESENTACAO:'Apresentação', NEGOCIACAO:'Negociação', FECHAMENTO:'Fechamento', PERDIDO:'Perdidos' };
                      const pct = crmData.negociacoes.total > 0 ? Math.round(total / crmData.negociacoes.total * 100) : 0;
                      return (
                        <div key={stage} className="p-3 flex items-center gap-3">
                          <span className="text-xs text-zinc-400 font-sans w-28 shrink-0">{labels[stage]}</span>
                          <div className="flex-1 bg-zinc-900 rounded-full h-1.5 overflow-hidden">
                            <div className="h-full bg-red-600 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs font-mono text-zinc-300 w-6 text-right">{total}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Fonte do Lead */}
                <div className="glass-panel rounded-lg overflow-hidden">
                  <div className="p-4 border-b border-zinc-900">
                    <p className="text-sm font-semibold text-white font-sans">Fonte do Lead</p>
                  </div>
                  <div className="divide-y divide-zinc-900">
                    {crmData.fontes_lead.map((f: any) => (
                      <div key={f.fonte} className="flex justify-between items-center p-3">
                        <span className="text-xs text-zinc-300 font-sans">{f.fonte}</span>
                        <span className="text-xs font-mono font-bold text-zinc-400">{f.total}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Negócios perdidos */}
              {crmData.negociacoes.perdidas.length > 0 && (
                <div className="glass-panel rounded-lg overflow-hidden border-l-4 border-l-red-600">
                  <div className="p-4 border-b border-zinc-900">
                    <p className="text-sm font-semibold text-white font-sans">Negócios Perdidos — Motivos</p>
                  </div>
                  <div className="divide-y divide-zinc-900">
                    {crmData.negociacoes.perdidas.map((p: any, i: number) => (
                      <div key={i} className="p-3">
                        <p className="text-xs font-semibold text-zinc-200 font-sans">{p.name}</p>
                        <p className="text-[11px] text-zinc-500 font-mono mt-0.5">{p.lost_reason || 'Motivo não informado'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Fluxo de Caixa Consolidado */}
              <div className="glass-panel rounded-lg overflow-hidden">
                <div className="p-4 border-b border-zinc-900">
                  <p className="text-sm font-semibold text-white font-sans">Fluxo de Caixa Consolidado — Últimos 12 meses</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead className="bg-zinc-950/60 border-b border-zinc-900">
                      <tr>
                        <th className="text-left px-4 py-2.5 text-zinc-400">Mês</th>
                        <th className="text-right px-4 py-2.5 text-emerald-400">Receitas</th>
                        <th className="text-right px-4 py-2.5 text-red-400">Despesas</th>
                        <th className="text-right px-4 py-2.5 text-zinc-300">Resultado</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900">
                      {crmData.fluxo_caixa.map((row: any) => (
                        <tr key={row.mes} className="hover:bg-zinc-900/30">
                          <td className="px-4 py-2.5 text-zinc-400">{row.mes}</td>
                          <td className="px-4 py-2.5 text-right text-emerald-400">
                            {row.receitas.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </td>
                          <td className="px-4 py-2.5 text-right text-red-400">
                            {row.despesas.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </td>
                          <td className={`px-4 py-2.5 text-right font-bold ${row.resultado >= 0 ? 'text-emerald-400' : 'text-red-500'}`}>
                            {row.resultado.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          ) : null}
        </div>
      )}

      {/* Filters Panel — oculto quando DRE ou CRM está ativo */}
      {activeArea !== 'dre' && activeArea !== 'crm' && <div className="glass-panel p-5 rounded-lg space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono uppercase tracking-wider">
            <Filter className="w-3.5 h-3.5" /> Filtros — {AREAS.find(a => a.id === activeArea)?.label}
          </div>
          <button
            onClick={handleClearFilters}
            className="text-[11px] text-zinc-500 hover:text-white font-mono uppercase tracking-wider cursor-pointer"
          >
            Limpar filtros
          </button>
        </div>

        {activeArea === 'financial' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <FilterField label="Data Inicial">
              <input type="date" value={(filters.date_from as string) || ''} onChange={e => updateFilter('date_from', e.target.value)} className={inputClass} />
            </FilterField>
            <FilterField label="Data Final">
              <input type="date" value={(filters.date_to as string) || ''} onChange={e => updateFilter('date_to', e.target.value)} className={inputClass} />
            </FilterField>
            <FilterField label="Tipo">
              <select value={(filters.type as string) || ''} onChange={e => updateFilter('type', e.target.value)} className={inputClass}>
                <option value="">Todos</option>
                <option value="ENTRADA">Entrada</option>
                <option value="SAIDA">Saída</option>
              </select>
            </FilterField>
            <FilterField label="Categoria">
              <select value={(filters.category as string) || ''} onChange={e => updateFilter('category', e.target.value)} className={inputClass}>
                <option value="">Todas</option>
                {financialCategories.map(cat => <option key={cat.id} value={cat.name}>{cat.name}</option>)}
              </select>
            </FilterField>
            <FilterField label="Status">
              <select value={(filters.status_filter as string) || ''} onChange={e => updateFilter('status_filter', e.target.value)} className={inputClass}>
                <option value="">Todos</option>
                <option value="PAGO">Pago</option>
                <option value="PENDENTE">Pendente</option>
              </select>
            </FilterField>
            <FilterField label="Projeto">
              <select value={(filters.project_id as string) || ''} onChange={e => updateFilter('project_id', e.target.value)} className={inputClass}>
                <option value="">Todos</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            </FilterField>
          </div>
        )}

        {activeArea === 'clients' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <FilterField label="Cadastrado de">
              <input type="date" value={(filters.created_from as string) || ''} onChange={e => updateFilter('created_from', e.target.value)} className={inputClass} />
            </FilterField>
            <FilterField label="Cadastrado até">
              <input type="date" value={(filters.created_to as string) || ''} onChange={e => updateFilter('created_to', e.target.value)} className={inputClass} />
            </FilterField>
            <FilterField label="Buscar (nome, email ou CPF/CNPJ)">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500 w-3.5 h-3.5" />
                <input
                  type="text"
                  value={(filters.search as string) || ''}
                  onChange={e => updateFilter('search', e.target.value)}
                  placeholder="Ex: José ou 38.229..."
                  className={`${inputClass} pl-8`}
                />
              </div>
            </FilterField>
          </div>
        )}

        {activeArea === 'projects' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <FilterField label="Status">
              <select value={(filters.status_filter as string) || ''} onChange={e => updateFilter('status_filter', e.target.value)} className={inputClass}>
                <option value="">Todos</option>
                {PROJECT_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </FilterField>
            <FilterField label="Cliente">
              <select value={(filters.client_id as string) || ''} onChange={e => updateFilter('client_id', e.target.value)} className={inputClass}>
                <option value="">Todos</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FilterField>
            <FilterField label="Prazo de">
              <input type="date" value={(filters.deadline_from as string) || ''} onChange={e => updateFilter('deadline_from', e.target.value)} className={inputClass} />
            </FilterField>
            <FilterField label="Prazo até">
              <input type="date" value={(filters.deadline_to as string) || ''} onChange={e => updateFilter('deadline_to', e.target.value)} className={inputClass} />
            </FilterField>
          </div>
        )}

        {activeArea === 'stock' && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <button
                onClick={() => updateFilter('report_mode', 'items')}
                className={`px-3 py-1.5 text-xs font-mono uppercase rounded border cursor-pointer transition ${
                  (filters.report_mode || 'items') === 'items'
                    ? 'bg-red-600 border-red-600 text-white'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                Itens em Estoque
              </button>
              <button
                onClick={() => updateFilter('report_mode', 'movements')}
                className={`px-3 py-1.5 text-xs font-mono uppercase rounded border cursor-pointer transition ${
                  filters.report_mode === 'movements'
                    ? 'bg-red-600 border-red-600 text-white'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                Movimentações
              </button>
            </div>

            {(filters.report_mode || 'items') === 'items' ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <FilterField label="Categoria">
                  <select value={(filters.category_id as string) || ''} onChange={e => updateFilter('category_id', e.target.value)} className={inputClass}>
                    <option value="">Todas</option>
                    {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </FilterField>
                <FilterField label="">
                  <label className="flex items-center gap-2 text-xs text-zinc-300 font-mono mt-6 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(filters.low_stock_only)}
                      onChange={e => updateFilter('low_stock_only', e.target.checked)}
                      className="accent-red-600"
                    />
                    Somente abaixo do mínimo
                  </label>
                </FilterField>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <FilterField label="Tipo de Movimento">
                  <select value={(filters.movement_type as string) || ''} onChange={e => updateFilter('movement_type', e.target.value)} className={inputClass}>
                    <option value="">Todos</option>
                    <option value="ENTRADA">Entrada</option>
                    <option value="SAIDA">Saída</option>
                  </select>
                </FilterField>
                <FilterField label="Data Inicial">
                  <input type="date" value={(filters.date_from as string) || ''} onChange={e => updateFilter('date_from', e.target.value)} className={inputClass} />
                </FilterField>
                <FilterField label="Data Final">
                  <input type="date" value={(filters.date_to as string) || ''} onChange={e => updateFilter('date_to', e.target.value)} className={inputClass} />
                </FilterField>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-zinc-800">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-5 py-2.5 rounded shadow-lg flex items-center gap-2 transition active:scale-95 cursor-pointer font-sans disabled:opacity-60 disabled:cursor-wait"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileBarChart className="w-4 h-4" />}
            Gerar Relatório
          </button>
        </div>
      </div>}

      {activeArea === 'crm' && null}

      {error && (
        <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-16">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Consultando registros...</p>
        </div>
      )}

      {/* Report Preview */}
      {!loading && report && (
        <div className="space-y-5">

          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div>
              <h2 className="text-lg font-serif text-white">{report.title}</h2>
              <p className="text-[11px] text-zinc-500 font-mono">Gerado em {report.generated_at} — {report.rows.length} registro(s)</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExport('pdf')}
                disabled={exporting !== null}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-red-950/40 border border-zinc-800 hover:border-red-900/40 text-zinc-300 hover:text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              >
                {exporting === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                PDF
              </button>
              <button
                onClick={() => handleExport('xlsx')}
                disabled={exporting !== null}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-emerald-950/40 border border-zinc-800 hover:border-emerald-900/40 text-zinc-300 hover:text-emerald-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              >
                {exporting === 'xlsx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                Excel
              </button>
            </div>
          </div>

          {/* Summary Cards */}
          {report.summary.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
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

          {/* Detailed Table */}
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
      )}

      {!loading && !report && !error && (
        <div className="glass-panel rounded-lg py-16 flex flex-col items-center justify-center text-center px-6">
          <FileBarChart className="w-10 h-10 text-zinc-700 mb-3" />
          <p className="text-zinc-400 text-sm font-sans">Selecione a área, ajuste os filtros e gere o relatório para visualizar aqui.</p>
        </div>
      )}

    </div>
  );
}

const inputClass = "w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs focus:outline-none focus:border-red-656 font-mono";

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      {label && <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">{label}</label>}
      {children}
    </div>
  );
}
