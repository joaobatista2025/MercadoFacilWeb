import os
import re
from hmac import compare_digest
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import quote

import mysql.connector
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from mysql.connector import Error
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Paragraph,
)


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mercadofacil-demonstracao-local")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv(
        "MERCADOFACIL_SECURE_COOKIES",
        "",
    ).lower()
    in {"1", "true", "sim", "yes"},
)

FORMAS_PAGAMENTO = {
    "dinheiro": "Dinheiro",
    "pix": "PIX",
    "cartao": "Cartao",
}
META_FIDELIDADE = Decimal("500.00")
VALOR_CUPOM = Decimal("15.00")
COMPRA_MINIMA_CUPOM = Decimal("150.00")


def db_config():
    config = {
        "host": os.getenv("MERCADOFACIL_DB_HOST") or os.getenv("MYSQLHOST", "localhost"),
        "user": os.getenv("MERCADOFACIL_DB_USER") or os.getenv("MYSQLUSER", "root"),
        "password": os.getenv("MERCADOFACIL_DB_PASSWORD") or os.getenv("MYSQLPASSWORD", "123456"),
        "database": os.getenv("MERCADOFACIL_DB_NAME") or os.getenv("MYSQLDATABASE", "mercadofacil"),
        "port": int(os.getenv("MERCADOFACIL_DB_PORT") or os.getenv("MYSQLPORT", "3306")),
        "connection_timeout": 15,
    }
    if os.getenv("MERCADOFACIL_DB_SSL", "").lower() in {"1", "true", "sim", "yes"}:
        config.update(
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )
    return config


@contextmanager
def banco(dictionary=True):
    conexao = mysql.connector.connect(**db_config())
    cursor = conexao.cursor(dictionary=dictionary)
    try:
        yield conexao, cursor
    finally:
        cursor.close()
        conexao.close()


def credenciais_acesso():
    return (
        os.getenv("MERCADOFACIL_ADMIN_USER", "mercadofacil"),
        os.getenv("MERCADOFACIL_ADMIN_PASSWORD", "Mercado@2026"),
    )


@app.before_request
def exigir_login():
    if app.config.get("TESTING"):
        return None
    if request.endpoint in {"login", "health", "static"}:
        return None
    if session.get("autenticado"):
        return None
    destino = request.full_path if request.method == "GET" else None
    return redirect(url_for("login", next=destino))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("autenticado"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        usuario_esperado, senha_esperada = credenciais_acesso()
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if compare_digest(usuario, usuario_esperado) and compare_digest(
            senha,
            senha_esperada,
        ):
            session.clear()
            session["autenticado"] = True
            destino = request.form.get("next", "")
            if destino.startswith("/") and not destino.startswith("//"):
                return redirect(destino)
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha incorretos.", "erro")
    return render_template("login.html", next=request.args.get("next", ""))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/health")
def health():
    return {"status": "ok"}


def decimal_positivo(valor, campo):
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except InvalidOperation as erro:
        raise ValueError(f"{campo} deve ser um número válido.") from erro
    if numero <= 0:
        raise ValueError(f"{campo} deve ser maior que zero.")
    return numero


def inteiro_nao_negativo(valor, campo):
    try:
        numero = int(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{campo} deve ser um número inteiro.") from erro
    if numero < 0:
        raise ValueError(f"{campo} não pode ser negativo.")
    return numero


def data_iso(valor, campo, obrigatoria=False):
    if not valor:
        if obrigatoria:
            raise ValueError(f"{campo} é obrigatória.")
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError as erro:
        raise ValueError(f"{campo} deve ser uma data válida.") from erro


def validar_datas_lote(data_entrada, data_validade):
    if data_validade and data_validade < data_entrada:
        raise ValueError("A validade não pode ser anterior à data de entrada.")


def sincronizar_estoque(cursor, id_produto):
    cursor.execute(
        """
        UPDATE produtos p
        SET quantidade_estoque = (
            SELECT COALESCE(SUM(l.quantidade), 0)
            FROM lotes l
            WHERE l.id_produto = p.id_produto
        )
        WHERE p.id_produto = %s
        """,
        (id_produto,),
    )


@app.template_filter("brl")
def moeda_brasileira(valor):
    numero = Decimal(valor or 0)
    texto = f"{numero:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_cupons_por_saldo(cursor, id_cliente, saldo, id_venda_origem=None):
    gerados = 0
    while saldo >= META_FIDELIDADE:
        saldo -= META_FIDELIDADE
        cursor.execute(
            """
            INSERT INTO cupons_fidelidade
                (id_cliente, valor, data_geracao, data_validade, status, id_venda_origem)
            VALUES (%s, %s, NOW(), DATE_ADD(CURDATE(), INTERVAL 30 DAY),
                    'disponivel', %s)
            """,
            (id_cliente, VALOR_CUPOM, id_venda_origem),
        )
        gerados += 1
    return saldo, gerados


def dados_comprovante(id_venda):
    with banco() as (_, cursor):
        cursor.execute(
            """
            SELECT
                v.*,
                COALESCE(c.nome, 'Consumidor final') AS cliente,
                c.telefone AS cliente_telefone,
                c.email AS cliente_email,
                c.saldo_fidelidade AS saldo_fidelidade_atual
            FROM vendas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            WHERE v.id_venda = %s
            """,
            (id_venda,),
        )
        venda = cursor.fetchone()
        if not venda:
            return None, [], [], {"total": 0, "proxima_validade": None}
        cursor.execute(
            """
            SELECT
                p.codigo,
                p.nome,
                l.codigo_lote,
                iv.quantidade,
                iv.preco_unitario,
                iv.subtotal
            FROM itens_venda iv
            JOIN produtos p ON p.id_produto = iv.id_produto
            LEFT JOIN lotes l ON l.id_lote = iv.id_lote
            WHERE iv.id_venda = %s
            ORDER BY iv.id_item
            """,
            (id_venda,),
        )
        itens = cursor.fetchall()
        cursor.execute(
            """
            SELECT id_cupom, valor, data_validade, status
            FROM cupons_fidelidade
            WHERE id_venda_origem = %s
            ORDER BY id_cupom
            """,
            (id_venda,),
        )
        cupons_gerados = cursor.fetchall()
        if venda["id_cliente"]:
            cursor.execute(
                """
                SELECT COUNT(*) AS total, MIN(data_validade) AS proxima_validade
                FROM cupons_fidelidade
                WHERE id_cliente = %s
                  AND status = 'disponivel'
                  AND data_validade >= CURDATE()
                """,
                (venda["id_cliente"],),
            )
            cupons_disponiveis = cursor.fetchone()
        else:
            cupons_disponiveis = {"total": 0, "proxima_validade": None}
    return venda, itens, cupons_gerados, cupons_disponiveis


@app.route("/")
def dashboard():
    with banco() as (_, cursor):
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_vendas,
                COALESCE(SUM(valor_total), 0) AS faturamento
            FROM vendas
            WHERE DATE(data_venda) = CURDATE()
              AND status = 'concluida'
            """
        )
        resumo = cursor.fetchone()
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM produtos
            WHERE quantidade_estoque <= estoque_minimo
            """
        )
        baixo_estoque = cursor.fetchone()["total"]
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lotes
            WHERE quantidade > 0
              AND data_validade IS NOT NULL
              AND data_validade <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            """
        )
        validade_alertas = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM produtos")
        total_produtos = cursor.fetchone()["total"]
        cursor.execute(
            """
            SELECT
                v.id_venda,
                v.data_venda,
                v.valor_total,
                COALESCE(c.nome, 'Consumidor final') AS cliente
            FROM vendas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            WHERE v.status = 'concluida'
            ORDER BY v.data_venda DESC
            LIMIT 6
            """
        )
        vendas_recentes = cursor.fetchall()
        cursor.execute(
            """
            SELECT id_produto, nome, quantidade_estoque, estoque_minimo
            FROM produtos
            WHERE quantidade_estoque <= estoque_minimo
            ORDER BY quantidade_estoque, nome
            LIMIT 6
            """
        )
        alertas = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                l.id_lote,
                l.codigo_lote,
                l.quantidade,
                p.id_produto,
                p.nome,
                l.data_validade,
                DATEDIFF(l.data_validade, CURDATE()) AS dias_restantes
            FROM lotes l
            JOIN produtos p ON p.id_produto = l.id_produto
            WHERE l.quantidade > 0
              AND l.data_validade IS NOT NULL
              AND l.data_validade <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            ORDER BY l.data_validade, p.nome
            LIMIT 6
            """
        )
        alertas_validade = cursor.fetchall()

    return render_template(
        "dashboard.html",
        resumo=resumo,
        baixo_estoque=baixo_estoque,
        total_produtos=total_produtos,
        vendas_recentes=vendas_recentes,
        alertas=alertas,
        validade_alertas=validade_alertas,
        alertas_validade=alertas_validade,
    )


