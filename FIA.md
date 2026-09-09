# FIA — Finart Inteligência Artificial

FIA trabalha no departamento de arte final da Finart. Ela fecha chapa para
o CTP: recebe a arte do cliente, confere, imprime a prova, separa as tintas
e entrega o arquivo pronto para a gravadora.

Não é um programa que o operador manda rodar. É uma colega que fica de olho
nas pastas o dia inteiro, faz o que sabe fazer e chama alguém quando não
sabe.

---

## O que ela faz, do começo ao fim

```
   pasta do cliente                  o que a FIA faz                   CTP
   ────────────────                  ───────────────                   ───

   V:\<cliente>\MES\DIA        1. vê o arquivo chegar
        │                      2. espera terminar de chegar
        │                      3. confere se já não fez
        ▼                      4. mede a arte
   arte do cliente             5. lê a cobertura de tinta
        │                      6. IMPRIME A PROVA  ──────────► papel na mesa
        │                      7. monta na chapa, se precisar
        │                      8. separa C, M, Y, K
        ▼                      9. mede a chapa gravada
   chapa pronta               10. anota o que fez  ───────────► W:\CTP\...\FIA
```

A prova sai **antes** da chapa, sempre. Se a impressora estiver fora, nada
é gerado: o arquivo fica segurado e ela tenta de novo a cada 5 minutos.
Chapa no CTP sem papel na mesa é serviço que ninguém confere.

---

## Os seis clientes

| cliente | entra | chapas | o que tem de diferente |
|---|---|---|---|
| SOLIDA | PDF | 510x400 · 775x635 | nome pela OS; nada trava |
| VOPRIX | .cdr | 510x400 · 775x635 | ela mesma converte no CorelDRAW |
| FIALHO | PDF | 510x400 · 730x600 | encaixa até 15 mm de diferença |
| EMPORIO | PDF | 510x400 · 660x605 | nome pela OS, descrição até 25 letras |
| VIVA | PDF | 510x400 | descrição é o nome do arquivo |
| CREATIVE | PDF | 510x400 | **monta a arte na chapa, com pinça de 40 mm** |

Subpasta dentro da pasta do dia é trabalho igual — o operador cria
`noite`, `manhã`, o que quiser, para se organizar.

---

## O que ela sabe

**Da chapa**

- reconhecer o formato e casar com a chapa certa do cliente
- gravar a 1000 dpi nas 510x400 e 800 nas grandes
- montar arte menor na chapa, centralizada, sem nunca mudar o tamanho dela
- achar a marca de corte no vetor do PDF e medir a pinça a partir dela
- girar arte que chega em pé, para deitar como sempre vem
- separar C, M, Y, K e montar o PDF só com as tintas que existem
- reconhecer preto composto e gravar uma chapa em cinza no lugar de quatro

**Da arte, por dentro** (preflight)

- medir a **resolução efetiva** de cada imagem — quantos dpi ela tem no
  tamanho em que foi colocada, e não o dpi que o arquivo dela declara.
  Na **SOLIDA** o número sai no log e a chapa segue: a arte dela vem do
  cliente final e chega como chega
- reconhecer fonte que não está incorporada
- achar traço fino demais para a chapa segurar
- ver cor especial declarada na arte
- ignorar o que não importa: tirinha de degradê, fio de moldura, e a
  marca de corte de 0,25 pt que existe em todo arquivo

**Do arquivo**

- esperar o arquivo terminar de chegar pela rede
- reconhecer a mesma arte regravada com data nova, e não refazer
- recusar arquivo grande demais para a máquina dar conta
- exigir do CorelDRAW compressão sem perda e proibir reamostragem

**Do próprio trabalho**

- imprimir a prova identificada, com o nome do cliente e o formato
- medir a chapa depois de gravada e apagá-la se sair fora da resolução
- não fazer duas vezes: uma FIA por máquina, e registro com retrato do
  conteúdo
- avisar quando o código dela mudou no disco e a janela está desatualizada

---

## O que ela NÃO faz

**Não cria arte.** Ela confere arte que chega pronta. Design é de gente.

**Não altera o tamanho do que o cliente mandou.** Reduzir moveria o corte
de lugar. O que não cabe vira pendência, não vira arte menor.

**Não chuta.** Não achou a marca de corte, não veio em quadricromia, não
cabe na chapa, o nome diz verniz — ela para e chama. Uma chapa que falta dá
trabalho; uma chapa errada dá prejuízo.

**Não apaga nem move nada da pasta do cliente.** A pasta é compartilhada.
O controle do que já foi feito é dela, no PC.

**Não fecha documento que não foi ela que abriu.** Regra nascida de erro:
o CorelDRAW devolve o documento do operador se o arquivo já estiver aberto,
e fechar aquilo joga o trabalho dele fora.

---

## Como ela pede ajuda

Quando algo foge do padrão, ela grita na tela e anota:

```
!!!  PENDENCIA - PRECISA DE VOCE
!!!  arquivo: CUPOM 13 08.pdf
!!!  motivo : pagina 2: NAO veio em quadricromia - GRAY
!!!            (C 0.0000 M 0.0000 Y 0.0000 K 0.7734).
!!!            Sairia como 510x400_GRAY_CREATIVE_CUPOM 13 08 V.
!!!            Nao fechei: confira antes
```

Três coisas em toda pendência: **qual arquivo**, **o que ela viu** (com
número), e **o que teria feito**. Sem isso o operador precisa adivinhar.

Tudo fica em `C:\Finart\_ctp_ia`: o log do dia, o `_PENDENCIAS.txt` e o
registro do que já foi fechado.

---

## O que ela ainda vai aprender

- sangria: medir se a arte avança o bastante além do corte
- sobreimpressão: branco que some, preto que fecha
- ler e preencher a OS no GEREMPRE

---

## Onde ela mora

| | |
|---|---|
| código | `src/finart_ctp/` |
| ajustes desta máquina | `src/finart_ctp/config_local.py` (fora do Git) |
| log, registro, pendências | `C:\Finart\_ctp_ia` |
| o que precisou de mão | `C:\Finart\_PENDENCIAS` |
| saída | `W:\CTP\<MÊS>\<DIA>\FIA` |

Para conferir a resolução do que ela já entregou:

```
python -m finart_ctp.auditoria "W:\CTP\SETEMBRO\08\FIA"
```

Para saber o que ela fez no dia:

```
python -m finart_ctp.relatorio
```

```
CHAPAS ENTREGUES
   SOLIDA     35 chapa(s)    47.3 min de maquina
   VIVA       26 chapa(s)    30.0 min de maquina
   VOPRIX     16 chapa(s)    16.0 min de maquina
   EMPORIO    13 chapa(s)    11.2 min de maquina
   CREATIVE   11 chapa(s)     3.5 min de maquina
   FIALHO      4 chapa(s)     2.0 min de maquina
   TOTAL     105            110.0 min   |  5.0 GB gravados

PROVAS IMPRESSAS
   100 folha(s) A4

O QUE PAROU E ESPEROU GENTE
    3 x  nome repetido - virou MODELO ou _v2
    2 x  arte fora de quadricromia
    2 x  arquivo acima do limite
```

---

## O princípio

Toda regra dela nasceu de um erro que custou alguma coisa, e o comentário
no código conta qual foi. Isso é de propósito: quem for mexer um dia
precisa saber o que a regra está segurando antes de resolver simplificá-la.

Entre errar sozinha e parar para perguntar, a FIA para.
