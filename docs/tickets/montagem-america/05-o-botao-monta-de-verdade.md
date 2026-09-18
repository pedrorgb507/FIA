# 05: O botão monta de verdade

**What to build:** O botão do painel deixa de gerar texto para alguém
copiar e passa a **montar**. Quem montou termina o trabalho sozinho.

Tudo que a tela coletou vira uma ordem única, e é ela que manda montar.
A forma da ordem — que codifica as decisões melhor que a prosa:

```
ordem = {
  arquivo, chapa, maquina,
  imagens_frente, imagens_verso,
  colunas, linhas, vao, sangria,
  formato,                # a folha; limite diferente do da chapa
  tipo,                   # frente-verso, bate-vira, só frente
  quem,                   # quem está montando
  maquina_trocada,        # se saiu da regra, e por quê
  liberado_sem_caber,     # preenchido no ticket 06
}
```

A montagem sai na **pasta do dia**, com o sufixo `_MONTAGEM`, e o
original sai do portão sem ser apagado — ele é a fonte da montagem. A
arte é assentada com a marca de corte na pinça da chapa (pela borda do
arquivo quando não houver marca reconhecível), reaproveitando o caminho
que a FIA já tem.

Fica gravado quem montou. É aqui que nasce o registro que os tickets 06,
07 e 08 vão usar.

**Três travas, e nenhuma é formalidade** — todas vêm de erro já pago:

1. **nunca grava na `PARA CTP`** — escrever lá pularia a revisão, e a
   mudança de pasta *é* o aprovado;
2. **a pinça é conferida no arquivo que saiu**, não na conta que foi
   feita: entre escrever a matriz no PDF e ela valer há um programa
   inteiro. Não conferindo, a montagem é apagada e o serviço para;
3. **o portão nunca fica com dois PDFs do mesmo serviço** — a volta
   seguinte do vigia acharia duas chapas, e sairiam duas gravações e
   duas OS.

E o que já para hoje continua parando: arte que só cabe deitada, e arte
que não cabe em chapa nenhuma.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Montar pela tela grava a montagem na pasta do dia com o sufixo
      `_MONTAGEM`
- [ ] O original sai do portão e não é apagado
- [ ] A montagem nunca é gravada na `PARA CTP`
- [ ] A pinça é medida no arquivo que saiu; não conferindo, a montagem é
      apagada e o serviço para
- [ ] O portão não fica com dois PDFs do mesmo serviço
- [ ] Quem montou fica gravado, com data
- [ ] Arte que só cabe deitada para e pergunta; arte que não cabe em
      chapa nenhuma para
- [ ] Montagem já feita não é refeita
- [ ] Teste: a ordem completa executada contra pastas temporárias, com as
      bordas substituídas — do jeito que os fechamentos já são provados
