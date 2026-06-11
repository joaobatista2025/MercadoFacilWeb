UPDATE produtos
SET nome = 'Filé de Tilápia (800 g)',
    descricao = 'Filé de tilápia embalagem de 800 g'
WHERE nome = 'Filé de Peixe (800 g)';

UPDATE produtos
SET nome = 'Sorvete de Chocolate (1,5 L)',
    descricao = 'Sorvete de chocolate pote de 1,5 litro'
WHERE nome = 'Sorvete de Chocolate (1.5 L)';

UPDATE produtos
SET nome = 'Sorvete de Baunilha (1,5 L)',
    descricao = 'Sorvete de baunilha pote de 1,5 litro'
WHERE nome = 'Sorvete de Baunilha (1.5 L)';

UPDATE produtos
SET preco = CASE nome
    WHEN 'Arroz Branco (5 kg)' THEN 32.90
    WHEN 'Feijão Preto (1 kg)' THEN 9.80
    WHEN 'Macarrão Espaguete (500 g)' THEN 4.50
    WHEN 'Açúcar Refinado (1 kg)' THEN 4.80
    WHEN 'Sal Refinado (1 kg)' THEN 2.50
    WHEN 'Óleo de Soja (900 ml)' THEN 7.20
    WHEN 'Azeite de Oliva (500 ml)' THEN 45.00
    WHEN 'Farinha de Trigo (1 kg)' THEN 5.90
    WHEN 'Café em Pó (500 g)' THEN 18.50
    WHEN 'Molho de Tomate (340 g)' THEN 3.20
    WHEN 'Milho em Conserva (200 g)' THEN 3.80
    WHEN 'Ervilha em Conserva (200 g)' THEN 4.00
    WHEN 'Atum Ralado (170 g)' THEN 8.90
    WHEN 'Sardinha em Óleo (125 g)' THEN 5.50
    WHEN 'Biscoito Recheado (140 g)' THEN 3.50
    WHEN 'Biscoito Água e Sal (200 g)' THEN 4.90
    WHEN 'Pão de Forma (400 g)' THEN 8.50
    WHEN 'Fubá Mimoso (500 g)' THEN 3.50
    WHEN 'Leite em Pó (400 g)' THEN 16.90
    WHEN 'Aveia em Flocos (200 g)' THEN 5.50
    WHEN 'Leite Integral (1 L)' THEN 5.80
    WHEN 'Manteiga Com Sal (200 g)' THEN 12.90
    WHEN 'Margarina (500 g)' THEN 8.50
    WHEN 'Queijo Mussarela (1 kg)' THEN 45.00
    WHEN 'Queijo Prato (1 kg)' THEN 48.00
    WHEN 'Presunto Cozido (1 kg)' THEN 35.00
    WHEN 'Peito de Peru (1 kg)' THEN 55.00
    WHEN 'Requeijão Cremoso (200 g)' THEN 8.90
    WHEN 'Iogurte Natural (170 g)' THEN 3.50
    WHEN 'Iogurte de Morango (170 g)' THEN 3.80
    WHEN 'Creme de Leite (200 g)' THEN 3.90
    WHEN 'Leite Condensado (395 g)' THEN 6.50
    WHEN 'Salsicha (1 kg)' THEN 14.00
    WHEN 'Linguiça Calabresa (1 kg)' THEN 25.00
    WHEN 'Massa para Pastel (500 g)' THEN 9.50
    WHEN 'Peito de Frango (1 kg)' THEN 19.90
    WHEN 'Carne Moída (1 kg)' THEN 28.00
    WHEN 'Coxão Mole (1 kg)' THEN 42.00
    WHEN 'Bisteca Suína (1 kg)' THEN 22.00
    WHEN 'Hambúrguer Bovino (400 g)' THEN 18.90
    WHEN 'Lasanha Congelada (600 g)' THEN 15.90
    WHEN 'Pizza Congelada (400 g)' THEN 17.50
    WHEN 'Batata Frita Congelada (1 kg)' THEN 24.90
    WHEN 'Pão de Queijo Congelado (400 g)' THEN 16.00
    WHEN 'Sorvete de Chocolate (1,5 L)' THEN 25.00
    WHEN 'Sorvete de Baunilha (1,5 L)' THEN 25.00
    WHEN 'Nuggets de Frango (300 g)' THEN 12.50
    WHEN 'Filé de Tilápia (800 g)' THEN 35.00
    WHEN 'Ervilhas Congeladas (300 g)' THEN 10.90
    WHEN 'Brócolis Congelado (300 g)' THEN 14.90
    ELSE preco
END;
