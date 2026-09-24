/**
 * Montagens — a agenda de montagem vista como lista, com equipe e local.
 *
 * Montagem NAO tem tabela propria: e um CalendarEvent de tipo MONTAGEM (com
 * `team` e `location`). Esta aba e a mesma coisa que a Agenda, mas recortada
 * para montagens e com filtro por equipe, que e como o cliente acompanha o
 * dia. Criar aqui cria o mesmo evento que apareceria na Agenda.
 */
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { CalendarDays, Loader2, MapPin, Pencil, Plus, Trash2, Users, X } from 'lucide-react';
import { calendarService, clientService, projectService, getApiErrorMessage } from '../services/api';
import { Client, Project } from '../types';

interface Montagem {
  id: string;
  title: string;
  description?: string;
  type: string;
  status: string;
  start_date: string;
  start_time?: string | null;
  project_id?: string | null;
  project_title?: string | null;
  client_id?: string | null;
  client_name?: string | null;
  team?: string | null;
  location?: string | null;
}

const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

const STATUS_TONE: Record<string, string> = {
  AGENDADO: 'text-zinc-300 border-zinc-700',
  CONFIRMADO: 'text-emerald-400 border-emerald-700',
  CONCLUIDO: 'text-zinc-500 border-zinc-800',
  CANCELADO: 'text-rose-500 border-red-800',
};

function dataBR(iso: string | null | undefined): string {
  if (!iso) return '—';
  return iso.slice(0, 10).split('-').reverse().join('/');
}

const hoje = new Date();

