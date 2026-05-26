"""Testes das respostas analíticas expostas pela API principal."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from api import main


def test_dashboard_rejects_competence_not_loaded_in_dw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recusa uma competência válida no formato, mas ausente no Data Warehouse."""
    monkeypatch.setattr(main, "competences", lambda engine: ["2026-06", "2026-05"])

    with pytest.raises(HTTPException) as raised:
        main.get_dashboard("2027-01")

    assert raised.value.status_code == 404
    assert raised.value.detail == "Competência 2027-01 não carregada no DW."


def test_dashboard_uses_latest_loaded_competence_when_filter_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Escolhe a competência carregada mais recente quando não há filtro."""
    monkeypatch.setattr(main, "competences", lambda engine: ["2026-06", "2026-05"])
    monkeypatch.setattr(
        main,
        "dashboard",
        lambda engine, competence: {"competencia": competence},
    )

    result = main.get_dashboard(None)

    assert result["data"] == {"competencia": "2026-06"}
