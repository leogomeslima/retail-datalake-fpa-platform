"""DAG do Airflow que orquestra o processamento diário do Data Lake RetailCo."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule

from dags.dag_utils import (
    audit_task_failure,
    choose_ingestion_branch,
    existing_file,
    raw_files_for_store,
    write_audit,
)
from scripts.dre import gerar_dre, upsert_dre_datawarehouse
from scripts.extract import extrair_raw_para_bronze
from scripts.fpa import gerar_fpa
from scripts.kpis import gerar_kpis
from scripts.load import carregar_silver_datawarehouse, create_dw_engine
from scripts.transform import transformar_bronze_para_silver
from scripts.validate import validar_bronze


def extract_task(ds: str, **context: object) -> dict[str, object]:
    """Executa a extração Bronze e publica metadados serializáveis."""
    result = extrair_raw_para_bronze(ds, [1, 2, 3, 4, 5])
    return {"path": str(result.caminho_bronze), "records": result.total_registros}


def validation_task(ds: str, ti: object, **context: object) -> dict[str, object]:
    """Valida a saída Bronze diária e expõe caminhos válidos e inválidos."""
    extracted = ti.xcom_pull(task_ids="extrair_bronze")  # type: ignore[attr-defined]
    bronze = existing_file(extracted["path"])
    result = validar_bronze(ds, bronze)
    return {
        "valid_path": str(result.caminho_validos),
        "invalid_path": str(result.caminho_invalidos),
        "valid_records": result.registros_validos,
        "invalid_records": result.registros_invalidos,
    }


def transformation_task(ds: str, ti: object, **context: object) -> dict[str, object]:
    """Produz registros financeiros Silver a partir das linhas aceitas."""
    validated = ti.xcom_pull(task_ids="validar_qualidade")  # type: ignore[attr-defined]
    valid = existing_file(validated["valid_path"])
    result = transformar_bronze_para_silver(ds, valid)
    return {"silver_path": str(result.caminho_silver), "records": result.registros_saida}


def load_task(ds: str, ti: object, run_id: str, **context: object) -> dict[str, object]:
    """Carrega a saída Silver no Data Warehouse dimensional."""
    transformed = ti.xcom_pull(task_ids="transformar_silver")  # type: ignore[attr-defined]
    silver = existing_file(transformed["silver_path"])
    result = carregar_silver_datawarehouse(ds, silver, run_id)
    return result.__dict__


def kpi_task(ds: str, **context: object) -> str:
    """Cria produtos Gold de KPIs para o mês de referência."""
    reference = datetime.fromisoformat(ds)
    return str(gerar_kpis(reference.year, reference.month).resumo_path)


def dre_task(ds: str, **context: object) -> str:
    """Cria a saída Gold de DRE para o mês de referência."""
    reference = datetime.fromisoformat(ds)
    return str(gerar_dre(reference.year, reference.month).caminho_dre)


def fpa_task(ds: str, **context: object) -> str:
    """Cria a saída Gold de FP&A para o mês de referência."""
    reference = datetime.fromisoformat(ds)
    return str(gerar_fpa(reference.year, reference.month).caminho_fpa)


def publish_task(ds: str, ti: object, run_id: str, **context: object) -> None:
    """Carrega o fato DRE e publica as métricas finais de auditoria."""
    dre_artifact = ti.xcom_pull(task_ids="gerar_dre_gerencial")  # type: ignore[attr-defined]
    dre_path = existing_file(dre_artifact)
    upsert_dre_datawarehouse(pd.read_csv(dre_path), create_dw_engine())
    load_result = ti.xcom_pull(task_ids="carregar_datawarehouse")  # type: ignore[attr-defined]
    write_audit(
        "publicar_relatorio_diario",
        ds,
        "SUCCESS",
        {
            "registros_lidos": load_result["registros_recebidos"],
            "registros_validos": load_result["registros_recebidos"],
            "registros_inseridos": load_result["registros_inseridos"],
            "registros_ignorados": load_result["registros_atualizados"],
        },
        run_id,
    )


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(hours=2),
    "on_failure_callback": audit_task_failure,
}

with DAG(
    dag_id="etl_vendas_fpa",
    description="Pipeline ETL completo: Raw -> Bronze -> Silver -> Gold -> DW",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["etl", "vendas", "fpa", "producao"],
    doc_md="Pipeline diario de vendas das cinco lojas para analise FP&A.",
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end", trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
    sem_dados = EmptyOperator(task_id="sem_dados")
    checks = [
        PythonOperator(
            task_id=f"verificar_raw_loja_{loja_id}",
            python_callable=raw_files_for_store,
            op_kwargs={"data_referencia": "{{ ds }}", "loja_id": loja_id},
            execution_timeout=timedelta(minutes=5),
        )
        for loja_id in range(1, 6)
    ]
    branch = BranchPythonOperator(
        task_id="aguardar_todos_raw",
        python_callable=choose_ingestion_branch,
        execution_timeout=timedelta(minutes=5),
    )
    extraction = PythonOperator(
        task_id="extrair_bronze",
        python_callable=extract_task,
        op_kwargs={"ds": "{{ ds }}"},
        execution_timeout=timedelta(minutes=30),
    )
    validation = PythonOperator(
        task_id="validar_qualidade",
        python_callable=validation_task,
        op_kwargs={"ds": "{{ ds }}"},
        execution_timeout=timedelta(minutes=20),
    )
    invalids = EmptyOperator(task_id="registrar_invalidos")
    transformation = PythonOperator(
        task_id="transformar_silver",
        python_callable=transformation_task,
        op_kwargs={"ds": "{{ ds }}"},
        execution_timeout=timedelta(minutes=30),
    )
    load = PythonOperator(
        task_id="carregar_datawarehouse",
        python_callable=load_task,
        op_kwargs={"ds": "{{ ds }}", "run_id": "{{ run_id }}"},
        execution_timeout=timedelta(minutes=45),
    )
    kpis = PythonOperator(
        task_id="gerar_kpis", python_callable=kpi_task, op_kwargs={"ds": "{{ ds }}"}
    )
    dre = PythonOperator(
        task_id="gerar_dre_gerencial", python_callable=dre_task, op_kwargs={"ds": "{{ ds }}"}
    )
    fpa = PythonOperator(
        task_id="gerar_fpa", python_callable=fpa_task, op_kwargs={"ds": "{{ ds }}"}
    )
    gold = EmptyOperator(task_id="atualizar_gold_layer")
    publish = PythonOperator(
        task_id="publicar_relatorio_diario",
        python_callable=publish_task,
        op_kwargs={"ds": "{{ ds }}", "run_id": "{{ run_id }}"},
    )
    start >> checks >> branch
    branch >> sem_dados >> end
    branch >> extraction >> validation
    validation >> invalids
    validation >> transformation >> load >> [kpis, dre, fpa] >> gold >> publish >> end
