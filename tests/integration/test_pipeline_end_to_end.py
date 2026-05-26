"""Teste de integração do pipeline do Data Lake sem serviços externos."""

from __future__ import annotations

from datetime import date

from scripts.backfill import execute_backfill
from scripts.generate_sales_data import generate_raw_data
from scripts.run_pipeline import execute_daily_pipeline


def test_pipeline_raw_to_gold_produces_real_artifacts() -> None:
    """Gera documentos reais do PDV e os processa até a camada Gold."""
    generation = generate_raw_data(date(2026, 1, 1), days=1, seed=44)
    summary = execute_daily_pipeline("2026-01-01", load_database=False)
    assert generation["total_vendas"] > 0
    assert summary["validacao"]["registros_invalidos"] == 0  # type: ignore[index]
    assert summary["transformacao"]["registros_saida"] > 0  # type: ignore[index]
    assert summary["kpis"]["resumo_path"].exists()  # type: ignore[index,union-attr]


def test_backfill_processes_available_daily_partitions() -> None:
    """Usa o executor histórico sobre partições Raw reais sem banco de dados."""
    generate_raw_data(date(2026, 2, 1), days=2, seed=71)
    metrics = execute_backfill(date(2026, 2, 1), days=2, load_database=False)
    assert metrics["dias_processados"] == 2
    assert metrics["registros_silver"] > 0
