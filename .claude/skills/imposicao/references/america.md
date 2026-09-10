# A AMÉRICA — o cliente que a FIA monta

Combinado com o operador em 10/09/2026.

## Por que ela é diferente de todos os outros

Os seis clientes que a FIA já atende **mandam o arquivo pronto**: já
montado, já imposto, no tamanho da chapa. A FIA só faz o fechamento
final — confere, abre a OS, imprime a prova e grava.

**Na AMÉRICA não.** O arquivo chega **por montar**, e quem monta é a
casa. Então o arquivo que cai na pasta do dia **não é um serviço pronto —
é matéria-prima**. Mandá-lo para o CTP como se fosse pronto seria gravar
chapa de arquivo não montado.

## O portão: a pasta `PARA CTP`

```
V:\AMERICA\<Mês>\<Dia>\              <- o arquivo chega aqui. NAO tocar.
V:\AMERICA\<Mês>\<Dia>\PARA CTP\     <- só o que está aqui segue o fluxo
```

**A FIA só olha a `PARA CTP`.** O que estiver na pasta do dia, fora dela,
é arquivo esperando montagem — e esperar é o certo.

## O caminho, a quatro mãos

| | quem | o quê |
|---|---|---|
| 1 | cliente | põe o arquivo em `V:\AMERICA\<Mês>\<Dia>\` |
| 2 | **operador** | passa à FIA as informações da montagem (chapa, pinça, arranjo, vão) |
| 3 | **FIA** | monta e grava `<mesmo nome>_MONTAGEM.pdf`, **na pasta do dia** |
| 4 | **operador** | **revisa** e, aprovando, move para `PARA CTP` |
| 5 | **FIA** | dali em diante é o fluxo normal: OS, prova, chapa no CTP |

O passo 4 é humano de propósito. A montagem é decisão, não conta: quem
diz que está certa é quem vai rodar.

"Será inicialmente um trabalho a quatro mãos" — palavras do operador. O
que a FIA aprender de cada montagem entra nesta skill, e a mão dela
cresce.

## A regra do nome

**`<mesmo nome do arquivo>_MONTAGEM`** — sufixo, no fim.

Não é invenção: a pasta da AMÉRICA de 10/09/2026 já trazia
`CRISTÃOS.pdf` ao lado de `CRISTÃOS_MONTAGEM.cdr`, e as OS do GEREMPRE
guardam títulos como `SANTINHO LUIS E LULA_MONTAGEM` e
`CARTAO DE RETORNO CBCO_MONTAGE`. A casa já fazia assim.

O nome de origem vai **inteiro**, sem limpeza — é ele que amarra a
montagem ao arquivo que a gerou.

## Os números da AMÉRICA, lidos do GEREMPRE

Conferidos em 10/09/2026, em leitura travada, nas OS que a casa abriu
esta semana:

| | |
|---|---|
| **cliente** | **58** — `AMERICA (GRAFICA E EDITORA AMERICA LTDA)` |
| **chapa** | **90**, `PM_52`, 525 × 459 |
| **preço** | **R$ 8,00** a chapa |
| **de quem é a chapa** | do **cliente** (`RBCHAPA = 1`, `RBCHAPAPRO = 0`) |
| quadricromia | `OSLAN = 4` |
| pinça | **60 mm** |

Quatro OS desta semana usam exatamente isso: 19633, 19623, 19601, 19553,
19546 — todas `4 × 8,00 = 32,00`.

**Atenção:** existe também uma chapa **15**, chamada `525X459`, de dono
`0` (própria da Finart). **Não é a da AMÉRICA.** A da AMÉRICA é a 90. Usar
a 15 baixaria estoque no lugar errado.

A AMÉRICA tem outras máquinas: a `SM_74` (chapa 89, 745 × 605, R$ 12,00)
aparece nas OS de revista. Ao montar, saiba em qual delas o trabalho vai
correr — a pinça e o preço mudam.

## O nome da chapa no CTP

Lido do que já está gravado em `W:\CTP\SETEMBRO\10\`:

```
525x459_CMYK_AMERICA_Panfleto RAImundo
525x459_GREY_AMERICA_El Shaday
525x459_AMERICA_CRISTAOS
```

É o mesmo feitio dos outros clientes de formato no nome —
`<formato>_<cores>_AMERICA_<nome>`.

Cada operador tem a sua pasta dentro do dia (`FIA`, `JOAOZ`, `PEDRO`,
`eudson`); a FIA grava na dela.

## O que ainda não está ligado

A AMÉRICA **não está no `config.py`**: não há código de cliente, nem
chapa cadastrada, nem pasta de entrada, nem formato 525 × 459 nas
tabelas. Enquanto não estiver, **a FIA não toca em nada dela sozinha** —
e isso é bom: o vigia não vai varrer `V:\AMERICA` por engano.

Quando for ligar, a entrada tem de apontar para **`PARA CTP`**, e nunca
para a pasta do dia. Esse é o ponto inteiro.
