# As skills desta casa, e onde cada uma mora

Há **dois** lugares, e a diferença não é arrumação — ela decide quem
enxerga a skill e se ela tem cópia de segurança.

| onde | quem enxerga | está em git? |
|---|---|---|
| `.claude/skills/` (esta pasta) | **só este projeto** | **sim** — vai junto no repositório |
| `%USERPROFILE%\.claude\skills\` | **todo projeto desta máquina** | **sim** — em repositório PRÓPRIO, o `finart-skills` |

## O que mora aqui

`fechamento-arquivos-ctp`, `gerempre`, `imposicao` — as três são do
ofício de fechar chapa, e não servem a projeto nenhum além deste.

E a `cartographer`, desde **20/09/2026**, que é de fora: é o plugin de
Bootoshi, MIT, trazido para dentro a pedido do operador — *"para quando
eu puxar de lá, já seja instalada lá também"*. Estava só na pasta da
máquina, e ali não tinha cópia de segurança nenhuma; aqui ela chega na
outra máquina no primeiro `git pull`.

**Ela desenha o mapa do código, e o mapa NÃO se versiona** — está no
`.gitignore`. Gere, leia, jogue fora. O porquê, o que foi mudado ao
copiar e as duas armadilhas estão no `cartographer/DE-ONDE-VEIO.md`.

## O que mora na pasta da máquina

`whats_teams_email` e `verificar-efeito`. As duas são **compartilhadas
com o `C:\Finart\AUTOMAÇAO WPP`**, que é outro projeto e precisa andar
junto com este.

A `verificar-efeito` esteve aqui dentro por algumas horas em 17/09/2026
e saiu no mesmo dia, por pedido do operador: ela vai servir de base para
um agente que monitora **como os arquivos chegam na empresa**, e esse
agente nasce do lado do WPP. Dentro deste repositório o WPP não a
enxergava.

Seu conteúdo continua guardado no histórico —
`git show aa90418:.claude/skills/verificar-efeito/SKILL.md` — mas **a
cópia que vale é a da máquina**, e é lá que se edita. Uma skill em dois
lugares envelhece separada, e daqui a um mês ninguém sabe qual vale.

## O buraco fechou — a pasta da máquina TEM backup

Isto aqui dizia, até 21/09/2026, que a pasta da máquina não estava em
git nenhum e que disco que morresse levava as duas skills. **Não é mais
verdade, e não era desde 17/09**: no mesmo dia em que o buraco foi
apontado, ele foi tapado, e esta página ficou para trás.

A pasta `%USERPROFILE%\.claude\skills\` é um repositório próprio:

```
https://github.com/pedrorgb507/finart-skills.git     PRIVADO
```

**Edita-se lá mesmo e faz-se commit lá.** Não há passo de
sincronização e não há cópia aqui dentro — cópia em dois lugares
envelhece separada, que foi exatamente o que se evitou ao tirar a
`verificar-efeito` deste repositório. O `LEIA-ME.md` de lá conta o
resto: o que fica fora do versionamento, por que o remoto é privado, e
o cuidado de que uma regra mudada lá muda o WPP e a FIA na mesma hora.

**O que sobrou de cuidado**, e é outro: o backup existe, mas ele só
alcança o que foi **commitado**. Em 21/09/2026 havia quatro arquivos da
`whats_teams_email` mexidos e não commitados ali. Mexeu numa skill da
máquina? Faça o commit no repositório dela — o hook desta casa não
enxerga aquela pasta.

**E esta lição vale mais que o caso**: a página que avisa de um risco
tem de ser a primeira a saber quando o risco acaba. Quatro dias
dizendo "não há backup" sobre uma pasta que tinha backup é o mesmo
defeito de um aviso que aparece sempre — ensina a não acreditar nele.
