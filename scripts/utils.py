"""Utilitários compartilhados de arquivos, datas e checksum."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import get_settings


def parse_reference_date(data_referencia: str) -> date:
    """Interpreta uma data ISO de referência e falha com mensagem útil."""
    try:
        return date.fromisoformat(data_referencia)
    except ValueError as exc:
        raise ValueError(
            f"Data de referência inválida: {data_referencia}. Use YYYY-MM-DD."
        ) from exc


def date_partition_path(base: Path, data_referencia: str) -> Path:
    """Constrói um diretório de partição por ano, mês e dia."""
    reference = parse_reference_date(data_referencia)
    return (
        base / f"ano={reference.year}" / f"mes={reference.month:02d}" / f"dia={reference.day:02d}"
    )


def raw_store_partition(loja_id: int, data_referencia: str) -> Path:
    """Retorna a partição Raw de uma loja e um dia de referência."""
    return date_partition_path(
        get_settings().raw_path / "vendas" / f"loja=loja_{loja_id}", data_referencia
    )


def sha256_json(payload: Any) -> str:
    """Cria um checksum SHA-256 determinístico para conteúdo compatível com JSON."""
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    """Lê conteúdo JSON do disco."""
    try:
        with path.open("r", encoding="utf-8") as source:
            return json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Falha ao ler JSON {path}: {exc}") from exc


def atomic_write_json(path: Path, payload: Any) -> None:
    """Grava um documento JSON atomicamente para evitar arquivos Raw parciais."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, indent=2, default=str)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def atomic_write_dataframe(df: pd.DataFrame, path: Path, file_format: str) -> None:
    """Grava um DataFrame atomicamente como CSV ou Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        if file_format == "csv":
            df.to_csv(temporary_path, index=False, encoding="utf-8")
        elif file_format == "parquet":
            df.to_parquet(temporary_path, index=False)
        else:
            raise ValueError(f"Formato de gravação não suportado: {file_format}")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_config_json(filename: str) -> Any:
    """Carrega um documento JSON de configuração do diretório do projeto."""
    return load_json(get_settings().project_root / "config" / filename)


def append_json_line(path: Path, payload: dict[str, Any]) -> None:
    """Adiciona um evento de auditoria local em formato JSON Lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as destination:
        destination.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def dataframe_records(frame: pd.DataFrame) -> Iterable[dict[str, Any]]:
    """Produz linhas do DataFrame com valores nulos representados como ``None``."""
    normalized = frame.astype(object).where(pd.notna(frame), None)
    yield from normalized.to_dict(orient="records")


def utc_timestamp() -> str:
    """Retorna timestamp com fuso horário adequado para campos de metadados."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
