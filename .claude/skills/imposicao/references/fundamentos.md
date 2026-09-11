# Imposição: os fundamentos, e de onde eles vêm

Pesquisado em 10/09/2026, a pedido do operador. Aqui está o que a
literatura e a indústria dizem — separado do que é regra **desta casa**,
que mora no `SKILL.md`. Quando os dois discordam, quem manda é a casa,
mas a discordância fica anotada.

## Os estilos de trabalho (work styles)

É o vocabulário que todo software de imposição usa, e é onde a nossa
confusão morava.

| estilo | como a folha vira | a pinça | onde a montagem se divide | chapas |
|---|---|---|---|---|
| **Frente e verso** (sheetwise) | não vira: são duas chapas | mesma borda | não se divide | 2 jogos |
| **Vira sobre o eixo** (work-and-turn) | gira no eixo **vertical** | **continua a mesma borda** | no **centro vertical** | 1 jogo |
| **Vira pelo pé** (work-and-tumble) | gira no eixo **horizontal**, de cabeça para baixo | **muda para a borda oposta** | no **centro horizontal** | 1 jogo |

As duas últimas põem a frente numa metade da chapa e o verso na outra —
uma chapa só imprime os dois lados, e a folha passa duas vezes. Em
português a família toda é o **tira e retira**: frente e verso saem na
mesma face do papel, e a folha é cortada ao meio no fim.

**O vira sobre o eixo é o preferido**, e por duas razões concretas:
gasta **uma pinça em vez de duas** (a borda que a máquina segura é sempre
a mesma), e o registro sai melhor, porque a **guia lateral também não
muda** entre as passadas. No vira pelo pé, as duas bordas opostas
precisam de margem de pinça, e qualquer diferença de esquadro do papel
aparece como erro de registro.

### A montagem sai SEMPRE deitada na chapa

Antes de qualquer conta de encaixe, esta regra: **o lado maior da
montagem atravessa a chapa**, paralelo à pinça.

Não é aproveitamento — é **máquina**. A borda **longa** da folha é a que
entra na pinça, e a montagem tem de acompanhar. Uma montagem em pé numa
chapa grande **caberia**: as 4 peças de 150 × 210 dão 305 × 425, e na
SM 74 sobram 745 × 543 depois da pinça — entra folgado. E ainda assim
estaria **errada**, porque o papel não entra assim.

Palavras do operador, 11/09/2026: *"no caso do formato 4, se fosse rodar
na máquina grande, SM ou MOZP, estaria errado o jeito de colocar na
chapa, mesmo cabendo em pé; tem que ser deitada, pelo motivo do jeito
que o papel entra na impressora"*.

→ Então o giro **não se decide tentando encaixar**. Ele sai da forma da
montagem: gira 90° quando ela nasce mais alta que larga, e não gira
quando já nasce deitada. Um programa que tenta "em pé primeiro, deita se
não couber" acerta na chapa pequena por acidente e erra na grande.

### O giro que o tombo exige — e por que sai −90 / +90

Quando a folha é **tombada** (vira de ponta-cabeça) entre uma passada e
outra, o ponto do papel que estava a *Y* da pinça passa a estar a
*(altura − Y)* da **pinça nova**, e a cabeça da peça passa a apontar para
o lado contrário. Daí sai a regra:

> **O verso tem de estar 180° da frente.**

Só que a montagem quase sempre **já precisa girar 90° para caber na
chapa** — uma montagem em pé de 305 × 425 não entra nos 399 mm que
sobram da PM 52 depois da pinça; deitada, 425 × 305, entra. Então:

```
frente  −90°        verso  +90°        (diferença: 180°)
```

Girar **uma para cada lado** resolve as duas coisas de uma vez, e é como
o operador enuncia: *"a frente será rotacionada −90 graus e o verso 90
graus, pra dar certo na hora de rodar o frente e verso"*.

