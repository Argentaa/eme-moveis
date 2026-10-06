import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import {
  MessageCircle, QrCode, Send, Paperclip, RefreshCw, Plus, X,
  CheckCircle, Phone, Download, Settings, Wifi, WifiOff, CheckCheck,
} from 'lucide-react';
import { api, whatsappService, getApiErrorMessage } from '../services/api';
import type { WhatsappConversation, WhatsappMessage, WhatsappStatus } from '../types';
import ModuleTabs, { type ModuleTab, ActiveTabPlaceholder, useModuleTab } from './ModuleTabs';

const WHATSAPP_TABS: ModuleTab[] = [
  { id: 'conversas', label: 'Conversas', ready: true },
  { id: 'config', label: 'Configuração', ready: true },
];

interface WhatsappViewProps {
  userRole: string;
}

function kindLabel(kind: string): string {
  switch (kind) {
    case 'image': return 'Foto';
    case 'audio': return 'Áudio';
    case 'video': return 'Vídeo';
    case 'document': return 'Arquivo';
    default: return 'Texto';
  }
}

/** Iniciais p/ o avatar (WhatsApp Web mostra iniciais sem foto). */
function initials(label: string): string {
  const base = (label || '').trim();
  if (!base) return '?';
  const parts = base.split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return base.replace(/^\+/, '').slice(0, 2).toUpperCase();
}

const AVATAR_TONES = [
  'bg-emerald-900 text-emerald-200',
  'bg-teal-900 text-teal-200',
  'bg-sky-900 text-sky-200',
  'bg-amber-900 text-amber-200',
  'bg-rose-900 text-rose-200',
  'bg-violet-900 text-violet-200',
];

