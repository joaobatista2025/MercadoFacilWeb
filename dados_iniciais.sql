INSERT INTO clientes (nome, telefone, email, endereco, data_cadastro)
SELECT 'Consumidor Final', NULL, NULL, NULL, CURDATE()
WHERE NOT EXISTS (SELECT 1 FROM clientes WHERE nome = 'Consumidor Final');

INSERT IGNORE INTO clientes (nome, telefone, email, endereco, data_cadastro)
VALUES
('Ana Souza', '(85) 90000-0001', 'ana.souza@example.com', 'Rua Exemplo, 101 - Centro, Fortaleza/CE', CURDATE()),
('Bruno Lima', '(85) 90000-0002', 'bruno.lima@example.com', 'Rua Exemplo, 202 - Aldeota, Fortaleza/CE', CURDATE()),
('Carla Mendes', '(85) 90000-0003', 'carla.mendes@example.com', 'Rua Exemplo, 303 - Benfica, Fortaleza/CE', CURDATE()),
('Daniel Rocha', '(85) 90000-0004', 'daniel.rocha@example.com', 'Rua Exemplo, 404 - Messejana, Fortaleza/CE', CURDATE()),
('Eduarda Alves', '(85) 90000-0005', 'eduarda.alves@example.com', 'Rua Exemplo, 505 - Parangaba, Fortaleza/CE', CURDATE()),
('Felipe Martins', '(85) 90000-0006', 'felipe.martins@example.com', 'Rua Exemplo, 606 - Papicu, Fortaleza/CE', CURDATE()),
('Gabriela Costa', '(85) 90000-0007', 'gabriela.costa@example.com', 'Rua Exemplo, 707 - Montese, Fortaleza/CE', CURDATE()),
('Henrique Nunes', '(85) 90000-0008', 'henrique.nunes@example.com', 'Rua Exemplo, 808 - Cocó, Fortaleza/CE', CURDATE()),
('Isabela Freitas', '(85) 90000-0009', 'isabela.freitas@example.com', 'Rua Exemplo, 909 - Fátima, Fortaleza/CE', CURDATE()),
('Lucas Ribeiro', '(85) 90000-0010', 'lucas.ribeiro@example.com', 'Rua Exemplo, 1010 - Maraponga, Fortaleza/CE', CURDATE());

INSERT IGNORE INTO produtos
    (codigo, categoria, nome, descricao, preco, quantidade_estoque, estoque_minimo, data_validade)
VALUES
('MER-001', 'Mercearia e Básicos', 'Arroz Branco (5 kg)', 'Arroz branco pacote de 5 kg', 29.90, 0, 5, NULL),
('MER-002', 'Mercearia e Básicos', 'Feijão Preto (1 kg)', 'Feijão preto pacote de 1 kg', 8.99, 0, 5, NULL),
('MER-003', 'Mercearia e Básicos', 'Macarrão Espaguete (500 g)', 'Macarrão espaguete pacote de 500 g', 4.49, 0, 5, NULL),
('MER-004', 'Mercearia e Básicos', 'Açúcar Refinado (1 kg)', 'Açúcar refinado pacote de 1 kg', 5.29, 0, 5, NULL),
('MER-005', 'Mercearia e Básicos', 'Sal Refinado (1 kg)', 'Sal refinado pacote de 1 kg', 2.99, 0, 5, NULL),
('MER-006', 'Mercearia e Básicos', 'Óleo de Soja (900 ml)', 'Óleo de soja embalagem de 900 ml', 8.49, 0, 5, NULL),
('MER-007', 'Mercearia e Básicos', 'Azeite de Oliva (500 ml)', 'Azeite de oliva embalagem de 500 ml', 32.90, 0, 3, NULL),
('MER-008', 'Mercearia e Básicos', 'Farinha de Trigo (1 kg)', 'Farinha de trigo pacote de 1 kg', 6.49, 0, 5, NULL),
('MER-009', 'Mercearia e Básicos', 'Café em Pó (500 g)', 'Café em pó pacote de 500 g', 22.90, 0, 5, NULL),
('MER-010', 'Mercearia e Básicos', 'Molho de Tomate (340 g)', 'Molho de tomate embalagem de 340 g', 3.49, 0, 5, NULL),
('MER-011', 'Mercearia e Básicos', 'Milho em Conserva (200 g)', 'Milho em conserva lata de 200 g', 4.99, 0, 5, NULL),
('MER-012', 'Mercearia e Básicos', 'Ervilha em Conserva (200 g)', 'Ervilha em conserva lata de 200 g', 4.79, 0, 5, NULL),
('MER-013', 'Mercearia e Básicos', 'Atum Ralado (170 g)', 'Atum ralado lata de 170 g', 9.99, 0, 4, NULL),
('MER-014', 'Mercearia e Básicos', 'Sardinha em Óleo (125 g)', 'Sardinha em óleo lata de 125 g', 6.49, 0, 4, NULL),
('MER-015', 'Mercearia e Básicos', 'Biscoito Recheado (140 g)', 'Biscoito recheado pacote de 140 g', 3.29, 0, 5, NULL),
('MER-016', 'Mercearia e Básicos', 'Biscoito Água e Sal (200 g)', 'Biscoito água e sal pacote de 200 g', 4.99, 0, 5, NULL),
('MER-017', 'Mercearia e Básicos', 'Pão de Forma (400 g)', 'Pão de forma pacote de 400 g', 8.99, 0, 4, NULL),
('MER-018', 'Mercearia e Básicos', 'Fubá Mimoso (500 g)', 'Fubá mimoso pacote de 500 g', 3.99, 0, 5, NULL),
('MER-019', 'Mercearia e Básicos', 'Leite em Pó (400 g)', 'Leite em pó pacote de 400 g', 17.90, 0, 4, NULL),
('MER-020', 'Mercearia e Básicos', 'Aveia em Flocos (200 g)', 'Aveia em flocos pacote de 200 g', 5.99, 0, 4, NULL),

