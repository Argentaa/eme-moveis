# WhatsApp: sincronizar celular→ERP + visual estilo WhatsApp Web

Pedidos do dono: (1) mensagem enviada pelo celular não aparece no ERP — só a
resposta do cliente; (2) página do WhatsApp com cara de WhatsApp Web, no estilo
do sistema.

## Causa do (1) — confirmada no código

`_store_inbound` (whatsapp_bp.py) descarta tudo com `fromMe=True`. O que é
enviado pelo celular chega no webhook como `messages.upsert` com `fromMe=True`
(remoteJid = o contato, igual ao inbound) e hoje é ignorado. O teste
`test_whatsapp_webhook_ignora_fromme_e_outros_eventos` congela esse
comportamento — será atualizado.

## Fase A — backend TDD (whatsapp_bp.py + test_api.py)

A1. `_store_inbound` grava fromMe como `direction="out"` (não ignora mais);
    pushName do fromMe NÃO sobrescreve o nome da conversa (é o próprio dono);
    `messageTimestamp` do item vira `created_at` da linha (histórico sincronizado
    mantém a ordem real); `last_message_at` acompanha o maior tempo.
A2. `_extract_provider_id(resp)`: id da Evolution no retorno do envio
    (`key.id` → `id` → `messageId`); `send_message` grava no `provider_id` da
    linha `out`. Sem isso, o eco do envio do ERP (webhook fromMe com o mesmo
    id) duplicaria a mensagem — o dedupe existente por `provider_id` passa a
    cobrir os dois sentidos.
A3. `POST /api/whatsapp/conversations/<id>/sync`: puxa o histórico da
    Evolution (`POST /chat/findMessages/{instance}` com `where.key.remoteJid`,
    fallback `where.remoteJid`; normaliza `records|messages|data|result` em
    lista) e passa cada item pelo `_store_inbound` (dedupe natural por
    provider_id). Devolve `{ok, stored, duplicate, ignored}`. Sem config →
    409; sem conversa → 404; Evolution fora → 502 honesto.
A4. Testes: fromMe gravado como `out` (atualiza o teste do ignora); eco do
    envio do ERP não duplica (mock `_evo_call` no send + webhook com mesmo
    id); sync puxa in+out e a 2ª chamada só dedupa (mock `_evo_call`).

## Fase B — frontend (api.ts + WhatsappView.tsx)

B1. `whatsappService.sync(id)` → POST do A3.
B2. Aba Conversas vira layout WhatsApp Web no tema do sistema: painel único
    flex `h-[70vh]` (lista 1/3 + thread 2/3), header da lista com status + nova
    conversa, busca arredondada, itens com avatar de iniciais + hora + preview
    ("Você: …") + badge de não-lidas; thread com header (avatar, nome, telefone,
    cliente) + botões sincronizar/atualizar, área com divisores de dia, bolhas
    (out = verde-escuro, in = zinc) com hora + check, barra de digitação
    arredondada. Aba Config inalterada. Auto-seleciona a 1ª conversa.
B3. Gates: `npm run lint` (tsc) + `vite build`.

## Fora do escopo

- Grupos (`@g.us`) continuam ignorados; `messages.update` (lido/recebido)
  continua ignorado — sem duplo-tique azul real.
- Sem paginação no sync (teto 200 mensagens por sincronização).
- Sem acesso a produção neste ciclo: deploy = push + rebuild manual no painel
  + smoke (enviar pelo celular → Sincronizar → mensagem aparece).

## Fechamento

Commit+push, `git ls-remote origin main` == HEAD; Novidades (2 entradas pela
Donna); skill eme-moveis-ops (fromMe=out, provider_id no envio, endpoint sync,
novo visual); resumo final com gates e pendências do usuário.
