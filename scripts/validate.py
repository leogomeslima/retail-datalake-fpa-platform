"""Validação Bronze, pontuação de aprovação e encaminhamento à quarentena."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import get_settings
from scripts.data_quality import QUALITY_RULES, evaluate_rules, quality_score
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import atomic_write_dataframe, atomic_write_json, date_partition_path


@dataclass
class ValidationResult:
    """Caminhos e contagens produzidos pela validação de qualidade Bronze."""

    total_registros: int
    registros_validos: int
    registros_invalidos: int
    taxa_aprovacao: float
    caminho_validos: Path
    caminho_invalidos: Path
    caminho_relatorio: Path


def validate_dataframe(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Avalia regras de qualidade e separa linhas válidas das rejeitadas."""
    failures: dict[str, dict[str, int | str]] = {
        rule.name: {"falhas": 0, "severidade": rule.severity} for rule in QUALITY_RULES
    }
    valid_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        violated = evaluate_rules(record)
        for rule in violated:
            failures[rule.name]["falhas"] = int(failures[rule.name]["falhas"]) + 1
        blocking = [rule for rule in violated if rule.severity in {"CRITICA", "ERRO"}]
        if blocking:
            record["regras_violadas"] = "|".join(rule.name for rule in violated)
            invalid_rows.append(record)
        else:
            valid_rows.append(record)
    valid = pd.DataFrame(valid_rows, columns=frame.columns)
    invalid = pd.DataFrame(invalid_rows)
    report = {
        "total_registros": len(frame),
        "registros_validos": len(valid),
        "registros_invalidos": len(invalid),
        "taxa_aprovacao": quality_score(len(frame), len(invalid)),
        "por_regra": failures,
    }
    return valid, invalid, report


def validar_bronze(data_referencia: str, caminho_bronze: Path | None = None) -> ValidationResult:
    """Valida registros Bronze e persiste partições aceitas e rejeitadas."""
    started = time.perf_counter()
    logger = get_pipeline_logger("validar_qualidade", data_referencia)
    partition = date_partition_path(get_settings().bronze_path / "vendas", data_referencia)
    source = caminho_bronze or partition / f"vendas_bronze_{data_referencia.replace('-', '')}.csv"
    frame = pd.read_csv(source)
    valid, invalid, report = validate_dataframe(frame)
    valid_path = partition / f"vendas_validadas_{data_referencia.replace('-', '')}.csv"
    invalid_path = (
        get_settings().quarantine_path
        / f"registros_invalidos_{data_referencia.replace('-', '')}.csv"
    )
    report_path = partition / f"relatorio_qualidade_{data_referencia.replace('-', '')}.json"
    atomic_write_dataframe(valid, valid_path, "csv")
    atomic_write_dataframe(invalid, invalid_path, "csv")
    report |= {
        "data_referencia": data_referencia,
        "invalidos_salvos_em": str(invalid_path),
    }
    atomic_write_json(report_path, report)
    log_metrics(
        logger,
        "Validação Bronze concluída",
        report | {"duracao_ms": round((time.perf_counter() - started) * 1000)},
    )
    return ValidationResult(
        len(frame),
        len(valid),
        len(invalid),
        report["taxa_aprovacao"],
        valid_path,
        invalid_path,
        report_path,
    )


def main() -> None:
    """Ponto de entrada CLI para validação diária de qualidade."""
    parser = argparse.ArgumentParser(description="Valida registros Bronze.")
    parser.add_argument("data_referencia")
    args = parser.parse_args()
    result = validar_bronze(args.data_referencia)
    print(json.dumps(result.__dict__, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
