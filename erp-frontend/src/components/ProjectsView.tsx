import React, { useEffect, useState } from 'react';
import {
  BarChart, Layers, ListTodo, Plus, Search, Calendar, Landmark,
  Trash2, ArrowRight, ArrowLeft, CheckCircle, RefreshCw, Eye, Edit3, Edit2,
  Hammer, Clock, AlertTriangle, FileText, Paperclip, Download,
} from 'lucide-react';
import { projectService, clientService, funnelService, productionService, workerService, machineService, attachmentService, getApiErrorMessage } from '../services/api';
import { Project, Client, ProjectStatus, ProjectStep, ProjectEnvironment, Worker, Machine, TimeEntry, ProductionIssue, Attachment } from '../types';

interface ProjectsViewProps {
  userRole: string;
}

const COLUMNS_DEFAULTS: Array<{ id: ProjectStatus; label: string; color: string; desc: string }> = [
  { id: 'ORCAMENTO', label: 'Orçamento', color: 'border-t-zinc-700 bg-zinc-900/45', desc: 'Em discussão comercial' },
  { id: 'PROJETADO', label: 'Aprovado', color: 'border-t-amber-600 bg-amber-950/5', desc: 'Medição e detalhamento' },
  { id: 'PRODUCAO', label: 'Corte e Produção', color: 'border-t-red-700 bg-red-950/5', desc: 'Fabricação do móvel' },
  { id: 'MONTAGEM', label: 'Instalação', color: 'border-t-rose-500 bg-rose-950/5', desc: 'Montagem no cliente' },
  { id: 'CONCLUIDO', label: 'Concluído', color: 'border-t-emerald-600 bg-emerald-950/5', desc: 'Projeto finalizado' },
];

const ENV_TYPE_OPTIONS = ['COZINHA', 'QUARTO', 'SALA', 'PAINEL', 'ESCRITORIO', 'OUTRO'] as const;
const ENV_STATUS_OPTIONS = ['PLANEJADO', 'EM_PRODUCAO', 'CONCLUIDO'] as const;

function deadlineBadgeClasses(status: string): string {
  switch (status) {
    case 'VERMELHO': return 'bg-red-900 text-red-300 border border-red-800';
    case 'LARANJA': return 'bg-amber-900 text-amber-300 border border-amber-800';
    case 'VERDE': return 'bg-emerald-900 text-emerald-300 border border-emerald-700';
    case 'CONCLUIDO': return 'bg-zinc-700 text-zinc-300 border border-zinc-600';
    default: return 'bg-zinc-800 text-zinc-400 border border-zinc-700';
  }
}

function formatDateBR(d: string | null | undefined): string {
  if (!d) return 'S/D';
  try {
    const iso = d.substring(0, 10);
    const [y, m, day] = iso.split('-');
    if (!y || !m || !day) return d;
    return `${day}/${m}/${y}`;
  } catch { return d || 'S/D'; }
}

