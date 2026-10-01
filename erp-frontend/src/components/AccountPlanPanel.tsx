/**
 * Plano de Contas: categorias DRE + contas importadas do sistema legado.
 *
 * Cada categoria tem codigo (1-14), indicador (CREDITO/DEBITO) e a faixa do
 * DRE ("Nao listar no DRE" = conta gerencial/transferencia). Cada conta tem um
 * codigo estruturado X.Y ("4.2") e pertence a uma categoria (prefixo X).
 * A gestao e ADMIN/GERENTE; leitura para todos.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Plus, Pencil, Trash2, X, RefreshCw, Loader2, BookOpen,
} from 'lucide-react';
import { accountPlanService, getApiErrorMessage } from '../services/api';
import { AccountPlanCategory, AccountPlanItem } from '../types';

const INDICATOR_COLORS: Record<string, string> = {
  CREDITO: 'text-emerald-400 border-emerald-900 bg-emerald-950/40',
  DEBITO: 'text-red-400 border-red-900 bg-red-950/40',
};

export default function AccountPlanPanel({ userRole }: { userRole: string }) {
  const [groups, setGroups] = useState<AccountPlanCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const canEdit = ['ADMIN', 'GERENTE'].includes(userRole);

  // Modal de categoria
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [editingCat, setEditingCat] = useState<AccountPlanCategory | null>(null);
  const [catForm, setCatForm] = useState({ code: '', description: '', indicator: 'DEBITO', dre_range: '' });

  // Modal de conta
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<AccountPlanItem | null>(null);
  const [planForm, setPlanForm] = useState({ code: '', structured_code: '', description: '', category_id: '' });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setGroups(await accountPlanService.grouped());
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao carregar o plano de contas.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNewCat = () => {
    if (!canEdit) return;
    setEditingCat(null);
    setCatForm({ code: '', description: '', indicator: 'DEBITO', dre_range: '' });
    setCatModalOpen(true);
  };

  const openEditCat = (cat: AccountPlanCategory) => {
    if (!canEdit) return;
    setEditingCat(cat);
    setCatForm({
      code: String(cat.code),
      description: cat.description,
      indicator: cat.indicator,
      dre_range: cat.dre_range || '',
    });
    setCatModalOpen(true);
  };

  const openNewPlan = () => {
    if (!canEdit) return;
    setEditingPlan(null);
    setPlanForm({ code: '', structured_code: '', description: '', category_id: groups[0]?.id || '' });
    setPlanModalOpen(true);
  };

  const openEditPlan = (plan: AccountPlanItem) => {
    if (!canEdit) return;
    setEditingPlan(plan);
    setPlanForm({
      code: String(plan.code),
      structured_code: plan.structured_code,
      description: plan.description,
      category_id: plan.category_id,
    });
    setPlanModalOpen(true);
  };

  const submitCat = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        code: Number(catForm.code),
        description: catForm.description,
        indicator: catForm.indicator,
        dre_range: catForm.dre_range,
      };
      if (editingCat) {
        await accountPlanService.updateCategory(editingCat.id, payload);
      } else {
        await accountPlanService.createCategory(payload);
      }
      setCatModalOpen(false);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar categoria.'));
    } finally {
      setSaving(false);
    }
  };

  const submitPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        code: Number(planForm.code),
        structured_code: planForm.structured_code,
        description: planForm.description,
        category_id: planForm.category_id,
      };
      if (editingPlan) {
        await accountPlanService.updatePlan(editingPlan.id, payload);
      } else {
        await accountPlanService.createPlan(payload);
      }
      setPlanModalOpen(false);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar conta.'));
    } finally {
      setSaving(false);
    }
  };

  const removeCat = async (cat: AccountPlanCategory) => {
    if (!window.confirm(`Excluir a categoria "${cat.description}"? A exclusão é bloqueada enquanto houver contas vinculadas.`)) return;
    setError('');
    try {
      await accountPlanService.removeCategory(cat.id);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir categoria.'));
    }
  };

  const removePlan = async (plan: AccountPlanItem) => {
    if (!window.confirm(`Excluir a conta "${plan.label}"? A exclusão é bloqueada se a conta já foi usada em lançamentos.`)) return;
    setError('');
    try {
      await accountPlanService.removePlan(plan.id);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir conta.'));
    }
  };

  const restoreSeed = async () => {
    if (!canEdit) return;
    if (!window.confirm('Restaurar o padrão importado? Adiciona as categorias e contas oficiais que ainda não existirem, sem apagar o que você já ajustou.')) return;
    setRestoring(true);
    setError('');
    try {
      await accountPlanService.reloadSeed();
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao restaurar o padrão.'));
    } finally {
      setRestoring(false);
    }
  };

  const totalPlans = groups.reduce((acc, g) => acc + (g.plans?.length || 0), 0);

  if (loading && groups.length === 0) {
    return (
      <div className="glass-panel p-10 rounded-lg flex items-center justify-center text-zinc-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Carregando plano de contas...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="glass-panel p-5 rounded-lg flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-red-400" /> Plano de Contas
          </h3>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            {groups.length} categorias · {totalPlans} contas · importado do sistema legado
          </p>
        </div>
        {canEdit && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={restoreSeed}
              disabled={restoring}
              className="px-3 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 text-xs transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              title="Adiciona o padrão oficial que ainda não existir"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${restoring ? 'animate-spin' : ''}`} /> Restaurar padrão
            </button>
            <button
              type="button"
              onClick={openNewCat}
              className="px-3 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs transition cursor-pointer flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Nova categoria
            </button>
            <button
              type="button"
              onClick={openNewPlan}
              className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded text-xs transition cursor-pointer flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Nova conta
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{error}</div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Categorias */}
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
            <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono">Categorias (faixas do DRE)</h4>
            <span className="text-[11px] text-zinc-500 font-mono">{groups.length}</span>
          </div>
          <div className="overflow-x-auto max-h-[55vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-zinc-950/95 z-10">
                <tr className="text-left text-[10px] text-zinc-500 uppercase tracking-wider font-mono">
                  <th className="px-4 py-2">Cód.</th>
                  <th className="px-4 py-2">Descrição</th>
                  <th className="px-4 py-2">Indicador</th>
                  <th className="px-4 py-2">Faixa no DRE</th>
                  <th className="px-4 py-2 text-right">#</th>
                  {canEdit && <th className="px-4 py-2 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {groups.map((cat) => (
                  <tr key={cat.id} className="border-t border-zinc-900 hover:bg-zinc-900/40">
                    <td className="px-4 py-2.5 font-mono text-zinc-300">{cat.code}</td>
                    <td className="px-4 py-2.5 text-zinc-200">{cat.description}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${INDICATOR_COLORS[cat.indicator] || 'text-zinc-400 border-zinc-800'}`}>
                        {cat.indicator}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-zinc-400">{cat.dre_range || '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-zinc-400">{cat.plans?.length || 0}</td>
                    {canEdit && (
                      <td className="px-4 py-2.5 text-right whitespace-nowrap">
                        <button type="button" onClick={() => openEditCat(cat)} className="text-zinc-500 hover:text-emerald-400 p-1 cursor-pointer" title="Editar">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button type="button" onClick={() => removeCat(cat)} className="text-zinc-500 hover:text-red-400 p-1 cursor-pointer" title="Excluir">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Contas */}
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
            <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono">Contas</h4>
            <span className="text-[11px] text-zinc-500 font-mono">{totalPlans}</span>
          </div>
          <div className="overflow-x-auto max-h-[55vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-zinc-950/95 z-10">
                <tr className="text-left text-[10px] text-zinc-500 uppercase tracking-wider font-mono">
                  <th className="px-4 py-2">Cód.</th>
                  <th className="px-4 py-2">Descrição</th>
                  <th className="px-4 py-2">Categoria</th>
                  {canEdit && <th className="px-4 py-2 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {groups.map((cat) => (
                  <React.Fragment key={cat.id}>
                    {(cat.plans || []).map((plan) => (
                      <tr key={plan.id} className="border-t border-zinc-900 hover:bg-zinc-900/40">
                        <td className="px-4 py-2.5 font-mono text-zinc-300 whitespace-nowrap">{plan.structured_code}</td>
                        <td className="px-4 py-2.5 text-zinc-200">{plan.description}</td>
                        <td className="px-4 py-2.5 text-xs text-zinc-400">{cat.code} – {cat.description}</td>
                        {canEdit && (
                          <td className="px-4 py-2.5 text-right whitespace-nowrap">
                            <button type="button" onClick={() => openEditPlan(plan)} className="text-zinc-500 hover:text-emerald-400 p-1 cursor-pointer" title="Editar">
                              <Pencil className="w-4 h-4" />
                            </button>
                            <button type="button" onClick={() => removePlan(plan)} className="text-zinc-500 hover:text-red-400 p-1 cursor-pointer" title="Excluir">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modal categoria */}
      {catModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setCatModalOpen(false)}>
          <div className="glass-panel w-full max-w-lg rounded-lg flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 shrink-0">
              <div>
                <h3 className="text-sm font-bold text-zinc-200">{editingCat ? 'Editar categoria' : 'Nova categoria'}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-0.5">Grupo do DRE / plano de contas</p>
              </div>
              <button type="button" onClick={() => setCatModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={submitCat} className="p-6 space-y-4 overflow-y-auto flex-1 overscroll-contain">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Código *</label>
                  <input
                    type="number" min={1} required value={catForm.code}
                    onChange={(e) => setCatForm({ ...catForm, code: e.target.value })}
                    placeholder="Ex: 15"
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Indicador *</label>
                  <select
                    value={catForm.indicator}
                    onChange={(e) => setCatForm({ ...catForm, indicator: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                  >
                    <option value="DEBITO">Débito</option>
                    <option value="CREDITO">Crédito</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Descrição *</label>
                <input
                  type="text" required value={catForm.description}
                  onChange={(e) => setCatForm({ ...catForm, description: e.target.value })}
                  placeholder="Ex: Gastos com Pessoal"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Faixa no DRE</label>
                <input
                  type="text" value={catForm.dre_range}
                  onChange={(e) => setCatForm({ ...catForm, dre_range: e.target.value })}
                  placeholder="Ex: Custos fixos — ou 'Não listar no DRE'"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                />
              </div>
              <button type="submit" disabled={saving}
                className="w-full py-3 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-sm font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2">
                {saving && <Loader2 className="w-4 h-4 animate-spin" />} {editingCat ? 'Salvar alterações' : 'Criar categoria'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Modal conta */}
      {planModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setPlanModalOpen(false)}>
          <div className="glass-panel w-full max-w-lg rounded-lg flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 shrink-0">
              <div>
                <h3 className="text-sm font-bold text-zinc-200">{editingPlan ? 'Editar conta' : 'Nova conta'}</h3>
                <p className="text-xs text-zinc-400 font-mono mt-0.5">Código estruturado no formato X.Y</p>
              </div>
              <button type="button" onClick={() => setPlanModalOpen(false)} className="text-zinc-500 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={submitPlan} className="p-6 space-y-4 overflow-y-auto flex-1 overscroll-contain">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Código estruturado *</label>
                  <input
                    type="text" required value={planForm.structured_code}
                    onChange={(e) => setPlanForm({ ...planForm, structured_code: e.target.value })}
                    placeholder="Ex: 4.2"
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Código sequencial *</label>
                  <input
                    type="number" min={1} required value={planForm.code}
                    onChange={(e) => setPlanForm({ ...planForm, code: e.target.value })}
                    placeholder="Ex: 55"
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Descrição *</label>
                <input
                  type="text" required value={planForm.description}
                  onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })}
                  placeholder="Ex: Matéria-prima"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Categoria *</label>
                <select
                  required value={planForm.category_id}
                  onChange={(e) => setPlanForm({ ...planForm, category_id: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                >
                  <option value="" disabled>Selecione...</option>
                  {groups.map((cat) => (
                    <option key={cat.id} value={cat.id}>{cat.code} – {cat.description}</option>
                  ))}
                </select>
              </div>
              <button type="submit" disabled={saving}
                className="w-full py-3 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-sm font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2">
                {saving && <Loader2 className="w-4 h-4 animate-spin" />} {editingPlan ? 'Salvar alterações' : 'Criar conta'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}