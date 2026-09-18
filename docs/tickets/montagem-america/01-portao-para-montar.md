# 01: O portão `PARA MONTAR` existe, e a FIA diz o que está nele

**What to build:** A AMÉRICA passa a ter um segundo portão, irmão da
`PARA CTP` que a casa já conhece: a `PARA MONTAR`, dentro da pasta do
dia. O que está nele é o que falta montar — e o portão se lê sozinho,
sem ninguém precisar perguntar "esse já foi?".

Um comando de conferência mostra o que está esperando. Ele não monta
nada e não escreve nada: é o `--olhar` que a casa já usa no portão da
`PARA CTP`.

Arquivo que ainda está chegando pela rede não entra na lista — uma
montagem tem megabytes, e ler pela metade daria medida errada. Arquivo
que já foi montado antes também não: pergunta-se ao registro antes.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A `PARA MONTAR` é reconhecida dentro da pasta do dia da AMÉRICA, do
      mesmo jeito que a `PARA CTP`
- [ ] Um comando lista o que está esperando montagem, sem escrever nada
- [ ] Arquivo que ainda está sendo copiado não aparece na lista, e
      aparece na volta seguinte quando termina de chegar
- [ ] Arquivo já montado antes não aparece na lista
- [ ] A pasta do dia, fora do portão, continua intocada
- [ ] Teste: portão com arquivo estável, arquivo chegando e arquivo já
      registrado devolve só o primeiro
