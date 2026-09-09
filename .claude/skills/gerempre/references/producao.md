# O portão da produção

Isto é um portão, não uma receita. **A decisão é do operador**, dita com
todas as letras. Enquanto qualquer linha estiver em branco, o trabalho
continua na cópia de teste.

```
[x] o razao bate em todas as chapas, conferido ANTES de comecar
    09/09/2026: 96 de 96 batendo na producao
[x] a FIA existe no cadastro de funcionarios da PRODUCAO
    09/09/2026: FUNCOD 32, cargo 5, usuario FIA, gravada por autorizacao
    de Pedro Rafael. Sem linha na CAC: ela escreve por SQL, nao pela tela
[x] os codigos de cliente e os precos foram conferidos contra a
    PRODUCAO - os 9 precos e os 6 codigos de cliente do config.py
    batem exatamente com a producao, conferido em 09/09/2026
[x] o operador disse, com todas as letras, para virar a chave
    09/09/2026, Pedro Rafael: "entao vamos la PODE VIRAR A CHAVE"
[ ] o caminho de volta foi testado ANTES de precisar dele
    provado na copia de teste (132 -> 119 -> 132). Na producao o
    script existe e nao rodou
[ ] o operador acompanhou as primeiras OS, uma a uma, na tela
    a proxima OS que sair e a primeira de verdade
```

A chave virou em 09/09/2026, no `config_local.py` desta máquina. As duas
linhas em branco não são burocracia atrasada: são as que só se marcam
com a primeira OS de verdade na tela.

## O que muda, na prática

Uma linha no `config_local.py`:

```python
GEREMPRE_DSN = r"ARTE-JUNIOR/3050:C:\NeoGerempre\bdados\neobdados.fdb"
GEREMPRE_FUNCIONARIO = 32
```

O caminho é o de `ARTE-JUNIOR`, e não o do `U:` — a cópia que mora no
compartilhamento parou em 24/08. Ver `banco.md`, "O U: não é o banco
vivo".

O `config_local.py` fica fora do Git, então a produção nunca entra no
repositório por acidente.

## O caminho de volta

Testar antes de precisar quer dizer: numa OS de teste, apagar e conferir
que o estoque voltou ao que era.

```sql
DELETE FROM MOV WHERE MOVNOS = <numero>;   -- o gatilho devolve o saldo
DELETE FROM OS  WHERE OSCOD  = <numero>;
```

Depois, o razão de novo nas chapas envolvidas. Se o saldo tiver ficado
nulo em vez de voltar, é a armadilha nº 1: reconstrua pela soma dos
movimentos.

## Por que a numeração não volta

`GEN_OSCOD_ID` avança e não recua. Uma OS apagada deixa um buraco na
numeração, e isso é normal — o próprio programa deixa buracos quando um
operador desiste no meio. Não tente voltar o gerador.

## Os primeiros dias

Com produção ligada, vale um combinado: o operador confere cada OS aberta
pela FIA, na tela, antes de a próxima sair. O relatório do dia
(`python -m finart_ctp.relatorio`) mostra o que ela fez; a tela do
GEREMPRE mostra como ficou.

A pressa aqui não economiza nada. Uma OS que falta dá trabalho de uma
tarde; uma OS errada mexe no que a empresa tem e no que ela fatura, e só
aparece no inventário.
