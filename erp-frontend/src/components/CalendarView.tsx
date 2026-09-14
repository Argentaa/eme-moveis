import React, { useEffect, useState } from 'react';
import {
  ChevronLeft, ChevronRight, Plus, Calendar, Clock, User,
  Building2, Tag, CheckCircle, XCircle, RefreshCw, Edit3, Trash2, X, List
} from 'lucide-react';
import { calendarService, clientService, projectService, authService, getApiErrorMessage } from '../services/api';
import { Client, Project } from '../types';
import OverdueProjectsCard from './OverdueProjectsCard';

interface CalendarViewProps {
  userRole: string;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  MEDICAO: 'Medição',
  REUNIAO_CLIENTE: 'Reunião com Cliente',
  APROVACAO_PROJETO: 'Aprovação de Projeto',
  PRODUCAO: 'Produção',
  MONTAGEM: 'Montagem',
  ENTREGA: 'Entrega',
  ASSISTENCIA_TECNICA: 'Assistência Técnica',
  LIGACAO: 'Ligação',
  VISITA: 'Visita',
  WHATSAPP: 'WhatsApp',
  PERSONALIZADO: 'Evento Personalizado',
};

const EVENT_STATUS_LABELS: Record<string, string> = {
  AGENDADO: 'Agendado',
  CONFIRMADO: 'Confirmado',
  EM_ANDAMENTO: 'Em Andamento',
  CONCLUIDO: 'Concluído',
  CANCELADO: 'Cancelado',
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  MEDICAO: 'border-l-2 border-blue-500 bg-blue-500/25 text-blue-900',
  REUNIAO_CLIENTE: 'border-l-2 border-purple-500 bg-purple-500/25 text-purple-900',
  APROVACAO_PROJETO: 'border-l-2 border-amber-500 bg-amber-500/25 text-amber-900',
  PRODUCAO: 'border-l-2 border-orange-500 bg-orange-500/25 text-orange-900',
  MONTAGEM: 'border-l-2 border-red-500 bg-red-500/25 text-red-900',
  ENTREGA: 'border-l-2 border-emerald-500 bg-emerald-500/25 text-emerald-900',
  ASSISTENCIA_TECNICA: 'border-l-2 border-cyan-500 bg-cyan-500/25 text-cyan-900',
  LIGACAO: 'border-l-2 border-sky-500 bg-sky-500/25 text-sky-900',
  VISITA: 'border-l-2 border-teal-500 bg-teal-500/25 text-teal-900',
  WHATSAPP: 'border-l-2 border-green-500 bg-green-500/25 text-green-900',
  PERSONALIZADO: 'border-l-2 border-zinc-400 bg-zinc-400/25 text-zinc-800',
};

const EVENT_TYPE_DOT: Record<string, string> = {
  MEDICAO: 'bg-blue-500',
  REUNIAO_CLIENTE: 'bg-purple-500',
  APROVACAO_PROJETO: 'bg-amber-500',
  PRODUCAO: 'bg-orange-500',
  MONTAGEM: 'bg-red-500',
  ENTREGA: 'bg-emerald-500',
  ASSISTENCIA_TECNICA: 'bg-cyan-500',
  LIGACAO: 'bg-sky-500',
  VISITA: 'bg-teal-500',
  WHATSAPP: 'bg-green-500',
  PERSONALIZADO: 'bg-zinc-400',
};

const STATUS_COLORS: Record<string, string> = {
  AGENDADO: 'text-blue-800 bg-blue-500/20 border border-blue-500/40',
  CONFIRMADO: 'text-emerald-800 bg-emerald-500/20 border border-emerald-500/40',
  EM_ANDAMENTO: 'text-amber-800 bg-amber-500/20 border border-amber-500/40',
  CONCLUIDO: 'text-zinc-600 bg-zinc-500/20 border border-zinc-500/40',
  CANCELADO: 'text-red-800 bg-red-500/20 border border-red-500/40',
};

