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

**Status:** done

- [x] A montagem gravada aparece numa lista de "esperando revisão"
- [x] Aprovar exige identificar quem está aprovando
- [x] Aprovada, a montagem vai para a `PARA CTP` e o nome fica gravado
- [x] Nada vai para a `PARA CTP` sem alguém ter clicado
- [x] A cópia na pasta do dia continua existindo depois de aprovar
- [x] O vigia de hoje pega a montagem na `PARA CTP` e segue o fluxo
      normal, sem saber que veio daqui
- [x] Teste: aprovar move o arquivo e grava quem; sem aprovação o
      arquivo fica onde está

**Onde ficou:** `montagem.esperando_revisao` e `montagem.aprovar` (a
lógica), o segundo bloco da tela da fila e `POST /aprovar` (a casca).

**Copia, e não move**, e isso não é detalhe: o vigia *apaga* da `PARA
CTP` depois de gravar a chapa, e ele só pode fazer isso porque a cópia da
casa fica na pasta do dia. Movendo, a montagem sumiria justamente depois
de virar chapa — e ela é o que se olha quando alguém pergunta o que foi
para a gravadora.

**A lista olha a pasta, não só o registro.** O operador monta no
CorelDRAW e salva o `_MONTAGEM` na pasta do dia — é assim que a casa
sempre fez, e continua valendo. Listando só o que a FIA fez, a tela
mentiria sobre o que falta revisar. Essas aparecem dizendo "montada fora
da tela" e podem ser aprovadas do mesmo jeito.

**Sai da lista o que já está na `PARA CTP`**, mesmo tendo sido arrastado
à mão — pedir que o operador aprove de novo seria a tela não enxergar o
que ele acabou de fazer.

**Quem revisa vê os avisos antes de aprovar:** máquina trocada fora da
regra, e montagem liberada sem caber com o nome de quem liberou e o
motivo. Depois de aprovar vira chapa.

O ciclo inteiro foi provado de ponta a ponta: montar → esperar revisão →
aprovar → o vigia achando na `PARA CTP`.
