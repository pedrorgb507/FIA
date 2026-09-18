# 08: A tela de histórico

**What to build:** O operador tirou o caso difícil do caminho dele — a
equipe decide sozinha. Então ele precisa de um lugar onde **escolhe**
olhar, em vez de ser interrompido.

Uma tela que mostra a semana: cada montagem, quem montou, quem aprovou,
quem trocou a máquina fora da regra e por quê, e o que foi liberado sem
caber.

Não é burocracia. Máquina trocada fora da regra é onde a regra da casa
não cobre a realidade — e é daí que sai a próxima regra. Montagem
liberada sem caber é o caso que ninguém previu.

**Blocked by:** 05, 06, 07

**Status:** done

- [x] A tela lista as montagens do período, da mais recente para a mais
      antiga
- [x] Cada linha mostra quem montou e quem aprovou
- [x] Máquina trocada fora da regra aparece destacada, com o motivo
- [x] Montagem liberada sem caber aparece destacada, com o limite que
      estourou
- [x] Dá para olhar um dia específico, não só a semana
- [x] A tela só lê: não altera nem apaga registro nenhum

**Onde ficou:** `montagem.historico(dias=7, dia=None)` e
`servidor.pagina_do_historico`, em `/historico`. A fila aponta para ela
no rodapé; ela aponta de volta para a fila.

**O topo conta os casos que ensinam**, e não o total de montagens: máquina
trocada fora da regra, liberadas sem caber, e ainda não aprovadas. Uma
tela que só diz "foram 34 montagens" não serviria para o que ela existe.

**A data se ordena como data**, e não como texto. O `quando` é escrito
`dd/mm/aaaa` porque é para gente ler; ordenado como texto, `09/10` viria
antes de `17/09` e o histórico mostraria o mês errado no topo sem
ninguém entender por quê.

**Entrada com data ilegível não some da lista** — registro escrito à mão,
ou de uma versão anterior. Vai para o fim, porque não dá para saber
quando foi, mas aparece: são justamente as que alguém tem de ver.

**Não precisa da pasta do dia.** Lê o registro, que fica no PC da FIA —
o operador olha com o `V:` fora do ar e continua vendo o que a equipe
decidiu.

Há teste que lê a fonte e reprova se `historico` ou `pagina_do_historico`
ganharem qualquer escrita — um botão que apaga, no lugar onde se procura
o que deu errado, é o jeito mais rápido de perder o que ensina.
