BEGIN;

CREATE TABLE IF NOT EXISTS dim_loja (
    loja_sk SERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL UNIQUE,
    loja_nome VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    estado CHAR(2) NOT NULL,
    regiao VARCHAR(50) NOT NULL,
    data_abertura DATE NOT NULL,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    tier VARCHAR(20) NOT NULL,
    meta_mensal NUMERIC(15,2) NOT NULL,
    area_m2 INTEGER NOT NULL,
    capacidade_max INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_produto (
    produto_sk SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL UNIQUE,
    produto_nome VARCHAR(200) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    subcategoria VARCHAR(100) NOT NULL,
    marca VARCHAR(100) NOT NULL,
    preco_base NUMERIC(12,2) NOT NULL,
    custo_base NUMERIC(12,2) NOT NULL,
    margem_alvo_pct NUMERIC(5,2) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_tempo (
    data_sk INTEGER PRIMARY KEY,
    data DATE NOT NULL UNIQUE,
    ano INTEGER NOT NULL,
    semestre INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    nome_mes VARCHAR(20) NOT NULL,
    semana_ano INTEGER NOT NULL,
    dia INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    nome_dia_semana VARCHAR(20) NOT NULL,
    e_fim_semana BOOLEAN NOT NULL,
    e_feriado BOOLEAN NOT NULL DEFAULT FALSE,
    nome_feriado VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_cliente (
    cliente_sk SERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL UNIQUE,
    cliente_nome VARCHAR(200) NOT NULL,
    segmento VARCHAR(50) NOT NULL CHECK (segmento IN ('VAREJO', 'CORPORATIVO', 'VIP')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fato_vendas (
    venda_sk BIGSERIAL PRIMARY KEY,
    id_venda VARCHAR(50) NOT NULL,
    loja_sk INTEGER NOT NULL REFERENCES dim_loja(loja_sk),
    produto_sk INTEGER NOT NULL REFERENCES dim_produto(produto_sk),
    cliente_sk INTEGER NOT NULL REFERENCES dim_cliente(cliente_sk),
    data_sk INTEGER NOT NULL REFERENCES dim_tempo(data_sk),
    loja_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    cliente_id BIGINT NOT NULL,
    data_venda TIMESTAMP NOT NULL,
    canal_venda VARCHAR(50) NOT NULL,
    forma_pagamento VARCHAR(50) NOT NULL,
    parcelas INTEGER NOT NULL DEFAULT 1,
    vendedor_id VARCHAR(50) NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(12,2) NOT NULL CHECK (valor_unitario > 0),
    custo_unitario NUMERIC(12,2) NOT NULL,
    desconto_valor NUMERIC(12,2) NOT NULL DEFAULT 0,
    desconto_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    valor_bruto NUMERIC(12,2) NOT NULL,
    valor_liquido NUMERIC(12,2) NOT NULL,
    custo_total NUMERIC(12,2) NOT NULL,
    margem_bruta NUMERIC(12,2) NOT NULL,
    margem_bruta_pct NUMERIC(7,2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('CONCLUIDA', 'CANCELADA', 'PENDENTE')),
    motivo_cancelamento VARCHAR(200),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    dia INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    periodo VARCHAR(20) NOT NULL CHECK (periodo IN ('MANHA', 'TARDE', 'NOITE', 'MADRUGADA')),
    arquivo_origem VARCHAR(500) NOT NULL,
    pipeline_id UUID NOT NULL,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_venda, loja_id)
);

CREATE TABLE IF NOT EXISTS fato_orcamento (
    orcamento_sk SERIAL PRIMARY KEY,
    loja_sk INTEGER NOT NULL REFERENCES dim_loja(loja_sk),
    loja_id INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    receita_orcada NUMERIC(15,2) NOT NULL,
    margem_bruta_orcada NUMERIC(5,2) NOT NULL,
    despesas_fixas_orcadas NUMERIC(15,2) NOT NULL,
    despesas_var_orcadas NUMERIC(15,2) NOT NULL,
    resultado_orcado NUMERIC(15,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (loja_id, ano, mes)
);

CREATE TABLE IF NOT EXISTS fato_dre (
    dre_sk SERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES dim_loja(loja_id),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    receita_bruta NUMERIC(15,2) NOT NULL,
    descontos NUMERIC(15,2) NOT NULL,
    impostos NUMERIC(15,2) NOT NULL,
    receita_liquida NUMERIC(15,2) NOT NULL,
    cmv NUMERIC(15,2) NOT NULL,
    lucro_bruto NUMERIC(15,2) NOT NULL,
    margem_bruta_pct NUMERIC(7,2) NOT NULL,
    despesas_variaveis NUMERIC(15,2) NOT NULL,
    despesas_fixas NUMERIC(15,2) NOT NULL,
    ebitda NUMERIC(15,2) NOT NULL,
    margem_ebitda_pct NUMERIC(7,2) NOT NULL,
    depreciacao NUMERIC(15,2) NOT NULL,
    ebit NUMERIC(15,2) NOT NULL,
    despesas_financeiras NUMERIC(15,2) NOT NULL,
    resultado_antes_ir NUMERIC(15,2) NOT NULL,
    margem_liquida_pct NUMERIC(7,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (loja_id, ano, mes)
);

CREATE TABLE IF NOT EXISTS processed_files (
    file_id SERIAL PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    checksum VARCHAR(128) NOT NULL,
    data_referencia DATE NOT NULL,
    loja_id INTEGER NOT NULL,
    camada_destino VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('PROCESSED', 'REPROCESSED', 'FAILED', 'QUARANTINED')),
    registros_lidos INTEGER NOT NULL DEFAULT 0,
    registros_validos INTEGER NOT NULL DEFAULT 0,
    registros_invalidos INTEGER NOT NULL DEFAULT 0,
    pipeline_version VARCHAR(50) NOT NULL,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_audit_log (
    audit_id SERIAL PRIMARY KEY,
    dag_id VARCHAR(100) NOT NULL,
    run_id VARCHAR(200) NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    data_referencia DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    registros_lidos INTEGER NOT NULL DEFAULT 0,
    registros_validos INTEGER NOT NULL DEFAULT 0,
    registros_invalidos INTEGER NOT NULL DEFAULT 0,
    registros_inseridos INTEGER NOT NULL DEFAULT 0,
    registros_ignorados INTEGER NOT NULL DEFAULT 0,
    duracao_segundos NUMERIC(10,2) NOT NULL DEFAULT 0,
    mensagem TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processed_files_data_loja ON processed_files(data_referencia, loja_id);
CREATE INDEX IF NOT EXISTS idx_processed_files_checksum ON processed_files(checksum);
CREATE INDEX IF NOT EXISTS idx_fato_vendas_loja_mes ON fato_vendas(loja_id, ano, mes);
CREATE INDEX IF NOT EXISTS idx_fato_vendas_data ON fato_vendas(data_venda);
CREATE INDEX IF NOT EXISTS idx_fato_vendas_status ON fato_vendas(status);
CREATE INDEX IF NOT EXISTS idx_fato_vendas_produto ON fato_vendas(produto_id);
CREATE INDEX IF NOT EXISTS idx_fato_vendas_produto_sk ON fato_vendas(produto_sk);
CREATE INDEX IF NOT EXISTS idx_dim_produto_categoria ON dim_produto(categoria);

COMMIT;
