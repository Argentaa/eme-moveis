# Venda direta sem produção + multi-card por cliente

Respostas do dono (clarify 2026-10-06):
1. FECHAMENTO já produzido/entregue → SÓ registrar a venda (sem financeiro).
2. Função mora em BOTÃO EM CADA CARD do FECHAMENTO.
3. Multi-card = VÁRIOS CARDS DO MESMO CADASTRO (mesmo cliente, projetos diferentes).

## Parte A — venda direta sem produção (implementar agora)

Escopo pequeno e seguro: novo endpoint + botão no card.

- `POST /api/clients/<id>/register-direct-sale` (ADMIN/GERENTE):
  body {sale_date?, total_value?} — default data=hoje, valor=negotiation_value
  ou estimated_value do card. Valida total>0. Cria `Sale` (code V-NNNN,
  down_payment=0, installments=0) SEM FinancialRecord e SEM Project. Marca
  `sale_concluded_at`/`closed_at` (se null, idempotente como o conclude-sale) —
  o card sai do funil pelo mesmo filtro (`sale_concluded_at`). Log SISTEMA.
  Devolve `_sale_detail`. 404 sem cliente.
- Front (`ClientsView`): botão "Registrar venda" SÓ nos cards da ÚLTIMA coluna
  do funil (descoberto por position, não pelo nome — coluna renomeável):
  modal pequeno com valor (prefill displayValue) + data (hoje) + confirmar.
  `clientService.registerDirectSale`. Após salvar: reload + aviso de que não
  gerou financeiro nem produção.
- Relatórios: a Sale entra em vendas_mes/ano, fechamentos_periodo, meta e
  comissão via `closed_at` — igual à Gerar venda, menos financeiro/produção.
- Testes: cria Sale sem financial/project; usa negotiation_value por default;
  400 sem valor; idempotente nas flags; card sai do funil (sale_concluded_at).
- Sem migração (só código). Push + rebuild manual.

## Parte B — vários cards do MESMO cadastro (NÃO implementar sem aprovar)

Diagnóstico honesto: hoje `Client` = cadastro + card (1:1). Um card = uma linha
com `funnel_id`+`funnel_status`. O "Vincular" move a LINHA entre funis — por
isso o mesmo cliente não aparece 2x no mesmo funil. Permitir N cards do mesmo
cadastro exige entidade nova (oportunidade/negociação):

- Nova tabela `crm_opportunities` (id, client_id FK, funnel_id, funnel_status,
  estimated_value/negotiation_value, seller_id, lead_source, sale_concluded_at,
  closed_at, lost_reason, created_at) + migração com backfill (1 opportunity
  por Client com funnel_id, copiando os campos do funil).
- `ClientsView`: kanban lê opportunities (join client p/ nome/telefone);
  arrastar/editar/concluir operam na opportunity; cadastro central segue sem
  funil. `ClientDetailModal`, `_build_crm` (por_etapa, conversao, ticket),
  goals/comissões (closed_at da opportunity), `POST /api/sales`
  (+opportunity_id) e drill-down (`fechamentos_periodo` por opportunity, não
  por client — hoje o dedup é por client_id e esconderia a 2ª venda do mesmo
  cliente) passam a ler a nova tabela.
- É refactor estrutural (backend + front + relatórios + testes), com migração
  em produção populada. Estimativa: não cabe como "botãozinho" junto da
  Parte A. Proposta: entregar A agora; B vira plano próprio com QA em PG
  temporário antes do deploy.

## Fechamento desta entrega (só Parte A)

Commit+push, `git ls-remote origin main` == HEAD; Novidades (1 entrada pela
Donna); skill eme-moveis-ops (register-direct-sale + diagnóstico multi-card);
resumo final com gates e pendências do usuário (rebuild + smoke).