('LAF-001', 'Laticínios e Frios', 'Leite Integral (1 L)', 'Leite integral embalagem de 1 litro', 6.29, 0, 8, NULL),
('LAF-002', 'Laticínios e Frios', 'Manteiga Com Sal (200 g)', 'Manteiga com sal embalagem de 200 g', 13.90, 0, 4, NULL),
('LAF-003', 'Laticínios e Frios', 'Margarina (500 g)', 'Margarina embalagem de 500 g', 8.49, 0, 4, NULL),
('LAF-004', 'Laticínios e Frios', 'Queijo Mussarela (1 kg)', 'Queijo mussarela vendido por quilo', 42.90, 0, 3, NULL),
('LAF-005', 'Laticínios e Frios', 'Queijo Prato (1 kg)', 'Queijo prato vendido por quilo', 44.90, 0, 3, NULL),
('LAF-006', 'Laticínios e Frios', 'Presunto Cozido (1 kg)', 'Presunto cozido vendido por quilo', 29.90, 0, 3, NULL),
('LAF-007', 'Laticínios e Frios', 'Peito de Peru (1 kg)', 'Peito de peru vendido por quilo', 49.90, 0, 3, NULL),
('LAF-008', 'Laticínios e Frios', 'Requeijão Cremoso (200 g)', 'Requeijão cremoso embalagem de 200 g', 9.49, 0, 4, NULL),
('LAF-009', 'Laticínios e Frios', 'Iogurte Natural (170 g)', 'Iogurte natural embalagem de 170 g', 3.49, 0, 6, NULL),
('LAF-010', 'Laticínios e Frios', 'Iogurte de Morango (170 g)', 'Iogurte de morango embalagem de 170 g', 3.69, 0, 6, NULL),
('LAF-011', 'Laticínios e Frios', 'Creme de Leite (200 g)', 'Creme de leite embalagem de 200 g', 4.49, 0, 5, NULL),
('LAF-012', 'Laticínios e Frios', 'Leite Condensado (395 g)', 'Leite condensado embalagem de 395 g', 7.99, 0, 5, NULL),
('LAF-013', 'Laticínios e Frios', 'Salsicha (1 kg)', 'Salsicha embalagem de 1 kg', 14.90, 0, 4, NULL),
('LAF-014', 'Laticínios e Frios', 'Linguiça Calabresa (1 kg)', 'Linguiça calabresa embalagem de 1 kg', 25.90, 0, 4, NULL),
('LAF-015', 'Laticínios e Frios', 'Massa para Pastel (500 g)', 'Massa para pastel embalagem de 500 g', 8.99, 0, 4, NULL),

