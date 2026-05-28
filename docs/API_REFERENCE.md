# Referência da API RetailCo

## Visão Geral

| Item | Valor |
| --- | --- |
| Framework | FastAPI |
| URL local | `http://localhost:8000` |
| Base path | `/api` |
| Swagger UI | `http://localhost:8000/docs` |
| Formato | JSON |
| CORS local | `http://localhost:5173`, `http://127.0.0.1:5173` |

Os endpoints analíticos consultam o Data Warehouse. Os endpoints PDV emitem
arquivos reais na camada Raw e podem executar a carga do dia no DW.

## Endpoints Analíticos

### `GET /api/health`

Verifica conectividade da API com o Data Warehouse e informa a competência
mais recente com venda concluída.

Resposta `200`:

```json
{
  "status": "ok",
  "latest_competence": "2026-05",
  "checked_at": "2026-05-25T09:41:00+00:00"
}
```

### `GET /api/competences`

Lista competências existentes em `fato_vendas`, da mais recente para a mais
antiga.

Resposta `200`:

```json
{
  "items": ["2026-05", "2026-04", "2026-03", "2026-02", "2026-01"]
}
```

### `GET /api/dashboard`

Retorna o retrato completo do painel. O parâmetro `competencia` é
opcional; sem ele, a API escolhe a competência mais recente.

Parâmetros:

| Nome | Tipo | Obrigatório | Exemplo |
| --- | --- | --- | --- |
| `competencia` | string `YYYY-MM` | Não | `2026-04` |

Exemplo:

```http
GET /api/dashboard?competencia=2026-04
```

Estrutura da resposta `200`:

```json
{
  "updated_at": "2026-05-25T09:41:00+00:00",
  "data": {
    "competencia": "2026-04",
    "overview": {
      "receita_liquida": 13361503.3,
      "receita_bruta": 14351782.78,
      "descontos": 990279.48,
      "margem_bruta": 5006939.3,
      "pedidos": 4943,
      "canceladas": 232,
      "pendentes": 184,
      "ticket_medio": 2703.12
    },
    "dre": {},
    "trend": [],
    "stores": [],
    "products": [],
    "fpa": [],
    "channels": [],
    "pipeline": {}
  }
}
```

Erros:

| Status | Condição |
| --- | --- |
| `404` | Nenhuma competência foi carregada no DW ou a competência solicitada ainda não foi carregada |
| `422` | Formato de competência inválido |

### `GET /api/evolution`

Retorna séries históricas mensais para a página de evolução de lojas. Não recebe
parâmetros e contempla todas as competências carregadas.

Resposta `200`:

```json
{
  "updated_at": "2026-05-26T03:18:14+00:00",
  "data": {
    "stores": [
      { "loja_id": 1, "loja_nome": "Loja Centro" }
    ],
    "network": [
      {
        "competencia": "2026-04",
        "receita_liquida": 13361503.3,
        "ticket_medio": 2703.12,
        "ebitda": 2396368.0,
        "margem_ebitda_pct": 20.6,
        "cancelamento_pct": 4.33
      }
    ],
    "store_series": [
      {
        "competencia": "2026-04",
        "loja_id": 1,
        "loja_nome": "Loja Centro",
        "receita": 3424006.0,
        "ticket_medio": 2711.0,
        "margem_pct": 37.4,
        "market_share_pct": 25.6,
        "receita_orcada": 848500.0,
        "meta_atingida_pct": 403.5,
        "forecast_mes": 3424006.0
      }
    ]
  }
}
```

### `GET /api/forecast`

Retorna a previsão mensal para competências futuras baseada nos valores realizados e no
forecast de fechamento mais recente de cada loja.

Parâmetros:

| Parâmetro | Tipo | Regra |
| --- | --- | --- |
| `months` | inteiro | Horizonte futuro entre `1` e `12`; padrão `6` |
| `adjustment_pct` | decimal | Ajuste do cenário entre `-30` e `30`; padrão `0` |

Resposta `200` para `/api/forecast?months=6&adjustment_pct=5`:

```json
{
  "updated_at": "2026-05-26T03:20:00+00:00",
  "data": {
    "latest_competence": "2026-05",
    "months": 6,
    "adjustment_pct": 5,
    "network_projection": [
      {
        "competencia": "2026-06",
        "forecast_base": 14000000.0,
        "forecast_ajustado": 14700000.0,
        "receita_orcada": 4200000.0,
        "variacao_orcamento": 10500000.0,
        "meta_atingida_pct": 350.0,
        "ebitda_estimado": 2900000.0,
        "margem_ebitda_referencia_pct": 19.73
      }
    ],
    "store_projection": []
  }
}
```

O modelo usa a média das últimas variações mensais realizadas de cada loja, limitada
entre `-15%` e `15%`, e aplica o ajuste solicitado sobre a previsão base. Comparações
orçamentárias são retornadas apenas para competências que possuem orçamento provisionado.