@app.route("/produtos")
def produtos():
    busca = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    situacao = request.args.get("situacao", "").strip()
    condicoes = []
    parametros = []
    if busca:
        condicoes.append("(p.nome LIKE %s OR p.codigo LIKE %s)")
        parametros.extend((f"%{busca}%", f"%{busca}%"))
    if categoria:
        condicoes.append("p.categoria = %s")
        parametros.append(categoria)
    if situacao == "estoque_baixo":
        condicoes.append("p.quantidade_estoque <= p.estoque_minimo")
    elif situacao == "vencendo":
        condicoes.append(
            "EXISTS (SELECT 1 FROM lotes lf WHERE lf.id_produto = p.id_produto "
            "AND lf.quantidade > 0 AND lf.data_validade BETWEEN CURDATE() "
            "AND DATE_ADD(CURDATE(), INTERVAL 30 DAY))"
        )
    elif situacao == "vencido":
        condicoes.append(
            "EXISTS (SELECT 1 FROM lotes lf WHERE lf.id_produto = p.id_produto "
            "AND lf.quantidade > 0 AND lf.data_validade < CURDATE())"
        )

    consulta = """
        SELECT
            p.*,
            (
                SELECT MIN(l.data_validade)
                FROM lotes l
                WHERE l.id_produto = p.id_produto
                  AND l.quantidade > 0
                  AND l.data_validade IS NOT NULL
            ) AS proxima_validade,
            DATEDIFF(
                (
                    SELECT MIN(l2.data_validade)
                    FROM lotes l2
                    WHERE l2.id_produto = p.id_produto
                      AND l2.quantidade > 0
                      AND l2.data_validade IS NOT NULL
                ),
                CURDATE()
            ) AS dias_validade,
            (
                SELECT COUNT(*)
                FROM lotes l3
                WHERE l3.id_produto = p.id_produto AND l3.quantidade > 0
            ) AS total_lotes
        FROM produtos p
    """
    if condicoes:
        consulta += " WHERE " + " AND ".join(condicoes)
    consulta += " ORDER BY p.categoria, p.nome"

    with banco() as (_, cursor):
        cursor.execute(consulta, tuple(parametros))
        lista = cursor.fetchall()
        cursor.execute("SELECT DISTINCT categoria FROM produtos ORDER BY categoria")
        categorias = [linha["categoria"] for linha in cursor.fetchall()]
    return render_template(
        "produtos.html",
        produtos=lista,
        busca=busca,
        categoria=categoria,
        categorias=categorias,
        situacao=situacao,
    )


@app.route("/produtos/novo", methods=["GET", "POST"])
def produto_novo():
    if request.method == "POST":
        try:
            nome = request.form.get("nome", "").strip()
            if not nome:
                raise ValueError("O nome do produto é obrigatório.")
            categoria = request.form.get("categoria", "").strip()
            if not categoria:
                raise ValueError("A categoria do produto é obrigatória.")
            preco = decimal_positivo(request.form.get("preco"), "O preço")
            minimo = inteiro_nao_negativo(request.form.get("estoque_minimo"), "O estoque mínimo")
            descricao = request.form.get("descricao", "").strip() or None

            with banco() as (conexao, cursor):
                conexao.start_transaction()
                cursor.execute(
                    """
                    SELECT codigo
                    FROM produtos
                    WHERE codigo REGEXP '^[0-9]+$'
                    ORDER BY CAST(codigo AS UNSIGNED) DESC
                    LIMIT 1
                    FOR UPDATE
                    """
                )
                ultimo = cursor.fetchone()
                proximo_numero = int(ultimo["codigo"]) + 1 if ultimo else 1
                codigo = str(proximo_numero).zfill(3)
                cursor.execute(
                    """
                    INSERT INTO produtos
                        (codigo, categoria, nome, descricao, preco,
                         quantidade_estoque, estoque_minimo, data_validade)
                    VALUES (%s, %s, %s, %s, %s, 0, %s, NULL)
                    """,
                    (codigo, categoria, nome, descricao, preco, minimo),
                )
                id_produto = cursor.lastrowid
                conexao.commit()
            flash("Produto cadastrado. Agora informe o lote recebido.", "sucesso")
            return redirect(url_for("lote_novo", produto=id_produto))
        except (ValueError, Error) as erro:
            flash(str(erro), "erro")
    return render_template("produto_form.html", produto=None)


