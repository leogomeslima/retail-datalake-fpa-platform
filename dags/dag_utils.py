"""Auxiliares reutilizáveis de orquestração para tarefas do Airflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import text

from scripts.load import create_dw_engine
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import raw_store_partition


def raw_files_for_store(data_referencia: str, loja_id: int) -> dict[str, Any]:
    """Verifica uma partição Raw de loja sem bloquear as demais lojas."""
    files = list(raw_store_partition(loja_id, data_referencia).glob("*.json"))
    result = {"loja_id": loja_id, "arquivos": len(files), "disponivel": bool(files)}
    log_metrics(
        get_pipeline_logger(f"verificar_raw_loja_{loja_id}", data_referencia),
        "Verificação Raw concluída",
        result,
    )
    return result


def choose_ingestion_branch(task_instance: Any) -> str:
    """Continua a ingestão quando ao menos uma loja possui arquivos Raw."""
    checks = [
        task_instance.xcom_pull(task_ids=f"verificar_raw_loja_{loja_id}") for loja_id in range(1, 6)
    ]
    return "extrair_bronze" if any(item and item["disponivel"] for item in checks) else "sem_dados"


def write_audit(
    task_id: str,
    data_referencia: str,
    status: str,
    metrics: dict[str, int | float],
    run_id: str,
) -> None:
    """Insere um evento de execução do Airflow na tabela de auditoria do DW."""
    statement = text(
        """
        INSERT INTO pipeline_audit_log (
            dag_id, run_id, task_id, data_referencia, status, registros_lidos,
            registros_validos, registros_invalidos, registros_inseridos,
            registros_ignorados, duracao_segundos, mensagem
        ) VALUES (
            'etl_vendas_fpa', :run_id, :task_id, :data_referencia, :status,
            :registros_lidos, :registros_validos, :registros_invalidos,
            :registros_inseridos, :registros_ignorados, :duracao_segundos, :mensagem
        )
        """
    )
    parameters = {
        "run_id": run_id,
        "task_id": task_id,
        "data_referencia": data_referencia,
        "status": status,
        "registros_lidos": int(metrics.get("registros_lidos", 0)),
        "registros_validos": int(metrics.get("registros_validos", 0)),
        "registros_invalidos": int(metrics.get("registros_invalidos", 0)),
        "registros_inseridos": int(metrics.get("registros_inseridos", 0)),
        "registros_ignorados": int(metrics.get("registros_ignorados", 0)),
        "duracao_segundos": float(metrics.get("duracao_segundos", 0)),
        "mensagem": f"Tarefa {task_id} finalizada com status {status}",
    }
    with create_dw_engine().begin() as connection:
        connection.execute(statement, parameters)


def existing_file(path: str) -> Path:
    """Converte um caminho XCom em um caminho de sistema de arquivos verificado."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Artefato esperado não existe: {path}")
    return resolved


def audit_task_failure(context: dict[str, Any]) -> None:
    """Persiste metadados de falha quando o Airflow interrompe uma execução diária."""
    task_instance = context["task_instance"]
    data_referencia = context["ds"]
    run_id = context["run_id"]
    task_id = task_instance.task_id
    logger = get_pipeline_logger(task_id, data_referencia)
    try:
        write_audit(task_id, data_referencia, "FAILED", {}, run_id)
    except Exception:
        logger.exception("Falha ao registrar auditoria de task interrompida")
