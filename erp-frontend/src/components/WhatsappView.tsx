import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import {
  MessageCircle, QrCode, Send, Paperclip, RefreshCw, Plus, X,
  CheckCircle, Phone, Download, Settings, Wifi, WifiOff,
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

function fmtTime(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="glass-panel p-3 md:col-span-1">
            <div className="flex items-center gap-2 mb-2">
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por número ou nome…"
                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm" />
              <button type="button" title="Atualizar" onClick={loadConversations}
                className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700">
                <RefreshCw size={15} />
              </button>
            </div>
            {convLoading ? (
              <p className="text-sm text-zinc-400 p-2">Carregando conversas…</p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-zinc-400 p-2">
                {status && !status.configured
                  ? 'WhatsApp ainda não configurado — abra a aba Configuração.'
                  : 'Nenhuma conversa ainda. Inicie uma ou aguarde mensagens.'}
              </p>
            ) : (
              <ul className="divide-y divide-zinc-800 max-h-[60vh] overflow-y-auto">
                {filtered.map((c) => (
                  <li key={c.id}>
                    <button type="button" onClick={() => setSelectedId(c.id)}
                      className={`w-full text-left px-3 py-2.5 hover:bg-zinc-800/60 ${selectedId === c.id ? 'bg-zinc-800/80' : ''}`}>
                      <div className="flex items-center gap-2">
                        <Phone size={14} className="text-zinc-500 shrink-0" />
                        <span className="font-medium text-sm truncate">{c.name || c.phone}</span>
                      </div>
                      <div className="text-xs text-zinc-400 truncate mt-0.5">
                        {c.phone}{c.client_name ? ` · ${c.client_name}` : ''}
                      </div>
                      <div className="text-xs text-zinc-500 truncate mt-0.5">
                        {c.last_direction === 'out' ? 'Você: ' : ''}{c.last_body || '—'}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="glass-panel p-3 md:col-span-2 flex flex-col min-h-[50vh]">
            {!selected ? (
              <p className="text-sm text-zinc-400 m-auto">Selecione uma conversa à esquerda.</p>
            ) : (
              <>
                <div className="border-b border-zinc-800 pb-2 mb-2">
                  <div className="font-medium">{selected.name || selected.phone}</div>
                  <div className="text-xs text-zinc-400">
                    {selected.phone}{selected.client_name ? ` · Cliente: ${selected.client_name}` : ' · Sem cliente vinculado'}
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto space-y-2 max-h-[50vh] pr-1">
                  {msgLoading && messages.length === 0 ? (
                    <p className="text-sm text-zinc-400">Carregando mensagens…</p>
                  ) : messages.length === 0 ? (
                    <p className="text-sm text-zinc-400">Nenhuma mensagem ainda.</p>
                  ) : messages.map((m) => (
                    <div key={m.id} className={`flex ${m.direction === 'out' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${m.direction === 'out' ? 'bg-emerald-800' : 'bg-zinc-800'}`}>
                        {m.kind !== 'text' && (
                          <div className="text-xs opacity-80 mb-1">[{kindLabel(m.kind)}]{m.media_filename ? ` ${m.media_filename}` : ''}</div>
                        )}
                        {m.body && <div className="whitespace-pre-wrap break-words">{m.body}</div>}
                        {m.has_media && (
                          <button type="button" onClick={() => handleDownload(m)}
                            className="mt-1 flex items-center gap-1 text-xs underline opacity-90">
                            <Download size={12} /> Baixar arquivo
                          </button>
                        )}
                        <div className="text-[11px] opacity-60 mt-1">{fmtTime(m.created_at)}</div>
                      </div>
                    </div>
                  ))}
                  <div ref={threadEndRef} />
                </div>
                {sendError && <p className="text-xs text-red-400 mt-2">{sendError}</p>}
                {attachFile && (
                  <div className="flex items-center gap-2 mt-2 text-xs bg-zinc-800 rounded-lg px-2 py-1.5">
                    <Paperclip size={12} />
                    <span className="truncate flex-1">{attachFile.name}</span>
                    <button type="button" onClick={() => setAttachFile(null)} title="Remover anexo">
                      <X size={13} />
                    </button>
                  </div>
                )}
                <form onSubmit={handleSend} className="flex items-center gap-2 mt-2">
                  <input ref={fileInputRef} type="file" className="hidden"
                    onChange={(e) => setAttachFile(e.target.files?.[0] || null)} />
                  <button type="button" title="Anexar foto ou arquivo"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 shrink-0">
                    <Paperclip size={16} />
                  </button>
                  <input value={draft} onChange={(e) => setDraft(e.target.value)}
                    placeholder={attachFile ? 'Legenda (opcional)…' : 'Digite a mensagem…'}
                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm" />
                  <button type="submit" disabled={sending || (!draft.trim() && !attachFile)}
                    className="p-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 shrink-0"
                    title="Enviar">
                    <Send size={16} />
                  </button>
                </form>
              </>
            )}
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
              <p className="text-sm text-emerald-300 flex items-center gap-1">
                <CheckCircle size={15} /> Conectado{status.phone ? ` · ${status.phone}` : ''}. Pode usar o chat.
              </p>
            ) : (
              <>
                <p className="text-sm text-zinc-300 mb-3">
                  Estado: <b>{status.connection}</b>. Gere o QR e leia com o WhatsApp do celular (Aparelhos conectados).
                </p>
                <button type="button" onClick={handleQr} disabled={qrLoading}
                  className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm disabled:opacity-50 mb-3">
                  {qrLoading ? 'Gerando…' : 'Gerar QR code'}
                </button>
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
