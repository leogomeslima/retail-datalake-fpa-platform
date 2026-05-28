"""Testes unitários da projeção de receita no repositório analítico."""

import pytest

from api.repository import (
    approval_rate,
    forecast_trend,
    linear_regression,
    next_competence,
    regression_prediction,
)


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


def test_linear_regression_fits_simple_growth_series() -> None:
    model = linear_regression([100.0, 120.0, 140.0])

    assert model["intercept"] == pytest.approx(100.0)
    assert model["slope"] == pytest.approx(20.0)
    assert model["rmse"] == pytest.approx(0.0)
    assert model["r2"] == pytest.approx(1.0)


def test_regression_prediction_returns_backtest_and_interval() -> None:
    history = [
        {"competencia": "2026-01", "receita": 100.0},
        {"competencia": "2026-02", "receita": 120.0},
        {"competencia": "2026-03", "receita": 140.0},
        {"competencia": "2026-04", "receita": 160.0},
    ]

    result = regression_prediction(history, "receita", 2, "2026-04")

    assert result["projection"][0]["competencia"] == "2026-05"
    assert result["projection"][0]["previsao"] == pytest.approx(180.0)
    assert result["projection"][1]["competencia"] == "2026-06"
    assert result["backtest"]["competencia"] == "2026-04"
    assert result["model"]["observacoes_treino"] == 4


def test_approval_rate_calculates_valid_record_percentage() -> None:
    assert approval_rate(100, 3) == 97.0
    assert approval_rate(0, 0) == 100.0
