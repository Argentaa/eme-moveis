/**
 * Parceiros/Arquitetos — cadastro e ranking de quem indica.
 *
 * Antes disso o parceiro so existia como um select no cadastro do cliente e
 * como numero no relatorio: nao dava para cadastrar, corrigir telefone ou
 * desativar quem parou de indicar. O ranking vem do relatorio de parceiros,
 * ordenado por indicacoes e valor — nao e recalculado aqui.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { Building2, Loader2, Pencil, Plus, Trash2 } from 'lucide-react';
import { partnerService, reportService, getApiErrorMessage } from '../services/api';
import { Partner, ReportResult } from '../types';
import ReportPanel from './ReportPanel';

const fmt = (v: number) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const VAZIO = { name: '', office: '', phone: '', email: '', city: '', notes: '', active: true };

export default function PartnersPanel() {
  const [parceiros, setParceiros] = useState<Partner[]>([]);
  const [ranking, setRanking] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aberto, setAberto] = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({ ...VAZIO });

  const carregar = () => {
    setLoading(true);
    setError('');
    Promise.all([
      partnerService.list(),
      reportService.getReport('partners', {}).catch(() => null),
    ])
      .then(([ps, r]) => { setParceiros(ps); setRanking(r); })
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar os parceiros.')))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, []);

  const abrirNovo = () => { setEditandoId(null); setForm({ ...VAZIO }); setAberto(true); };
  const abrirEdicao = (p: Partner) => {
    setEditandoId(p.id);
    setForm({
      name: p.name, office: p.office || '', phone: p.phone || '', email: p.email || '',
      city: p.city || '', notes: p.notes || '', active: p.active,
    });
    setAberto(true);
  };

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    setError('');
    try {
      if (editandoId) await partnerService.update(editandoId, form as any);
      else await partnerService.create(form as any);
      setAberto(false);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar o parceiro.'));
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (p: Partner) => {
    if (!window.confirm(`Excluir ${p.name}? Os clientes já vinculados perdem a indicação.`)) return;
    try {
      await partnerService.remove(p.id);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir o parceiro.'));
    }
  };

  const ativos = parceiros.filter(p => p.active).length;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
            <Building2 className="w-3 h-3" /> Parceiros ativos
          </span>
          <p className="text-2xl font-bold font-sans text-white mt-2">{ativos}</p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">{parceiros.length} cadastrado(s)</p>
        </div>
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">
            Indicações no período
          </span>
          <p className="text-2xl font-bold font-sans text-white mt-2">
            {ranking ? (ranking.rows?.length ?? 0) : '—'}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">linhas no ranking</p>
        </div>
        <div className="glass-panel p-5 rounded-lg">
          <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono block">Total de parceiros</span>
          <p className="text-2xl font-bold font-sans text-zinc-400 mt-2">{parceiros.length}</p>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={abrirNovo}
          className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer">
          <Plus className="w-3.5 h-3.5" /> Novo parceiro
        </button>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {aberto && (
        <form onSubmit={salvar} className="glass-panel p-5 rounded-lg space-y-4">
          <h3 className="text-sm font-semibold text-white font-sans">
            {editandoId ? 'Editar parceiro' : 'Novo parceiro'}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Nome *</label>
              <input type="text" value={form.name} required
                onChange={e => setForm({ ...form, name: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Escritório</label>
              <input type="text" value={form.office}
                onChange={e => setForm({ ...form, office: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Cidade</label>
              <input type="text" value={form.city}
                onChange={e => setForm({ ...form, city: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Telefone</label>
              <input type="text" value={form.phone}
                onChange={e => setForm({ ...form, phone: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">E-mail</label>
              <input type="email" value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Situação</label>
              <select value={form.active ? '1' : '0'}
                onChange={e => setForm({ ...form, active: e.target.value === '1' })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="1">Ativo</option>
                <option value="0">Inativo</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-zinc-900">
            <button type="button" onClick={() => setAberto(false)}
              className="px-3.5 py-2 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-xs font-mono uppercase cursor-pointer">
              Cancelar
            </button>
            <button type="submit" disabled={salvando}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer disabled:opacity-60">
              {salvando && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Salvar
            </button>
          </div>
        </form>
      )}

      {loading && !parceiros.length ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando parceiros...</p>
        </div>
      ) : (
        <div className="glass-panel rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
                <tr>
                  <th className="py-3 px-5 font-normal">Nome</th>
                  <th className="py-3 px-5 font-normal">Escritório</th>
                  <th className="py-3 px-5 font-normal">Cidade</th>
                  <th className="py-3 px-5 font-normal">Contato</th>
                  <th className="py-3 px-5 font-normal">Situação</th>
                  <th className="py-3 px-5 font-normal text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {parceiros.map(p => (
                  <tr key={p.id} className={p.active ? 'hover:bg-zinc-900/40' : 'opacity-50'}>
                    <td className="py-3 px-5 font-sans text-xs">{p.name}</td>
                    <td className="py-3 px-5 font-sans text-xs text-zinc-400">{p.office || '—'}</td>
                    <td className="py-3 px-5 font-sans text-xs text-zinc-400">{p.city || '—'}</td>
                    <td className="py-3 px-5 font-mono text-[10px] text-zinc-400">
                      {p.phone || '—'}
                      {p.email && <span className="block">{p.email}</span>}
                    </td>
                    <td className="py-3 px-5 font-mono text-[10px]">
                      {p.active ? <span className="text-emerald-400">ATIVO</span>
                        : <span className="text-zinc-500">INATIVO</span>}
                    </td>
                    <td className="py-3 px-5">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => abrirEdicao(p)} title="Editar"
                          className="p-1.5 text-zinc-500 hover:text-white transition cursor-pointer">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => excluir(p)} title="Excluir"
                          className="p-1.5 text-zinc-500 hover:text-rose-500 transition cursor-pointer">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {parceiros.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-zinc-500 font-mono">
                      Nenhum parceiro cadastrado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {ranking && (
        <div>
          <h3 className="text-xs uppercase font-mono text-zinc-400 mb-2">Ranking de indicações</h3>
          <ReportPanel report={ranking} loading={loading} loadingLabel="Calculando ranking..." />
        </div>
      )}
    </div>
  );
}
