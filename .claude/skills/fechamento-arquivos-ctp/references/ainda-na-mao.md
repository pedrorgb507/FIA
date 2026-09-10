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

## Verniz

Nunca fecha sozinho, por mais que o resto esteja em ordem — EMPORIO, VIVA
e CREATIVE. Pedido do operador: verniz se confere antes.

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
