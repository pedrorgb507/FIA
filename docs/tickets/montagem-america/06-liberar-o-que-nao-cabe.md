# 06: Liberar o que não cabe, com nome

**What to build:** O painel já tem o *"dar andamento assim mesmo"*, que
destrava a montagem que não cabe. Agora ele passa a gravar **quem**
liberou.

Foi decisão do operador que isso seja fechado na equipe: qualquer um
pode liberar, e o caso **não sobe para ele**. Quem recebe o papel
continua sabendo que foi decisão de alguém, porque a ordem sai dizendo
isso — o que muda é que agora diz de quem.

A marca continua caindo a cada mudança: um "pode ir" dado para uma
montagem não vale para a seguinte.

Os dois limites são diferentes e o aviso precisa continuar dizendo qual
estourou: **área útil** é da chapa, o que a gravadora alcança tirada a
pinça; **formato** é da folha, o que a impressora pega.

**Blocked by:** 05

**Status:** done

- [x] Liberar uma montagem que não cabe exige identificar quem está
      liberando
- [x] A liberação fica gravada no registro, com o motivo do não-caber
- [x] A ordem gerada diz que foi liberada à mão e por quem
- [x] O aviso continua dizendo qual dos dois limites estourou
- [x] A liberação cai quando qualquer campo da montagem muda
- [x] O caso não gera pendência para o operador — é decisão fechada da
      equipe
- [x] Teste: montagem que estoura a área útil e montagem que estoura o
      formato, liberadas, aparecem no registro com nome e motivo

**Onde ficou:** o motor passou a devolver os `estouros` inteiros,
`montagem.executar` grava `liberado_por` e `liberado_porque`, a ordem em
texto do painel diz por quem, e quatro casos novos no provador.

**O que marca não é o pedido, é o que aconteceu.** A tela manda
`liberado_sem_caber` junto com a ordem, mas quem sabe se a montagem
estourou de verdade é o motor, que mediu. Marcando pelo pedido, uma
montagem que cabia sairia no histórico como liberada — e o histórico
existe justamente para separar os casos que ensinam dos que não ensinam
nada.

**O motivo vem com número**, e sai do motor:

```
nao cabe no UTIL DA CHAPA: a montagem da 805.0 x 300.0 e o util e
525.0 x 399.0 (chapa 525 x 459 menos a pinca 60)
nao cabe no FORMATO 4: a montagem da 805.0 x 300.0 e a area util da
folha e 315 x 460 (folha 330 x 480)
```

"Não coube" sozinho não ensinaria nada a quem for olhar o histórico
depois — e é de lá que a próxima regra da casa nasce.

**Não vira pendência e não grita**, que é a decisão do operador contra a
recomendação de escalar. A linha do dia conta o que houve; o histórico
guarda o nome. Ele escolhe quando olhar, em vez de ser interrompido.
