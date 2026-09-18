# 07: A revisão — aprovar e mandar para a `PARA CTP`

**What to build:** A montagem gravada na pasta do dia precisa de olho
humano antes de virar chapa. Hoje isso é o operador arrastando o arquivo;
passa a ser qualquer um da equipe, num clique, com o nome gravado.

Quem revisou abre a montagem, confere e aprova. O sistema move para a
`PARA CTP` e grava quem aprovou. Dali em diante o vigia de hoje assume:
OS, prova, chapa no CTP.

**A revisão continua humana** — o que muda é quem pode fazê-la. O sistema
nunca move nada por conta própria; ele move porque uma pessoa clicou, e é
justamente esse clique que permite saber quem aprovou. Quando sair chapa
errada, saber quem viu é como a regra nasce.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] A montagem gravada aparece numa lista de "esperando revisão"
- [ ] Aprovar exige identificar quem está aprovando
- [ ] Aprovada, a montagem vai para a `PARA CTP` e o nome fica gravado
- [ ] Nada vai para a `PARA CTP` sem alguém ter clicado
- [ ] A cópia na pasta do dia continua existindo depois de aprovar
- [ ] O vigia de hoje pega a montagem na `PARA CTP` e segue o fluxo
      normal, sem saber que veio daqui
- [ ] Teste: aprovar move o arquivo e grava quem; sem aprovação o
      arquivo fica onde está
