# 04: O painel — escolher o processo e ver o livro inteiro antes de gravar

**What to build:** O painel de ordem de montagem hoje pensa em **peças**:
quantas imagens na frente, quantas no verso, colunas × linhas. Ele passa
a pensar também em **livro**: processo, páginas do livro, páginas por
caderno — e mostra, antes de existir arquivo, **quantos cadernos e
quantas chapas** aquilo vira, com o nome de cada uma.

A ideia que sustenta o painel continua a mesma: **o formulário é a
chapa.** Escolhido o processo, o diagrama passa a desenhar o caderno com
o número da página em cada célula, como o operador vai ver na chapa.

**Blocked by:** 02

**Status:** todo

- [ ] Um seletor de processo: folha solta · canoa · lombada
- [ ] Em folha solta, o painel continua **exatamente** como é hoje —
      quem monta poucas páginas não pode pagar pela mudança
- [ ] Em canoa e lombada: páginas do livro e páginas por caderno
- [ ] O diagrama mostra **o número da página em cada célula**
- [ ] A lista de chapas sai com os nomes (`caderno 1 frente`, …) e o
      total — é o que o operador confere antes de mandar
- [ ] Páginas que não fecham em caderno **avisam** e dizem quanto sobra;
      quem decide o que fazer com a sobra é gente
- [ ] Canoa de mais de um caderno avisa da **fuga** enquanto o ticket 06
      estiver aberto
- [ ] Os avisos que já travam o botão (não cabe na área útil, não cabe no
      formato) continuam travando, e por caderno
- [ ] Provado pelo `ferramentas/provar_painel.py`, no Edge sem tela

**Sem abas**, como já ficou combinado em 10/09/2026: aba esconde, e aqui
toda escolha muda o desenho — esconder faria decidir sem ver a
consequência.

**E o painel continua não decidindo.** Ele lê, desenha e avisa. Qual
processo, quantas páginas por caderno e o que fazer com a sobra são de
quem vai rodar.