export default function AssemblyPanel() {
  const [year, setYear] = useState(hoje.getFullYear());
  const [month, setMonth] = useState(hoje.getMonth() + 1);
  const [equipe, setEquipe] = useState('');
  const [eventos, setEventos] = useState<Montagem[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [formAberto, setFormAberto] = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: '', start_date: hoje.toISOString().substring(0, 10), start_time: '',
    team: '', location: '', project_id: '', client_id: '', status: 'AGENDADO',
  });
  const [salvando, setSalvando] = useState(false);

  const carregar = () => {
    setLoading(true);
    setError('');
    calendarService
      .getAll(month, year)
      .then((todos: Montagem[]) => setEventos((todos || []).filter(e => e.type === 'MONTAGEM')))
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar as montagens.')))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, [month, year]);

  useEffect(() => {
    projectService.getAll().then(setProjects).catch(() => setProjects([]));
    clientService.getAll().then(setClients).catch(() => setClients([]));
  }, []);

  // Equipes vem dos proprios eventos: nao existe cadastro de equipe (decisao
  // do plano — texto livre), entao o filtro se monta com o que foi usado.
  const equipes = useMemo(
    () => [...new Set(eventos.map(e => (e.team || '').trim()).filter(Boolean))].sort(),
    [eventos],
  );

  const visiveis = useMemo(
    () => (equipe ? eventos.filter(e => (e.team || '').trim() === equipe) : eventos),
    [eventos, equipe],
  );

  const porData = useMemo(() => {
    const mapa = new Map<string, Montagem[]>();
    for (const e of visiveis) {
      const dia = (e.start_date || '').slice(0, 10);
      if (!mapa.has(dia)) mapa.set(dia, []);
      mapa.get(dia)!.push(e);
    }
    return [...mapa.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }, [visiveis]);

  const abrirNova = () => {
    setEditandoId(null);
    setForm({
      title: '', start_date: hoje.toISOString().substring(0, 10), start_time: '',
      team: '', location: '', project_id: '', client_id: '', status: 'AGENDADO',
    });
    setFormAberto(true);
  };

  const abrirEdicao = (m: Montagem) => {
    setEditandoId(m.id);
    setForm({
      title: m.title || '', start_date: (m.start_date || '').slice(0, 10),
      start_time: m.start_time || '', team: m.team || '', location: m.location || '',
      project_id: m.project_id || '', client_id: m.client_id || '', status: m.status || 'AGENDADO',
    });
    setFormAberto(true);
  };

  const salvar = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.start_date) {
      setError('Título e data são obrigatórios.');
      return;
    }
    setSalvando(true);
    setError('');
    const payload: any = { ...form, type: 'MONTAGEM' };
    for (const k of ['start_time', 'team', 'location', 'project_id', 'client_id']) {
      if (!payload[k]) delete payload[k];
    }
    try {
      if (editandoId) await calendarService.update(editandoId, payload);
      else await calendarService.create(payload);
      setFormAberto(false);
      setEditandoId(null);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar a montagem.'));
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (m: Montagem) => {
    if (!window.confirm(`Excluir a montagem "${m.title}"?`)) return;
    try {
      await calendarService.delete(m.id);
      carregar();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao excluir a montagem.'));
    }
  };

  return (
    <div className="space-y-5">
      {/* Filtros */}
      <div className="glass-panel p-4 rounded-lg flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Mês</label>
          <select value={month} onChange={e => setMonth(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            {MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Ano</label>
          <select value={year} onChange={e => setYear(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            {[year - 1, year, year + 1].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Equipe</label>
          <select value={equipe} onChange={e => setEquipe(e.target.value)}
            className="bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
            <option value="">Todas as equipes</option>
            {equipes.map(eq => <option key={eq} value={eq}>{eq}</option>)}
          </select>
        </div>
        <div className="ml-auto">
          <button onClick={abrirNova}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/50 border border-red-900/40 text-red-400 rounded text-xs font-mono uppercase transition cursor-pointer">
            <Plus className="w-3.5 h-3.5" /> Nova montagem
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {/* Formulario inline */}
      {formAberto && (
        <form onSubmit={salvar} className="glass-panel p-5 rounded-lg space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white font-sans">
              {editandoId ? 'Editar montagem' : 'Nova montagem'}
            </h3>
            <button type="button" onClick={() => { setFormAberto(false); setEditandoId(null); }}
              className="text-zinc-500 hover:text-white transition cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Título *</label>
              <input type="text" value={form.title} placeholder="Ex.: Montagem cozinha — cliente Silva"
                onChange={e => setForm({ ...form, title: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Equipe</label>
              <input type="text" value={form.team} placeholder="Ex.: Equipe A"
                onChange={e => setForm({ ...form, team: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Data *</label>
              <input type="date" value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Hora</label>
              <input type="time" value={form.start_time}
                onChange={e => setForm({ ...form, start_time: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Local</label>
              <input type="text" value={form.location} placeholder="Endereço da montagem"
                onChange={e => setForm({ ...form, location: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Status</label>
              <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="AGENDADO">Agendado</option>
                <option value="CONFIRMADO">Confirmado</option>
                <option value="CONCLUIDO">Concluído</option>
                <option value="CANCELADO">Cancelado</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Projeto</label>
              <select value={form.project_id} onChange={e => setForm({ ...form, project_id: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="">Nenhum</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">Cliente</label>
              <select value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-3 py-2 text-xs font-mono focus:outline-none">
                <option value="">Nenhum</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-zinc-900">
            <button type="button" onClick={() => { setFormAberto(false); setEditandoId(null); }}
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

      {/* Lista */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando montagens...</p>
        </div>
      ) : porData.length === 0 ? (
        <div className="glass-panel p-10 rounded-lg text-center">
          <CalendarDays className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
          <p className="text-sm text-zinc-300 font-mono">Nenhuma montagem no período.</p>
          <p className="text-xs text-zinc-500 font-mono mt-1">
            Montagens criadas aqui aparecem também na Agenda.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {porData.map(([dia, lista]) => (
            <div key={dia} className="glass-panel rounded-lg overflow-hidden">
              <div className="px-5 py-3 border-b border-zinc-900 flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-red-500" />
                <span className="text-sm font-semibold text-white font-sans">{dataBR(dia)}</span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  {lista.length} montagem(ns)
                </span>
              </div>
              <div className="divide-y divide-zinc-900">
                {lista.map(m => (
                  <div key={m.id} className="px-5 py-4 flex items-start justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {m.start_time && (
                          <span className="text-xs font-mono text-zinc-400">{m.start_time.slice(0, 5)}</span>
                        )}
                        <span className="text-sm font-semibold text-white font-sans">{m.title}</span>
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${STATUS_TONE[m.status] || STATUS_TONE.AGENDADO}`}>
                          {m.status}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-zinc-400 font-mono">
                        {m.team && (
                          <span className="flex items-center gap-1"><Users className="w-3 h-3" />{m.team}</span>
                        )}
                        {m.location && (
                          <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{m.location}</span>
                        )}
                        {m.project_title && <span>Projeto: {m.project_title}</span>}
                        {m.client_name && <span>Cliente: {m.client_name}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button onClick={() => abrirEdicao(m)} title="Editar"
                        className="p-1.5 text-zinc-400 hover:text-white transition cursor-pointer">
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => excluir(m)} title="Excluir"
                        className="p-1.5 text-zinc-400 hover:text-rose-500 transition cursor-pointer">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
