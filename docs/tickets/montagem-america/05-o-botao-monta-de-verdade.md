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

**Status:** done

- [x] Montar pela tela grava a montagem na pasta do dia com o sufixo
      `_MONTAGEM`
- [x] O original sai do portão e não é apagado
- [x] A montagem nunca é gravada na `PARA CTP`
- [x] A pinça é medida no arquivo que saiu; não conferindo, a montagem é
      apagada e o serviço para
- [x] O portão não fica com dois PDFs do mesmo serviço
- [x] Quem montou fica gravado, com data
- [x] Arte que só cabe deitada para e pergunta; arte que não cabe em
      chapa nenhuma para
- [x] Montagem já feita não é refeita
- [x] Teste: a ordem completa executada contra pastas temporárias, com as
      bordas substituídas — do jeito que os fechamentos já são provados

**Onde ficou:** `montagem.executar(ordem)` — a função que recebe a ordem
e faz o trabalho —, `POST /montar` no servidor (casca fina), o
`ordemObjeto()` e o botão no painel, e o campo de quem está montando.

**Provado de ponta a ponta** com o motor de imposição de verdade: a
montagem saiu 525x459 na pasta do dia, a pinça foi conferida **no arquivo
que saiu** (desenho a 57,6 mm do pé, pinça 60), o original saiu do portão
guardado, a `PARA CTP` ficou vazia, e pedir de novo recusa. 3,8 s.

**O motor não foi reescrito** — ele já existe, já assenta a peça deitada
em cada célula, gira a metade do verso no bate-vira, desenha as marcas
com os EPS da casa, e tem prova própria que confere o pixel de cada
célula. Ele ganhou um parâmetro: a sangria pode vir da ordem, porque o
painel deixa digitá-la.

**Dívida conhecida:** o motor mora em `ferramentas/` e `src` não devia
importar de lá. Não mudou de casa junto com este ticket de propósito —
são mil linhas do caminho mais caro da casa, e movê-las no mesmo commit
que liga o botão juntaria dois riscos que não precisam andar juntos.

**O nome de quem monta** é lembrado no navegador (`localStorage`): digita
uma vez por PC. Não é login — é a mesma escolha de não ter senha, sem
reescrever o nome a cada montagem.
