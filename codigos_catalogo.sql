UPDATE produtos SET codigo = CONCAT('TMP-', id_produto);

UPDATE produtos
SET codigo = CASE nome
    WHEN 'Arroz Branco (5 kg)' THEN '001'
    WHEN 'Feijão Preto (1 kg)' THEN '002'
    WHEN 'Macarrão Espaguete (500 g)' THEN '003'
    WHEN 'Açúcar Refinado (1 kg)' THEN '004'
    WHEN 'Sal Refinado (1 kg)' THEN '005'
    WHEN 'Óleo de Soja (900 ml)' THEN '006'
    WHEN 'Azeite de Oliva (500 ml)' THEN '007'
    WHEN 'Farinha de Trigo (1 kg)' THEN '008'
    WHEN 'Café em Pó (500 g)' THEN '009'
    WHEN 'Molho de Tomate (340 g)' THEN '010'
    WHEN 'Milho em Conserva (200 g)' THEN '011'
    WHEN 'Ervilha em Conserva (200 g)' THEN '012'
    WHEN 'Atum Ralado (170 g)' THEN '013'
    WHEN 'Sardinha em Óleo (125 g)' THEN '014'
    WHEN 'Biscoito Recheado (140 g)' THEN '015'
    WHEN 'Biscoito Água e Sal (200 g)' THEN '016'
    WHEN 'Pão de Forma (400 g)' THEN '017'
    WHEN 'Fubá Mimoso (500 g)' THEN '018'
    WHEN 'Leite em Pó (400 g)' THEN '019'
    WHEN 'Aveia em Flocos (200 g)' THEN '020'
    WHEN 'Leite Integral (1 L)' THEN '021'
    WHEN 'Manteiga Com Sal (200 g)' THEN '022'
    WHEN 'Margarina (500 g)' THEN '023'
    WHEN 'Queijo Mussarela (1 kg)' THEN '024'
    WHEN 'Queijo Prato (1 kg)' THEN '025'
    WHEN 'Presunto Cozido (1 kg)' THEN '026'
    WHEN 'Peito de Peru (1 kg)' THEN '027'
    WHEN 'Requeijão Cremoso (200 g)' THEN '028'
    WHEN 'Iogurte Natural (170 g)' THEN '029'
    WHEN 'Iogurte de Morango (170 g)' THEN '030'
    WHEN 'Creme de Leite (200 g)' THEN '031'
    WHEN 'Leite Condensado (395 g)' THEN '032'
    WHEN 'Salsicha (1 kg)' THEN '033'
    WHEN 'Linguiça Calabresa (1 kg)' THEN '034'
    WHEN 'Massa para Pastel (500 g)' THEN '035'
    WHEN 'Peito de Frango (1 kg)' THEN '036'
    WHEN 'Carne Moída (1 kg)' THEN '037'
    WHEN 'Coxão Mole (1 kg)' THEN '038'
    WHEN 'Bisteca Suína (1 kg)' THEN '039'
    WHEN 'Hambúrguer Bovino (400 g)' THEN '040'
    WHEN 'Lasanha Congelada (600 g)' THEN '041'
    WHEN 'Pizza Congelada (400 g)' THEN '042'
    WHEN 'Batata Frita Congelada (1 kg)' THEN '043'
    WHEN 'Pão de Queijo Congelado (400 g)' THEN '044'
    WHEN 'Sorvete de Chocolate (1,5 L)' THEN '045'
    WHEN 'Sorvete de Baunilha (1,5 L)' THEN '046'
    WHEN 'Nuggets de Frango (300 g)' THEN '047'
    WHEN 'Filé de Tilápia (800 g)' THEN '048'
    WHEN 'Ervilhas Congeladas (300 g)' THEN '049'
    WHEN 'Brócolis Congelado (300 g)' THEN '050'
    ELSE codigo
END;

SET @proximo_codigo := 50;

UPDATE produtos
SET codigo = LPAD((@proximo_codigo := @proximo_codigo + 1), 3, '0')
WHERE codigo LIKE 'TMP-%'
ORDER BY id_produto;
