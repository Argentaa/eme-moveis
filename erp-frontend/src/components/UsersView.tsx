import React, { useEffect, useState } from 'react';
import { 
  Shield, UserPlus, RefreshCw, CheckCircle, Mail, Key, User, ShieldCheck, Trash2,
  Tag, Plus, Pencil, X, Save, Package, Landmark, Users as UsersIcon
} from 'lucide-react';
import { authService, stockService, getApiErrorMessage } from '../services/api';
import { User as UserType, Category } from '../types';

interface UsersViewProps {
  currentUser: UserType | null;
}

export default function UsersView({ currentUser }: UsersViewProps) {
  const [activeTab, setActiveTab] = useState<'users' | 'categories'>('users');

  const [users, setUsers] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Create User Form State
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    name: '',
    email: '',
    role: 'ESTOQUE' as 'ADMIN' | 'GERENTE' | 'ESTOQUE'
  });
  
  const [submitError, setSubmitError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Categories management state
  const [stockCategories, setStockCategories] = useState<Category[]>([]);
  const [financialCategories, setFinancialCategories] = useState<Category[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoryError, setCategoryError] = useState('');
  const [newStockCategoryName, setNewStockCategoryName] = useState('');
  const [newFinancialCategoryName, setNewFinancialCategoryName] = useState('');
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [editingCategoryName, setEditingCategoryName] = useState('');

  const loadCategories = async () => {
    setCategoriesLoading(true);
    try {
      const [stockCats, finCats] = await Promise.all([
        stockService.getCategories('STOCK'),
        stockService.getCategories('FINANCIAL'),
      ]);
      setStockCategories(stockCats);
      setFinancialCategories(finCats);
    } catch (err) {
      console.error('Erro ao carregar categorias:', err);
    } finally {
      setCategoriesLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'categories') {
      loadCategories();
    }
  }, [activeTab]);

  const handleCreateCategory = async (categoryType: 'STOCK' | 'FINANCIAL') => {
    const name = categoryType === 'STOCK' ? newStockCategoryName.trim() : newFinancialCategoryName.trim();
    if (!name) return;

    setCategoryError('');
    try {
      await stockService.createCategory({ name, category_type: categoryType });
      if (categoryType === 'STOCK') {
        setNewStockCategoryName('');
      } else {
        setNewFinancialCategoryName('');
      }
      loadCategories();
    } catch (err) {
      setCategoryError(getApiErrorMessage(err, 'Erro ao criar categoria.'));
    }
  };

  const handleStartEditCategory = (category: Category) => {
    setEditingCategoryId(category.id);
    setEditingCategoryName(category.name);
    setCategoryError('');
  };

  const handleCancelEditCategory = () => {
    setEditingCategoryId(null);
    setEditingCategoryName('');
  };

  const handleSaveEditCategory = async () => {
    if (!editingCategoryId || !editingCategoryName.trim()) return;

    setCategoryError('');
    try {
      await stockService.updateCategory(editingCategoryId, { name: editingCategoryName.trim() });
      setEditingCategoryId(null);
      setEditingCategoryName('');
      loadCategories();
    } catch (err) {
      setCategoryError(getApiErrorMessage(err, 'Erro ao editar categoria.'));
    }
  };

  const handleDeleteCategory = async (category: Category) => {
    if (!confirm(`Excluir a categoria "${category.name}"?`)) return;

    setCategoryError('');
    try {
      await stockService.deleteCategory(category.id);
      loadCategories();
    } catch (err) {
      setCategoryError(getApiErrorMessage(err, 'Erro ao excluir categoria.'));
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await authService.getUsers();
      setUsers(data);
    } catch (err) {
      console.error('Falha de leitura administrativa de usuários:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') {
      loadUsers();
    }
  }, [activeTab]);

  const handleOpenModal = () => {
    setFormData({
      username: '',
      password: '',
      name: '',
      email: '',
      role: 'ESTOQUE'
    });
    setSubmitError('');
    setSuccessMsg('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    setSuccessMsg('');

    if (!formData.username || !formData.password || !formData.name || !formData.email) {
      setSubmitError('Por favor, digite todas as informações cadastrais.');
      return;
    }

    try {
      await authService.createUser(formData);
      setSuccessMsg(`Usuário "${formData.name}" cadastrado com sucesso!`);
      setTimeout(() => {
        setIsModalOpen(false);
        loadUsers();
      }, 1500);
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, 'Erro ao registrar credencial de funcionário.'));
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (userId === currentUser?.id) {
      alert('Você não pode alterar sua própria função administrativa.');
      return;
    }

    try {
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole as any } : u));
      await authService.updateUserRole(userId, newRole);
    } catch (err) {
      console.error('Falha de alteração de permissões:', err);
      alert(getApiErrorMessage(err, 'Falha ao alterar permissão.'));
      loadUsers();
    }
  };

  const handleDeleteUser = async (userId: string, userName: string) => {
    if (userId === currentUser?.id) {
      alert('Você não pode excluir sua própria conta.');
      return;
    }

    const confirmed = window.confirm(
      `Tem certeza que deseja remover o acesso de "${userName}"?\n\nEsta ação não pode ser desfeita.`
    );
    if (!confirmed) return;

    try {
      await authService.deleteUser(userId);
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (err: any) {
      console.error('Falha ao remover usuário:', err);
      alert(getApiErrorMessage(err, 'Erro ao remover usuário.'));
    }
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Controle de Segurança & Acessos</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Console Administrativo de controle de chaves, permissões e categorias.</p>
        </div>

        {activeTab === 'users' && (
          <button 
            onClick={handleOpenModal}
            className="bg-red-655 hover:bg-red-700 text-white text-sm font-semibold px-4 py-2.5 rounded shadow shadow-lg flex items-center justify-center gap-1.5 transition active:scale-95 cursor-pointer bg-red-650"
          >
            <UserPlus className="w-4 h-4" /> Cadastrar Acesso
          </button>
        )}
      </div>

      {/* Sub-tabs selector */}
      <div className="flex gap-2 border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-mono uppercase tracking-wide transition cursor-pointer border-b-2 ${
            activeTab === 'users'
              ? 'text-white border-red-600'
              : 'text-zinc-500 border-transparent hover:text-zinc-300'
          }`}
        >
          <UsersIcon className="w-4 h-4" /> Usuários
        </button>
        <button
          onClick={() => setActiveTab('categories')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-mono uppercase tracking-wide transition cursor-pointer border-b-2 ${
            activeTab === 'categories'
              ? 'text-white border-red-600'
              : 'text-zinc-500 border-transparent hover:text-zinc-300'
          }`}
        >
          <Tag className="w-4 h-4" /> Categorias
        </button>
      </div>

      {activeTab === 'users' && (
      <>

      {/* Intro Panel alert */}
      <div className="p-4 bg-zinc-900/60 border border-zinc-c800 rounded-lg flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-xs font-mono uppercase text-red-500 font-bold">Diretiva de Acessos EME Móveis</p>
          <p className="text-xs text-zinc-400 leading-relaxed">
            As alterações feitas nesta central entram em vigor imediatamente nas sessões dos usuários. 
            O perfil <strong className="text-white">ADMIN</strong> detém acessos totais de auditoria e financeiro.
            O perfil <strong className="text-white">GERENTE</strong> detém acessos operacionais de clientes e projetos.
            O perfil <strong className="text-white">ESTOQUE</strong> monitora exclusivamente insumos e transferências de carga.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs font-semibold">Buscando perfis corporativos...</p>
        </div>
      ) : (
        /* Profiles Database Listing */
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                <tr>
                  <th className="py-4 px-6 font-normal">Colaborador</th>
                  <th className="py-4 px-6 font-normal">Nome de Usuário</th>
                  <th className="py-4 px-6 font-normal">Contatos</th>
                  <th className="py-4 px-6 font-normal">Nível de Permissão (Role)</th>
                  <th className="py-4 px-6 font-normal text-right">Ação Rápida de Cargo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {users.map((colaborador) => (
                  <tr key={colaborador.id} className="hover:bg-zinc-900/30 transition">
                    <td className="py-4 px-6 flex items-center gap-3">
                      <img 
                        src={colaborador.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(currentUser.name)}&background=b91c1c&color=fff&size=150`} 
                        alt={colaborador.name} 
                        className="w-10 h-10 rounded-full border border-zinc-800 object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div>
                        <div className="font-semibold text-white font-sans text-base flex items-center gap-1.5">
                          <span>{colaborador.name}</span>
                          {colaborador.id === currentUser?.id && (
                            <span className="text-[9px] font-mono text-red-400 uppercase bg-red-950/40 px-1 rounded border border-red-900/30">Você</span>
                          )}
                        </div>
                        <span className="text-xs text-zinc-500 font-mono">ID: {colaborador.id}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 font-mono text-xs text-white">
                      @{colaborador.username}
                    </td>
                    <td className="py-4 px-6 space-y-0.5">
                      <div className="flex items-center gap-1 text-xs text-zinc-400">
                        <Mail className="w-3.5 h-3.5 text-zinc-500" />
                        <span>{colaborador.email}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <span className={`inline-block px-2.5 py-0.5 text-xs font-mono font-semibold rounded border ${
                        colaborador.role === 'ADMIN' 
                          ? 'text-red-400 bg-red-950/40 border-red-900/40' 
                          : colaborador.role === 'GERENTE'
                          ? 'text-amber-400 bg-amber-950/40 border-amber-900/40'
                          : 'text-zinc-400 bg-zinc-900 border-zinc-800'
                      }`}>
                        {colaborador.role}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      {colaborador.id !== currentUser?.id ? (
                        <div className="flex items-center justify-end gap-2">
                          <select 
                            value={colaborador.role}
                            onChange={(e) => handleRoleChange(colaborador.id, e.target.value)}
                            className="bg-zinc-900 border border-zinc-800 text-xs rounded text-zinc-300 focus:outline-none focus:border-red-656 py-1 px-2.5 font-mono"
                          >
                            <option value="ESTOQUE">Mudar para ESTOQUE</option>
                            <option value="PROJETISTA">Mudar para PROJETISTA</option>
                            <option value="GERENTE">Mudar para GERENTE</option>
                            <option value="ADMIN">Mudar para ADMIN</option>
                          </select>
                          <button
                            onClick={() => handleDeleteUser(colaborador.id, colaborador.name)}
                            className="p-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-500 hover:text-red-400 hover:border-red-900/50 hover:bg-red-950/30 transition cursor-pointer"
                            title={`Remover acesso de ${colaborador.name}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-zinc-650 font-mono italic">Protegido</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      </>
      )}

      {activeTab === 'categories' && (
      <>

      {/* Intro Panel alert */}
      <div className="p-4 bg-zinc-900/60 border border-zinc-c800 rounded-lg flex items-start gap-3">
        <Tag className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-xs font-mono uppercase text-red-500 font-bold">Categorias do Sistema</p>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Categorias de <strong className="text-white">Estoque</strong> classificam os itens do estoque.
            Categorias <strong className="text-white">Financeiras</strong> classificam os lançamentos de caixa.
            Categorias com itens ou lançamentos vinculados não podem ser excluídas — apenas renomeadas.
          </p>
        </div>
      </div>

      {categoryError && (
        <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
          {categoryError}
        </div>
      )}

      {categoriesLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs font-semibold">Carregando categorias...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

          {/* Stock categories column */}
          <div className="glass-panel rounded-lg p-5 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <Package className="w-4 h-4 text-red-500" /> Categorias de Estoque
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newStockCategoryName}
                onChange={(e) => setNewStockCategoryName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCreateCategory('STOCK'); }}
                placeholder="Nova categoria de estoque..."
                className="flex-1 bg-zinc-900 border border-zinc-805 text-white rounded px-3.5 py-2.5 text-sm focus:outline-none focus:border-red-656"
              />
              <button
                onClick={() => handleCreateCategory('STOCK')}
                disabled={!newStockCategoryName.trim()}
                className="px-3.5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                title="Adicionar categoria"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1.5">
              {stockCategories.length === 0 && (
                <p className="text-xs text-zinc-500 font-mono py-3 text-center">Nenhuma categoria de estoque cadastrada.</p>
              )}
              {stockCategories.map(cat => (
                <div key={cat.id} className="flex items-center justify-between gap-2 bg-zinc-900/60 border border-zinc-850 rounded px-3.5 py-2.5">
                  {editingCategoryId === cat.id ? (
                    <>
                      <input
                        type="text"
                        value={editingCategoryName}
                        onChange={(e) => setEditingCategoryName(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleSaveEditCategory(); if (e.key === 'Escape') handleCancelEditCategory(); }}
                        autoFocus
                        className="flex-1 bg-zinc-950 border border-red-656 text-white rounded px-2.5 py-1.5 text-sm focus:outline-none"
                      />
                      <button onClick={handleSaveEditCategory} className="p-1.5 text-emerald-400 hover:text-emerald-300 cursor-pointer" title="Salvar">
                        <Save className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={handleCancelEditCategory} className="p-1.5 text-zinc-500 hover:text-white cursor-pointer" title="Cancelar">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="text-sm text-zinc-200 font-sans">{cat.name}</span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button onClick={() => handleStartEditCategory(cat)} className="p-1.5 text-zinc-500 hover:text-blue-400 cursor-pointer" title="Editar">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleDeleteCategory(cat)} className="p-1.5 text-zinc-500 hover:text-red-400 cursor-pointer" title="Excluir">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Financial categories column */}
          <div className="glass-panel rounded-lg p-5 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <Landmark className="w-4 h-4 text-red-500" /> Categorias Financeiras
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newFinancialCategoryName}
                onChange={(e) => setNewFinancialCategoryName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCreateCategory('FINANCIAL'); }}
                placeholder="Nova categoria financeira..."
                className="flex-1 bg-zinc-900 border border-zinc-805 text-white rounded px-3.5 py-2.5 text-sm focus:outline-none focus:border-red-656"
              />
              <button
                onClick={() => handleCreateCategory('FINANCIAL')}
                disabled={!newFinancialCategoryName.trim()}
                className="px-3.5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                title="Adicionar categoria"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1.5">
              {financialCategories.length === 0 && (
                <p className="text-xs text-zinc-500 font-mono py-3 text-center">Nenhuma categoria financeira cadastrada.</p>
              )}
              {financialCategories.map(cat => (
                <div key={cat.id} className="flex items-center justify-between gap-2 bg-zinc-900/60 border border-zinc-850 rounded px-3.5 py-2.5">
                  {editingCategoryId === cat.id ? (
                    <>
                      <input
                        type="text"
                        value={editingCategoryName}
                        onChange={(e) => setEditingCategoryName(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleSaveEditCategory(); if (e.key === 'Escape') handleCancelEditCategory(); }}
                        autoFocus
                        className="flex-1 bg-zinc-950 border border-red-656 text-white rounded px-2.5 py-1.5 text-sm focus:outline-none"
                      />
                      <button onClick={handleSaveEditCategory} className="p-1.5 text-emerald-400 hover:text-emerald-300 cursor-pointer" title="Salvar">
                        <Save className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={handleCancelEditCategory} className="p-1.5 text-zinc-500 hover:text-white cursor-pointer" title="Cancelar">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="text-sm text-zinc-200 font-sans">{cat.name}</span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button onClick={() => handleStartEditCategory(cat)} className="p-1.5 text-zinc-500 hover:text-blue-400 cursor-pointer" title="Editar">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleDeleteCategory(cat)} className="p-1.5 text-zinc-500 hover:text-red-400 cursor-pointer" title="Excluir">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      </>
      )}

      {/* New Login Account Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-800 shadow-2xl animate-in fade-in duration-200">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center">
              <div>
                <h3 className="text-base font-serif font-bold text-white">Atribuir Novo Acesso</h3>
                <p className="text-xs text-zinc-400 font-mono">Credenciais de segurança para colaboradores</p>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase cursor-pointer"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-7 space-y-6">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}

              {successMsg && (
                <div className="p-3 bg-emerald-950/50 border border-emerald-900 text-emerald-400 text-xs rounded font-mono">
                  {successMsg}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Nome Completo *</label>
                <input 
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Carlos Heitor Silva"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Endereço de E-mail *</label>
                <input 
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="carlos.h@ememoveis.com.br"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Username / Login *</label>
                  <input 
                    type="text"
                    required
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value.toLowerCase() })}
                    placeholder="carlos"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Senha Inicial *</label>
                  <input 
                    type="password"
                    required
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="******"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Nível de Permissão (Role) *</label>
                <select 
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value as any })}
                  className="w-full bg-zinc-900 border border-zinc-850 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                >
                  <option value="ESTOQUE">ESTOQUE (Acesso exclusivo ao estoque)</option>
                    <option value="PROJETISTA">PROJETISTA (Clientes, Projetos, Estoque e Agenda)</option>
                  <option value="GERENTE">GERENTE (Projetos, clientes, relatórios)</option>
                  <option value="ADMIN">ADMIN (Controle total de permissões/caixa)</option>
                </select>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800 font-sans mt-6">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-850 font-mono cursor-pointer"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer"
                >
                  Atribuir Credencial
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