@app.route("/produtos/<int:id_produto>/editar", methods=["GET", "POST"])
def produto_editar(id_produto):
    with banco() as (_, cursor):
        cursor.execute("SELECT * FROM produtos WHERE id_produto = %s", (id_produto,))
        produto = cursor.fetchone()
    if not produto:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("produtos"))

    if request.method == "POST":
        try:
            nome = request.form.get("nome", "").strip()
            if not nome:
                raise ValueError("O nome do produto é obrigatório.")
            categoria = request.form.get("categoria", "").strip()
            if not categoria:
                raise ValueError("A categoria do produto é obrigatória.")
            preco = decimal_positivo(request.form.get("preco"), "O preço")
            minimo = inteiro_nao_negativo(request.form.get("estoque_minimo"), "O estoque mínimo")
            descricao = request.form.get("descricao", "").strip() or None

            with banco() as (conexao, cursor):
                cursor.execute(
                    """
                    UPDATE produtos
                    SET categoria = %s, nome = %s,
                        descricao = %s, preco = %s, estoque_minimo = %s
                    WHERE id_produto = %s
                    """,
                    (categoria, nome, descricao, preco, minimo, id_produto),
                )
                conexao.commit()
            flash("Produto atualizado com sucesso.", "sucesso")
            return redirect(url_for("produtos"))
        except (ValueError, Error) as erro:
            flash(str(erro), "erro")

    return render_template("produto_form.html", produto=produto)


@app.post("/produtos/<int:id_produto>/excluir")
def produto_excluir(id_produto):
    try:
        with banco() as (conexao, cursor):
            cursor.execute("DELETE FROM produtos WHERE id_produto = %s", (id_produto,))
            conexao.commit()
        flash("Produto excluído.", "sucesso")
    except Error:
        flash("Este produto possui lotes ou vendas vinculadas e não pode ser excluído.", "erro")
    return redirect(url_for("produtos"))


@app.route("/lotes")
def lotes():
    busca = request.args.get("q", "").strip()
    situacao = request.args.get("situacao", "").strip()
    condicoes = []
    parametros = []
    if busca:
        condicoes.append(
            "(p.nome LIKE %s OR p.codigo LIKE %s OR l.codigo_lote LIKE %s OR l.fornecedor LIKE %s)"
        )
        parametros.extend((f"%{busca}%", f"%{busca}%", f"%{busca}%", f"%{busca}%"))
    if situacao == "ativos":
        condicoes.append("l.quantidade > 0")
    elif situacao == "vencendo":
        condicoes.append(
            "l.quantidade > 0 AND l.data_validade BETWEEN CURDATE() "
            "AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)"
        )
    elif situacao == "vencidos":
        condicoes.append("l.quantidade > 0 AND l.data_validade < CURDATE()")
    elif situacao == "esgotados":
        condicoes.append("l.quantidade = 0")

    consulta = """
        SELECT
            l.*,
            p.nome AS produto,
            p.codigo AS codigo_produto,
            DATEDIFF(l.data_validade, CURDATE()) AS dias_validade
        FROM lotes l
        JOIN produtos p ON p.id_produto = l.id_produto
    """
    if condicoes:
        consulta += " WHERE " + " AND ".join(condicoes)
    consulta += " ORDER BY l.data_validade IS NULL, l.data_validade, p.nome"

    with banco() as (_, cursor):
        cursor.execute(consulta, tuple(parametros))
        lista = cursor.fetchall()
    return render_template(
        "lotes.html",
        lotes=lista,
        busca=busca,
        situacao=situacao,
    )


