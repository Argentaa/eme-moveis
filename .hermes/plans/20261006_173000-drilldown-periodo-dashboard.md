# Pedidos do cliente (vídeo 2026-10-01) — período + drill-down nos dashboards

Origem: transcrição do vídeo (áudio): 3 pedidos — (1) filtro mensal/tri/sem/anual nos
dashboards, (2) cards clicáveis com drill-down (quais vendas / qual conta), (3) dashboard
inicial abrindo no mês corrente (bug: dia 1º sem venda mostrando "2 vendas").

Ordem de execução: (3) → (1) → (2). Push ao fechar + rebuild manual no painel (usuário).

## Achados da análise (código vs. produção no vídeo)

- Comercial e Produção JÁ têm `PeriodFilter` estilo DRE (commit bec8997, pushado). Falta:
  Fluxo de Caixa do Financeiro (só `?year=`) e Dashboard Executivo (mês/ano avulso).
- `GET /api/reports/crm` aceita `?year=&month=&period=` mas `_build_crm` ignora mês/período
  em `conversao` (conta fechados de TODOS os tempos) e `ticket_medio`. É o bug do pedido (3):
  `DashboardView` chama `crmReport()` sem params e o card "Vendas realizadas" mistura
  anual no mês. Prova: dia 1º, `entriesTotal=0` (mês) vs "2 vendas" (all-time).
- Nenhum card é clicável. Mas os dados do drill-down já existem: aging + lista vêm juntos
  no `FinancialAgingPanel`; `GET /api/sales` lista vendas com cliente/data/valor.
- `CashFlowChart` é genérico por linha (só lê keys month/income/outcome/...) — bucket
  tri/sem/anual no backend não exige mudar o gráfico.
- `clients.closed_at` (ou `sale_concluded_at`) é a data do fechamento; FECHAMENTO sem data
  (arrasto p/ ganho não grava, fluxo antigo) = `undated` — declarar, não somar (convenção).

## Fase A — backend TDD (reports_bp.py + tests/test_api.py)

A1. Helper `_crm_range(year, month, period) -> (d0, d1)`: mensal→o mês; trimestral→tri que
    contém o mês; semestral→semestre que contém o mês; anual→o ano.
A2. `conversao` passa a ser do período: fechados = FECHAMENTO ou sale_concluded_at, com
    data (closed_at→sale_concluded_at) dentro de [d0,d1]; sem data → `undated` (fora da
    conta, declarado). `taxa` = fechados ÷ clientes criados no período (0 se vazio).
    Contrato preservado p/ teste existente (conclude-sale data = hoje → conta no default).
A3. Novo bloco `fechamentos_periodo`: união Sales (sale_date no range) + CRM fechados com
    data no range, dedup por client_id (Sale vence), `itens=[{client_id,name,data,valor,
    origem}]` ordenados por data desc + `undated`. Fonte do card + modal.
A4. `vendas_mes`/`vendas_ano` ganham `itens` (mesmo shape) p/ modal sem fetch extra.
A5. `_build_cash_flow` aceita `?period=` (default mensal = saída idêntica): trimestral→4
    linhas T1-T4, semestral→S1-S2, anual→1 linha; acumulado corrido nos buckets.
A6. Testes novos (acrescentar no fim do test_api.py via patch com âncora — arquivo >180KB,
    não usar write_file): conversao respeita mês + undated; fechamentos dedup Sale×CRM;
    itens em vendas_mes/ano; cash-flow trimestral (4 linhas, T1 soma certo; default 12).
    Rodar `-k` isolado e depois a suíte inteira (`/usr/local/bin/pytest`).

## Fase B — frontend (tipos + 4 telas)

B1. `types.ts`: `FechamentoItem` + `fechamentos_periodo` no CrmReport; `itens` em
    vendas_mes/vendas_ano.
B2. Novo `SalesDrillModal.tsx` (presentational: open/onClose/título/itens; totais
    calculados dentro; padrão `fixed inset-0 z-50` + painel `max-h-[92vh] flex flex-col`,
    header `shrink-0`, lista `overflow-y-auto`; fora de condicional de aba).
B3. `DashboardView`: passa `{year, month, period:'mensal'}` (mês selecionado) ao crmReport
    — recarrega ao trocar de mês (mover p/ o effect mensal junto de weekly/goal); card
    "Vendas realizadas" = fechamentos_periodo.qtd + "em {mês}" + clique → modal; nota
    "N sem data" quando undated>0. Adiciona toggle de período (Mensal/Tri/Sem/Anual) que
    recorta entradas/saídas/consumo locais pelo range (espelho do quickRange) e o
    crmReport; semanal/meta continuam mensais; "últimos 12 meses" continua trailing.
B4. `FinancialView` Fluxo de Caixa: `PeriodFilter` (ano+período) → `cash-flow {year,period,
    mode}`; tabela e gráfico reusados sem mudança (linhas genéricas).
B5. `CommercialDashboard`: cards "Vendas do mês/ano" clicáveis → modal com
    vendas_mes.itens / vendas_ano.itens.
B6. `FinancialAgingPanel`: buckets + card "Vencidas" clicáveis filtram a lista abaixo
    (mesma regra do backend: dias>0 vencidas; >=-7 →0_7; >=-30 →8_30; senão acima_30;
    null só aparece em "todas"); clique de novo limpa; destaque ring no selecionado.
B7. Gates: `npm run lint` (tsc) + `npm run build`. Sem vitest/playwright.

## Fora do escopo (declarado)

- `ticket_medio`, `orcamentos`, `negociacoes.por_etapa` (snapshot do pipeline) continuam
  all-time; `fontes_lead`, `top_products`, parceiros idem.
- Sem paginação em `GET /api/sales` (base pequena; modal usa `itens` do relatório).
- Sem acesso a produção neste ciclo (docker bloqueado): deploy = push + rebuild manual
  no painel pelo usuário + smoke (conferir asset novo e alembic_version).

## Fechamento

Commit+push, confirmar `git ls-remote origin main` == HEAD; entradas no
`DEFAULT_CHANGELOG_ENTRIES` (Novidades, pela Donna); atualizar skill eme-moveis-ops
(fechamentos_periodo, cash-flow ?period=, cards clicáveis); resumo final por área/fase
com gates e pendências do usuário (rebuild + smoke).
