from datetime import datetime
from zoneinfo import ZoneInfo

from app.daily_trigger import is_scheduled_delivery_time


def test_weekday_delivery_runs_at_14_in_configured_timezone() -> None:
    weekday = datetime(2026, 10, 26, 14, 0, tzinfo=ZoneInfo("Asia/Tashkent"))
    assert weekday.weekday() == 0
    assert is_scheduled_delivery_time(weekday)


def test_weekend_delivery_runs_at_08_in_configured_timezone() -> None:
    weekend = datetime(2026, 10, 25, 8, 7, tzinfo=ZoneInfo("Asia/Tashkent"))
    assert weekend.weekday() == 6
    assert is_scheduled_delivery_time(weekend)


def test_off_schedule_cron_slots_are_skipped_for_weekdays_and_weekends() -> None:
    weekday_morning = datetime(2026, 10, 26, 8, 0, tzinfo=ZoneInfo("Asia/Tashkent"))
    weekend_afternoon = datetime(2026, 10, 25, 14, 0, tzinfo=ZoneInfo("Asia/Tashkent"))
    assert not is_scheduled_delivery_time(weekday_morning)
    assert not is_scheduled_delivery_time(weekend_afternoon)


def test_delivery_has_a_bounded_retry_window() -> None:
    on_boundary = datetime(2026, 10, 26, 14, 14, tzinfo=ZoneInfo("Asia/Tashkent"))
    outside_window = datetime(2026, 10, 26, 14, 15, tzinfo=ZoneInfo("Asia/Tashkent"))
    assert is_scheduled_delivery_time(on_boundary)
    assert not is_scheduled_delivery_time(outside_window)
