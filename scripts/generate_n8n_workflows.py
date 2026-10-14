"""Generate importable n8n Community workflow templates for IELTS AI Tutor."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "n8n" / "workflows"
PYTHON_URL = "http://ielts-webhook.railway.internal:8080"

EVENTS = [
    ("Daily IELTS Lesson", "daily_lesson", "0 0 * * *", "/internal/daily", None),
    (
        "Vocabulary Revision",
        "vocabulary_revision",
        "5 8 * * *",
        "/internal/scheduled-event",
        "vocabulary_revision",
    ),
    (
        "Daily Mini Test",
        "daily_mini_test",
        "0 18 * * *",
        "/internal/scheduled-event",
        "daily_mini_test",
    ),
    (
        "Smart Reminders",
        "smart_reminders",
        "30 19 * * *",
        "/internal/scheduled-event",
        "smart_reminders",
    ),
    (
        "Weekly IELTS Exam",
        "weekly_ielts_exam",
        "0 10 * * 0",
        "/internal/scheduled-event",
        "weekly_ielts_exam",
    ),
    (
        "Weekly Progress Report",
        "weekly_progress_report",
        "0 19 * * 0",
        "/internal/scheduled-event",
        "weekly_progress_report",
    ),
    (
        "AI Budget Monitoring",
        "ai_budget_monitoring",
        "0 9 * * *",
        "/internal/scheduled-event",
        "ai_budget_monitoring",
    ),
]


def http_node(name: str, path: str, event_type: str | None) -> dict[str, object]:
    parameters: dict[str, object] = {
        "method": "POST",
        "url": PYTHON_URL + path,
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "options": {"timeout": 15000},
    }
    if event_type is not None:
        body = "={{ JSON.stringify({event_type: '" + event_type + "', event_date: $now.setZone('Asia/Tashkent').toISODate()}) }}"
        parameters.update({"sendBody": True, "specifyBody": "json", "jsonBody": body})
    return {
        "parameters": parameters,
        "id": name.lower().replace(" ", "-"),
        "name": "Call IELTS Python service",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [460, 300],
    }


def scheduled_workflow(name: str, slug: str, cron: str, path: str, event: str | None) -> dict[str, object]:
    trigger = {
        "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}},
        "id": slug + "-schedule",
        "name": "Schedule",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [220, 300],
    }
    request = http_node(name, path, event)
    return {
        "name": name,
        "nodes": [trigger, request],
        "connections": {"Schedule": {"main": [[{"node": request["name"], "type": "main", "index": 0}]]}},
        "active": False,
        "settings": {"executionOrder": "v1", "timezone": "Asia/Tashkent", "saveDataErrorExecution": "none", "saveDataSuccessExecution": "none"},
        "versionId": slug + "-initial",
        "meta": {"templateCredsSetupCompleted": False},
        "tags": [],
    }


def health_workflow() -> dict[str, object]:
    schedule = {
        "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 */30 * * *"}]}},
        "id": "health-schedule",
        "name": "Schedule",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [220, 300],
    }
    check = {
        "parameters": {
            "url": PYTHON_URL + "/health",
            "options": {"timeout": 10000, "response": {"response": {"neverError": True, "responseFormat": "json", "includeResponseHeadersAndStatus": True}}},
        },
        "id": "health-request",
        "name": "Check IELTS health",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [460, 300],
        "onError": "continueRegularOutput",
    }
    branch = {
        "parameters": {"conditions": {"options": {"caseSensitive": True, "typeValidation": "strict", "version": 2}, "conditions": [{"leftValue": "={{ $json.statusCode }}", "rightValue": 200, "operator": {"type": "number", "operation": "equals"}}], "combinator": "and"}},
        "id": "health-status",
        "name": "Is healthy?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [700, 300],
    }
    alert = http_node("Health alert", "/internal/scheduled-event", "application_health_monitoring")
    alert["id"] = "health-alert"
    alert["name"] = "Notify through IELTS Python service"
    alert["position"] = [940, 420]
    return {
        "name": "Application Health Monitoring",
        "nodes": [schedule, check, branch, alert],
        "connections": {
            "Schedule": {"main": [[{"node": "Check IELTS health", "type": "main", "index": 0}]]},
            "Check IELTS health": {"main": [[{"node": "Is healthy?", "type": "main", "index": 0}]]},
            "Is healthy?": {"main": [[], [{"node": "Notify through IELTS Python service", "type": "main", "index": 0}]]},
        },
        "active": False,
        "settings": {"executionOrder": "v1", "timezone": "Asia/Tashkent", "saveDataErrorExecution": "none", "saveDataSuccessExecution": "none"},
        "versionId": "application-health-initial",
        "meta": {"templateCredsSetupCompleted": False},
        "tags": [],
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, slug, cron, path, event in EVENTS:
        (OUTPUT / f"{slug}.json").write_text(
            json.dumps(scheduled_workflow(name, slug, cron, path, event), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (OUTPUT / "application_health_monitoring.json").write_text(
        json.dumps(health_workflow(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
