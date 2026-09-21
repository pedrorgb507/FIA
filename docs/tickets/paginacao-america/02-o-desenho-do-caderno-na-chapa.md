# 02: O desenho — pôr um caderno paginado na chapa

**What to build:** Hoje o `montar_bate_vira.montar()` monta uma grade de
uma peça repetida (ou de frente e verso). Ele passa a aceitar um
**caderno paginado** — a lista de lugares que o `paginacao.py` devolve —
e a pôr em cada célula a **página que aquele lugar pede**, no giro que o
arranjo manda.

Tudo o que a montagem já sabe fazer continua valendo, e sem exceção: a
sangria pela regra do vão, a pinça medida até a marca de corte, as
marcas de corte nos quatro lados, o registro nos dois lados, a escala de
cor de pé, a conferência da pinça no arquivo que saiu.

O que ele ganha é só isto: **qual página vai em cada célula**, e que a
saída passa a ser **um arquivo por caderno e por lado**.

**Blocked by:** 01

**Status:** todo

- [ ] `montar()` aceita os lugares de um caderno (célula, giro, frente,
      verso) em vez de supor a peça repetida
- [ ] Uma página local que não existe (o `0` do Preps) sai como célula
      vazia — não se inventa página em branco
- [ ] A saída sai nomeada por caderno e lado, com o nome que o operador
      escreve (`caderno 1 frente`)
- [ ] Bate-vira continua saindo em **uma** chapa por caderno; frente e
      verso, em duas
- [ ] A pinça continua sendo conferida no arquivo que saiu, caderno por
      caderno — a conta acontece numa matriz escrita no PDF, e que ela
      tenha valido se mede no arquivo
- [ ] A montagem continua **sem escrever na `PARA CTP`** — a trava do
      portão vale igual para caderno
- [ ] Teste: um livro de 16 páginas em canoa sai com as páginas certas em
      cada célula, medidas no PDF que saiu
- [ ] Teste: o mesmo livro em lombada sai igual (a dobra é a mesma), e em
      32 páginas sai **diferente** (o encaixe muda)

**O que decide se isto está certo:** não é o relatório, é o **pixel**. A
mesma lição da pinça — o que se escreve numa matriz do PDF e o que
aparece na chapa são duas coisas, e entre uma e outra há um programa
inteiro. Rasterizar e conferir custa segundos e não tem como mentir.
