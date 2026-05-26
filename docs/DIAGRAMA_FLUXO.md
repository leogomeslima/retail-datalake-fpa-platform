# Diagrama de Fluxo - Retail Data Lake FP&A

## Fluxo Geral da Plataforma

```mermaid
flowchart TD
    U["Operador / Analista"] --> PDV["Página Operação PDV<br/>React :5173/pdv"]
    U --> BI["Painel de Indicadores FP&A<br/>React :5173"]
    U --> AFUI["Interface Airflow<br/>:8080 ou porta configurada"]

    PDV --> CFG["GET /api/pdv/config<br/>Lojas, produtos e turnos"]
    PDV --> EMIT["POST /api/pdv/turnos<br/>Fechar turno"]
    PDV --> DAY["POST /api/pdv/fechamentos-gerais<br/>Fechar dia completo e carregar DW"]
    DAY --> GEN
    DAY --> NOW
    EMIT --> GEN["VendaService<br/>Gera vendas realistas"]
    GEN --> VALIDRAW["Contrato Pydantic<br/>Checksum SHA-256"]
    VALIDRAW --> RAW["RAW JSON Imutável<br/>loja / ano / mês / dia / turno"]

    PDV --> NOW["POST /api/pdv/processamentos<br/>Processamento imediato"]
    NOW --> ETL["Pipeline ETL da data"]

    RAW --> SCHEDULE["airflow-scheduler<br/>Agenda diária 06:00"]
    AFUI --> TRIGGER["Trigger manual da DAG<br/>Data lógica selecionada"]
    SCHEDULE --> DAG["DAG etl_vendas_fpa"]
    TRIGGER --> DAG
    DAG --> CHECK{"Há Raw<br/>para a data?"}
    CHECK -->|Não| EMPTY["Tarefa sem_dados<br/>Execução encerrada"]
    CHECK -->|Sim| ETL

    ETL --> EXTRACT["Extract<br/>Raw para Bronze"]
    EXTRACT --> CONTRACT{"Arquivo atende<br/>ao contrato?"}
    CONTRACT -->|Não| QUAR["Quarantine<br/>Arquivo rejeitado"]
    CONTRACT -->|Sim| BRONZE["Bronze CSV<br/>Dados achatados + origem"]

    BRONZE --> QUALITY["Validate<br/>Regras de qualidade"]
    QUALITY --> RULES{"Registro<br/>aprovado?"}
    RULES -->|Não| INVALID["Quarantine CSV<br/>Registros inválidos"]
    RULES -->|Sim| SILVER["Silver Parquet<br/>Valores + calendário + status"]

    SILVER --> LOAD["Load Idempotente<br/>UPSERT PostgreSQL"]
    SILVER --> GOLD["Gold<br/>KPIs + DRE + FP&A"]
    LOAD --> DW["Data Warehouse<br/>Modelo estrela"]
    GOLD --> DW

    DW --> AUDIT["processed_files<br/>pipeline_audit_log"]
    DW --> VIEWS["Views Analíticas"]
    VIEWS --> API["FastAPI :8000<br/>/api/dashboard"]
    API --> BI
    AUDIT --> API

    style RAW fill:#eef7f3,stroke:#08735a
    style DW fill:#e8f0fa,stroke:#204c86
    style BI fill:#ecf8f4,stroke:#08735a
    style QUAR fill:#fff1f0,stroke:#b53838
    style INVALID fill:#fff1f0,stroke:#b53838
    style DAG fill:#eef4ff,stroke:#017cee
```

## Caminhos de Execução

