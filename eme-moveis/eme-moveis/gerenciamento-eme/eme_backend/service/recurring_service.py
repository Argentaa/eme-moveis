from datetime import date, timedelta
import calendar
from typing import Optional
from fastapi import HTTPException, status
from repo.recurring_repo import recurring_repo
from repo.financial_repo import financial_repo
from repo.stock_repo import stock_repo
from schemas.recurring import FinancialCreateExtended, FinancialMode, RecurringFrequency


def calc_next_date(current: date, frequency: str) -> date:
    """Calcula a próxima data baseada na frequência."""
    if frequency == "SEMANAL":
        return current + timedelta(weeks=1)
    elif frequency == "QUINZENAL":
        return current + timedelta(days=15)
    elif frequency == "MENSAL":
        # Avança um mês mantendo o dia (ou último dia do mês se não existir)
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    elif frequency == "ANUAL":
        try:
            return date(current.year + 1, current.month, current.day)
        except ValueError:
            # 29/02 em ano não bissexto
            return date(current.year + 1, current.month, 28)
    return current


class RecurringService:

    async def _validate_category(self, category_name: str) -> None:
        category = await stock_repo.find_category_by_name(category_name, category_type="FINANCIAL")
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Categoria financeira '{category_name}' não existe.",
            )

    async def create_extended(self, data: FinancialCreateExtended) -> dict:
        """Cria lançamento normal, parcelado ou fixo."""
        await self._validate_category(data.category)

        start_date = data.date

        # ── PARCELADO ────────────────────────────────────────
        if data.mode == FinancialMode.PARCELADO:
            n = data.installments
            if not n or n < 2 or n > 60:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Número de parcelas deve ser entre 2 e 60.",
                )
            parcela_valor = round(data.amount / n, 2)
            # Ajuste de centavos na última parcela
            resto = round(data.amount - parcela_valor * n, 2)

            created = []
            current_date = start_date
            for i in range(1, n + 1):
                valor = parcela_valor + (resto if i == n else 0)
                row = await financial_repo.create(
                    description=f"{data.description} ({i}/{n})",
                    record_type=data.type,
                    category=data.category,
                    amount=valor,
                    date=str(current_date),
                    status="PENDENTE",
                    project_id=data.project_id,
                )
                created.append(row)
                if i < n:
                    current_date = calc_next_date(current_date, "MENSAL")

            return {
                "mode": "PARCELADO",
                "installments": n,
                "total": data.amount,
                "records_created": len(created),
                "first_record_id": created[0]["id"] if created else None,
            }

        # ── FIXO (RECORRENTE) ────────────────────────────────
        elif data.mode == FinancialMode.FIXO:
            if not data.frequency:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Frequência é obrigatória para lançamento fixo.",
                )
            # Cria o primeiro lançamento imediatamente
            row = await financial_repo.create(
                description=data.description,
                record_type=data.type,
                category=data.category,
                amount=data.amount,
                date=str(start_date),
                status=data.status,
                project_id=data.project_id,
            )
            # Calcula a próxima data
            next_date = calc_next_date(start_date, data.frequency.value)
            # Registra a recorrência
            rec = await recurring_repo.create({
                "description": data.description,
                "type": data.type,
                "category": data.category,
                "amount": data.amount,
                "frequency": data.frequency.value,
                "start_date": str(start_date),
                "next_date": str(next_date),
                "project_id": data.project_id,
            })
            return {
                "mode": "FIXO",
                "frequency": data.frequency.value,
                "first_record_id": row["id"],
                "recurring_id": rec["id"],
                "next_date": str(next_date),
            }

        # ── NORMAL (1x) ──────────────────────────────────────
        else:
            row = await financial_repo.create(
                description=data.description,
                record_type=data.type,
                category=data.category,
                amount=data.amount,
                date=str(start_date),
                status=data.status,
                project_id=data.project_id,
            )
            return {"mode": "NORMAL", "record_id": row["id"]}

    async def get_recurring(self) -> list[dict]:
        rows = await recurring_repo.find_all_active()
        result = []
        for r in rows:
            row = dict(r)
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    row[k] = str(v)
            result.append(row)
        return result

    async def deactivate(self, rec_id: str) -> dict:
        ok = await recurring_repo.deactivate(rec_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Recorrência não encontrada")
        return {"message": "Recorrência cancelada com sucesso"}

    async def process_due(self) -> dict:
        """Gera os lançamentos das recorrências vencidas (chamar via cron ou manualmente)."""
        due = await recurring_repo.find_due()
        generated = 0
        for rec in due:
            await financial_repo.create(
                description=rec["description"],
                record_type=rec["type"],
                category=rec["category"],
                amount=float(rec["amount"]),
                date=str(rec["next_date"]),
                status="PENDENTE",
                project_id=rec.get("project_id"),
            )
            next_date = calc_next_date(
                rec["next_date"] if isinstance(rec["next_date"], date) else date.fromisoformat(str(rec["next_date"])),
                rec["frequency"]
            )
            await recurring_repo.update_next_date(rec["id"], str(next_date))
            generated += 1
        return {"generated": generated}


recurring_service = RecurringService()
