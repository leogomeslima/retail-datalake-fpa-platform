BEGIN;

ALTER TABLE dim_cliente
    ALTER COLUMN cliente_id TYPE BIGINT;

ALTER TABLE fato_vendas
    ALTER COLUMN cliente_id TYPE BIGINT;

COMMIT;
