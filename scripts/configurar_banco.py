import os
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db_config


def executar_script(cursor, caminho):
    conteudo = caminho.read_text(encoding="utf-8")
    for comando in conteudo.split(";"):
        comando = comando.strip()
        if comando:
            cursor.execute(comando)


def main():
    raiz = Path(__file__).resolve().parents[1]
    config = db_config()
    nome_banco = config.pop("database")
    criar_banco = os.getenv(
        "MERCADOFACIL_CREATE_DATABASE",
        "true",
    ).lower() in {"1", "true", "sim", "yes"}

    if criar_banco:
        conexao = mysql.connector.connect(**config)
    else:
        conexao = mysql.connector.connect(database=nome_banco, **config)
    cursor = conexao.cursor()
    if criar_banco:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{nome_banco}` "
            "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{nome_banco}`")
    executar_script(cursor, raiz / "schema_sem_database.sql")
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'clientes'
          AND COLUMN_NAME = 'email'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE clientes ADD COLUMN email VARCHAR(150) NULL AFTER telefone")
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'clientes'
          AND COLUMN_NAME = 'saldo_fidelidade'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "ALTER TABLE clientes ADD COLUMN saldo_fidelidade "
            "DECIMAL(10,2) NOT NULL DEFAULT 0"
        )
    cursor.execute(
        """
        DELETE duplicado
        FROM clientes duplicado
        JOIN clientes original
          ON original.nome = duplicado.nome
         AND original.id_cliente < duplicado.id_cliente
        LEFT JOIN vendas v ON v.id_cliente = duplicado.id_cliente
        LEFT JOIN cupons_fidelidade cf ON cf.id_cliente = duplicado.id_cliente
        WHERE v.id_venda IS NULL
          AND cf.id_cupom IS NULL
        """
    )
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'clientes'
          AND INDEX_NAME = 'uq_clientes_nome'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "ALTER TABLE clientes ADD CONSTRAINT uq_clientes_nome UNIQUE (nome)"
        )
    colunas_vendas = {
        "valor_bruto": "DECIMAL(10,2) NOT NULL DEFAULT 0",
        "desconto_fidelidade": "DECIMAL(10,2) NOT NULL DEFAULT 0",
        "forma_pagamento": "VARCHAR(20) NOT NULL DEFAULT 'dinheiro'",
        "valor_recebido": "DECIMAL(10,2) NULL",
        "troco": "DECIMAL(10,2) NOT NULL DEFAULT 0",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'concluida'",
        "data_cancelamento": "DATETIME NULL",
        "fidelidade_creditada": "DECIMAL(10,2) NOT NULL DEFAULT 0",
        "saldo_fidelidade_apos": "DECIMAL(10,2) NULL",
        "id_cupom_fidelidade": "INT NULL",
    }
    for coluna, definicao in colunas_vendas.items():
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'vendas'
              AND COLUMN_NAME = %s
            """,
            (nome_banco, coluna),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(f"ALTER TABLE vendas ADD COLUMN {coluna} {definicao}")
    cursor.execute(
        "UPDATE vendas SET valor_bruto = valor_total "
        "WHERE valor_bruto = 0 AND valor_total > 0"
    )
    cursor.execute(
        """
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
        )
        """
    )
    cursor.execute(
        """
        SELECT
            v.id_venda,
            v.id_cliente,
            v.valor_total
        FROM vendas v
        WHERE v.id_cliente IS NOT NULL
          AND v.status = 'concluida'
          AND v.fidelidade_creditada = 0
        ORDER BY v.id_cliente, v.data_venda, v.id_venda
        """
    )
    vendas_sem_fidelidade = cursor.fetchall()
    cliente_atual = None
    saldo = None
    for id_venda, id_cliente, valor_total in vendas_sem_fidelidade:
        if id_cliente != cliente_atual:
            if cliente_atual is not None:
                cursor.execute(
                    "UPDATE clientes SET saldo_fidelidade = %s WHERE id_cliente = %s",
                    (saldo, cliente_atual),
                )
            cursor.execute(
                "SELECT saldo_fidelidade FROM clientes WHERE id_cliente = %s",
                (id_cliente,),
            )
            resultado = cursor.fetchone()
            saldo = resultado[0] if resultado else 0
            cliente_atual = id_cliente
        saldo += valor_total
        while saldo >= 500:
            saldo -= 500
            cursor.execute(
                """
                INSERT INTO cupons_fidelidade
                    (id_cliente, valor, data_geracao, data_validade, status,
                     id_venda_origem)
                VALUES (%s, 15, NOW(), DATE_ADD(CURDATE(), INTERVAL 30 DAY),
                        'disponivel', %s)
                """,
                (id_cliente, id_venda),
            )
        cursor.execute(
            """
            UPDATE vendas
            SET fidelidade_creditada = valor_total,
                saldo_fidelidade_apos = %s
            WHERE id_venda = %s
            """,
            (saldo, id_venda),
        )
    if cliente_atual is not None:
        cursor.execute(
            "UPDATE clientes SET saldo_fidelidade = %s WHERE id_cliente = %s",
            (saldo, cliente_atual),
        )
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'produtos'
          AND COLUMN_NAME = 'codigo'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE produtos ADD COLUMN codigo VARCHAR(30) NULL AFTER id_produto")
        cursor.execute(
            """
            UPDATE produtos
            SET codigo = CONCAT('LEG-', LPAD(id_produto, 4, '0'))
            WHERE codigo IS NULL
            """
        )
        cursor.execute("ALTER TABLE produtos MODIFY codigo VARCHAR(30) NOT NULL")
        cursor.execute("ALTER TABLE produtos ADD CONSTRAINT uq_produtos_codigo UNIQUE (codigo)")
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'produtos'
          AND COLUMN_NAME = 'categoria'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            ALTER TABLE produtos
            ADD COLUMN categoria VARCHAR(80) NOT NULL DEFAULT 'Mercearia e Básicos'
            AFTER codigo
            """
        )
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'produtos'
          AND INDEX_NAME = 'uq_produtos_nome'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "ALTER TABLE produtos ADD CONSTRAINT uq_produtos_nome UNIQUE (nome)"
        )
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'produtos'
          AND COLUMN_NAME = 'data_validade'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE produtos ADD COLUMN data_validade DATE NULL")
    cursor.execute(
        """
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
        )
        """
    )
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'lotes'
          AND COLUMN_NAME = 'fornecedor'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE lotes ADD COLUMN fornecedor VARCHAR(100) NULL AFTER codigo_lote")
    cursor.execute(
        """
        UPDATE lotes
        SET codigo_lote = CONCAT(
                'LT-',
                DATE_FORMAT(data_entrada, '%Y'),
                '-',
                LPAD(id_lote, 3, '0')
            ),
            fornecedor = COALESCE(fornecedor, 'Estoque já cadastrado')
        WHERE codigo_lote LIKE 'INICIAL-%'
        """
    )
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'itens_venda'
          AND COLUMN_NAME = 'id_lote'
        """,
        (nome_banco,),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE itens_venda ADD COLUMN id_lote INT NULL AFTER id_produto")
        cursor.execute(
            """
            ALTER TABLE itens_venda
            ADD CONSTRAINT fk_itens_venda_lotes
            FOREIGN KEY (id_lote) REFERENCES lotes(id_lote)
            """
        )
    cursor.execute(
        """
        INSERT INTO lotes
            (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
        SELECT
            p.id_produto,
            CONCAT('LT-', DATE_FORMAT(CURDATE(), '%Y'), '-', LPAD(p.id_produto, 3, '0')),
            'Estoque já cadastrado',
            p.data_validade,
            p.quantidade_estoque,
            CURDATE()
        FROM produtos p
        WHERE p.quantidade_estoque > 0
          AND NOT EXISTS (
              SELECT 1 FROM lotes l WHERE l.id_produto = p.id_produto
          )
        """
    )
    executar_script(cursor, raiz / "dados_iniciais.sql")
    executar_script(cursor, raiz / "catalogo_precos.sql")
    cursor.execute(
        "SELECT codigo FROM produtos WHERE nome = 'Arroz Branco (5 kg)' LIMIT 1"
    )
    arroz = cursor.fetchone()
    if arroz and arroz[0] != "001":
        executar_script(cursor, raiz / "codigos_catalogo.sql")
    cursor.execute(
        """
        UPDATE lotes l
        JOIN produtos p ON p.id_produto = l.id_produto
        SET l.codigo_lote = CONCAT(p.codigo, RIGHT(l.codigo_lote, 3))
        WHERE l.codigo_lote REGEXP '^PRD-[0-9]+-L[12]$'
        """
    )
    cursor.execute(
        """
        INSERT IGNORE INTO lotes
            (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
        SELECT
            p.id_produto,
            CONCAT(p.codigo, '-L1'),
            CASE
                WHEN p.categoria = 'Mercearia e Básicos' THEN 'Distribuidora Fortaleza'
                WHEN p.categoria = 'Laticínios e Frios' THEN 'Laticínios do Ceará'
                ELSE 'Fornecedor Nordeste'
            END,
            DATE_ADD(CURDATE(), INTERVAL (45 + MOD(p.id_produto, 60)) DAY),
            20 + MOD(p.id_produto, 11),
            CURDATE()
        FROM produtos p
        WHERE NOT EXISTS (
            SELECT 1 FROM lotes l WHERE l.id_produto = p.id_produto
        )
        """
    )
    cursor.execute(
        """
        INSERT IGNORE INTO lotes
            (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
        SELECT
            p.id_produto,
            CONCAT(p.codigo, '-L2'),
            CASE
                WHEN p.categoria = 'Mercearia e Básicos' THEN 'Atacado Ceará'
                WHEN p.categoria = 'Laticínios e Frios' THEN 'Fornecedor Nordeste'
                ELSE 'Distribuidora Regional'
            END,
            DATE_ADD(CURDATE(), INTERVAL (150 + MOD(p.id_produto, 90)) DAY),
            15 + MOD(p.id_produto, 9),
            CURDATE()
        FROM produtos p
        WHERE (
            SELECT COUNT(*)
            FROM lotes l
            WHERE l.id_produto = p.id_produto
        ) < 2
        """
    )
    cursor.execute(
        """
        INSERT INTO lotes
            (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
        SELECT
            p.id_produto,
            CONCAT('LT-', DATE_FORMAT(CURDATE(), '%Y'), '-', LPAD(p.id_produto, 3, '0')),
            'Estoque já cadastrado',
            p.data_validade,
            p.quantidade_estoque,
            CURDATE()
        FROM produtos p
        WHERE p.quantidade_estoque > 0
          AND NOT EXISTS (
              SELECT 1 FROM lotes l WHERE l.id_produto = p.id_produto
          )
        """
    )
    cursor.execute(
        """
        UPDATE produtos p
        SET quantidade_estoque = (
            SELECT COALESCE(SUM(l.quantidade), 0)
            FROM lotes l
            WHERE l.id_produto = p.id_produto
        )
        """
    )
    conexao.commit()
    cursor.close()
    conexao.close()
    print("Banco MercadoFacil configurado com sucesso.")


if __name__ == "__main__":
    main()