export default function ProjectsView({ userRole }: ProjectsViewProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectColumns, setProjectColumns] = useState<any[]>([]);
  const [editingCol, setEditingCol] = useState<string | null>(null);
  const [editingColLabel, setEditingColLabel] = useState('');
  const [editingColDesc, setEditingColDesc] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'deadline_asc' | 'deadline_desc' | 'client_az' | 'title_az' | 'value_desc' | 'value_asc'>('deadline_asc');
  const [viewMode, setViewMode] = useState<'KANBAN' | 'LIST'>('KANBAN');

  // Modal Control
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [isStepsModalOpen, setIsStepsModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeDetailTab, setActiveDetailTab] = useState<'GERAL' | 'AMBIENTES' | 'TEMPO' | 'OCORRENCIAS' | 'ARQUIVOS'>('GERAL');

  // Detail tab data
  const [environments, setEnvironments] = useState<ProjectEnvironment[]>([]);
  const [envLoading, setEnvLoading] = useState(false);
  const [envForm, setEnvForm] = useState<{ name: string; env_type: string; area_m2: string; value: string; status: string }>({ name: '', env_type: 'COZINHA', area_m2: '', value: '', status: 'PLANEJADO' });
  const [editingEnvId, setEditingEnvId] = useState<string | null>(null);
  const [envError, setEnvError] = useState('');
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [timeLoading, setTimeLoading] = useState(false);
  const [timeForm, setTimeForm] = useState<{ environment_id: string; worker_id: string; machine_id: string; hours: string; hours_type: string; work_date: string; notes: string }>({ environment_id: '', worker_id: '', machine_id: '', hours: '', hours_type: 'PRODUTIVA', work_date: new Date().toISOString().substring(0,10), notes: '' });
  const [timeError, setTimeError] = useState('');
  const [issues, setIssues] = useState<ProductionIssue[]>([]);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [issueForm, setIssueForm] = useState<{ kind: string; worker_id: string; material: string; quantity: string; hours_spent: string; cost: string; reason: string; issue_date: string; notes: string }>({ kind: 'RETRABALHO', worker_id: '', material: '', quantity: '', hours_spent: '', cost: '', reason: '', issue_date: new Date().toISOString().substring(0,10), notes: '' });
  const [issueError, setIssueError] = useState('');
  // Arquivos por projeto
  const [projectAttachments, setProjectAttachments] = useState<Attachment[]>([]);
  const [attLoading, setAttLoading] = useState(false);
  const [attError, setAttError] = useState('');
  const [attUploading, setAttUploading] = useState(false);

  // GERAL tab edit fields (when in detail modal)
  const [geralEdit, setGeralEdit] = useState<{ start_date: string; planned_end_date: string; actual_end_date: string }>({ start_date: '', planned_end_date: '', actual_end_date: '' });
  const [geralSaving, setGeralSaving] = useState(false);
  const [geralError, setGeralError] = useState('');

  // Form States for creation
  const [formData, setFormData] = useState({
    title: '',
    client_id: '',
    description: '',
    status: 'ORCAMENTO' as ProjectStatus,
    value: '',
    deadline: '',
    start_date: '',
    planned_end_date: '',
    actual_end_date: '',
  });

  const [submitError, setSubmitError] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [projs, cls] = await Promise.all([
        projectService.getAll(),
        clientService.getAll(),
      ]);
      setProjects(projs);
      setClients(cls);
    } catch (err) {
      console.error('Erro ao buscar dados de projetos:', err);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    loadData();
    loadProjectColumns();
  }, []);
  const loadProjectColumns = async () => {
    try {
      const cols = await funnelService.getAll('PROJECTS');
      if (cols && cols.length > 0) setProjectColumns(cols);
    } catch (err) {
      console.error('Erro ao carregar colunas:', err);
    }
  };

  const COLUMNS = COLUMNS_DEFAULTS.map(def => {
    const fromDB = projectColumns.find(c => c.column_key === def.id);
    return fromDB ? { ...def, label: fromDB.label, desc: fromDB.description || def.desc } : def;
  });

  const handleSaveCol = async (colId: string) => {
    try {
      await funnelService.update(colId, { label: editingColLabel, description: editingColDesc }, 'PROJECTS');
      setEditingCol(null);
      loadProjectColumns();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao salvar coluna.'));
    }
  };

  const handleOpenCreateModal = () => {
    setFormData({
      title: '',
      client_id: clients[0]?.id || '',
      description: '',
      status: 'ORCAMENTO',
      value: '',
      deadline: '',
      start_date: '',
      planned_end_date: '',
      actual_end_date: '',
    });
    setSubmitError('');
    setEditingProjectId(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (proj: Project) => {
    setEditingProjectId(proj.id);
    setFormData({
      title: proj.title,
      client_id: proj.client_id,
      description: proj.description,
      status: proj.status,
      value: String(proj.value),
      deadline: proj.deadline ? proj.deadline.substring(0, 10) : '',
      start_date: proj.start_date ? proj.start_date.substring(0, 10) : '',
      planned_end_date: proj.planned_end_date ? proj.planned_end_date.substring(0, 10) : '',
      actual_end_date: proj.actual_end_date ? proj.actual_end_date.substring(0, 10) : '',
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleSubmitProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    if (!formData.title || !formData.client_id || !formData.deadline) {
      setSubmitError('Título do projeto, cliente e prazo final são obrigatórios.');
      return;
    }

    try {
      const payload: any = {
        title: formData.title,
        client_id: formData.client_id,
        description: formData.description,
        status: formData.status,
        value: Number(formData.value) || 0,
        deadline: formData.deadline,
        start_date: formData.start_date || null,
        planned_end_date: formData.planned_end_date || null,
        actual_end_date: formData.actual_end_date || null,
      };
      if (editingProjectId) {
        await projectService.update(editingProjectId, payload);
      } else {
        const defaultSteps: ProjectStep[] = [
          { id: '1', label: 'Orçamento apresentado ao cliente', completed: false },
          { id: '2', label: 'Orçamento aprovado e confirmado', completed: false },
          { id: '3', label: 'Medição técnica e projetos prontos', completed: false },
          { id: '4', label: 'Aguardando materiais', completed: false },
          { id: '5', label: 'Corte e produção finalizados', completed: false },
          { id: '6', label: 'Montagem/Instalação concluída', completed: false },
        ];
        await projectService.create({ ...payload, steps: defaultSteps });
      }
      setIsModalOpen(false);
      setEditingProjectId(null);
      loadData();
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, editingProjectId ? 'Erro ao atualizar projeto.' : 'Erro ao registrar projeto.'));
    }
  };

  const shiftStatus = async (id: string, direction: 'LEFT' | 'RIGHT') => {
    const proj = projects.find(p => p.id === id);
    if (!proj) return;
    const currentIndex = COLUMNS.findIndex(col => col.id === proj.status);
    let nextIndex = currentIndex;
    if (direction === 'LEFT' && currentIndex > 0) nextIndex -= 1;
    else if (direction === 'RIGHT' && currentIndex < COLUMNS.length - 1) nextIndex += 1;
    if (nextIndex === currentIndex) return;
    const nextStatus = COLUMNS[nextIndex].id;
    try {
      setProjects(prev => prev.map(p => p.id === id ? { ...p, status: nextStatus } : p));
      await projectService.update(id, { status: nextStatus });
    } catch (err) {
      console.error('Falha ao redefinir status de produção:', err);
      alert(getApiErrorMessage(err, 'Falha ao atualizar status do projeto.'));
      loadData();
    }
  };

  const handleOpenSteps = (proj: Project) => {
    setSelectedProject(proj);
    setActiveDetailTab('GERAL');
    setGeralEdit({
      start_date: proj.start_date ? proj.start_date.substring(0, 10) : '',
      planned_end_date: proj.planned_end_date ? proj.planned_end_date.substring(0, 10) : '',
      actual_end_date: proj.actual_end_date ? proj.actual_end_date.substring(0, 10) : '',
    });
    setGeralError('');
    setIsStepsModalOpen(true);
    // preload detail data silently
    loadEnvironments(proj.id);
    loadTimeEntries(proj.id);
    loadIssues(proj.id);
    loadWorkersMachines();
  };

  // Sync geralEdit when selectedProject changes externally
  useEffect(() => {
    if (selectedProject && isStepsModalOpen && activeDetailTab === 'GERAL') {
      setGeralEdit({
        start_date: selectedProject.start_date ? selectedProject.start_date.substring(0, 10) : '',
        planned_end_date: selectedProject.planned_end_date ? selectedProject.planned_end_date.substring(0, 10) : '',
        actual_end_date: selectedProject.actual_end_date ? selectedProject.actual_end_date.substring(0, 10) : '',
      });
    }
  }, [selectedProject?.id]);

  const loadEnvironments = async (projectId: string) => {
    setEnvLoading(true);
    setEnvError('');
    try {
      const data = await productionService.getEnvironments(projectId);
      setEnvironments(data || []);
    } catch (err) {
      setEnvError(getApiErrorMessage(err, 'Erro ao carregar ambientes.'));
    } finally { setEnvLoading(false); }
  };
  const loadWorkersMachines = async () => {
    try {
      const [ws, ms] = await Promise.all([
        workerService.getAll().catch(() => [] as Worker[]),
        machineService.getAll().catch(() => [] as Machine[]),
      ]);
      setWorkers(ws);
      setMachines(ms);
    } catch { /* ignore */ }
  };
  const loadTimeEntries = async (projectId: string) => {
    setTimeLoading(true);
    try {
      const data = await productionService.getTime(projectId);
      setTimeEntries(data || []);
    } catch { setTimeEntries([]); }
    finally { setTimeLoading(false); }
  };
  const loadIssues = async (projectId: string) => {
    setIssuesLoading(true);
    try {
      const data = await productionService.getIssues(projectId);
      setIssues(data || []);
    } catch { setIssues([]); }
    finally { setIssuesLoading(false); }
  };
  const loadProjectAttachments = async (projectId: string) => {
    setAttLoading(true);
    setAttError('');
    try {
      const data = await attachmentService.getProjectAttachments(projectId);
      setProjectAttachments(data || []);
    } catch (err) {
      setAttError(getApiErrorMessage(err, 'Erro ao carregar arquivos.'));
    } finally { setAttLoading(false); }
  };
  const handleProjectFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedProject) return;
    setAttUploading(true);
    setAttError('');
    try {
      await attachmentService.uploadProjectAttachment(selectedProject.id, file);
      await loadProjectAttachments(selectedProject.id);
    } catch (err) {
      setAttError(getApiErrorMessage(err, 'Erro ao enviar arquivo.'));
    } finally {
      setAttUploading(false);
      e.target.value = '';
    }
  };
  const handleDownloadProjectAttachment = async (att: Attachment) => {
    try { await attachmentService.download(att.id); } catch (err) { setAttError(getApiErrorMessage(err, 'Erro ao baixar arquivo.')); }
  };
  const handleDeleteProjectAttachment = async (attId: string) => {
    if (!selectedProject) return;
    if (!confirm('Remover este arquivo?')) return;
    try {
      await attachmentService.remove(attId);
      await loadProjectAttachments(selectedProject.id);
    } catch (err) { setAttError(getApiErrorMessage(err, 'Erro ao remover arquivo.')); }
  };

  useEffect(() => {
    if (activeDetailTab === 'ARQUIVOS' && selectedProject) {
      loadProjectAttachments(selectedProject.id);
    }
  }, [activeDetailTab, selectedProject?.id]);
  const handleSaveGeralDates = async () => {
    if (!selectedProject) return;
    setGeralSaving(true);
    setGeralError('');
    try {
      const payload: any = {
        start_date: geralEdit.start_date || null,
        planned_end_date: geralEdit.planned_end_date || null,
        actual_end_date: geralEdit.actual_end_date || null,
      };
      const updated = await projectService.update(selectedProject.id, payload);
      setSelectedProject(prev => prev ? { ...prev, ...updated } : prev);
      setProjects(prev => prev.map(p => p.id === selectedProject.id ? { ...p, ...updated } : p));
    } catch (err) {
      setGeralError(getApiErrorMessage(err, 'Erro ao salvar datas.'));
    } finally { setGeralSaving(false); }
  };

  const handleCreateOrUpdateEnv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;
    if (!envForm.name.trim()) { setEnvError('Nome do ambiente é obrigatório.'); return; }
    setEnvError('');
    try {
      const payload: any = {
        name: envForm.name.trim(),
        env_type: envForm.env_type,
        area_m2: envForm.area_m2 ? Number(envForm.area_m2) : null,
        value: envForm.value ? Number(envForm.value) : null,
        status: envForm.status,
      };
      if (editingEnvId) {
        await productionService.updateEnvironment(editingEnvId, payload);
      } else {
        await productionService.createEnvironment(selectedProject.id, payload);
      }
      setEnvForm({ name: '', env_type: 'COZINHA', area_m2: '', value: '', status: 'PLANEJADO' });
      setEditingEnvId(null);
      await loadEnvironments(selectedProject.id);
      // refresh project totals
      const refreshed = await projectService.getById(selectedProject.id).catch(() => null);
      if (refreshed) {
        setSelectedProject(refreshed);
        setProjects(prev => prev.map(p => p.id === refreshed.id ? refreshed : p));
      }
    } catch (err) { setEnvError(getApiErrorMessage(err, 'Erro ao salvar ambiente.')); }
  };
  const handleEditEnv = (env: ProjectEnvironment) => {
    setEditingEnvId(env.id);
    setEnvForm({ name: env.name, env_type: env.env_type, area_m2: env.area_m2 != null ? String(env.area_m2) : '', value: env.value != null ? String(env.value) : '', status: env.status });
  };
  const handleDeleteEnv = async (id: string) => {
    if (!selectedProject) return;
    if (!confirm('Remover este ambiente?')) return;
    try {
      await productionService.deleteEnvironment(id);
      await loadEnvironments(selectedProject.id);
      const refreshed = await projectService.getById(selectedProject.id).catch(() => null);
      if (refreshed) {
        setSelectedProject(refreshed);
        setProjects(prev => prev.map(p => p.id === refreshed.id ? refreshed : p));
      }
    } catch (err) { alert(getApiErrorMessage(err, 'Erro ao remover ambiente.')); }
  };

  const handleCreateTime = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;
    if (!timeForm.hours || !timeForm.work_date) { setTimeError('Horas e data são obrigatórios.'); return; }
    setTimeError('');
    try {
      const payload: any = {
        environment_id: timeForm.environment_id || null,
        worker_id: timeForm.worker_id || null,
        machine_id: timeForm.machine_id || null,
        hours: Number(timeForm.hours),
        hours_type: timeForm.hours_type,
        work_date: timeForm.work_date,
        notes: timeForm.notes,
      };
      await productionService.createTime(selectedProject.id, payload);
      setTimeForm({ environment_id: '', worker_id: '', machine_id: '', hours: '', hours_type: 'PRODUTIVA', work_date: new Date().toISOString().substring(0,10), notes: '' });
      await loadTimeEntries(selectedProject.id);
    } catch (err) { setTimeError(getApiErrorMessage(err, 'Erro ao registrar apontamento.')); }
  };
  const handleDeleteTime = async (id: string) => {
    if (!selectedProject) return;
    if (!confirm('Remover apontamento?')) return;
    try { await productionService.deleteTime(id); await loadTimeEntries(selectedProject.id); } catch (err) { alert(getApiErrorMessage(err, 'Erro ao remover.')); }
  };

  const handleCreateIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;
    if (!issueForm.reason.trim()) { setIssueError('Motivo é obrigatório.'); return; }
    setIssueError('');
    try {
      const payload: any = {
        kind: issueForm.kind,
        worker_id: issueForm.worker_id || null,
        material: issueForm.material || '',
        quantity: issueForm.quantity ? Number(issueForm.quantity) : null,
        hours_spent: issueForm.hours_spent ? Number(issueForm.hours_spent) : null,
        cost: issueForm.cost ? Number(issueForm.cost) : null,
        reason: issueForm.reason,
        issue_date: issueForm.issue_date,
        notes: issueForm.notes,
      };
      await productionService.createIssue(selectedProject.id, payload);
      setIssueForm({ kind: 'RETRABALHO', worker_id: '', material: '', quantity: '', hours_spent: '', cost: '', reason: '', issue_date: new Date().toISOString().substring(0,10), notes: '' });
      await loadIssues(selectedProject.id);
    } catch (err) { setIssueError(getApiErrorMessage(err, 'Erro ao registrar ocorrência.')); }
  };
  const handleDeleteIssue = async (id: string) => {
    if (!selectedProject) return;
    if (!confirm('Remover ocorrência?')) return;
    try { await productionService.deleteIssue(id); await loadIssues(selectedProject.id); } catch (err) { alert(getApiErrorMessage(err, 'Erro ao remover.')); }
  };

  const toggleStepCheckbox = async (stepId: string) => {
    if (!selectedProject) return;
    const updatedSteps = selectedProject.steps.map(step =>
      step.id === stepId ? { ...step, completed: !step.completed } : step
    );
    const updatedProj = { ...selectedProject, steps: updatedSteps };
    setSelectedProject(updatedProj);
    try {
      setProjects(prev => prev.map(p => p.id === selectedProject.id ? updatedProj : p));
      await projectService.updateSteps(selectedProject.id, updatedSteps);
    } catch (err) {
      console.error('Erro ao salvar checklists de fábrica:', err);
      alert(getApiErrorMessage(err, 'Erro ao salvar checklist.'));
      loadData();
    }
  };

  const handleDeleteProj = async (id: string, title: string) => {
    if (userRole !== 'ADMIN') {
      alert('Apenas os administradores podem excluir projetos.');
      return;
    }
    if (confirm(`Remover definitivamente o projeto "${title}"?\nRegistros de faturamento e medição associados serão limpos.`)) {
      try {
        await projectService.delete(id);
        loadData();
      } catch (err) {
        console.error('Erro de exclusão:', err);
        alert(getApiErrorMessage(err, 'Erro ao remover projeto.'));
      }
    }
  };

  const filteredProjects = projects
    .filter(p =>
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.client_name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'deadline_asc': return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
        case 'deadline_desc': return new Date(b.deadline).getTime() - new Date(a.deadline).getTime();
        case 'client_az': return (a.client_name || '').localeCompare(b.client_name || '');
        case 'title_az': return a.title.localeCompare(b.title);
        case 'value_desc': return b.value - a.value;
        case 'value_asc': return a.value - b.value;
        default: return 0;
      }
    });

  const totalM2Ambientes = environments.reduce((acc, e) => acc + (Number(e.area_m2) || 0), 0);
  const totalValorAmbientes = environments.reduce((acc, e) => acc + (Number(e.value) || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header with Visual switcher */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Projetos & Kanban</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Acompanhamento da produção dos móveis.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="bg-zinc-900 border border-zinc-800 p-1 rounded-md flex">
            <button
              onClick={() => setViewMode('KANBAN')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all flex items-center gap-1 cursor-pointer ${viewMode === 'KANBAN' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'}`}
            >
              <Layers className="w-3.5 h-3.5" /> Funil
            </button>
            <button
              onClick={() => setViewMode('LIST')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all flex items-center gap-1 cursor-pointer ${viewMode === 'LIST' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'}`}
            >
              <ListTodo className="w-3.5 h-3.5" /> Lista Geral
            </button>
          </div>
          {['ADMIN', 'GERENTE'].includes(userRole) && (
            <button
              onClick={handleOpenCreateModal}
              className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded shadow-md flex items-center gap-1.5 transition active:scale-95 cursor-pointer font-sans h-[38px]"
            >
              <Plus className="w-4 h-4" /> Registrar Projeto
            </button>
          )}
        </div>
      </div>
      {/* Filter panel */}
      <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center">
        <div className="relative w-full md:flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Buscar projeto por título ou cliente..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-805 text-white pl-10 pr-4 py-2 text-sm rounded focus:outline-none focus:border-red-606 font-sans"
          />
        </div>
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as any)}
          className="bg-zinc-900 border border-zinc-805 text-zinc-300 font-mono text-xs rounded px-3 py-2 focus:outline-none cursor-pointer shrink-0"
        >
          <option value="deadline_asc">📅 Entrega (mais próxima)</option>
          <option value="deadline_desc">📅 Entrega (mais distante)</option>
          <option value="client_az">👤 Cliente (A-Z)</option>
          <option value="title_az">🔤 Título (A-Z)</option>
          <option value="value_desc">💰 Valor (maior)</option>
          <option value="value_asc">💰 Valor (menor)</option>
        </select>
        <div className="text-xs text-zinc-400 font-mono w-full md:w-auto text-right">
          Total: {filteredProjects.length} projetos em andamento
        </div>
      </div>
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando andamento fabril...</p>
        </div>
      ) : viewMode === 'KANBAN' ? (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 overflow-x-auto min-w-[950px] pb-4">
          {COLUMNS.map((col) => {
            const colProjects = filteredProjects.filter(p => p.status === col.id);
            const colValue = colProjects.reduce((acc, p) => acc + p.value, 0);
            return (
              <div
                key={col.id}
                className={`glass-panel rounded-xl flex flex-col min-h-[550px] overflow-hidden border-t-2 ${col.color}`}
              >
                <div className="p-4 bg-zinc-950/60 border-b border-zinc-900">
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      {editingCol === col.id ? (
                        <div className="space-y-1.5">
                          <input
                            type="text"
                            value={editingColLabel}
                            onChange={e => setEditingColLabel(e.target.value)}
                            className="w-full bg-zinc-950 border border-red-600 text-white rounded px-2 py-1 text-sm focus:outline-none"
                            autoFocus
                          />
                          <input
                            type="text"
                            value={editingColDesc}
                            onChange={e => setEditingColDesc(e.target.value)}
                            placeholder="Descrição (opcional)"
                            className="w-full bg-zinc-950 border border-zinc-700 text-zinc-400 rounded px-2 py-1 text-xs focus:outline-none"
                          />
                          <div className="flex gap-1.5 mt-1">
                            <button onClick={() => handleSaveCol(col.id)} className="text-[10px] font-mono text-emerald-400 hover:text-emerald-300 cursor-pointer">Salvar</button>
                            <button onClick={() => setEditingCol(null)} className="text-[10px] font-mono text-zinc-500 hover:text-white cursor-pointer">Cancelar</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-1.5">
                            <h3 className="text-sm font-sans font-bold text-white tracking-wide">{col.label}</h3>
                            {['ADMIN', 'GERENTE'].includes(userRole) && (
                              <button
                                onClick={() => { setEditingCol(col.id); setEditingColLabel(col.label); setEditingColDesc(col.desc); }}
                                className="p-0.5 text-zinc-600 hover:text-zinc-300 cursor-pointer"
                                title="Editar nome da coluna"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                          <p className="text-[10px] text-zinc-500 font-mono mt-0.5">{col.desc}</p>
                          {colValue > 0 && (
                            <p className="text-[11px] font-mono text-emerald-600 font-semibold mt-0.5">
                              {colValue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                            </p>
                          )}
                        </>
                      )}
                    </div>
                    <span className="text-xs font-bold font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 ml-2 shrink-0">
                      {colProjects.length}
                    </span>
                  </div>
                </div>
                <div className="p-3 space-y-3 flex-1 overflow-y-auto max-h-[500px]">
                  {colProjects.map((p) => {
                    const compSteps = p.steps.filter(s => s.completed).length;
                    const totSteps = p.steps.length;
                    const progressPct = totSteps > 0 ? Math.round((compSteps / totSteps) * 100) : 0;
                    const badge = p.deadline_status || 'VERDE';
                    return (
                      <div
                        key={p.id}
                        className="p-4 bg-zinc-950/70 hover:bg-zinc-900 border border-zinc-900 hover:border-red-800/40 rounded-lg group transition shadow-lg relative"
                      >
                        <div>
                          <h4 className="text-sm font-semibold text-zinc-100 line-clamp-2 leading-tight group-hover:text-white">
                            {p.title}
                          </h4>
                          <span className="text-[11px] text-zinc-400 font-sans block mt-1">
                            👤 {p.client_name}
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${deadlineBadgeClasses(badge)}`}>
                            {badge === 'VERMELHO' && <AlertTriangle className="w-3 h-3 mr-1" />}
                            {badge === 'LARANJA' && <Clock className="w-3 h-3 mr-1" />}
                            {badge === 'VERDE' && <CheckCircle className="w-3 h-3 mr-1" />}
                            {badge === 'CONCLUIDO' && <CheckCircle className="w-3 h-3 mr-1" />}
                            {badge}
                          </span>
                          {(p.total_environments != null || p.total_area_m2 != null) && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700">
                              <Hammer className="w-3 h-3 mr-1" />
                              {p.total_environments ?? 0} amb. {p.total_area_m2 != null ? `· ${Number(p.total_area_m2).toFixed(1)} m²` : ''}
                            </span>
                          )}
                        </div>
                        <div className="mt-3.5 flex justify-between items-center text-[10px] font-mono border-t border-zinc-900 pt-2.5">
                          <span className="text-emerald-400 font-bold">
                            {p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                          </span>
                          <span className="text-zinc-500">
                            📅 {p.deadline ? new Date(p.deadline).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : 'S/D'}
                          </span>
                        </div>
                        {(p.total_area_m2 != null || p.total_environments != null) && (
                          <div className="text-[10px] font-mono text-zinc-500 mt-1">
                            {p.total_environments ?? 0} ambientes{p.total_area_m2 != null ? ` - ${Number(p.total_area_m2).toFixed(1)} m²` : ''}
                          </div>
                        )}
                        <div className="mt-3 text-[10px] font-mono">
                          <div className="flex justify-between items-center text-zinc-500 mb-1">
                            <span>Projeto: {compSteps}/{totSteps}</span>
                            <span className="text-zinc-300 font-semibold">{progressPct}%</span>
                          </div>
                          <div className="w-full bg-zinc-900 h-1 rounded-full overflow-hidden">
                            <div className="bg-red-650 h-full" style={{ width: `${progressPct}%` }}></div>
                          </div>
                        </div>
                        <div className="mt-4 flex justify-between gap-1 border-t border-zinc-900 pt-3">
                          <div className="flex gap-1">
                            <button
                              onClick={() => shiftStatus(p.id, 'LEFT')}
                              disabled={p.status === 'ORCAMENTO'}
                              className="p-1 text-zinc-500 hover:text-white disabled:pointer-events-none disabled:opacity-20 cursor-pointer"
                              title="Recuar Fase"
                            >
                              <ArrowLeft className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => shiftStatus(p.id, 'RIGHT')}
                              disabled={p.status === 'CONCLUIDO'}
                              className="p-1 text-zinc-500 hover:text-white disabled:pointer-events-none disabled:opacity-20 cursor-pointer"
                              title="Avançar Fase"
                            >
                              <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          <div className="flex gap-1.5">
                            <button
                              onClick={() => handleOpenSteps(p)}
                              className="p-1 text-zinc-400 hover:text-red-500 flex items-center gap-0.5 text-[10px] font-mono py-0.5 px-1.5 bg-zinc-900 rounded border border-zinc-800 cursor-pointer"
                              title="Abrir detalhe"
                            >
                              <Eye className="w-3 h-3 text-red-600" /> Detalhe
                            </button>
                            {['ADMIN', 'GERENTE'].includes(userRole) && (
                              <button
                                onClick={() => handleOpenEditModal(p)}
                                className="p-1 text-zinc-600 hover:text-blue-400 cursor-pointer"
                                title="Editar projeto"
                              >
                                <Edit3 className="w-3 h-3" />
                              </button>
                            )}
                            {userRole === 'ADMIN' && (
                              <button
                                onClick={() => handleDeleteProj(p.id, p.title)}
                                className="p-1 text-zinc-600 hover:text-red-400 cursor-pointer"
                                title="Deletar"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {colProjects.length === 0 && (
                    <div className="py-12 border-2 border-dashed border-zinc-900 rounded-lg flex items-center justify-center">
                      <p className="text-[11px] text-zinc-600 font-mono">Vazio</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                <tr>
                  <th className="py-4 px-6 font-normal">Ambiente Comercial / Projeto</th>
                  <th className="py-4 px-6 font-normal">Cliente Associado</th>
                  <th className="py-4 px-6 font-normal">Status do Projeto</th>
                  <th className="py-4 px-6 font-normal">Prazo</th>
                  <th className="py-4 px-6 font-normal">Orçamento Valor</th>
                  <th className="py-4 px-6 font-normal">Ambientes / m²</th>
                  <th className="py-4 px-6 font-normal text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {filteredProjects.map((p) => (
                  <tr key={p.id} className="hover:bg-zinc-900/40">
                    <td className="py-4 px-6">
                      <div className="font-semibold text-white font-sans">{p.title}</div>
                      <span className="text-zinc-400 text-xs mt-0.5 block line-clamp-1">{p.description}</span>
                    </td>
                    <td className="py-4 px-6 text-zinc-300 font-sans">
                      {p.client_name}
                    </td>
                    <td className="py-4 px-6">
                      <span className="inline-block px-2.5 py-1 text-xs font-mono font-semibold text-red-400 bg-red-950/40 border border-red-900/40 rounded">
                        {p.status}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-mono font-semibold ${deadlineBadgeClasses(p.deadline_status || 'VERDE')}`}>
                        {p.deadline_status || 'VERDE'}
                      </span>
                      <span className="block text-xs font-mono text-zinc-500 mt-1">{p.deadline ? new Date(p.deadline).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : 'S/D'}</span>
                    </td>
                    <td className="py-4 px-6 font-mono font-bold text-emerald-400 text-sm">
                      {p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </td>
                    <td className="py-4 px-6 font-mono text-xs text-zinc-400">
                      {p.total_environments != null ? `${p.total_environments} amb.` : '-'} {p.total_area_m2 != null ? `· ${Number(p.total_area_m2).toFixed(1)} m²` : ''}
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => handleOpenSteps(p)}
                          className="p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 transition cursor-pointer"
                          title="Detalhe"
                        >
                          <Eye className="w-3.5 h-3.5 text-red-600" />
                        </button>
                        {['ADMIN', 'GERENTE'].includes(userRole) && (
                          <button
                            onClick={() => handleOpenEditModal(p)}
                            className="p-2 bg-zinc-900 hover:bg-blue-950/40 text-zinc-400 hover:text-blue-400 rounded border border-zinc-800 transition cursor-pointer"
                            title="Editar projeto"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {userRole === 'ADMIN' && (
                          <button
                            onClick={() => handleDeleteProj(p.id, p.title)}
                            className="p-2 bg-zinc-900 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-800 transition cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {/* Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="bg-zinc-950/80 p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h3 className="text-lg font-serif font-semibold text-white">{editingProjectId ? 'Editar Projeto' : 'Registrar Novo Projeto'}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-1">Gestão completa dos projetos da marcenaria</p>
              </div>
              <button
                onClick={() => { setIsModalOpen(false); setEditingProjectId(null); }}
                className="text-zinc-500 hover:text-white transition font-mono text-xs uppercase cursor-pointer"
              >
                Sair
              </button>
            </div>
            <form onSubmit={handleSubmitProject} className="p-7 space-y-6 font-sans overflow-y-auto">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Título do Projeto *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Ex: Cozinha Planejada MDF Freijó e Laca"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2 font-sans">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Cliente da Carteira *</label>
                  <select
                    value={formData.client_id}
                    onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="">-- Selecione o Cliente --</option>
                    {clients.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Status Inicial</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as ProjectStatus })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  >
                    {COLUMNS.map(col => (
                      <option key={col.id} value={col.id}>{col.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Valor Total Orçado (R$) *</label>
                  <input
                    type="number"
                    required
                    value={formData.value}
                    onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                    placeholder="35000"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Prazo Fim Limite</label>
                  <input
                    type="date"
                    required
                    value={formData.deadline}
                    onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Início</label>
                  <input type="date" value={formData.start_date} onChange={e => setFormData({ ...formData, start_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2.5 text-sm focus:outline-none font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Prev. Término</label>
                  <input type="date" value={formData.planned_end_date} onChange={e => setFormData({ ...formData, planned_end_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2.5 text-sm focus:outline-none font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Conclusão Real</label>
                  <input type="date" value={formData.actual_end_date} onChange={e => setFormData({ ...formData, actual_end_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2.5 text-sm focus:outline-none font-mono" />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Observações do Projeto</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Materiais específicos, chapas de MDF, ferragens comandadas, etc."
                  rows={3}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 leading-relaxed"
                />
              </div>
              <div className="pt-5 flex justify-end gap-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => { setIsModalOpen(false); setEditingProjectId(null); }}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 rounded border border-zinc-850 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer"
                >
                  {editingProjectId ? 'Salvar Alterações' : 'Registrar Projeto'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Detail Modal with tabs GERAL / AMBIENTES / TEMPO / OCORRENCIAS */}
      {isStepsModalOpen && selectedProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-2xl rounded-xl overflow-hidden border border-zinc-800 shadow-2xl flex flex-col max-h-[92vh]">
            <div className="bg-zinc-950 p-5 border-b border-zinc-800/80 flex justify-between items-center shrink-0">
              <div className="min-w-0">
                <h3 className="text-base font-serif font-bold text-white line-clamp-1">{selectedProject.title}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-0.5">{selectedProject.client_name} · {selectedProject.status} · <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-mono ${deadlineBadgeClasses(selectedProject.deadline_status || 'VERDE')}`}>{selectedProject.deadline_status || 'VERDE'}</span></p>
              </div>
              <button
                onClick={() => setIsStepsModalOpen(false)}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase cursor-pointer ml-4 shrink-0"
              >
                Sair
              </button>
            </div>
            {/* Tabs */}
            <div className="flex gap-1 p-2 bg-zinc-950/60 border-b border-zinc-900 shrink-0 overflow-x-auto">
              {(['GERAL','AMBIENTES','TEMPO','OCORRENCIAS','ARQUIVOS'] as const).map(tab => {
                const icons: Record<string, any> = { GERAL: Layers, AMBIENTES: Hammer, TEMPO: Clock, OCORRENCIAS: AlertTriangle, ARQUIVOS: FileText };
                const Icon = icons[tab];
                return (
                  <button key={tab} onClick={() => setActiveDetailTab(tab)} className={`flex items-center gap-1.5 px-3 py-2 rounded text-xs font-mono uppercase tracking-wider cursor-pointer whitespace-nowrap ${activeDetailTab===tab ? 'bg-red-600 text-white' : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'}`}>
                    <Icon className="w-3.5 h-3.5" /> {tab}
                  </button>
                );
              })}
            </div>
            <div className="overflow-y-auto flex-1 p-6 space-y-5">
              {activeDetailTab === 'GERAL' && (
                <div className="space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] text-zinc-400 font-mono uppercase block">Início</label>
                      <input type="date" value={geralEdit.start_date} onChange={e => setGeralEdit({ ...geralEdit, start_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] text-zinc-400 font-mono uppercase block">Prev. Término</label>
                      <input type="date" value={geralEdit.planned_end_date} onChange={e => setGeralEdit({ ...geralEdit, planned_end_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] text-zinc-400 font-mono uppercase block">Conclusão Real</label>
                      <input type="date" value={geralEdit.actual_end_date} onChange={e => setGeralEdit({ ...geralEdit, actual_end_date: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                    </div>
                  </div>
                  {geralError && <div className="p-2 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{geralError}</div>}
                  <div className="flex gap-2">
                    <button onClick={handleSaveGeralDates} disabled={geralSaving} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-mono rounded cursor-pointer disabled:opacity-60">{geralSaving ? 'Salvando...' : 'Salvar datas'}</button>
                    <span className="text-[11px] text-zinc-500 font-mono self-center">Prazo base: {formatDateBR(selectedProject.deadline)} · Status prazo: <span className={`px-1.5 py-0.5 rounded ${deadlineBadgeClasses(selectedProject.deadline_status || 'VERDE')}`}>{selectedProject.deadline_status || 'VERDE'}</span></span>
                  </div>

                  <div className="bg-zinc-900/40 p-3 rounded border border-zinc-800 text-xs font-mono text-zinc-400 space-y-1">
                    <div>Valor: <span className="text-emerald-400 font-bold">{Number(selectedProject.value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span></div>
                    <div>Ambientes: {selectedProject.total_environments ?? (selectedProject.environments?.length ?? environments.length)} · Área total: {selectedProject.total_area_m2 != null ? Number(selectedProject.total_area_m2).toFixed(2) + ' m²' : (totalM2Ambientes ? totalM2Ambientes.toFixed(2)+' m²' : '-')}</div>
                    <div className="text-zinc-500 line-clamp-3">{selectedProject.description || 'Sem observações.'}</div>
                  </div>

                  <div className="text-xs text-zinc-400 font-mono mb-1 bg-zinc-900/40 p-3 rounded border border-zinc-850">
                    Checklist operacional — marque apenas as etapas já concluídas.
                  </div>
                  <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                    {selectedProject.steps.map((step) => (
                      <label
                        key={step.id}
                        className="flex items-center gap-3 p-3 bg-zinc-900/60 hover:bg-zinc-900 border border-zinc-850/60 rounded cursor-pointer transition select-none"
                      >
                        <input
                          type="checkbox"
                          checked={step.completed}
                          onChange={() => toggleStepCheckbox(step.id)}
                          className="w-4.5 h-4.5 text-red-600 bg-zinc-950 border-zinc-800 rounded focus:ring-opacity-0 focus:outline-none focus:ring-0 checked:bg-red-600 cursor-pointer accent-red-600"
                        />
                        <span className={`text-sm font-sans font-medium transition ${step.completed ? 'text-zinc-500 line-through' : 'text-zinc-200'}`}>
                          {step.label}
                        </span>
                      </label>
                    ))}
                    {selectedProject.steps.length === 0 && (
                      <p className="text-zinc-500 font-mono text-xs text-center py-4">Nenhuma etapa cadastrada no cronograma.</p>
                    )}
                  </div>
                </div>
              )}

              {activeDetailTab === 'AMBIENTES' && (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-3 text-xs font-mono">
                    <span className="px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">{environments.length} ambientes</span>
                    <span className="px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">{totalM2Ambientes.toFixed(2)} m² totais</span>
                    <span className="px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-emerald-400">{totalValorAmbientes.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>
                  </div>
                  {envError && <div className="p-2 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{envError}</div>}
                  <form onSubmit={handleCreateOrUpdateEnv} className="glass-panel p-4 rounded-lg border border-zinc-800 space-y-3">
                    <div className="text-xs font-mono uppercase text-zinc-400 tracking-wider flex items-center gap-2"><Hammer className="w-3.5 h-3.5" /> {editingEnvId ? 'Editar ambiente' : 'Novo ambiente'}</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Nome *</label>
                        <input type="text" value={envForm.name} onChange={e => setEnvForm({ ...envForm, name: e.target.value })} placeholder="Ex: Cozinha planejada" className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Tipo</label>
                        <select value={envForm.env_type} onChange={e => setEnvForm({ ...envForm, env_type: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none cursor-pointer">
                          {ENV_TYPE_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Área (m²)</label>
                        <input type="number" step="0.01" value={envForm.area_m2} onChange={e => setEnvForm({ ...envForm, area_m2: e.target.value })} placeholder="12.5" className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Valor (R$)</label>
                        <input type="number" step="0.01" value={envForm.value} onChange={e => setEnvForm({ ...envForm, value: e.target.value })} placeholder="8500" className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Status</label>
                        <select value={envForm.status} onChange={e => setEnvForm({ ...envForm, status: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none cursor-pointer">
                          {ENV_STATUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button type="submit" className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-mono rounded cursor-pointer flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> {editingEnvId ? 'Salvar' : 'Adicionar'}</button>
                      {editingEnvId && <button type="button" onClick={() => { setEditingEnvId(null); setEnvForm({ name: '', env_type: 'COZINHA', area_m2: '', value: '', status: 'PLANEJADO' }); setEnvError(''); }} className="px-3 py-2 bg-zinc-800 text-zinc-300 text-xs font-mono rounded cursor-pointer">Cancelar</button>}
                    </div>
                  </form>

                  {envLoading ? <p className="text-xs font-mono text-zinc-500">Carregando ambientes...</p> : (
                    <div className="space-y-2">
                      {environments.length === 0 && <p className="text-xs font-mono text-zinc-500 text-center py-6 border border-dashed border-zinc-800 rounded">Nenhum ambiente cadastrado.</p>}
                      {environments.map(env => (
                        <div key={env.id} className="p-3 bg-zinc-900/60 border border-zinc-800 rounded flex justify-between items-center">
                          <div>
                            <div className="text-sm font-semibold text-white font-sans">{env.name}</div>
                            <div className="text-[11px] font-mono text-zinc-400 mt-0.5">{env.env_type} · {env.area_m2 != null ? Number(env.area_m2).toFixed(2)+' m²' : '-'} · {env.value != null ? Number(env.value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'}) : '-'}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded text-[10px] font-mono border ${env.status==='CONCLUIDO' ? 'bg-emerald-900 text-emerald-300 border-emerald-800' : env.status==='EM_PRODUCAO' ? 'bg-amber-900 text-amber-300 border-amber-800' : 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>{env.status}</span>
                            <button onClick={() => handleEditEnv(env)} className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded cursor-pointer"><Edit3 className="w-3.5 h-3.5" /></button>
                            <button onClick={() => handleDeleteEnv(env.id)} className="p-1.5 bg-zinc-800 hover:bg-red-950 text-zinc-400 hover:text-red-400 rounded cursor-pointer"><Trash2 className="w-3.5 h-3.5" /></button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeDetailTab === 'TEMPO' && (
                <div className="space-y-4">
                  {timeError && <div className="p-2 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{timeError}</div>}
                  <form onSubmit={handleCreateTime} className="glass-panel p-4 rounded-lg border border-zinc-800 space-y-3">
                    <div className="text-xs font-mono uppercase text-zinc-400 tracking-wider flex items-center gap-2"><Clock className="w-3.5 h-3.5" /> Novo apontamento</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Ambiente</label>
                        <select value={timeForm.environment_id} onChange={e => setTimeForm({ ...timeForm, environment_id: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono cursor-pointer">
                          <option value="">— Sem ambiente —</option>
                          {environments.map(ev => <option key={ev.id} value={ev.id}>{ev.name}</option>)}
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Funcionário</label>
                        <select value={timeForm.worker_id} onChange={e => setTimeForm({ ...timeForm, worker_id: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono cursor-pointer">
                          <option value="">— Sem funcionário —</option>
                          {workers.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Máquina</label>
                        <select value={timeForm.machine_id} onChange={e => setTimeForm({ ...timeForm, machine_id: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono cursor-pointer">
                          <option value="">— Sem máquina —</option>
                          {machines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Tipo</label>
                        <select value={timeForm.hours_type} onChange={e => setTimeForm({ ...timeForm, hours_type: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono cursor-pointer">
                          <option value="PRODUTIVA">PRODUTIVA</option>
                          <option value="IMPRODUTIVA">IMPRODUTIVA</option>
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Horas *</label>
                        <input type="number" step="0.01" value={timeForm.hours} onChange={e => setTimeForm({ ...timeForm, hours: e.target.value })} placeholder="8" className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Data *</label>
                        <input type="date" value={timeForm.work_date} onChange={e => setTimeForm({ ...timeForm, work_date: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono" />
                      </div>
                      <div className="sm:col-span-2 space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Observações</label>
                        <input type="text" value={timeForm.notes} onChange={e => setTimeForm({ ...timeForm, notes: e.target.value })} placeholder="Detalhe do serviço" className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs" />
                      </div>
                    </div>
                    <button type="submit" className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-mono rounded cursor-pointer flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Adicionar apontamento</button>
                  </form>
                  {timeLoading ? <p className="text-xs font-mono text-zinc-500">Carregando apontamentos...</p> : (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                      {timeEntries.length===0 && <p className="text-xs font-mono text-zinc-500 text-center py-6 border border-dashed border-zinc-800 rounded">Nenhum apontamento.</p>}
                      {timeEntries.map(te => (
                        <div key={te.id} className="p-3 bg-zinc-900/60 border border-zinc-800 rounded flex justify-between items-start">
                          <div className="text-xs font-mono">
                            <div className="font-semibold text-white">{Number(te.hours).toFixed(2)}h · {te.hours_type} · {formatDateBR(te.work_date)}</div>
                            <div className="text-zinc-400 mt-0.5">{te.worker_name || '—'} {te.machine_name ? `· máquina ${te.machine_name}` : ''} {te.environment_name ? `· ${te.environment_name}` : ''}</div>
                            {te.notes && <div className="text-zinc-500 mt-1">{te.notes}</div>}
                          </div>
                          <button onClick={() => handleDeleteTime(te.id)} className="p-1.5 bg-zinc-800 hover:bg-red-950 text-zinc-400 hover:text-red-400 rounded cursor-pointer shrink-0"><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeDetailTab === 'OCORRENCIAS' && (
                <div className="space-y-4">
                  {issueError && <div className="p-2 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{issueError}</div>}
                  <form onSubmit={handleCreateIssue} className="glass-panel p-4 rounded-lg border border-zinc-800 space-y-3">
                    <div className="text-xs font-mono uppercase text-zinc-400 tracking-wider flex items-center gap-2"><AlertTriangle className="w-3.5 h-3.5" /> Nova ocorrência</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Tipo</label>
                        <select value={issueForm.kind} onChange={e => setIssueForm({ ...issueForm, kind: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono cursor-pointer">
                          <option value="RETRABALHO">RETRABALHO</option>
                          <option value="DESPERDICIO">DESPERDÍCIO</option>
                          <option value="PERDA">PERDA</option>
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Funcionário</label>
                        <select value={issueForm.worker_id} onChange={e => setIssueForm({ ...issueForm, worker_id: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono cursor-pointer">
                          <option value="">—</option>
                          {workers.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Material</label>
                        <input type="text" value={issueForm.material} onChange={e => setIssueForm({ ...issueForm, material: e.target.value })} placeholder="MDF, ferragem ..." className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Quantidade</label>
                        <input type="number" step="0.01" value={issueForm.quantity} onChange={e => setIssueForm({ ...issueForm, quantity: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Horas gastas</label>
                        <input type="number" step="0.01" value={issueForm.hours_spent} onChange={e => setIssueForm({ ...issueForm, hours_spent: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Custo (R$)</label>
                        <input type="number" step="0.01" value={issueForm.cost} onChange={e => setIssueForm({ ...issueForm, cost: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Data</label>
                        <input type="date" value={issueForm.issue_date} onChange={e => setIssueForm({ ...issueForm, issue_date: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs font-mono" />
                      </div>
                      <div className="space-y-1.5 sm:col-span-2">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Motivo *</label>
                        <input type="text" value={issueForm.reason} onChange={e => setIssueForm({ ...issueForm, reason: e.target.value })} placeholder="Descreva o motivo" className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs" />
                      </div>
                      <div className="space-y-1.5 sm:col-span-2">
                        <label className="text-[10px] text-zinc-400 font-mono uppercase">Observações</label>
                        <input type="text" value={issueForm.notes} onChange={e => setIssueForm({ ...issueForm, notes: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 text-white rounded px-3 py-2 text-xs" />
                      </div>
                    </div>
                    <button type="submit" className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-mono rounded cursor-pointer flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Adicionar ocorrência</button>
                  </form>
                  {issuesLoading ? <p className="text-xs font-mono text-zinc-500">Carregando ocorrências...</p> : (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                      {issues.length===0 && <p className="text-xs font-mono text-zinc-500 text-center py-6 border border-dashed border-zinc-800 rounded">Nenhuma ocorrência.</p>}
                      {issues.map(is => (
                        <div key={is.id} className="p-3 bg-zinc-900/60 border border-zinc-800 rounded flex justify-between items-start">
                          <div className="text-xs font-mono">
                            <div className="font-semibold text-white flex gap-2 items-center"><span className={`px-1.5 py-0.5 rounded text-[10px] border ${is.kind==='RETRABALHO' ? 'bg-amber-900 text-amber-300 border-amber-800' : is.kind==='PERDA' ? 'bg-red-900 text-red-300 border-red-800' : 'bg-zinc-800 text-zinc-300 border-zinc-700'}`}>{is.kind}</span> {formatDateBR(is.issue_date)} · {is.material || '-'}</div>
                            <div className="text-zinc-400 mt-1">{is.reason}</div>
                            <div className="text-zinc-500 mt-0.5 flex gap-3 flex-wrap">{is.quantity!=null ? `Qtd: ${is.quantity}` : ''} {is.hours_spent!=null ? `Horas: ${is.hours_spent}` : ''} {is.cost!=null ? `Custo: ${Number(is.cost).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}` : ''} {is.worker_name ? `· ${is.worker_name}` : ''}</div>
                          </div>
                          <button onClick={() => handleDeleteIssue(is.id)} className="p-1.5 bg-zinc-800 hover:bg-red-950 text-zinc-400 hover:text-red-400 rounded cursor-pointer shrink-0"><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {activeDetailTab === 'ARQUIVOS' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-mono uppercase text-zinc-400 tracking-wider flex items-center gap-2"><Paperclip className="w-3.5 h-3.5" /> Arquivos do projeto</div>
                    <label className={`px-4 py-2 rounded text-xs font-mono cursor-pointer flex items-center gap-1.5 ${attUploading ? 'bg-zinc-800 text-zinc-400' : 'bg-red-600 hover:bg-red-700 text-white'}`}>
                      <Paperclip className="w-3.5 h-3.5" /> {attUploading ? 'Enviando...' : 'Upload'}
                      <input type="file" className="hidden" onChange={handleProjectFileChange} disabled={attUploading} />
                    </label>
                  </div>
                  {attError && <div className="p-2 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{attError}</div>}
                  {attLoading ? <p className="text-xs font-mono text-zinc-500">Carregando arquivos...</p> : (
                    <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                      {projectAttachments.length === 0 && <p className="text-xs font-mono text-zinc-500 text-center py-8 border border-dashed border-zinc-800 rounded glass-panel">Nenhum arquivo anexado a este projeto.</p>}
                      {projectAttachments.map(att => (
                        <div key={att.id} className="p-3 bg-zinc-900/60 border border-zinc-800 rounded flex justify-between items-center glass-panel">
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-semibold text-white font-sans flex items-center gap-2 truncate"><FileText className="w-4 h-4 text-zinc-400 shrink-0" /> <span className="truncate">{att.filename}</span></div>
                            <div className="text-[11px] font-mono text-zinc-500 mt-0.5">{att.created_at ? new Date(att.created_at).toLocaleString('pt-BR') : '-'} {att.created_by ? `· ${att.created_by}` : ''} {att.size ? `· ${(att.size/1024).toFixed(1)} KB` : ''}</div>
                          </div>
                          <div className="flex items-center gap-1.5 ml-3 shrink-0">
                            <button onClick={() => handleDownloadProjectAttachment(att)} className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded cursor-pointer" title="Download"><Download className="w-3.5 h-3.5" /></button>
                            <button onClick={() => handleDeleteProjectAttachment(att.id)} className="p-1.5 bg-zinc-800 hover:bg-red-950 text-zinc-400 hover:text-red-400 rounded cursor-pointer" title="Remover"><Trash2 className="w-3.5 h-3.5" /></button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-zinc-800 flex justify-end shrink-0">
              <button
                onClick={() => setIsStepsModalOpen(false)}
                className="px-5 py-2 text-xs font-mono uppercase bg-zinc-900 hover:bg-zinc-800 text-white border border-zinc-800 rounded transition cursor-pointer"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