### `GET /api/data-quality`

Retorna qualidade, auditoria e rastreabilidade do pipeline a partir das tabelas
`processed_files` e `pipeline_audit_log`.

Parâmetros:

| Parâmetro | Tipo | Regra |
| --- | --- | --- |
| `days` | inteiro | Janela operacional entre `1` e `90`; padrão `14` |

Resposta `200` para `/api/data-quality?days=14`:

```json
{
  "updated_at": "2026-05-28T03:10:00+00:00",
  "data": {
    "days": 14,
    "overview": {
      "total_arquivos": 2205,
      "processados": 2205,
      "reprocessados": 0,
      "registros_lidos": 31123,
      "registros_validos": 31123,
      "total_rejeicoes": 0,
      "taxa_aprovacao": 100.0,
      "taxa_sucesso_execucoes": 100.0,
      "ultima_data_referencia": "2026-05-27"
    },
    "daily_quality": [
      {
        "data_referencia": "2026-05-27",
        "arquivos": 15,
        "lojas": 5,
        "registros_lidos": 225,
        "registros_validos": 225,
        "registros_invalidos": 0,
        "taxa_aprovacao": 100.0
      }
    ],
    "task_quality": [],
    "recent_files": [],
    "recent_runs": [],
    "coverage": [],
    "alerts": ["Nenhuma anomalia operacional detectada no período analisado."]
  }
}
```

### `GET /api/stores/{store_id}`

Retorna o drill-down de uma loja com desempenho, produtos, canais, qualidade, rastreabilidade
e previsões futuras.

Parâmetros:

| Parâmetro | Tipo | Regra |
| --- | --- | --- |
| `store_id` | inteiro | Identificador da loja na rota |
| `forecast_months` | inteiro | Horizonte futuro entre `1` e `12`; padrão `6` |

Resposta `200` para `/api/stores/1?forecast_months=6`:

```json
{
  "updated_at": "2026-05-28T10:20:00+00:00",
  "data": {
    "latest_competence": "2026-05",
    "forecast_months": 6,
    "store": {
      "loja_id": 1,
      "loja_nome": "Loja Centro",
      "cidade": "São Paulo",
      "estado": "SP"
    },
    "overview": {
      "receita_liquida": 3200000.0,
      "ticket_medio": 2700.0,
      "market_share_pct": 25.4,
      "meta_atingida_pct": 380.0,
      "forecast_mes": 3300000.0
    },
    "history": [],
    "products": [],
    "channels": [],
    "quality": [],
    "recent_files": [],
    "forecast_projection": [],
    "ml_prediction": {}
  }
}
```

Resposta `404` quando a loja não existe ou não possui histórico realizado.

### `GET /api/ml-forecast`

Retorna uma previsão estatística mensal baseada no histórico realizado. A API usa uma
regressão linear simples por posição temporal, calcula backtest do último mês disponível
e devolve uma faixa estimada por erro do modelo.

Parâmetros:

| Parâmetro | Tipo | Regra |
| --- | --- | --- |
| `months` | inteiro | Horizonte futuro entre `1` e `12`; padrão `6` |

Resposta `200` para `/api/ml-forecast?months=3`:

```json
{
  "updated_at": "2026-05-27T23:28:24-03:00",
  "data": {
    "latest_competence": "2026-05",
    "months": 3,
    "network": {
      "model": {
        "tipo": "Regressão linear simples",
        "tendencia_mensal_pct": 0.42,
        "rmse": 642847.78,
        "r2": 0.018,
        "observacoes_treino": 5
      },
      "backtest": {
        "competencia": "2026-05",
        "erro_percentual_abs": 8.84
      },
      "projection": [
        {
          "competencia": "2026-06",
          "previsao": 14118156.89,
          "limite_inferior": 12737916.15,
          "limite_superior": 15498397.62
        }
      ]
    },
    "store_models": []
  }
}
```

## Endpoints do PDV

### `GET /api/pdv/config`

Retorna opções utilizadas no formulário operacional.

Resposta `200`:

```json
{
  "lojas": [
    {
      "loja_id": 1,
      "loja_nome": "Loja Centro",
      "cidade": "São Paulo",
      "estado": "SP"
    }
  ],
  "produtos": [
    {
      "produto_id": 501,
      "produto_nome": "Notebook Dell Inspiron 15",
      "categoria": "Informática"
    }
  ],
  "turnos": ["MANHA", "TARDE", "NOITE"]
}
```

### `POST /api/pdv/turnos`

Simula um fechamento de turno e persiste um arquivo JSON real na Raw.

Corpo:

```json
{
  "loja_id": 1,
  "data": "2026-05-25",
  "turno": "MANHA",
  "quantidade": 8,
  "seed": 20260525
}
```

Validações:

| Campo | Regra |
| --- | --- |
| `loja_id` | Inteiro de `1` a `5` |
| `data` | Data ISO `YYYY-MM-DD` |
| `turno` | `MANHA`, `TARDE` ou `NOITE` |
| `quantidade` | Inteiro de `1` a `150` |
| `seed` | Inteiro positivo; opcional |

Resposta `201`:

```json
{
  "status": "RAW_EMITIDO",
  "arquivo": "/opt/airflow/retail/data/raw/vendas/loja=loja_1/ano=2026/mes=05/dia=25/vendas_1_20260525_manha.json",
  "pipeline_id": "9a0ab503-2269-4161-b3b4-6fbca1c2928b",
  "loja_id": 1,
  "loja_nome": "Loja Centro",
  "turno": "MANHA",
  "data": "2026-05-25",
  "quantidade": 8,
  "totais": {
    "valor_bruto": 23646.14,
    "descontos": 1056.42,
    "valor_liquido": 22589.72,
    "concluidas": 7,
    "pendentes": 0,
    "canceladas": 1
  },
  "vendas": []
}
```

Erros:

| Status | Condição |
| --- | --- |
| `409` | Já existe arquivo Raw para a loja/data/turno |
| `422` | Corpo inválido ou fora dos limites |

Importante: a receita mostrada imediatamente no recibo inclui as transações
do arquivo emitido. Os indicadores analíticos do painel consideram as
regras do DW, incluindo filtro de vendas concluídas.

### `POST /api/pdv/fechamentos-gerais`

Emite o fechamento geral de uma data, criando um Raw imutável para cada combinação
das cinco lojas e dos três turnos operacionais, e processa imediatamente a data no DW.

Corpo:

```json
{
  "data": "2026-06-10",
  "quantidade_por_turno": 20,
  "seed": 20260610
}
```

Resposta `201`:

```json
{
  "status": "RAW_DIA_EMITIDO",
  "data": "2026-06-10",
  "lojas": 5,
  "turnos_por_loja": 3,
  "arquivos_raw": 15,
  "quantidade": 300,
  "totais": {
    "valor_liquido": 761244.52,
    "concluidas": 282,
    "pendentes": 11,
    "canceladas": 7
  },
  "emissoes": [],
  "processamento": {
    "status": "PROCESSADO",
    "run_id": "pdv_api_20260610_20260526T032000",
    "arquivos_raw": 15,
    "registros_inseridos": 300,
    "registros_atualizados": 0
  }
}
```

Antes de iniciar a escrita, o endpoint verifica todos os quinze caminhos de destino.
Se qualquer Raw da data já existir, retorna `409` e não inicia o fechamento geral.
Quando a emissão é concluída, a carga é executada automaticamente para atualizar as
telas analíticas.

### `POST /api/pdv/processamentos`

Processa todos os fechamentos Raw disponíveis na data solicitada, usando o
mesmo pipeline aplicado pelo Airflow.

Corpo:

```json
{
  "data": "2026-05-25"
}
```

Resposta `200`:

```json
{
  "status": "PROCESSADO",
  "run_id": "pdv_api_20260525_20260525T094033",
  "data": "2026-05-25",
  "arquivos_raw": 1,
  "registros_extraidos": 8,
  "registros_validos": 8,
  "registros_invalidos": 0,
  "registros_silver": 7,
  "registros_cancelados": 1,
  "registros_inseridos": 8,
  "registros_atualizados": 0
}
```

Erros:

| Status | Condição |
| --- | --- |
| `404` | Não existe arquivo Raw para a data |
| `422` | Data inválida |
| `500` | Pipeline retornou um resumo inconsistente |

## Exemplos de Consumo

### PowerShell

```powershell
$turno = @{
  loja_id = 1
  data = "2026-05-25"
  turno = "MANHA"
  quantidade = 8
  seed = 20260525
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body $turno `
  -Uri "http://localhost:8000/api/pdv/turnos"
```

```powershell
$processamento = @{ data = "2026-05-25" } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body $processamento `
  -Uri "http://localhost:8000/api/pdv/processamentos"
```

### JavaScript

```javascript
const response = await fetch("http://localhost:8000/api/dashboard?competencia=2026-05");
const snapshot = await response.json();
console.log(snapshot.data.overview.receita_liquida);
```

## Idempotência e Auditoria

- `POST /api/pdv/turnos` não sobrescreve Raw emitida.
- `POST /api/pdv/fechamentos-gerais` não inicia emissão se a data possuir Raw anterior e,
  quando bem-sucedido, executa a carga no DW automaticamente.
- O processamento usa `UPSERT` na chave `(id_venda, loja_id)`.
- Cada processamento iniciado pelo PDV recebe um `run_id` com prefixo `pdv_api_`.
- Arquivos são rastreados em `processed_files`.
- Cargas são registradas em `pipeline_audit_log`.
