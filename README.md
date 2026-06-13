# MercadoFacil Web

As vendas registram a forma de pagamento (dinheiro, PIX ou cartao), calculam
o troco quando necessario e geram um comprovante simples para impressao.
Uma venda pode ser cancelada pelo historico; nesse caso, o sistema devolve
cada quantidade exatamente ao lote utilizado e retira a venda do faturamento.

Para clientes cadastrados, o sistema gera uma mensagem de WhatsApp com o total
da venda e a situacao do Clube MercadoFacil. Essa opcao funciona localmente,
nao exige API paga, assinatura ou mensalidade.

## Clube MercadoFacil

- Cada R$ 500 pagos por um cliente cadastrado gera um cupom de R$ 15.
- O cupom vale por 30 dias.
- Pode ser usado em compras a partir de R$ 150.
- Apenas um cupom pode ser utilizado por venda.
- O valor que ultrapassar R$ 500 continua acumulado para a proxima meta.
- Vendas canceladas nao geram saldo nem cupom.

Lotes podem ser corrigidos pelo menu `Lotes`, incluindo produto, codigo,
fornecedor, quantidade, entrada e validade. Um lote sem vendas tambem pode ser
excluido. Depois que participa de uma venda, seu produto e sua exclusao ficam
bloqueados para preservar o historico; uma venda incorreta deve ser cancelada
e registrada novamente.

Sistema web para gerenciamento de clientes, produtos, estoque, vendas e
fechamento diário de um pequeno mercado.

O estoque é separado por lotes. Cada lote registra fornecedor, quantidade, data
de entrada e validade. Um produto pode ter diversos lotes e fornecedores. Na
venda, o operador usa o código de barras do fabricante para localizar o produto
rapidamente. O sistema faz a baixa interna em um lote disponível, enquanto a
conferência de lotes e validades fica no módulo de estoque/inventário.

## Leitor de código de barras

O sistema possui campo de leitura rápida na tela de venda. Um leitor USB comum
funciona como teclado: o operador posiciona o cursor no campo `Ler código de
barras`, passa o leitor e o sistema pesquisa o cadastro do produto.

- O código de barras do fabricante identifica o produto.
- Ao bipar novamente o mesmo produto, a quantidade é incrementada no carrinho.
- O controle de lote e validade é feito pelo responsável do estoque em
  conferências periódicas, por exemplo a cada 15 dias.

Essa escolha deixa o caixa mais rápido e mantém o controle de validade fora do
momento da venda, que é o fluxo mais adequado para um mercadinho pequeno.

Cada produto possui um código interno global, numérico e único no formato
`001`, `002` e assim por diante. O código é gerado automaticamente após o
último número cadastrado. A categoria serve apenas para organização e filtros.

Os dados demonstrativos incluem dois lotes com fornecedores e validades
diferentes para cada produto.

> Esta é a versão atual. Os dados são armazenados no MySQL. Arquivos antigos
> baseados em `clientes.txt`, `vendas.txt` ou `estoque.txt` não fazem parte
> desta aplicação.

## Iniciar no computador de demonstração

1. Inicie o serviço `MySQL80`.
2. Execute `CONFIGURAR_BANCO.bat` somente na primeira utilização.
3. Execute `INICIAR_SITE.bat`.
4. O sistema abrirá em `http://localhost:5000`.

Credenciais da versão local:

- Usuário: `mercadofacil`
- Senha: `Mercado@2026`

O computador precisa ter Python 3, MySQL 8 e as dependências instaladas:

```powershell
py -m pip install -r requirements.txt
```

## Banco de dados

Por padrão, a versão local usa:

- Servidor: `localhost`
- Porta: `3306`
- Usuário: `root`
- Banco: `mercadofacil`

A senha local fica apenas nos arquivos `.bat` de demonstração. Para publicação,
configure as variáveis documentadas em `.env.example`.

## Publicação

O projeto está preparado para hospedagem Flask com `gunicorn`. Em serviços que
fornecem MySQL, as variáveis `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`,
`MYSQLPASSWORD` e `MYSQLDATABASE` também são reconhecidas automaticamente.

A versão local não fica acessível por outros computadores. Para abrir o sistema
por um link, a aplicação e o banco precisam ser publicados em uma hospedagem.
Antes da apresentação, mantenha também a cópia local no pendrive como reserva.

O arquivo `render.yaml` prepara um serviço gratuito no Render. As credenciais
do banco e a senha de acesso devem ser cadastradas como variáveis secretas no
painel da hospedagem e nunca enviadas ao GitHub.