@app.route("/lotes/novo", methods=["GET", "POST"])
def lote_novo():
    with banco() as (_, cursor):
        cursor.execute("SELECT id_produto, codigo, nome FROM produtos ORDER BY categoria, nome")
        lista_produtos = cursor.fetchall()

    if request.method == "POST":
        try:
            id_produto = int(request.form.get("id_produto", ""))
            codigo_lote = request.form.get("codigo_lote", "").strip()
            fornecedor = request.form.get("fornecedor", "").strip() or None
            quantidade = inteiro_nao_negativo(request.form.get("quantidade"), "A quantidade")
            data_entrada = data_iso(
                request.form.get("data_entrada"),
                "A data de entrada",
                obrigatoria=True,
            )
            data_validade = data_iso(request.form.get("data_validade"), "A validade")
            if not codigo_lote:
                raise ValueError("O código do lote é obrigatório.")
            if quantidade == 0:
                raise ValueError("A quantidade recebida deve ser maior que zero.")
            validar_datas_lote(data_entrada, data_validade)

            with banco() as (conexao, cursor):
                cursor.execute(
                    """
                    INSERT INTO lotes
                        (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (id_produto, codigo_lote, fornecedor, data_validade, quantidade, data_entrada),
                )
                sincronizar_estoque(cursor, id_produto)
                conexao.commit()
            flash("Lote recebido e estoque atualizado.", "sucesso")
            return redirect(url_for("lotes"))
        except (ValueError, Error) as erro:
            mensagem = (
                "Já existe um lote com este código para o produto selecionado."
                if isinstance(erro, Error) and erro.errno == 1062
                else str(erro)
            )
            flash(mensagem, "erro")

    return render_template(
        "lote_form.html",
        lote=None,
        produtos=lista_produtos,
        hoje=date.today().isoformat(),
    )


@app.route("/lotes/<int:id_lote>/editar", methods=["GET", "POST"])
def lote_editar(id_lote):
    with banco() as (_, cursor):
        cursor.execute(
            """
            SELECT
                l.*,
                p.nome AS produto,
                EXISTS(
                    SELECT 1 FROM itens_venda iv WHERE iv.id_lote = l.id_lote
                ) AS possui_vendas
            FROM lotes l
            JOIN produtos p ON p.id_produto = l.id_produto
            WHERE l.id_lote = %s
            """,
            (id_lote,),
        )
        lote = cursor.fetchone()
    if not lote:
        flash("Lote não encontrado.", "erro")
        return redirect(url_for("lotes"))

    if request.method == "POST":
        try:
            id_produto = int(request.form.get("id_produto", ""))
            codigo_lote = request.form.get("codigo_lote", "").strip()
            fornecedor = request.form.get("fornecedor", "").strip() or None
            quantidade = inteiro_nao_negativo(request.form.get("quantidade"), "A quantidade")
            data_entrada = data_iso(
                request.form.get("data_entrada"),
                "A data de entrada",
                obrigatoria=True,
            )
            data_validade = data_iso(request.form.get("data_validade"), "A validade")
            if not codigo_lote:
                raise ValueError("O código do lote é obrigatório.")
            validar_datas_lote(data_entrada, data_validade)
            if lote["possui_vendas"] and id_produto != lote["id_produto"]:
                raise ValueError(
                    "O produto deste lote não pode ser alterado porque ele já participou de uma venda."
                )

            with banco() as (conexao, cursor):
                cursor.execute(
                    """
                    UPDATE lotes
                    SET id_produto = %s, codigo_lote = %s, fornecedor = %s,
                        data_validade = %s, quantidade = %s, data_entrada = %s
                    WHERE id_lote = %s
                    """,
                    (
                        id_produto,
                        codigo_lote,
                        fornecedor,
                        data_validade,
                        quantidade,
                        data_entrada,
                        id_lote,
                    ),
                )
                sincronizar_estoque(cursor, lote["id_produto"])
                if id_produto != lote["id_produto"]:
                    sincronizar_estoque(cursor, id_produto)
                conexao.commit()
            flash("Lote atualizado e estoque recalculado.", "sucesso")
            return redirect(url_for("lotes"))
        except (ValueError, Error) as erro:
            mensagem = (
                "Já existe um lote com este código para o produto selecionado."
                if isinstance(erro, Error) and erro.errno == 1062
                else str(erro)
            )
            flash(mensagem, "erro")

    with banco() as (_, cursor):
        cursor.execute("SELECT id_produto, codigo, nome FROM produtos ORDER BY categoria, nome")
        lista_produtos = cursor.fetchall()
    return render_template(
        "lote_form.html",
        lote=lote,
        produtos=lista_produtos,
        hoje=date.today().isoformat(),
    )


@app.post("/lotes/<int:id_lote>/excluir")
def lote_excluir(id_lote):
    try:
        with banco() as (conexao, cursor):
            cursor.execute(
                """
                SELECT
                    l.id_produto,
                    EXISTS(
                        SELECT 1 FROM itens_venda iv WHERE iv.id_lote = l.id_lote
                    ) AS possui_vendas
                FROM lotes l
                WHERE l.id_lote = %s
                """,
                (id_lote,),
            )
            lote = cursor.fetchone()
            if not lote:
                raise ValueError("Lote não encontrado.")
            if lote["possui_vendas"]:
                raise ValueError(
                    "Este lote já participou de uma venda e não pode ser excluído."
                )
            cursor.execute("DELETE FROM lotes WHERE id_lote = %s", (id_lote,))
            sincronizar_estoque(cursor, lote["id_produto"])
            conexao.commit()
        flash("Lote excluído e estoque recalculado.", "sucesso")
    except (ValueError, Error) as erro:
        flash(str(erro), "erro")
    return redirect(url_for("lotes"))


@app.route("/clientes")
def clientes():
    busca = request.args.get("q", "").strip()
    with banco() as (_, cursor):
        sql = """
            SELECT
                c.*,
                COALESCE(SUM(
                    CASE
                        WHEN v.status = 'concluida' THEN v.valor_total
                        ELSE 0
                    END
                ), 0) AS total_gasto,
                SUM(
                    CASE
                        WHEN v.status = 'concluida' THEN 1
                        ELSE 0
                    END
                ) AS compras_concluidas,
                (
                    SELECT COUNT(*)
                    FROM cupons_fidelidade cf
                    WHERE cf.id_cliente = c.id_cliente
                      AND cf.status = 'disponivel'
                      AND cf.data_validade >= CURDATE()
                ) AS cupons_disponiveis,
                (
                    SELECT MIN(cf.data_validade)
                    FROM cupons_fidelidade cf
                    WHERE cf.id_cliente = c.id_cliente
                      AND cf.status = 'disponivel'
                      AND cf.data_validade >= CURDATE()
                ) AS proxima_validade
            FROM clientes c
            LEFT JOIN vendas v ON v.id_cliente = c.id_cliente
            WHERE c.nome <> 'Consumidor Final'
        """
        parametros = []
        if busca:
            sql += " AND c.nome LIKE %s"
            parametros.append(f"%{busca}%")
        sql += """
            GROUP BY
                c.id_cliente,
                c.nome,
                c.telefone,
                c.email,
                c.endereco,
                c.data_cadastro,
                c.saldo_fidelidade
            ORDER BY c.nome
        """
        cursor.execute(sql, parametros)
        lista = cursor.fetchall()
    return render_template(
        "clientes.html",
        clientes=lista,
        busca=busca,
        meta_fidelidade=META_FIDELIDADE,
    )


@app.route("/clientes/novo", methods=["GET", "POST"])
def cliente_novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome do cliente é obrigatório.", "erro")
        else:
            with banco() as (conexao, cursor):
                cursor.execute(
                    """
                    INSERT INTO clientes (nome, telefone, email, endereco, data_cadastro)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        nome,
                        request.form.get("telefone", "").strip() or None,
                        request.form.get("email", "").strip() or None,
                        request.form.get("endereco", "").strip() or None,
                        date.today(),
                    ),
                )
                conexao.commit()
            flash("Cliente cadastrado com sucesso.", "sucesso")
            return redirect(url_for("clientes"))
    return render_template("cliente_form.html", cliente=None)


