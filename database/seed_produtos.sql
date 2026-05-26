INSERT INTO dim_produto (
    produto_id, produto_nome, categoria, subcategoria, marca, preco_base, custo_base, margem_alvo_pct
) VALUES
    (501, 'Notebook Dell Inspiron 15', 'Informática', 'Notebooks', 'Dell', 3500.00, 2100.00, 40.00),
    (502, 'Notebook Lenovo IdeaPad', 'Informática', 'Notebooks', 'Lenovo', 2800.00, 1680.00, 40.00),
    (503, 'Samsung Galaxy A54', 'Celulares', 'Smartphones', 'Samsung', 1800.00, 990.00, 45.00),
    (504, 'iPhone 14', 'Celulares', 'Smartphones', 'Apple', 5500.00, 3300.00, 40.00),
    (505, 'Smart TV LG 55', 'Eletrônicos', 'TVs', 'LG', 2900.00, 1600.00, 44.83),
    (506, 'Fone JBL Bluetooth', 'Eletrônicos', 'Áudio', 'JBL', 350.00, 140.00, 60.00),
    (507, 'Geladeira Brastemp 400L', 'Eletrodomésticos', 'Linha Branca', 'Brastemp', 3200.00, 1920.00, 40.00),
    (508, 'Máquina de Lavar 11kg', 'Eletrodomésticos', 'Linha Branca', 'Electrolux', 1900.00, 1140.00, 40.00),
    (509, 'Cadeira Gamer', 'Móveis', 'Escritório', 'ThunderX', 1200.00, 600.00, 50.00),
    (510, 'Mesa Standing Desk', 'Móveis', 'Escritório', 'ErgoDesk', 1800.00, 900.00, 50.00),
    (511, 'Mouse Logitech MX Master', 'Acessórios', 'Informática', 'Logitech', 450.00, 180.00, 60.00),
    (512, 'Teclado Mecânico', 'Acessórios', 'Informática', 'Redragon', 380.00, 152.00, 60.00),
    (513, 'Toner HP Original', 'Suprimentos', 'Impressão', 'HP', 280.00, 140.00, 50.00),
    (514, 'Resma de Papel A4', 'Suprimentos', 'Escritório', 'Chamex', 45.00, 22.00, 51.11)
ON CONFLICT (produto_id) DO UPDATE SET
    produto_nome = EXCLUDED.produto_nome,
    categoria = EXCLUDED.categoria,
    subcategoria = EXCLUDED.subcategoria,
    preco_base = EXCLUDED.preco_base,
    custo_base = EXCLUDED.custo_base;