('CON-001', 'Carnes e Congelados', 'Peito de Frango (1 kg)', 'Peito de frango embalagem de 1 kg', 19.90, 0, 4, NULL),
('CON-002', 'Carnes e Congelados', 'Carne Moída (1 kg)', 'Carne bovina moída embalagem de 1 kg', 34.90, 0, 4, NULL),
('CON-003', 'Carnes e Congelados', 'Coxão Mole (1 kg)', 'Coxão mole vendido por quilo', 42.90, 0, 3, NULL),
('CON-004', 'Carnes e Congelados', 'Bisteca Suína (1 kg)', 'Bisteca suína embalagem de 1 kg', 24.90, 0, 3, NULL),
('CON-005', 'Carnes e Congelados', 'Hambúrguer Bovino (400 g)', 'Hambúrguer bovino embalagem de 400 g', 13.90, 0, 4, NULL),
('CON-006', 'Carnes e Congelados', 'Lasanha Congelada (600 g)', 'Lasanha congelada embalagem de 600 g', 16.90, 0, 4, NULL),
('CON-007', 'Carnes e Congelados', 'Pizza Congelada (400 g)', 'Pizza congelada embalagem de 400 g', 18.90, 0, 4, NULL),
('CON-008', 'Carnes e Congelados', 'Batata Frita Congelada (1 kg)', 'Batata frita congelada embalagem de 1 kg', 17.90, 0, 4, NULL),
('CON-009', 'Carnes e Congelados', 'Pão de Queijo Congelado (400 g)', 'Pão de queijo congelado embalagem de 400 g', 14.90, 0, 4, NULL),
('CON-010', 'Carnes e Congelados', 'Sorvete de Chocolate (1,5 L)', 'Sorvete de chocolate pote de 1,5 litro', 24.90, 0, 3, NULL),
('CON-011', 'Carnes e Congelados', 'Sorvete de Baunilha (1,5 L)', 'Sorvete de baunilha pote de 1,5 litro', 24.90, 0, 3, NULL),
('CON-012', 'Carnes e Congelados', 'Nuggets de Frango (300 g)', 'Nuggets de frango embalagem de 300 g', 12.90, 0, 4, NULL),
('CON-013', 'Carnes e Congelados', 'Filé de Tilápia (800 g)', 'Filé de tilápia embalagem de 800 g', 29.90, 0, 3, NULL),
('CON-014', 'Carnes e Congelados', 'Ervilhas Congeladas (300 g)', 'Ervilhas congeladas embalagem de 300 g', 8.99, 0, 4, NULL),
('CON-015', 'Carnes e Congelados', 'Brócolis Congelado (300 g)', 'Brócolis congelado embalagem de 300 g', 9.99, 0, 4, NULL);

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'ARZ5-260601', 'Distribuidora Fortaleza',
       DATE_ADD(CURDATE(), INTERVAL 150 DAY), 24, CURDATE()
FROM produtos WHERE codigo = 'MER-001';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'ARZ5-260602', 'Atacado Ceará',
       DATE_ADD(CURDATE(), INTERVAL 240 DAY), 18, CURDATE()
FROM produtos WHERE codigo = 'MER-001';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'FJP1-260615', 'Distribuidora Fortaleza',
       DATE_ADD(CURDATE(), INTERVAL 120 DAY), 20, CURDATE()
FROM produtos WHERE codigo = 'MER-002';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'MAC5-260520', 'Atacado Ceará',
       DATE_ADD(CURDATE(), INTERVAL 180 DAY), 30, CURDATE()
FROM produtos WHERE codigo = 'MER-003';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'CAF5-260610', 'Café Regional',
       DATE_ADD(CURDATE(), INTERVAL 90 DAY), 16, CURDATE()
FROM produtos WHERE codigo = 'MER-009';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'LEI1-260610', 'Laticínios do Ceará',
       DATE_ADD(CURDATE(), INTERVAL 12 DAY), 28, CURDATE()
FROM produtos WHERE codigo = 'LAF-001';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'LEI1-260611', 'Fornecedor Nordeste',
       DATE_ADD(CURDATE(), INTERVAL 28 DAY), 24, CURDATE()
FROM produtos WHERE codigo = 'LAF-001';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'IOG-MOR-2606', 'Laticínios do Ceará',
       DATE_ADD(CURDATE(), INTERVAL 18 DAY), 18, CURDATE()
FROM produtos WHERE codigo = 'LAF-010';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'FRG1-260610', 'Frigorífico Regional',
       DATE_ADD(CURDATE(), INTERVAL 45 DAY), 15, CURDATE()
FROM produtos WHERE codigo = 'CON-001';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'PIZ4-260601', 'Congelados Nordeste',
       DATE_ADD(CURDATE(), INTERVAL 100 DAY), 12, CURDATE()
FROM produtos WHERE codigo = 'CON-007';

INSERT IGNORE INTO lotes
    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
SELECT id_produto, 'SOR-CHOC-2605', 'Distribuidora Gelada',
       DATE_ADD(CURDATE(), INTERVAL 180 DAY), 10, CURDATE()
FROM produtos WHERE codigo = 'CON-010';
