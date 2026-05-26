INSERT INTO dim_tempo (
    data_sk, data, ano, semestre, trimestre, mes, nome_mes, semana_ano,
    dia, dia_semana, nome_dia_semana, e_fim_semana
)
SELECT
    TO_CHAR(dia, 'YYYYMMDD')::INTEGER,
    dia::DATE,
    EXTRACT(YEAR FROM dia)::INTEGER,
    CASE WHEN EXTRACT(MONTH FROM dia) <= 6 THEN 1 ELSE 2 END,
    EXTRACT(QUARTER FROM dia)::INTEGER,
    EXTRACT(MONTH FROM dia)::INTEGER,
    TO_CHAR(dia, 'TMMonth'),
    EXTRACT(WEEK FROM dia)::INTEGER,
    EXTRACT(DAY FROM dia)::INTEGER,
    EXTRACT(ISODOW FROM dia)::INTEGER,
    TO_CHAR(dia, 'TMDay'),
    EXTRACT(ISODOW FROM dia) IN (6, 7)
FROM GENERATE_SERIES(DATE '2025-01-01', DATE '2027-12-31', INTERVAL '1 day') AS calendario(dia)
ON CONFLICT (data_sk) DO NOTHING;

