"""Testes unitários da projeção de receita no repositório analítico."""

import pytest

from api.repository import forecast_trend, next_competence


def test_next_competence_advances_across_year_boundary() -> None:
    assert next_competence("2026-11", 3) == "2027-02"


def test_forecast_trend_ignores_current_open_competence() -> None:
    history = [
        {"competencia": "2026-01", "receita": 100.0},
        {"competencia": "2026-02", "receita": 110.0},
        {"competencia": "2026-03", "receita": 121.0},
        {"competencia": "2026-04", "receita": 133.1},
        {"competencia": "2026-05", "receita": 12.0},
    ]

    assert forecast_trend(history, "2026-05") == pytest.approx(0.1)


def test_forecast_trend_limits_outlier_growth() -> None:
    history = [
        {"competencia": "2026-01", "receita": 100.0},
        {"competencia": "2026-02", "receita": 500.0},
        {"competencia": "2026-03", "receita": 1000.0},
    ]

    assert forecast_trend(history, "2026-04") == 0.15
