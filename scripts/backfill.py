"""Executor de carga histórica inicial para um intervalo Raw gerado."""

from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta

from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.run_pipeline import execute_daily_pipeline


def execute_backfill(start_date: date, days: int, load_database: bool = True) -> dict[str, int]:
    """Processa cada partição diária disponível em um intervalo histórico."""
    if days < 1:
        raise ValueError("O backfill requer pelo menos um dia")
    processed_records = 0
    for offset in range(days):
        reference = (start_date + timedelta(days=offset)).isoformat()
        summary = execute_daily_pipeline(reference, load_database)
        transformation = summary["transformacao"]
        if not isinstance(transformation, dict):
            raise TypeError("Resultado de transformação inválido durante backfill")
        processed_records += int(transformation["registros_saida"])
    metrics = {"dias_processados": days, "registros_silver": processed_records}
    log_metrics(
        get_pipeline_logger("backfill", start_date.isoformat()), "Backfill concluido", metrics
    )
    return metrics


def parse_month(value: str) -> tuple[date, int]:
    """Retorna o primeiro dia e a duração de uma competência ``YYYY-MM``."""
    try:
        year, month = (int(part) for part in value.split("-", maxsplit=1))
        return date(year, month, 1), calendar.monthrange(year, month)[1]
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Mês inválido. Use YYYY-MM, por exemplo 2026-04.") from exc


def main() -> None:
    """Ponto de entrada CLI para processamento histórico de Raw."""
    parser = argparse.ArgumentParser(description="Processa intervalo historico Raw ate DW.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--month", help="Processa um mês calendário completo no formato YYYY-MM.")
    parser.add_argument("--skip-database", action="store_true")
    args = parser.parse_args()
    start_date, days = parse_month(args.month) if args.month else (args.start_date, args.days)
    print(execute_backfill(start_date, days, not args.skip_database))


if __name__ == "__main__":
    main()