const EMPTY_FORM = {
  title: '',
  description: '',
  type: 'PERSONALIZADO',
  status: 'AGENDADO',
  start_date: new Date().toISOString().substring(0, 10),
  start_time: '',
  end_date: '',
  end_time: '',
  project_id: '',
  client_id: '',
  assigned_user_id: '',
  observations: '',
};

export default function CalendarView({ userRole }: CalendarViewProps) {
  const today = new Date();
  const [viewMode, setViewMode] = useState<'month' | 'list'>('month');
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ ...EMPTY_FORM });
  const [submitError, setSubmitError] = useState('');
  const canEdit = ['ADMIN', 'GERENTE'].includes(userRole);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const data = await calendarService.getAll(currentMonth, currentYear);
      setEvents(data);
    } catch (err) {
      console.error('Erro ao carregar agenda:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [currentMonth, currentYear]);

  useEffect(() => {
    Promise.all([
      clientService.getAll().catch(() => []),
      projectService.getAll().catch(() => []),
    ]).then(([cls, projs]) => {
      setClients(cls);
      setProjects(projs);
    });
  }, []);

  const prevMonth = () => {
    if (currentMonth === 1) { setCurrentMonth(12); setCurrentYear(y => y - 1); }
    else setCurrentMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (currentMonth === 12) { setCurrentMonth(1); setCurrentYear(y => y + 1); }
    else setCurrentMonth(m => m + 1);
  };

  const getDaysInMonth = (month: number, year: number) => new Date(year, month, 0).getDate();
  const getFirstDayOfMonth = (month: number, year: number) => new Date(year, month - 1, 1).getDay();

  const getEventsForDate = (dateStr: string) =>
    events.filter(e => e.start_date === dateStr || e.start_date?.substring(0, 10) === dateStr);

  const formatDateStr = (year: number, month: number, day: number) =>
    `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

  const selectedDateEvents = selectedDate ? getEventsForDate(selectedDate) : [];

  const MONTH_NAMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                       'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  const DAY_NAMES = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];

  const handleOpenCreate = (dateStr?: string) => {
    setEditingEventId(null);
    setFormData({ ...EMPTY_FORM, start_date: dateStr || today.toISOString().substring(0, 10) });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (event: any) => {
    setEditingEventId(event.id);
    setFormData({
      title: event.title || '',
      description: event.description || '',
      type: event.type || 'PERSONALIZADO',
      status: event.status || 'AGENDADO',
      start_date: event.start_date?.substring(0, 10) || '',
      start_time: event.start_time || '',
      end_date: event.end_date?.substring(0, 10) || '',
      end_time: event.end_time || '',
      project_id: event.project_id || '',
      client_id: event.client_id || '',
      assigned_user_id: event.assigned_user_id || '',
      observations: event.observations || '',
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    if (!formData.title || !formData.start_date) {
      setSubmitError('Título e data de início são obrigatórios.');
      return;
    }
    try {
      const payload: any = { ...formData };
      if (!payload.project_id) delete payload.project_id;
      if (!payload.client_id) delete payload.client_id;
      if (!payload.assigned_user_id) delete payload.assigned_user_id;
      if (!payload.end_date) delete payload.end_date;
      if (!payload.start_time) delete payload.start_time;
      if (!payload.end_time) delete payload.end_time;
      if (editingEventId) {
        await calendarService.update(editingEventId, payload);
      } else {
        await calendarService.create(payload);
      }
      setIsModalOpen(false);
      setEditingEventId(null);
      loadEvents();
    } catch (err: any) {
      setSubmitError(getApiErrorMessage(err, 'Erro ao salvar evento.'));
    }
  };

  const handleDelete = async (event: any) => {
    if (!confirm(`Remover o evento "${event.title}"?`)) return;
    try {
      await calendarService.delete(event.id);
      setSelectedDate(null);
      loadEvents();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao remover evento.'));
    }
  };

  const daysInMonth = getDaysInMonth(currentMonth, currentYear);
  const firstDay = getFirstDayOfMonth(currentMonth, currentYear);

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-serif text-zinc-900 dark:text-zinc-100 tracking-wide">Agenda Operacional</h1>
          <p className="text-sm text-zinc-400 font-mono mt-1">Medições, montagens, entregas e compromissos da marcenaria.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="bg-zinc-900 border border-zinc-800 p-1 rounded-md flex">
            <button
              onClick={() => setViewMode('month')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1 cursor-pointer ${viewMode === 'month' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'}`}
            >
              <Calendar className="w-3.5 h-3.5" /> Mensal
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1 cursor-pointer ${viewMode === 'list' ? 'bg-red-650 text-white font-bold' : 'text-zinc-400 hover:text-white'}`}
            >
              <List className="w-3.5 h-3.5" /> Lista
            </button>
          </div>
          {canEdit && (
            <button
              onClick={() => handleOpenCreate()}
              className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded shadow-md flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
            >
              <Plus className="w-4 h-4" /> Novo Evento
            </button>
          )}
        </div>
      </div>

      {/* Projetos atrasados */}
      <OverdueProjectsCard compact={true} />

      {/* Navigation */}
      <div className="glass-panel p-4 rounded-lg flex items-center justify-between">
        <button onClick={prevMonth} className="p-2 text-zinc-400 hover:text-white cursor-pointer">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <h2 className="text-lg font-serif text-zinc-900 dark:text-zinc-100 font-semibold">
          {MONTH_NAMES[currentMonth - 1]} {currentYear}
        </h2>
        <button onClick={nextMonth} className="p-2 text-zinc-400 hover:text-white cursor-pointer">
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-10 h-10 text-red-600 animate-spin mb-4" />
          <p className="text-zinc-400 font-mono text-xs">Carregando agenda...</p>
        </div>
      ) : viewMode === 'month' ? (
        <div className="space-y-4">
          {/* Calendar Grid */}
          <div className="glass-panel rounded-lg overflow-hidden">
            {/* Day headers */}
            <div className="grid grid-cols-7 border-b border-zinc-800">
              {DAY_NAMES.map(d => (
                <div key={d} className="py-2 text-center text-[11px] font-mono text-zinc-500 uppercase">
                  {d}
                </div>
              ))}
            </div>
            {/* Days grid */}
            <div className="grid grid-cols-7">
              {Array.from({ length: firstDay }).map((_, i) => (
                <div key={`empty-${i}`} className="min-h-[80px] border-b border-r border-zinc-900/50 bg-zinc-950/30" />
              ))}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1;
                const dateStr = formatDateStr(currentYear, currentMonth, day);
                const dayEvents = getEventsForDate(dateStr);
                const isToday = dateStr === today.toISOString().substring(0, 10);
                const isSelected = dateStr === selectedDate;
                return (
                  <div
                    key={day}
                    onClick={() => setSelectedDate(isSelected ? null : dateStr)}
                    className={`min-h-[80px] border-b border-r border-zinc-900/50 p-1.5 cursor-pointer transition ${
                      isSelected ? 'bg-red-950/20 border-red-900/40' :
                      isToday ? 'bg-zinc-900/60' : 'hover:bg-zinc-900/40'
                    }`}
                  >
                    <div className={`text-xs font-mono mb-1 w-6 h-6 flex items-center justify-center rounded-full ${
                      isToday ? 'bg-red-600 text-white font-bold' : 'text-zinc-400'
                    }`}>
                      {day}
                    </div>
                    <div className="space-y-0.5">
                      {dayEvents.slice(0, 3).map(ev => (
                        <div
                          key={ev.id}
                          className={`text-[10px] px-1 py-0.5 rounded truncate ${EVENT_TYPE_COLORS[ev.type] || 'bg-zinc-700'}`}
                        >
                          {ev.start_time ? ev.start_time.substring(0, 5) + ' ' : ''}{ev.title}
                        </div>
                      ))}
                      {dayEvents.length > 3 && (
                        <div className="text-[10px] text-zinc-500 font-mono px-1">
                          +{dayEvents.length - 3} mais
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected day events panel */}
          {selectedDate && (
            <div className="glass-panel rounded-lg overflow-hidden">
              <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 font-sans">
                  {new Date(selectedDate + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                  <span className="ml-2 text-xs text-zinc-500 font-mono">({selectedDateEvents.length} evento{selectedDateEvents.length !== 1 ? 's' : ''})</span>
                </h3>
                <div className="flex gap-2">
                  {canEdit && (
                    <button
                      onClick={() => handleOpenCreate(selectedDate)}
                      className="text-xs text-red-400 hover:text-red-300 font-mono cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Adicionar neste dia
                    </button>
                  )}
                  <button onClick={() => setSelectedDate(null)} className="text-zinc-500 hover:text-white cursor-pointer">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {selectedDateEvents.length === 0 ? (
                <div className="py-8 text-center text-zinc-500 font-mono text-xs">
                  Nenhum evento neste dia.
                  {canEdit && <span className="text-red-400 cursor-pointer ml-1" onClick={() => handleOpenCreate(selectedDate)}>Criar um?</span>}
                </div>
              ) : (
                <div className="divide-y divide-zinc-900">
                  {selectedDateEvents.map(ev => (
                    <div key={ev.id} className="p-4 flex justify-between items-start gap-4">
                      <div className="flex gap-3 flex-1 min-w-0">
                        <div className={`w-3 h-3 rounded-full mt-1 shrink-0 ${EVENT_TYPE_DOT[ev.type] || 'bg-zinc-400'}`} />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-zinc-900 dark:text-white font-sans">{ev.title}</span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${STATUS_COLORS[ev.status] || ''}`}>
                              {EVENT_STATUS_LABELS[ev.status] || ev.status}
                            </span>
                          </div>
                          <div className="text-[11px] text-zinc-700 dark:text-zinc-400 font-mono mt-0.5 space-x-3">
                            <span>{EVENT_TYPE_LABELS[ev.type] || ev.type}</span>
                            {ev.start_time && <span>🕐 {ev.start_time.substring(0, 5)}{ev.end_time ? ` - ${ev.end_time.substring(0, 5)}` : ''}</span>}
                          </div>
                          {(ev.client_name || ev.project_title) && (
                            <div className="text-[11px] text-zinc-700 dark:text-zinc-500 mt-1 space-x-2">
                              {ev.client_name && <span>👤 {ev.client_name}</span>}
                              {ev.project_title && <span>📦 {ev.project_title}</span>}
                            </div>
                          )}
                          {ev.assigned_user_name && (
                            <div className="text-[11px] text-zinc-700 dark:text-zinc-500">👷 {ev.assigned_user_name}</div>
                          )}
                          {ev.observations && (
                            <div className="text-[11px] text-zinc-700 dark:text-zinc-500 mt-1 italic">{ev.observations}</div>
                          )}
                        </div>
                      </div>
                      {canEdit && (
                        <div className="flex gap-1 shrink-0">
                          <button onClick={() => handleOpenEdit(ev)} className="p-1.5 text-zinc-400 hover:text-blue-600 dark:text-zinc-500 dark:hover:text-blue-400 cursor-pointer">
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => handleDelete(ev)} className="p-1.5 text-zinc-400 hover:text-red-600 dark:text-zinc-500 dark:hover:text-red-400 cursor-pointer">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Lista de todos os eventos do mês */
        <div className="glass-panel rounded-lg overflow-hidden">
          {events.length === 0 ? (
            <div className="py-16 text-center text-zinc-500 font-mono text-xs">
              Nenhum evento em {MONTH_NAMES[currentMonth - 1]}.
            </div>
          ) : (
            <div className="divide-y divide-zinc-900">
              {events.map(ev => (
                <div key={ev.id} className="p-4 flex justify-between items-start gap-4 hover:bg-zinc-900/30">
                  <div className="flex gap-3 flex-1 min-w-0">
                    <div className={`w-3 h-3 rounded-full mt-1 shrink-0 ${EVENT_TYPE_DOT[ev.type] || 'bg-zinc-400'}`} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono text-zinc-700 dark:text-zinc-400">
                          {new Date(ev.start_date + 'T12:00:00').toLocaleDateString('pt-BR')}
                          {ev.start_time && ` ${ev.start_time.substring(0, 5)}`}
                        </span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${STATUS_COLORS[ev.status] || ''}`}>
                          {EVENT_STATUS_LABELS[ev.status] || ev.status}
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-zinc-900 dark:text-white font-sans mt-0.5">{ev.title}</div>
                      <div className="text-[11px] text-zinc-700 dark:text-zinc-500 mt-0.5 space-x-2">
                        <span>{EVENT_TYPE_LABELS[ev.type] || ev.type}</span>
                        {ev.client_name && <span>· {ev.client_name}</span>}
                        {ev.project_title && <span>· {ev.project_title}</span>}
                      </div>
                    </div>
                  </div>
                  {canEdit && (
                    <div className="flex gap-1 shrink-0">
                      <button onClick={() => handleOpenEdit(ev)} className="p-1.5 text-zinc-400 hover:text-blue-600 dark:text-zinc-500 dark:hover:text-blue-400 cursor-pointer">
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => handleDelete(ev)} className="p-1.5 text-zinc-400 hover:text-red-600 dark:text-zinc-500 dark:hover:text-red-400 cursor-pointer">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal criar/editar evento */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-lg rounded-xl overflow-hidden border border-zinc-800 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="bg-zinc-950 p-6 border-b border-zinc-850 flex justify-between items-center sticky top-0 z-10">
              <h3 className="text-lg font-serif font-semibold text-white">
                {editingEventId ? 'Editar Evento' : 'Novo Evento'}
              </h3>
              <button onClick={() => { setIsModalOpen(false); setEditingEventId(null); }} className="text-zinc-500 hover:text-white font-mono text-xs uppercase cursor-pointer">
                Sair
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-7 space-y-6 font-sans">
              {submitError && (
                <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 text-xs rounded font-mono">{submitError}</div>
              )}

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Título *</label>
                <input
                  type="text" required value={formData.title}
                  onChange={e => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Ex: Medição Cozinha Silva"
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none focus:border-red-656"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Tipo</label>
                  <select value={formData.type} onChange={e => setFormData({ ...formData, type: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono">
                    {Object.entries(EVENT_TYPE_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Status</label>
                  <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono">
                    {Object.entries(EVENT_STATUS_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Data Início *</label>
                  <input type="date" required value={formData.start_date}
                    onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Horário</label>
                  <input type="time" value={formData.start_time}
                    onChange={e => setFormData({ ...formData, start_time: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Data Fim</label>
                  <input type="date" value={formData.end_date}
                    onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Horário Fim</label>
                  <input type="time" value={formData.end_time}
                    onChange={e => setFormData({ ...formData, end_time: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Cliente</label>
                  <select value={formData.client_id} onChange={e => setFormData({ ...formData, client_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono">
                    <option value="">Nenhum</option>
                    {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-300 font-mono uppercase block">Projeto</label>
                  <select value={formData.project_id} onChange={e => setFormData({ ...formData, project_id: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none font-mono">
                    <option value="">Nenhum</option>
                    {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Descrição</label>
                <textarea value={formData.description} rows={2}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none leading-relaxed" />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-mono uppercase block">Observações</label>
                <textarea value={formData.observations} rows={2}
                  onChange={e => setFormData({ ...formData, observations: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-805 text-white rounded px-4 py-3 text-sm focus:outline-none leading-relaxed" />
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800">
                <button type="button" onClick={() => { setIsModalOpen(false); setEditingEventId(null); }}
                  className="px-4 py-2 text-xs bg-zinc-900 text-zinc-400 rounded border border-zinc-800 cursor-pointer font-mono">
                  Cancelar
                </button>
                <button type="submit"
                  className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-semibold cursor-pointer">
                  {editingEventId ? 'Salvar Alterações' : 'Criar Evento'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
