import React, { useEffect, useMemo, useState } from 'react';
import {
  Star,
  MessageCircle,
  ShieldCheck,
  CalendarClock,
  PhoneCall,
  AlertTriangle,
  Plus,
  Check,
  X,
  RefreshCw,
  Send,
} from 'lucide-react';
import {
  ticketService,
  clientService,
  projectService,
  calendarService,
  settingsService,
  satisfactionService,
  posvendaService,
  getApiErrorMessage,
} from '../services/api';
import {
  Client,
  Project,
  ServiceTicket,
  SatisfactionSurvey,
  SatisfactionSummary,
  PosvendaCheckin,
  FollowupEvent,
} from '../types';

export interface PosvendaData {
  clients: Client[];
  projects: Project[];
  delivered: Project[];
  tickets: ServiceTicket[];
  surveys: SatisfactionSurvey[];
  satSummary: SatisfactionSummary | null;
  checkins: PosvendaCheckin[];
  followups: FollowupEvent[];
  userRole: string;
  reload: () => Promise<void>;
}

function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function fmtDate(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    return new Date(value.length <= 10 ? value + 'T12:00:00' : value).toLocaleDateString('pt-BR');
  } catch {
    return value;
  }
}

function daysOpen(iso: string | null | undefined): number | null {
  if (!iso) return null;
  try {
    const t = new Date(iso).getTime();
    if (isNaN(t)) return null;
    return Math.max(0, Math.floor((Date.now() - t) / 86400000));
  } catch {
    return null;
  }
}

function daysUntil(dateOnly: string | null | undefined): number | null {
  if (!dateOnly) return null;
  try {
    const t = new Date(dateOnly + 'T12:00:00').getTime();
    if (isNaN(t)) return null;
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    return Math.round((t - today) / 86400000);
  } catch {
    return null;
  }
}

function warrantyState(p: Project): { label: string; tone: string } {
  const months = p.warranty_months || 0;
  if (!p.warranty_until || months <= 0)
    return { label: 'Sem garantia', tone: 'text-zinc-500 border-zinc-800' };
  const d = daysUntil(p.warranty_until);
  if (d == null) return { label: 'Sem garantia', tone: 'text-zinc-500 border-zinc-800' };
  if (d < 0) return { label: `Vencida em ${fmtDate(p.warranty_until)}`, tone: 'text-rose-400 border-red-900/50' };
  if (d <= 30)
    return { label: `Vence em ${d}d (${fmtDate(p.warranty_until)})`, tone: 'text-amber-400 border-amber-900/50' };
  return { label: `Vigente até ${fmtDate(p.warranty_until)}`, tone: 'text-emerald-400 border-emerald-900/50' };
}

const panelBox = 'glass-panel rounded-lg p-4 border border-zinc-900';
const inputCls =
  'w-full bg-zinc-950 border border-zinc-800 text-white px-3 py-2 text-sm rounded focus:outline-none focus:border-zinc-700 font-sans';
const labelCls = 'text-xs text-zinc-300 font-mono uppercase tracking-wider block mb-1';

// ── 8.7 Dashboard ─────────────────────────────────────────────────────

