# Dá para fazer um sistema próprio da Finart?

Pergunta do operador em 10/09/2026: um sistema da casa, **primeiro
idêntico** ao GEREMPRE, depois melhorado — sem perder nenhuma parte.

Respondido depois de varrer produção inteira, com a trava de leitura.
Refaça a varredura com `ferramentas/varredura_gerempre.py`.

## A resposta curta

**Dá. E o banco é a parte fácil — o risco não está onde parece.**

## Por que o banco é fácil

| | |
|---|---|
| tabelas em uso | 9 de 16 |
| campos vivos na `OS` | 116 de 146 |
| **regra de negócio no banco** | **104 linhas de PSQL, em 6 gatilhos** |
| e dessas, substanciais | **um gatilho só**, o `TR_OS_BEFO` |
| procedimentos com regra | nenhum — os 11 são consulta de relatório |
| o razão | **fechava 96 de 96 em 10/09/2026** |

A regra inteira cabe numa tela e meia. E o razão fechando dá o que toda
migração precisa e quase nunca tem: **um ponto de partida provadamente
consistente**, e um juiz para conferir cada passo.

## Onde está o risco

```
neogerempre.exe   5,9 MB   19/03/2020   Delphi, compilado, sem fonte
```

Um executável fechado, com os relatórios embutidos — não há um `.fr3`
sequer para ler. E como o banco **não exige quase nada** (uma chave
primária numa tabela vazia, zero estrangeiras), toda regra que não está
naquelas 104 linhas está dentro do exe, invisível.

**O que se lê, se reproduz. O que o programa faz só se descobre olhando
ele funcionar** — tela por tela, relatório por relatório, com quem usa do
lado. Esse é o trabalho de verdade, e ele não é de programação: é de
observação.

## As cinco maneiras de "perder uma parte"

**1. Os 78% de movimento órfão.** 102.168 de 131.502 apontam para OS que
não existe mais — `MOV` desde 2015, `OS` só desde junho/2024, numeração
reiniciada. Um sistema com integridade referencial de verdade
**recusaria quatro quintos da história de estoque**. Ou se mantém a
tolerância, ou se decide conscientemente o que fazer com onze anos de
movimento sem OS. É decisão de dono, não de quem programa.

**2. O caminho de volta sem gabarito.** `OSSIT = 2` / `OSTIPO = 4`
devolvem chapa ao estoque, e já correram 6 vezes — mas em 10/09/2026
**nenhuma OS estava nesses estados**. É a parte mais fácil de se perder
em silêncio: não há dado de produção que sirva para conferir.

**3. Os 24 movimentos sem chapa.** O `UPDATE` do gatilho não casa linha,
não reclama, e o estoque não anda. Um sistema com chave estrangeira
rejeitaria essas 24 linhas; um sem, repetiria o silêncio. Escolha
consciente, dos dois jeitos.

**4. `charset NONE`.** O banco guarda byte cru, sem codificação
declarada. Migração tem de ser byte a byte, ou todo acento vira lixo.

**5. E a maior: as regras invisíveis.** Uma chave primária em 303
colunas. Tudo que o Delphi recusa e o gatilho não recusa é regra que
**não temos como enxergar** — só aparece no dia em que alguém digitar
algo que o programa velho barrava e o novo aceita. Não há como listar o
que não se vê; só há como descobrir usando.

## Como fazer, se for para fazer

**Não big-bang.** O sistema novo fala com o **mesmo banco Firebird** no
começo, tela por tela, convivendo com o exe velho. O razão é o juiz:
fecha hoje, e tem de continuar fechando depois de cada passo. Quando toda
tela tiver migrado, aí sim se troca o banco por baixo.

Assim nunca se fica sem sistema, e cada passo é reversível — que é
exatamente o que "idêntico primeiro, melhorar depois" pede.

## Uma coisa para consertar antes, independente de refazer

```
U:\config.txt
    User_Name=sysdba
    Password=masterkey
```

Texto puro, num compartilhamento de rede, e `masterkey` é a **senha de
fábrica do Firebird**, inalterada desde 2008. Somando com a armadilha 8 —
a `FUN` guarda a senha de todo funcionário em texto puro —, quem alcança
aquela pasta é administrador do banco de produção da empresa.

Trocar isso não depende de refazer sistema nenhum. E refazer sem
consertar seria carregar o problema para dentro do sistema novo.
