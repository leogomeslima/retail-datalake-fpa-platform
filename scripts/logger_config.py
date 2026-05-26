"""Registro estruturado em JSON utilizado pelos componentes do pipeline."""

from __future__ import annotations

import json
import logging
from collections.abc import MutableMapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import get_settings


class JsonFormatter(logging.Formatter):
    """Serializa registros de log do pipeline como documentos JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Formata um evento de log com campos estáveis de auditoria."""
        event = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "pipeline": getattr(record, "pipeline", "etl_vendas_fpa"),
            "task": getattr(record, "task", record.name),
            "data_referencia": getattr(record, "data_referencia", None),
            "message": record.getMessage(),
            "metrics": getattr(record, "metrics", {}),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False, default=str)


class PipelineLoggerAdapter(logging.LoggerAdapter):
    """Combina o contexto estático do pipeline com métricas de cada evento."""

    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        """Combina metadados do adaptador sem descartar métricas do evento."""
        event_extra = kwargs.get("extra", {})
        kwargs["extra"] = {**(self.extra or {}), **event_extra}
        return msg, kwargs


def get_pipeline_logger(task: str, data_referencia: str | None = None) -> logging.LoggerAdapter:
    """Cria logger estruturado para console e log diário do Data Lake."""
    settings = get_settings()
    logger = logging.getLogger(f"retail_etl.{task}")
    logger.setLevel(settings.log_level)
    logger.propagate = False
    if not logger.handlers:
        formatter = JsonFormatter()
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        log_file = settings.logs_path / f"pipeline_{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
    return PipelineLoggerAdapter(
        logger,
        {"pipeline": "etl_vendas_fpa", "task": task, "data_referencia": data_referencia},
    )


def log_metrics(
    logger: logging.LoggerAdapter, message: str, metrics: dict[str, Any], level: int = logging.INFO
) -> None:
    """Registra um evento estruturado de negócio com métricas de processamento."""
    logger.log(level, message, extra={"metrics": metrics})


def audit_json_path(data_referencia: str) -> Path:
    """Retorna o destino local JSON Lines de auditoria para uma data de referência."""
    return get_settings().logs_path / f"audit_{data_referencia.replace('-', '')}.jsonl"
