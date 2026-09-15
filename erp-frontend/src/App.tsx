import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Building2, Layers, Users, Landmark, Package, Shield, FileBarChart, CalendarDays, Sparkles,
  Power, Menu, X, User, ArrowRight, HelpCircle, Eye, EyeOff, Moon, Sun, ShoppingCart
} from 'lucide-react';

// Assets
import logoFull from './assets/logo-eme-full.png';
import logoIcon from './assets/logo-eme-icon.png';

// Services
import { authService, getApiErrorMessage } from './services/api';
import { User as UserType } from './types';

// Views
import DashboardView from './components/DashboardView';
import ClientsView from './components/ClientsView';
import ProjectsView from './components/ProjectsView';
import FinancialView from './components/FinancialView';
import StockView from './components/StockView';
import PurchasesView from './components/PurchasesView';
import UsersView from './components/UsersView';
import ReportsView from './components/ReportsView';
import CalendarView from './components/CalendarView';
import NovidadesView from './components/NovidadesView';

type TabId = 'dashboard' | 'clients' | 'projects' | 'financial' | 'stock' | 'purchases' | 'users' | 'reports' | 'calendar' | 'novidades';
type ThemeMode = 'dark' | 'light';

interface TabItem {
  id: TabId;
  label: string;
  icon: React.ComponentType<any>;
  roles: string[];
}

