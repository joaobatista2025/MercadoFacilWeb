CREATE TABLE IF NOT EXISTS clientes (
   id_cliente INT AUTO_INCREMENT PRIMARY KEY,
   nome VARCHAR(100) NOT NULL UNIQUE,
   telefone VARCHAR(20),
   email VARCHAR(150),
   endereco VARCHAR(150),
   data_cadastro DATE NOT NULL,
   saldo_fidelidade DECIMAL(10,2) NOT NULL DEFAULT 0,
   CONSTRAINT chk_clientes_fidelidade CHECK (saldo_fidelidade >= 0)
);

CREATE TABLE IF NOT EXISTS produtos (
   id_produto INT AUTO_INCREMENT PRIMARY KEY,
   codigo VARCHAR(30) NOT NULL UNIQUE,
   categoria VARCHAR(80) NOT NULL,
   nome VARCHAR(100) NOT NULL,
   descricao VARCHAR(200),
   preco DECIMAL(10,2) NOT NULL,
   quantidade_estoque INT NOT NULL,
   estoque_minimo INT NOT NULL,
   data_validade DATE,
   CONSTRAINT chk_produtos_preco CHECK (preco > 0),
   CONSTRAINT chk_produtos_estoque CHECK (quantidade_estoque >= 0),
   CONSTRAINT chk_produtos_minimo CHECK (estoque_minimo >= 0)
);

CREATE TABLE IF NOT EXISTS lotes (
   id_lote INT AUTO_INCREMENT PRIMARY KEY,
   id_produto INT NOT NULL,
   codigo_lote VARCHAR(50) NOT NULL,
   fornecedor VARCHAR(100),
   data_validade DATE,
   quantidade INT NOT NULL,
   data_entrada DATE NOT NULL,
   CONSTRAINT chk_lotes_quantidade CHECK (quantidade >= 0),
   CONSTRAINT uq_lote_produto UNIQUE (id_produto, codigo_lote),
   CONSTRAINT fk_lotes_produtos FOREIGN KEY (id_produto)
      REFERENCES produtos(id_produto) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS vendas (
   id_venda INT AUTO_INCREMENT PRIMARY KEY,
   id_cliente INT,
   data_venda DATETIME NOT NULL,
   valor_bruto DECIMAL(10,2) NOT NULL DEFAULT 0,
   desconto_fidelidade DECIMAL(10,2) NOT NULL DEFAULT 0,
   valor_total DECIMAL(10,2) NOT NULL,
   forma_pagamento VARCHAR(20) NOT NULL DEFAULT 'dinheiro',
   valor_recebido DECIMAL(10,2),
   troco DECIMAL(10,2) NOT NULL DEFAULT 0,
   status VARCHAR(20) NOT NULL DEFAULT 'concluida',
   data_cancelamento DATETIME,
   fidelidade_creditada DECIMAL(10,2) NOT NULL DEFAULT 0,
   saldo_fidelidade_apos DECIMAL(10,2),
   id_cupom_fidelidade INT,
   CONSTRAINT chk_vendas_bruto CHECK (valor_bruto >= 0),
   CONSTRAINT chk_vendas_desconto CHECK (desconto_fidelidade >= 0),
   CONSTRAINT chk_vendas_total CHECK (valor_total >= 0),
   CONSTRAINT chk_vendas_troco CHECK (troco >= 0),
   CONSTRAINT fk_vendas_clientes FOREIGN KEY (id_cliente)
      REFERENCES clientes(id_cliente) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS cupons_fidelidade (
   id_cupom INT AUTO_INCREMENT PRIMARY KEY,
   id_cliente INT NOT NULL,
   valor DECIMAL(10,2) NOT NULL DEFAULT 15,
   data_geracao DATETIME NOT NULL,
   data_validade DATE NOT NULL,
   status VARCHAR(20) NOT NULL DEFAULT 'disponivel',
   id_venda_origem INT,
   id_venda_utilizacao INT,
   CONSTRAINT chk_cupons_valor CHECK (valor > 0),
   CONSTRAINT fk_cupons_cliente FOREIGN KEY (id_cliente)
      REFERENCES clientes(id_cliente) ON DELETE CASCADE,
   CONSTRAINT fk_cupons_venda_origem FOREIGN KEY (id_venda_origem)
      REFERENCES vendas(id_venda) ON DELETE SET NULL,
   CONSTRAINT fk_cupons_venda_utilizacao FOREIGN KEY (id_venda_utilizacao)
      REFERENCES vendas(id_venda) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS itens_venda (
   id_item INT AUTO_INCREMENT PRIMARY KEY,
   id_venda INT NOT NULL,
   id_produto INT NOT NULL,
   id_lote INT,
   quantidade INT NOT NULL,
   preco_unitario DECIMAL(10,2) NOT NULL,
   subtotal DECIMAL(10,2) NOT NULL,
   CONSTRAINT chk_itens_quantidade CHECK (quantidade > 0),
   CONSTRAINT chk_itens_preco CHECK (preco_unitario > 0),
   CONSTRAINT chk_itens_subtotal CHECK (subtotal >= 0),
   CONSTRAINT fk_itens_venda_vendas FOREIGN KEY (id_venda)
      REFERENCES vendas(id_venda) ON DELETE CASCADE,
   CONSTRAINT fk_itens_venda_produtos FOREIGN KEY (id_produto)
      REFERENCES produtos(id_produto),
   CONSTRAINT fk_itens_venda_lotes FOREIGN KEY (id_lote)
      REFERENCES lotes(id_lote)
);
