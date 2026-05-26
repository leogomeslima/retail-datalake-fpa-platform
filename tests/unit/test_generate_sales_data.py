"""Cobertura da geração Raw mensal e das garantias de imutabilidade."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from scripts.generate_sales_data import generate_raw_data, parse_month


def first_sale_id(data_lake: Path, month: str) -> str:
    """Lê um identificador de venda gerado em uma partição Raw mensal."""
    for path in sorted((data_lake / "raw" / "vendas").rglob("*.json")):
        if f"mes={month}" not in path.parts:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["vendas"]:
            return str(payload["vendas"][0]["id_venda"])
    raise AssertionError("Expected at least one generated sale.")


def test_parse_month_uses_complete_calendar_month() -> None:
    """Permite qualquer competência futura, respeitando anos bissextos."""
    assert parse_month("2026-04") == (date(2026, 4, 1), 30)
    assert parse_month("2028-02") == (date(2028, 2, 1), 29)


def test_months_generate_distinct_transaction_ids(temporary_data_lake: Path) -> None:
    """A inclusão de um novo mês não pode colidir com chaves já existentes."""
    generate_raw_data(date(2026, 1, 1), days=1, seed=41)
    generate_raw_data(date(2026, 4, 1), days=1, seed=41)

    january_id = first_sale_id(temporary_data_lake, "01")
    april_id = first_sale_id(temporary_data_lake, "04")

    assert january_id.startswith("VND-20260101-")
    assert april_id.startswith("VND-20260401-")
    assert january_id != april_id


def test_generation_refuses_to_overwrite_raw_partition() -> None:
    """Trata documentos já emitidos pelo PDV como imutáveis por padrão."""
    generate_raw_data(date(2026, 4, 1), days=1, seed=55)

    with pytest.raises(FileExistsError, match="não será sobrescrito"):
        generate_raw_data(date(2026, 4, 1), days=1, seed=55)
