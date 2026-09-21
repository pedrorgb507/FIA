# As skills desta casa, e onde cada uma mora

Há **dois** lugares, e a diferença não é arrumação — ela decide quem
enxerga a skill e se ela tem cópia de segurança.

| onde | quem enxerga | está em git? |
|---|---|---|
| `.claude/skills/` (esta pasta) | **só este projeto** | **sim** — vai junto no repositório |
| `%USERPROFILE%\.claude\skills\` | **todo projeto desta máquina** | **não** |

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

## O buraco que fica, e é conhecido

**A pasta da máquina não está em git nenhum.** Nem a `whats_teams_email`,
nem a `verificar-efeito`. Disco que morrer leva as duas.

Isso foi dito ao operador em 17/09/2026 e continua aberto. A saída limpa
é um repositório só para as skills compartilhadas, que os dois projetos
puxam — meia hora de trabalho, e resolve para sempre.
