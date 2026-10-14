import json
import re
from pathlib import Path


WORKFLOWS = Path(__file__).resolve().parents[1] / "n8n" / "workflows"
EXPECTED = {
    "daily_lesson.json": ("/internal/daily", None),
    "vocabulary_revision.json": ("/internal/scheduled-event", "vocabulary_revision"),
    "daily_mini_test.json": ("/internal/scheduled-event", "daily_mini_test"),
    "smart_reminders.json": ("/internal/scheduled-event", "smart_reminders"),
    "weekly_ielts_exam.json": ("/internal/scheduled-event", "weekly_ielts_exam"),
    "weekly_progress_report.json": ("/internal/scheduled-event", "weekly_progress_report"),
    "ai_budget_monitoring.json": ("/internal/scheduled-event", "ai_budget_monitoring"),
    "application_health_monitoring.json": ("/health", "application_health_monitoring"),
}


def test_all_eight_workflow_exports_are_inactive_and_secret_free() -> None:
    files = {path.name for path in WORKFLOWS.glob("*.json")}
    assert files == set(EXPECTED)
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.json"))
    assert not re.search(r"sk-[A-Za-z0-9_-]{20,}", serialized)
    assert not re.search(r"\b\d{8,}:[A-Za-z0-9_-]{25,}\b", serialized)
    assert "X-Daily-Job-Secret" not in serialized

    for filename in EXPECTED:
        workflow = json.loads((WORKFLOWS / filename).read_text(encoding="utf-8"))
        assert workflow["active"] is False
        assert workflow["settings"]["timezone"] == "Asia/Tashkent"
        assert workflow["settings"]["saveDataSuccessExecution"] == "none"
        assert workflow["settings"]["saveDataErrorExecution"] == "none"


def test_scheduled_workflows_call_only_the_python_internal_event_api() -> None:
    for filename, (path, event) in EXPECTED.items():
        workflow = json.loads((WORKFLOWS / filename).read_text(encoding="utf-8"))
        request_nodes = [node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"]
        matching = [node for node in request_nodes if node["parameters"].get("url", "").endswith(path)]
        assert matching, filename
        if event is None:
            continue
        event_nodes = matching
        if filename == "application_health_monitoring.json":
            event_nodes = [
                node for node in request_nodes
                if node["parameters"].get("url", "").endswith("/internal/scheduled-event")
            ]
        assert any(event in json.dumps(node["parameters"], ensure_ascii=False) for node in event_nodes)
        assert all(
            node.get("credentials", {}).get("httpHeaderAuth", {}).get("name") == "IELTS Internal API"
            for node in event_nodes
        )
