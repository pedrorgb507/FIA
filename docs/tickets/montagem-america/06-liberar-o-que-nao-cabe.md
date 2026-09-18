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

**Status:** ready-for-agent

- [ ] Liberar uma montagem que não cabe exige identificar quem está
      liberando
- [ ] A liberação fica gravada no registro, com o motivo do não-caber
- [ ] A ordem gerada diz que foi liberada à mão e por quem
- [ ] O aviso continua dizendo qual dos dois limites estourou
- [ ] A liberação cai quando qualquer campo da montagem muda
- [ ] O caso não gera pendência para o operador — é decisão fechada da
      equipe
- [ ] Teste: montagem que estoura a área útil e montagem que estoura o
      formato, liberadas, aparecem no registro com nome e motivo
