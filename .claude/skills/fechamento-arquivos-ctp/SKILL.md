---
name: fechamento-arquivos-ctp
description: Fechar arquivo de cliente e entregar a chapa para o CTP - medir o formato, conferir a arte por dentro, decidir a cor, imprimir a prova e gravar. Use sempre que aparecer chapa, CTP, gravacao, prova, quadricromia, escala de cinza, perfil de cor, separacao de tintas, resolucao de imagem, traco fino, pinca, marca de corte, sangria, CorelDRAW, Ghostscript, ou arquivo dos clientes SOLIDA, VOPRIX, FIALHO, EMPORIO, VIVA e CREATIVE - e tambem para entender por que uma chapa saiu errada.
---

# Fechamento de arquivo para o CTP

A FIA pega a arte que o cliente joga na pasta do dia, confere, imprime a
prova e põe o PDF da chapa na pasta do CTP, onde a gravadora a queima.
Era trabalho de gente no Photoshop e no InDesign.

Seis clientes, cada um com o seu jeito de mandar e de nomear:
`references/clientes.md`.

## O princípio

**Chapa errada é pior que chapa faltando.**

Chapa que não existe dá trabalho: alguém percebe e refaz. Chapa errada na
pasta do CTP não dá erro em lugar nenhum — abre, imprime na prova
reduzida igual às outras, e só mostra o defeito na tiragem, com a chapa
queimada e o papel rodando.

Daí a regra que vale em todo o programa: **entre errar sozinha e parar
para perguntar, pare**. O que sai do padrão vira **pendência** — uma
linha no log, um aviso na tela, o arquivo intocado — e quem resolve é
gente. Chutar formato, pinça, cor ou nome não é opção.

## O caminho de um arquivo

Quatro passos, nesta ordem. A ordem foi comprada com erro: a prova sai
com a ordem de serviço no verso, então o número da OS tem de existir
**antes** da prova, e a OS só se abre depois de saber quantas chapas o
trabalho gasta.

| | passo | o que decide |
|---|---|---|
| 1 | **conferir**, página a página | formato, giro, pinça, cor, preflight — sem gerar nada |
| 2 | **a OS** no GEREMPRE | só se o arquivo passou INTEIRO; ver a skill `gerempre` |
| 3 | **a prova** impressa | A4 retrato, arte na frente, OS no verso, mesma folha |
| 4 | **a chapa** na pasta do CTP | pelo caminho longo ou pelo curto |

Conferir é rápido; gravar leva minutos. Por isso são passos separados — a
prova continua saindo cedo, como sempre saiu.

**O passo 2 mexe em ESTOQUE.** A OS dá baixa de chapa na hora. Antes de
tocar em qualquer coisa que escreva no GEREMPRE, leia a skill `gerempre`.

**A pasta de entrada é compartilhada e nada é movido nem apagado dela.**
Quem controla o que já foi feito é o registro `_processados.json`, na
`PASTA_CONTROLE`, no disco local.

## Os dois caminhos até a chapa

|  | caminho **longo** | caminho **curto** |
|---|---|---|
| o que faz | separa as tintas no Ghostscript e remonta o PDF | entrega o PDF do cliente inteiro |
| quem separa | nós | a gravadora |
| para quem | SOLIDA, FIALHO, EMPORIO, VIVA, CREATIVE | VOPRIX (`ENTREGAR_PDF_DIRETO`) |
| custo | minutos, e o arquivo triplica de tamanho | zero — com uma página, é cópia byte a byte |
| exige | nada | arte já vetorial, no tamanho da chapa, sem giro nem montagem |

O curto nasceu de uma chapa errada — o perfil ICC tirava o preto do canal
K. A história inteira, com os números, está em `references/cor.md`.

**Arte de uma cor desenhada com as quatro tintas não vai pelo curto.** A
chapa é uma, mas o arquivo tem C, M, Y e K escritos dentro e a gravadora
gravaria quatro. Essa volta pelo longo, que junta tudo num cinza.

## Se pede, não se herda

Três vezes a mesma lição, cada uma cobrada em papel ou em chapa:

- **frente e verso** — a Konica está em SIMPLEX (`Duplex=1` no driver), e
  o programa supunha o contrário. A prova saía numa folha e a OS em
  outra. Agora `-dDuplex` vai explícito em toda impressão, ligado ou
  desligado;
- **a predefinição do PDF** — o `PublishToPDF` usa o que estiver marcado
  na janela do CorelDRAW naquele dia, e a janela é a mesma que o operador
  usa à mão. Agora a `FINART` é carregada pelo nome, e a conversão **para**
  se ela não vier em CMYK;
