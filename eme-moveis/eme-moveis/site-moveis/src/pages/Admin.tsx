import React, { useState, useEffect } from 'react';
import { 
  Lock, User, LogOut, Plus, Edit2, Trash2, Folder, 
  Clock, Image as ImageIcon, Upload, X, ArrowLeft, CheckCircle2, AlertTriangle, Filter
} from 'lucide-react';

interface Project {
  id?: number;
  title: string;
  description: string;
  category: string;
  mainImage: string;
  album?: string[];
}

interface TimelineItem {
  id?: number;
  year: string;
  title: string;
  description: string;
  image: string;
}

export default function Admin() {
  // Auth state
  const [token, setToken] = useState<string | null>(localStorage.getItem('eme_admin_token'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loadingLogin, setLoadingLogin] = useState(false);

  // Active partition state: 'projects' | 'timeline' | 'settings' | 'account'
  const [activeTab, setActiveTab] = useState<'projects' | 'timeline' | 'settings' | 'account'>('projects');

  // Account Change State
  const [newUsername, setNewUsername] = useState(localStorage.getItem('eme_admin_username') || 'admin');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [savingAccount, setSavingAccount] = useState(false);

  // Site settings state
  const [settingsForm, setSettingsForm] = useState({
    heroImage: '',
    aboutImage: ''
  });
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [uploadProgressSettings, setUploadProgressSettings] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');

  // Core lists state
  const [projects, setProjects] = useState<Project[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  // Form states
  const [projectForm, setProjectForm] = useState<Project>({
    title: '',
    description: '',
    category: 'Cozinha',
    mainImage: ''
  });
  const [timelineForm, setTimelineForm] = useState<TimelineItem>({
    year: '',
    title: '',
    description: '',
    image: ''
  });

  // Editor states
  const [isEditingProject, setIsEditingProject] = useState(false);
  const [editProjectId, setEditProjectId] = useState<number | null>(null);

  const [isEditingTimeline, setIsEditingTimeline] = useState(false);
  const [editTimelineId, setEditTimelineId] = useState<number | null>(null);

  // Filter category state
  const [projectFilter, setProjectFilter] = useState('Todos');

  // Interactive message state
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [uploadProgress, setUploadProgress] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');

  // Setup form category choices
  const categories = ['Adega', 'Banheiro', 'Closet', 'Cozinha', 'Quarto', 'Sala'];

  // Clear messages helper
  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // On mount or token change, load active partitions
  useEffect(() => {
    if (token) {
      if (activeTab === 'settings') {
        loadSettings();
      } else {
        loadData();
      }
    }
  }, [token, activeTab]);

  const loadSettings = async () => {
    setLoadingSettings(true);
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data = await res.json();
        setSettingsForm({
          heroImage: data.heroImage || '/images/banner-principal.jpg',
          aboutImage: data.aboutImage || '/images/sobre-nos.jpg'
        });
      }
    } catch (e) {
      console.error('Error loading settings:', e);
      showToast('Erro ao carregar configurações', 'error');
    } finally {
      setLoadingSettings(false);
    }
  };

  const saveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(settingsForm)
      });
      if (res.ok) {
        showToast('Configurações salvas!');
      } else {
        const err = await res.json();
        showToast(err.error || 'Erro ao salvar configurações', 'error');
      }
    } catch (e) {
      console.error('Error saving settings:', e);
      showToast('Erro técnico ao salvar', 'error');
    } finally {
      setSavingSettings(false);
    }
  };

  const loadData = async () => {
    setLoadingData(true);
    try {
      if (activeTab === 'projects') {
        const res = await fetch('/api/projects');
        if (res.ok) {
          const list = await res.json();
          setProjects(list);
        }
      } else {
        const res = await fetch('/api/timeline');
        if (res.ok) {
          const list = await res.json();
          setTimeline(list);
        }
      }
    } catch (e) {
      console.error('Error fetching data:', e);
      showToast('Falha de conexão com o servidor', 'error');
    } finally {
      setLoadingData(false);
    }
  };

  // Auth Handler
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setLoadingLogin(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await res.json();
      if (res.ok && data.token) {
        localStorage.setItem('eme_admin_token', data.token);
        localStorage.setItem('eme_admin_username', data.user.username);
        setToken(data.token);
        setNewUsername(data.user.username);
        showToast('Login realizado com sucesso', 'success');
      } else {
        setLoginError(data.error || 'Credenciais inválidas');
      }
    } catch (err) {
      setLoginError('Problema ao conectar ao backend administrativo');
    } finally {
      setLoadingLogin(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('eme_admin_token');
    localStorage.removeItem('eme_admin_username');
    setToken(null);
    showToast('Sessão finalizada', 'success');
  };

  const saveAccountCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword && newPassword !== confirmPassword) {
      showToast('As senhas digitadas não batem!', 'error');
      return;
    }
    setSavingAccount(true);
    try {
      const res = await fetch('/api/auth/update-credentials', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          username: newUsername,
          password: newPassword || undefined
        })
      });
      if (res.ok) {
        localStorage.setItem('eme_admin_username', newUsername);
        showToast('Credenciais atualizadas com sucesso!');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        const err = await res.json();
        showToast(err.error || 'Erro ao salvar credenciais', 'error');
      }
    } catch (e) {
      showToast('Erro de conexão ao salvar', 'error');
    } finally {
      setSavingAccount(false);
    }
  };

  // Master upload file helper
  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    folder: 'projetos' | 'timeline' | 'site-assets',
    fieldKey?: 'heroImage' | 'aboutImage' | 'album'
  ) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);

    if (folder === 'site-assets') {
      setUploadProgressSettings('uploading');
    } else {
      setUploadProgress('uploading');
    }

    try {
      const res = await fetch(`/api/upload?folder=${folder}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      const data = await res.json();
      if (res.ok && data.filePath) {
        if (folder === 'site-assets') {
          setUploadProgressSettings('success');
          if (fieldKey && fieldKey !== 'album') {
            setSettingsForm(prev => ({ ...prev, [fieldKey]: data.filePath }));
          }
        } else {
          setUploadProgress('success');
          if (folder === 'projetos') {
            if (fieldKey === 'album') {
              setProjectForm(prev => {
                const currentAlbum = prev.album || [];
                return {
                  ...prev,
                  album: [...currentAlbum, data.filePath],
                  mainImage: prev.mainImage || data.filePath
                };
              });
            } else {
              setProjectForm(prev => ({ ...prev, mainImage: data.filePath }));
            }
          } else {
            setTimelineForm(prev => ({ ...prev, image: data.filePath }));
          }
        }
        showToast('Imagem enviada com sucesso');
      } else {
        if (folder === 'site-assets') {
          setUploadProgressSettings('error');
        } else {
          setUploadProgress('error');
        }
        showToast(data.error || 'Erro no upload de imagem', 'error');
      }
    } catch (err) {
      if (folder === 'site-assets') {
        setUploadProgressSettings('error');
      } else {
        setUploadProgress('error');
      }
      showToast('Ocorreu um erro ao enviar arquivo', 'error');
    }
  };

  // Project Actions
  const saveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectForm.title || !projectForm.mainImage || !projectForm.category) {
      showToast('Por favor, preencha o título, categoria e adicione uma imagem', 'error');
      return;
    }

    try {
      const url = isEditingProject ? `/api/projects/${editProjectId}` : '/api/projects';
      const method = isEditingProject ? 'PUT' : 'POST';

      const payload = {
        title: projectForm.title,
        description: projectForm.description,
        category: projectForm.category,
        image: projectForm.mainImage,
        album: projectForm.album && projectForm.album.length > 0 ? projectForm.album : [projectForm.mainImage]
      };

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        showToast(isEditingProject ? 'Projeto atualizado!' : 'Projeto adicionado!');
        resetProjectForm();
        loadData();
      } else {
        const err = await res.json();
        showToast(err.error || 'Erro ao registrar projeto', 'error');
      }
    } catch (err) {
      showToast('Erro interno do servidor ao salvar', 'error');
    }
  };

  const handleEditProjectClick = (proj: Project & { mainImage: string }) => {
    setProjectForm({
      title: proj.title,
      description: proj.description || '',
      category: proj.category,
      mainImage: proj.mainImage,
      album: proj.album && proj.album.length > 0 ? proj.album : [proj.mainImage]
    });
    setEditProjectId(proj.id || null);
    setIsEditingProject(true);
    setUploadProgress('idle');
  };

  const deleteProjectClick = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este projeto?')) return;
    try {
      const res = await fetch(`/api/projects/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        showToast('Projeto removido com sucesso');
        loadData();
      } else {
        showToast('Falha ao remover item', 'error');
      }
    } catch (err) {
      showToast('Erro técnico ao excluir', 'error');
    }
  };

  const resetProjectForm = () => {
    setProjectForm({ title: '', description: '', category: 'Cozinha', mainImage: '', album: [] });
    setIsEditingProject(false);
    setEditProjectId(null);
    setUploadProgress('idle');
  };

  // Timeline Actions
  const saveTimeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!timelineForm.year || !timelineForm.title || !timelineForm.description) {
      showToast('Por favor, preencha o Ano, Título e Descrição', 'error');
      return;
    }

    try {
      const url = isEditingTimeline ? `/api/timeline/${editTimelineId}` : '/api/timeline';
      const method = isEditingTimeline ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(timelineForm)
      });

      if (res.ok) {
        showToast(isEditingTimeline ? 'História atualizada!' : 'Meta/Fase adicionada!');
        resetTimelineForm();
        loadData();
      } else {
        const err = await res.json();
        showToast(err.error || 'Erro ao registrar linha do tempo', 'error');
      }
    } catch (err) {
      showToast('Erro técnico ao salvar', 'error');
    }
  };

  const handleEditTimelineClick = (time: TimelineItem) => {
    setTimelineForm({
      year: time.year,
      title: time.title,
      description: time.description,
      image: time.image || ''
    });
    setEditTimelineId(time.id || null);
    setIsEditingTimeline(true);
    setUploadProgress('idle');
  };

  const deleteTimelineClick = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir esta fase da linha do tempo?')) return;
    try {
      const res = await fetch(`/api/timeline/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        showToast('Evolução histórica removida');
        loadData();
      } else {
        showToast('Erro ao remover fase histórica', 'error');
      }
    } catch (err) {
      showToast('Erro técnico técnico ao deletar', 'error');
    }
  };

  const resetTimelineForm = () => {
    setTimelineForm({ year: '', title: '', description: '', image: '' });
    setIsEditingTimeline(false);
    setEditTimelineId(null);
    setUploadProgress('idle');
  };

  // Render Login Layout if no token is stored
  if (!token) {
    return (
      <div className="min-h-screen bg-black text-white flex flex-col justify-center items-center px-4 relative overflow-hidden">
        {/* Visual Blur Circles */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-950/20 rounded-full mix-blend-multiply filter blur-3xl opacity-30 pointer-events-none"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-red-950/20 rounded-full mix-blend-multiply filter blur-3xl opacity-30 pointer-events-none"></div>

        {/* Back Link to Home */}
        <a 
          href="/" 
          className="absolute top-8 left-8 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={18} />
          <span>Voltar ao Site</span>
        </a>

        {/* Brand Header */}
        <div className="text-center mb-8 relative z-10 animate-fade-in">
          <img
            src="/images/logo/logo-eme-moveis.png"
            alt="eMe Móveis"
            className="h-24 sm:h-28 w-auto mx-auto mb-3 select-none"
            draggable={false}
          />
          <p className="text-sm text-gray-400 font-medium">Portal Administrativo Oficial</p>
        </div>

        {/* Login Card */}
        <div className="bg-[#0c0c0c] border border-gray-900 w-full max-w-md p-10 rounded-2xl shadow-2xl relative z-10">
          <h2 className="text-xl font-bold mb-6 text-center text-white/90">Acesso Restrito</h2>

          {loginError && (
            <div className="bg-red-950/30 border border-red-800/40 text-red-500 rounded-xl p-4 mb-6 flex items-center gap-3 text-sm">
              <AlertTriangle size={18} className="shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-xs uppercase font-extrabold tracking-wider text-gray-400 mb-2">Usuário</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-500">
                  <User size={18} />
                </span>
                <input 
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-[#141414] border border-gray-800 focus:border-red-800 rounded-xl pl-11 pr-4 py-4 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all text-sm font-sans"
                  placeholder="Seu usuário"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs uppercase font-extrabold tracking-wider text-gray-400 mb-2">Senha</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-500">
                  <Lock size={18} />
                </span>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#141414] border border-gray-800 focus:border-red-800 rounded-xl pl-11 pr-4 py-4 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all text-sm font-sans"
                  placeholder="Sua senha secreta"
                  required
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loadingLogin}
              className="w-full bg-red-800 hover:bg-red-900 disabled:opacity-50 text-white py-4 rounded-xl font-bold transition-all text-sm tracking-wide shadow-lg"
            >
              {loadingLogin ? 'Autenticando...' : 'Entrar no Painel'}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-gray-900 text-center text-xs text-gray-500 select-none">
            Utilize as credenciais padrão de estudante ou solicite seu TI.
          </div>
        </div>
      </div>
    );
  }

  // Filter project listing
  const filteredProjects = projectFilter === 'Todos' 
    ? projects 
    : projects.filter(p => p.category === projectFilter);

  // Render Admin Dashboard Interface after Authentication
  return (
    <div className="min-h-screen bg-black text-white font-sans flex flex-col justify-start relative">
      {/* Dynamic Toast feedback */}
      {toastMessage && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-6 py-4 rounded-xl shadow-2xl border ${
          toastMessage.type === 'success' 
            ? 'bg-neutral-900 border-red-800/40 text-white' 
            : 'bg-red-950/40 border-red-800/50 text-red-500'
        }`}>
          {toastMessage.type === 'success' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <span className="text-sm font-semibold">{toastMessage.text}</span>
        </div>
      )}

      {/* Main Admin Header bar */}
      <header className="bg-neutral-950 border-b border-gray-900 py-5 sticky top-0 z-45 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <img
                src="/images/logo/logo-eme-icon.png"
                alt="eMe Móveis"
                className="h-9 w-9 select-none"
                draggable={false}
              />
              <h1 className="text-xl font-extrabold tracking-tighter">
                eMe <span className="text-red-800">PAINEL</span>
              </h1>
            </div>
            <nav className="flex space-x-1">
              <button
                onClick={() => setActiveTab('projects')}
                className={`px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${
                  activeTab === 'projects' ? 'bg-red-800 text-white shadow-md' : 'text-gray-400 hover:text-white'
                }`}
              >
                <Folder size={16} />
                <span>Projetos (Portfólio)</span>
              </button>
              <button
                onClick={() => setActiveTab('timeline')}
                className={`px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${
                  activeTab === 'timeline' ? 'bg-red-800 text-white shadow-md' : 'text-gray-400 hover:text-white'
                }`}
              >
                <Clock size={16} />
                <span>Linha do Tempo</span>
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className={`px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${
                  activeTab === 'settings' ? 'bg-red-800 text-white shadow-md' : 'text-gray-400 hover:text-white'
                }`}
              >
                <ImageIcon size={16} />
                <span>Banners & Capas</span>
              </button>
              <button
                onClick={() => setActiveTab('account')}
                className={`px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${
                  activeTab === 'account' ? 'bg-red-800 text-white shadow-md' : 'text-gray-400 hover:text-white'
                }`}
              >
                <User size={16} />
                <span>Acesso & Senha</span>
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <a 
              href="/" 
              className="text-xs bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-lg transition-all"
            >
              Consultar Site Público
            </a>
            <button
              onClick={handleLogout}
              className="text-xs bg-red-950/40 hover:bg-red-900 border border-red-800/20 text-red-400 hover:text-white px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all"
            >
              <LogOut size={14} />
              <span>Sair</span>
            </button>
          </div>
        </div>
      </header>

      {/* Dashboard container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 flex-grow w-full">
        
        {/* SECTION A: PROJECTS MANAGEMENT */}
        {activeTab === 'projects' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
            
            {/* Project Creator Form card */}
            <div className="lg:col-span-5 bg-[#0a0a0a] border border-gray-900 p-8 rounded-2xl shadow-xl">
              <h2 className="text-lg font-extrabold mb-6 flex items-center gap-2 text-white/90">
                {isEditingProject ? <Edit2 size={18} className="text-red-700" /> : <Plus size={20} className="text-red-700" />}
                <span>{isEditingProject ? 'Editar Projeto' : 'Adicionar Projeto'}</span>
              </h2>

              <form onSubmit={saveProject} className="space-y-6">
                <div>
                  <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Título do Ambiente</label>
                  <input 
                    type="text"
                    value={projectForm.title}
                    onChange={(e) => setProjectForm(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all font-sans text-sm"
                    placeholder="Ex: Cozinha Planejada Provence"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Categoria</label>
                    <select 
                      value={projectForm.category}
                      onChange={(e) => setProjectForm(prev => ({ ...prev, category: e.target.value }))}
                      className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all text-sm"
                    >
                      {categories.map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Descrição Curta</label>
                  <textarea 
                    value={projectForm.description}
                    onChange={(e) => setProjectForm(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl p-4 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all font-sans text-sm resize-none"
                    placeholder="Descreva materiais, puxadores, ferragens ou o conceito visual..."
                  />
                </div>

                {/* File Upload Field */}
                <div>
                  <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Imagem de Capa do Projeto</label>
                  
                  {projectForm.mainImage ? (
                    <div className="relative group rounded-xl overflow-hidden aspect-video border border-gray-800">
                      <img 
                        src={projectForm.mainImage} 
                        alt="Miniatura" 
                        className="w-full h-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                        <button
                          type="button"
                          onClick={() => setProjectForm(prev => ({ ...prev, mainImage: '' }))}
                          className="bg-red-850 hover:bg-red-900 border border-red-700/30 text-white p-3 rounded-full flex items-center gap-1.5 font-bold transition-all text-sm shadow-md"
                        >
                          <X size={16} />
                          <span>Remover Capa</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="border border-dashed border-gray-850 hover:border-red-800/80 rounded-2xl p-6 flex flex-col justify-center items-center bg-[#121212]/30 relative transition-colors">
                      <input 
                        type="file" 
                        accept="image/*"
                        onChange={(e) => handleFileUpload(e, 'projetos')}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      />
                      <Upload size={32} className="text-gray-500 mb-3" />
                      <span className="text-sm font-semibold text-gray-300">Escolha a Capa</span>
                      <span className="text-xs text-gray-500 mt-2 text-center leading-relaxed">
                        PNG, JPG, WEBP • <strong className="text-red-700">Ideal:</strong> 1200x900px <br />
                        <span className="text-[11px] text-gray-500 block mt-1">Para performance ideal, mantenha abaixo de 200 KB (Máx 5MB)</span>
                      </span>

                      {uploadProgress === 'uploading' && (
                        <div className="absolute inset-0 bg-black/85 flex flex-col items-center justify-center rounded-2xl">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800 mb-3"></div>
                          <span className="text-xs text-gray-300">Enviando imagem ao servidor local...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Galeria do Projeto (Álbum) */}
                <div className="border-t border-gray-900 pt-6 mt-6">
                  <div className="flex justify-between items-center mb-3">
                    <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400">
                      Galeria / Fotos do Projeto ({projectForm.album?.length || 0} fotos)
                    </label>
                  </div>
                  
                  {/* Album Grid list */}
                  {projectForm.album && projectForm.album.length > 0 ? (
                    <div className="grid grid-cols-4 gap-3 mb-4">
                      {projectForm.album.map((picUrl, idx) => {
                        const isCover = projectForm.mainImage === picUrl;
                        return (
                          <div key={idx} className={`relative group aspect-square rounded-lg overflow-hidden border ${isCover ? 'border-red-800 ring-2 ring-red-800/40' : 'border-gray-850'}`}>
                            <img src={picUrl} alt={`Foto ${idx + 1}`} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                            
                            {/* Cover badge */}
                            {isCover && (
                              <span className="absolute top-1 left-1 bg-red-800 text-white text-[8px] font-extrabold px-1 py-0.5 rounded uppercase pointer-events-none">
                                Capa
                              </span>
                            )}

                            {/* Action Overlay */}
                            <div className="absolute inset-0 bg-black/85 opacity-0 group-hover:opacity-100 flex flex-col justify-between p-1.5 transition-all">
                              {/* Remove from Album */}
                              <button
                                type="button"
                                onClick={() => {
                                  const newAlbum = (projectForm.album || []).filter(url => url !== picUrl);
                                  setProjectForm(prev => {
                                    let nextMain = prev.mainImage;
                                    if (picUrl === prev.mainImage) {
                                      nextMain = newAlbum[0] || '';
                                    }
                                    return {
                                      ...prev,
                                      album: newAlbum,
                                      mainImage: nextMain
                                    };
                                  });
                                }}
                                className="self-end bg-red-950 hover:bg-red-800 border border-red-800/40 text-red-100 p-1 rounded transition-colors"
                                title="Remover imagem"
                              >
                                <X size={10} />
                              </button>

                              {/* Make Cover Button if not already cover */}
                              {!isCover && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setProjectForm(prev => ({ ...prev, mainImage: picUrl }));
                                  }}
                                  className="w-full bg-neutral-900 border border-gray-800 text-[8px] leading-tight font-bold py-1 rounded text-gray-200 hover:bg-red-800 hover:text-white transition-colors"
                                >
                                  Usar Cover
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-550 italic mb-4">Nenhuma imagem adicional adicionada ainda.</p>
                  )}

                  {/* Add images upload block */}
                  <div className="border border-dashed border-gray-850 hover:border-red-800/80 rounded-xl p-4 flex flex-col justify-center items-center bg-[#121212]/30 relative transition-colors">
                    <input 
                      type="file" 
                      accept="image/*"
                      onChange={(e) => handleFileUpload(e, 'projetos', 'album')}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <Upload size={20} className="text-gray-500 mb-2" />
                    <span className="text-xs font-semibold text-gray-300">Adicionar Foto ao Álbum</span>
                    <span className="text-[9px] text-gray-500 mt-0.5">PNG, JPG, WEBP (várias fotos por projeto)</span>
                  </div>
                </div>

                <div className="flex gap-4 pt-4 border-t border-gray-900">
                  <button 
                    type="submit" 
                    className="flex-grow bg-red-800 hover:bg-red-900 text-white py-3 px-6 rounded-xl font-bold transition-all text-sm tracking-wide shadow-md"
                  >
                    {isEditingProject ? 'Atualizar Projeto' : 'Salvar Projeto'}
                  </button>
                  {isEditingProject && (
                    <button 
                      type="button" 
                      onClick={resetProjectForm}
                      className="bg-gray-900 hover:bg-gray-800 text-gray-300 py-3 px-6 rounded-xl font-bold transition-all text-sm"
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </form>
            </div>

            {/* Project List Table card */}
            <div className="lg:col-span-7 bg-[#0a0a0a] border border-gray-900 p-8 rounded-2xl shadow-xl">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <h2 className="text-lg font-extrabold text-white/90">Portfólio Cadastrado</h2>
                
                {/* Visual Category filter dropdown */}
                <div className="flex items-center gap-2 bg-neutral-900 border border-gray-850 px-3 py-1.5 rounded-xl">
                  <Filter size={14} className="text-gray-400" />
                  <select
                    value={projectFilter}
                    onChange={(e) => setProjectFilter(e.target.value)}
                    className="bg-transparent border-none text-xs font-bold text-gray-300 focus:outline-none"
                  >
                    <option value="Todos">Todas Categorias</option>
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              </div>

              {loadingData ? (
                <div className="flex justify-center items-center py-24">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800"></div>
                </div>
              ) : filteredProjects.length === 0 ? (
                <div className="text-center py-20 text-gray-500">
                  <ImageIcon size={44} className="mx-auto mb-4 opacity-30" />
                  <p className="text-sm font-semibold">Nenhum projeto encontrado nesta categoria.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead>
                      <tr className="border-b border-gray-900 text-xs font-extrabold uppercase tracking-wide text-gray-500">
                        <th className="pb-4">Imagem</th>
                        <th className="pb-4">Projeto</th>
                        <th className="pb-4">Categoria</th>
                        <th className="pb-4 text-right">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-900">
                      {filteredProjects.map(proj => (
                        <tr key={proj.id} className="group">
                          <td className="py-4">
                            <div className="w-14 h-10 rounded overflow-hidden border border-gray-900">
                              <img 
                                src={proj.mainImage} 
                                alt={proj.title} 
                                className="w-full h-full object-cover"
                                referrerPolicy="no-referrer"
                              />
                            </div>
                          </td>
                          <td className="py-4 pr-4">
                            <p className="font-bold text-white max-w-[200px] truncate">{proj.title}</p>
                            <p className="text-xs text-red-500 font-bold mt-0.5">
                              {proj.album ? proj.album.length : 1} {proj.album?.length === 1 ? 'foto cadastrada' : 'fotos cadastradas'}
                            </p>
                            <p className="text-xs text-gray-500 max-w-[200px] truncate mt-0.5">{proj.description}</p>
                          </td>
                          <td className="py-4">
                            <span className="text-xs bg-gray-900 border border-gray-850 px-2.5 py-1 rounded-full text-red-400 font-bold">
                              {proj.category}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <div className="inline-flex space-x-2">
                              <button
                                onClick={() => handleEditProjectClick(proj)}
                                className="p-2 bg-gray-950 hover:bg-gray-900 rounded-lg text-gray-400 hover:text-white transition-all shadow border border-gray-900"
                              >
                                <Edit2 size={14} />
                              </button>
                              <button
                                onClick={() => deleteProjectClick(proj.id!)}
                                className="p-2 bg-red-950/20 hover:bg-red-800 rounded-lg text-red-400 hover:text-white transition-all border border-red-900/10"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* SECTION B: TIMELINE MANAGEMENT */}
        {activeTab === 'timeline' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
            
            {/* Timeline Item Creator card */}
            <div className="lg:col-span-5 bg-[#0a0a0a] border border-gray-900 p-8 rounded-2xl shadow-xl">
              <h2 className="text-lg font-extrabold mb-6 flex items-center gap-2 text-white/90">
                {isEditingTimeline ? <Edit2 size={18} className="text-red-700" /> : <Plus size={20} className="text-red-700" />}
                <span>{isEditingTimeline ? 'Editar Evento Histórico' : 'Adicionar Evento Histórico'}</span>
              </h2>

              <form onSubmit={saveTimeline} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="md:col-span-1">
                    <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Ano</label>
                    <input 
                      type="text"
                      maxLength={10}
                      value={timelineForm.year}
                      onChange={(e) => setTimelineForm(prev => ({ ...prev, year: e.target.value }))}
                      className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all font-mono font-bold text-sm text-center"
                      placeholder="Ex: 2024"
                      required
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Título do Evento</label>
                    <input 
                      type="text"
                      value={timelineForm.title}
                      onChange={(e) => setTimelineForm(prev => ({ ...prev, title: e.target.value }))}
                      className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all font-sans text-sm"
                      placeholder="Ex: Ampliação do Parque Tecnológico"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Descrição dos Fatos</label>
                  <textarea 
                    value={timelineForm.description}
                    onChange={(e) => setTimelineForm(prev => ({ ...prev, description: e.target.value }))}
                    rows={4}
                    className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl p-4 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all font-sans text-sm resize-none"
                    placeholder="Conte o avanço, ampliação, investimento na equipe ou outra marca que impulsionou a eMe"
                    required
                  />
                </div>

                {/* File Upload Field for Timeline item */}
                <div>
                  <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Foto Marcante (Opcional)</label>
                  
                  {timelineForm.image ? (
                    <div className="relative group rounded-xl overflow-hidden aspect-video border border-gray-800">
                      <img 
                        src={timelineForm.image} 
                        alt="Miniatura" 
                        className="w-full h-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                        <button
                          type="button"
                          onClick={() => setTimelineForm(prev => ({ ...prev, image: '' }))}
                          className="bg-red-850 hover:bg-red-900 border border-red-700/30 text-white p-3 rounded-full flex items-center gap-1.5 font-bold transition-all text-sm shadow-md"
                        >
                          <X size={16} />
                          <span>Remover</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="border border-dashed border-gray-850 hover:border-red-800/80 rounded-2xl p-6 flex flex-col justify-center items-center bg-[#121212]/30 relative transition-colors">
                      <input 
                        type="file" 
                        accept="image/*"
                        onChange={(e) => handleFileUpload(e, 'timeline')}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      />
                      <Upload size={32} className="text-gray-500 mb-3" />
                      <span className="text-sm font-semibold text-gray-300">Escolha um arquivo</span>
                      <span className="text-xs text-gray-500 mt-2 text-center leading-relaxed">
                        PNG, JPG, WEBP • <strong className="text-red-700">Dimensão ideal:</strong> 800x600px <br />
                        <span className="text-[11px] text-gray-500 block mt-1">Para performance ideal, mantenha abaixo de 200 KB (Máx 5MB)</span>
                      </span>

                      {uploadProgress === 'uploading' && (
                        <div className="absolute inset-0 bg-black/85 flex flex-col items-center justify-center rounded-2xl">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800 mb-3"></div>
                          <span className="text-xs text-gray-300">Enviando imagem ao servidor local...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex gap-4 pt-4 border-t border-gray-900">
                  <button 
                    type="submit" 
                    className="flex-grow bg-red-800 hover:bg-red-900 text-white py-3 px-6 rounded-xl font-bold transition-all text-sm tracking-wide shadow-md"
                  >
                    {isEditingTimeline ? 'Atualizar Evento' : 'Salvar Evento'}
                  </button>
                  {isEditingTimeline && (
                    <button 
                      type="button" 
                      onClick={resetTimelineForm}
                      className="bg-gray-900 hover:bg-gray-800 text-gray-300 py-3 px-6 rounded-xl font-bold transition-all text-sm"
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </form>
            </div>

            {/* Timeline Items Listing card */}
            <div className="lg:col-span-7 bg-[#0a0a0a] border border-gray-900 p-8 rounded-2xl shadow-xl">
              <h2 className="text-lg font-extrabold mb-8 text-white/90">Marcos Históricos Cadastrados</h2>

              {loadingData ? (
                <div className="flex justify-center items-center py-24">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800"></div>
                </div>
              ) : timeline.length === 0 ? (
                <div className="text-center py-20 text-gray-500">
                  <Clock size={44} className="mx-auto mb-4 opacity-30" />
                  <p className="text-sm font-semibold">Nenhuma marca cronológica cadastrada.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {timeline.map(item => (
                    <div 
                      key={item.id} 
                      className="border border-gray-900 hover:border-gray-800 bg-[#0c0c0c] p-5 rounded-2xl flex items-start gap-4 transition-all"
                    >
                      {item.image && (
                        <div className="w-16 h-16 rounded-xl overflow-hidden border border-gray-900 shrink-0">
                          <img 
                            src={item.image} 
                            alt={item.title} 
                            className="w-full h-full object-cover"
                            referrerPolicy="no-referrer"
                          />
                        </div>
                      )}
                      
                      <div className="flex-grow">
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-extrabold text-[#951d1d] text-base bg-red-950/20 border border-red-900/10 px-2.5 py-0.5 rounded">
                            {item.year}
                          </span>
                          <h3 className="font-bold text-white text-base">{item.title}</h3>
                        </div>
                        <p className="text-xs text-gray-400 mt-2 leading-relaxed line-clamp-2 md:line-clamp-none">
                          {item.description}
                        </p>
                      </div>

                      <div className="flex space-x-2 shrink-0 self-center">
                        <button
                          onClick={() => handleEditTimelineClick(item)}
                          className="p-2 bg-gray-950 hover:bg-gray-900 rounded-lg text-gray-400 hover:text-white transition-all shadow border border-gray-900"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => deleteTimelineClick(item.id!)}
                          className="p-2 bg-red-950/20 hover:bg-red-800 rounded-lg text-red-400 hover:text-white transition-all border border-red-900/10"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* SECTION C: SETTINGS MANAGEMENT */}
        {activeTab === 'settings' && (
          <div className="max-w-4xl mx-auto bg-[#0a0a0a] border border-gray-900 p-8 md:p-10 rounded-2xl shadow-xl">
            <h2 className="text-xl font-extrabold mb-2 flex items-center gap-2 text-white/90">
              <ImageIcon className="text-red-800" size={22} />
              <span>Personalizar Imagens de Destaque</span>
            </h2>
            <p className="text-xs text-gray-400 mb-8">
              Substitua de forma simples as imagens principais exibidas no topo do site e na seção de história institucional (Nossa História).
            </p>

            {loadingSettings ? (
              <div className="flex justify-center items-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800"></div>
              </div>
            ) : (
              <form onSubmit={saveSettings} className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Banner Principal */}
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400">
                        Banner do Topo (Hero principal)
                      </label>
                      <span className="text-[10px] text-gray-500 font-mono">1920x1080 ideal</span>
                    </div>

                    {settingsForm.heroImage ? (
                      <div className="relative group rounded-xl overflow-hidden aspect-video border border-gray-900 bg-neutral-900">
                        <img 
                          src={settingsForm.heroImage} 
                          alt="Banner Principal" 
                          className="w-full h-full object-cover"
                          referrerPolicy="no-referrer"
                        />
                        <div className="absolute inset-0 bg-black/65 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                          <button
                            type="button"
                            onClick={() => setSettingsForm(prev => ({ ...prev, heroImage: '' }))}
                            className="bg-red-850 hover:bg-red-900 border border-red-755 text-white p-3 rounded-full flex items-center gap-1.5 font-bold transition-all text-sm shadow-md"
                          >
                            <X size={16} />
                            <span>Alterar Imagem</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="border border-dashed border-gray-850 hover:border-red-800/80 rounded-2xl p-6 flex flex-col justify-center items-center bg-[#121212]/30 relative transition-colors aspect-video text-center">
                        <input 
                          type="file" 
                          accept="image/*"
                          onChange={(e) => handleFileUpload(e, 'site-assets', 'heroImage')}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        />
                        <Upload size={28} className="text-gray-500 mb-2" />
                        <span className="text-xs font-bold text-gray-300">Enviar Imagem</span>
                        <span className="text-[10px] text-gray-400 mt-1 leading-relaxed">
                          Clique para escolher. <br />
                          <strong className="text-red-500">Ideal: 1920x1080px</strong>. <br />
                          Recomendado: abaixo de 200 KB (Máx 5MB).
                        </span>

                        {uploadProgressSettings === 'uploading' && (
                          <div className="absolute inset-0 bg-black/85 flex flex-col items-center justify-center rounded-2xl">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800 mb-3"></div>
                            <span className="text-[10px] text-gray-400">Fazendo upload...</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Nossa História */}
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400">
                        Imagem "Nossa História"
                      </label>
                      <span className="text-[10px] text-gray-500 font-mono font-sans">Alta resolução ideal</span>
                    </div>

                    {settingsForm.aboutImage ? (
                      <div className="relative group rounded-xl overflow-hidden aspect-video border border-gray-900 bg-neutral-900">
                        <img 
                          src={settingsForm.aboutImage} 
                          alt="Foto Nossa História" 
                          className="w-full h-full object-cover"
                          referrerPolicy="no-referrer"
                        />
                        <div className="absolute inset-0 bg-black/65 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                          <button
                            type="button"
                            onClick={() => setSettingsForm(prev => ({ ...prev, aboutImage: '' }))}
                            className="bg-red-850 hover:bg-red-900 border border-red-755 text-white p-3 rounded-full flex items-center gap-1.5 font-bold transition-all text-sm shadow-md"
                          >
                            <X size={16} />
                            <span>Alterar Imagem</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="border border-dashed border-gray-850 hover:border-red-800/80 rounded-2xl p-6 flex flex-col justify-center items-center bg-[#121212]/30 relative transition-colors aspect-video text-center">
                        <input 
                          type="file" 
                          accept="image/*"
                          onChange={(e) => handleFileUpload(e, 'site-assets', 'aboutImage')}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        />
                        <Upload size={28} className="text-gray-500 mb-2" />
                        <span className="text-xs font-bold text-gray-300">Enviar Imagem</span>
                        <span className="text-[10px] text-gray-400 mt-1 leading-relaxed">
                          Clique para escolher. <br />
                          <strong className="text-red-500">Ideal: 1200x800px</strong>. <br />
                          Recomendado: abaixo de 200 KB (Máx 5MB).
                        </span>

                        {uploadProgressSettings === 'uploading' && (
                          <div className="absolute inset-0 bg-black/85 flex flex-col items-center justify-center rounded-2xl">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-800 mb-3"></div>
                            <span className="text-[10px] text-gray-400">Fazendo upload...</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-6 border-t border-gray-900 flex justify-end">
                  <button 
                    type="submit" 
                    disabled={savingSettings}
                    className="bg-red-800 hover:bg-red-900 disabled:opacity-50 text-white font-bold px-8 py-3.5 rounded-xl transition-all text-sm shadow-lg shadow-red-950/20 flex items-center gap-2"
                  >
                    {savingSettings && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>}
                    <span>{savingSettings ? 'Salvando...' : 'Salvar Alterações'}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* SECTION D: ACCOUNT MANAGEMENT */}
        {activeTab === 'account' && (
          <div className="max-w-md mx-auto bg-[#0a0a0a] border border-gray-900 p-8 md:p-10 rounded-2xl shadow-xl">
            <h2 className="text-xl font-extrabold mb-2 flex items-center gap-2 text-white/90">
              <Lock className="text-red-800" size={22} />
              <span>Gerenciar Usuário & Senha</span>
            </h2>
            <p className="text-xs text-gray-400 mb-6 leading-relaxed">
              Mude as credenciais do usuário administrador diretamente pela interface. Deixe o campo de senha vazio caso queira manter a senha atual e alterar apenas o nome do usuário.
            </p>

            <form onSubmit={saveAccountCredentials} className="space-y-6">
              <div>
                <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Nome do Usuário</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-500">
                    <User size={16} />
                  </span>
                  <input 
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl pl-11 pr-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all text-sm"
                    placeholder="Ex: admin"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Nova Senha (Opcional)</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-500">
                    <Lock size={16} />
                  </span>
                  <input 
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl pl-11 pr-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all text-sm font-sans"
                    placeholder="Deixe em branco para não alterar"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs uppercase font-extrabold tracking-wide text-gray-400 mb-2">Confirmar Nova Senha</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-500">
                    <Lock size={16} />
                  </span>
                  <input 
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full bg-[#121212] border border-gray-800 focus:border-red-800 rounded-xl pl-11 pr-4 py-3.5 text-white focus:outline-none focus:ring-1 focus:ring-red-800 transition-all text-sm font-sans"
                    placeholder="Confirme a nova senha"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-gray-900 flex justify-end">
                <button 
                  type="submit" 
                  disabled={savingAccount}
                  className="w-full bg-red-800 hover:bg-red-900 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl transition-all text-sm shadow-lg flex justify-center items-center gap-2"
                >
                  {savingAccount && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>}
                  <span>{savingAccount ? 'Salvando...' : 'Salvar Novas Credenciais'}</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
