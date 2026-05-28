"""Aplicação FastAPI que atende ao painel React em tempo real."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.pdv import router as pdv_router
from api.repository import (
    competences,
    dashboard,
    data_quality_status,
    evolution,
    forecast,
    latest_competence,
    ml_forecast,
    store_detail,
)
from scripts.load import create_dw_engine

app = FastAPI(title="RetailCo FP&A API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
engine = create_dw_engine()
app.include_router(pdv_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Expõe a integridade da API e a disponibilidade do banco de dados."""
    latest = latest_competence(engine)
    return {
        "status": "ok",
        "latest_competence": latest or "sem_dados",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


@app.get("/api/competences")
def list_competences() -> dict[str, list[str]]:
    """Expõe os períodos carregados disponíveis nos filtros do painel."""
    return {"items": competences(engine)}


@app.get("/api/dashboard")
def get_dashboard(
    competencia: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
) -> dict[str, object]:
    """Retorna uma fotografia analítica em tempo real para uma competência."""
    available = competences(engine)
    selected = competencia or (available[0] if available else None)
    if selected is None:
        raise HTTPException(status_code=404, detail="Nenhuma competência carregada no DW.")
    if selected not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Competência {selected} não carregada no DW.",
        )
    return {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": dashboard(engine, selected),
    }


@app.get("/api/evolution")
def get_evolution() -> dict[str, object]:
    """Retorna séries mensais da rede e das lojas para análise de evolução."""
    return {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": evolution(engine),
    }


@app.get("/api/data-quality")
def get_data_quality(days: int = Query(default=14, ge=1, le=90)) -> dict[str, object]:
    """Retorna qualidade, auditoria e rastreabilidade do pipeline."""
    return {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": data_quality_status(engine, days),
    }


@app.get("/api/stores/{store_id}")
def get_store_detail(
    store_id: int,
    forecast_months: int = Query(default=6, ge=1, le=12),
) -> dict[str, object]:
    """Retorna visão detalhada de desempenho, qualidade e previsão de uma loja."""
    try:
        data = store_detail(engine, store_id, forecast_months)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": data,
    }


@app.get("/api/forecast")
def get_forecast(
    months: int = Query(default=6, ge=1, le=12),
    adjustment_pct: float = Query(default=0, ge=-30, le=30),
) -> dict[str, object]:
    """Retorna projeções mensais futuras com ajuste de cenário."""
    return {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": forecast(engine, months, adjustment_pct),
    }


@app.get("/api/ml-forecast")
def get_ml_forecast(months: int = Query(default=6, ge=1, le=12)) -> dict[str, object]:
    """Retorna previsão estatística mensal baseada no histórico realizado."""
    try:
        forecast_data = ml_forecast(engine, months)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": forecast_data,
    }