- **as reamostragens** — desligadas na marra a cada conversão. Bastava
  alguém marcar a caixa para toda arte da VOPRIX sair em 300 dpi numa
  chapa de 1000: borrada, sem sintoma até a impressão.

Configuração de máquina compartilhada não é promessa. Peça o que você
precisa, toda vez.

## Armadilhas

**1. O Ghostscript passa a cor pelo perfil ICC embutido.**
Arquivo com perfil próprio (a Corel embute um de 557 KB) tem o CMYK
convertido origem → perfil → dispositivo, e essa volta **não é
identidade**: cinza feito só de K sai remisturado nas quatro tintas.
Numa pasta de verdade o K caiu de 0,0515 para 0,0060 — 8,6 vezes menos
preto na chapa gravada. `-dUseFastColor=true` lê a cor como ela está
escrita. **Isto ainda acontece no caminho longo, por decisão** — ver
`references/cor.md`.

**2. Comparar em resoluções diferentes engana.**
Rasterizar um PDF vetorial em 100 dpi e comparar com uma chapa de 1000
dpi reduzida para 100 mostra uma diferença que não existe: o traço fino
sai cheio de um lado e cinza do outro, e isso é da redução. Compare os
dois lados **na resolução da chapa**, ou reduza os dois igualmente
depois. Foi assim que eu quase reportei um defeito que não havia.

**3. O `-dFitPage` quebra quando precisa GIRAR a página.**
Arte deitada de 510x400 indo para A4 em pé é exatamente o caso. Por isso
a prova é montada por nós, no tamanho e no sentido exatos da folha, e o
Ghostscript não faz encaixe nenhum.

**4. O nome de saída só se fecha na hora de gravar.**
As regras de colisão — `MODELO` da VOPRIX, ` 01`/` 02` do Fialho, `_v2`
dos outros — olham os arquivos que **já estão** na pasta do CTP. Na
conferência, que vem antes, nenhuma chapa existe ainda: as duas páginas
de um mesmo arquivo escolheriam o mesmo nome e a segunda sobrescreveria a
primeira.

**5. Montar documento novo em volta de uma página perde `/OCProperties`.**
É a ficha das CAMADAS, e mora no catálogo do PDF, fora da página. Sem
ela, o que estava escondido — guia de corte, gabarito de verniz — fica
com visibilidade indefinida e a gravadora pode gravar. Clone o documento
e apague as outras páginas.

**6. O PDF que a Corel devolve pode ser 25 vezes maior que o preciso.**
Com bitmap cru, um `.cdr` de 13 MB virou PDF de 1007 MB. Com ZIP — sem
perda, conferido pixel a pixel — o mesmo arquivo deu 39,6 MB. As duas
compressões são exigidas por cima da predefinição, que guarda cru.

**7. A automação usa a sessão do CorelDRAW do operador.**
Nunca mexer em `Visible`; nunca fechar documento que não fomos nós que
abrimos — o `OpenDocument` de um arquivo já aberto devolve o documento
dele, e fechar aquilo joga fora o trabalho da pessoa. Arquivo aberto na
sessão não é convertido: fica para a próxima passada.

**8. A marca de corte se lê no VETOR, nunca na imagem.**
Em arte cheia, mancha passa por risco e risco passa por mancha; duas
versões do detector deram números diferentes para o mesmo arquivo. No
PDF a marca é um traço com coordenada exata. E a pinça se mede **da
marca**, não da borda do arquivo — são coisas diferentes, e medir do
lugar errado pôs a arte 12 mm fora do lugar.

**9. Arquivo que aparece na pasta pode não ter terminado de chegar.**
0 byte, ou crescendo. É pulado calado a cada varredura e só vira aviso
depois de `AVISAR_ARQUIVO_PARADO`. Aconteceu de verdade: um PDF de 4 OS
ficou 3 minutos com 0 byte e ninguém soube.

## Onde está o resto

| | |
|---|---|
| `references/clientes.md` | os seis clientes: o que mandam, formatos, nome de saída |
| `references/cor.md` | quadricromia, cinza, perfil ICC, cor especial |
| `references/arte.md` | preflight, pinça, marca de corte, giro, montagem |
| `references/ainda-na-mao.md` | o que a FIA não faz, e por quê |
| skill `gerempre` | a OS, o estoque e o banco da empresa |
| `README.md` | o passo a passo completo, com exemplos de nome |
| `src/finart_ctp/processador.py` | o fluxo: mede, confere, conduz página a página |
| `src/finart_ctp/config.py` | **formatos, dpi, tolerâncias, limites** |
| `tests/` | 325 testes; quase todo caso citado aqui tem um |

Os números ficam no `config.py` e não aqui: mudam, e duas cópias
envelhecem separadas. Os comentários de lá contam de onde veio cada um.
