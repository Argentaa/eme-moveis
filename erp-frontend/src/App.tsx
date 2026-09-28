import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Building2, Layers, Users, Landmark, Package, Shield, FileBarChart, CalendarDays, Sparkles,
  Power, Menu, X, User, ArrowRight, HelpCircle, Eye, EyeOff, Moon, Sun, ShoppingCart, Wrench, Truck, MessageCircle
} from 'lucide-react';

// Assets
import logoFull from './assets/logo-eme-full.png';
import logoIcon from './assets/logo-eme-icon.png';

// Services
import { authService, changelogService, getApiErrorMessage } from './services/api';
import { User as UserType } from './types';

// Views
import DashboardView from './components/DashboardView';
import ClientsView from './components/ClientsView';
import ProjectsView from './components/ProjectsView';
import FinancialView from './components/FinancialView';
import StockView from './components/StockView';
import PurchasesView from './components/PurchasesView';
import SuppliersView from './components/SuppliersView';
import TicketsView from './components/TicketsView';
import WhatsappView from './components/WhatsappView';
import UsersView from './components/UsersView';
import ReportsView from './components/ReportsView';
import CalendarView from './components/CalendarView';
import NovidadesView from './components/NovidadesView';

type TabId = 'dashboard' | 'clients' | 'suppliers' | 'projects' | 'financial' | 'stock' | 'purchases' | 'tickets' | 'whatsapp' | 'users' | 'reports' | 'calendar' | 'novidades';
type ThemeMode = 'dark' | 'light';

const TAB_STORAGE_KEY = 'eme_tab';

/** Leitura tolerante do localStorage: um valor corrompido nao pode derrubar o app no boot. */
function readStoredUser(): UserType | null {
  const raw = localStorage.getItem('eme_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserType;
  } catch {
    localStorage.removeItem('eme_user');
    return null;
  }
}

function isTabId(value: string | null): value is TabId {
  return !!value && TABS.some(t => t.id === value);
}

interface TabItem {
  id: TabId;
  label: string;
  icon: React.ComponentType<any>;
  roles: string[];
}

