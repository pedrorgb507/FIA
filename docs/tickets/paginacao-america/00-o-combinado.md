# 00: Os três processos de montagem da AMÉRICA — o combinado

Ditado pelo operador em **20/09/2026**, e é daqui que os tickets desta
pasta saem:

> *"a américa usa os 3 tipos de montagem: **folha solta**, que seriam
> arquivos com poucas páginas, para montagens quase sempre com 1 formato
> bate-vira ou 1 formato frente e verso; outra montagem que a américa
> usa, e geralmente para livros e revistas, é o formato **canoa**
> (saddle-stitched), nesse formato monto vários livros, com a definição
> escrita de cada caderno (caderno 1 frente / caderno 1 verso); e a
> américa também usa o processo de montagem **HOT-MELT, lombada**
> (perfect-bound), onde os livros ou revistas têm uma quantidade de
> páginas maiores, e precisa desse processo para colar as páginas na
> capa."*

| processo | quando | os cadernos |
|---|---|---|
| **folha solta** | poucas páginas | não há caderno — cada página é uma peça |
| **canoa** (saddle-stitched) | livro e revista | **encaixados** um dentro do outro |
| **lombada** (hot-melt, perfect-bound) | livro grande | **empilhados** lado a lado |

## O que a leitura do Preps já provou

Feita em 20/09/2026 na bancada, com `ferramentas/ler_paginacao_preps.py`:

- **um lugar tem duas páginas** — a da frente e a do verso do mesmo
  pedaço de papel. A montagem do verso não é uma segunda conta;
- **canoa e lombada dobram IGUAL dentro do caderno.** Os dois tutoriais
  do Preps trazem o caderno de 16 com a paginação idêntica, lugar por
  lugar. O que muda é só como as páginas do livro são repartidas entre
  os cadernos, e a marca de colação;
- **não há uma dobra só por número de páginas** — o `A4 Multi.tpl` traz
  outro arranjo de 16. Então a dobra é **catálogo lido**, não fórmula;
- a folha diz **como ela vira** (5º campo do `%SSiPressSheet`: 0 frente e
  verso, 1 bate-vira, 3 só frente) e **qual é a pinça** (6º campo).

O texto longo, com os números, está na skill `imposicao` —
*"Os três processos da AMÉRICA"* e `references/preps.md`.

## A ordem dos tickets, e por que ela é essa

De baixo para cima: primeiro a **conta** (não depende de máquina
nenhuma e roda inteira na bancada), depois o **desenho**, depois as
**marcas**, depois a **tela**. O catálogo de dobras da casa e a fuga da
canoa andam por fora, porque dependem da máquina da gráfica e de
resposta do operador.

| | |
|---|---|
| 01 | a conta: qual página cai em que lugar — **done** |
| 02 | o desenho: montar um caderno paginado na chapa |
| 03 | as marcas de colação — a escadinha da lombada |
| 04 | o painel: escolher processo, caderno e ver o livro inteiro |
| 05 | o catálogo de dobras da casa, lido dos 2020 modelos |
| 06 | a fuga da canoa (*creep*) — **esperando o operador** |
