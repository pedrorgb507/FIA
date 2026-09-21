# 03: As marcas de colação — a escadinha que denuncia caderno trocado

**What to build:** A marca preta na dobra de cada caderno que **anda um
degrau a cada caderno**. Empilhados os cadernos, as marcas formam uma
escadinha contínua na lombada: faltando um caderno, ou dois trocados de
lugar, a escada quebra e **se vê de longe, antes de colar**.

É a única conferência de ordem de caderno que funciona com o livro
fechado.

**Blocked by:** 02

**Status:** todo

- [ ] A marca sai na dobra do caderno, no lugar que o estilo manda
- [ ] Ela **anda um passo por caderno** (o `stepsize` do Preps)
- [ ] A de **lombada** só sai em lombada; a de **canoa** só sai em canoa
- [ ] Livro de um caderno só não leva marca de colação — não há ordem a
      conferir
- [ ] Teste: oito cadernos dão oito marcas em oito alturas diferentes, e
      nenhuma se repete

**A regra vem do próprio Preps**, escrita no `INFO.SMG` do grupo de
marcas de exemplo:

> *"The Perfect Bound collation mark will appear only on a perfect bound
> signature between the highest and lowest numbered pages. The
> Saddle-Stitch collation mark will only appear on a saddle-stitch
> signature, at the head of the low page."*

Ou seja: **a marca conhece o estilo de encadernação e se recusa a sair
no errado.** Não é decoração — é a marca dizendo "este caderno é de
lombada", e sair a de canoa numa lombada seria dar ao conferidor uma
escada que não significa nada.

Os números do exemplo do Preps: passo de **6,35 mm**, com `collstart` e
`collsize` dizendo onde a escada começa e quanto ela ocupa. **Os da casa
saem dos 2020 modelos** — ticket 05.
