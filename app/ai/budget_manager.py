from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.models import AIUsage


class BudgetExceeded(Exception):
    pass


def reserve(session: Session, owner_id: int, input_tokens: int, output_tokens: int) -> AIUsage:
    settings = get_settings()
    now = date.today()
    month = now.strftime("%Y-%m")
    input_rate = settings.ai_input_price_per_million / 1_000_000
    output_rate = settings.ai_output_price_per_million / 1_000_000
    reservation = input_tokens * input_rate + output_tokens * output_rate
    start = now.replace(day=1)
    existing = float(
        session.scalar(
            select(func.sum(AIUsage.reserved_usd + AIUsage.actual_usd)).where(
                AIUsage.month == month
            )
        )
        or 0
    )
    daily = int(
        session.scalar(
            select(func.count(AIUsage.id)).where(
                AIUsage.owner_id == owner_id,
                AIUsage.request_date >= start,
                AIUsage.request_date <= now,
            )
        )
        or 0
    )
    if (
        daily >= settings.max_daily_ai_requests
        or existing + reservation > settings.monthly_ai_budget_usd
    ):
        raise BudgetExceeded("Достигнут установленный лимит AI-запросов или месячного бюджета.")
    usage = AIUsage(owner_id=owner_id, month=month, request_date=now, reserved_usd=reservation)
    session.add(usage)
    session.commit()
    session.refresh(usage)
    return usage


def settle(session: Session, usage: AIUsage, input_tokens: int, output_tokens: int) -> None:
    settings = get_settings()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.actual_usd = (
        input_tokens * settings.ai_input_price_per_million
        + output_tokens * settings.ai_output_price_per_million
    ) / 1_000_000
    usage.reserved_usd = 0
    session.commit()
