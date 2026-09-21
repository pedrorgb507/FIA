# O que a FIA ainda não faz

Cada linha aqui é um serviço que **para** e espera gente. Nenhuma é
esquecimento: ou o caso ainda não foi combinado com o operador, ou
adivinhar sairia caro.

É também a lista do que automatizar em seguida. Quando um caso destes for
resolvido, tire-o daqui e ponha a regra em `clientes.md` ou `arte.md`.

## Arquivo que chega no formato errado

| cliente | o que chega | por que para |
|---|---|---|
| FIALHO | `.cdr`, `.ai`, arte por montar | padrão temporário: só anda PDF já no tamanho da chapa |
| VIVA | `.cdr` | idem — montagem ainda é na mão |
| CREATIVE | qualquer coisa que não seja PDF | idem |
| SOLIDA | nome sem número de OS | é a OS que dá nome à chapa |

O `.cdr` da VOPRIX **é** convertido, porque a arte dela já vem montada no
tamanho da chapa e o padrão do nome é conhecido. Nos outros, converter
seria só o começo do trabalho.

Arquivo de arte que o programa não sabe tratar (`.cdr`, `.ai`, `.eps`,
`.psd`, `.indd`, `.tif`, `.jpg`, `.png`) **vira pendência uma vez**, em
vez de sumir da vista. Nasceu da Creative: ela mandou 7 `.cdr` em dias
passados e o programa só olhava `.pdf` naquela pasta — cada um teria
sumido sem uma linha no log.

## Montagem

Só a **Creative** é montada, e só o caso dela: uma arte, centralizada na
largura, com pinça no pé. Ver `arte.md`.

Fora disso, montagem continua no InDesign:

- mais de uma arte na mesma chapa (imposição);
- arte que não bate com chapa nenhuma e está fora do encaixe do Fialho;
- caderno, dobra, paginação.

## Cor fora da quadricromia

VOPRIX, EMPORIO, VIVA e CREATIVE param quando a arte não usa as quatro
tintas. A prova sai, os números aparecem na tela, e **quem manda fechar é
gente**.

Em quadricromia o caminho é sempre o mesmo; é fora dela que a decisão
muda de trabalho para trabalho. Este é um "para" de propósito, não uma
falta.

## Verniz — e máscara, que é a mesma coisa

**A FIA nem abre.** Arquivo com `verniz` ou `mascara` no nome é pulado
**calado**, de **todo** cliente, antes de qualquer conversão. Vira
**fotolito**, e fotolito ela ainda não sabe fazer.

Duas conversas, e a segunda desfez o tom da primeira:

- **17/09/2026, verniz.** Primeiro só a VIVA — *"quando o arquivo chegar
  com nome de verniz*.*, pode desconsiderar; não precisa fazer nada, nem
  precisa avisar — só deixar parado na pasta"*. Depois, de todos:
  *"vamos colocar a trava então em todos os arquivos que tiver o nome de
  verniz, de todos os clientes... pois serão feitos fotolitos e não
  chapas, e você ainda não tem essa habilidade"*;
- **21/09/2026, máscara.** *"aconteceu na pasta da voprix, MASCARA, siga
  a mesma regra para quando o nome for verniz, o nome MASCARA tb é para
  uma mascara de verniz, então pode desconsiderar quando cair um arquivo
  com esse nome"*.

**O SILÊNCIO É O PEDIDO, e não descuido.** Em toda a outra parte desta
casa pular arquivo calado é defeito — a armadilha 19 existe para isso. A
diferença aqui: o operador **sabe** que o arquivo está ali e sabe o que
fazer com ele. O aviso não lhe dizia nada de novo, e era ele que abria
uma tela cheia por arquivo, todo dia.

**O registro concordou nas duas vezes**, e foi ele que convenceu:

| | arquivos | chapas geradas |
|---|---|---|
| `verniz` no nome, desde 02/09/2026 | 11 | **zero** |
| `mascara` no nome, desde 09/09/2026 | 5 | **zero** |

Os cinco da máscara viraram pendência de **tamanho** — 478×328, 660×480,
297×420 —, e é o tamanho que denuncia: medida de **peça**, nunca de
chapa. Máscara se faz no tamanho do trabalho. No CTP inteiro não há uma
chapa com `mascara` no nome.

**Casa por PALAVRA inteira**, sem acento e sem caixa: `Mascara_Verniz`
conta (a palavra pode estar no meio), `VERNIZADO` e `MASCARADA` não.
`MASCARAS` no plural **também não** — ficou de fora de propósito, porque
só o singular tem caso medido.

