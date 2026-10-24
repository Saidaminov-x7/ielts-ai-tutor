"""Idempotently import the private IELTS course source files into the app DB."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from app.database.session import SessionLocal, init_db
from app.learning.course_sources import build_course_dataset, import_course_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roadmap", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    args = parser.parse_args()
    dataset = build_course_dataset(args.roadmap, args.vocabulary)
    target = Path(__file__).resolve().parents[1] / "data" / "ielts_vocabulary_30_weeks.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    import json

    target.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    init_db()
    with SessionLocal() as session:
        imported = import_course_dataset(session, target)
    print(
        f"Validated {len(dataset['weeks'])} weeks and "
        f"{len(dataset['vocabulary'])} cards; imported {imported['weeks']} weeks and "
        f"{imported['vocabulary']} cards into the configured local database; wrote {target}."
    )


if __name__ == "__main__":
    main()