export function PosvendaDashboard({ tickets, delivered, satSummary, checkins, followups }: PosvendaData) {
  const hoje = todayISO();
  const abertos = tickets.filter((t) => !['RESOLVIDO', 'ENCERRADO'].includes(t.status));
  const emGarantia = abertos.filter((t) => t.in_warranty);
  const vigentes = delivered.filter((p) => (p.warranty_months || 0) > 0 && p.warranty_until && (daysUntil(p.warranty_until) ?? -1) >= 0);
  const vencendo = delivered.filter((p) => {
    const d = daysUntil(p.warranty_until);
    return (p.warranty_months || 0) > 0 && d != null && d >= 0 && d <= 30;
  });
  const followPend = followups.filter((f) => f.status === 'AGENDADO' && f.start_date >= hoje);
  const followAtras = followups.filter((f) => f.status === 'AGENDADO' && f.start_date < hoje);
  const proxFollow = [...followups]
    .filter((f) => f.status === 'AGENDADO')
    .sort((a, b) => a.start_date.localeCompare(b.start_date))
    .slice(0, 5);
  const abertosAntigos = [...abertos]
    .sort((a, b) => (a.opened_at || '').localeCompare(b.opened_at || ''))
    .slice(0, 5);

  const cards = [
    { label: 'Satisfação média', value: satSummary && satSummary.answered > 0 ? `${satSummary.average.toFixed(1)} ★` : '—', sub: satSummary ? `${satSummary.answered}/${satSummary.total} respostas` : 'sem pesquisas' },
    { label: 'Garantias vigentes', value: String(vigentes.length), sub: vencendo.length > 0 ? `${vencendo.length} vencendo em 30d` : 'nenhuma vencendo' },
    { label: 'Follow-ups pendentes', value: String(followPend.length + followAtras.length), sub: followAtras.length > 0 ? `${followAtras.length} atrasados` : 'em dia' },
    { label: 'Chamados abertos', value: String(abertos.length), sub: emGarantia.length > 0 ? `${emGarantia.length} em garantia` : `${checkins.length} check-ins feitos` },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="glass-panel p-5 rounded-lg">
            <p className="text-[11px] text-zinc-500 font-mono uppercase tracking-wider">{c.label}</p>
            <p className="text-2xl font-bold text-white mt-1">{c.value}</p>
            <p className="text-[11px] text-zinc-500 font-mono mt-1">{c.sub}</p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={panelBox}>
          <h3 className="text-sm font-semibold text-zinc-200 mb-2">Próximos contatos programados</h3>
          {proxFollow.length === 0 ? (
            <p className="text-xs text-zinc-600 font-mono">Nada agendado. Concluir um projeto agenda sozinho.</p>
          ) : (
            <div className="space-y-2">
              {proxFollow.map((f) => (
                <div key={f.id} className="flex items-center justify-between gap-2 text-xs font-mono">
                  <span className="text-zinc-200 truncate">{f.title}</span>
                  <span className={f.start_date < hoje ? 'text-rose-400 shrink-0' : 'text-zinc-500 shrink-0'}>
                    {fmtDate(f.start_date)}
                    {f.start_date < hoje ? ' (atrasado)' : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className={panelBox}>
          <h3 className="text-sm font-semibold text-zinc-200 mb-2">Chamados abertos mais antigos</h3>
          {abertosAntigos.length === 0 ? (
            <p className="text-xs text-zinc-600 font-mono">Nenhum chamado aberto.</p>
          ) : (
            <div className="space-y-2">
              {abertosAntigos.map((t) => {
                const d = daysOpen(t.opened_at);
                return (
                  <div key={t.id} className="flex items-center justify-between gap-2 text-xs font-mono">
                    <span className="text-zinc-200 truncate">
                      {t.number} · {t.client_name || 'Sem cliente'}
                      {t.in_warranty ? <span className="text-emerald-400"> · garantia</span> : null}
                    </span>
                    <span className={d != null && d > 14 ? 'text-rose-400 shrink-0' : 'text-zinc-500 shrink-0'}>
                      {d != null ? `${d}d aberto` : t.status}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 8.3 Pesquisa de satisfação ────────────────────────────────────────

export function SatisfactionTab({ clients, projects, surveys, satSummary, reload }: PosvendaData) {
  const [showNew, setShowNew] = useState(false);
  const [clientId, setClientId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [answering, setAnswering] = useState<SatisfactionSurvey | null>(null);
  const [score, setScore] = useState('5');
  const [comment, setComment] = useState('');
  const [sendingId, setSendingId] = useState('');

  const clientProjects = useMemo(
    () => (clientId ? projects.filter((p) => p.client_id === clientId) : projects),
    [projects, clientId],
  );

  const handleCreate = async () => {
    if (!clientId) {
      setError('Escolha o cliente.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await satisfactionService.create({ client_id: clientId, project_id: projectId || null });
      setShowNew(false);
      setClientId('');
      setProjectId('');
      await reload();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao criar pesquisa.'));
    } finally {
      setSaving(false);
    }
  };

  const handleAnswer = async () => {
    if (!answering) return;
    setSaving(true);
    try {
      await satisfactionService.answer(answering.id, { score: Number(score), comment: comment.trim() });
      setAnswering(null);
      setComment('');
      await reload();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao registrar resposta.'));
    } finally {
      setSaving(false);
    }
  };

  const handleSend = async (s: SatisfactionSurvey) => {
    setSendingId(s.id);
    try {
      const r = await satisfactionService.sendWhatsapp(s.id);
      if (r.sent) {
        alert('Enviado pelo WhatsApp.');
        await reload();
      } else if (r.fallback_wa_me) {
        window.open(r.fallback_wa_me, '_blank');
      } else {
        alert(r.detail || 'Não foi possível enviar.');
      }
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao enviar.'));
    } finally {
      setSendingId('');
    }
  };

  const dist = satSummary?.distribution || {};
  const maxDist = Math.max(1, ...[1, 2, 3, 4, 5].map((i) => dist[String(i)] || 0));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-lg">
          <p className="text-[11px] text-zinc-500 font-mono uppercase tracking-wider">Nota média</p>
          <p className="text-2xl font-bold text-white mt-1 flex items-center gap-1">
            {satSummary && satSummary.answered > 0 ? satSummary.average.toFixed(1) : '—'}
            <Star className="w-5 h-5 text-amber-400" />
          </p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">{satSummary?.answered || 0} respostas</p>
        </div>
        <div className="glass-panel p-5 rounded-lg">
          <p className="text-[11px] text-zinc-500 font-mono uppercase tracking-wider">Taxa de resposta</p>
          <p className="text-2xl font-bold text-white mt-1">{satSummary ? `${satSummary.response_rate}%` : '—'}</p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">{satSummary?.total || 0} enviadas</p>
        </div>
        <div className="glass-panel p-5 rounded-lg col-span-2">
          <p className="text-[11px] text-zinc-500 font-mono uppercase tracking-wider mb-2">Distribuição das notas</p>
          <div className="space-y-1">
            {[5, 4, 3, 2, 1].map((n) => (
              <div key={n} className="flex items-center gap-2 text-[11px] font-mono">
                <span className="text-zinc-400 w-3">{n}</span>
                <div className="flex-1 h-2 bg-zinc-900 rounded overflow-hidden">
                  <div className="h-full bg-amber-400/80" style={{ width: `${((dist[String(n)] || 0) / maxDist) * 100}%` }} />
                </div>
                <span className="text-zinc-500 w-6 text-right">{dist[String(n)] || 0}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={() => { setShowNew(true); setError(''); }}
          className="px-4 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded flex items-center gap-2 cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Nova pesquisa
        </button>
      </div>

      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-2">Pesquisas enviadas</h3>
        {surveys.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nenhuma pesquisa enviada ainda.</p>
        ) : (
          <div className="space-y-2">
            {surveys.map((s) => (
              <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 p-3 bg-zinc-950 border border-zinc-800 rounded">
                <div className="min-w-0">
                  <p className="text-sm text-zinc-100 truncate">
                    {s.client_name || 'Sem cliente'}
                    {s.project_title ? <span className="text-zinc-500"> · {s.project_title}</span> : null}
                  </p>
                  <p className="text-[11px] text-zinc-500 font-mono">
                    enviada {fmtDate(s.sent_at)}
                    {s.answered
                      ? <span className="text-emerald-400"> · nota {s.score} {s.comment ? `· "${s.comment}"` : ''}</span>
                      : <span className="text-amber-400"> · aguardando resposta</span>}
                  </p>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <button
                    onClick={() => handleSend(s)}
                    disabled={sendingId === s.id}
                    className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 text-[11px] font-mono flex items-center gap-1 cursor-pointer disabled:opacity-50"
                    title="Enviar por WhatsApp (ou abrir wa.me)"
                  >
                    {sendingId === s.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                    WhatsApp
                  </button>
                  <button
                    onClick={() => { setAnswering(s); setScore(String(s.score || 5)); setComment(''); }}
                    className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 text-[11px] font-mono flex items-center gap-1 cursor-pointer"
                    title="Registrar resposta recebida"
                  >
                    <MessageCircle className="w-3 h-3" /> Responder
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-panel w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-serif font-bold text-white">Nova pesquisa</h3>
              <button onClick={() => setShowNew(false)} className="p-1 text-zinc-500 hover:text-white cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            {error && <p className="text-xs text-rose-400 font-mono">{error}</p>}
            <div>
              <label className={labelCls}>Cliente *</label>
              <select value={clientId} onChange={(e) => { setClientId(e.target.value); setProjectId(''); }} className={inputCls}>
                <option value="">Selecione...</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Projeto (opcional)</label>
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className={inputCls}>
                <option value="">Nenhum</option>
                {clientProjects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowNew(false)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 cursor-pointer">Cancelar</button>
              <button onClick={handleCreate} disabled={saving} className="px-6 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded disabled:opacity-50 cursor-pointer">
                {saving ? 'Salvando...' : 'Enviar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {answering && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-panel w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-serif font-bold text-white">Registrar resposta</h3>
              <button onClick={() => setAnswering(null)} className="p-1 text-zinc-500 hover:text-white cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-xs text-zinc-400 font-mono">{answering.client_name}{answering.project_title ? ` · ${answering.project_title}` : ''}</p>
            <div>
              <label className={labelCls}>Nota (1 a 5)</label>
              <select value={score} onChange={(e) => setScore(e.target.value)} className={inputCls}>
                {[5, 4, 3, 2, 1].map((n) => <option key={n} value={String(n)}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Comentário (opcional)</label>
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} className={`${inputCls} resize-none`} placeholder="O que o cliente disse..." />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setAnswering(null)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded border border-zinc-700 cursor-pointer">Cancelar</button>
              <button onClick={handleAnswer} disabled={saving} className="px-6 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded disabled:opacity-50 cursor-pointer">
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 8.4 Garantias ─────────────────────────────────────────────────────

export function WarrantiesTab({ delivered, tickets, reload }: PosvendaData) {
  const [months, setMonths] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState('');

  const handleSave = async (p: Project) => {
    const raw = months[p.id];
    if (raw == null || raw === '') return;
    const n = Number(raw);
    if (!Number.isInteger(n) || n < 0 || n > 120) {
      alert('Meses de garantia: número de 0 a 120.');
      return;
    }
    setSavingId(p.id);
    try {
      await projectService.setWarranty(p.id, n);
      setMonths((m) => {
        const c = { ...m };
        delete c[p.id];
        return c;
      });
      await reload();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao salvar garantia.'));
    } finally {
      setSavingId('');
    }
  };

  const emGarantia = tickets.filter((t) => t.in_warranty && !['RESOLVIDO', 'ENCERRADO'].includes(t.status));

  return (
    <div className="space-y-4">
      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-1 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-zinc-400" /> Garantias dos projetos entregues
        </h3>
        <p className="text-[11px] text-zinc-500 font-mono mb-3">
          A data-limite é calculada da entrega + meses. Chamado de projeto em garantia entra como coberto sozinho.
        </p>
        {delivered.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nenhum projeto entregue ainda.</p>
        ) : (
          <div className="space-y-2">
            {delivered.map((p) => {
              const w = warrantyState(p);
              return (
                <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <div className="min-w-0">
                    <p className="text-sm text-zinc-100 truncate">{p.title} <span className="text-zinc-500">· {p.client_name}</span></p>
                    <p className="text-[11px] font-mono mt-0.5">
                      <span className={`px-1.5 py-0.5 rounded border ${w.tone}`}>{w.label}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <input
                      type="number"
                      min={0}
                      max={120}
                      placeholder={String(p.warranty_months || 0)}
                      value={months[p.id] ?? ''}
                      onChange={(e) => setMonths((m) => ({ ...m, [p.id]: e.target.value }))}
                      className="w-20 bg-zinc-900 border border-zinc-800 text-white px-2 py-1 text-xs rounded font-mono"
                      title="Meses de garantia"
                    />
                    <span className="text-[11px] text-zinc-500 font-mono">meses</span>
                    <button
                      onClick={() => handleSave(p)}
                      disabled={savingId === p.id || (months[p.id] ?? '') === ''}
                      className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 text-[11px] font-mono cursor-pointer disabled:opacity-40"
                    >
                      {savingId === p.id ? '...' : 'Salvar'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-2">Chamados cobertos pela garantia ({emGarantia.length})</h3>
        {emGarantia.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nenhum chamado aberto em garantia.</p>
        ) : (
          <div className="space-y-2">
            {emGarantia.map((t) => (
              <div key={t.id} className="flex items-center justify-between gap-2 text-xs font-mono p-2 bg-zinc-950 border border-zinc-800 rounded">
                <span className="text-zinc-200 truncate">{t.number} · {t.client_name || 'Sem cliente'}{t.project_title ? ` · ${t.project_title}` : ''}</span>
                <span className="text-zinc-500 shrink-0">{t.status}{t.warranty_until ? ` · até ${fmtDate(t.warranty_until)}` : ''}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── 8.5 Agenda de pós-venda ───────────────────────────────────────────

export function ScheduleTab({ followups, userRole, reload }: PosvendaData) {
  const hoje = todayISO();
  const [generating, setGenerating] = useState(false);
  const [daysCfg, setDaysCfg] = useState('');
  const [daysLoaded, setDaysLoaded] = useState(false);
  const [savingCfg, setSavingCfg] = useState(false);
  const [actingId, setActingId] = useState('');

  useEffect(() => {
    settingsService.list()
      .then((all) => {
        const row = all.find((s) => s.key === 'posvenda_followup_days');
        setDaysCfg(row?.value || '7,30');
      })
      .catch(() => setDaysCfg('7,30'))
      .finally(() => setDaysLoaded(true));
  }, []);

  const atrasados = followups.filter((f) => f.status === 'AGENDADO' && f.start_date < hoje)
    .sort((a, b) => a.start_date.localeCompare(b.start_date));
  const proximos = followups.filter((f) => f.status === 'AGENDADO' && f.start_date >= hoje)
    .sort((a, b) => a.start_date.localeCompare(b.start_date));
  const concluidos = followups.filter((f) => f.status !== 'AGENDADO')
    .sort((a, b) => b.start_date.localeCompare(a.start_date))
    .slice(0, 10);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const r = await posvendaService.generateFollowups();
      alert(r.created > 0 ? `${r.created} contato(s) agendado(s) (${r.days.join(', ')} dias).` : 'Nada novo — agenda já em dia.');
      await reload();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao gerar agenda.'));
    } finally {
      setGenerating(false);
    }
  };

  const handleStatus = async (f: FollowupEvent, status: string) => {
    setActingId(f.id);
    try {
      await calendarService.update(f.id, { status });
      await reload();
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao atualizar.'));
    } finally {
      setActingId('');
    }
  };

  const handleSaveCfg = async () => {
    const partes = daysCfg.split(',').map((s) => s.trim()).filter((s) => /^\d+$/.test(s) && Number(s) > 0 && Number(s) <= 365);
    if (partes.length === 0) {
      alert('Informe dias válidos separados por vírgula (ex.: 7,30).');
      return;
    }
    setSavingCfg(true);
    try {
      await settingsService.update({ posvenda_followup_days: partes.join(',') });
      setDaysCfg(partes.join(','));
      alert('Salvo. Use "Gerar agenda" para aplicar nos projetos já entregues.');
    } catch (err) {
      alert(getApiErrorMessage(err, 'Erro ao salvar.'));
    } finally {
      setSavingCfg(false);
    }
  };

  const row = (f: FollowupEvent, late: boolean) => (
    <div key={f.id} className="flex flex-wrap items-center justify-between gap-2 p-3 bg-zinc-950 border border-zinc-800 rounded">
      <div className="min-w-0">
        <p className="text-sm text-zinc-100 truncate">{f.title}</p>
        <p className="text-[11px] text-zinc-500 font-mono">
          {fmtDate(f.start_date)}
          {late ? <span className="text-rose-400"> · atrasado</span> : null}
          {f.status !== 'AGENDADO' ? <span className="text-zinc-500"> · {f.status}</span> : null}
        </p>
      </div>
      {f.status === 'AGENDADO' && (
        <div className="flex gap-1.5 shrink-0">
          <button
            onClick={() => handleStatus(f, 'CONCLUIDO')}
            disabled={actingId === f.id}
            className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-emerald-400 rounded border border-zinc-800 text-[11px] font-mono flex items-center gap-1 cursor-pointer disabled:opacity-50"
          >
            <Check className="w-3 h-3" /> Feito
          </button>
          <button
            onClick={() => handleStatus(f, 'CANCELADO')}
            disabled={actingId === f.id}
            className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-500 rounded border border-zinc-800 text-[11px] font-mono cursor-pointer disabled:opacity-50"
          >
            Cancelar
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <div className={`${panelBox} flex flex-wrap items-end justify-between gap-3`}>
        <div>
          <h3 className="text-sm font-semibold text-zinc-200 mb-1 flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-zinc-400" /> Contatos programados
          </h3>
          <p className="text-[11px] text-zinc-500 font-mono">
            Concluir um projeto agenda sozinho. Projetos antigos: use Gerar agenda.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          {userRole === 'ADMIN' && daysLoaded && (
            <div className="flex items-end gap-1.5">
              <div>
                <label className={labelCls}>Dias p/ contato</label>
                <input
                  value={daysCfg}
                  onChange={(e) => setDaysCfg(e.target.value)}
                  placeholder="7,30"
                  className="w-28 bg-zinc-950 border border-zinc-800 text-white px-2 py-1 text-xs rounded font-mono"
                  title="Dias após a entrega, separados por vírgula"
                />
              </div>
              <button
                onClick={handleSaveCfg}
                disabled={savingCfg}
                className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded border border-zinc-800 text-[11px] font-mono cursor-pointer disabled:opacity-50"
              >
                {savingCfg ? '...' : 'Salvar'}
              </button>
            </div>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-3 py-1.5 bg-white hover:bg-zinc-100 text-zinc-900 text-xs font-semibold rounded flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {generating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CalendarClock className="w-3.5 h-3.5" />}
            Gerar agenda
          </button>
        </div>
      </div>

      {atrasados.length > 0 && (
        <div className={panelBox}>
          <h3 className="text-sm font-semibold text-rose-400 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Atrasados ({atrasados.length})
          </h3>
          <div className="space-y-2">{atrasados.map((f) => row(f, true))}</div>
        </div>
      )}

      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-2">Próximos ({proximos.length})</h3>
        {proximos.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nada agendado.</p>
        ) : (
          <div className="space-y-2">{proximos.map((f) => row(f, false))}</div>
        )}
      </div>

      {concluidos.length > 0 && (
        <div className={panelBox}>
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">Últimos concluídos</h3>
          <div className="space-y-2">{concluidos.map((f) => row(f, false))}</div>
        </div>
      )}
    </div>
  );
}

// ── 8.6 Check-ins ─────────────────────────────────────────────────────

const CHECKIN_TYPES = ['LIGACAO', 'VISITA', 'WHATSAPP'] as const;

export function CheckinsTab({ clients, projects, checkins, followups, reload }: PosvendaData) {
  const hoje = todayISO();
  const [clientId, setClientId] = useState('');
  const [ctype, setCtype] = useState<string>('WHATSAPP');
  const [projectId, setProjectId] = useState('');
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const programados = followups
    .filter((f) => f.status === 'AGENDADO')
    .sort((a, b) => a.start_date.localeCompare(b.start_date));

  const handleCreate = async () => {
    if (!clientId) {
      setError('Escolha o cliente.');
      return;
    }
    if (!content.trim()) {
      setError('Descreva o contato.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await posvendaService.createCheckin({
        client_id: clientId,
        type: ctype,
        content: content.trim(),
        project_id: projectId || null,
      });
      setClientId('');
      setProjectId('');
      setContent('');
      await reload();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao registrar check-in.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-1 flex items-center gap-2">
          <PhoneCall className="w-4 h-4 text-zinc-400" /> Registrar check-in
        </h3>
        <p className="text-[11px] text-zinc-500 font-mono mb-3">
          Contato proativo pós-entrega. Entra no histórico do cliente marcado como check-in.
        </p>
        {error && <p className="text-xs text-rose-400 font-mono mb-2">{error}</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Cliente *</label>
            <select value={clientId} onChange={(e) => setClientId(e.target.value)} className={inputCls}>
              <option value="">Selecione...</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Canal</label>
              <select value={ctype} onChange={(e) => setCtype(e.target.value)} className={inputCls}>
                {CHECKIN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Projeto (opcional)</label>
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className={inputCls}>
                <option value="">Nenhum</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            </div>
          </div>
        </div>
        <div className="mt-3">
          <label className={labelCls}>O que foi tratado *</label>
          <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={2} className={`${inputCls} resize-none`} placeholder="Ex.: ligou, porta com folga ajustada na visita..." />
        </div>
        <div className="flex justify-end mt-3">
          <button onClick={handleCreate} disabled={saving} className="px-6 py-2 bg-white hover:bg-zinc-100 text-zinc-900 text-sm font-semibold rounded disabled:opacity-50 cursor-pointer">
            {saving ? 'Salvando...' : 'Registrar'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={panelBox}>
          <h3 className="text-sm font-semibold text-zinc-200 mb-2">Programados ({programados.length})</h3>
          {programados.length === 0 ? (
            <p className="text-xs text-zinc-600 font-mono">Nada programado.</p>
          ) : (
            <div className="space-y-2">
              {programados.slice(0, 8).map((f) => (
                <div key={f.id} className="flex items-center justify-between gap-2 text-xs font-mono p-2 bg-zinc-950 border border-zinc-800 rounded">
                  <span className="text-zinc-200 truncate">{f.title}</span>
                  <span className={f.start_date < hoje ? 'text-rose-400 shrink-0' : 'text-zinc-500 shrink-0'}>{fmtDate(f.start_date)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className={panelBox}>
          <h3 className="text-sm font-semibold text-zinc-200 mb-2">Feitos ({checkins.length})</h3>
          {checkins.length === 0 ? (
            <p className="text-xs text-zinc-600 font-mono">Nenhum check-in registrado.</p>
          ) : (
            <div className="space-y-2">
              {checkins.slice(0, 8).map((c) => (
                <div key={c.id} className="p-2 bg-zinc-950 border border-zinc-800 rounded">
                  <p className="text-xs text-zinc-200 truncate">
                    <span className="text-zinc-500 font-mono">[{c.type}]</span> {c.client_name || 'Sem cliente'}
                  </p>
                  <p className="text-[11px] text-zinc-400 truncate">{c.content.replace('[CHECK-IN PÓS-VENDA]', '').trim()}</p>
                  <p className="text-[10px] text-zinc-600 font-mono">{fmtDate(c.created_at)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 8.7 Pendências ────────────────────────────────────────────────────

export function PendingTab({ tickets, followups }: PosvendaData) {
  const hoje = todayISO();
  const abertos = tickets
    .filter((t) => !['RESOLVIDO', 'ENCERRADO'].includes(t.status))
    .sort((a, b) => (a.opened_at || '').localeCompare(b.opened_at || ''));
  const atrasados = followups
    .filter((f) => f.status === 'AGENDADO' && f.start_date < hoje)
    .sort((a, b) => a.start_date.localeCompare(b.start_date));

  return (
    <div className="space-y-4">
      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-1 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-zinc-400" /> Chamados abertos por tempo ({abertos.length})
        </h3>
        <p className="text-[11px] text-zinc-500 font-mono mb-3">Do mais antigo para o mais novo.</p>
        {abertos.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nenhum chamado aberto.</p>
        ) : (
          <div className="space-y-2">
            {abertos.map((t) => {
              const d = daysOpen(t.opened_at);
              const critico = d != null && d > 14;
              return (
                <div key={t.id} className="flex flex-wrap items-center justify-between gap-2 p-3 bg-zinc-950 border border-zinc-800 rounded">
                  <div className="min-w-0">
                    <p className="text-sm text-zinc-100 truncate">
                      {t.number} · {t.client_name || 'Sem cliente'}
                      {t.in_warranty ? <span className="text-emerald-400 text-xs"> · em garantia</span> : null}
                    </p>
                    <p className="text-[11px] text-zinc-500 font-mono truncate">{t.status} · {t.description}</p>
                  </div>
                  <span className={`text-[11px] font-mono shrink-0 px-1.5 py-0.5 rounded border ${critico ? 'text-rose-400 border-red-900/50' : 'text-zinc-500 border-zinc-800'}`}>
                    {d != null ? `${d}d aberto` : t.status}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className={panelBox}>
        <h3 className="text-sm font-semibold text-zinc-200 mb-2">Contatos programados atrasados ({atrasados.length})</h3>
        {atrasados.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Agenda em dia.</p>
        ) : (
          <div className="space-y-2">
            {atrasados.map((f) => (
              <div key={f.id} className="flex items-center justify-between gap-2 text-xs font-mono p-2 bg-zinc-950 border border-zinc-800 rounded">
                <span className="text-zinc-200 truncate">{f.title}</span>
                <span className="text-rose-400 shrink-0">{fmtDate(f.start_date)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}