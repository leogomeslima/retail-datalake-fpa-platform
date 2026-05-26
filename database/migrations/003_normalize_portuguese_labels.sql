BEGIN;

UPDATE dim_loja
SET cidade = 'São Paulo',
    updated_at = CURRENT_TIMESTAMP
WHERE cidade = 'Sao Paulo';

UPDATE dim_produto
SET categoria = CASE categoria
        WHEN 'Informatica' THEN 'Informática'
        WHEN 'Eletronicos' THEN 'Eletrônicos'
        WHEN 'Eletrodomesticos' THEN 'Eletrodomésticos'
        WHEN 'Moveis' THEN 'Móveis'
        WHEN 'Acessorios' THEN 'Acessórios'
        ELSE categoria
    END,
    subcategoria = CASE subcategoria
        WHEN 'Audio' THEN 'Áudio'
        WHEN 'Escritorio' THEN 'Escritório'
        WHEN 'Impressao' THEN 'Impressão'
        WHEN 'Informatica' THEN 'Informática'
        ELSE subcategoria
    END,
    produto_nome = CASE produto_nome
        WHEN 'Maquina de Lavar 11kg' THEN 'Máquina de Lavar 11kg'
        WHEN 'Teclado Mecanico' THEN 'Teclado Mecânico'
        ELSE produto_nome
    END
WHERE categoria IN ('Informatica', 'Eletronicos', 'Eletrodomesticos', 'Moveis', 'Acessorios')
   OR subcategoria IN ('Audio', 'Escritorio', 'Impressao', 'Informatica')
   OR produto_nome IN ('Maquina de Lavar 11kg', 'Teclado Mecanico');

UPDATE fato_vendas
SET canal_venda = 'Loja Física'
WHERE canal_venda = 'Loja Fisica';

COMMIT;