/** Cor estável por conversa (mesmo contato, mesma cor). */
function avatarTone(key: string): string {
  let h = 0;
  for (const ch of (key || '?')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return AVATAR_TONES[h % AVATAR_TONES.length];
}

function fmtHour(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** "Hoje" / "Ontem" / "12/03/2026" — divisor de dia do thread. */
function dayLabel(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  if (sameDay(d, now)) return 'Hoje';
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay(d, yesterday)) return 'Ontem';
  return d.toLocaleDateString('pt-BR');
}

/** Na lista: hora se for hoje, data curta se for outro dia. */
function fmtListTime(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (sameDay(d, new Date())) return fmtHour(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function MediaPreview({ m }: { m: WhatsappMessage }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!m.has_media) return;
    if (m.kind !== 'image' && m.kind !== 'audio' && m.kind !== 'video') return;
    let alive = true;
    let objUrl = '';
    api.get(whatsappService.mediaUrl(m.id), { responseType: 'blob' })
      .then((resp) => {
        if (!alive) return;
        objUrl = URL.createObjectURL(resp.data);
        setUrl(objUrl);
      })
      .catch(() => { /* sem bytes: fica só o botão Baixar */ });
    return () => {
      alive = false;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [m.id, m.has_media]);
  if (!url) return null;
  if (m.kind === 'image') {
    return <img src={url} alt={m.media_filename || 'Foto recebida'} className="max-h-64 rounded-lg mb-1" />;
  }
  if (m.kind === 'audio') {
    return <audio src={url} controls className="max-w-full mb-1" />;
  }
  return <video src={url} controls className="max-h-64 rounded-lg mb-1" />;
}

export default function WhatsappView({ userRole }: WhatsappViewProps) {
  const [activeTab, setActiveTab] = useModuleTab('whatsapp', WHATSAPP_TABS, 'conversas');
  const isAdmin = userRole === 'ADMIN';

  // ── estado compartilhado ──────────────────────────────────────────
  const [status, setStatus] = useState<WhatsappStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const [conversations, setConversations] = useState<WhatsappConversation[]>([]);
  const [convLoading, setConvLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [messages, setMessages] = useState<WhatsappMessage[]>([]);
  const [msgLoading, setMsgLoading] = useState(false);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');
  const [attachFile, setAttachFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);
  // Sincronização com o celular (puxa o histórico da Evolution).
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [newName, setNewName] = useState('');
  const [newError, setNewError] = useState('');

  // ── config ────────────────────────────────────────────────────────
  const [cfgUrl, setCfgUrl] = useState('');
  const [cfgKey, setCfgKey] = useState('');
  const [cfgInstance, setCfgInstance] = useState('eme-moveis');
  const [cfgWebhookBase, setCfgWebhookBase] = useState('');
  const [cfgMsg, setCfgMsg] = useState('');
  const [cfgError, setCfgError] = useState('');
  const [cfgSaving, setCfgSaving] = useState(false);
  const [qrBase64, setQrBase64] = useState('');
  const [qrLoading, setQrLoading] = useState(false);
  const [qrError, setQrError] = useState('');
  const [discLoading, setDiscLoading] = useState(false);
  const [discMsg, setDiscMsg] = useState('');

  const loadStatus = useCallback(async () => {
    try {
      const s = await whatsappService.status();
      setStatus(s);
    } catch {
      setStatus(null);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      const list = await whatsappService.conversations();
      setConversations(list);
    } catch {
      // Sem config ou sem rede: lista vazia, o aviso da aba explica.
    } finally {
      setConvLoading(false);
    }
  }, []);

  const loadMessages = useCallback(async (convId: string) => {
    setMsgLoading(true);
    try {
      const list = await whatsappService.messages(convId);
      setMessages(list);
    } finally {
      setMsgLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadConversations();
  }, [loadStatus, loadConversations]);

  // Abre a primeira conversa sozinho (cara de WhatsApp Web).
  useEffect(() => {
    if (!selectedId && conversations.length > 0) setSelectedId(conversations[0].id);
  }, [conversations, selectedId]);

  // Atualiza a lista a cada 10 s (só na aba de conversas).
  useEffect(() => {
    if (activeTab !== 'conversas') return;
    const t = setInterval(loadConversations, 10000);
    return () => clearInterval(t);
  }, [activeTab, loadConversations]);

  // Atualiza o thread aberto a cada 5 s.
  useEffect(() => {
    if (activeTab !== 'conversas' || !selectedId) return;
    loadMessages(selectedId);
    const t = setInterval(() => loadMessages(selectedId), 5000);
    return () => clearInterval(t);
  }, [activeTab, selectedId, loadMessages]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const selected = conversations.find((c) => c.id === selectedId) || null;
  const filtered = conversations.filter((c) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return c.phone.includes(q) || (c.name || '').toLowerCase().includes(q)
      || (c.client_name || '').toLowerCase().includes(q);
  });

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!selected || sending) return;
    if (!draft.trim() && !attachFile) return;
    setSending(true);
    setSendError('');
    try {
      if (attachFile) {
        await whatsappService.sendMedia(selected.id, attachFile, draft.trim());
        setAttachFile(null);
      } else {
        await whatsappService.sendText(selected.id, draft.trim());
      }
      setDraft('');
      await loadMessages(selected.id);
      await loadConversations();
    } catch (err) {
      setSendError(getApiErrorMessage(err, 'Falha ao enviar. Tente de novo.'));
    } finally {
      setSending(false);
    }
  }

  /** Sincronizar: puxa o histórico da Evolution (o que foi falado no celular). */
  async function handleSync() {
    if (!selected || syncing) return;
    setSyncing(true);
    setSyncMsg('');
    try {
      const r = await whatsappService.sync(selected.id);
      setSyncMsg(r.stored > 0 ? `${r.stored} mensagem(ns) sincronizada(s).` : 'Já estava em dia — nada novo.');
      await loadMessages(selected.id);
      await loadConversations();
    } catch (err) {
      setSyncMsg(getApiErrorMessage(err, 'Não foi possível sincronizar.'));
    } finally {
      setSyncing(false);
    }
  }

  async function handleDownload(m: WhatsappMessage) {
    try {
      const resp = await api.get(whatsappService.mediaUrl(m.id), { responseType: 'blob' });
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = m.media_filename || 'arquivo';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      // Se a mídia veio da Evolution agora, recarrega p/ mostrar o preview.
      if (selected) await loadMessages(selected.id);
    } catch {
      setSendError('Não foi possível baixar o arquivo.');
    }
  }

  async function handleNewConversation(e: FormEvent) {
    e.preventDefault();
    setNewError('');
    try {
      const conv = await whatsappService.start(newPhone, newName.trim());
      setNewPhone('');
      setNewName('');
      setIsNewModalOpen(false);
      await loadConversations();
      setSelectedId(conv.id);
    } catch (err) {
      setNewError(getApiErrorMessage(err, 'Não foi possível abrir a conversa.'));
    }
  }

  async function handleSetup(e: FormEvent) {
    e.preventDefault();
    setCfgError('');
    setCfgMsg('');
    setCfgSaving(true);
    try {
      const r = await whatsappService.setup({
        url: cfgUrl.trim(),
        global_key: cfgKey.trim(),
        instance: cfgInstance.trim() || 'eme-moveis',
        webhook_base: cfgWebhookBase.trim() || undefined,
      });
      setCfgMsg(`Instância "${r.instance.name}" pronta. Webhook: ${r.webhook}`);
      setCfgKey('');
      await loadStatus();
    } catch (err) {
      setCfgError(getApiErrorMessage(err, 'Falha ao configurar. Confira URL e chave.'));
    } finally {
      setCfgSaving(false);
    }
  }

  async function handleQr() {
    setQrError('');
    setQrLoading(true);
    try {
      const r = await whatsappService.qr();
      setQrBase64(r.base64);
    } catch (err) {
      setQrError(getApiErrorMessage(err, 'Não foi possível gerar o QR.'));
    } finally {
      setQrLoading(false);
    }
  }

  async function handleDisconnect() {
    if (!window.confirm('Desconectar o WhatsApp deste aparelho? As conversas e mensagens ficam salvas — depois é só gerar um QR novo para parear de novo.')) return;
    setDiscMsg('');
    setDiscLoading(true);
    try {
      // A resposta já traz o estado VERIFICADO na Evolution (o backend espera
      // a sessão cair): atualiza a tela por ela, sem reconsultar na hora —
      // era essa releitura imediata que trazia o "open" transitório e o selo
      // voltava a mostrar Conectado.
      const r = await whatsappService.logout();
      setQrBase64('');
      setStatus((prev) => ({
        configured: true,
        instance: r.instance,
        connection: r.connection,
        phone: r.phone,
        webhook: prev?.webhook,
      }));
      setDiscMsg(r.ok
        ? 'Desconectado. Gere um QR novo abaixo para parear outra conta.'
        : 'A Evolution ainda mostra conectado — aguarde uns segundos e clique em Atualizar estado.');
    } catch (err) {
      setDiscMsg(getApiErrorMessage(err, 'Não foi possível desconectar.'));
    } finally {
      setDiscLoading(false);
    }
  }

  const connected = status?.configured && status.connection === 'open';

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <MessageCircle size={22} className="text-emerald-400" />
        <h2 className="text-xl font-semibold">WhatsApp</h2>
        {!statusLoading && (
          <span className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${connected ? 'bg-emerald-900 text-emerald-200' : 'bg-zinc-800 text-zinc-300'}`}>
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {connected ? `Conectado${status?.phone ? ` · ${status.phone}` : ''}` : 'Desconectado'}
          </span>
        )}
        <div className="flex-1" />
        {activeTab === 'conversas' && (
          <button type="button" onClick={() => setIsNewModalOpen(true)}
            className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600">
            <Plus size={15} /> Nova conversa
          </button>
        )}
      </div>

      <ModuleTabs tabs={WHATSAPP_TABS} active={activeTab} onChange={setActiveTab} />
      <ActiveTabPlaceholder tabs={WHATSAPP_TABS} active={activeTab} />

      {activeTab === 'conversas' && (
        <div className="glass-panel mt-4 overflow-hidden">
          <div className="flex flex-col lg:flex-row lg:h-[72vh]">
            {/* ── Lista (estilo WhatsApp Web) ── */}
            <div className="flex flex-col lg:w-[340px] shrink-0 border-b lg:border-b-0 lg:border-r border-zinc-800 min-h-0">
              <div className="p-3 border-b border-zinc-800/80">
                <div className="flex items-center gap-2">
                  <input value={search} onChange={(e) => setSearch(e.target.value)}
                    placeholder="Pesquisar conversa…"
                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-emerald-700" />
                  <button type="button" title="Atualizar lista" onClick={loadConversations}
                    className="p-2 rounded-full bg-zinc-800 hover:bg-zinc-700 shrink-0">
                    <RefreshCw size={15} />
                  </button>
                </div>
              </div>
              <div className="overflow-y-auto max-h-[28vh] lg:max-h-none lg:flex-1">
                {convLoading ? (
                  <p className="text-sm text-zinc-400 p-4">Carregando conversas…</p>
                ) : filtered.length === 0 ? (
                  <p className="text-sm text-zinc-400 p-4">
                    {status && !status.configured
                      ? 'WhatsApp ainda não configurado — abra a aba Configuração.'
                      : 'Nenhuma conversa ainda. Inicie uma ou aguarde mensagens.'}
                  </p>
                ) : (
                  <ul className="divide-y divide-zinc-800/60">
                    {filtered.map((c) => {
                      const active = selectedId === c.id;
                      const label = c.name || c.phone;
                      return (
                        <li key={c.id}>
                          <button type="button" onClick={() => { setSelectedId(c.id); setSyncMsg(''); }}
                            className={`w-full text-left px-3 py-3 flex items-center gap-3 transition ${active ? 'bg-zinc-800/90' : 'hover:bg-zinc-800/50'}`}>
                            <span className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${avatarTone(c.phone)}`}>
                              {initials(label)}
                            </span>
                            <span className="flex-1 min-w-0">
                              <span className="flex items-baseline justify-between gap-2">
                                <span className="font-medium text-sm truncate">{label}</span>
                                <span className="text-[11px] text-zinc-500 shrink-0">{fmtListTime(c.last_message_at)}</span>
                              </span>
                              <span className="flex items-center justify-between gap-2 mt-0.5">
                                <span className="text-xs text-zinc-400 truncate">
                                  {c.last_direction === 'out' ? 'Você: ' : ''}{c.last_body || '—'}
                                </span>
                                {(c.unread || 0) > 0 && (
                                  <span className="text-[10px] font-bold bg-emerald-600 text-white rounded-full min-w-5 h-5 px-1 flex items-center justify-center shrink-0">
                                    {c.unread}
                                  </span>
                                )}
                              </span>
                              {(c.client_name || c.phone !== label) && (
                                <span className="block text-[11px] text-zinc-600 truncate mt-0.5">
                                  {c.phone}{c.client_name ? ` · ${c.client_name}` : ''}
                                </span>
                              )}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>

            {/* ── Thread (estilo WhatsApp Web) ── */}
            <div className="flex-1 flex flex-col min-h-[60vh] lg:min-h-0 min-w-0">
              {!selected ? (
                <div className="m-auto text-center px-6">
                  <MessageCircle size={44} className="text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-400">Selecione uma conversa para ver as mensagens.</p>
                  <p className="text-[11px] text-zinc-600 mt-1">O que você falar no celular aparece aqui depois de sincronizar.</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-3 px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/60">
                    <span className={`w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${avatarTone(selected.phone)}`}>
                      {initials(selected.name || selected.phone)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{selected.name || selected.phone}</div>
                      <div className="text-[11px] text-zinc-400 truncate flex items-center gap-1">
                        <Phone size={11} className="shrink-0" />
                        <span className="truncate">{selected.phone}{selected.client_name ? ` · ${selected.client_name}` : ' · Sem cliente vinculado'}</span>
                      </div>
                    </div>
                    <button type="button" title="Sincronizar com o celular (puxa o histórico)" onClick={handleSync} disabled={syncing}
                      className="flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-full border border-emerald-800 text-emerald-300 hover:bg-emerald-900/40 disabled:opacity-50 shrink-0">
                      <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
                      {syncing ? 'Sincronizando…' : 'Sincronizar'}
                    </button>
                  </div>
                  <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-3"
                    style={{ backgroundImage: 'radial-gradient(#27272a 0.8px, transparent 0.8px)', backgroundSize: '18px 18px' }}>
                    {msgLoading && messages.length === 0 ? (
                      <p className="text-sm text-zinc-400 text-center mt-6">Carregando mensagens…</p>
                    ) : messages.length === 0 ? (
                      <p className="text-sm text-zinc-400 text-center mt-6">Nenhuma mensagem ainda. Diga oi — ou sincronize o celular.</p>
                    ) : messages.map((m, idx) => {
                      const prev = idx > 0 ? messages[idx - 1] : null;
                      const showDay = !prev || dayLabel(prev.created_at) !== dayLabel(m.created_at);
                      const out = m.direction === 'out';
                      return (
                        <div key={m.id}>
                          {showDay && (
                            <div className="flex justify-center my-3">
                              <span className="text-[11px] font-mono text-zinc-400 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1">
                                {dayLabel(m.created_at)}
                              </span>
                            </div>
                          )}
                          <div className={`flex ${out ? 'justify-end' : 'justify-start'} mb-1.5`}>
                            <div className={`max-w-[85%] sm:max-w-[75%] px-3 py-2 text-sm shadow ${out ? 'bg-emerald-900/90 text-zinc-100 rounded-lg rounded-tr-none' : 'bg-zinc-800 text-zinc-100 rounded-lg rounded-tl-none'}`}>
                              <MediaPreview m={m} />
                              {m.kind !== 'text' && (
                                <div className="text-xs opacity-80 mb-1">[{kindLabel(m.kind)}]{m.media_filename ? ` ${m.media_filename}` : ''}</div>
                              )}
                              {m.body && <div className="whitespace-pre-wrap break-words">{m.body}</div>}
                              {(m.has_media || m.media_pending) && (
                                <button type="button" onClick={() => handleDownload(m)}
                                  className="mt-1 flex items-center gap-1 text-xs underline opacity-90">
                                  <Download size={12} /> Baixar arquivo
                                </button>
                              )}
                              <div className={`flex items-center gap-1 mt-1 text-[10px] opacity-70 ${out ? 'justify-end' : 'justify-start'}`}>
                                <span>{fmtHour(m.created_at)}</span>
                                {out && <CheckCheck size={13} className="text-sky-300" />}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    <div ref={threadEndRef} />
                  </div>
                  {syncMsg && <p className="text-[11px] text-zinc-400 font-mono px-4 py-1.5 bg-zinc-900/60 border-t border-zinc-800/60">{syncMsg}</p>}
                  {sendError && <p className="text-xs text-red-400 px-4 pt-1">{sendError}</p>}
                  {attachFile && (
                    <div className="flex items-center gap-2 mx-3 mt-2 text-xs bg-zinc-800 rounded-lg px-2 py-1.5">
                      <Paperclip size={12} />
                      <span className="truncate flex-1">{attachFile.name}</span>
                      <button type="button" onClick={() => setAttachFile(null)} title="Remover anexo">
                        <X size={13} />
                      </button>
                    </div>
                  )}
                  <form onSubmit={handleSend} className="flex items-center gap-2 px-3 py-2.5 border-t border-zinc-800 bg-zinc-900/60">
                    <input ref={fileInputRef} type="file" className="hidden"
                      onChange={(e) => setAttachFile(e.target.files?.[0] || null)} />
                    <button type="button" title="Anexar foto ou arquivo"
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2.5 rounded-full bg-zinc-800 hover:bg-zinc-700 shrink-0">
                      <Paperclip size={16} />
                    </button>
                    <input value={draft} onChange={(e) => setDraft(e.target.value)}
                      placeholder={attachFile ? 'Legenda (opcional)…' : 'Digite uma mensagem…'}
                      className="flex-1 bg-zinc-950 border border-zinc-800 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-700" />
                    <button type="submit" disabled={sending || (!draft.trim() && !attachFile)}
                      className="p-2.5 rounded-full bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 shrink-0"
                      title="Enviar">
                      <Send size={16} />
                    </button>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'config' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="glass-panel p-4">
            <div className="flex items-center gap-2 mb-3">
              <Settings size={17} className="text-zinc-400" />
              <h3 className="font-semibold">Configuração automática</h3>
            </div>
            {!isAdmin ? (
              <p className="text-sm text-zinc-400">Só ADMIN configura a integração. O chat continua disponível para leitura e envio.</p>
            ) : (
              <form onSubmit={handleSetup} className="space-y-3">
                <div>
                  <label className="text-xs text-zinc-400">URL da Evolution API</label>
                  <input value={cfgUrl} onChange={(e) => setCfgUrl(e.target.value)}
                    placeholder="https://evo.seudominio.com"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Chave global (AUTHENTICATION_API_KEY)</label>
                  <input value={cfgKey} onChange={(e) => setCfgKey(e.target.value)} type="password"
                    placeholder="Só é enviada ao salvar; nunca volta na leitura"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-400">Instância</label>
                    <input value={cfgInstance} onChange={(e) => setCfgInstance(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400">Base pública do ERP (webhook)</label>
                    <input value={cfgWebhookBase} onChange={(e) => setCfgWebhookBase(e.target.value)}
                      placeholder="https://erp.ememoveis.com.br"
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
                  </div>
                </div>
                {cfgError && <p className="text-xs text-red-400">{cfgError}</p>}
                {cfgMsg && <p className="text-xs text-emerald-300 flex items-center gap-1"><CheckCircle size={13} /> {cfgMsg}</p>}
                <button type="submit" disabled={cfgSaving}
                  className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-sm disabled:opacity-50">
                  {cfgSaving ? 'Salvando…' : 'Salvar e criar instância'}
                </button>
              </form>
            )}
          </div>

          <div className="glass-panel p-4">
            <div className="flex items-center gap-2 mb-3">
              <QrCode size={17} className="text-zinc-400" />
              <h3 className="font-semibold">Conexão</h3>
              <div className="flex-1" />
              <button type="button" onClick={loadStatus} className="text-xs px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700">
                Atualizar estado
              </button>
            </div>
            {statusLoading ? (
              <p className="text-sm text-zinc-400">Consultando…</p>
            ) : !status?.configured ? (
              <p className="text-sm text-zinc-400">WhatsApp não configurado. Preencha ao lado e salve — a instância é criada sozinha.</p>
            ) : connected ? (
              <>
                <p className="text-sm text-emerald-300 flex items-center gap-1">
                  <CheckCircle size={15} /> Conectado{status.phone ? ` · ${status.phone}` : ''}. Pode usar o chat.
                </p>
                {isAdmin ? (
                  <div className="mt-3">
                    <button type="button" onClick={handleDisconnect} disabled={discLoading}
                      className="px-4 py-2 rounded-lg bg-red-800 hover:bg-red-700 text-sm disabled:opacity-50">
                      {discLoading ? 'Desconectando…' : 'Desconectar conta'}
                    </button>
                    <p className="text-[11px] text-zinc-500 mt-2">
                      Desconecta este aparelho sem apagar conversas. Para parear outra conta, desconecte e gere um QR novo.
                    </p>
                  </div>
                ) : (
                  <p className="text-[11px] text-zinc-500 mt-2">Só ADMIN desconecta a conta.</p>
                )}
                {discMsg && <p className="text-xs text-zinc-300 mt-2">{discMsg}</p>}
              </>
            ) : (
              <>
                <p className="text-sm text-zinc-300 mb-3">
                  Estado: <b>{status.connection}</b>. Gere o QR e leia com o WhatsApp do celular (Aparelhos conectados).
                </p>
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <button type="button" onClick={handleQr} disabled={qrLoading}
                    className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm disabled:opacity-50">
                    {qrLoading ? 'Gerando…' : qrBase64 ? 'Gerar novo QR code' : 'Gerar QR code'}
                  </button>
                  {isAdmin && (
                    <button type="button" onClick={handleDisconnect} disabled={discLoading} title="Forçar desconexão da sessão (se o aparelho travou conectado)"
                      className="px-4 py-2 rounded-lg border border-red-900 text-red-300 hover:bg-red-950/40 text-sm disabled:opacity-50">
                      {discLoading ? 'Desconectando…' : 'Desconectar conta'}
                    </button>
                  )}
                </div>
                {discMsg && <p className="text-xs text-zinc-300 mb-2">{discMsg}</p>}
                {qrError && <p className="text-xs text-red-400">{qrError}</p>}
                {qrBase64 && (
                  <div>
                    <img src={`data:image/png;base64,${qrBase64}`} alt="QR code do WhatsApp"
                      className="w-56 h-56 bg-white rounded-lg" />
                    <p className="text-xs text-zinc-500 mt-2">O QR vale ~3 min. Se expirar, gere outro.</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {isNewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setIsNewModalOpen(false)}>
          <div className="glass-panel w-full max-w-sm p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-4">
              <MessageCircle size={17} className="text-emerald-400" />
              <h3 className="font-semibold">Nova conversa</h3>
              <div className="flex-1" />
              <button type="button" onClick={() => setIsNewModalOpen(false)} title="Fechar">
                <X size={17} />
              </button>
            </div>
            <form onSubmit={handleNewConversation} className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400">Telefone (com DDI e DDD)</label>
                <input value={newPhone} onChange={(e) => setNewPhone(e.target.value)}
                  placeholder="5555999998888"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
              </div>
              <div>
                <label className="text-xs text-zinc-400">Nome (opcional)</label>
                <input value={newName} onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
              </div>
              {newError && <p className="text-xs text-red-400">{newError}</p>}
              <button type="submit" className="w-full px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-sm">
                Abrir conversa
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