Sem giro para caber, a mesma regra vira frente 0° e verso 180°.

### As duas pinças do tombo

Porque a pinça **troca de borda**, as **duas pontas** da folha precisam
de margem. É a desvantagem conhecida do tombo — gasta duas margens onde
o vira gasta uma — e é o que separa, nesta casa:

| | como vira | pinças | a montagem se parte |
|---|---|---|---|
| **bate-vira, 1 pinça** | vira de lado | 1 | por uma linha **vertical** |
| **bate-vira, 2 pinças** | **tombo** | **2** | por uma linha **horizontal** |
| **frente e verso** | tombo, com **2 chapas** | 1 por chapa | não se parte |

No bate-vira de duas pinças a montagem fica **centrada entre as duas
margens**: é o que faz o verso cair atrás da frente depois do tombo.

### Como saber qual é, olhando o desenho

É a pergunta mais rápida, e não depende do nome que cada casa usa:

> **Por onde a montagem se parte ao meio — por uma linha vertical ou por
> uma horizontal?**

- frente e verso lado a lado, cabeças se encontrando num vão
  **vertical** → **vira sobre o eixo**, a pinça continua a mesma;
- frente e verso um sobre o outro, cabeça com cabeça num vão
  **horizontal** → **vira pelo pé**, a pinça troca de borda.

Nesta casa o termo usado é **bate-vira**, e o trabalho do flyer 15×21
(ver `SKILL.md`) se parte por uma linha **vertical** — ou seja, é o
**vira sobre o eixo**, com a pinça na mesma borda nas duas passadas.

## Os sinais gráficos da folha

Do guia brasileiro do Buggy (ver Fontes), que é a referência mais
próxima da nossa prática.

**Três marcas de impressão**, e só três:

| marca | o que é | para que serve |
|---|---|---|
| **de corte** | traço contínuo, **~3 mm** no guia | onde a guilhotina corta |
| **de dobra** | linha **pontilhada** | onde o impresso dobra |
| **de registro** | círculo ou retângulo com duas semirretas perpendiculares no centro | o impressor casa as camadas de tinta |

Mais dois elementos de controle, que não são marcas:

- **barra de controle** (tira de cor) — o impressor afere quanta tinta e
  quanta água o papel recebeu;
- **tarja estelar** — mesma função, por outro desenho.

**Tudo isso vive fora do corte e é jogado fora nas aparas.** Para chegar
lá, tem de estar gravado na chapa junto com a arte — não é enfeite de
arquivo, é ferramenta de quem está na máquina.

### Cor de registro

**100% de C, 100% de M, 100% de Y e 100% de K ao mesmo tempo.** Não é
preto (que é só K) nem preto rico. O ponto é que a marca sai **em todas
as chapas**, no mesmo lugar: se as quatro casarem, ela aparece como um
traço preto limpo; se alguma sair do lugar, a marca mostra colorido nas
bordas — e é assim que o impressor enxerga o erro de registro.

Ao desenhar marca por programa, é isso que tem de ser escrito: as quatro
tintas cheias, e não `K = 100`.

### Sangria — e aqui a casa e o livro discordam

O guia manda a sangria **exceder o corte em pelo menos 3 mm**, e
recomenda **5 mm**.

A regra desta casa é **metade do vão entre as peças**. Com vão de 5 mm
isso dá **2,5 mm** — abaixo do mínimo do guia. Não é erro: é o que o vão
comporta, e vão maior come área útil de papel. Mas a conta é boa de ter
na mão:

| sangria desejada | vão necessário |
|---|---|
| 2,5 mm (o de hoje) | 5 mm |
| 3 mm (mínimo do guia) | 6 mm |
| 5 mm (recomendado) | 10 mm |

## Formato aberto e formato fechado

Todo impresso que dobra é produzido **planificado**. Então há sempre dois
tamanhos, e confundi-los é montar errado:

- **formato aberto** — desdobrado, que é o que vai para a chapa;
- **formato fechado** — dobrado, que é o que o cliente vê.

## Os softwares de imposição

Levantados para saber o que existe e o que essas ferramentas fazem que
nós precisaríamos refazer:

| software | feitio |
|---|---|
| **Kodak Preps** | o mais difundido da indústria; cadernos, aproveitamento de folha |
| **Heidelberg Prinect Signa Station** | o do mundo Heidelberg, integrado à máquina |
| **Quite Imposing (Plus)** | plug-in do Acrobat, tradicional em gráfica |
| **Fiery Impose** | vem com o RIP Fiery, exporta o imposto em PDF |
| **Montax Imposer** | Windows, avulso ou plug-in; templates repetidos, hot folder, linha de comando |
| **Tilia Labs Phoenix** | encaixe automático, corte por faca, otimização |
| **Ultimate Impostrip** | automação de fluxo |

O que **todos** fazem, e é a lista do que uma imposição de verdade
precisa ter:

1. repetir uma peça N vezes numa folha, com vão e sangria;
2. girar peças (90°, 180°) por aproveitamento ou por exigência do vira;
3. desenhar marcas de corte, dobra e registro, em cor de registro;
4. pôr barra de controle e identificação da chapa;
5. **guardar o arranjo como modelo** e repetir em outro trabalho;
6. respeitar pinça, área útil do papel e área de imagem da máquina.

O item 5 é o que separa brincadeira de ferramenta: numa gráfica o mesmo
arranjo volta toda semana.

## O que dá para fazer aqui, com o que já existe

Na máquina do CTP já há **pypdf** e **Pillow**, e o **Ghostscript** que a
FIA usa o dia inteiro. Isso basta para imposição:

- `pypdf` põe uma página dentro de outra em posição e giro exatos
  (`Transformation().rotate().translate()` com `merge_transformed_page`),
  que é a operação central da imposição;
- as caixas do PDF (`ArtBox`, `TrimBox`, `BleedBox`, `MediaBox`) dizem
  onde é o corte e onde é a sangria **sem ninguém medir na régua** — foi
  da `ArtBox` que saiu o 150 × 210 do flyer;
- marcas e barra de cor são vetor simples, desenháveis direto no PDF.

Nada disso precisa do CorelDRAW. O Corel continua sendo o caminho de
quem **recebe** `.cdr` (ver `corel-com.md`); a imposição em si é PDF.

## Fontes

- [Work-&-turn and Work-&-tumble — Lithotech](https://lithotech.co.za/work-turn-and-work-tumble/)
- [Work-and-Tumble — PrintWiki](https://printwiki.org/Work-and-Tumble)
- [Between the Sheets — CreativePro](https://creativepro.com/between-the-sheets/)
- [Gripper Edge Explained — PDF Press](https://pdfpress.app/blog/gripper-edge-explained)
- [Buggy, *Produção de impressos em offset: guia básico para designers*, Recife, 2009 (ISBN 978-85-907722-1-7)](https://www.rafaelhoffmann.com/aula/arquivos/materiais_processos_impressao/producao_impressos_offset.pdf) — marcas, sangria, aparas, formato aberto/fechado
- [Impressão offset — Portal Chambril](https://www.portalchambril.com.br/artigos-tecnicos/impressao-offset/) — *tira e retira*, imposição, traçado
- [Registration Marks — Print Wiki](https://print.wiki/terms/registration-marks/) · [Color Vision Printing](https://www.colorvisionprinting.com/blog/printing-registration-a-key-factor-in-high-quality-printing)
- [Best Imposition Software 2026 — PDF Press](https://pdfpress.app/blog/best-imposition-software-2026) · [Montax Imposer](https://www.montax-imposer.com/)
- [pypdf](https://pypi.org/project/pypdf/) · [pikepdf](https://pikepdf.readthedocs.io/)