**O único jeito de isto errar**: arte de verdade que se chame `mascara`
por outro motivo — rímel, fantasia — seria pulada calada, sem chapa.
Nenhuma apareceu em 507 arquivos.

Mora em `config.PALAVRAS_QUE_PEDEM_OLHO`, e quem lê é `nomes.e_verniz`,
chamado no `monitor.varrer`. **O dia em que a FIA mandar para fotolito,
essa função deixa de ser "ignore" e passa a ser "mande para o outro
caminho".**

Sobrou uma porta atrás, que hoje quase não se alcança: no
`processador`, EMPORIO, VIVA e CREATIVE ainda param com pendência se um
desses nomes chegar lá sem passar pelo vigia. A mensagem diz **qual
palavra casou** — acusar VERNIZ num arquivo onde ela nem aparece mandaria
procurar o que não está escrito.

## Dois arquivos com a mesma OS

`49728 - EDNA - COLINHAS 4MOD` e `49728 - EDNA - COLINHAS 4MOD 1`, no
mesmo dia. São dois serviços cobrados separados ou um trabalho partido em
dois arquivos? A diferença é o dobro do valor. **Não há regra** — a FIA
para e pergunta.

## Colisão de nome

Resolvida, mas sempre com aviso, porque o resultado precisa de olho
humano:

- **VOPRIX**: as duas viram `MODELO 1` e `MODELO 2`, e a que já estava
  gravada é renomeada;
- **FIALHO**: ` 01` e ` 02`, idem;
- **os outros**: a segunda sai `_v2`.

## O perfil ICC no caminho longo

SOLIDA, FIALHO, EMPORIO, VIVA e CREATIVE continuam sendo lidos **com** o
perfil embutido, o que remistura o preto em arquivos que trazem perfil.
Decisão do operador em 09/09/2026: deixar como está e registrar o risco.

Medido: EMPORIO, CREATIVE e FIALHO não são afetados; VIVA é; SOLIDA não
foi medida. Números e o comando de teste em `cor.md`.

## Quando o GEREMPRE está fora do ar

A chapa **não** para por causa disso: a prova sai sem verso e o
lançamento fica para a mão, com pendência anotada. Serviço que fecha e
ninguém cobra é prejuízo silencioso — por isso o aviso é obrigatório.

## Decidir um "não sei dizer"

Trabalho manual **novo**, criado de propósito em 09/09/2026.

Quando a arte volta para a pasta com nome e tamanho de um trabalho já
feito, mas a entrada antiga do registro não guardou o retrato do
conteúdo, não há como confirmar se é a mesma. O programa para e mostra
que chapa saiu e quando. Quem decide é gente:

- **já saiu** → tire o arquivo da pasta do dia;
- **é serviço novo** → salve com outro nome, que ele pega sozinho.

Isso some com o tempo: toda entrada nova do registro guarda o retrato.
Em 09/09/2026 eram 87 de 156 sem ele, e o número só cai. Não dá para
apressar preenchendo os antigos — os arquivos de origem ainda estão no
`V:`, mas é varredura de rede sobre meses de pasta com risco de casar
arquivo errado, para resolver o que a guarda já cobre.

## O que a ponte do Teams tirou da mão, e o que não tirou

Tirou: baixar o arquivo do Teams e salvá-lo na pasta do dia. A SOLIDA
posta no canal e o arquivo aparece.

**Não** tirou, e não deve: o cliente continua nomeando o arquivo, e é
disso que sai a OS. Se um dia chegar nome sem número de OS, para — está
na tabela lá em cima, e continua valendo.

Cliente novo no Teams **não** é só criar um canal. Canal padrão é visível
ao time inteiro, e dois clientes concorrentes veriam a arte e as OS um do
outro. O segundo entra por canal privado ou link de solicitação; o
`CAIXAS_TEAMS` existe para isso custar uma linha.

## O que ninguém automatizou porque ninguém pediu

- **substituir uma chapa já entregue** no CTP. Hoje é cópia à mão, e é
  bom que seja: pode já ter sido queimada;
- **refazer um arquivo** já processado — existe, mas é comando manual;
- **desfazer uma OS** aberta por engano. O caminho está provado e
  guardado em `ferramentas/prova_do_caminho_de_volta.py`, mas não há
  botão: mexer em estoque sozinho não é para o programa fazer.
