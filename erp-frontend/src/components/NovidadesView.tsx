import React, { useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, RefreshCw, Sparkles, Send, X } from 'lucide-react';
import { changelogService, getApiErrorMessage } from '../services/api';
import { ChangelogEntry } from '../types';

interface NovidadesViewProps {
  userRole: string;
}

const CATEGORY_META: Record<string, { label: string; cls: string }> = {
  NOVIDADE: { label: 'Novidade', cls: 'bg-sky-500/20 text-sky-700 border-sky-400/40 dark:text-sky-300' },
  MELHORIA: { label: 'Melhoria', cls: 'bg-emerald-500/20 text-emerald-700 border-emerald-400/40 dark:text-emerald-300' },
  CORRECAO: { label: 'Correção', cls: 'bg-amber-500/20 text-amber-700 border-amber-400/40 dark:text-amber-300' },
  GERAL: { label: 'Geral', cls: 'bg-zinc-500/20 text-zinc-600 border-zinc-400/40 dark:text-zinc-300' },
};

const CATEGORY_OPTIONS = [
  { value: 'NOVIDADE', label: 'Novidade' },
  { value: 'MELHORIA', label: 'Melhoria' },
  { value: 'CORRECAO', label: 'Correção' },
  { value: 'GERAL', label: 'Geral' },
];

function formatDateBR(value: string): string {
  if (!value) return '';
  const d = new Date(value + 'T12:00:00');
  if (isNaN(d.getTime())) return value;
  return d.toLocaleDateString('pt-BR');
}

const EMPTY_FORM = {
  title: '',
  content: '',
  category: 'GERAL',
  entry_date: new Date().toISOString().substring(0, 10),
};

export default function NovidadesView({ userRole }: NovidadesViewProps) {
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ChangelogEntry | null>(null);
  const [formData, setFormData] = useState({ ...EMPTY_FORM });
  const [submitError, setSubmitError] = useState('');
  const [saving, setSaving] = useState(false);

  const canManage = userRole === 'ADMIN';

  const loadEntries = async () => {
    setLoading(true);
    setLoadError('');
    try {
      setEntries(await changelogService.list());
    } catch (err) {
      setLoadError(getApiErrorMessage(err, 'Erro ao carregar novidades.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntries();
  }, []);

  const handleOpenCreate = () => {
    setEditingEntry(null);
    setFormData({ ...EMPTY_FORM });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (entry: ChangelogEntry) => {
    setEditingEntry(entry);
    setFormData({
      title: entry.title,
      content: entry.content || '',
      category: entry.category,
      entry_date: entry.entry_date ? entry.entry_date.substring(0, 10) : EMPTY_FORM.entry_date,
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    if (!formData.title.trim()) {
      setSubmitError('O título é obrigatório.');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        title: formData.title.trim(),
        content: formData.content,
        category: formData.category,
        entry_date: formData.entry_date,
      };
      if (editingEntry) {
        await changelogService.update(editingEntry.id, payload);
      } else {
        await changelogService.create(payload);
      }
      setIsModalOpen(false);
      loadEntries();
    } catch (err) {
      setSubmitError(getApiErrorMessage(err, 'Erro ao salvar a novidade.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (entry: ChangelogEntry) => {
    if (!window.confirm('Deseja mesmo excluir esta novidade?')) return;
    try {
      await changelogService.remove(entry.id);
      loadEntries();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao excluir a novidade.'));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-white tracking-wide">Novidades</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">
            Atualizações e mudanças do sistema, registradas em cards.
          </p>
        </div>
        {canManage && (
          <button
            onClick={handleOpenCreate}
            className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded shadow-md flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Nova Novidade
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando novidades...</p>
        </div>
      ) : loadError ? (
        <div className="glass-panel p-6 rounded-lg text-center">
          <p className="text-sm text-red-400 font-mono">{loadError}</p>
          <button
            onClick={loadEntries}
            className="mt-3 px-4 py-2 text-xs bg-zinc-900 text-zinc-300 rounded border border-zinc-800 cursor-pointer hover:text-white"
          >
            Tentar novamente
          </button>
        </div>
      ) : entries.length === 0 ? (
        <div className="glass-panel p-10 rounded-lg flex flex-col items-center justify-center text-center">
          <Sparkles className="w-10 h-10 text-zinc-600 mb-3" />
          <p className="text-zinc-400 font-mono text-sm">Nenhuma novidade registrada ainda.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {entries.map((entry) => {
            const meta = CATEGORY_META[entry.category] || CATEGORY_META.GERAL;
            return (
              <div
                key={entry.id}
                className="glass-panel rounded-lg p-5 flex flex-col gap-3 border-t-2 border-t-red-800/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border shrink-0 ${meta.cls}`}>
                    {meta.label}
                  </span>
                  {canManage && (
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => handleOpenEdit(entry)}
                        className="p-1 text-zinc-500 hover:text-sky-400 cursor-pointer"
                        title="Editar novidade"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(entry)}
                        className="p-1 text-zinc-500 hover:text-red-400 cursor-pointer"
                        title="Excluir novidade"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
                <h3 className="text-base font-semibold text-white font-sans">{entry.title}</h3>
                {entry.content && (
                  <p className="text-sm text-zinc-300 whitespace-pre-wrap font-sans">{entry.content}</p>
                )}
                <p className="text-[11px] font-mono text-zinc-500 mt-auto pt-2 border-t border-zinc-900">
                  {formatDateBR(entry.entry_date)}
                  {entry.created_by ? ' · por ' + entry.created_by : ''}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal criar/editar */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
            <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 p-5 border-b border-zinc-800 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-red-500" />
                <h3 className="text-base font-serif font-semibold text-white">
                  {editingEntry ? 'Editar Novidade' : 'Nova Novidade'}
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-zinc-500 hover:text-white cursor-pointer"
                title="Fechar"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">
                  {submitError}
                </div>
              )}
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Título *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Ex: Nova aba Produtos na negociação"
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Conteúdo</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  rows={4}
                  placeholder="Descreva o que mudou..."
                  className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 resize-none"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Categoria</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600"
                  >
                    {CATEGORY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block">Data</label>
                  <input
                    type="date"
                    value={formData.entry_date}
                    onChange={(e) => setFormData({ ...formData, entry_date: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-800 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-600 font-mono"
                  />
                </div>
              </div>
              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-300 hover:text-white rounded border border-zinc-800 cursor-pointer font-mono"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold flex items-center gap-1.5 transition active:scale-95 cursor-pointer disabled:opacity-50"
                >
                  <Send className="w-4 h-4" /> {editingEntry ? 'Salvar Alterações' : 'Publicar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}