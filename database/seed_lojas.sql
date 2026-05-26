INSERT INTO dim_loja (
    loja_id, loja_nome, cidade, estado, regiao, data_abertura, tier,
    meta_mensal, area_m2, capacidade_max
) VALUES
    (1, 'Loja Centro', 'São Paulo', 'SP', 'Sudeste', DATE '2018-03-01', 'PREMIUM', 680000.00, 850, 420),
    (2, 'Loja Norte', 'Manaus', 'AM', 'Norte', DATE '2019-07-15', 'STANDARD', 290000.00, 510, 260),
    (3, 'Loja Campinas', 'Campinas', 'SP', 'Sudeste', DATE '2020-01-10', 'STANDARD', 510000.00, 640, 330),
    (4, 'Loja Rio', 'Rio de Janeiro', 'RJ', 'Sudeste', DATE '2017-11-20', 'PREMIUM', 820000.00, 920, 470),
    (5, 'Loja BH', 'Belo Horizonte', 'MG', 'Sudeste', DATE '2021-05-05', 'STANDARD', 390000.00, 570, 285)
ON CONFLICT (loja_id) DO UPDATE SET
    loja_nome = EXCLUDED.loja_nome,
    cidade = EXCLUDED.cidade,
    meta_mensal = EXCLUDED.meta_mensal,
    updated_at = CURRENT_TIMESTAMP;
