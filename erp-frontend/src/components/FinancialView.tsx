import React, { useEffect, useState, useRef } from 'react';
import { 
  ArrowUpRight, ArrowDownRight, Wallet, Filter, Plus, Search, 
  Trash2, Landmark, Check, AlertTriangle, RefreshCw, Send, DollarSign, Edit3,
  Receipt, FileText, FileType, X, Loader2, ChevronDown, ChevronRight, UserX,
  Target, Truck, BarChart3, TrendingUp
} from 'lucide-react';
import { financialService, projectService, stockService, recurringService, clientService, supplierService, budgetService, reportService, bankAccountService, getApiErrorMessage } from '../services/api';
import { FinancialRecord, Project, Category, Supplier, BudgetGoal, BudgetAnalysis, Client, ReportResult, BankAccount, BankOverview } from '../types';

interface FinancialViewProps {
  userRole: string;
}

export default function FinancialView({ userRole }: FinancialViewProps) {
  const [activeTab, setActiveTab] = useState<'records' | 'overdue' | 'banks'>('records');
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
    doc_number: '',
    issue_date: '',
    doc_type: '',
    bank: '',
    bank_account_id: '',
    account_plan: '',
    item_description: '',
    client_id: '',
    supplier_id: '',
    is_recurring: false,
  });

  // Overdue (pendências) tab state
  const [overdueData, setOverdueData] = useState<any>(null);
  const [overdueLoading, setOverdueLoading] = useState(true);
  const [expandedClientId, setExpandedClientId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState('');
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [clients, setClients] = useState<Client[]>([]);

  // Fluxo de caixa
  const [cfData, setCfData] = useState<ReportResult | null>(null);
  const [cfLoading, setCfLoading] = useState(false);
  const [cfYear, setCfYear] = useState(new Date().getFullYear());

  // Orçamento
  const [budgetData, setBudgetData] = useState<BudgetAnalysis | null>(null);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [goals, setGoals] = useState<BudgetGoal[]>([]);
  const [budgetYear, setBudgetYear] = useState(new Date().getFullYear());
  const [budgetMonth, setBudgetMonth] = useState('');
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [editingGoalId, setEditingGoalId] = useState<string | null>(null);
  const [goalForm, setGoalForm] = useState({ year: new Date().getFullYear(), month: '', category: '', target_value: '' });
  const [goalError, setGoalError] = useState('');
  const [goalSaving, setGoalSaving] = useState(false);

  // Fornecedor inline
  const [isSupplierModalOpen, setIsSupplierModalOpen] = useState(false);
  const [newSupplierName, setNewSupplierName] = useState('');
  const [supplierError, setSupplierError] = useState('');

  // Contas bancárias
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankOverview, setBankOverview] = useState<BankOverview | null>(null);
  const [bankLoading, setBankLoading] = useState(false);
  const [bankModalOpen, setBankModalOpen] = useState(false);
  const [editingBankId, setEditingBankId] = useState<string | null>(null);
  const [bankFormData, setBankFormData] = useState({ name: '', bank: '', agency: '', account_number: '', account_type: 'CORRENTE', opening_balance: '', opening_date: '', low_balance_threshold: '', notes: '', active: true });
  const [bankError, setBankError] = useState('');
  const [bankSaving, setBankSaving] = useState(false);

  const canEditOrDelete = ['ADMIN', 'GERENTE'].includes(userRole);

  const reloadBudget = async () => {
    try {
      const [analysis, gols] = await Promise.all([
        budgetService.getAnalysis(budgetYear, budgetMonth),
        budgetService.getGoals(budgetYear, budgetMonth ? Number(budgetMonth) : undefined),
      ]);
      setBudgetData(analysis);
      setGoals(gols);
    } catch (err) {
      console.error('Erro ao recarregar orçamento:', err);
    }
  };

  const handleOpenGoalModal = (goal?: BudgetGoal) => {
    setEditingGoalId(goal ? goal.id : null);
    setGoalForm({
      year: goal ? goal.year : budgetYear,
      month: goal && goal.month ? String(goal.month) : '',
      category: goal ? goal.category : '',
      target_value: goal ? String(goal.target_value) : '',
    });
    setGoalError('');
    setIsGoalModalOpen(true);
  };

  const handleSubmitGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    setGoalError('');
    const cat = goalForm.category.trim();
    if (!cat || !goalForm.target_value) {
      setGoalError('Categoria e valor da meta são obrigatórios.');
      return;
    }
    setGoalSaving(true);
    try {
      const payload = {
        year: Number(goalForm.year) || budgetYear,
        month: goalForm.month ? Number(goalForm.month) : null,
        category: cat,
        target_value: Number(goalForm.target_value) || 0,
      };
      if (editingGoalId) {
        await budgetService.updateGoal(editingGoalId, payload);
      } else {
        await budgetService.createGoal(payload);
      }
      setIsGoalModalOpen(false);
      reloadBudget();
    } catch (err) {
      setGoalError(getApiErrorMessage(err, 'Erro ao salvar a meta.'));
    } finally {
      setGoalSaving(false);
    }
  };

  const handleDeleteGoal = async (goal: BudgetGoal) => {
    if (!window.confirm('Excluir esta meta de orçamento?')) return;
    try {
      await budgetService.removeGoal(goal.id);
      reloadBudget();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir a meta.'));
    }
  };

  const handleCreateSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    setSupplierError('');
    if (!newSupplierName.trim()) {
      setSupplierError('Informe o nome do fornecedor.');
      return;
    }
    try {
      const sup = await supplierService.create({ name: newSupplierName.trim() });
      setSuppliers(prev => [...prev, sup]);
      setFormData(prev => ({ ...prev, supplier_id: sup.id }));
      setIsSupplierModalOpen(false);
      setNewSupplierName('');
    } catch (err) {
      setSupplierError(getApiErrorMessage(err, 'Erro ao criar fornecedor.'));
    }
  };

  // ── Contas bancárias helpers ──────────────────────────────────
  const reloadBanks = async () => {
    try {
      setBankLoading(true);
      const [banks, overview] = await Promise.all([
        bankAccountService.list().catch(() => [] as BankAccount[]),
        bankAccountService.overview().catch(() => null as unknown as BankOverview),
      ]);
      setBankAccounts(banks as BankAccount[]);
      if (overview) setBankOverview(overview as BankOverview);
    } catch { /* ignore */ } finally { setBankLoading(false); }
  };

  const handleOpenBankModal = (bank?: BankAccount) => {
    if (bank) {
      setEditingBankId(bank.id);
      setBankFormData({
        name: bank.name || '',
        bank: bank.bank || '',
        agency: bank.agency || '',
        account_number: bank.account_number || '',
        account_type: bank.account_type || 'CORRENTE',
        opening_balance: String(bank.opening_balance ?? ''),
        opening_date: bank.opening_date ? bank.opening_date.substring(0, 10) : '',
        low_balance_threshold: bank.low_balance_threshold != null ? String(bank.low_balance_threshold) : '',
        notes: bank.notes || '',
        active: bank.active,
      });
    } else {
      setEditingBankId(null);
      setBankFormData({ name: '', bank: '', agency: '', account_number: '', account_type: 'CORRENTE', opening_balance: '', opening_date: '', low_balance_threshold: '', notes: '', active: true });
    }
    setBankError('');
    setBankModalOpen(true);
  };

  const handleSubmitBank = async (e: React.FormEvent) => {
    e.preventDefault();
    setBankError('');
    if (!bankFormData.name.trim()) {
      setBankError('Nome da conta é obrigatório.');
      return;
    }
    setBankSaving(true);
    try {
      const payload: any = {
        name: bankFormData.name.trim(),
        bank: bankFormData.bank.trim(),
        agency: bankFormData.agency.trim(),
        account_number: bankFormData.account_number.trim(),
        account_type: bankFormData.account_type,
        opening_balance: bankFormData.opening_balance ? Number(bankFormData.opening_balance) : 0,
        opening_date: bankFormData.opening_date || null,
        low_balance_threshold: bankFormData.low_balance_threshold ? Number(bankFormData.low_balance_threshold) : null,
        notes: bankFormData.notes.trim(),
        active: bankFormData.active,
      };
      if (editingBankId) {
        await bankAccountService.update(editingBankId, payload);
      } else {
        await bankAccountService.create(payload);
      }
      setBankModalOpen(false);
      setEditingBankId(null);
      reloadBanks();
    } catch (err) {
      setBankError(getApiErrorMessage(err, 'Erro ao salvar conta bancária.'));
    } finally {
      setBankSaving(false);
    }
  };

  const handleDeleteBank = async (id: string, name: string) => {
    if (!window.confirm(`Excluir a conta "${name}"? Esta ação só é permitida se não houver lançamentos vinculados.`)) return;
    try {
      await bankAccountService.remove(id);
      reloadBanks();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir conta bancária.'));
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [fins, projs, cats, supps, clis] = await Promise.all([
        financialService.getAll(),
        projectService.getAll(),
        stockService.getCategories('FINANCIAL'),
        supplierService.getAll().catch(() => []),
        clientService.getAll().catch(() => []),
      ]);
      setRecords(fins);
      setProjects(projs);
      setCategories(cats);
      setSuppliers(supps);
      setClients(clis);
    } catch (err) {
      console.error('Erro ao ler dados do financeiro:', err);
    } finally {
      setLoading(false);
    }
    // Contas bancárias (silencioso se falhar)
    try {
      setBankLoading(true);
      const [banks, overview] = await Promise.all([
        bankAccountService.list().catch(() => [] as BankAccount[]),
        bankAccountService.overview().catch(() => null as unknown as BankOverview),
      ]);
      setBankAccounts(banks as BankAccount[]);
      if (overview) setBankOverview(overview as BankOverview);
    } catch { /* ignore */ } finally { setBankLoading(false); }
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
    let active = true;
    setCfLoading(true);
    reportService.getReport('cash-flow', { year: String(cfYear) })
      .then((data) => { if (active) setCfData(data); })
      .catch(() => { if (active) setCfData(null); })
      .finally(() => { if (active) setCfLoading(false); });
    return () => { active = false; };
  }, [cfYear]);

  useEffect(() => {
    let active = true;
    setBudgetLoading(true);
    Promise.all([
      budgetService.getAnalysis(budgetYear, budgetMonth),
      budgetService.getGoals(budgetYear, budgetMonth ? Number(budgetMonth) : undefined),
    ])
      .then(([analysis, gols]) => {
        if (active) {
          setBudgetData(analysis);
          setGoals(gols);
        }
      })
      .catch((err) => {
        console.error('Erro ao carregar orçamento:', err);
        if (active) setBudgetData(null);
      })
      .finally(() => { if (active) setBudgetLoading(false); });
    return () => { active = false; };
  }, [budgetYear, budgetMonth]);

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
      status: 'PAGO',
      mode: 'NORMAL',
      installments: '1',
      doc_number: '',
      issue_date: '',
      doc_type: '',
      bank: '',
      bank_account_id: '',
      account_plan: '',
      item_description: '',
      client_id: '',
      supplier_id: '',
      is_recurring: false,
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
      status: record.status,
      mode: 'NORMAL',
      installments: record.installments ? String(record.installments) : '1',
      doc_number: record.doc_number || '',
      issue_date: record.issue_date ? record.issue_date.substring(0, 10) : '',
      doc_type: record.doc_type || '',
      bank: record.bank || '',
      bank_account_id: record.bank_account_id || '',
      account_plan: record.account_plan || '',
      item_description: record.item_description || '',
      client_id: record.client_id || '',
      supplier_id: record.supplier_id || '',
      is_recurring: record.is_recurring || false,
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
        status: formData.status,
        doc_number: formData.doc_number || undefined,
        issue_date: formData.issue_date || undefined,
        doc_type: formData.doc_type || undefined,
        bank: formData.bank || undefined,
        bank_account_id: formData.bank_account_id || null,
        account_plan: formData.account_plan || undefined,
        item_description: formData.item_description || undefined,
        installments: Number(formData.installments) || 1,
        client_id: formData.client_id || undefined,
        supplier_id: formData.supplier_id || undefined,
        is_recurring: formData.is_recurring,
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
        <button
          onClick={() => setActiveTab('banks')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-mono uppercase tracking-wide transition cursor-pointer border-b-2 ${
            activeTab === 'banks'
              ? 'text-white border-red-600'
              : 'text-zinc-500 border-transparent hover:text-zinc-300'
          }`}
        >
          <Wallet className="w-4 h-4" /> Contas Bancárias
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

      {/* Fluxo de Caixa Mensal */}
      <div className="glass-panel rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-red-500" />
            <h3 className="text-sm font-semibold text-white font-sans">Fluxo de Caixa Mensal</h3>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-zinc-400 font-mono">Ano:</label>
            <select
              value={cfYear}
              onChange={(e) => setCfYear(Number(e.target.value))}
              className="bg-zinc-900 border border-zinc-800 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-600 font-mono"
            >
              {[cfYear - 1, cfYear, cfYear + 1].map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <TrendingUp className="w-4 h-4 text-zinc-600" />
          </div>
        </div>
        {cfLoading ? (
          <div className="flex justify-center py-6">
            <RefreshCw className="w-6 h-6 text-red-600 animate-spin" />
          </div>
        ) : cfData ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {cfData.summary.map((s) => (
                <div key={s.label} className="bg-zinc-950/50 rounded p-3 border border-zinc-900">
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">{s.label}</span>
                  <span className={`text-sm font-bold font-mono block mt-1 ${s.tone === 'positive' ? 'text-emerald-400' : s.tone === 'negative' ? 'text-red-500' : 'text-white'}`}>{s.value}</span>
                </div>
              ))}
            </div>
            <CFBarChart data={cfData} />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono text-zinc-300">
                <thead className="text-zinc-500 uppercase tracking-wider border-b border-zinc-900">
                  <tr>
                    {cfData.columns.map((c) => (
                      <th key={c.key} className="py-2 pr-4 font-normal">{c.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {cfData.rows.map((row: any) => (
                    <tr key={row.month} className="hover:bg-zinc-900/40">
                      <td className="py-2 pr-4 text-zinc-400">{row.month}</td>
                      <td className="py-2 pr-4 text-emerald-400">{row.income}</td>
                      <td className="py-2 pr-4 text-red-500">{row.outcome}</td>
                      <td className="py-2 pr-4 text-white">{row.balance}</td>
                      <td className="py-2 pr-4 text-zinc-300">{row.accumulated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-xs text-zinc-500 font-mono">Não foi possível carregar o fluxo de caixa.</p>
        )}
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
                  <th className="py-4 px-6 font-normal">Conta</th>
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
                      <td className="py-4 px-6 text-xs text-zinc-400 font-mono">
                        {record.bank_account_name || record.bank || <span className="text-zinc-600">—</span>}
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
                    <td colSpan={8} className="py-12 text-center text-zinc-500 font-mono">
                      Nenhum lançamento corresponde aos filtros.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Orçamento x Realizado */}
      <div className="glass-panel rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-red-500" />
            <h3 className="text-sm font-semibold text-white font-sans">Planejamento Orçamentário</h3>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={budgetYear}
              onChange={(e) => setBudgetYear(Number(e.target.value))}
              className="bg-zinc-900 border border-zinc-800 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-600 font-mono"
            >
              {[budgetYear - 1, budgetYear, budgetYear + 1].map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              value={budgetMonth}
              onChange={(e) => setBudgetMonth(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-600 font-mono"
            >
              <option value="">Ano todo</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                <option key={m} value={m}>Mês {m}</option>
              ))}
            </select>
            {canEditOrDelete && (
              <button
                onClick={() => handleOpenGoalModal()}
                className="bg-red-600 hover:bg-red-700 text-white text-xs font-medium px-3 py-1.5 rounded flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" /> Nova Meta
              </button>
            )}
          </div>
        </div>

        {budgetLoading ? (
          <div className="flex justify-center py-6">
            <RefreshCw className="w-6 h-6 text-red-600 animate-spin" />
          </div>
        ) : budgetData ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {budgetData.summary.map((s) => (
                <div key={s.label} className="bg-zinc-950/50 rounded p-3 border border-zinc-900">
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">{s.label}</span>
                  <span className={`text-sm font-bold font-mono block mt-1 ${s.tone === 'positive' ? 'text-emerald-400' : s.tone === 'negative' ? 'text-red-500' : 'text-white'}`}>{s.value}</span>
                </div>
              ))}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono text-zinc-300">
                <thead className="text-zinc-500 uppercase tracking-wider border-b border-zinc-900">
                  <tr>
                    <th className="py-2 pr-4 font-normal">Categoria</th>
                    <th className="py-2 pr-4 font-normal">Orçado</th>
                    <th className="py-2 pr-4 font-normal">Realizado</th>
                    <th className="py-2 pr-4 font-normal">Diferença</th>
                    <th className="py-2 pr-4 font-normal w-40">% Realizado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {budgetData.rows.map((row) => {
                    const pct = row.percentage === '--' ? 0 : Number(row.percentage.replace('%', '').replace(',', '.'));
                    const pctCls = pct >= 100 ? 'bg-red-600' : pct >= 60 ? 'bg-emerald-600' : 'bg-amber-600';
                    return (
                      <tr key={row.category} className="hover:bg-zinc-900/40">
                        <td className="py-2.5 pr-4 text-white font-sans">{row.category}</td>
                        <td className="py-2.5 pr-4 text-zinc-300">{row.budget}</td>
                        <td className="py-2.5 pr-4 text-zinc-300">{row.actual}</td>
                        <td className="py-2.5 pr-4 text-zinc-300">{row.difference}</td>
                        <td className="py-2.5 pr-4">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-zinc-900 rounded overflow-hidden">
                              <div className={`h-full ${pctCls}`} style={{ width: `${Math.min(100, pct)}%` }} />
                            </div>
                            <span className="text-[11px] text-zinc-400 shrink-0">{row.percentage}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {goals.length > 0 && (
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">Metas cadastradas:</span>
                {goals.map((g) => (
                  <span key={g.id} className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-300 rounded">
                    {g.category} — {g.target_value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                    {g.month ? ` (mês ${g.month})` : ' (anual)'}
                    {canEditOrDelete && (
                      <>
                        <button onClick={() => handleOpenGoalModal(g)} className="text-zinc-500 hover:text-sky-400 cursor-pointer" title="Editar"><Edit3 className="w-3 h-3" /></button>
                        <button onClick={() => handleDeleteGoal(g)} className="text-zinc-500 hover:text-red-400 cursor-pointer" title="Excluir"><Trash2 className="w-3 h-3" /></button>
                      </>
                    )}
                  </span>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="text-xs text-zinc-500 font-mono">Não foi possível carregar o orçamento.</p>
        )}
      </div>

      </>
      )}

      {activeTab === 'banks' && (
        <div className="space-y-5">
          {/* Overview */}
          {bankOverview ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-emerald-600">
                <div>
                  <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Total em Contas</span>
                  <p className="text-xl font-bold font-sans text-emerald-400 mt-1">
                    {bankOverview.total_balance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                  <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Saldo consolidado atual</span>
                </div>
                <div className="p-3 bg-zinc-950 rounded text-emerald-500 border border-zinc-900">
                  <Wallet className="w-5 h-5" />
                </div>
              </div>
              <div className="glass-panel p-5 rounded-lg flex justify-between items-center border-l-4 border-l-sky-600">
                <div>
                  <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">Total Projetado</span>
                  <p className="text-xl font-bold font-sans text-sky-400 mt-1">
                    {bankOverview.total_projected.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                  <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">Com pendentes reconciliados</span>
                </div>
                <div className="p-3 bg-zinc-950 rounded text-sky-500 border border-zinc-900">
                  <TrendingUp className="w-5 h-5" />
                </div>
              </div>
            </div>
          ) : bankLoading ? (
            <div className="flex justify-center py-6"><RefreshCw className="w-6 h-6 text-red-600 animate-spin" /></div>
          ) : null}

          <div className="flex justify-between items-center">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Landmark className="w-5 h-5 text-red-600" /> Contas Bancárias
            </h3>
            {canEditOrDelete && (
              <button
                onClick={() => handleOpenBankModal()}
                className="bg-red-600 hover:bg-red-700 text-white text-xs font-medium px-3 py-2 rounded flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" /> Nova Conta
              </button>
            )}
          </div>

          {bankLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 text-red-600 animate-spin mb-3" />
              <p className="text-zinc-400 font-mono text-xs">Carregando contas...</p>
            </div>
          ) : bankAccounts.length === 0 ? (
            <div className="glass-panel rounded-lg py-12 flex flex-col items-center justify-center text-center px-6">
              <Landmark className="w-8 h-8 text-zinc-600 mb-3" />
              <p className="text-zinc-400 text-sm font-mono">Nenhuma conta bancária cadastrada.</p>
              <p className="text-zinc-500 text-xs font-mono mt-1">Cadastre sua primeira conta para vincular lançamentos.</p>
            </div>
          ) : (
            <>
              {/* Cards grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {bankAccounts.map(acc => (
                  <div key={acc.id} className="glass-panel p-5 rounded-lg border border-zinc-800">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="text-sm font-semibold text-white font-sans">{acc.name}</h4>
                        <p className="text-xs text-zinc-400 font-mono mt-0.5">{acc.bank || '—'} {acc.agency ? `· Ag ${acc.agency}` : ''} {acc.account_number ? `· ${acc.account_number}` : ''}</p>
                      </div>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${acc.active ? 'bg-emerald-950/40 text-emerald-400 border-emerald-900/30' : 'bg-zinc-900 text-zinc-500 border-zinc-800'}`}>
                        {acc.active ? 'Ativa' : 'Inativa'}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <span className={`text-lg font-bold font-mono ${acc.current_balance >= 0 ? 'text-emerald-400' : 'text-red-500'}`}>
                        {acc.current_balance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">{acc.account_type}</span>
                    </div>
                    <div className="mt-2 text-[11px] font-mono text-zinc-500 space-y-0.5">
                      <div>Abertura: {acc.opening_balance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} {acc.opening_date ? `· ${new Date(acc.opening_date).toLocaleDateString('pt-BR')}` : ''}</div>
                      {acc.low_balance_threshold != null && (
                        <div>Alerta saldo baixo: {Number(acc.low_balance_threshold).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</div>
                      )}
                      {acc.notes && <div className="text-zinc-400 truncate">{acc.notes}</div>}
                    </div>
                  </div>
                ))}
              </div>

              {/* Tabela */}
              <div className="glass-panel rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-zinc-300">
                    <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-900">
                      <tr>
                        <th className="py-3 px-4 font-normal">Conta</th>
                        <th className="py-3 px-4 font-normal">Banco</th>
                        <th className="py-3 px-4 font-normal">Agência / Número</th>
                        <th className="py-3 px-4 font-normal">Tipo</th>
                        <th className="py-3 px-4 font-normal text-right">Saldo Atual</th>
                        <th className="py-3 px-4 font-normal text-center">Status</th>
                        {canEditOrDelete && <th className="py-3 px-4 font-normal text-right">Ações</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900">
                      {bankAccounts.map(acc => (
                        <tr key={acc.id} className="hover:bg-zinc-900/40">
                          <td className="py-3 px-4 font-sans font-medium text-white">{acc.name}</td>
                          <td className="py-3 px-4 text-zinc-400 font-mono text-xs">{acc.bank || '—'}</td>
                          <td className="py-3 px-4 text-zinc-400 font-mono text-xs">{acc.agency || '—'} / {acc.account_number || '—'}</td>
                          <td className="py-3 px-4"><span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800">{acc.account_type}</span></td>
                          <td className={`py-3 px-4 text-right font-mono font-bold text-sm ${acc.current_balance >= 0 ? 'text-emerald-400' : 'text-red-500'}`}>
                            {acc.current_balance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className={`text-[11px] font-mono px-2 py-0.5 rounded border ${acc.active ? 'bg-emerald-950/40 text-emerald-400 border-emerald-900/30' : 'bg-zinc-900 text-zinc-500 border-zinc-800'}`}>
                              {acc.active ? 'Ativa' : 'Inativa'}
                            </span>
                          </td>
                          {canEditOrDelete && (
                            <td className="py-3 px-4 text-right space-x-1">
                              <button onClick={() => handleOpenBankModal(acc)} className="p-2 bg-zinc-900 hover:bg-blue-950/40 text-zinc-400 hover:text-blue-400 rounded border border-zinc-800 transition cursor-pointer" title="Editar"><Edit3 className="w-3.5 h-3.5" /></button>
                              <button onClick={() => handleDeleteBank(acc.id, acc.name)} className="p-2 bg-zinc-900 hover:bg-red-950/40 text-zinc-400 hover:text-red-400 rounded border border-zinc-800 transition cursor-pointer" title="Excluir"><Trash2 className="w-3.5 h-3.5" /></button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
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
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nº do Documento</label>
                  <input
                    type="text"
                    value={formData.doc_number}
                    onChange={(e) => setFormData({ ...formData, doc_number: e.target.value })}
                    placeholder="Ex: NF 456 / Boleto 00123"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data de Emissão</label>
                  <input
                    type="date"
                    value={formData.issue_date}
                    onChange={(e) => setFormData({ ...formData, issue_date: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Tipo de Documento</label>
                  <select
                    value={formData.doc_type}
                    onChange={(e) => setFormData({ ...formData, doc_type: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="">— Selecione —</option>
                    <option value="BOLETO">Boleto</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="DEBITO_AUTOMATICO">Débito Automático</option>
                    <option value="DINHEIRO">Dinheiro</option>
                    <option value="FATURA">Fatura</option>
                    <option value="PIX">PIX</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Banco / Conta (legado)</label>
                  <input
                    type="text"
                    value={formData.bank}
                    onChange={(e) => setFormData({ ...formData, bank: e.target.value })}
                    placeholder="Ex: Sicredi 1234"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Conta Bancária</label>
                <select
                  value={formData.bank_account_id}
                  onChange={(e) => {
                    const val = e.target.value;
                    const acc = bankAccounts.find(b => b.id === val);
                    setFormData(prev => ({
                      ...prev,
                      bank_account_id: val,
                      bank: acc?.bank ? acc.bank : prev.bank,
                    }));
                  }}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                >
                  <option value="">Nenhuma (usar bank texto)</option>
                  {bankAccounts.filter(b => b.active).map(b => (
                    <option key={b.id} value={b.id}>{b.name} — {b.bank || 'sem banco'}</option>
                  ))}
                </select>
                {bankAccounts.length === 0 && (
                  <p className="text-[11px] text-zinc-500 font-mono">Cadastre contas na aba Contas Bancárias para vincular.</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Cliente (Opcional)</label>
                  <select
                    value={formData.client_id}
                    onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="">Nenhum</option>
                    {clients.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Fornecedor (Opcional)</label>
                  <div className="flex gap-2">
                    <select
                      value={formData.supplier_id}
                      onChange={(e) => setFormData({ ...formData, supplier_id: e.target.value })}
                      className="flex-1 bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                    >
                      <option value="">Nenhum</option>
                      {suppliers.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                    {canEditOrDelete && (
                      <button
                        type="button"
                        onClick={() => { setNewSupplierName(''); setSupplierError(''); setIsSupplierModalOpen(true); }}
                        className="px-3 bg-zinc-900 hover:bg-emerald-950/40 text-zinc-400 hover:text-emerald-400 rounded border border-zinc-800 transition cursor-pointer"
                        title="Cadastrar fornecedor"
                      >
                        <Truck className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Plano de Contas</label>
                  <input
                    type="text"
                    value={formData.account_plan}
                    onChange={(e) => setFormData({ ...formData, account_plan: e.target.value })}
                    placeholder="Ex: 3.1.01 – Materiais"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nº de Parcelas</label>
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={formData.installments}
                    onChange={(e) => setFormData({ ...formData, installments: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Descrição do Item / Serviço (Detalhada)</label>
                <textarea
                  value={formData.item_description}
                  onChange={(e) => setFormData({ ...formData, item_description: e.target.value })}
                  rows={2}
                  placeholder="Ex: 12 chapas de MDF 15mm, ferragens, corrediças..."
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 resize-none"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_recurring}
                  onChange={(e) => setFormData({ ...formData, is_recurring: e.target.checked })}
                  className="accent-red-600 w-4 h-4"
                />
                Despesa Recorrente
              </label>

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

      {/* Goal Modal — nova meta de orçamento */}
      {isGoalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 p-5 border-b border-zinc-800 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-red-500" />
                <h3 className="text-base font-serif font-semibold text-white">{editingGoalId ? 'Editar Meta' : 'Nova Meta de Orçamento'}</h3>
              </div>
              <button onClick={() => setIsGoalModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleSubmitGoal} className="p-6 space-y-4">
              {goalError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{goalError}</div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Ano *</label>
                  <input
                    type="number"
                    required
                    min={2000}
                    max={2100}
                    value={goalForm.year}
                    onChange={(e) => setGoalForm({ ...goalForm, year: Number(e.target.value) })}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Mês (opcional)</label>
                  <select
                    value={goalForm.month}
                    onChange={(e) => setGoalForm({ ...goalForm, month: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                  >
                    <option value="">Anual</option>
                    {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                      <option key={m} value={m}>Mês {m}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Categoria *</label>
                <input
                  type="text"
                  required
                  value={goalForm.category}
                  onChange={(e) => setGoalForm({ ...goalForm, category: e.target.value })}
                  placeholder="Ex: VENDAS, MATERIAL, MÃO DE OBRA"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Valor da Meta (R$) *</label>
                <input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={goalForm.target_value}
                  onChange={(e) => setGoalForm({ ...goalForm, target_value: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                />
              </div>
              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button type="button" onClick={() => setIsGoalModalOpen(false)} className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono">
                  Cancelar
                </button>
                <button type="submit" disabled={goalSaving} className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer disabled:opacity-50">
                  {goalSaving ? 'Salvando...' : editingGoalId ? 'Salvar Alterações' : 'Criar Meta'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Supplier Modal — cadastro rápido */}
      {isSupplierModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-sm rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 p-5 border-b border-zinc-800 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Truck className="w-5 h-5 text-red-500" />
                <h3 className="text-base font-serif font-semibold text-white">Novo Fornecedor</h3>
              </div>
              <button onClick={() => setIsSupplierModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateSupplier} className="p-6 space-y-4">
              {supplierError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{supplierError}</div>
              )}
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nome do Fornecedor *</label>
                <input
                  type="text"
                  required
                  value={newSupplierName}
                  onChange={(e) => setNewSupplierName(e.target.value)}
                  placeholder="Ex: Madeireira Sul"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                />
              </div>
              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button type="button" onClick={() => setIsSupplierModalOpen(false)} className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono">
                  Cancelar
                </button>
                <button type="submit" className="px-5 py-2 text-sm bg-emerald-700 hover:bg-emerald-600 text-white rounded font-semibold cursor-pointer">
                  Criar Fornecedor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bank Account Modal — nova/editar conta */}
      {bankModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="bg-zinc-950 p-6 border-b border-zinc-800 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-bold text-white">
                  {editingBankId ? 'Editar Conta Bancária' : 'Nova Conta Bancária'}
                </h3>
                <p className="text-xs text-zinc-400 font-mono">Cadastro de conta para vincular lançamentos.</p>
              </div>
              <button onClick={() => setBankModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmitBank} className="p-6 space-y-4 font-sans">
              {bankError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{bankError}</div>
              )}
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Nome da Conta *</label>
                <input type="text" required value={bankFormData.name} onChange={e => setBankFormData({ ...bankFormData, name: e.target.value })} placeholder="Ex: Conta Principal" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Banco</label>
                  <input type="text" value={bankFormData.bank} onChange={e => setBankFormData({ ...bankFormData, bank: e.target.value })} placeholder="Ex: Sicredi" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Tipo</label>
                  <select value={bankFormData.account_type} onChange={e => setBankFormData({ ...bankFormData, account_type: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono">
                    <option value="CORRENTE">CORRENTE</option>
                    <option value="POUPANCA">POUPANCA</option>
                    <option value="APLICACAO">APLICACAO</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Agência</label>
                  <input type="text" value={bankFormData.agency} onChange={e => setBankFormData({ ...bankFormData, agency: e.target.value })} placeholder="Ex: 1234" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Número da Conta</label>
                  <input type="text" value={bankFormData.account_number} onChange={e => setBankFormData({ ...bankFormData, account_number: e.target.value })} placeholder="Ex: 56789-0" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono" />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Saldo Inicial (R$)</label>
                  <input type="number" step="0.01" value={bankFormData.opening_balance} onChange={e => setBankFormData({ ...bankFormData, opening_balance: e.target.value })} placeholder="0" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data de Abertura</label>
                  <input type="date" value={bankFormData.opening_date} onChange={e => setBankFormData({ ...bankFormData, opening_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono" />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Alerta Saldo Baixo (R$)</label>
                <input type="number" step="0.01" value={bankFormData.low_balance_threshold} onChange={e => setBankFormData({ ...bankFormData, low_balance_threshold: e.target.value })} placeholder="Opcional" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono" />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Observações</label>
                <textarea value={bankFormData.notes} onChange={e => setBankFormData({ ...bankFormData, notes: e.target.value })} rows={2} placeholder="Opcional" className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 resize-none" />
              </div>
              <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                <input type="checkbox" checked={bankFormData.active} onChange={e => setBankFormData({ ...bankFormData, active: e.target.checked })} className="accent-red-600 w-4 h-4" />
                Conta ativa
              </label>
              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button type="button" onClick={() => setBankModalOpen(false)} className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono">Cancelar</button>
                <button type="submit" disabled={bankSaving} className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer disabled:opacity-50">{bankSaving ? 'Salvando...' : editingBankId ? 'Salvar Alterações' : 'Criar Conta'}</button>
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

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Documento</span>
                  <p className="text-zinc-300 text-sm mt-0.5">
                    {detailRecord.doc_number || '—'}{detailRecord.doc_type ? ' · ' + detailRecord.doc_type : ''}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Conta Bancária</span>
                  <p className="text-zinc-300 text-sm mt-0.5">{detailRecord.bank_account_name || detailRecord.bank || '—'}</p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Fornecedor</span>
                  <p className="text-zinc-300 text-sm mt-0.5">{detailRecord.supplier_name || '—'}</p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">Parcelas</span>
                  <p className="text-zinc-300 text-sm mt-0.5">{detailRecord.installments || 1}</p>
                </div>
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

function parseMoney(s: string): number {
  if (!s) return 0;
  const n = parseFloat(s.replace(/[^0-9,.-]/g, '').replace(/\./g, '').replace(',', '.'));
  return isNaN(n) ? 0 : n;
}

function CFBarChart({ data }: { data: ReportResult }) {
  const rows = data.rows as any[];
  const max = Math.max(1, ...rows.map(r => Math.max(parseMoney(r.income), parseMoney(r.outcome))));
  const W = 640;
  const H = 180;
  const pad = 22;
  const bw = (W - pad * 2) / rows.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Gráfico do fluxo de caixa mensal">
      {rows.map((r, i) => {
        const inc = parseMoney(r.income);
        const out = parseMoney(r.outcome);
        const hInc = (inc / max) * (H - pad * 2 - 18);
        const hOut = (out / max) * (H - pad * 2 - 18);
        const xc = pad + i * bw + bw / 2;
        return (
          <g key={r.month}>
            <title>{`${r.month}: entradas ${r.income}, saídas ${r.outcome}`}</title>
            <rect x={xc - 9} y={H - pad - hInc} width={11} height={hInc || 1} rx={2} fill="#34d399" />
            <rect x={xc + 2} y={H - pad - hOut} width={11} height={hOut || 1} rx={2} fill="#f87171" />
            <text x={xc} y={H - 6} textAnchor="middle" fontSize={8} fill="#71717a">
              {String(r.month).split(' - ')[0]}
            </text>
          </g>
        );
      })}
      <rect x={pad} y={pad} width={W - pad * 2} height={H - pad * 2 - 12} fill="none" stroke="#27272a" strokeWidth={1} rx={4} />
    </svg>
  );
}
