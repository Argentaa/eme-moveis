import React, { useEffect, useState } from 'react';
import { 
  BarChart, Layers, ListTodo, Plus, Search, Calendar, Landmark, 
  Trash2, ArrowRight, ArrowLeft, CheckCircle, RefreshCw, Eye, Edit3, Edit2
} from 'lucide-react';
import { projectService, clientService, funnelService, getApiErrorMessage } from '../services/api';
import { Project, Client, ProjectStatus, ProjectStep } from '../types';

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

  // Form States for creation
  const [formData, setFormData] = useState({
    title: '',
    client_id: '',
    description: '',
    status: 'ORCAMENTO' as ProjectStatus,
    value: '',
    deadline: '',
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
    });
    setSubmitError('');
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
      deadline: proj.deadline.substring(0, 10),
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
      const payload = {
        title: formData.title,
        client_id: formData.client_id,
        description: formData.description,
        status: formData.status,
        value: Number(formData.value) || 0,
        deadline: formData.deadline,
      };

      if (editingProjectId) {
        await projectService.update(editingProjectId, payload);
      } else {
        // Setup initial factory checklist apenas para projetos novos
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

    if (direction === 'LEFT' && currentIndex > 0) {
      nextIndex -= 1;
    } else if (direction === 'RIGHT' && currentIndex < COLUMNS.length - 1) {
      nextIndex += 1;
    }

    if (nextIndex === currentIndex) return;

    const nextStatus = COLUMNS[nextIndex].id;

    try {
      // Optimistic Update
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
    setIsStepsModalOpen(true);
  };

  const toggleStepCheckbox = async (stepId: string) => {
    if (!selectedProject) return;

    const updatedSteps = selectedProject.steps.map(step => 
      step.id === stepId ? { ...step, completed: !step.completed } : step
    );

    // If all steps completed, automatically move status to CONCLUIDO maybe?
    // Let's keep it manual or update local model state
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

  return (
    <div className="space-y-6">
      
      {/* Header with Visual switcher */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Projetos & Kanban</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Acompanhamento da produção dos móveis.</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode switcher */}
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
        
        /* KANBAN BOARD SYSTEM */
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 overflow-x-auto min-w-[950px] pb-4">
          {COLUMNS.map((col) => {
            const colProjects = filteredProjects.filter(p => p.status === col.id);
            const colValue = colProjects.reduce((acc, p) => acc + p.value, 0);

            return (
              <div 
                key={col.id} 
                className={`glass-panel rounded-xl flex flex-col min-h-[550px] overflow-hidden border-t-2 ${col.color}`}
              >
                {/* Visual Header */}
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

                {/* Cards Container */}
                <div className="p-3 space-y-3 flex-1 overflow-y-auto max-h-[500px]">
                  {colProjects.map((p) => {
                    const compSteps = p.steps.filter(s => s.completed).length;
                    const totSteps = p.steps.length;
                    const progressPct = totSteps > 0 ? Math.round((compSteps / totSteps) * 100) : 0;

                    return (
                      <div 
                        key={p.id}
                        className="p-4 bg-zinc-950/70 hover:bg-zinc-900 border border-zinc-900 hover:border-red-800/40 rounded-lg group transition shadow-lg relative"
                      >
                        {/* Title & Customer */}
                        <div>
                          <h4 className="text-sm font-semibold text-zinc-100 line-clamp-2 leading-tight group-hover:text-white">
                            {p.title}
                          </h4>
                          <span className="text-[11px] text-zinc-400 font-sans block mt-1">
                            👤 {p.client_name}
                          </span>
                        </div>

                        {/* Money & Deadline Badge */}
                        <div className="mt-3.5 flex justify-between items-center text-[10px] font-mono border-t border-zinc-900 pt-2.5">
                          <span className="text-emerald-400 font-bold">
                            {p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
                          </span>
                          <span className="text-zinc-500">
                            📅 {p.deadline ? new Date(p.deadline).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : 'S/D'}
                          </span>
                        </div>

                        {/* Steps checklist completion bar */}
                        <div className="mt-3 text-[10px] font-mono">
                          <div className="flex justify-between items-center text-zinc-500 mb-1">
                            <span>Projeto: {compSteps}/{totSteps}</span>
                            <span className="text-zinc-300 font-semibold">{progressPct}%</span>
                          </div>
                          <div className="w-full bg-zinc-900 h-1 rounded-full overflow-hidden">
                            <div className="bg-red-650 h-full" style={{ width: `${progressPct}%` }}></div>
                          </div>
                        </div>

                        {/* Interactive Sliders */}
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
                              title="Abrir checklist de fábrica"
                            >
                              <ListTodo className="w-3 h-3 text-red-600" /> Checklist
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
        
        /* TABLE LIST VIEW SYSTEM */
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                <tr>
                  <th className="py-4 px-6 font-normal">Ambiente Comercial / Projeto</th>
                  <th className="py-4 px-6 font-normal">Cliente Associado</th>
                  <th className="py-4 px-6 font-normal">Status do Projeto</th>
                  <th className="py-4 px-6 font-normal">Orçamento Valor</th>
                  <th className="py-4 px-6 font-normal">Entrega Limite</th>
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
                    <td className="py-4 px-6 font-mono font-bold text-emerald-400 text-sm">
                      {p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </td>
                    <td className="py-4 px-6 font-mono text-xs text-zinc-400">
                      {p.deadline ? new Date(p.deadline).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : 'S/D'}
                    </td>
                    <td className="py-4 px-6 text-right space-x-2 shrink-0">
                      <button 
                        onClick={() => handleOpenSteps(p)}
                        className="p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 transition cursor-pointer"
                        title="Checar Etapas"
                      >
                        <ListTodo className="w-3.5 h-3.5 text-red-600" />
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
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950/80 p-6 border-b border-zinc-800 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-semibold text-white">{editingProjectId ? 'Editar Projeto' : 'Registrar Novo Projeto'}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-1">Gestão completa dos projetos da marcenaria</p>
              </div>
              <button 
                onClick={() => { setIsModalOpen(false); setEditingProjectId(null); }}
                className="text-zinc-500 hover:text-white transition font-mono text-xs uppercase"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleSubmitProject} className="p-7 space-y-6 font-sans">
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

      {/* Production Checklist Status Steps Detail Modal */}
      {isStepsModalOpen && selectedProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950 p-5 border-b border-zinc-800/80 flex justify-between items-center">
              <div>
                <h3 className="text-base font-serif font-bold text-white line-clamp-1">{selectedProject.title}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-0.5">Checklist operacional de fabricação</p>
              </div>
              <button 
                onClick={() => setIsStepsModalOpen(false)}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase"
              >
                Sair
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="text-xs text-zinc-400 font-mono mb-2 bg-zinc-900/40 p-3 rounded rounded-lg border border-zinc-850">
                Controle de andamento do projeto. Marque apenas as etapas já concluídas.
              </div>

              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
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

              <div className="pt-4 border-t border-zinc-800 mt-6 flex justify-end">
                <button 
                  onClick={() => setIsStepsModalOpen(false)}
                  className="px-5 py-2 text-xs font-mono uppercase bg-red-800 hover:bg-red-900 text-white font-semibold rounded transition"
                >
                  ✓ Concluir Consulta
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