@app.route("/clientes/<int:id_cliente>/editar", methods=["GET", "POST"])
def cliente_editar(id_cliente):
    with banco() as (_, cursor):
        cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
    if not cliente:
        flash("Cliente não encontrado.", "erro")
        return redirect(url_for("clientes"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome do cliente é obrigatório.", "erro")
        else:
            with banco() as (conexao, cursor):
                cursor.execute(
                    """
                    UPDATE clientes
                    SET nome = %s, telefone = %s, email = %s, endereco = %s
                    WHERE id_cliente = %s
                    """,
                    (
                        nome,
                        request.form.get("telefone", "").strip() or None,
                        request.form.get("email", "").strip() or None,
                        request.form.get("endereco", "").strip() or None,
                        id_cliente,
                    ),
                )
                conexao.commit()
            flash("Cliente atualizado com sucesso.", "sucesso")
            return redirect(url_for("clientes"))

    return render_template("cliente_form.html", cliente=cliente)


@app.post("/clientes/<int:id_cliente>/excluir")
def cliente_excluir(id_cliente):
    with banco() as (conexao, cursor):
        cursor.execute("DELETE FROM clientes WHERE id_cliente = %s", (id_cliente,))
        conexao.commit()
    flash("Cliente excluído. As vendas anteriores foram preservadas.", "sucesso")
    return redirect(url_for("clientes"))


@app.route("/vendas")
def vendas():
    with banco() as (_, cursor):
        cursor.execute(
            """
            SELECT
                v.id_venda,
                v.data_venda,
                v.valor_total,
                v.forma_pagamento,
                v.troco,
                v.status,
                COALESCE(c.nome, 'Consumidor final') AS cliente,
                COUNT(DISTINCT iv.id_produto) AS tipos_itens,
                COALESCE(SUM(iv.quantidade), 0) AS unidades
            FROM vendas v
            LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
            LEFT JOIN itens_venda iv ON iv.id_venda = v.id_venda
            GROUP BY
                v.id_venda, v.data_venda, v.valor_total, v.forma_pagamento,
                v.troco, v.status, c.nome
            ORDER BY v.data_venda DESC
            LIMIT 100
            """
        )
        lista = cursor.fetchall()
    return render_template(
        "vendas.html",
        vendas=lista,
        formas_pagamento=FORMAS_PAGAMENTO,
    )


@app.route("/vendas/nova", methods=["GET", "POST"])
def venda_nova():
    with banco() as (_, cursor):
        cursor.execute(
            """
            SELECT
                c.id_cliente,
                c.nome,
                c.saldo_fidelidade,
                (
                    SELECT cf.id_cupom
                    FROM cupons_fidelidade cf
                    WHERE cf.id_cliente = c.id_cliente
                      AND cf.status = 'disponivel'
                      AND cf.data_validade >= CURDATE()
                    ORDER BY cf.data_validade, cf.id_cupom
                    LIMIT 1
                ) AS id_cupom,
                (
                    SELECT cf.valor
                    FROM cupons_fidelidade cf
                    WHERE cf.id_cliente = c.id_cliente
                      AND cf.status = 'disponivel'
                      AND cf.data_validade >= CURDATE()
                    ORDER BY cf.data_validade, cf.id_cupom
                    LIMIT 1
                ) AS valor_cupom,
                (
                    SELECT cf.data_validade
                    FROM cupons_fidelidade cf
                    WHERE cf.id_cliente = c.id_cliente
                      AND cf.status = 'disponivel'
                      AND cf.data_validade >= CURDATE()
                    ORDER BY cf.data_validade, cf.id_cupom
                    LIMIT 1
                ) AS validade_cupom
            FROM clientes c
            WHERE c.nome <> 'Consumidor Final'
            ORDER BY c.nome
            """
        )
        lista_clientes = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                p.id_produto,
                p.codigo,
                p.categoria,
                p.nome,
                p.preco,
                SUM(l.quantidade) AS quantidade_estoque,
                COUNT(l.id_lote) AS total_lotes
            FROM produtos p
            JOIN lotes l ON l.id_produto = p.id_produto
            WHERE l.quantidade > 0
              AND (l.data_validade IS NULL OR l.data_validade >= CURDATE())
            GROUP BY p.id_produto, p.codigo, p.categoria, p.nome, p.preco
            ORDER BY p.categoria, p.nome
            """
        )
        lista_produtos = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                l.id_lote,
                l.id_produto,
                l.codigo_lote,
                l.fornecedor,
                l.data_validade,
                l.quantidade,
                p.nome AS produto,
                p.codigo AS codigo_produto,
                p.preco
            FROM lotes l
            JOIN produtos p ON p.id_produto = l.id_produto
            WHERE l.quantidade > 0
              AND (l.data_validade IS NULL OR l.data_validade >= CURDATE())
            ORDER BY
                p.categoria,
                p.nome,
                l.data_validade IS NULL,
                l.data_validade,
                l.data_entrada,
                l.id_lote
            """
        )
        lista_lotes = cursor.fetchall()

    if request.method == "POST":
        ids = request.form.getlist("lote_id[]")
        quantidades = request.form.getlist("quantidade[]")
        id_cliente = request.form.get("id_cliente") or None
        id_cupom_solicitado = request.form.get("id_cupom_fidelidade") or None
        forma_pagamento = request.form.get("forma_pagamento", "").strip()
        conexao = None

        try:
            if forma_pagamento not in FORMAS_PAGAMENTO:
                raise ValueError("Selecione uma forma de pagamento valida.")
            lotes_solicitados = {}
            for lote_id, quantidade in zip(ids, quantidades):
                if not lote_id:
                    continue
                qtd = inteiro_nao_negativo(quantidade, "A quantidade")
                if qtd == 0:
                    raise ValueError("A quantidade de cada item deve ser maior que zero.")
                chave = int(lote_id)
                lotes_solicitados[chave] = lotes_solicitados.get(chave, 0) + qtd
            if not lotes_solicitados:
                raise ValueError("Adicione pelo menos um produto e selecione o lote.")

            conexao = mysql.connector.connect(**db_config())
            cursor = conexao.cursor(dictionary=True)
            conexao.start_transaction()
            itens = []
            valor_bruto = Decimal("0.00")

            for lote_id, quantidade in lotes_solicitados.items():
                cursor.execute(
                    """
                    SELECT
                        l.id_lote,
                        l.id_produto,
                        l.codigo_lote,
                        l.data_validade,
                        l.quantidade AS quantidade_lote,
                        p.nome,
                        p.preco
                    FROM lotes l
                    JOIN produtos p ON p.id_produto = l.id_produto
                    WHERE l.id_lote = %s
                    FOR UPDATE
                    """,
                    (lote_id,),
                )
                item = cursor.fetchone()
                if not item:
                    raise ValueError("Um dos lotes selecionados não existe mais.")
                if item["data_validade"] and item["data_validade"] < date.today():
                    raise ValueError(
                        f"O lote {item['codigo_lote']} de {item['nome']} está vencido."
                    )
                if item["quantidade_lote"] < quantidade:
                    raise ValueError(
                        f"Estoque insuficiente no lote {item['codigo_lote']} "
                        f"de {item['nome']}. Disponível: {item['quantidade_lote']}."
                    )
                subtotal = item["preco"] * quantidade
                valor_bruto += subtotal
                itens.append((item, quantidade, subtotal))

            cliente = None
            if id_cliente:
                cursor.execute(
                    """
                    SELECT id_cliente, nome, saldo_fidelidade
                    FROM clientes
                    WHERE id_cliente = %s
                    FOR UPDATE
                    """,
                    (id_cliente,),
                )
                cliente = cursor.fetchone()
                if not cliente:
                    raise ValueError("O cliente selecionado não existe mais.")

            desconto = Decimal("0.00")
            cupom = None
            if id_cupom_solicitado:
                if not cliente:
                    raise ValueError("O cupom de fidelidade exige um cliente cadastrado.")
                cursor.execute(
                    """
                    SELECT id_cupom, id_cliente, valor, data_validade, status
                    FROM cupons_fidelidade
                    WHERE id_cupom = %s
                    FOR UPDATE
                    """,
                    (id_cupom_solicitado,),
                )
                cupom = cursor.fetchone()
                if (
                    not cupom
                    or cupom["id_cliente"] != cliente["id_cliente"]
                    or cupom["status"] != "disponivel"
                    or cupom["data_validade"] < date.today()
                ):
                    raise ValueError("O cupom selecionado não está mais disponível.")
                if valor_bruto < COMPRA_MINIMA_CUPOM:
                    raise ValueError(
                        "O cupom de R$ 15 exige uma compra mínima de R$ 150."
                    )
                desconto = cupom["valor"]

            total = valor_bruto - desconto
            valor_recebido = None
            troco = Decimal("0.00")
            if forma_pagamento == "dinheiro":
                valor_recebido = decimal_positivo(
                    request.form.get("valor_recebido"),
                    "O valor recebido",
                )
                if valor_recebido < total:
                    raise ValueError(
                        f"O valor recebido e menor que o total de {moeda_brasileira(total)}."
                    )
                troco = valor_recebido - total

            cursor.execute(
                """
                INSERT INTO vendas
                    (id_cliente, data_venda, valor_bruto, desconto_fidelidade,
                     valor_total, forma_pagamento, valor_recebido, troco, status,
                     fidelidade_creditada, saldo_fidelidade_apos,
                     id_cupom_fidelidade)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, 'concluida',
                        %s, %s, %s)
                """,
                (
                    id_cliente,
                    valor_bruto,
                    desconto,
                    total,
                    forma_pagamento,
                    valor_recebido,
                    troco,
                    total if cliente else Decimal("0.00"),
                    None,
                    cupom["id_cupom"] if cupom else None,
                ),
            )
            id_venda = cursor.lastrowid

            saldo_apos = None
            cupons_gerados = 0
            if cliente:
                saldo_apos = cliente["saldo_fidelidade"] + total
                saldo_apos, cupons_gerados = gerar_cupons_por_saldo(
                    cursor,
                    cliente["id_cliente"],
                    saldo_apos,
                    id_venda,
                )
                cursor.execute(
                    "UPDATE clientes SET saldo_fidelidade = %s WHERE id_cliente = %s",
                    (saldo_apos, cliente["id_cliente"]),
                )
                cursor.execute(
                    """
                    UPDATE vendas
                    SET saldo_fidelidade_apos = %s
                    WHERE id_venda = %s
                    """,
                    (saldo_apos, id_venda),
                )
            if cupom:
                cursor.execute(
                    """
                    UPDATE cupons_fidelidade
                    SET status = 'utilizado', id_venda_utilizacao = %s
                    WHERE id_cupom = %s
                    """,
                    (id_venda, cupom["id_cupom"]),
                )

            for item, quantidade, subtotal in itens:
                cursor.execute(
                    """
                    INSERT INTO itens_venda
                        (id_venda, id_produto, id_lote, quantidade, preco_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        id_venda,
                        item["id_produto"],
                        item["id_lote"],
                        quantidade,
                        item["preco"],
                        subtotal,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE lotes
                    SET quantidade = quantidade - %s
                    WHERE id_lote = %s
                    """,
                    (quantidade, item["id_lote"]),
                )
                sincronizar_estoque(cursor, item["id_produto"])

            conexao.commit()
            mensagem = f"Venda #{id_venda} registrada. Total: {moeda_brasileira(total)}."
            if cupons_gerados:
                mensagem += f" Cliente ganhou {cupons_gerados} cupom(ns) de R$ 15."
            flash(mensagem, "sucesso")
            return redirect(url_for("venda_comprovante", id_venda=id_venda))
        except (ValueError, Error) as erro:
            if conexao and conexao.is_connected():
                conexao.rollback()
            flash(str(erro), "erro")
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()

    return render_template(
        "venda_form.html",
        clientes=lista_clientes,
        produtos=lista_produtos,
        lotes=lista_lotes,
    )


@app.route("/vendas/<int:id_venda>/comprovante")
def venda_comprovante(id_venda):
    venda, itens, cupons_gerados, cupons_disponiveis = dados_comprovante(id_venda)
    if not venda:
        flash("Venda não encontrada.", "erro")
        return redirect(url_for("vendas"))

    forma_pagamento = FORMAS_PAGAMENTO.get(
        venda["forma_pagamento"],
        venda["forma_pagamento"].title(),
    )
    status = "CANCELADA" if venda["status"] == "cancelada" else "CONCLUÍDA"
    primeiro_nome = venda["cliente"].split()[0].title()
    saldo_fidelidade = (
        venda["saldo_fidelidade_apos"]
        if venda["saldo_fidelidade_apos"] is not None
        else (venda["saldo_fidelidade_atual"] or Decimal("0.00"))
    )
    faltam_fidelidade = max(Decimal("0.00"), META_FIDELIDADE - saldo_fidelidade)
    mensagem = (
        f"*MercadoFácil*\n\n"
        f"Olá, {primeiro_nome}! Sua compra #{venda['id_venda']} foi {status.lower()}.\n"
        f"Total: *{moeda_brasileira(venda['valor_total'])}*."
    )
    if venda["id_cliente"] and venda["status"] != "cancelada":
        if cupons_gerados:
            mensagem += "\n\nParabéns! Você ganhou um cupom de R$ 15."
        else:
            mensagem += (
                f"\n\nClube MercadoFácil: faltam "
                f"{moeda_brasileira(faltam_fidelidade)} para seu próximo cupom."
            )
        mensagem += "\nObrigado pela preferência!"

    telefone = re.sub(r"\D", "", venda["cliente_telefone"] or "")
    if telefone and not telefone.startswith("55") and len(telefone) in (10, 11):
        telefone = "55" + telefone
    telefone_valido = len(telefone) in (12, 13) and telefone.startswith("55")
    whatsapp_url = (
        f"https://wa.me/{telefone}?text={quote(mensagem)}"
        if venda["id_cliente"] and telefone_valido
        else None
    )
    assunto = quote(f"Comprovante MercadoFacil - Venda #{venda['id_venda']}")
    email_url = (
        f"mailto:{quote(venda['cliente_email'])}?subject={assunto}&body={quote(mensagem)}"
        if venda["id_cliente"] and venda["cliente_email"]
        else None
    )

    return render_template(
        "comprovante.html",
        venda=venda,
        itens=itens,
        forma_pagamento=forma_pagamento,
        whatsapp_url=whatsapp_url,
        email_url=email_url,
        cupons_gerados=cupons_gerados,
        cupons_disponiveis=cupons_disponiveis,
        saldo_fidelidade=saldo_fidelidade,
        faltam_fidelidade=faltam_fidelidade,
        meta_fidelidade=META_FIDELIDADE,
    )


@app.route("/vendas/<int:id_venda>/comprovante.pdf")
def venda_comprovante_pdf(id_venda):
    venda, itens, cupons_gerados, cupons_disponiveis = dados_comprovante(id_venda)
    if not venda:
        flash("Venda não encontrada.", "erro")
        return redirect(url_for("vendas"))

    saldo = (
        venda["saldo_fidelidade_apos"]
        if venda["saldo_fidelidade_apos"] is not None
        else (venda["saldo_fidelidade_atual"] or Decimal("0.00"))
    )
    faltam = max(Decimal("0.00"), META_FIDELIDADE - saldo)
    forma_pagamento = FORMAS_PAGAMENTO.get(
        venda["forma_pagamento"],
        venda["forma_pagamento"].title(),
    )
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Comprovante MercadoFacil #{id_venda}",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloMercadoFacil",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#176B45"),
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    subtitulo = ParagraphStyle(
        "SubtituloMercadoFacil",
        parent=estilos["BodyText"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#52605A"),
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    )
    normal = ParagraphStyle(
        "NormalMercadoFacil",
        parent=estilos["BodyText"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#18201D"),
    )
    destaque = ParagraphStyle(
        "DestaqueMercadoFacil",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor("#105337"),
    )
    historia = [
        Paragraph("MercadoFácil", titulo),
        Paragraph("Comprovante de venda", subtitulo),
    ]
    status = "CANCELADA" if venda["status"] == "cancelada" else "CONCLUÍDA"
    info = [
        ["Venda", f"#{venda['id_venda']}", "Situação", status],
        ["Data", venda["data_venda"].strftime("%d/%m/%Y às %H:%M"), "Cliente", venda["cliente"]],
        ["Pagamento", forma_pagamento, "", ""],
    ]
    tabela_info = Table(info, colWidths=[26 * mm, 52 * mm, 27 * mm, 55 * mm])
    tabela_info.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F7F5")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E1DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D6E1DB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    historia.extend([tabela_info, Spacer(1, 6 * mm)])

    dados_itens = [["Produto", "Lote", "Qtd.", "Unitário", "Subtotal"]]
    for item in itens:
        dados_itens.append(
            [
                Paragraph(f"{item['codigo']} - {item['nome']}", normal),
                item["codigo_lote"] or "-",
                str(item["quantidade"]),
                moeda_brasileira(item["preco_unitario"]),
                moeda_brasileira(item["subtotal"]),
            ]
        )
    tabela_itens = Table(
        dados_itens,
        repeatRows=1,
        colWidths=[70 * mm, 30 * mm, 14 * mm, 24 * mm, 26 * mm],
    )
    tabela_itens.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B45")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6E1DB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    historia.extend([tabela_itens, Spacer(1, 5 * mm)])

    totais = []
    if venda["desconto_fidelidade"]:
        totais.append(["Subtotal", moeda_brasileira(venda["valor_bruto"])])
        totais.append(
            ["Desconto fidelidade", f"-{moeda_brasileira(venda['desconto_fidelidade'])}"]
        )
    totais.append(["Total", moeda_brasileira(venda["valor_total"])])
    if venda["forma_pagamento"] == "dinheiro":
        totais.append(["Valor recebido", moeda_brasileira(venda["valor_recebido"])])
        totais.append(["Troco", moeda_brasileira(venda["troco"])])
    tabela_totais = Table(totais, colWidths=[45 * mm, 35 * mm], hAlign="RIGHT")
    tabela_totais.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.HexColor("#176B45")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#105337")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    historia.extend([tabela_totais, Spacer(1, 6 * mm)])

    if venda["id_cliente"]:
        fidelidade = ["<b>Clube MercadoFácil</b><br/>"]
        if venda["status"] == "cancelada":
            fidelidade.append("Esta venda foi cancelada e não conta para a fidelidade.")
        else:
            if cupons_gerados:
                validade = cupons_gerados[0]["data_validade"].strftime("%d/%m/%Y")
                fidelidade.append(
                    f"Parabéns! Esta compra gerou {len(cupons_gerados)} cupom(ns) "
                    f"de R$ 15, válido(s) até {validade}.<br/>"
                )
            if venda["id_cupom_fidelidade"]:
                fidelidade.append(
                    f"Desconto utilizado nesta compra: "
                    f"{moeda_brasileira(venda['desconto_fidelidade'])}.<br/>"
                )
            fidelidade.append(
                f"Acumulado: {moeda_brasileira(saldo)} de "
                f"{moeda_brasileira(META_FIDELIDADE)}.<br/>"
                f"Faltam {moeda_brasileira(faltam)} para o próximo cupom.<br/>"
            )
            if cupons_disponiveis["total"]:
                validade = cupons_disponiveis["proxima_validade"].strftime("%d/%m/%Y")
                fidelidade.append(
                    f"Cupons disponíveis: {cupons_disponiveis['total']} "
                    f"(próxima validade: {validade}).<br/>"
                )
            fidelidade.append(
                "Cada cupom vale R$ 15, por 30 dias, em compras a partir de R$ 150."
            )
        quadro = Table([[Paragraph("".join(fidelidade), destaque)]], colWidths=[164 * mm])
        quadro.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E8F4ED")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#A9D0B9")),
                    ("PADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        historia.extend([quadro, Spacer(1, 6 * mm)])

    rodape = ParagraphStyle(
        "RodapeMercadoFacil",
        parent=normal,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#66716C"),
    )
    historia.append(Paragraph("Agradecemos a preferência. Até a próxima compra!", rodape))
    documento.build(historia)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"MercadoFacil_Comprovante_{id_venda}.pdf",
    )


@app.post("/vendas/<int:id_venda>/cancelar")
def venda_cancelar(id_venda):
    conexao = None
    try:
        conexao = mysql.connector.connect(**db_config())
        cursor = conexao.cursor(dictionary=True)
        conexao.start_transaction()
        cursor.execute(
            """
            SELECT
                status,
                id_cliente,
                fidelidade_creditada,
                id_cupom_fidelidade
            FROM vendas
            WHERE id_venda = %s
            FOR UPDATE
            """,
            (id_venda,),
        )
        venda = cursor.fetchone()
        if not venda:
            raise ValueError("Venda nao encontrada.")
        if venda["status"] == "cancelada":
            raise ValueError("Esta venda ja foi cancelada.")

        cursor.execute(
            """
            SELECT id_cupom, status
            FROM cupons_fidelidade
            WHERE id_venda_origem = %s
            FOR UPDATE
            """,
            (id_venda,),
        )
        cupons_gerados = cursor.fetchall()
        if any(cupom["status"] == "utilizado" for cupom in cupons_gerados):
            raise ValueError(
                "Esta venda gerou um cupom que já foi utilizado. "
                "Cancele primeiro a venda que utilizou o cupom."
            )

        cursor.execute(
            """
            SELECT id_produto, id_lote, quantidade
            FROM itens_venda
            WHERE id_venda = %s
            FOR UPDATE
            """,
            (id_venda,),
        )
        itens = cursor.fetchall()
        produtos_afetados = set()
        for item in itens:
            if item["id_lote"]:
                cursor.execute(
                    "UPDATE lotes SET quantidade = quantidade + %s WHERE id_lote = %s",
                    (item["quantidade"], item["id_lote"]),
                )
            produtos_afetados.add(item["id_produto"])

        for id_produto in produtos_afetados:
            sincronizar_estoque(cursor, id_produto)

        if venda["id_cliente"]:
            cursor.execute(
                """
                SELECT saldo_fidelidade
                FROM clientes
                WHERE id_cliente = %s
                FOR UPDATE
                """,
                (venda["id_cliente"],),
            )
            cliente = cursor.fetchone()
            if cliente:
                cupons_a_reverter = sum(
                    1 for cupom in cupons_gerados if cupom["status"] == "disponivel"
                )
                cursor.execute(
                    """
                    UPDATE cupons_fidelidade
                    SET status = 'cancelado'
                    WHERE id_venda_origem = %s
                      AND status = 'disponivel'
                    """,
                    (id_venda,),
                )
                saldo = (
                    cliente["saldo_fidelidade"]
                    + (META_FIDELIDADE * cupons_a_reverter)
                    - (venda["fidelidade_creditada"] or Decimal("0.00"))
                )
                saldo = max(Decimal("0.00"), saldo)
                saldo, _ = gerar_cupons_por_saldo(
                    cursor,
                    venda["id_cliente"],
                    saldo,
                    None,
                )
                cursor.execute(
                    "UPDATE clientes SET saldo_fidelidade = %s WHERE id_cliente = %s",
                    (saldo, venda["id_cliente"]),
                )
                if venda["id_cupom_fidelidade"]:
                    cursor.execute(
                        """
                        UPDATE cupons_fidelidade
                        SET status = 'disponivel', id_venda_utilizacao = NULL
                        WHERE id_cupom = %s
                        """,
                        (venda["id_cupom_fidelidade"],),
                    )

        cursor.execute(
            """
            UPDATE vendas
            SET status = 'cancelada', data_cancelamento = NOW()
            WHERE id_venda = %s
            """,
            (id_venda,),
        )
        conexao.commit()
        flash(
            f"Venda #{id_venda} cancelada e estoque devolvido aos lotes.",
            "sucesso",
        )
    except (ValueError, Error) as erro:
        if conexao and conexao.is_connected():
            conexao.rollback()
        flash(str(erro), "erro")
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()
    return redirect(url_for("vendas"))


@app.route("/caixa")
def caixa():
    data_selecionada = request.args.get("data") or date.today().isoformat()
    with banco() as (_, cursor):
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_vendas,
                COALESCE(SUM(valor_total), 0) AS faturamento,
                COALESCE(AVG(valor_total), 0) AS ticket_medio
            FROM vendas
            WHERE DATE(data_venda) = %s
              AND status = 'concluida'
            """,
            (data_selecionada,),
        )
        resumo = cursor.fetchone()
        cursor.execute(
            """
            SELECT
                p.nome,
                SUM(iv.quantidade) AS quantidade,
                SUM(iv.subtotal) AS faturamento
            FROM vendas v
            JOIN itens_venda iv ON iv.id_venda = v.id_venda
            JOIN produtos p ON p.id_produto = iv.id_produto
            WHERE DATE(v.data_venda) = %s
              AND v.status = 'concluida'
            GROUP BY p.id_produto, p.nome
            ORDER BY faturamento DESC
            """,
            (data_selecionada,),
        )
        itens = cursor.fetchall()
    return render_template(
        "caixa.html",
        data_selecionada=data_selecionada,
        resumo=resumo,
        itens=itens,
    )


@app.errorhandler(Error)
def erro_banco(erro):
    return render_template("erro.html", detalhe=str(erro)), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
