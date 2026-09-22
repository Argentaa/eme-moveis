import React, { useEffect, useState } from 'react';
import { 
  Package, AlertTriangle, Search, Plus, Trash2, ArrowUpRight, 
  ArrowDownRight, RefreshCw, Send, ListTodo, Layers, Landmark, User, ShieldAlert, Edit3
} from 'lucide-react';
import { stockService, getApiErrorMessage } from '../services/api';
import { StockItem, StockMovement, Category } from '../types';

interface StockViewProps {
  userRole: string;
}

export default function StockView({ userRole }: StockViewProps) {
  const [stock, setStock] = useState<StockItem[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  // Layout panel switcher
  const [currentTab, setCurrentTab] = useState<'ITEMS' | 'MOVEMENTS'>('ITEMS');

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('TODOS');

  // Modais Control
  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [isMovementModalOpen, setIsMovementModalOpen] = useState(false);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);

  // Creation forms states
  const [itemFormData, setItemFormData] = useState({
    name: '',
    sku: '',
    category_id: '',
    quantity: '0',
    min_quantity: '5',
    unit: 'chapa',
    price: '0',
    supplier: ''
  });

  const [movementFormData, setMovementFormData] = useState({
    item_id: '',
    type: 'SAIDA' as 'ENTRADA' | 'SAIDA',
    quantity: '1',
    reason: ''
  });

  const [categoryFormData, setCategoryFormData] = useState({
    name: '',
    description: ''
  });

  const [submitError, setSubmitError] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [st, movs, cats] = await Promise.all([
        stockService.getAll(),
        stockService.getMovements(),
        stockService.getCategories()
      ]);
      setStock(st);
      setMovements(movs);
      setCategories(cats);
    } catch (err) {
      console.error('Erro ao buscar almoxarifado de estoque:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenItemModal = () => {
    setItemFormData({
      name: '',
      sku: '',
      category_id: categories[0]?.id || '',
      quantity: '0',
      min_quantity: '5',
      unit: 'chapa',
      price: '0',
      supplier: ''
    });
    setSubmitError('');
    setIsItemModalOpen(true);
  };

  const handleOpenEditModal = (item: StockItem) => {
    setEditingItemId(item.id);
    setItemFormData({
      name: item.name,
      sku: item.sku,
      category_id: item.category_id,
      quantity: String(item.quantity),
      min_quantity: String(item.min_quantity),
      unit: item.unit,
      price: String(item.price || 0),
      supplier: item.supplier || ''
    });
    setSubmitError('');
    setIsItemModalOpen(true);
  };

  const handleOpenMovementModal = (item?: StockItem) => {
    setMovementFormData({
      item_id: item ? item.id : (stock[0]?.id || ''),
      type: 'SAIDA',
      quantity: '1',
      reason: ''
    });
    setSubmitError('');
    setIsMovementModalOpen(true);
  };

  const handleOpenCategoryModal = () => {
    setCategoryFormData({ name: '', description: '' });
    setSubmitError('');
    setIsCategoryModalOpen(true);
  };

  const handleSubmitItem = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    const { name, sku, category_id, quantity, min_quantity, unit, price, supplier } = itemFormData;
    if (!name || !sku || !category_id || !unit) {
      setSubmitError(categories.length === 0 ? 'Cadastre uma categoria antes de salvar o insumo.' : 'Por favor, preencha todos os campos obrigatórios.');
      return;
    }

    const payload = {
      name,
      sku,
      category_id,
      quantity: Number(quantity) || 0,
      min_quantity: Number(min_quantity) || 0,
      unit,
      price: Number(price) || 0,
      supplier: supplier || ''
    };

    try {
      if (editingItemId) {
        await stockService.update(editingItemId, payload);
      } else {
        await stockService.create(payload);
      }
      setIsItemModalOpen(false);
      setEditingItemId(null);
      loadData();
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, editingItemId ? 'Erro ao editar insumo.' : 'Erro ao criar insumo.'));
    }
  };

  const handleCreateMovement = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    const { item_id, type, quantity, reason } = movementFormData;
    if (!item_id || !type || !quantity || !reason) {
      setSubmitError('Preencha as informações da transferência.');
      return;
    }

    try {
      await stockService.createMovement({
        item_id,
        type,
        quantity: Number(quantity) || 0,
        reason
      });
      setIsMovementModalOpen(false);
      loadData();
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, 'Erro operacional na transferência.'));
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');

    if (!categoryFormData.name) {
      setSubmitError('O nome da categoria é obrigatório.');
      return;
    }

    try {
      const category = await stockService.createCategory(categoryFormData);
      setCategories(prev => [...prev, category].sort((a, b) => a.name.localeCompare(b.name)));
      setItemFormData(prev => ({ ...prev, category_id: prev.category_id || category.id }));
      setIsCategoryModalOpen(false);
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, 'Erro ao registrar categoria.'));
    }
  };

  const handleDeleteItem = async (id: string, name: string) => {
    if (!['ADMIN', 'GERENTE'].includes(userRole)) {
      alert('Acesso negado: Apenas administradores ou gerentes podem apagar itens da base de estoque.');
      return;
    }

    if (confirm(`Remover definitivamente o material "${name}" do estoque?`)) {
      try {
        await stockService.delete(id);
        loadData();
      } catch (err) {
        console.error('Falha de remoção de estoque:', err);
        alert(getApiErrorMessage(err, 'Falha ao remover item de estoque.'));
      }
    }
  };

  // Filter items
  const filteredStock = stock.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          item.sku.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          item.supplier.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'TODOS' || item.category_id === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6 font-sans">
      
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Estoque & Insumos</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Controle de entradas, saídas e saldo de estoque.</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Section view tabs switcher */}
          <div className="bg-zinc-900 border border-zinc-c800 p-1 rounded-md flex mr-2">
            <button 
              onClick={() => setCurrentTab('ITEMS')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition ${currentTab === 'ITEMS' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'} cursor-pointer`}
            >
              🛠️ Material Ativo
            </button>
            <button 
              onClick={() => setCurrentTab('MOVEMENTS')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition ${currentTab === 'MOVEMENTS' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'} cursor-pointer`}
            >
              📋 Histórico de movimentações
            </button>
          </div>

          <button 
            onClick={() => handleOpenMovementModal()}
            className="bg-zinc-900 border border-zinc-800 text-zinc-200 hover:text-white font-mono text-xs px-3.5 py-2.5 rounded hover:bg-zinc-850 cursor-pointer text-center"
          >
            ⇅ Lançar Movimentação
          </button>

          <button 
            onClick={handleOpenItemModal}
            className="bg-red-650 hover:bg-red-700 text-white text-xs font-semibold px-4 py-2.5 rounded shadow shadow-lg flex items-center gap-1 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" /> Novo material
          </button>

          <button 
            onClick={handleOpenCategoryModal}
            className="p-2.5 bg-zinc-900 border border-zinc-800 rounded text-zinc-400 hover:text-white cursor-pointer"
            title="Adicionar Categoria"
          >
            📁
          </button>
        </div>
      </div>

      {currentTab === 'ITEMS' ? (
        <>
          {/* Quick stock warning notifications bar */}
          {stock.some(item => item.quantity <= item.min_quantity) && (
            <div className="p-4 bg-red-950/20 border-l-4 border-l-red-600 rounded text-sm text-red-400 flex items-center gap-3 font-medium">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>Há materiais abaixo do nível crítico de segurança do estoque! Providencie a reposição imediata junto aos fornecedores selecionados.</span>
            </div>
          )}

          {/* Filtering Tools */}
          <div className="glass-panel p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center">
            
            {/* Search */}
            <div className="relative w-full md:flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
              <input 
                type="text"
                placeholder="Pesquisar por especificação do material, SKU ou fornecedor..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-805 text-white pl-10 pr-4 py-2 text-sm rounded focus:outline-none focus:border-red-656 font-sans"
              />
            </div>

            {/* Filter Category selection */}
            <div className="w-full md:w-auto flex items-center gap-2">
              <span className="text-xs text-zinc-400 font-mono whitespace-nowrap">Classificar:</span>
              <select 
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-zinc-900 border border-zinc-c800 text-white text-xs rounded px-3 py-1.5 focus:outline-none focus:border-red-656 font-mono"
              >
                <option value="TODOS">Todos os Insumos</option>
                {categories.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
              <p className="text-zinc-400 font-mono text-xs">Acessando estoque...</p>
            </div>
          ) : (
            /* Stock Catalog grid */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredStock.map((item) => {
                const isLow = item.quantity <= item.min_quantity;

                return (
                  <div 
                    key={item.id} 
                    className={`glass-panel p-5 rounded-lg flex flex-col justify-between border ${isLow ? 'border-red-950 glow-red' : 'border-zinc-900'}`}
                  >
                    <div>
                      {/* Classification Category & Unit */}
                      <div className="flex justify-between items-center text-[10px] font-mono uppercase text-zinc-500">
                        <span>{item.category_name}</span>
                        <span>Cod: {item.sku}</span>
                      </div>

                      {/* Material Spec */}
                      <h4 className="text-base font-semibold text-white mt-1.5 leading-tight">{item.name}</h4>
                      
                      {/* Supplier */}
                      <p className="text-xs text-zinc-400 mt-1">Fornecedor: <span className="text-zinc-300 font-medium">{item.supplier || 'Interno / Diversos'}</span></p>

                      {/* Cost */}
                      <div className="mt-4 font-mono text-zinc-400 text-xs">
                        Custo Unitário: <span className="text-emerald-400 font-bold">{item.price.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>
                      </div>
                    </div>

                    <div className="mt-5 pt-3.5 border-t border-zinc-900 flex justify-between items-end">
                      {/* Quantities */}
                      <div>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block">Volume Disponível</span>
                        <div className="flex items-baseline gap-1.5">
                          <span className={`text-2xl font-bold ${isLow ? 'text-red-500 animate-pulse' : 'text-white'}`}>
                            {item.quantity}
                          </span>
                          <span className="text-zinc-400 font-mono text-xs font-semibold">{item.unit}</span>
                        </div>
                        {isLow && (
                          <span className="text-[9px] font-mono text-red-400 bg-red-950/40 px-1.5 py-0.5 rounded border border-red-900/30 block mt-1">
                            Abaixo do mínimo ({item.min_quantity})
                          </span>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="space-x-1 whitespace-nowrap">
                        <button 
                          onClick={() => handleOpenMovementModal(item)}
                          className="px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 transition font-mono text-[10px] uppercase cursor-pointer"
                          title="Lançar entrada/saída"
                        >
                          Lançar Material
                        </button>
                        {['ADMIN', 'GERENTE'].includes(userRole) && (
                          <>
                            <button
                              onClick={() => handleOpenEditModal(item)}
                              className="p-1.5 bg-zinc-900 hover:bg-blue-950/40 text-zinc-500 hover:text-blue-400 rounded border border-zinc-800 transition cursor-pointer inline-flex"
                              title="Editar item"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                            <button 
                              onClick={() => handleDeleteItem(item.id, item.name)}
                              className="p-1.5 bg-zinc-900 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded border border-zinc-800 transition cursor-pointer inline-flex"
                              title="Excluir item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {filteredStock.length === 0 && (
                <div className="py-20 text-center text-zinc-500 font-mono col-span-full">
                  Nenhum material cadastrado coincide com a busca.
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        /* STOCK MOVEMENTS LOG LEDGER */
        <div className="glass-panel p-5 rounded-lg flex flex-col">
          <h3 className="text-lg font-serif text-white mb-4">Histórico Geral de Transferências</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300 font-mono">
              <thead className="text-xs uppercase text-zinc-500 bg-zinc-950/60 border-b border-zinc-905">
                <tr>
                  <th className="py-3 px-4 font-normal">Registro Data</th>
                  <th className="py-3 px-4 font-normal">Componente / Material</th>
                  <th className="py-3 px-4 font-normal text-center">Tipo</th>
                  <th className="py-3 px-4 font-normal text-right">Qtd</th>
                  <th className="py-3 px-4 font-normal">Justificativa Operacional / Motivo</th>
                  <th className="py-3 px-4 font-normal">Operador</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900 text-xs">
                {movements.map((mov) => (
                  <tr key={mov.id} className="hover:bg-zinc-900/30">
                    <td className="py-3 px-4 text-zinc-400 whitespace-nowrap">
                      {new Date(mov.date).toLocaleString('pt-BR')}
                    </td>
                    <td className="py-3 px-4 font-sans font-semibold text-white">
                      {mov.item_name}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-bold uppercase rounded-full ${
                        mov.type === 'ENTRADA' 
                          ? 'bg-emerald-950/30 text-emerald-400 border border-emerald-900/40' 
                          : 'bg-red-950/30 text-red-400 border border-red-900/40'
                      }`}>
                        {mov.type === 'ENTRADA' ? '+' : '-'} {mov.type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-white">
                      {mov.quantity}
                    </td>
                    <td className="py-3 px-4 text-zinc-300">
                      {mov.reason}
                    </td>
                    <td className="py-3 px-4 text-zinc-400 font-sans">
                      👤 {mov.created_by}
                    </td>
                  </tr>
                ))}

                {movements.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-zinc-500">
                      Nenhuma movimentação de estoque efetuada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Slideout Item Modal */}
      {isItemModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-bold text-white">{editingItemId ? "Editar Insumo" : "Adicionar Insumo ao Estoque"}</h3>
                <p className="text-xs text-zinc-400 font-mono">Cadastro de materiais e insumos do estoque</p>
              </div>
              <button 
                onClick={() => setIsItemModalOpen(false)}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleSubmitItem} className="p-7 space-y-6">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}

              <div className="space-y-2 font-sans">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Nome do Material / Especificação *</label>
                <input 
                  type="text"
                  required
                  value={itemFormData.name}
                  onChange={(e) => setItemFormData({ ...itemFormData, name: e.target.value })}
                  placeholder="Ex: MDF Duratex Couro 15mm"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2 font-sans">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Código SKU / Identificação *</label>
                  <input 
                    type="text"
                    required
                    value={itemFormData.sku}
                    onChange={(e) => setItemFormData({ ...itemFormData, sku: e.target.value })}
                    placeholder="Ex: MDF-COURO-15"
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2 font-sans">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Categoria de Destino *</label>
                  <select 
                    value={itemFormData.category_id}
                    disabled={categories.length === 0}
                    onChange={(e) => setItemFormData({ ...itemFormData, category_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  >
                    <option value="">
                      {categories.length === 0 ? 'Cadastre uma categoria primeiro' : '-- Selecione a categoria --'}
                    </option>
                    {categories.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  {categories.length === 0 && (
                    <button
                      type="button"
                      onClick={handleOpenCategoryModal}
                      className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-red-400 hover:text-red-300 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" /> Criar categoria
                    </button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 font-sans">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Qtde Inicial *</label>
                  <input 
                    type="number"
                    required
                    value={itemFormData.quantity}
                    onChange={(e) => setItemFormData({ ...itemFormData, quantity: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-850 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Estoque Crítico *</label>
                  <input 
                    type="number"
                    required
                    value={itemFormData.min_quantity}
                    onChange={(e) => setItemFormData({ ...itemFormData, min_quantity: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-850 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2 font-sans">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Unidade Medida</label>
                  <select 
                    value={itemFormData.unit}
                    onChange={(e) => setItemFormData({ ...itemFormData, unit: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-850 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  >
                    <option value="chapa">Chapa / Placa</option>
                    <option value="rolo">Rolo / Fita</option>
                    <option value="unidade">Unidade / Peça</option>
                    <option value="par">Par</option>
                    <option value="kg">Kg</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 font-sans">
                <div className="space-y-2 font-sans">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Preço de Custo (R$)</label>
                  <input 
                    type="number"
                    value={itemFormData.price}
                    onChange={(e) => setItemFormData({ ...itemFormData, price: e.target.value })}
                    placeholder="240"
                    className="w-full bg-zinc-900 border border-zinc-850 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>

                <div className="space-y-2 font-sans">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Fornecedor Preferencial</label>
                  <input 
                    type="text"
                    value={itemFormData.supplier}
                    onChange={(e) => setItemFormData({ ...itemFormData, supplier: e.target.value })}
                    placeholder="Ex: Duratex Brasil"
                    className="w-full bg-zinc-900 border border-zinc-850 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800 font-sans mt-6">
                <button 
                  type="button"
                  onClick={() => setIsItemModalOpen(false)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-850 font-mono cursor-pointer"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={categories.length === 0}
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {editingItemId ? "Salvar Alterações" : "Salvar Cadastro"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Slideout Movement Modal */}
      {isMovementModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-805 shadow-2xl">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-serif font-bold text-white">⇅ Registrar Movimentações</h3>
                <p className="text-xs text-zinc-400 font-mono">Registre entradas e saídas de materiais do estoque.</p>
              </div>
              <button 
                onClick={() => setIsMovementModalOpen(false)}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleCreateMovement} className="p-7 space-y-6 font-sans">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Insumo a Transferir *</label>
                <select 
                  value={movementFormData.item_id}
                  onChange={(e) => setMovementFormData({ ...movementFormData, item_id: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                >
                  <option value="">-- Selecione o item --</option>
                  {stock.map(item => (
                    <option key={item.id} value={item.id}>{item.name} (SKU: {item.sku}) - Qtd atual: {item.quantity} {item.unit}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Sentido de movimentação</label>
                  <select 
                    value={movementFormData.type}
                    onChange={(e) => setMovementFormData({ ...movementFormData, type: e.target.value as any })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  >
                    <option value="SAIDA">SAÍDA (Consumo fábrica / Perda)</option>
                    <option value="ENTRADA">ENTRADA (Compra / Reposição)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Quantidade</label>
                  <input 
                    type="number"
                    min="1"
                    required
                    value={movementFormData.quantity}
                    onChange={(e) => setMovementFormData({ ...movementFormData, quantity: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656 font-mono"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Justificativa *</label>
                <textarea 
                  required
                  value={movementFormData.reason}
                  onChange={(e) => setMovementFormData({ ...movementFormData, reason: e.target.value })}
                  placeholder="Ex: Utilizado na produção da cozinha do cliente João Silva ou Entrada referente à NF 10432 da fornecedor Duratex."
                  rows={3}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button 
                  type="button"
                  onClick={() => setIsMovementModalOpen(false)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-850 font-mono cursor-pointer"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="px-5 py-2 text-sm bg-red-655 hover:bg-red-700 text-white rounded font-semibold cursor-pointer"
                >
                  Salvar Movimentação
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Category Modal */}
      {isCategoryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden border border-zinc-805 shadow-2xl">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center">
              <div>
                <h3 className="text-base font-serif font-bold text-white">Registrar Nova Categoria</h3>
                <p className="text-xs text-zinc-400 font-mono">Crie categorias para facilitar o controle dos materiais.</p>
              </div>
              <button 
                onClick={() => setIsCategoryModalOpen(false)}
                className="text-zinc-500 hover:text-white font-mono text-xs uppercase cursor-pointer"
              >
                Sair
              </button>
            </div>

            <form onSubmit={handleCreateCategory} className="p-7 space-y-6 form-sans">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Nome da Categoria *</label>
                <input 
                  type="text"
                  required
                  value={categoryFormData.name}
                  onChange={(e) => setCategoryFormData({ ...categoryFormData, name: e.target.value })}
                  placeholder="Ex: Vidros / Perfis de Led"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Descrição</label>
                <textarea 
                  value={categoryFormData.description}
                  onChange={(e) => setCategoryFormData({ ...categoryFormData, description: e.target.value })}
                  placeholder="Descreva quais materiais pertencem a esta categoria."
                  rows={2}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-805 mt-6">
                <button 
                  type="button"
                  onClick={() => setIsCategoryModalOpen(false)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-805 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer"
                >
                  Criar Categoria
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
