# FIA — o que você precisa saber antes de mexer

Automação do fechamento de chapa da Finart. A FIA vigia as pastas dos
clientes, confere a arte, imprime a prova, abre a OS no GEREMPRE e entrega
a chapa no CTP.

O `FIA.md` conta **o que ela faz**, para gente. Este arquivo conta **como
trabalhar nela**.

---

## ISTO É PRODUÇÃO. Escrever mexe em estoque de verdade.

Não é ambiente de teste com cara de produção — é a gráfica funcionando.

- **o `config_local.py` desta máquina aponta para o GEREMPRE de verdade**,
  que desde 25/09/2026 mora **nesta própria máquina, o EUDSON-PC**, e a
  FIA é o funcionário 32. Cada OS aberta dá **baixa de
  chapa no estoque, na hora**;
- **a pasta do CTP é a prova de que a chapa saiu.** Arquivo apagado de lá
  é decisão de gente, nunca sua;
- o `config_local.py` **não está no git**. A mesma linha de código faz
  coisas diferentes em máquinas diferentes — confira em qual banco você
  está antes de rodar qualquer coisa que escreva.

**Nunca rode um script solto que passe pelo `_os_do_arquivo`.** A trava
dos testes mora no `tests/conftest.py` e **só protege quem roda por
`pytest`**. Um `python algo.py` para depurar importa o `config_local.py`
inteiro e escreve no banco de verdade. Já aconteceu duas vezes, e a
segunda foi depurando justamente esta armadilha.

---

## As skills são a documentação de verdade

Não estão aqui por organização: é nelas que mora o ofício, com o caso
real e o preço pago atrás de cada regra. **Leia antes de mexer na área.**

| skill | quando |
|---|---|
| `fechamento-arquivos-ctp` | o caminho da arte até a chapa, os clientes, cor, resolução, as armadilhas |
| `gerempre` | qualquer coisa que toque o banco: OS, vaga, estoque, razão |
| `imposicao` | montagem, sangria, pinça, paginação, AMÉRICA, Preps |

Há mais em `.claude/skills/` — veja o `LEIA-ME.md` de lá, inclusive sobre
duas skills que moram **fora** do repositório, na pasta da máquina.

Especificações e tickets: `docs/specs/` e `docs/tickets/`.

---

## Os dois programas, e são separados de propósito

```
run_ctp.py         o vigia: varre as pastas dos clientes e fecha chapa
run_montagem.py    a fila da montagem da AMÉRICA, no navegador (8787)
```

Um cair não derruba o outro. Os dois sobem sozinhos ao abrir a pasta no
VS Code (`.vscode/tasks.json`, `runOn: folderOpen`).

O vigia **avisa na janela quando o código mudou no disco** e segue com a
versão antiga até alguém reiniciar. Mudou config ou módulo? Pare e suba
de novo, senão você testa o que não mexeu.

---

## Testes

```
.venv/Scripts/python.exe -m pytest -q
```

Mais de mil, e passam todos. **Teste que falha é trabalho não terminado**
— não commite por cima.

Boa parte deles guarda um caso de produção que custou caro, e o docstring
conta qual. Ao mudar um comportamento, o teste que quebra costuma estar
te dizendo por que aquilo era assim; leia antes de ajustar o número.

---

## Duas máquinas, um repositório

Este projeto é usado daqui e de um notebook. Dois hooks cuidam disso,
em `.claude/settings.json`:

- `puxar_do_github.sh` **no começo da sessão** — traz o que a outra
  máquina fez;
- `salvar_no_github.sh` **no fim de cada resposta** — empurra o que está
  commitado.

Sincronizar é mão dupla. Já houve um lado 124 commits atrás do outro
porque só um empurrava.

**Divergência não se resolve sozinha.** Havendo conflito, o hook desfaz o
rebase e chama gente — junte o histórico à mão, olhando o que cada lado
quis dizer. E trabalho sem commit no disco **segura** o pull: rebase por
cima do que não está salvo é a forma mais fácil de perder o dia de
alguém.

---

## Como se escreve aqui

**Comentário explica POR QUE, não o quê.** A casa toda é assim: cada
trava tem escrito atrás dela o caso que a criou, com data e número
medido. É isso que impede alguém — inclusive você, daqui a um mês — de
"simplificar" uma regra que existe por um motivo caro.

- **português**, e o tom é de quem conta o caso, não de manual;
- **código e comentário em ASCII, sem acento**; `.md` com acento normal;
- mensagem de commit no mesmo espírito: o título diz a mudança, o corpo
  diz o que se aprendeu e o que se perdeu. Veja `git log` para o tom;
- **número medido vale mais que estimativa.** Quase toda constante deste
  projeto tem, no comentário, de onde o número saiu.

---

## O BANCO NÃO SE TOCA SEM O OPERADOR AUTORIZAR

Regra dita por ele em **21/09/2026**, no dia em que a FIA ganhou
administrador no SERVIDOR: *"vc não mexe no banco de dados a não ser
que eu autorize"*.

**Vale para qualquer coisa que escreva no GEREMPRE por fora do caminho
normal** — `gfix`, `gbak`, varredura, intervalo de varredura, `UPDATE`
solto, parar ou subir o Firebird, mexer no arquivo do banco. Pedir
primeiro, com o comando escrito na frente dele, e esperar o sim.

O que **continua livre**: ler. Cabeçalho, log, razão, consulta — ler é
o que encontra causa, e ler não quebra nada.

E o que a FIA faz **no trabalho dela** segue normal: abrir e completar
OS pelo `processador`, que é o caminho combinado e coberto de teste.
A regra é sobre mexer no banco **como administrador**, não sobre ela
trabalhar.

**Por que isto virou regra agora.** Até 21/09 ela não conseguia: o
servidor recusava. Com o WinRM ligado, a distância entre uma ideia
minha e o inventário da empresa passou a ser um comando — e este banco
tem **página corrompida e não aceita `gbak`**, ou seja, **não tem
restauração**. Engano ali não é queda, é o fim do registro da empresa.
Some-se a isso que eu errei o diagnóstico desta mesma queda duas vezes
na mesma semana, e a conta fecha: quem tem o poder e já errou é
exatamente quem precisa parar para perguntar.

## O que não se faz

- **não afrouxe uma trava sem o operador pedir.** Várias existem porque
  alguém pagou por elas. As listas de exceção (`CLIENTES_SEM_TRAVA_*`)
  crescem **um cliente de cada vez**, e só quando ele disser;
- **não mexa em pasta de cliente** além do combinado em cada protocolo;
- **não invente convenção de nome de arquivo.** Nome de chapa é
  combinado da casa, e quem decide é quem grava;
- **não apague nada do CTP nem do GEREMPRE** por conta própria;
- **não mexa no banco sem autorização** — a seção acima, e é a mais
  cara de todas.
