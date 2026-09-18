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

**Status:** done

- [x] A `PARA MONTAR` é reconhecida dentro da pasta do dia da AMÉRICA, do
      mesmo jeito que a `PARA CTP`
- [x] Um comando lista o que está esperando montagem, sem escrever nada
- [x] Arquivo que ainda está sendo copiado não aparece na lista, e
      aparece na volta seguinte quando termina de chegar
- [x] Arquivo já montado antes não aparece na lista
- [x] A pasta do dia, fora do portão, continua intocada
- [x] Teste: portão com arquivo estável, arquivo chegando e arquivo já
      registrado devolve só o primeiro

**Onde ficou:** `src/finart_ctp/montagem.py` — o módulo que a spec pediu
—, `SUBPASTA_PARA_MONTAR` no config, `ferramentas/montar_america.py` para
conferir a fila de dentro da máquina, e `tests/test_montagem.py`.

O registro da montagem (`_montagens.json`) nasceu aqui, com as duas
metades: `carregar_montagens` / `ja_montado`, que é do que esta fila
precisa, e `anotar_montagem`, para o 05 chamar quando a montagem for
gravada de verdade. Sem quem escreve, o "não refaz" não teria como ser
provado de ponta a ponta.

O portão NÃO é criado sozinho, igual ao da `PARA CTP` da AMÉRICA: quem
põe arquivo nele é gente, e a pasta do dia fica intocada. Portão que
ainda não existe devolve fila vazia, e não erro.
