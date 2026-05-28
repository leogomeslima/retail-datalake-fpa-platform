# Plataforma Retail Data Lake FP&A

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Airflow](https://img.shields.io/badge/Apache_Airflow-2.8-017CEE)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

Este projeto simula uma plataforma de dados de ponta a ponta para uma rede varejista com 5 lojas físicas. Cada loja gera arquivos JSON com suas vendas diárias, enviados para um Data Lake local organizado em camadas (Raw -> Bronze -> Silver -> Gold). Um pipeline ETL orquestrado com Apache Airflow coleta, valida, transforma e consolida esses dados. Os dados tratados são carregados em um Data Warehouse PostgreSQL com modelagem dimensional, onde são gerados KPIs de vendas, DRE gerencial e indicadores de FP&A.

O projeto demonstra, de forma prática, domínio em Engenharia de Dados, Data Lake, ETL, Apache Airflow, PostgreSQL, modelagem dimensional, SQL analítico, qualidade de dados, KPIs financeiros e gestão FP&A, habilidades diretamente aplicáveis a posições de Data Engineer, Analytics Engineer e Data Analyst com visão financeira.

## Índice

- [Plataforma Retail Data Lake FP\&A](#plataforma-retail-data-lake-fpa)
  - [Índice](#índice)
  - [Aplicação em Funcionamento](#aplicação-em-funcionamento)
  - [Arquitetura](#arquitetura)
  - [Pré-requisitos](#pré-requisitos)
  - [Execução](#execução)
    - [Adicionar abril ou meses futuros](#adicionar-abril-ou-meses-futuros)
  - [Estrutura](#estrutura)
  - [Camadas](#camadas)
  - [Pipeline](#pipeline)
  - [Data Warehouse](#data-warehouse)
  - [Métricas Financeiras](#métricas-financeiras)
  - [Testes](#testes)
  - [Boas Práticas](#boas-práticas)
  - [Power BI](#power-bi)
  - [Painel React](#painel-react)
  - [Documentação](#documentação)
  - [Diagrama de Fluxo](#diagrama-de-fluxo)
  - [Roadmap](#roadmap)

## Aplicação em Funcionamento

A interface React consome exclusivamente dados processados no Data Warehouse. As telas
abaixo foram capturadas com a aplicação em execução, após cargas reais emitidas pelo PDV
e processadas pelo pipeline.

### Painel de Indicadores

Visão executiva para acompanhar receita líquida, EBITDA, ticket médio, metas por loja,
produtos, canais e saúde do processamento.

![Painel de Indicadores com métricas financeiras e operacionais](artifacts/readme-dashboard-largo.jpg)

### Evolução de Lojas

Análise temporal das lojas e da rede, com gráfico de linhas, comparação de medidas e
detalhamento da competência mais recente.

![Página de Evolução de Lojas com gráfico de linhas](artifacts/readme-evolucao-larga.jpg)

### Ajuste de Forecast

Projeção dos próximos meses baseada no realizado, com cenário ajustável, comparação
contra orçamento e detalhamento por unidade.

![Página de Ajuste de Forecast com projeções mensais](artifacts/readme-forecast-largo.jpg)

### Operação PDV

Terminal operacional para emitir o fechamento de um turno ou fechar o dia completo,
gerando arquivos Raw e carregando o Data Warehouse.

![Página de Operação PDV com emissão de fechamento diário](artifacts/readme-pdv-largo.jpg)

## Arquitetura

```text
PDV RetailCo (5 lojas, 3 turnos)
        |
        v
data/raw/vendas/loja=loja_N/ano=YYYY/mes=MM/dia=DD/*.json
        |
        v
Apache Airflow: contrato Pydantic + regras de qualidade
        |                                      |
        v                                      v
Bronze CSV padronizado                  Quarantine CSV
        |
        v
Silver Parquet: financeiro, tempo, rastreabilidade
        |                                      |
        v                                      v
Gold CSV: KPIs, DRE, FP&A       PostgreSQL 15 Data Warehouse
                                               |
                                               v
                           Views analíticas / Power BI / SQL

Airflow metadata PostgreSQL :5433       Retail Data Warehouse PostgreSQL :5432
```

O banco interno do Airflow e o Data Warehouse são serviços independentes. O grão de `fato_vendas` é uma linha por item; nesta versão inicial, cada venda simulada possui exatamente um item, e a chave idempotente é `(id_venda, loja_id)`.

## Pré-requisitos

- Docker Engine 24 ou superior e Docker Compose 2.20 ou superior.
- GNU Make ou execução direta dos comandos equivalentes de `docker compose`.
- Para desenvolvimento sem containers: Python 3.11 e ambiente virtual.

`requirements.txt` define o runtime ETL standalone com SQLAlchemy 2.0. O container `requirements-airflow.txt` deliberadamente preserva SQLAlchemy 1.4 fornecido pelo Airflow 2.8, pois essa é a restrição oficial do orquestrador; as operações SQL usadas pelo pipeline são compatíveis com as duas versões.

## Execução

Prepare as variáveis locais e suba a plataforma:

```bash
cp .env.example .env
make build
make up
```

A interface do Airflow fica disponível em `http://localhost:8080` por padrão. Caso a porta
esteja ocupada, altere `AIRFLOW_WEBSERVER_PORT` no `.env`, por exemplo para `8081`. O DW
responde em `localhost:5432`, enquanto os metadados do Airflow respondem separadamente em
`localhost:5433`.

Gere os 90 dias de dados Raw (1.350 arquivos JSON e milhares de vendas) e processe uma data:

```bash
make generate-data
make run-pipeline REFERENCE_DATE=2026-01-01
make run-backfill
make psql
```

### Adicionar abril ou meses futuros

O gerador aceita qualquer competência `YYYY-MM` e cria identificadores de venda baseados na data, sem colidir com lotes processados anteriormente. Para carregar abril de 2026:

```bash
make generate-month MONTH=2026-04
make load-month MONTH=2026-04
```

Para carregar outro mês, altere apenas a competência:

```bash
make generate-month MONTH=2027-01
make load-month MONTH=2027-01
```

Ao processar um novo ano, o pipeline inclui automaticamente as novas datas em `dim_tempo` e provisiona `fato_orcamento` para os doze meses daquele ano. A premissa de crescimento anual do orçamento é configurável em `.env` por `BUDGET_ANNUAL_GROWTH`, cujo padrão é `0.05`.

Os arquivos Raw são imutáveis por padrão. Caso uma partição precise de correção deliberada antes de uma nova carga, gere-a novamente com `--overwrite` e preserve o evento nos logs de auditoria.

Em ambientes iniciados antes da ampliação de `cliente_id` para `BIGINT`, aplique uma vez:

PowerShell:

```powershell
Get-Content database\migrations\002_expand_customer_business_key.sql |
  docker compose --env-file .env exec -T postgres_dw psql -U retail_user -d retail_dw
```

Bash:

```bash
docker compose --env-file .env exec -T postgres_dw psql -U retail_user -d retail_dw \
  < database/migrations/002_expand_customer_business_key.sql
```

Em ambientes que já tenham dados cadastrados antes da revisão ortográfica dos rótulos,
aplique também a normalização de nomes exibidos no painel:

```powershell
Get-Content database\migrations\003_normalize_portuguese_labels.sql |
  docker compose --env-file .env exec -T postgres_dw psql -U retail_user -d retail_dw
```

No uso diário, basta depositar os JSONs do PDV na partição Raw da data; a DAG Airflow `etl_vendas_fpa` executa a carga incremental às 06:00, e o `UPSERT` impede duplicação.

### Airflow automático e acionamento manual

Sim. Com `airflow-scheduler` ativo, o Airflow permanece em segundo plano verificando o
agendamento da DAG `etl_vendas_fpa`, configurada para executar diariamente às `06:00`.
Quando não encontra arquivos Raw da data, a execução encerra pelo ramo `sem_dados`.

Para acionar a DAG manualmente pela interface:

1. Acesse `http://localhost:${AIRFLOW_WEBSERVER_PORT}` e faça login; no `.env.example`,
   o endereço padrão é `http://localhost:8080`.
2. Localize a DAG `etl_vendas_fpa`.
3. Ative a DAG caso esteja pausada.
4. Clique em `Trigger DAG` e defina a data lógica desejada.
5. Acompanhe as tasks no Grid ou Graph View.

Para executar manualmente por terminal usando o Airflow:

```bash
make trigger-airflow REFERENCE_DATE=2026-05-25
```

O comando equivalente é:

```bash
docker compose exec airflow-scheduler airflow dags unpause etl_vendas_fpa
docker compose exec airflow-scheduler airflow dags trigger -e 2026-05-25 etl_vendas_fpa
```

Na página PDV, o botão `Processar data no DW` fornece um caminho imediato: ele chama o
mesmo pipeline ETL pela API e registra o `run_id` com prefixo `pdv_api_`, sem aguardar a
execução agendada da DAG. Use o Airflow quando quiser monitoramento orquestrado por tarefas,
novas tentativas e histórico visual da execução.

Consultas para confirmar a carga:

```sql
SELECT COUNT(*) FROM fato_vendas;
SELECT * FROM vw_meta_vs_realizado ORDER BY ano, mes, loja_id LIMIT 5;
SELECT * FROM vw_indicadores_fpa ORDER BY ano, mes, loja_id;
```

Também é possível emitir somente um fechamento de turno pelo aplicativo PDV:

```bash
python -m app_vendas.main --loja-id 1 --data 2026-05-24 --turno MANHA --quantidade 35
python -m scripts.run_pipeline 2026-05-24 --skip-database
```

## Estrutura

```text
api/              API FastAPI de indicadores e operações PDV
app_vendas/       simulador PDV e escrita atômica de Raw
config/           settings via ambiente, lojas, produtos e orçamento
dags/             DAG Airflow diária e utilitários de auditoria
scripts/          gerador, qualidade, ETL, carga, KPIs, DRE e FP&A
database/         DDL, seeds, migrations, views e 20 queries
data/             camadas locais particionadas e logs JSON
dashboards/       modelo semântico e dicionário para Power BI
docs/             manuais operacionais e referência REST
frontend/         React: Painel de Indicadores e terminal PDV
notebooks/        EDA, qualidade e FP&A sobre artefatos reais
tests/            testes unitários e integração do pipeline/DW
```

## Camadas

| Camada | Conteúdo | Exemplo |
| --- | --- | --- |
| Raw | JSON imutável por loja, dia e turno com checksum | `data/raw/vendas/loja=loja_1/ano=2026/mes=01/dia=01/vendas_1_20260101_manha.json` |
| Bronze | Registros achatados, validados por contrato e com origem | `data/bronze/vendas/ano=2026/mes=01/dia=01/vendas_bronze_20260101.csv` |
| Silver | Parquet tipado com valores, calendário e status operacional | `data/silver/vendas_tratadas/ano=2026/mes=01/dia=01/vendas_silver_20260101.parquet` |
| Gold | Agregações de negócio mensais prontas para BI | `data/gold/indicadores_fpa/fpa_202601.csv` |
| Quarantine | Linhas ou arquivos recusados com causa observável | `data/quarantine/registros_invalidos_20260101.csv` |

Cada registro Silver inclui `arquivo_origem`, `arquivo_checksum`, `pipeline_id`, `timestamp_ingestao`, `processed_at` e `pipeline_version`. Reprocessar uma origem alterada atualiza o fato e o controle `processed_files`; reprocessar sem alteração não duplica fatos.

## Pipeline

1. `generate_sales_data.py` gera vendas Faker em horário comercial, Pareto de produtos, clientes recorrentes, sazonalidade de fim de semana, descontos e cancelamentos.
2. `extract.py` valida o envelope JSON com Pydantic e grava Bronze; arquivos corrompidos vão para quarentena sem impedir outras lojas.
3. `validate.py` executa onze regras, calcula a taxa de aprovação e isola linhas inválidas.
4. `transform.py` deduplica, converte tipos, calcula valores e tempo e separa cancelamentos.
5. `load.py` carrega clientes e vendas com PostgreSQL `ON CONFLICT DO UPDATE`, registra checksums em `processed_files` e mantém auditoria.
6. `kpis.py`, `dre.py` e `fpa.py` produzem Gold mensal e alimentam o resultado gerencial.

Para a carga inicial, `backfill.py` percorre todas as partições Raw históricas e aplica a mesma execução idempotente usada diariamente, sem um caminho alternativo de transformação.

A DAG `etl_vendas_fpa` é agendada diariamente às 06:00, possui novas tentativas exponenciais, limites de tempo, `max_active_runs=1`, verificação Raw por loja, XComs e ramificação quando não há arquivos para ingerir.

## Data Warehouse

O modelo estrela contém:

| Tabela | Responsabilidade |
| --- | --- |
| `dim_loja`, `dim_produto`, `dim_cliente`, `dim_tempo` | Contexto mestre e calendário |
| `fato_vendas` | Item vendido com medidas financeiras e origem |
| `fato_orcamento` | Meta financeira mensal por loja |
| `fato_dre` | Demonstração de resultado mensal calculada |
| `processed_files` | Checksum, camada, status e reprocessamento |
| `pipeline_audit_log` | Execuções, volumes, rejeições e duração |

O arquivo `database/views.sql` publica dez views: faturamento mensal, receita por loja, ticket, ranking, meta versus realizado, DRE, FP&A, top produtos, canais e saúde do pipeline. `database/queries_analiticas.sql` contém vinte consultas prontas para analistas.

## Métricas Financeiras

```text
valor_bruto       = quantidade * valor_unitario
valor_liquido     = valor_bruto - desconto_valor
custo_total       = quantidade * custo_unitario
margem_bruta      = valor_liquido - custo_total
receita_liquida   = receita_bruta - descontos - impostos
EBITDA            = lucro_bruto - despesas_variaveis - despesas_fixas
forecast_mes      = receita_realizada / dias_com_venda * dias_do_mes
run_rate_anual    = forecast_mes * 12
budget_variance   = receita_realizada - receita_orcada
```

Alertas FP&A são classificados como `VERMELHO` abaixo de 80% da meta, `AMARELO` entre 80% e 95% e `VERDE` a partir de 95%.

## Testes

Instale as dependências para desenvolvimento local e execute as verificações:

```bash
python -m pip install -r requirements.txt
make quality
```

Os testes unitários cobrem fórmulas, deduplicação, classificação de turno, regras de qualidade, KPIs, DRE e forecast. O teste end-to-end gera arquivos Raw reais e processa até Gold em uma área temporária. Para provar idempotência no PostgreSQL:

```bash
set TEST_DATABASE_URL=postgresql+psycopg2://retail_user:retail_password@localhost:5432/retail_dw
python -m pytest tests/integration/test_load_postgres.py
```

## Boas Práticas

- Contrato de entrada Pydantic, checksum SHA-256 e escrita atômica.
- Separação Raw, Bronze, Silver, Gold e Quarantine com particionamento por data.
- Configuração por ambiente, logs JSON e auditoria no warehouse.
- UPSERT real para fatos, DRE e dimensão cliente; seeds reexecutáveis.
- Black, Ruff, Mypy, pre-commit, testes unitários e integração.
- Falha de arquivo ou loja isolada durante extração e rastreável em quarentena.

## Power BI

Use `dashboards/powerbi_model.md` para configurar os relacionamentos e `dashboards/metricas_dashboard.md` para implementar medidas. As views publicadas reduzem a lógica DAX necessária e expõem ranking, semáforo, forecast e run rate diretamente do DW.

## Painel React

O frontend em `frontend/` consulta a API FastAPI em `api/` diretamente sobre o Data Warehouse. Ele apresenta receita, EBITDA, ticket, margem, pendências, tendência mensal, ranking de lojas, top produtos, forecast, canais e observabilidade do pipeline, com atualização automática a cada 15 segundos.

Os serviços sobem junto com a plataforma:

```bash
docker compose --env-file .env.example up -d --build api frontend
```

- Painel de Indicadores: `http://localhost:5173`
- Evolução de lojas: `http://localhost:5173/evolucao`
- Detalhe da loja: `http://localhost:5173/lojas/1`
- Ajuste de forecast: `http://localhost:5173/forecast`
- Previsão ML: `http://localhost:5173/previsao-ml`
- Qualidade dos dados: `http://localhost:5173/qualidade`
- API: `http://localhost:8000/api/health`
- Swagger: `http://localhost:8000/docs`

### Operação PDV

A página `http://localhost:5173/pdv` simula o fechamento operacional de um terminal sem
dados fictícios pré-carregados. O operador escolhe loja, data, turno e quantidade de vendas; a emissão grava
um JSON Raw validado e imutável, apresenta as transações e permite processar imediatamente a
data pelas camadas Bronze, Silver, Gold e Data Warehouse.

Cada turno de uma loja possui namespace próprio de vendas e clientes, permitindo fechar
`MANHA`, `TARDE` e `NOITE` na mesma data sem colisão de chaves.

O botão `Fechar dia completo, emitir Raw e carregar DW` executa o fechamento geral: usa a quantidade
informada para cada uma das cinco lojas e três turnos, gerando `15` arquivos Raw e um
resumo consolidado; ao concluir a emissão, executa imediatamente o pipeline até o Data
Warehouse para refletir o dia no dashboard, na evolução e no forecast. Caso algum
arquivo daquela data já exista, a emissão diária é recusada para preservar a
imutabilidade e evitar um fechamento parcial.

### Evolução de Lojas

A página `http://localhost:5173/evolucao` acompanha a trajetória mensal de cada unidade
em gráficos de linha. É possível comparar receita líquida, ticket médio, margem bruta,
meta atingida e participação na receita, além de consultar forecast da loja, EBITDA e cancelamento
consolidados da rede.

### Drill-down por Loja

A página `http://localhost:5173/lojas/1` detalha uma unidade específica e pode ser aberta
diretamente pelo ranking de lojas do dashboard. Ela reúne histórico mensal, receita,
ticket médio, meta, EBITDA, produtos líderes, canais de venda, status operacional,
qualidade dos arquivos, rastreabilidade dos últimos arquivos e previsão futura combinando
forecast gerencial com previsão estatística.

### Ajuste de Forecast

A página `http://localhost:5173/forecast` projeta de 3 a 12 competências futuras a
partir do realizado e do forecast de fechamento vigente. O cenário aplica a tendência
recente por loja, limitada entre `-15%` e `15%` ao mês, e permite um ajuste gerencial
entre `-30%` e `30%`. A tela confronta previsão e orçamento quando o orçamento da
competência futura já estiver provisionado, além de estimar EBITDA com a margem recente.

### Previsão ML

A página `http://localhost:5173/previsao-ml` oferece uma visão preditiva estatística
separada do ajuste gerencial. Ela treina uma regressão linear simples sobre a receita
mensal realizada, mostra tendência, RMSE, ajuste R², backtest do último mês e uma faixa
estimada para os próximos meses. Junho aparece nessa tela como previsão futura, não como
movimento realizado.

### Qualidade dos Dados

A página `http://localhost:5173/qualidade` monitora a saúde do fluxo de arquivos. Ela
consolida `processed_files` e `pipeline_audit_log` para mostrar taxa de aprovação,
arquivos processados, reprocessamentos, rejeições, duração média das tarefas, cobertura
por loja na última data e rastreabilidade dos arquivos mais recentes.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [`docs/ARQUITETURA_E_OPERACAO.md`](docs/ARQUITETURA_E_OPERACAO.md) | Arquitetura, implantação, Data Lake, DW, ETL, dashboard e testes |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Contratos REST, payloads, respostas e códigos de erro |
| [`docs/GUIA_PDV.md`](docs/GUIA_PDV.md) | Procedimento operacional de emissão e processamento do PDV |
| [`docs/DIAGRAMA_FLUXO.md`](docs/DIAGRAMA_FLUXO.md) | Diagramas Mermaid do fluxo geral, DAG Airflow e operação PDV |

## Diagrama de Fluxo

O fluxo completo da plataforma, incluindo as alternativas de execução por Airflow
ou pelo processamento imediato do PDV, está documentado em
[`docs/DIAGRAMA_FLUXO.md`](docs/DIAGRAMA_FLUXO.md).

```mermaid
flowchart LR
    PDV["PDV React"] --> RAW["Raw JSON Imutável"]
    RAW --> RUN{"Execução"}
    RUN -->|Agendada ou manual| AIR["Airflow DAG"]
    RUN -->|Imediata| FAST["API PDV"]
    AIR --> ETL["ETL"]
    FAST --> ETL
    ETL --> DW["Data Warehouse"]
    DW --> API["FastAPI"]
    API --> DASH["Painel de Indicadores React"]
```

## Roadmap

- Armazenamento de objetos compatível com S3/MinIO para substituir volume local.
- Métricas Prometheus e alertas operacionais por SLA.
- Histórico SCD tipo 2 para mudanças organizacionais de lojas e produtos.
- Forecast estatístico com validação de erro contra o realizado.
