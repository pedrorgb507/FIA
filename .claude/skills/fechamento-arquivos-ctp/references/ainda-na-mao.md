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

## O que ninguém automatizou porque ninguém pediu

- **substituir uma chapa já entregue** no CTP. Hoje é cópia à mão, e é
  bom que seja: pode já ter sido queimada;
- **refazer um arquivo** já processado — existe, mas é comando manual;
- **desfazer uma OS** aberta por engano. O caminho está provado e
  guardado em `ferramentas/prova_do_caminho_de_volta.py`, mas não há
  botão: mexer em estoque sozinho não é para o programa fazer.
