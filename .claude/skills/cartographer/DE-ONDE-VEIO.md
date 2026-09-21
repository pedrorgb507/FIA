# A cartographer, e por que ela mora aqui dentro

Ela **não é desta casa**. É o plugin `cartographer`, versão **1.4.0**, de
**Bootoshi** (<https://github.com/kingbootoshi/cartographer>), sob
licença **MIT** — a `LICENSE` ao lado é a dele, e vai junto porque a MIT
pede isso de quem redistribui.

## Por que ela foi trazida para dentro do repositório

Pedido do operador em **20/09/2026**: *"salva a skill `/cartographer`
nesse projeto, para quando eu puxar de lá, já seja instalada lá
também"*.

Ela estava instalada só **nesta máquina**, na pasta de plugins do
usuário — que não está em git nenhum. Dentro de `.claude/skills/` ela
vai no repositório e aparece sozinha na outra máquina no primeiro
`git pull`, que é a regra escrita no `LEIA-ME.md` desta pasta.

É o mesmo buraco que o `LEIA-ME.md` aponta para a `whats_teams_email` e
a `verificar-efeito`: skill que mora só na máquina, disco que morrer
leva junto. Esta saiu do buraco.

## O que foi mudado ao copiar, e só isso

Uma coisa: os **caminhos do scanner**. Como plugin, a SKILL.md os
escrevia com `${CLAUDE_PLUGIN_ROOT}`, que **não existe** para uma skill
de projeto — os três comandos falhariam sem dizer por quê. Agora estão
relativos ao repositório:

    .claude/skills/cartographer/scripts/scan-codebase.py

O resto do texto é o do autor, palavra por palavra.

## Como rodar nesta casa (as duas máquinas são Windows)

**Use a opção 1, o `uv`** — medido em 20/09/2026 nesta máquina: ele
instalou as 7 dependências (o `tiktoken` entre elas) em **302 ms**, num
ambiente isolado, e o scanner devolveu 166 arquivos e 702.823 tokens.

```
uv run .claude/skills/cartographer/scripts/scan-codebase.py . --format json
```

As outras duas opções da SKILL.md são piores aqui: o `.venv` do projeto
**não tem tiktoken** (e não deve ter — não é dependência da FIA), e o
`python3` do PATH é o atalho da Microsoft Store.

## DUAS COISAS PARA NÃO FAZER, e as duas custam

**1. NÃO COMMITE O MAPA.** Decidido em 20/09/2026, e a razão é a da casa:
*uma folha escrita em dois lugares é uma medida errada esperando a hora*.
O mapa descreve o que já se lê no código, e envelhece calado — o de
18/09 tinha **dois dias** e já não sabia do `paginacao.py`, do leitor do
Preps nem da bancada. Ninguém percebeu, porque mapa errado não dá erro
em lugar nenhum.

O `docs/CODEBASE_MAP.md` está no `.gitignore` justamente para isso não
voltar por descuido. **Gere, leia, jogue fora.** O uso certo dele é
alguém — pessoa ou agente — se orientar numa área que não conhece.

O que **não** se lê no código (por que a regra existe, que incidente a
causou, que número foi medido) mora nas skills e nos comentários, e é
essa metade que importa.

**2. CUIDADO COM O PASSO 7 DA SKILL.** Ele manda *"atualizar o
`CLAUDE.md` com um resumo apontando para o mapa"*. O `CLAUDE.md` desta
casa é **escrito à mão** e ensina a trabalhar aqui — produção, travas,
sincronismo entre as duas máquinas, estilo. Ele não é resumo de
arquitetura, e **não aponta para o mapa de propósito**.

Deixe-o em paz. Se um dia o mapa merecer uma linha lá, ela se escreve à
mão, como o resto do arquivo.

## Para atualizar a skill

Quando sair versão nova do plugin, copie por cima **refazendo a troca
dos caminhos** — e reveja esta nota. A versão que está aqui é a 1.4.0.
