import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import {
  MessageCircle, QrCode, Send, Paperclip, RefreshCw, Plus, X,
  CheckCircle, Phone, Download, Settings, Wifi, WifiOff, CheckCheck,
  Pencil, Trash2, CornerUpLeft, Zap,
} from 'lucide-react';
import { api, whatsappService, clientService, getApiErrorMessage } from '../services/api';
import type {
  WhatsappConversation, WhatsappMessage, WhatsappStatus, WhatsappQuickReply, Client,
} from '../types';
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
  const canManage = userRole === 'ADMIN' || userRole === 'GERENTE';

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

  // ── resposta citando / reação / respostas rápidas ──────────────────
  const [replyTo, setReplyTo] = useState<WhatsappMessage | null>(null);
  const [reactingId, setReactingId] = useState<string | null>(null);
  const [quickReplies, setQuickReplies] = useState<WhatsappQuickReply[]>([]);
  const [quickOpen, setQuickOpen] = useState(false);
  const [quickError, setQuickError] = useState('');
  const [isQuickManageOpen, setIsQuickManageOpen] = useState(false);
  const [quickForm, setQuickForm] = useState({ id: '', title: '', body: '' });
  const [quickSaving, setQuickSaving] = useState(false);
  const [listFilter, setListFilter] = useState<'all' | 'unread' | 'client'>('all');
  const [avatarUrl, setAvatarUrl] = useState('');
  // "digitando…" não pode virar enxurrada: no máximo 1 envio a cada 8 s.
  const presenceAt = useRef(0);

  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [newName, setNewName] = useState('');
  const [newError, setNewError] = useState('');

  // ── editar conversa (nome + vínculo com cliente, só no ERP) ──────────
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editClientId, setEditClientId] = useState('');
  const [clientsList, setClientsList] = useState<Client[]>([]);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const [deleting, setDeleting] = useState(false);

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

  const loadQuickReplies = useCallback(async () => {
    try {
      setQuickReplies(await whatsappService.quickReplies());
    } catch {
      setQuickReplies([]);
    }
  }, []);

  useEffect(() => {
    loadQuickReplies();
  }, [loadQuickReplies]);

  // Trocar de conversa limpa a citação pendente e o painel de respostas.
  useEffect(() => {
    setReplyTo(null);
    setQuickOpen(false);
    setAvatarUrl('');
    if (!selectedId) return;
    let alive = true;
    whatsappService.avatar(selectedId)
      .then((r) => { if (alive) setAvatarUrl(r.url || ''); })
      .catch(() => { /* sem foto: fica nas iniciais */ });
    return () => { alive = false; };
  }, [selectedId]);

  // Digitar avisa o cliente ("digitando…"), no máximo 1 vez a cada 8 s.
  useEffect(() => {
    if (!selectedId || !draft.trim()) return;
    const now = Date.now();
    if (now - presenceAt.current < 8000) return;
    presenceAt.current = now;
    whatsappService.presence(selectedId, 'composing').catch(() => { /* presença é enfeite */ });
  }, [draft, selectedId]);

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

  // Atualiza o thread aberto a cada 5 s e marca como lido ao abrir.
  useEffect(() => {
    if (activeTab !== 'conversas' || !selectedId) return;
    loadMessages(selectedId);
    whatsappService.markRead(selectedId)
      .then(() => loadConversations())
      .catch(() => { /* badge local já zerou no backend */ });
    const t = setInterval(() => loadMessages(selectedId), 5000);
    return () => clearInterval(t);
  }, [activeTab, selectedId, loadMessages, loadConversations]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const selected = conversations.find((c) => c.id === selectedId) || null;
  const filtered = conversations.filter((c) => {
    if (listFilter === 'unread' && !(c.unread || 0)) return false;
    if (listFilter === 'client' && !c.client_id) return false;
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return c.phone.includes(q) || (c.name || '').toLowerCase().includes(q)
      || (c.client_name || '').toLowerCase().includes(q);
  });
  const totalUnread = conversations.reduce((soma, c) => soma + (c.unread || 0), 0);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!selected || sending) return;
    if (!draft.trim() && !attachFile) return;
    setSending(true);
    setSendError('');
    try {
      if (attachFile) {
        await whatsappService.sendMedia(selected.id, attachFile, draft.trim(), replyTo?.id || null);
        setAttachFile(null);
      } else {
        await whatsappService.sendText(selected.id, draft.trim(), replyTo?.id || null);
      }
      setDraft('');
      setReplyTo(null);
      whatsappService.presence(selected.id, 'paused').catch(() => { /* opcional */ });
      await loadMessages(selected.id);
      await loadConversations();
    } catch (err) {
      setSendError(getApiErrorMessage(err, 'Falha ao enviar. Tente de novo.'));
    } finally {
      setSending(false);
    }
  }

  /** Reação: clicar no mesmo emoji remove (reaction vazia). */
  async function handleReact(m: WhatsappMessage, emoji: string) {
    if (reactingId) return;
    setReactingId(m.id);
    setSendError('');
    try {
      const updated = await whatsappService.react(m.id, m.reaction === emoji ? '' : emoji);
      setMessages((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setSendError(getApiErrorMessage(err, 'Não foi possível reagir.'));
    } finally {
      setReactingId(null);
    }
  }

  /** Apaga para todos — some também no celular do cliente. */
  async function handleDeleteMessage(m: WhatsappMessage) {
    if (!window.confirm('Apagar esta mensagem para todos? Ela some também no celular do cliente.')) return;
    setSendError('');
    try {
      const updated = await whatsappService.removeMessage(m.id);
      setMessages((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setSendError(getApiErrorMessage(err, 'Não foi possível apagar a mensagem.'));
    }
  }

  /** Resposta rápida: troca {nome} pelo primeiro nome do contato/cliente. */
  function applyQuickReply(q: WhatsappQuickReply) {
    const nome = ((selected?.client_name || selected?.name || '').trim().split(/\s+/)[0]) || 'cliente';
    const texto = q.body.replace(/\{nome\}/g, nome);
    setDraft((prev) => (prev ? `${prev} ${texto}` : texto));
    setQuickOpen(false);
  }

  function openQuickManage() {
    setQuickError('');
    setQuickForm({ id: '', title: '', body: '' });
    setIsQuickManageOpen(true);
    setQuickOpen(false);
  }

  async function handleQuickSave(e: FormEvent) {
    e.preventDefault();
    if (quickSaving) return;
    if (!quickForm.title.trim() || !quickForm.body.trim()) {
      setQuickError('Título e texto são obrigatórios.');
      return;
    }
    setQuickSaving(true);
    setQuickError('');
    try {
      const payload = { title: quickForm.title.trim(), body: quickForm.body.trim() };
      if (quickForm.id) await whatsappService.updateQuickReply(quickForm.id, payload);
      else await whatsappService.createQuickReply(payload);
      setQuickForm({ id: '', title: '', body: '' });
      await loadQuickReplies();
    } catch (err) {
      setQuickError(getApiErrorMessage(err, 'Não foi possível salvar.'));
    } finally {
      setQuickSaving(false);
    }
  }

  async function handleQuickDelete(id: string) {
    if (!window.confirm('Excluir esta resposta rápida?')) return;
    setQuickError('');
    try {
      await whatsappService.removeQuickReply(id);
      await loadQuickReplies();
    } catch (err) {
      setQuickError(getApiErrorMessage(err, 'Não foi possível excluir.'));
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

  /** Abre o modal de edição com os dados atuais + cadastro de clientes. */
  async function openEdit() {
    if (!selected) return;
    setEditError('');
    setEditName(selected.name || '');
    setEditClientId(selected.client_id || '');
    setIsEditOpen(true);
    try {
      const list = await clientService.getAll();
      setClientsList([...list].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')));
    } catch {
      setClientsList([]);
    }
  }

  async function handleEditSave(e: FormEvent) {
    e.preventDefault();
    if (!selected || editSaving) return;
    setEditSaving(true);
    setEditError('');
    try {
      await whatsappService.update(selected.id, {
        name: editName.trim(),
        client_id: editClientId || null,
      });
      setIsEditOpen(false);
      await loadConversations();
    } catch (err) {
      setEditError(getApiErrorMessage(err, 'Não foi possível salvar.'));
    } finally {
      setEditSaving(false);
    }
  }

  /** Apaga a conversa só no ERP (o celular não é tocado). */
  async function handleDelete() {
    if (!selected || deleting) return;
    const label = selected.name || selected.phone;
    if (!window.confirm(`Apagar a conversa com "${label}" e as ${messages.length} mensagem(ns)? Isso limpa só o ERP — no celular continua tudo.`)) return;
    setDeleting(true);
    try {
      await whatsappService.remove(selected.id);
      setSelectedId(null);
      setMessages([]);
      setSyncMsg('');
      await loadConversations();
    } catch (err) {
      setSendError(getApiErrorMessage(err, 'Não foi possível apagar a conversa.'));
    } finally {
      setDeleting(false);
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
        {totalUnread > 0 && (
          <span className="text-[11px] font-bold bg-emerald-600 text-white rounded-full min-w-5 h-5 px-1.5 flex items-center justify-center"
            title="Mensagens não lidas">
            {totalUnread}
          </span>
        )}
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
                <div className="flex items-center gap-1 mt-2">
                  {([['all', 'Todas'], ['unread', 'Não lidas'], ['client', 'Com cliente']] as const).map(([id, label]) => (
                    <button key={id} type="button" onClick={() => setListFilter(id)}
                      className={`text-[11px] px-2.5 py-1 rounded-full border transition ${listFilter === id
                        ? 'bg-emerald-800/60 border-emerald-700 text-emerald-200'
                        : 'border-zinc-800 text-zinc-400 hover:bg-zinc-800/60'}`}>
                      {label}{id === 'unread' && totalUnread > 0 ? ` (${totalUnread})` : ''}
                    </button>
                  ))}
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
                    {avatarUrl ? (
                      <img src={avatarUrl} alt={selected.name || selected.phone}
                        className="w-9 h-9 rounded-full object-cover shrink-0 bg-zinc-800"
                        onError={() => setAvatarUrl('')} />
                    ) : (
                      <span className={`w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${avatarTone(selected.phone)}`}>
                        {initials(selected.name || selected.phone)}
                      </span>
                    )}
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
                    {canManage && (
                      <>
                        <button type="button" title="Editar nome e vínculo com cliente" onClick={openEdit}
                          className="p-2 rounded-full bg-zinc-800 hover:bg-zinc-700 shrink-0">
                          <Pencil size={14} />
                        </button>
                        <button type="button" title="Apagar conversa (só no ERP)" onClick={handleDelete} disabled={deleting}
                          className="p-2 rounded-full bg-zinc-800 hover:bg-red-900 text-zinc-300 hover:text-red-200 disabled:opacity-50 shrink-0">
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
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
                      const citada = m.reply_to_id ? messages.find((x) => x.id === m.reply_to_id) : null;
                      return (
                        <div key={m.id}>
                          {showDay && (
                            <div className="flex justify-center my-3">
                              <span className="text-[11px] font-mono text-zinc-400 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1">
                                {dayLabel(m.created_at)}
                              </span>
                            </div>
                          )}
                          <div className={`flex items-end gap-1.5 ${out ? 'justify-end' : 'justify-start'} mb-1.5 group`}>
                            {/* Ações no hover: reagir, responder citando, apagar para todos */}
                            <div className={`flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition shrink-0 ${out ? 'order-1' : 'order-2'}`}>
                              {['👍', '❤️', '😂'].map((emoji) => (
                                <button key={emoji} type="button" title={`Reagir ${emoji}`}
                                  onClick={() => handleReact(m, emoji)}
                                  disabled={reactingId === m.id}
                                  className="text-sm leading-none p-1 rounded hover:bg-zinc-800 disabled:opacity-40">
                                  {emoji}
                                </button>
                              ))}
                              <button type="button" title="Responder citando" onClick={() => setReplyTo(m)}
                                className="p-1 rounded text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
                                <CornerUpLeft size={13} />
                              </button>
                              {out && !m.deleted && m.provider_id && (
                                <button type="button" title="Apagar para todos" onClick={() => handleDeleteMessage(m)}
                                  className="p-1 rounded text-zinc-400 hover:bg-red-900/60 hover:text-red-200">
                                  <Trash2 size={13} />
                                </button>
                              )}
                            </div>
                            <div className={`${out ? 'order-2' : 'order-1'} max-w-[85%] sm:max-w-[75%] px-3 py-2 text-sm shadow ${out ? 'bg-emerald-900/90 text-zinc-100 rounded-lg rounded-tr-none' : 'bg-zinc-800 text-zinc-100 rounded-lg rounded-tl-none'}`}>
                              {citada && (
                                <div className={`mb-1 rounded border-l-2 pl-2 py-0.5 text-[11px] ${out ? 'border-emerald-400/70 bg-emerald-950/40' : 'border-zinc-500 bg-zinc-900/60'}`}>
                                  <div className="font-semibold opacity-90">
                                    {citada.direction === 'out' ? 'Você' : (selected.name || selected.phone)}
                                  </div>
                                  <div className="truncate opacity-80">
                                    {citada.body || (citada.deleted ? 'Mensagem apagada' : kindLabel(citada.kind))}
                                  </div>
                                </div>
                              )}
                              <MediaPreview m={m} />
                              {m.deleted ? (
                                <div className="italic opacity-70">Mensagem apagada</div>
                              ) : (
                                <>
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
                                </>
                              )}
                              {m.reaction && (
                                <div className="mt-1">
                                  <span className="inline-block text-xs bg-zinc-900/70 border border-zinc-700 rounded-full px-1.5 py-0.5">
                                    {m.reaction}
                                  </span>
                                </div>
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
                  {quickOpen && (
                    <div className="mx-3 mb-1 max-h-48 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-900/95 p-2">
                      <div className="flex items-center justify-between mb-1 px-1">
                        <span className="text-[11px] uppercase tracking-wide text-zinc-500">Respostas rápidas</span>
                        {canManage && (
                          <button type="button" onClick={openQuickManage}
                            className="text-[11px] text-emerald-300 hover:underline">Gerenciar</button>
                        )}
                      </div>
                      {quickReplies.length === 0 ? (
                        <p className="text-xs text-zinc-500 px-1 py-2">Nenhuma resposta cadastrada.</p>
                      ) : (
                        <ul className="space-y-1">
                          {quickReplies.map((q) => (
                            <li key={q.id}>
                              <button type="button" onClick={() => applyQuickReply(q)}
                                className="w-full text-left px-2 py-1.5 rounded hover:bg-zinc-800">
                                <span className="block text-xs font-medium text-zinc-200">{q.title}</span>
                                <span className="block text-[11px] text-zinc-500 truncate">{q.body}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {replyTo && (
                    <div className="mx-3 mt-2 flex items-start gap-2 rounded-lg border-l-2 border-emerald-600 bg-zinc-800/80 px-2 py-1.5">
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-semibold text-emerald-300">
                          Respondendo {replyTo.direction === 'out' ? 'sua mensagem' : (selected.name || selected.phone)}
                        </div>
                        <div className="text-[11px] text-zinc-400 truncate">
                          {replyTo.body || (replyTo.deleted ? 'Mensagem apagada' : kindLabel(replyTo.kind))}
                        </div>
                      </div>
                      <button type="button" onClick={() => setReplyTo(null)} title="Cancelar citação">
                        <X size={13} />
                      </button>
                    </div>
                  )}
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
                    <button type="button" title="Respostas rápidas" onClick={() => setQuickOpen((v) => !v)}
                      className={`p-2.5 rounded-full shrink-0 ${quickOpen ? 'bg-emerald-800 text-emerald-200' : 'bg-zinc-800 hover:bg-zinc-700'}`}>
                      <Zap size={16} />
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

      {isEditOpen && selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setIsEditOpen(false)}>
          <div className="glass-panel w-full max-w-sm p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-4">
              <Pencil size={17} className="text-emerald-400" />
              <h3 className="font-semibold">Editar conversa</h3>
              <div className="flex-1" />
              <button type="button" onClick={() => setIsEditOpen(false)} title="Fechar">
                <X size={17} />
              </button>
            </div>
            <form onSubmit={handleEditSave} className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400">Telefone</label>
                <input value={selected.phone} disabled
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1 text-zinc-500" />
              </div>
              <div>
                <label className="text-xs text-zinc-400">Nome / apelido (vazio = mostra o telefone)</label>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} maxLength={160}
                  placeholder={selected.phone}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1" />
              </div>
              <div>
                <label className="text-xs text-zinc-400">Cliente vinculado</label>
                <select value={editClientId} onChange={(e) => setEditClientId(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm mt-1">
                  <option value="">Sem vínculo</option>
                  {selected.client_id && !clientsList.some((c) => c.id === selected.client_id) && (
                    <option value={selected.client_id}>Vinculado atualmente</option>
                  )}
                  {clientsList.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}{c.phone ? ` · ${c.phone}` : ''}
                    </option>
                  ))}
                </select>
              </div>
              {editError && <p className="text-xs text-red-400">{editError}</p>}
              <button type="submit" disabled={editSaving}
                className="w-full px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-sm disabled:opacity-50">
                {editSaving ? 'Salvando…' : 'Salvar'}
              </button>
            </form>
          </div>
        </div>
      )}

      {isQuickManageOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setIsQuickManageOpen(false)}>
          <div className="glass-panel w-full max-w-lg max-h-[92vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-zinc-800 shrink-0">
              <Zap size={17} className="text-emerald-400" />
              <h3 className="font-semibold">Respostas rápidas</h3>
              <div className="flex-1" />
              <button type="button" onClick={() => setIsQuickManageOpen(false)} title="Fechar">
                <X size={17} />
              </button>
            </div>
            <div className="px-5 py-3 overflow-y-auto flex-1 overscroll-contain space-y-3">
              <ul className="space-y-1">
                {quickReplies.map((q) => (
                  <li key={q.id} className="flex items-start gap-2 rounded-lg border border-zinc-800 px-2 py-1.5">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium">{q.title}</div>
                      <div className="text-[11px] text-zinc-400 truncate">{q.body}</div>
                    </div>
                    <button type="button" title="Editar"
                      onClick={() => setQuickForm({ id: q.id, title: q.title, body: q.body })}
                      className="p-1 text-zinc-400 hover:text-zinc-100">
                      <Pencil size={13} />
                    </button>
                    <button type="button" title="Excluir" onClick={() => handleQuickDelete(q.id)}
                      className="p-1 text-zinc-400 hover:text-red-300">
                      <Trash2 size={13} />
                    </button>
                  </li>
                ))}
              </ul>
              <form onSubmit={handleQuickSave} className="space-y-2 border-t border-zinc-800 pt-3">
                <div className="text-xs text-zinc-400">
                  {quickForm.id ? 'Editando resposta' : 'Nova resposta'}
                </div>
                <input value={quickForm.title} maxLength={80}
                  onChange={(e) => setQuickForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="Título (ex.: Prazo de entrega)"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm" />
                <textarea value={quickForm.body} rows={3}
                  onChange={(e) => setQuickForm((f) => ({ ...f, body: e.target.value }))}
                  placeholder="Texto. Use {nome} para o nome do cliente."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm resize-y" />
                {quickError && <p className="text-xs text-red-400">{quickError}</p>}
                <div className="flex items-center gap-2">
                  <button type="submit" disabled={quickSaving}
                    className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-sm disabled:opacity-50">
                    {quickSaving ? 'Salvando…' : quickForm.id ? 'Salvar alterações' : 'Adicionar'}
                  </button>
                  {quickForm.id && (
                    <button type="button" onClick={() => setQuickForm({ id: '', title: '', body: '' })}
                      className="text-xs text-zinc-400 hover:text-zinc-200">
                      Cancelar edição
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
