from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Activity


@dataclass(frozen=True)
class TopicStatus:
    topic: str
    accuracy: float
    recommendation: str


def recommendation(accuracy: float) -> str:
    if accuracy < 60:
        return "Повторное изучение"
    if accuracy < 80:
        return "Дополнительное закрепление"
    if accuracy < 90:
        return "Усвоено на приемлемом уровне"
    return "Хорошо освоено"


def weak_topics(session: Session, owner_id: int) -> list[TopicStatus]:
    rows = session.execute(
        select(Activity.topic, func.avg(Activity.score))
        .where(Activity.owner_id == owner_id, Activity.topic != "")
        .group_by(Activity.topic)
    ).all()
    result = [
        TopicStatus(topic, round(float(avg or 0), 1), recommendation(float(avg or 0)))
        for topic, avg in rows
    ]
    return sorted(result, key=lambda item: item.accuracy)


def adapt_day(session: Session, owner_id: int, day_number: int) -> str:
    rows = (
        session.execute(
            select(func.avg(Activity.score))
            .where(Activity.owner_id == owner_id, Activity.topic != "")
            .group_by(Activity.topic)
        )
        .scalars()
        .all()
    )
    if rows and float(min(rows)) < 60:
        return "Сначала повторите слабую тему, затем переходите к материалу дня."
    if rows and float(min(rows)) < 80:
        return "Добавьте 15 минут упражнений на слабую тему."
    return f"Продолжайте программу: учебный день {day_number}."
