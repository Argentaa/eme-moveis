import React, { useEffect, useState, useRef } from 'react';
import { 
  ArrowUpRight, ArrowDownRight, Wallet, Filter, Plus, Search, 
  Trash2, Landmark, Check, AlertTriangle, RefreshCw, Send, DollarSign, Edit3,
  Receipt, FileText, FileType, X, Loader2, ChevronDown, ChevronRight, UserX
} from 'lucide-react';
import { financialService, projectService, stockService, recurringService, getApiErrorMessage } from '../services/api';
import { FinancialRecord, Project, Category } from '../types';

interface FinancialViewProps {
  userRole: string;
}

export default function FinancialView({ userRole }: FinancialViewProps) {
  const [activeTab, setActiveTab] = useState<'records' | 'overdue'>('records');
  const [records, setRecords] = useState<FinancialRecord[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Search and Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<'TODOS' | 'ENTRADA' | 'SAIDA'>('TODOS');
  const [selectedCategory, setSelectedCategory] = useState<string>('TODOS');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');

  // Modal control
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRecordId, setEditingRecordId] = useState<string | null>(null);

  // Receipt generation states
  const [receiptMenuOpenId, setReceiptMenuOpenId] = useState<string | null>(null);
  const [generatingReceiptId, setGeneratingReceiptId] = useState<string | null>(null);
  const [receiptError, setReceiptError] = useState('');
  const [detailRecord, setDetailRecord] = useState<FinancialRecord | null>(null);
  const receiptMenuRef = useRef<HTMLDivElement | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    description: '',
    type: 'SAIDA' as 'ENTRADA' | 'SAIDA',
    category: '',
    amount: '',
    date: new Date().toISOString().substring(0, 10),
    due_date: new Date().toISOString().substring(0, 10),
    project_id: '',
    status: 'PAGO' as 'PAGO' | 'PENDENTE',
    mode: 'NORMAL' as 'NORMAL' | 'PARCELADO' | 'FIXO',
    installments: '2',
    frequency: 'MENSAL' as 'SEMANAL' | 'QUINZENAL' | 'MENSAL' | 'ANUAL',
  });

  // Overdue (pendências) tab state
  const [overdueData, setOverdueData] = useState<any>(null);
  const [overdueLoading, setOverdueLoading] = useState(true);
  const [expandedClientId, setExpandedClientId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState('');

  const canEditOrDelete = ['ADMIN', 'GERENTE'].includes(userRole);

  const loadData = async () => {
    setLoading(true);
    try {
      const [fins, projs, cats] = await Promise.all([
        financialService.getAll(),
        projectService.getAll(),
        stockService.getCategories('FINANCIAL')
      ]);
      setRecords(fins);
      setProjects(projs);
      setCategories(cats);
    } catch (err) {
      console.error('Erro ao ler dados do financeiro:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadOverdue = async () => {
    setOverdueLoading(true);
    try {
      const data = await financialService.getOverdue();
      setOverdueData(data);
    } catch (err) {
      console.error('Erro ao ler pendências:', err);
    } finally {
      setOverdueLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'overdue') {
      loadOverdue();
    }
  }, [activeTab]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (receiptMenuRef.current && !receiptMenuRef.current.contains(event.target as Node)) {
        setReceiptMenuOpenId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleGenerateReceipt = async (recordId: string, format: 'pdf' | 'docx') => {
    setReceiptError('');
    setReceiptMenuOpenId(null);
    setGeneratingReceiptId(recordId);
    try {
      await financialService.downloadReceipt(recordId, format);
    } catch (err) {
      console.error('Erro ao gerar recibo:', err);
      const message = getApiErrorMessage(err, 'Erro ao gerar o recibo. Tente novamente.');
      setReceiptError(message);
      alert(message);
    } finally {
      setGeneratingReceiptId(null);
    }
  };

  const handleOpenCreateModal = () => {
    setEditingRecordId(null);
    setFormData({
      description: '',
      type: 'SAIDA',
      category: categories[0]?.name || '',
      amount: '',
      date: new Date().toISOString().substring(0, 10),
      due_date: new Date().toISOString().substring(0, 10),
      project_id: '',
      status: 'PAGO'
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (record: FinancialRecord) => {
    setEditingRecordId(record.id);
    setFormData({
      description: record.description,
      type: record.type,
      category: record.category,
      amount: String(record.amount),
      date: record.date.substring(0, 10),
      due_date: record.due_date ? record.due_date.substring(0, 10) : record.date.substring(0, 10),
      project_id: record.project_id || '',
      status: record.status
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleSubmitRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    if (!formData.description || !formData.amount || !formData.date) {
      setSubmitError('Por favor, preencha a descrição, valor e a data do lançamento.');
      return;
    }

    if (!formData.category) {
      setSubmitError('Selecione uma categoria. Se nenhuma estiver disponível, cadastre uma em Acessos & TI > Categorias.');
      return;
    }

    try {
      const payload: any = {
        description: formData.description,
        type: formData.type,
        category: formData.category,
        amount: Number(formData.amount) || 0,
        date: formData.date,
        due_date: formData.due_date,
        project_id: formData.project_id || undefined,
        status: formData.status
      };

      if (editingRecordId) {
        await financialService.update(editingRecordId, payload);
      } else if (formData.mode === 'PARCELADO') {
        await recurringService.createExtended({
          ...payload,
          mode: 'PARCELADO',
          installments: Number(formData.installments) || 2,
        });
      } else if (formData.mode === 'FIXO') {
        await recurringService.createExtended({
          ...payload,
          mode: 'FIXO',
          frequency: formData.frequency,
          status: 'PENDENTE',
        });
      } else {
        await financialService.create(payload);
      }

      setIsModalOpen(false);
      setEditingRecordId(null);
      loadData();
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, editingRecordId ? 'Erro ao atualizar lançamento.' : 'Erro ao registrar movimentação.'));
    }
  };

  const handleToggleStatus = async (record: FinancialRecord) => {
    if (!canEditOrDelete) {
      alert('Apenas administradores e gerentes podem reconciliar status financeiros.');
      return;
    }

    const nextStatus = record.status === 'PAGO' ? 'PENDENTE' : 'PAGO';

    try {
      setRecords(prev => prev.map(f => f.id === record.id ? { ...f, status: nextStatus } : f));
      await financialService.update(record.id, { status: nextStatus });
    } catch (err) {
      console.error('Erro ao atualizar status do caixa:', err);
      alert(getApiErrorMessage(err, 'Erro ao atualizar status do lançamento.'));
      loadData();
    }
  };

  const handleDelete = async (id: string, description: string) => {
    if (!canEditOrDelete) {
      alert('Acesso negado: apenas administradores e gerentes podem excluir lançamentos.');
      return;
    }

    if (confirm(`Excluir definitivamente o lançamento "${description}"?\nEssa operação removerá os totais do fechamento anual.`)) {
      try {
        await financialService.delete(id);
        loadData();
      } catch (err) {
        console.error('Erro ao deletar financeiro:', err);
        alert(getApiErrorMessage(err, 'Erro ao excluir lançamento.'));
      }
    }
  };

  // Calculations for current selection
  const filteredRecords = records.filter(r => {
    const matchesSearch = r.description.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          r.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === 'TODOS' || r.type === selectedType;
    const matchesCategory = selectedCategory === 'TODOS' || r.category === selectedCategory;
    const recordDate = r.due_date || r.date;
    const matchesPeriodStart = !periodStart || recordDate >= periodStart;
    const matchesPeriodEnd = !periodEnd || recordDate <= periodEnd;
    return matchesSearch && matchesType && matchesCategory && matchesPeriodStart && matchesPeriodEnd;
  });

  const totalInflow = filteredRecords
    .filter(r => r.type === 'ENTRADA' && r.status === 'PAGO')
    .reduce((acc, r) => acc + r.amount, 0);

  const totalOutflow = filteredRecords
    .filter(r => r.type === 'SAIDA' && r.status === 'PAGO')
    .reduce((acc, r) => acc + r.amount, 0);

  const pendingInflow = filteredRecords
    .filter(r => r.type === 'ENTRADA' && r.status === 'PENDENTE')
    .reduce((acc, r) => acc + r.amount, 0);

  const pendingOutflow = filteredRecords
    .filter(r => r.type === 'SAIDA' && r.status === 'PENDENTE')
    .reduce((acc, r) => acc + r.amount, 0);

  const netBalance = totalInflow - totalOutflow;

  return (
    <div className="space-y-6">
      
      {/* Top Bar Section */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Fluxo de Caixa & Contabilidade</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Gestão de receitas, despesas e pagamentos.</p>
        </div>

        {['ADMIN', 'GERENTE'].includes(userRole) && (
          <button 
            onClick={handleOpenCreateModal}
            className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2.5 rounded shadow-lg flex items-center gap-1.5 transition active:scale-95 cursor-pointer font-sans"
          >
            <Plus className="w-4 h-4" /> Novo Lançamento
          </button>
        )}
      </div>

      {/* Sub-tabs selector */}
      <div className="flex gap-2 border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('records')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-mono uppercase tracking-wide transition cursor-pointer border-b-2 ${
            activeTab === 'records'
              ? 'text-white border-red-600'
              : 'text-zinc-500 border-transparent hover:text-zinc-300'
          }`}
        >
          <Landmark className="w-4 h-4" /> Lançamentos
        </button>
        <button
          onClick={() => setActiveTab('overdue')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-mono uppercase tracking-wide transition cursor-pointer border-b-2 ${
            activeTab === 'overdue'
              ? 'text-white border-red-600'
              : 'text-zinc-500 border-transparent hover:text-zinc-300'
          }`}
        >
          <AlertTriangle className="w-4 h-4" /> Pendências
        </button>
      </div>

      {activeTab === 'records' && (
      <>

      {/* Grid containing Quick accounting KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        
        {/* KPI 1 */}
        <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-emerald-600">
          <div>
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Receitas</span>
            <p className="text-xl font-bold font-sans text-emerald-400 mt-1">
              {totalInflow.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </p>
            {pendingInflow > 0 && (
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">
                A receber: {pendingInflow.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
              </span>
            )}
          </div>
          <div className="p-3 bg-zinc-950 rounded text-emerald-500 border border-zinc-900">
            <ArrowUpRight className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 2 */}
        <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-red-650">
          <div>
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Despesas</span>
            <p className="text-xl font-bold font-sans text-red-500 mt-1">
              {totalOutflow.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </p>
            {pendingOutflow > 0 && (
              <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">
                Contas a pagar: {pendingOutflow.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
              </span>
            )}
          </div>
          <div className="p-3 bg-zinc-950 rounded text-red-500 border border-zinc-900">
            <ArrowDownRight className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 3 */}
        <div className={`glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 ${netBalance >= 0 ? 'border-l-zinc-300' : 'border-l-red-800'}`}>
          <div>
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Saldo</span>
            <p className={`text-xl font-bold font-sans mt-1 ${netBalance >= 0 ? 'text-white' : 'text-red-500'}`}>
              {netBalance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </p>
            <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Resultados reconciliados e líquidos</span>
          </div>
          <div className="p-3 bg-zinc-950 rounded text-red-600 border border-zinc-900">
            <Wallet className="w-5 h-5" />
          </div>
        </div>

      </div>

      {/* Advanced Filters */}
      <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center">
        
        {/* Search */}
        <div className="relative w-full md:flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
          <input 
            type="text"
            placeholder="Buscar por descrição..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-805 text-white pl-9 pr-4 py-2 text-sm rounded focus:outline-none focus:border-red-656 font-sans"
          />
        </div>

        {/* Filter Type */}
        <div className="w-full md:w-auto flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-mono whitespace-nowrap">Histórico:</span>
          <select 
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as any)}
            className="bg-zinc-900 border border-zinc-805 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-656 font-mono"
          >
            <option value="TODOS">Todas Movimentações</option>
            <option value="ENTRADA">Apenas Entradas (Receitas)</option>
            <option value="SAIDA">Apenas Saídas (Despesas)</option>
          </select>
        </div>

        {/* Filter Category */}
        <div className="w-full md:w-auto flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-mono whitespace-nowrap">Categoria:</span>
          <select 
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-656 font-mono"
          >
            <option value="TODOS">Todas Categorias</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
        </div>

        {/* Filter Period */}
        <div className="w-full md:w-auto flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-mono whitespace-nowrap">Período:</span>
          <input
            type="date"
            value={periodStart}
            onChange={e => setPeriodStart(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-656 font-mono"
          />
          <span className="text-xs text-zinc-500 font-mono">até</span>
          <input
            type="date"
            value={periodEnd}
            onChange={e => setPeriodEnd(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-656 font-mono"
          />
          {(periodStart || periodEnd) && (
            <button
              onClick={() => { setPeriodStart(''); setPeriodEnd(''); }}
              className="text-xs text-zinc-500 hover:text-red-400 font-mono cursor-pointer"
              title="Limpar período"
            >✕</button>
          )}
        </div>

      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Acessando livro caixa...</p>
        </div>
      ) : (
        /* Balance entries list */
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                <tr>
                  <th className="py-4 px-6 font-normal">Data</th>
                  <th className="py-4 px-6 font-normal">Descrição do Lançamento</th>
                  <th className="py-4 px-6 font-normal">Categoria</th>
                  <th className="py-4 px-6 font-normal">Ambiente/Projeto</th>
                  <th className="py-4 px-6 font-normal text-right">Valor</th>
                  <th className="py-4 px-6 font-normal text-center">Status Recibo</th>
                  <th className="py-4 px-6 font-normal text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {filteredRecords.map((record) => {
                  const correlatedProj = projects.find(p => p.id === record.project_id);

                  return (
                    <tr key={record.id} className="hover:bg-zinc-900/40">
                      <td className="py-4 px-6 font-mono text-xs text-zinc-400 whitespace-nowrap">
                        {new Date(record.date + 'T00:00:00').toLocaleDateString('pt-BR')}
                      </td>
                      <td className="py-4 px-6">
                        <button
                          onClick={() => setDetailRecord(record)}
                          className="text-left cursor-pointer group"
                          title="Ver detalhes do lançamento"
                        >
                          <span className="font-semibold text-white font-sans text-sm block group-hover:underline">{record.description}</span>
                          <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Lançamento ID: {record.id}</span>
                        </button>
                      </td>
                      <td className="py-4 px-6">
                        <span className="inline-block px-2.5 py-0.5 text-xs font-semibold rounded bg-zinc-900 text-zinc-300 border border-zinc-800">
                          {record.category}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-xs text-zinc-400 font-sans">
                        {correlatedProj ? correlatedProj.title : <span className="text-zinc-650 font-mono">-</span>}
                      </td>
                      <td className={`py-4 px-6 text-right font-mono font-bold text-sm ${record.type === 'ENTRADA' ? 'text-emerald-400' : 'text-rose-500'}`}>
                        {record.type === 'ENTRADA' ? '+' : '-'} {record.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </td>
                      <td className="py-4 px-6 text-center">
                        <button
                          onClick={() => handleToggleStatus(record)}
                          disabled={!canEditOrDelete}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-mono font-bold rounded-full transition border ${
                            record.status === 'PAGO' 
                              ? 'bg-emerald-950/40 text-emerald-400 border-emerald-900/40 hover:bg-emerald-950/70' 
                              : 'bg-zinc-900 text-amber-500 border-amber-900/40 hover:bg-amber-950/70'
                          } ${canEditOrDelete ? 'cursor-pointer' : 'cursor-default'}`}
                          title={canEditOrDelete ? 'Clique para alterar status' : 'Status reconciliado'}
                        >
                          {record.status === 'PAGO' ? <Check className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                          <span>{record.status === 'PAGO' ? 'Pago' : 'Pendente'}</span>
                        </button>
                      </td>
                      <td className="py-4 px-6 text-right space-x-2 whitespace-nowrap">
                        <div className="relative inline-block" ref={receiptMenuOpenId === record.id ? receiptMenuRef : undefined}>
                          <button
                            onClick={() => setReceiptMenuOpenId(receiptMenuOpenId === record.id ? null : record.id)}
                            disabled={generatingReceiptId === record.id}
                            className="p-2 bg-zinc-900 hover:bg-emerald-950/40 text-zinc-400 hover:text-emerald-400 rounded border border-zinc-800 transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                            title="Gerar recibo"
                          >
                            {generatingReceiptId === record.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Receipt className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {receiptMenuOpenId === record.id && (
                            <div className="absolute right-0 mt-1 w-40 bg-zinc-900 border border-zinc-800 rounded shadow-xl z-20 overflow-hidden font-sans text-left">
                              <button
                                onClick={() => handleGenerateReceipt(record.id, 'pdf')}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white cursor-pointer"
                              >
                                <FileText className="w-3.5 h-3.5 text-red-500" /> Recibo em PDF
                              </button>
                              <button
                                onClick={() => handleGenerateReceipt(record.id, 'docx')}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white cursor-pointer border-t border-zinc-850"
                              >
                                <FileType className="w-3.5 h-3.5 text-blue-400" /> Recibo em Word
                              </button>
                            </div>
                          )}
                        </div>

                        {canEditOrDelete && (
                          <button 
                            onClick={() => handleOpenEditModal(record)}
                            className="p-2 bg-zinc-900 hover:bg-blue-950/40 text-zinc-400 hover:text-blue-400 rounded border border-zinc-800 transition cursor-pointer"
                            title="Editar Lançamento"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        )}

                        {canEditOrDelete && (
                          <button 
                            onClick={() => handleDelete(record.id, record.description)}
                            className="p-2 bg-zinc-900 hover:bg-red-950/40 text-zinc-400 hover:text-red-400 rounded border border-zinc-800 transition cursor-pointer"
                            title="Remover Registro"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}

                {filteredRecords.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-zinc-500 font-mono">
                      Nenhum lançamento corresponde aos filtros.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      </>
      )}

      {activeTab === 'overdue' && (
      <div className="space-y-5">

        {overdueLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
            <p className="text-zinc-400 font-mono text-xs">Verificando pendências...</p>
          </div>
        ) : !overdueData || overdueData.clients.length === 0 ? (
          <div className="glass-panel rounded-lg py-16 flex flex-col items-center justify-center text-center px-6">
            <Check className="w-10 h-10 text-emerald-600 mb-3" />
            <p className="text-zinc-300 text-sm font-sans">Nenhuma pendência vencida no momento. Tudo em dia!</p>
          </div>
        ) : (
          <>
            <div className="glass-panel p-5 rounded-lg border-l-4 border-l-red-650 flex justify-between items-center">
              <div>
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Total Vencido em Aberto</span>
                <p className="text-2xl font-bold font-sans text-red-500 mt-1">
                  {overdueData.grand_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-600" />
            </div>

            <div className="space-y-3">
              {overdueData.clients.map((client: any) => {
                const clientKey = client.client_id || 'sem-cliente';
                const isExpanded = expandedClientId === clientKey;
                return (
                  <div key={clientKey} className="glass-panel rounded-lg overflow-hidden">
                    <button
                      onClick={() => setExpandedClientId(isExpanded ? null : clientKey)}
                      className="w-full flex items-center justify-between p-4 hover:bg-zinc-900/40 transition cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        {isExpanded ? <ChevronDown className="w-4 h-4 text-zinc-400" /> : <ChevronRight className="w-4 h-4 text-zinc-400" />}
                        {client.client_name === 'Sem cliente vinculado' ? (
                          <UserX className="w-4 h-4 text-zinc-500" />
                        ) : (
                          <Landmark className="w-4 h-4 text-red-500" />
                        )}
                        <span className="text-sm font-semibold text-white font-sans">{client.client_name}</span>
                      </div>
                      <span className="text-sm font-bold font-mono text-red-500">
                        {client.total_overdue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </span>
                    </button>

                    {isExpanded && (
                      <div className="border-t border-zinc-900 divide-y divide-zinc-900">
                        {client.projects.map((proj: any) => (
                          <div key={proj.project_id || 'sem-projeto'} className="p-4 pl-10">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-xs font-semibold text-zinc-300 font-sans">{proj.project_title}</span>
                              <span className="text-xs font-bold font-mono text-amber-500">
                                {proj.subtotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                              </span>
                            </div>
                            <div className="space-y-1.5">
                              {proj.records.map((rec: any) => (
                                <div key={rec.id} className="flex justify-between items-center text-[11px] font-mono text-zinc-500 pl-4">
                                  <span>{rec.description} — venceu em {new Date(rec.date).toLocaleDateString('pt-BR', { timeZone: 'UTC' })}</span>
                                  <span className="text-zinc-400">{rec.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
      )}

      {/* Creation/Edit Modal form */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-bold text-white">
                  {editingRecordId ? 'Editar Lançamento Contábil' : 'Novo Lançamento Contábil'}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">Registro e controle de entradas e saídas financeiras.</p>
              </div>
              <button 
                onClick={() => { setIsModalOpen(false); setEditingRecordId(null); }}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleSubmitRecord} className="p-7 space-y-6 font-sans">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Descrição do Lançamento *</label>
                <input 
                  type="text"
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Ex: Compra de MDF e ferragens sob encomenda da fábrica"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Fluxo Financeiro</label>
                  <select 
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  >
                    <option value="SAIDA">SAÍDA (Despesa / Custo)</option>
                    <option value="ENTRADA">ENTRADA (Receita / Sinal)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Categoria do Caixa</label>
                  <select 
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  >
                    {categories.length === 0 && <option value="">Nenhuma categoria cadastrada</option>}
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.name}>{cat.name}</option>
                    ))}
                  </select>
                  {categories.length === 0 && (
                    <p className="text-[11px] text-amber-500 font-mono">
                      Cadastre categorias em Acessos & TI antes de lançar.
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor Nominal (R$) *</label>
                  <input 
                    type="number"
                    required
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    placeholder="2500"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data do Lançamento *</label>
                  <input 
                    type="date"
                    required
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data de Vencimento *</label>
                  <input 
                    type="date"
                    required
                    value={formData.due_date}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Vincular Ambiente / Projeto (Opcional)</label>
                  <select 
                    value={formData.project_id}
                    onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="">Nenhum</option>
                    {projects.map(p => (
                      <option key={p.id} value={p.id}>{p.title}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Ato Financeiro</label>
                  <select 
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="PAGO">EFETUADO (Pago / Recebido)</option>
                    <option value="PENDENTE">LANCADO (Pendente / A faturar)</option>
                  </select>
                </div>
              </div>

              {/* Modo de lançamento — só exibe na criação, não na edição */}
              {!editingRecordId && (
                <div className="space-y-3 p-4 bg-zinc-950/40 rounded-lg border border-zinc-800">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Modo de Lançamento</label>
                  <div className="flex gap-2">
                    {(['NORMAL', 'PARCELADO', 'FIXO'] as const).map(m => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setFormData({ ...formData, mode: m })}
                        className={`flex-1 py-2 text-xs font-mono rounded border transition cursor-pointer ${
                          formData.mode === m
                            ? 'bg-red-600 text-white border-red-600'
                            : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-white'
                        }`}
                      >
                        {m === 'NORMAL' ? '1x Normal' : m === 'PARCELADO' ? 'Parcelado' : 'Fixo / Recorrente'}
                      </button>
                    ))}
                  </div>

                  {formData.mode === 'PARCELADO' && (
                    <div className="space-y-2 mt-2">
                      <label className="text-xs text-zinc-400 font-mono block">Número de parcelas</label>
                      <input
                        type="number"
                        min={2}
                        max={60}
                        value={formData.installments}
                        onChange={e => setFormData({ ...formData, installments: e.target.value })}
                        className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-2.5 text-sm focus:outline-none focus:border-red-656 font-mono"
                      />
                      <p className="text-[11px] text-zinc-500 font-mono">
                        {Number(formData.installments) >= 2 && Number(formData.amount) > 0
                          ? `${formData.installments}x de R$ ${(Number(formData.amount) / Number(formData.installments)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })} — todas com status PENDENTE`
                          : 'Informe o valor e o número de parcelas'}
                      </p>
                    </div>
                  )}

                  {formData.mode === 'FIXO' && (
                    <div className="space-y-2 mt-2">
                      <label className="text-xs text-zinc-400 font-mono block">Frequência de repetição</label>
                      <select
                        value={formData.frequency}
                        onChange={e => setFormData({ ...formData, frequency: e.target.value as any })}
                        className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-2.5 text-sm focus:outline-none font-mono"
                      >
                        <option value="SEMANAL">Semanal (toda semana)</option>
                        <option value="QUINZENAL">Quinzenal (a cada 15 dias)</option>
                        <option value="MENSAL">Mensal (todo mês)</option>
                        <option value="ANUAL">Anual (todo ano)</option>
                      </select>
                      <p className="text-[11px] text-zinc-500 font-mono">
                        O primeiro lançamento é criado agora. Os próximos são gerados automaticamente.
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800 mt-6">
                <button 
                  type="button"
                  onClick={() => { setIsModalOpen(false); setEditingRecordId(null); }}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-800 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer"
                >
                  {editingRecordId ? 'Salvar Alterações' : 'Confirmar Lançamento'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Detail Modal — view record + generate receipt */}
      {detailRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-bold text-white">Detalhes do Lançamento</h3>
                <p className="text-xs text-zinc-400 font-mono">ID: {detailRecord.id}</p>
              </div>
              <button
                onClick={() => { setDetailRecord(null); setReceiptError(''); }}
                className="text-zinc-500 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-7 space-y-6 font-sans">
              <div>
                <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Descrição</span>
                <p className="text-white text-sm font-semibold mt-0.5">{detailRecord.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Tipo</span>
                  <p className={`text-sm font-semibold mt-0.5 ${detailRecord.type === 'ENTRADA' ? 'text-emerald-400' : 'text-rose-500'}`}>
                    {detailRecord.type === 'ENTRADA' ? 'Entrada' : 'Saída'}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Valor</span>
                  <p className="text-white text-sm font-mono font-bold mt-0.5">
                    {detailRecord.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Categoria</span>
                  <p className="text-zinc-300 text-sm mt-0.5">{detailRecord.category}</p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Data</span>
                  <p className="text-zinc-300 text-sm mt-0.5">
                    {new Date(detailRecord.date + 'T00:00:00').toLocaleDateString('pt-BR')}
                  </p>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Ambiente / Projeto</span>
                <p className="text-zinc-300 text-sm mt-0.5">
                  {projects.find(p => p.id === detailRecord.project_id)?.title || 'Nenhum vinculado'}
                </p>
              </div>

              {receiptError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {receiptError}
                </div>
              )}

              {canEditOrDelete && (
                <button
                  onClick={() => { setDetailRecord(null); handleOpenEditModal(detailRecord); }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-900 hover:bg-blue-950/40 border border-zinc-800 hover:border-blue-900/40 text-zinc-300 hover:text-blue-400 rounded text-sm font-medium transition cursor-pointer"
                >
                  <Edit3 className="w-4 h-4" /> Editar este lançamento
                </button>
              )}

              <div className="pt-4 border-t border-zinc-800 space-y-2">
                <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block mb-2">Gerar Recibo</span>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleGenerateReceipt(detailRecord.id, 'pdf')}
                    disabled={generatingReceiptId === detailRecord.id}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-900 hover:bg-red-950/40 border border-zinc-800 hover:border-red-900/40 text-zinc-300 hover:text-red-400 rounded text-sm font-medium transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                  >
                    {generatingReceiptId === detailRecord.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                    PDF
                  </button>
                  <button
                    onClick={() => handleGenerateReceipt(detailRecord.id, 'docx')}
                    disabled={generatingReceiptId === detailRecord.id}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-900 hover:bg-blue-950/40 border border-zinc-800 hover:border-blue-900/40 text-zinc-300 hover:text-blue-400 rounded text-sm font-medium transition cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                  >
                    {generatingReceiptId === detailRecord.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileType className="w-4 h-4" />
                    )}
                    Word
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
