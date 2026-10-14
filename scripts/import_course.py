import argparse
from pathlib import Path

from app.database.session import SessionLocal, init_db
from app.importer import TARGET_NAME, import_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the supplied IELTS course workbook")
    parser.add_argument("workbook", nargs="?", default=TARGET_NAME)
    parser.add_argument("--report", default="data/import-report.json")
    args = parser.parse_args()
    path = Path(args.workbook)
    if not path.is_file():
        parser.error(
            f"Workbook not found: {path}. Supply the original XLSX; "
            "its contents will not be fabricated."
        )
    init_db()
    with SessionLocal() as session:
        report = import_workbook(session, path)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.save(report_path)
    print(
        f"Листов: {report.sheets}; дней добавлено/обновлено: "
        f"{report.days_added}/{report.days_updated}; слов: {report.words_added}"
    )
    for item in report.warnings:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {item}")
    for item in report.errors:
        print(f"ОШИБКА: {item}")
    print(f"Отчёт: {report_path}")


if __name__ == "__main__":
    main()
