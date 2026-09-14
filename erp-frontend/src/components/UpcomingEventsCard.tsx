import React, { useEffect, useState } from 'react';
import { Calendar, Clock, User, Package, AlertTriangle, CheckCircle } from 'lucide-react';
import { calendarService, projectService } from '../services/api';

const EVENT_TYPE_LABELS: Record<string, string> = {
  MEDICAO: 'Medição',
  REUNIAO_CLIENTE: 'Reunião',
  APROVACAO_PROJETO: 'Aprovação',
  PRODUCAO: 'Produção',
  MONTAGEM: 'Montagem',
  ENTREGA: 'Entrega',
  ASSISTENCIA_TECNICA: 'Assistência',
  LIGACAO: 'Ligação',
  VISITA: 'Visita',
  WHATSAPP: 'WhatsApp',
  PERSONALIZADO: 'Evento',
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  MEDICAO: 'bg-blue-500/20 text-blue-700 border-blue-400/40',
  REUNIAO_CLIENTE: 'bg-purple-500/20 text-purple-700 border-purple-400/40',
  APROVACAO_PROJETO: 'bg-amber-500/20 text-amber-700 border-amber-400/40',
  PRODUCAO: 'bg-orange-500/20 text-orange-700 border-orange-400/40',
  MONTAGEM: 'bg-red-500/20 text-red-700 border-red-400/40',
  ENTREGA: 'bg-emerald-500/20 text-emerald-700 border-emerald-400/40',
  ASSISTENCIA_TECNICA: 'bg-cyan-500/20 text-cyan-700 border-cyan-400/40',
  LIGACAO: 'bg-sky-500/20 text-sky-700 border-sky-400/40',
  VISITA: 'bg-teal-500/20 text-teal-700 border-teal-400/40',
  WHATSAPP: 'bg-green-500/20 text-green-700 border-green-400/40',
  PERSONALIZADO: 'bg-zinc-500/20 text-zinc-600 border-zinc-400/40',
};

export default function UpcomingEventsCard() {
  const [events, setEvents] = useState<any[]>([]);
  const [urgentProjects, setUrgentProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const today = new Date();
  const todayStr = today.toISOString().substring(0, 10);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().substring(0, 10);

  useEffect(() => {
    Promise.all([
      calendarService.getWeek().catch(() => []),
      projectService.getAll().catch(() => []),
    ]).then(([evts, projs]) => {
      setEvents(evts);
      const sevenDays = new Date();
      sevenDays.setDate(sevenDays.getDate() + 7);
      const urgent = projs.filter((p: any) => {
        if (p.status === 'CONCLUIDO') return false;
        const deadline = new Date(p.deadline + 'T12:00:00');
        return deadline <= sevenDays;
      }).sort((a: any, b: any) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime());
      setUrgentProjects(urgent.slice(0, 5));
    }).finally(() => setLoading(false));
  }, []);

  const todayEvents = events.filter(e => e.start_date?.substring(0, 10) === todayStr);
  const tomorrowEvents = events.filter(e => e.start_date?.substring(0, 10) === tomorrowStr);
  const weekEvents = events.filter(e => {
    const d = e.start_date?.substring(0, 10);
    return d && d > tomorrowStr;
  });

  const totalItems = todayEvents.length + tomorrowEvents.length + weekEvents.length + urgentProjects.length;

  if (loading) return null;

  const EventItem = ({ ev }: { ev: any; key?: React.Key }) => (
    <div className="flex items-start gap-2.5 py-2">
      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0 mt-0.5 ${EVENT_TYPE_COLORS[ev.type] || EVENT_TYPE_COLORS.PERSONALIZADO}`}>
        {EVENT_TYPE_LABELS[ev.type] || 'Evento'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-100 font-sans truncate">{ev.title}</p>
        <div className="flex items-center gap-2 text-[11px] text-zinc-500 font-mono mt-0.5">
          {ev.start_time && <span className="flex items-center gap-0.5"><Clock className="w-3 h-3" />{ev.start_time.substring(0, 5)}</span>}
          {ev.client_name && <span className="flex items-center gap-0.5 truncate"><User className="w-3 h-3" />{ev.client_name}</span>}
        </div>
      </div>
    </div>
  );

  const Section = ({ title, items, emptyMsg }: { title: string; items: any[]; emptyMsg?: string }) => (
    <div>
      <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 mb-1">{title}</p>
      {items.length === 0 && emptyMsg
        ? <p className="text-[11px] text-zinc-500 font-mono py-1">{emptyMsg}</p>
        : <div className="divide-y divide-zinc-100 dark:divide-zinc-900">{items.map(ev => <EventItem key={ev.id} ev={ev} />)}</div>
      }
    </div>
  );

  return (
    <div className="glass-panel p-5 rounded-lg">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-red-500" />
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-white font-sans">Próximos Compromissos</h3>
        </div>
        <span className="text-[11px] font-mono text-zinc-500 bg-zinc-100 dark:bg-zinc-900 px-2 py-0.5 rounded">
          {totalItems} item{totalItems !== 1 ? 's' : ''}
        </span>
      </div>

      {totalItems === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <CheckCircle className="w-8 h-8 text-emerald-500 mb-2" />
          <p className="text-sm text-zinc-500 font-mono">Nenhum compromisso nos próximos 7 dias.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {todayEvents.length > 0 && <Section title="Hoje" items={todayEvents} />}
          {tomorrowEvents.length > 0 && <Section title="Amanhã" items={tomorrowEvents} />}
          {weekEvents.length > 0 && <Section title="Esta semana" items={weekEvents} />}

          {urgentProjects.length > 0 && (
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-amber-600 mb-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Projetos com prazo próximo
              </p>
              <div className="divide-y divide-zinc-100 dark:divide-zinc-900">
                {urgentProjects.map(proj => {
                  const deadline = new Date(proj.deadline + 'T12:00:00');
                  const diff = Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                  return (
                    <div key={proj.id} className="flex items-start gap-2.5 py-2">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0 mt-0.5 ${
                        diff < 0 ? 'bg-red-500/20 text-red-700 border-red-400/40' :
                        diff <= 1 ? 'bg-red-500/20 text-red-700 border-red-400/40' :
                        diff <= 3 ? 'bg-amber-500/20 text-amber-700 border-amber-400/40' :
                        'bg-zinc-500/20 text-zinc-600 border-zinc-400/40'
                      }`}>
                        {diff < 0 ? `${Math.abs(diff)}d atrasado` : diff === 0 ? 'Hoje' : `${diff}d`}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-100 font-sans truncate">{proj.title}</p>
                        {proj.client_name && (
                          <p className="text-[11px] text-zinc-500 font-mono flex items-center gap-0.5 mt-0.5">
                            <User className="w-3 h-3" />{proj.client_name}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
