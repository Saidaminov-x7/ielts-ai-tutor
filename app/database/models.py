from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CourseDay(Base):
    __tablename__ = "course_days"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    week_number: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(300))
    grammar: Mapped[str] = mapped_column(Text, default="")
    reading: Mapped[str] = mapped_column(Text, default="")
    listening: Mapped[str] = mapped_column(Text, default="")
    writing: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[str] = mapped_column(Text, default="")


class CourseWeek(Base):
    """Source roadmap content, explicitly authored at weekly granularity."""

    __tablename__ = "course_weeks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    month: Mapped[int] = mapped_column(Integer, default=1)
    topic: Mapped[str] = mapped_column(String(300))
    grammar: Mapped[str] = mapped_column(Text, default="")
    listening: Mapped[str] = mapped_column(Text, default="")
    reading_writing: Mapped[str] = mapped_column(Text, default="")
    speaking_outcome: Mapped[str] = mapped_column(Text, default="")


class CourseDayVocabulary(Base):
    __tablename__ = "course_day_vocabulary"
    __table_args__ = (
        UniqueConstraint("owner_id", "day_number", "vocabulary_id", name="uq_course_day_vocab"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    day_number: Mapped[int] = mapped_column(Integer, index=True)
    vocabulary_id: Mapped[int] = mapped_column(Integer, index=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class Vocabulary(Base):
    __tablename__ = "vocabulary"
    __table_args__ = (UniqueConstraint("english", "translation", name="uq_vocab_pair"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    english: Mapped[str] = mapped_column(String(200), index=True)
    translation: Mapped[str] = mapped_column(String(300))
    transcription: Mapped[str] = mapped_column(String(200), default="")
    example: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    learned_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    next_review: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    course_day: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_key: Mapped[str | None] = mapped_column(
        String(80), nullable=True, unique=True, index=True
    )
    course_week: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pronunciation_hint: Mapped[str] = mapped_column(String(300), default="")
    collocation: Mapped[str] = mapped_column(String(300), default="")
    collocation_translation: Mapped[str] = mapped_column(String(500), default="")
    collocation_transcription: Mapped[str] = mapped_column(String(300), default="")
    collocation_pronunciation_hint: Mapped[str] = mapped_column(String(300), default="")


class VocabularyProgress(Base):
    """Per-learner spaced repetition state for shared course vocabulary."""

    __tablename__ = "vocabulary_progress"
    __table_args__ = (
        UniqueConstraint("owner_id", "vocabulary_id", name="uq_vocab_progress_owner_word"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    vocabulary_id: Mapped[int] = mapped_column(Integer, index=True)
    next_review: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)


class VocabularyExampleSet(Base):
    """Validated, shared cache of Gemini examples for a source vocabulary item."""

    __tablename__ = "vocabulary_example_sets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    examples_json: Mapped[str] = mapped_column(Text, default="[]")
    pending_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class GeminiDailyQuota(Base):
    """Atomic daily request counter shared by all Gemini learning features."""

    __tablename__ = "gemini_daily_quotas"
    __table_args__ = (
        UniqueConstraint("owner_id", "request_date", name="uq_gemini_daily_quota_owner_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    request_date: Mapped[date] = mapped_column(Date, index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)


class ReviewSession(Base):
    __tablename__ = "review_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    word_ids_json: Mapped[str] = mapped_column(Text)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    day_number: Mapped[int] = mapped_column(Integer, default=1)
    kind: Mapped[str] = mapped_column(String(40))
    topic: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[float | None] = mapped_column(Float, default=0, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )


class WritingAttempt(Base):
    __tablename__ = "writing_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    task_type: Mapped[str] = mapped_column(String(30))
    estimated_band: Mapped[float] = mapped_column(Float)
    feedback_json: Mapped[str] = mapped_column(Text)
    submission_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class DailyDelivery(Base):
    __tablename__ = "daily_deliveries"
    __table_args__ = (UniqueConstraint("owner_id", "day", name="uq_daily_delivery_owner_day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"
    __table_args__ = (UniqueConstraint("event_key", name="uq_scheduled_event_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_key: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskProgress(Base):
    __tablename__ = "task_progress"
    __table_args__ = (
        UniqueConstraint("owner_id", "day_number", "task_key", name="uq_task_progress"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    day_number: Mapped[int] = mapped_column(Integer)
    task_key: Mapped[str] = mapped_column(String(80))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ErrorLog(Base):
    __tablename__ = "error_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    topic: Mapped[str] = mapped_column(String(200), index=True)
    exercise: Mapped[str] = mapped_column(String(300), default="")
    wrong_answer: Mapped[str] = mapped_column(Text)
    correct_answer: Mapped[str] = mapped_column(Text)
    error_type: Mapped[str] = mapped_column(String(100), default="grammar")
    explanation: Mapped[str] = mapped_column(Text, default="")
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    day_number: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer, default=10)
    answers_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    day_number: Mapped[int] = mapped_column(Integer)
    questions_json: Mapped[str] = mapped_column(Text)
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExamSession(Base):
    __tablename__ = "exam_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    week_number: Mapped[int] = mapped_column(Integer)
    questions_json: Mapped[str] = mapped_column(Text)
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    deadline: Mapped[datetime] = mapped_column(DateTime, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AIUsage(Base):
    __tablename__ = "ai_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(
        String(20), default="openai", server_default="openai", index=True
    )
    month: Mapped[str] = mapped_column(String(7), index=True)
    request_date: Mapped[date] = mapped_column(Date, index=True)
    reserved_usd: Mapped[float] = mapped_column(Float, default=0)
    actual_usd: Mapped[float] = mapped_column(Float, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)


class UserSettings(Base):
    __tablename__ = "user_settings"
    owner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_time: Mapped[str] = mapped_column(String(5), default="19:00")
    current_day: Mapped[int] = mapped_column(Integer, default=1)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    max_streak: Mapped[int] = mapped_column(Integer, default=0)
    completed_days: Mapped[int] = mapped_column(Integer, default=0)
    course_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    course_schedule_day: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CourseResetArchive(Base):
    """Owner-scoped historical snapshot of state cleared by a course restart."""

    __tablename__ = "course_reset_archives"
    __table_args__ = (
        UniqueConstraint("owner_id", "request_key", name="uq_course_reset_owner_request"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    request_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reset_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    payload_json: Mapped[str] = mapped_column(Text)


class ObsidianSave(Base):
    """Idempotency ledger for explicit Telegram-to-vault saves."""

    __tablename__ = "obsidian_saves"
    __table_args__ = (UniqueConstraint("owner_id", "update_id", name="uq_obsidian_save_update"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    update_id: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
