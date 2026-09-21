# 01: A conta — qual página cai em que lugar

**What to build:** Um módulo que responde uma pergunta só: dado um livro
de N páginas, um processo e um tamanho de caderno, **que página vai em
que lugar de que chapa**. Conta pura — sem Ghostscript, sem CorelDRAW,
sem abrir arquivo —, porque é assim que ela se prova por teste e roda
inteira fora da gráfica.

A dobra vem de **catálogo lido de modelo do Preps**, nunca de fórmula
inventada, e o que não estiver no catálogo **para** em voz alta.

**Blocked by:** None

**Status:** done

- [x] Canoa reparte os cadernos **encaixados**: o de fora leva o começo e
      o fim do livro
- [x] Lombada reparte **empilhados**: cada caderno leva um pedaço seguido
- [x] Folha solta não tem caderno, e o programa diz isso em vez de
      devolver lista vazia
- [x] Cada lugar devolve o **par** frente/verso
- [x] Caderno que não fecha em múltiplo de 4, e sobra de página, **param**
- [x] Dobra que não está no catálogo **para**, dizendo o que conhece e
      onde procurar
- [x] Os nomes das chapas saem como o operador escreve: `caderno 1
      frente`, `caderno 1 verso` — e no bate-vira, `caderno 1` só
- [x] Teste: o arranjo bate com os `.tpl` do Preps, lugar por lugar
- [x] Teste: canoa e lombada dobram igual nos dois tutoriais do Preps
- [x] Teste: todo lugar carrega **uma folha de papel** — as páginas 2i−1
      e 2i

**Onde ficou:** `src/finart_ctp/paginacao.py` e
`tests/test_paginacao.py` (23 testes, cinco deles lendo os `.tpl` de
verdade e pulando quando o Preps não está na máquina).

**A invariante que prende o encaixe inteiro:** um lugar é um pedaço de
papel, e papel tem dois lados que são a **mesma folha do livro** — a
página 2i−1 e a 2i. Errando um caderno no encaixe, algum lugar passa a
juntar páginas de folhas diferentes, e o teste vê na hora. Foi a
conferência mais barata que achei para uma conta que, de outro jeito, só
se prova depois de dobrada e cortada.

**Uma armadilha de leitura, que custou a primeira rodada dos testes:** o
Preps grava os lugares na ordem do PostScript, em que o **y cresce para
cima** — a fileira de baixo vem primeiro no arquivo. O catálogo conta a
linha de cima para baixo, que é a ordem em que se lê uma tabela. Nenhuma
das duas está errada, e comparar sem ordenar acusava diferença onde não
havia. Compara-se **por posição**.

**De onde vieram os arranjos:** dos modelos de **exemplo** do Preps, que
é o que a bancada tem (58 numa pasta só). Os 2020 da casa estão na
máquina da gráfica — ver o ticket 05.
