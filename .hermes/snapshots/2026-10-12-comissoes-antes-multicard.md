# Retrato PRÉ-multi-card — 12/10/2026 (~19h, produção `eme`)

Guarda de precaução antes da tabela `deals` (plano `2026-10-12_161500-multi-card-deals.md`).
Depois da entrega, recalcular e comparar — o critério NOVO deve continuar dando
os mesmos números abaixo até que uma venda nova seja gerada.

- **Dump integral do banco:** `cache/scratch/eme-deals/eme_pre_multicard_20261012.dump` (no host, fora do repo)
- **Código em produção:** commit `a36b738` (reabertura de negociação + comissões por Sale)
- **Regras de comissão cadastradas:** nenhuma (tudo cai em "sem atribuição" até criarem regra)

## Vendas geradas (6)

| Código | Cliente | Data da venda | Valor | Vendedor |
|---|---|---|---|---|
| V-0003 | Gustavo Lopes | 03/08/2026 | 4.500,00 | SEM VENDEDOR |
| V-0002 | Murilo Dalmolin Romitti | 19/08/2026 | 15.000,00 | SEM VENDEDOR |
| V-0001 | Elisandra Lucas | 25/08/2026 | 3.695,00 | SEM VENDEDOR |
| V-0004 | Manúcia Piaia | 21/09/2026 | 12.570,00 | joao |
| V-0006 | Elisandra Lucas | 08/10/2026 | 3.990,00 | joao |
| V-0005 | Raquel Laís Antunes | 09/10/2026 | 5.705,00 | joao |

## Critério NOVO (vale desde o deploy de hoje) — `Sale.sale_date` × `total_value`

| Mês | Qtd | Total |
|---|---|---|
| 2026-08 | 3 | 23.195,00 |
| 2026-09 | 1 | 12.570,00 |
| 2026-10 | 2 | 9.695,00 |

3 vendas sem vendedor (V-0001/2/3) → "sem atribuição", não entram na conta de ninguém.

## Critério ANTIGO (antes de hoje) — `clients.closed_at` × `estimated_value`

| Mês | Qtd | Total |
|---|---|---|
| 2026-09 | 1 | 12.570,00 (Manúcia) |
| 2026-10 | 4 | 40.000,00 (Murilo 15.000 + Raquel 25.000 + Gustavo 0 + Elisandra 0) |

Agosto no critério antigo dava zero (ninguém tinha "concluído" em agosto).
