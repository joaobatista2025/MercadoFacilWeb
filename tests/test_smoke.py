import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app, banco  # noqa: E402


class MercadoFacilSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)
        cls.client = app.test_client()
        cls.produto_id = None
        cls.lote_id = None
        cls.cliente_id = None
        cls.venda_id = None

    @classmethod
    def tearDownClass(cls):
        with banco() as (conexao, cursor):
            if cls.venda_id:
                cursor.execute("DELETE FROM itens_venda WHERE id_venda = %s", (cls.venda_id,))
                cursor.execute("DELETE FROM vendas WHERE id_venda = %s", (cls.venda_id,))
            if cls.produto_id:
                cursor.execute("DELETE FROM lotes WHERE id_produto = %s", (cls.produto_id,))
            if cls.produto_id:
                cursor.execute("DELETE FROM produtos WHERE id_produto = %s", (cls.produto_id,))
            if cls.cliente_id:
                cursor.execute("DELETE FROM clientes WHERE id_cliente = %s", (cls.cliente_id,))
            conexao.commit()

    def test_01_paginas_principais(self):
        for rota in ["/", "/produtos", "/lotes", "/clientes", "/vendas", "/vendas/nova", "/caixa"]:
            resposta = self.client.get(rota)
            self.assertEqual(resposta.status_code, 200, rota)

    def test_02_fluxo_completo_de_venda(self):
        resposta = self.client.post(
            "/clientes/novo",
            data={
                "nome": "Cliente Teste Web",
                "telefone": "85999990000",
                "email": "cliente.teste@example.com",
                "endereco": "Teste",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)

        resposta = self.client.post(
            "/produtos/novo",
            data={
                "categoria": "Produtos de Teste",
                "nome": "Produto Teste Web",
                "descricao": "Criado pelo teste automatizado",
                "codigo_barras": "7890009990015",
                "preco": "12.50",
                "estoque_minimo": "2",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)

        with banco() as (conexao, cursor):
            cursor.execute(
                "SELECT id_cliente FROM clientes WHERE nome = 'Cliente Teste Web' ORDER BY id_cliente DESC LIMIT 1"
            )
            self.__class__.cliente_id = cursor.fetchone()["id_cliente"]
            cursor.execute(
                "UPDATE clientes SET saldo_fidelidade = 490.00 WHERE id_cliente = %s",
                (self.cliente_id,),
            )
            conexao.commit()
            cursor.execute(
                """
                SELECT id_produto, codigo, codigo_barras
                FROM produtos
                WHERE nome = 'Produto Teste Web'
                ORDER BY id_produto DESC
                LIMIT 1
                """
            )
            produto_teste = cursor.fetchone()
            self.__class__.produto_id = produto_teste["id_produto"]
            self.assertTrue(produto_teste["codigo"].isdigit())
            self.assertGreaterEqual(len(produto_teste["codigo"]), 3)
            self.assertEqual(produto_teste["codigo_barras"], "7890009990015")

        resposta = self.client.post(
            "/lotes/novo",
            data={
                "id_produto": str(self.produto_id),
                "codigo_lote": "LOTE-TESTE-01",
                "codigo_barras_lote": "7890009990015L1",
                "fornecedor": "Fornecedor A",
                "quantidade": "10",
                "data_entrada": "2026-06-09",
                "data_validade": "2026-12-31",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)

        resposta = self.client.post(
            "/lotes/novo",
            data={
                "id_produto": str(self.produto_id),
                "codigo_lote": "LOTE-TESTE-PROXIMO",
                "codigo_barras_lote": "7890009990015L2",
                "fornecedor": "Fornecedor B",
                "quantidade": "3",
                "data_entrada": "2026-06-09",
                "data_validade": "2026-07-15",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)

        with banco() as (_, cursor):
            cursor.execute(
                """
                SELECT id_lote
                FROM lotes
                WHERE id_produto = %s AND codigo_lote = 'LOTE-TESTE-PROXIMO'
                """,
                (self.produto_id,),
            )
            lote_proximo_id = cursor.fetchone()["id_lote"]

        resposta = self.client.post(
            f"/lotes/{lote_proximo_id}/editar",
            data={
                "id_produto": str(self.produto_id),
                "codigo_lote": "LOTE-TESTE-PROXIMO",
                "codigo_barras_lote": "7890009990015L2",
                "fornecedor": "Fornecedor B",
                "quantidade": "3",
                "data_entrada": "2026-09-01",
                "data_validade": "2026-08-15",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"anterior", resposta.data)

        resposta = self.client.post(
            f"/lotes/{lote_proximo_id}/editar",
            data={
                "id_produto": str(self.produto_id),
                "codigo_lote": "LOTE-TESTE-CORRIGIDO",
                "codigo_barras_lote": "7890009990015L2C",
                "fornecedor": "Fornecedor B Corrigido",
                "quantidade": "3",
                "data_entrada": "2026-06-09",
                "data_validade": "2026-08-15",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"atualizado", resposta.data)

        with banco() as (_, cursor):
            cursor.execute(
                """
                SELECT id_lote
                FROM lotes
                WHERE id_produto = %s AND codigo_lote = 'LOTE-TESTE-01'
                """,
                (self.produto_id,),
            )
            self.__class__.lote_id = cursor.fetchone()["id_lote"]

        resposta = self.client.post(
            "/vendas/nova",
            data={
                "id_cliente": str(self.cliente_id),
                "lote_id[]": str(self.lote_id),
                "quantidade[]": "2",
                "forma_pagamento": "dinheiro",
                "valor_recebido": "30.00",
            },
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"registrada", resposta.data)

        with banco() as (_, cursor):
            cursor.execute(
                "SELECT quantidade_estoque FROM produtos WHERE id_produto = %s",
                (self.produto_id,),
            )
            self.assertEqual(cursor.fetchone()["quantidade_estoque"], 11)
            cursor.execute(
                """
                SELECT codigo_lote, codigo_barras_lote, quantidade
                FROM lotes
                WHERE id_produto = %s
                ORDER BY data_validade
                """,
                (self.produto_id,),
            )
            lotes = cursor.fetchall()
            self.assertEqual(lotes[0]["codigo_lote"], "LOTE-TESTE-CORRIGIDO")
            self.assertEqual(lotes[0]["codigo_barras_lote"], "7890009990015L2C")
            self.assertEqual(lotes[0]["quantidade"], 3)
            self.assertEqual(lotes[1]["quantidade"], 8)
            cursor.execute(
                """
                SELECT
                    id_venda,
                    valor_bruto,
                    desconto_fidelidade,
                    valor_total,
                    forma_pagamento,
                    valor_recebido,
                    troco,
                    status,
                    fidelidade_creditada,
                    saldo_fidelidade_apos
                FROM vendas
                WHERE id_cliente = %s
                ORDER BY id_venda DESC
                LIMIT 1
                """,
                (self.cliente_id,),
            )
            venda = cursor.fetchone()
            self.__class__.venda_id = venda["id_venda"]
            self.assertEqual(float(venda["valor_bruto"]), 25.0)
            self.assertEqual(float(venda["desconto_fidelidade"]), 0.0)
            self.assertEqual(float(venda["valor_total"]), 25.0)
            self.assertEqual(venda["forma_pagamento"], "dinheiro")
            self.assertEqual(float(venda["valor_recebido"]), 30.0)
            self.assertEqual(float(venda["troco"]), 5.0)
            self.assertEqual(venda["status"], "concluida")
            self.assertEqual(float(venda["fidelidade_creditada"]), 25.0)
            self.assertEqual(float(venda["saldo_fidelidade_apos"]), 15.0)
            cursor.execute(
                "SELECT saldo_fidelidade FROM clientes WHERE id_cliente = %s",
                (self.cliente_id,),
            )
            self.assertEqual(float(cursor.fetchone()["saldo_fidelidade"]), 15.0)
            cursor.execute(
                """
                SELECT valor, data_validade, status
                FROM cupons_fidelidade
                WHERE id_venda_origem = %s
                """,
                (self.venda_id,),
            )
            cupom = cursor.fetchone()
            self.assertEqual(float(cupom["valor"]), 15.0)
            self.assertEqual(cupom["status"], "disponivel")

        resposta = self.client.get(f"/vendas/{self.venda_id}/comprovante")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Comprovante", resposta.data)
        self.assertIn(b"Clube MercadoF", resposta.data)
        self.assertIn(b"https://wa.me/5585999990000", resposta.data)
        self.assertIn(b"mailto:cliente.teste%40example.com", resposta.data)

        resposta = self.client.get(f"/vendas/{self.venda_id}/comprovante.pdf")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.mimetype, "application/pdf")
        self.assertTrue(resposta.data.startswith(b"%PDF"))

        resposta = self.client.get("/clientes")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Cliente Teste Web", resposta.data)
        self.assertIn(b"R$ 25,00", resposta.data)
        self.assertIn(b"R$ 15,00", resposta.data)
        self.assertIn(b"R$ 485,00", resposta.data)

        resposta = self.client.post(
            f"/vendas/{self.venda_id}/cancelar",
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"cancelada", resposta.data)

        with banco() as (_, cursor):
            cursor.execute(
                "SELECT quantidade_estoque FROM produtos WHERE id_produto = %s",
                (self.produto_id,),
            )
            self.assertEqual(cursor.fetchone()["quantidade_estoque"], 13)
            cursor.execute(
                "SELECT quantidade FROM lotes WHERE id_lote = %s",
                (self.lote_id,),
            )
            self.assertEqual(cursor.fetchone()["quantidade"], 10)
            cursor.execute(
                "SELECT status FROM vendas WHERE id_venda = %s",
                (self.venda_id,),
            )
            self.assertEqual(cursor.fetchone()["status"], "cancelada")
            cursor.execute(
                "SELECT saldo_fidelidade FROM clientes WHERE id_cliente = %s",
                (self.cliente_id,),
            )
            self.assertEqual(float(cursor.fetchone()["saldo_fidelidade"]), 490.0)
            cursor.execute(
                """
                SELECT status
                FROM cupons_fidelidade
                WHERE id_venda_origem = %s
                """,
                (self.venda_id,),
            )
            self.assertEqual(cursor.fetchone()["status"], "cancelado")

        resposta = self.client.post(
            f"/lotes/{self.lote_id}/excluir",
            follow_redirects=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"n\xc3\xa3o pode ser exclu\xc3\xaddo", resposta.data)


if __name__ == "__main__":
    os.environ.setdefault("MERCADOFACIL_DB_PASSWORD", "123456")
    unittest.main(verbosity=2)
