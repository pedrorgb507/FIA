# 09: `.cdr` no portão e arquivo de várias páginas

**What to build:** O portão passa a aceitar o que a AMÉRICA realmente
manda, e não só o caso limpo.

**O `.cdr`** é publicado em PDF pelo motor da própria Corel — e não se
rasteriza, ao contrário do da VOPRIX e do da PRIME: a AMÉRICA manda a
imagem já dentro do arquivo. O PDF publicado é que entra na fila e vai
para a tela. O `.cdr` sai do portão e não é apagado: ele é a fonte.

**Arquivo de várias páginas** a tela **mostra e pergunta** — nunca
adivinha. A gravadora não puxa múltiplas páginas, e já houve arquivo que
foi para o CTP com duas páginas dentro: a OS cobrou as chapas certas, a
prova saiu com as duas, e mesmo assim só uma seria gravada.

Quando o resultado forem duas chapas, elas saem numeradas **no fim do
nome**, com dois algarismos. Com uma página só, o nome continua limpo,
sem número.

> **Correção de 18/09/2026.** Este ticket dizia "numeradas **na frente**,
> porque a pasta do CTP é lida em ordem alfabética". Estava errado, e a
> spec não pedia isso — é sobra da primeira versão da regra, de 17/09 de
> manhã, que o operador desfez na mesma tarde: *"cada pagina, num pdf
> diferente, diferenciando no final do nome com _01, _02 e assim por
> diante (...) essa regra vai servir para america tb"*.
>
> O argumento do "na frente" também não se sustenta: as páginas de um
> mesmo trabalho dividem o nome inteiro até o sublinhado, então ficam
> juntas e em ordem de qualquer jeito. Quem espalhava era o número na
> frente, que junta os `01` de trabalhos diferentes e separa as páginas
> do mesmo. E o fim do nome já era o costume da casa — a FIALHO numera
> assim desde sempre. Confirmado com o operador antes de fechar o ticket.

**Blocked by:** 05

**Status:** done

- [x] `.cdr` no portão é publicado pela Corel e entra na fila como PDF
- [x] O `.cdr` sai do portão e não é apagado
- [x] O portão não fica com o `.cdr` e o PDF publicado ao mesmo tempo
- [x] Arquivo de várias páginas é mostrado na fila com o número de
      páginas e pergunta o que fazer, em vez de decidir
- [x] Resultando em mais de uma chapa, elas saem numeradas com dois
      algarismos — **no fim do nome**, ver a correção acima
- [x] Uma página só continua saindo com nome limpo, sem número
- [x] Arquivo aberto no Corel do operador não é convertido: avisa e deixa
      para a próxima passada

**Onde ficou:** `montagem.publicar` e `_publicar_pelo_corel`, o `.cdr` nas
`EXTENSOES` do portão, o botão "Publicar em PDF" na fila e `POST
/publicar`, e a recusa do motor a escolher páginas.

**Publicar não acontece sozinho**, e essa é a decisão que sustenta o
resto. A fila é uma tela que a equipe atualiza à vontade; publicando por
conta própria, um F5 viraria uma sessão do CorelDRAW — e dez F5, dez. O
`.cdr` aparece na fila dizendo que falta publicar, e quem aperta é gente.
É a mesma escolha do montar e do aprovar: o passo caro acontece com
clique. Provado: duas olhadas na fila, zero chamadas à Corel.

**O `.cdr` não se mede** — nem se abre fora do CorelDRAW. Ele volta da
medição dizendo que falta um passo, e **não como erro**: não há nada
errado com ele.

**O motor deixou de escolher página.** No bate-vira ele pegava a 1 e a 2
e seguia calado — as outras sumiam sem ninguém ver. Ele já recusava
adivinhar em "só frente"; era o mesmo chute, sem a mesma recusa. Agora
para e diz quantas páginas há.
