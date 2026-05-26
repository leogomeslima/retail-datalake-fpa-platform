"""Configurações da aplicação resolvidas a partir de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Configuração tipada de execução para os serviços do pipeline."""

    project_root: Path
    data_lake_base_path: Path
    pipeline_version: str
    log_level: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_pool_size: int
    postgres_max_overflow: int
    taxa_imposto: float
    taxa_despesa_variavel: float
    alerta_meta_vermelho: float
    alerta_meta_amarelo: float
    budget_annual_growth: float

    @property
    def raw_path(self) -> Path:
        """Retorna a localização da camada de dados Raw."""
        return self.data_lake_base_path / "raw"

    @property
    def bronze_path(self) -> Path:
        """Retorna a localização da camada de dados Bronze."""
        return self.data_lake_base_path / "bronze"

    @property
    def silver_path(self) -> Path:
        """Retorna a localização da camada de dados Silver."""
        return self.data_lake_base_path / "silver"

    @property
    def gold_path(self) -> Path:
        """Retorna a localização da camada de dados Gold."""
        return self.data_lake_base_path / "gold"

    @property
    def quarantine_path(self) -> Path:
        """Retorna a localização dos registros em quarentena."""
        return self.data_lake_base_path / "quarantine"

    @property
    def logs_path(self) -> Path:
        """Retorna a localização dos logs estruturados do pipeline."""
        return self.data_lake_base_path / "logs"

    @property
    def database_url(self) -> str:
        """Monta a cadeia de conexão SQLAlchemy para PostgreSQL."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def ensure_data_directories(self) -> None:
        """Cria os diretórios de execução das camadas de dados."""
        for path in (
            self.raw_path,
            self.bronze_path,
            self.silver_path,
            self.gold_path,
            self.quarantine_path,
            self.logs_path,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Carrega as configurações uma única vez por processo Python."""
    base_path = Path(os.getenv("DATA_LAKE_BASE_PATH", str(PROJECT_ROOT / "data")))
    settings = Settings(
        project_root=PROJECT_ROOT,
        data_lake_base_path=base_path,
        pipeline_version=os.getenv("PIPELINE_VERSION", "1.0.0"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "retail_dw"),
        postgres_user=os.getenv("POSTGRES_USER", "retail_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "retail_password"),
        postgres_pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "5")),
        postgres_max_overflow=int(os.getenv("POSTGRES_MAX_OVERFLOW", "10")),
        taxa_imposto=float(os.getenv("TAXA_IMPOSTO", "0.12")),
        taxa_despesa_variavel=float(os.getenv("TAXA_DESPESA_VARIAVEL", "0.06")),
        alerta_meta_vermelho=float(os.getenv("ALERTA_META_VERMELHO", "0.80")),
        alerta_meta_amarelo=float(os.getenv("ALERTA_META_AMARELO", "0.95")),
        budget_annual_growth=float(os.getenv("BUDGET_ANNUAL_GROWTH", "0.05")),
    )
    settings.ensure_data_directories()
    return settings