```mermaid
flowchart LR
    DATA["Arquivos Raw da data"] --> CHOICE{"Como processar?"}

    CHOICE -->|Automático| AUTO["Scheduler Airflow<br/>Todos os dias às 06:00"]
    CHOICE -->|Manual orquestrado| MANUAL["Interface Airflow ou<br/>make trigger-airflow"]
    CHOICE -->|Imediato operacional| DIRECT["Botão do PDV<br/>Processar data no DW"]

    AUTO --> DAG["DagRun<br/>tarefas + novas tentativas + histórico visual"]
    MANUAL --> DAG
    DIRECT --> APIEXEC["FastAPI<br/>run_id pdv_api_*"]

    DAG --> PIPE["Mesmo pipeline ETL<br/>Raw -> Bronze -> Silver -> Gold -> DW"]
    APIEXEC --> PIPE
    PIPE --> PANEL["Painel atualizado<br/>Atualização a cada 15 s"]
```

## Fluxo da DAG Airflow

```mermaid
flowchart TD
    START(["start"]) --> L1["verificar_raw_loja_1"]
    START --> L2["verificar_raw_loja_2"]
    START --> L3["verificar_raw_loja_3"]
    START --> L4["verificar_raw_loja_4"]
    START --> L5["verificar_raw_loja_5"]

    L1 --> BRANCH{"aguardar_todos_raw"}
    L2 --> BRANCH
    L3 --> BRANCH
    L4 --> BRANCH
    L5 --> BRANCH

    BRANCH -->|Nenhum dado| NODATA["sem_dados"]
    NODATA --> END(["end"])

    BRANCH -->|Com dados| B["extrair_bronze"]
    B --> V["validar_qualidade"]
    V --> INV["registrar_invalidos"]
    V --> S["transformar_silver"]
    S --> LOAD["carregar_datawarehouse"]

    LOAD --> KPIS["gerar_kpis"]
    LOAD --> DRE["gerar_dre_gerencial"]
    LOAD --> FPA["gerar_fpa"]

    KPIS --> GOLD["atualizar_gold_layer"]
    DRE --> GOLD
    FPA --> GOLD
    GOLD --> PUB["publicar_relatorio_diario"]
    PUB --> END

    style LOAD fill:#e8f0fa,stroke:#204c86
    style PUB fill:#ecf8f4,stroke:#08735a
    style NODATA fill:#f5f5f5,stroke:#737373
```

## Fluxo do Operador PDV

```mermaid
sequenceDiagram
    actor O as Operador
    participant F as Página PDV React
    participant A as API FastAPI
    participant R as Data Lake Raw
    participant P as Pipeline ETL
    participant D as Data Warehouse
    participant C as Painel de Indicadores

    O->>F: Seleciona loja, data, turno e volume
    F->>A: POST /api/pdv/turnos
    A->>A: Gera vendas e valida contrato
    A->>R: Grava JSON Raw imutável
    R-->>A: Arquivo + checksum + pipeline_id
    A-->>F: Totais e lista de transações
    F-->>O: Exibe resumo do caixa

    O->>F: Clica "Fechar dia completo, emitir Raw e carregar DW"
    F->>A: POST /api/pdv/fechamentos-gerais
    A->>R: Grava 15 documentos Raw
    A->>P: Executa a carga automática da data
    P->>D: UPSERT fatos, DRE e auditoria
    A-->>F: Resumo Raw e processamento

    O->>F: Clica "Processar data no DW"
    F->>A: POST /api/pdv/processamentos
    A->>P: Executa data com run_id pdv_api_*
    P->>D: UPSERT fatos, DRE e auditoria
    D-->>A: Inseridos e atualizados
    A-->>F: Resultado do processamento
    F-->>O: Confirma carga

    C->>A: GET /api/dashboard?competencia=YYYY-MM
    A->>D: Consulta views e fatos
    D-->>A: Indicadores
    A-->>C: Snapshot atualizado
```

## Decisões Importantes

| Decisão | Efeito no Fluxo |
| --- | --- |
| Raw imutável | Um mesmo fechamento loja/data/turno não é substituído acidentalmente |
| IDs separados por turno | `MANHA`, `TARDE` e `NOITE` podem coexistir na mesma data |
| UPSERT no fato | Reprocessar uma data não duplica vendas |
| `run_id` auditável | É possível distinguir execução Airflow e processamento iniciado no PDV |
| Duas formas de execução | Operação imediata via PDV ou orquestração completa via Airflow |