const TABS: TabItem[] = [
  { id: 'dashboard', label: 'Painel Geral', icon: Layers, roles: ['ADMIN', 'GERENTE', 'ESTOQUE'] },
  { id: 'clients', label: 'Clientes (CRM)', icon: Users, roles: ['ADMIN', 'GERENTE', 'PROJETISTA'] },
  { id: 'projects', label: 'Projetos (Kanban)', icon: Building2, roles: ['ADMIN', 'GERENTE', 'PROJETISTA'] },
  { id: 'financial', label: 'Financeiro Caixa', icon: Landmark, roles: ['ADMIN', 'GERENTE'] },
  { id: 'stock', label: 'Estoque', icon: Package, roles: ['ADMIN', 'GERENTE', 'ESTOQUE', 'PROJETISTA'] },
  { id: 'purchases', label: 'Compras', icon: ShoppingCart, roles: ['ADMIN', 'GERENTE', 'ESTOQUE'] },
  { id: 'reports', label: 'Relatórios', icon: FileBarChart, roles: ['ADMIN', 'GERENTE'] },
  { id: 'calendar', label: 'Agenda', icon: CalendarDays, roles: ['ADMIN', 'GERENTE', 'PROJETISTA'] },
  { id: 'novidades', label: 'Novidades', icon: Sparkles, roles: ['ADMIN', 'GERENTE', 'ESTOQUE', 'PROJETISTA'] },
  { id: 'users', label: 'Acessos & Ti', icon: Shield, roles: ['ADMIN'] },
];

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('eme_token'));
  const [currentUser, setCurrentUser] = useState<UserType | null>(() => {
    const raw = localStorage.getItem('eme_user');
    return raw ? JSON.parse(raw) : null;
  });

  // Login form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // Layout navigation states
  const [activeTab, setActiveTab] = useState<TabId>(() => {
    // Determine default tab based on role if logged in
    const raw = localStorage.getItem('eme_user');
    if (raw) {
      const u = JSON.parse(raw) as UserType;
      if (u.role === 'ESTOQUE') return 'stock';
    }
    return 'dashboard';
  });
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('eme_theme');
    if (stored === 'light' || stored === 'dark') return stored;
    return 'dark';
  });

  useEffect(() => {
    localStorage.setItem('eme_theme', theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  const ThemeIcon = theme === 'dark' ? Sun : Moon;

  // Validate active session
  useEffect(() => {
    if (token) {
      authService.me()
        .then((profile) => {
          setCurrentUser(profile);
          localStorage.setItem('eme_user', JSON.stringify(profile));
          
          // Guard active tab based on role privileges
          const tabAllowed = TABS.find(t => t.id === activeTab)?.roles.includes(profile.role);
          if (!tabAllowed) {
            setActiveTab(profile.role === 'ESTOQUE' ? 'stock' : 'dashboard');
          }
        })
        .catch((err) => {
          console.error('Sessão expirada ou inválida:', err);
          handleLogout();
        });
    }
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);

    if (!username || !password) {
      setLoginError('Informe o nome de usuário e a senha para autenticar.');
      setLoginLoading(false);
      return;
    }

    try {
      const data = await authService.login(username, password);
      setToken(data.token);
      setCurrentUser(data.user);
      
      // Auto-focus preferred areas on login
      if (data.user.role === 'ESTOQUE') {
        setActiveTab('stock');
      } else {
        setActiveTab('dashboard');
      }
    } catch (err: any) {
      setLoginError(getApiErrorMessage(err, 'Acesso incorreto ou indisponível.'));
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setToken(null);
    setCurrentUser(null);
    setUsername('');
    setPassword('');
  };

  // Render Login Layout
  if (!token || !currentUser) {
    return (
      <div className={`theme-${theme} min-h-screen relative flex items-center justify-center bg-radial from-neutral-950 via-zinc-950 to-neutral-950 px-4 py-12`}>
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-red-800 via-red-650 to-red-900 shadow"></div>
        <button
          type="button"
          onClick={toggleTheme}
          className="absolute right-5 top-5 p-2.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition cursor-pointer"
          title={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'}
        >
          <ThemeIcon className="w-4 h-4" />
        </button>

        <div className="w-full max-w-md space-y-8">
          
          {/* Top Logo branding */}
          <div className="text-center">
            <img src={logoFull} alt="EME Móveis" className="h-20 mx-auto object-contain" />
            <p className="text-xs uppercase font-mono tracking-[0.2em] text-zinc-500 mt-3">
              Ateliê de Ambientes Digitais & Planejados
            </p>
          </div>

          {/* Login Card Form */}
          <div className="glass-panel p-8 rounded-xl border border-zinc-900/80 shadow-2xl relative overflow-hidden backdrop-blur-md">
            <div className="absolute top-0 right-0 w-32 h-32 bg-red-600/5 blur-3xl rounded-full"></div>

            <div className="mb-6">
              <h2 className="text-lg font-medium text-white font-sans">Acesso Corporativo</h2>
              <p className="text-xs text-zinc-400 font-mono mt-0.5">Informe suas credenciais para gerenciar a marcenaria</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-4">
              
              {loginError && (
                <div className="p-3 bg-red-950/40 border border-red-900/50 text-red-400 text-xs rounded font-mono">
                  {loginError}
                </div>
              )}

              {/* Username Input */}
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Usuário de Rede</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
                  <input 
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase())}
                    placeholder="Ex: admin, gerente, estoque"
                    className="w-full bg-zinc-900/80 border border-zinc-850 focus:border-red-650 text-white pl-10 pr-4 py-2 text-sm rounded focus:outline-none transition font-sans"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="space-y-1">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Senha de Acesso</label>
                <div className="relative">
                  <input 
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Sua senha corporativa"
                    className="w-full bg-zinc-900/80 border border-zinc-c800 focus:border-red-650 text-white pl-3.5 pr-10 py-2 text-sm rounded focus:outline-none transition font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Sign In CTA */}
              <button 
                type="submit"
                disabled={loginLoading}
                className="w-full mt-6 flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold text-sm py-2.5 rounded transition shadow-md active:scale-[0.98] disabled:opacity-50 cursor-pointer font-sans"
              >
                {loginLoading ? 'Conectando rede...' : 'Acessar Console'}
                <ArrowRight className="w-4 h-4" />
              </button>

            </form>

          </div>

          {/* Aesthetic credentials footer */}
          <p className="text-center text-[10px] text-zinc-600 font-mono tracking-wider">
            EME MÓVEIS INDUSTRIAL S/A &copy; 2026 — TODOS OS DIREITOS RESERVADOS.
          </p>

        </div>
      </div>
    );
  }

  // Filter tabs allowed for current employee role
  const allowedTabs = TABS.filter(t => t.roles.includes(currentUser.role));

  return (
    <div className={`theme-${theme} min-h-screen flex flex-col md:flex-row bg-zinc-955 text-zinc-100 selection:bg-red-800 select-none`}>
      
      {/* Sidebar Rail Menu */}
      <div className={`w-full md:w-64 bg-zinc-950 border-r border-zinc-900 flex flex-col justify-between shrink-0 transition-all z-20`}>
        
        <div>
          {/* Workspace Brand logo header */}
          <div className="p-5 border-b border-zinc-900 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <img src={logoIcon} alt="EME Móveis" className="w-9 h-9 object-contain shrink-0" />
              <div>
                <span className="font-serif text-white text-base tracking-wider font-bold">EME MÓVEIS</span>
                <span className="text-[9px] font-mono text-zinc-500 uppercase block leading-none">Internal System</span>
              </div>
            </div>
            
            <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
          </div>

          {/* Navigation Links list */}
          <nav className="p-4 space-y-1.5 font-sans">
            {allowedTabs.map((tab) => {
              const TabIcon = tab.icon;
              const isSelected = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3.5 px-4 py-3 rounded text-sm text-left font-medium transition duration-200 cursor-pointer ${
                    isSelected 
                      ? 'text-white active-link-glow font-bold' 
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900/40'
                  }`}
                >
                  <TabIcon className={`w-4 h-4 shrink-0 transition ${isSelected ? 'text-red-500' : 'text-zinc-500 group-hover:text-white'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Profile and Logout Actions footer */}
        <div className="p-4 border-t border-zinc-900 bg-zinc-950/60 font-sans">
          <div className="flex items-center gap-3 mb-4">
            <img 
              src={currentUser.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(currentUser.name)}&background=b91c1c&color=fff&size=150`} 
              alt={currentUser.name} 
              className="w-10 h-10 rounded-full border border-zinc-800 object-cover"
              referrerPolicy="no-referrer"
            />
            <div className="flex-1 w-full overflow-hidden">
              <h4 className="text-xs font-semibold text-white line-clamp-1">{currentUser.name}</h4>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                <span className="text-[10px] font-mono text-zinc-400 font-bold tracking-wide uppercase">
                  {currentUser.role}
                </span>
              </div>
            </div>
          </div>

          <button 
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 bg-zinc-900 hover:bg-red-950/40 text-xs font-mono font-semibold uppercase py-2.5 rounded border border-zinc-800 hover:text-red-400 transition cursor-pointer"
          >
            <Power className="w-3.5 h-3.5" /> Encerrar Sessão
          </button>
        </div>

      </div>

      {/* Main Panel Content Container */}
      <main className="flex-1 bg-neutral-950 flex flex-col min-h-screen">
        
        {/* Top Operational Status Header */}
        <header className="p-5 border-b border-zinc-900 flex justify-between items-center bg-zinc-950/30">
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
            <span>Área de Trabalho</span>
            <span>&raquo;</span>
            <span className="text-white font-bold">{TABS.find(t => t.id === activeTab)?.label}</span>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition cursor-pointer"
            title={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'}
          >
            <ThemeIcon className="w-4 h-4" />
          </button>
        </header>

        {/* Dynamic page rendering section */}
        <div className="p-6 md:p-8 flex-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              {activeTab === 'dashboard' && <DashboardView userRole={currentUser.role} />}
              {activeTab === 'clients' && <ClientsView userRole={currentUser.role} />}
              {activeTab === 'projects' && <ProjectsView userRole={currentUser.role} />}
              {activeTab === 'financial' && <FinancialView userRole={currentUser.role} />}
              {activeTab === 'stock' && <StockView userRole={currentUser.role} />}
              {activeTab === 'purchases' && <PurchasesView userRole={currentUser.role} />}
              {activeTab === 'reports' && <ReportsView userRole={currentUser.role} />}
              {activeTab === 'calendar' && <CalendarView userRole={currentUser.role} />}
              {activeTab === 'novidades' && <NovidadesView userRole={currentUser.role} />}
              {activeTab === 'users' && <UsersView currentUser={currentUser} />}
            </motion.div>
          </AnimatePresence>
        </div>

      </main>

    </div>
  );
}