const TABS: TabItem[] = [
  { id: 'dashboard', label: 'Dashboard Executivo', icon: Layers, roles: ['ADMIN', 'GERENTE', 'ESTOQUE'] },
  { id: 'clients', label: 'Comercial', icon: Users, roles: ['ADMIN', 'GERENTE', 'PROJETISTA'] },
  { id: 'financial', label: 'Financeiro', icon: Landmark, roles: ['ADMIN', 'GERENTE'] },
  { id: 'projects', label: 'Produção', icon: Building2, roles: ['ADMIN', 'GERENTE', 'PROJETISTA'] },
  { id: 'suppliers', label: 'Clientes/Fornecedores', icon: Truck, roles: ['ADMIN', 'GERENTE', 'ESTOQUE'] },
  { id: 'stock', label: 'Estoque', icon: Package, roles: ['ADMIN', 'GERENTE', 'ESTOQUE', 'PROJETISTA'] },
  { id: 'purchases', label: 'Compras', icon: ShoppingCart, roles: ['ADMIN', 'GERENTE', 'ESTOQUE'] },
  { id: 'tickets', label: 'Pós-venda', icon: Wrench, roles: ['ADMIN', 'GERENTE'] },
  { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, roles: ['ADMIN', 'GERENTE'] },
  { id: 'reports', label: 'Relatórios', icon: FileBarChart, roles: ['ADMIN', 'GERENTE'] },
  { id: 'calendar', label: 'Agenda', icon: CalendarDays, roles: ['ADMIN', 'GERENTE', 'PROJETISTA'] },
  { id: 'novidades', label: 'Novidades', icon: Sparkles, roles: ['ADMIN', 'GERENTE', 'ESTOQUE', 'PROJETISTA'] },
  { id: 'users', label: 'Acessos & Ti', icon: Shield, roles: ['ADMIN'] },
];

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('eme_token'));
  const [currentUser, setCurrentUser] = useState<UserType | null>(() => readStoredUser());

  // Login form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // Layout navigation states
  const [activeTab, setActiveTab] = useState<TabId>(() => {
    // Restaura a ultima aba usada (sobrevive a reload / nova aba).
    const stored = localStorage.getItem(TAB_STORAGE_KEY);
    if (isTabId(stored)) return stored;
    // Sem aba salva: default por perfil
    const u = readStoredUser();
    if (u?.role === 'ESTOQUE') return 'stock';
    return 'dashboard';
  });
  // Menu lateral no mobile: no desktop a sidebar e sempre visivel (md:),
  // entao este estado so governa a gaveta em telas pequenas.
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [unreadNews, setUnreadNews] = useState(0);

  // Badge de novidades nao lidas (por usuario). Revalida quando a sessao muda.
  useEffect(() => {
    if (!token) {
      setUnreadNews(0);
      return;
    }
    let active = true;
    changelogService.unreadCount()
      .then((r) => { if (active) setUnreadNews(r.unread || 0); })
      .catch(() => { if (active) setUnreadNews(0); });
    return () => { active = false; };
  }, [token]);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('eme_theme');
    if (stored === 'light' || stored === 'dark') return stored;
    return 'dark';
  });

  useEffect(() => {
    localStorage.setItem('eme_theme', theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(TAB_STORAGE_KEY, activeTab);
  }, [activeTab]);

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
          <div className="glass-panel p-8 rounded-xl border border-zinc-900/80 shadow-2xl relative overflow-hidden">
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
      
      {/* Backdrop da gaveta: so no mobile, fecha ao toque */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Rail Menu — gaveta no mobile, coluna fixa no desktop */}
      <div className={`fixed md:static inset-y-0 left-0 w-72 md:w-64 bg-zinc-950 border-r border-zinc-900 flex flex-col justify-between shrink-0 overflow-y-auto overscroll-contain transition-transform duration-200 md:transition-none z-40 md:z-20 ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        
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
            
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="md:hidden p-1.5 -mr-1 text-zinc-400 hover:text-white rounded border border-zinc-800 cursor-pointer"
                title="Fechar menu"
                aria-label="Fechar menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Navigation Links list */}
          <nav className="p-4 space-y-1.5 font-sans">
            {allowedTabs.map((tab) => {
              const TabIcon = tab.icon;
              const isSelected = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center gap-3.5 px-4 py-3 rounded text-sm text-left font-medium transition duration-200 cursor-pointer ${
                    isSelected 
                      ? 'text-white active-link-glow font-bold' 
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900/40'
                  }`}
                >
                  <TabIcon className={`w-4 h-4 shrink-0 transition ${isSelected ? 'text-red-500' : 'text-zinc-500 group-hover:text-white'}`} />
                  <span className="flex-1">{tab.label}</span>
                  {tab.id === 'novidades' && unreadNews > 0 && (
                    <span
                      className="shrink-0 min-w-[20px] h-5 px-1.5 rounded-full bg-red-600 text-white text-[10px] font-mono font-bold flex items-center justify-center"
                      title={`${unreadNews} novidade(s) nao lida(s)`}
                    >
                      {unreadNews > 99 ? '99+' : unreadNews}
                    </span>
                  )}
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
      <main className="flex-1 min-w-0 bg-neutral-950 flex flex-col min-h-screen">
        
        {/* Top Operational Status Header */}
        <header className="p-3 sm:p-5 border-b border-zinc-900 flex justify-between items-center gap-2 bg-zinc-950/30">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden shrink-0 p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition cursor-pointer"
              title="Abrir menu"
              aria-label="Abrir menu"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 min-w-0">
              <span className="hidden sm:inline">Área de Trabalho</span>
              <span className="hidden sm:inline">&raquo;</span>
              <span className="text-white font-bold truncate">{TABS.find(t => t.id === activeTab)?.label}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            className="shrink-0 p-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition cursor-pointer"
            title={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'}
          >
            <ThemeIcon className="w-4 h-4" />
          </button>
        </header>

        {/* Dynamic page rendering section */}
        <div className="p-3 sm:p-6 md:p-8 flex-1 min-w-0">
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
              {activeTab === 'suppliers' && <SuppliersView userRole={currentUser.role} />}
              {activeTab === 'projects' && <ProjectsView userRole={currentUser.role} />}
              {activeTab === 'financial' && <FinancialView userRole={currentUser.role} />}
              {activeTab === 'stock' && <StockView userRole={currentUser.role} />}
              {activeTab === 'purchases' && <PurchasesView userRole={currentUser.role} />}
              {activeTab === 'tickets' && <TicketsView userRole={currentUser.role} />}
              {activeTab === 'whatsapp' && <WhatsappView userRole={currentUser.role} />}
              {activeTab === 'reports' && <ReportsView userRole={currentUser.role} />}
              {activeTab === 'calendar' && <CalendarView userRole={currentUser.role} />}
              {activeTab === 'novidades' && <NovidadesView userRole={currentUser.role} onUnreadChange={setUnreadNews} />}
              {activeTab === 'users' && <UsersView currentUser={currentUser} />}
            </motion.div>
          </AnimatePresence>
        </div>

      </main>

    </div>
  );
}
