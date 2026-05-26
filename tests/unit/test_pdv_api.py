"""Testes do endpoint de fechamento diário completo do PDV."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from api.pdv import FechamentoGeralRequest, emit_all_shifts


def test_daily_closing_emits_all_store_shift_files_and_processes_dw(
    temporary_data_lake, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cria todos os Raw de turno e processa imediatamente a data operacional."""
    processed_dates: list[date] = []

    def fake_processing(sale_date: date) -> dict[str, object]:
        processed_dates.append(sale_date)
        return {"status": "PROCESSADO", "registros_inseridos": 30}

    monkeypatch.setattr("api.pdv.process_raw_date", fake_processing)
    result = emit_all_shifts(
        FechamentoGeralRequest(
            data=date(2026, 6, 10),
            quantidade_por_turno=2,
            seed=20260610,
        )
    )

    raw_files = list((temporary_data_lake / "raw" / "vendas").rglob("*.json"))

    assert result["status"] == "RAW_DIA_EMITIDO"
    assert result["arquivos_raw"] == 15
    assert result["quantidade"] == 30
    assert len(result["emissoes"]) == 15
    assert len(raw_files) == 15
    assert result["processamento"]["status"] == "PROCESSADO"
    assert processed_dates == [date(2026, 6, 10)]


def test_daily_closing_refuses_partial_reemission_for_same_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Não sobrescreve nem amplia uma data que já possua fechamento Raw."""
    monkeypatch.setattr(
        "api.pdv.process_raw_date",
        lambda sale_date: {"status": "PROCESSADO", "data": sale_date.isoformat()},
    )
    request = FechamentoGeralRequest(
        data=date(2026, 6, 11),
        quantidade_por_turno=1,
        seed=20260611,
    )
    emit_all_shifts(request)

    with pytest.raises(HTTPException) as raised:
        emit_all_shifts(request)

    assert raised.value.status_code == 409
    assert "Fechamento geral não emitido" in raised.value.detail
