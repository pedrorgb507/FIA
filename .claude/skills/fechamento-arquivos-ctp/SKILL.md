---
name: fechamento-arquivos-ctp
description: Fechar arquivo de cliente e entregar a chapa para o CTP - receber a arte, medir o formato, conferir por dentro, decidir a cor, imprimir a prova e gravar. Use SEMPRE que o assunto for chapa ou CTP, mesmo de passagem. Use sempre que aparecer chapa, CTP, gravacao, prova, quadricromia, escala de cinza, perfil de cor, separacao de tintas, resolucao de imagem, traco fino, pinca, marca de corte, sangria, CorelDRAW, Ghostscript, pendencia, chapa duplicada, a entrada pelo Teams/OneDrive, ou arquivo dos clientes SOLIDA, VOPRIX, FIALHO, EMPORIO, VIVA, CREATIVE, PRIME e AMERICA - e tambem para entender por que uma chapa saiu errada.
---

# Fechamento de arquivo para o CTP

A FIA pega a arte que o cliente joga na pasta do dia, confere, imprime a
prova e põe o PDF da chapa na pasta do CTP, onde a gravadora a queima.
Era trabalho de gente no Photoshop e no InDesign.

Oito clientes, cada um com o seu jeito de mandar e de nomear:
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

### De onde o arquivo vem

Do `V:`, sempre — mas nem sempre alguém o pôs lá. Desde 09/09/2026 o que
a SOLIDA posta no canal dela do Teams atravessa **sozinho** até a pasta do
dia (`entrada_teams.py`), e o vigia segue dali sem saber a diferença:

```
canal do Teams → SharePoint → OneDrive sincroniza → V:\<cliente>\MES\DIA → chapa
```

Não há token nem aplicativo registrado: quem autentica é o OneDrive da
máquina. Isso foi escolhido — credencial própria expira de madrugada e
ninguém descobre até segunda.

O que muda para quem fecha chapa: **sumiu o olhar humano da entrada.**
Antes alguém baixava o arquivo do Teams e o salvava, e via cada um antes
de entrar. Hoje ninguém vê. Duas defesas nasceram disso — o aviso da
rajada (o fim de semana inteiro entra junto quando a janela abre na
segunda, e o programa diz o que vai fazer antes de fazer) e a guarda da
regravação, na armadilha 10.

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

## No CTP: um arquivo, uma página. Sempre, todo cliente

Regra do operador, 17/09/2026: *"nunca mande para o ctp arquivo, pdf com
duas paginas (...) crie dois arquivos, com numeros na frente do nome
exemplo 01..02.. e por ai vai (...) sempre coloca no ctp 01 pagina 01
arquivo por vez.. ele nao puxa multiplas paginas"*.

**A gravadora puxa a primeira página e ignora o resto.** Um PDF de duas
páginas na pasta do CTP não vira duas chapas: vira uma chapa e uma página
esquecida — e ninguém vê, porque o arquivo *está* lá, com o nome certo e
o tamanho certo.

```
745x605_CMYK_AMERICA_PASTA PRE MEETING fv.pdf        ← 2 páginas, ERRADO
01 745x605_CMYK_AMERICA_PASTA PRE MEETING fv.pdf     ← certo
02 745x605_CMYK_AMERICA_PASTA PRE MEETING fv.pdf
```

**O número vai na FRENTE**, com dois algarismos. A pasta do CTP é lida em
ordem alfabética, e é assim que a ordem das páginas vira a ordem da fila
de gravação; com o número atrás, quem manda na ordem é o nome do trabalho
e as páginas se espalham. Dois algarismos porque `10` viria antes de `2`.

Quem faz isso é `entrega.entregar_no_ctp()`, e ele vale para todos: com
uma página é cópia byte a byte, como sempre foi; com mais de uma, recorta
uma por arquivo preservando o `/OCProperties` (a ficha das camadas — sem
ela a camada escondida pode gravar). A conferência muda junto: partido,
o tamanho em bytes não prova nada, então o que se confere é a conta e a
forma (`chegou_por_pagina`).

**A conta da OS nunca esteve envolvida nisto.** Ela já cobra
`páginas × tintas` — as 8 chapas daquele arquivo estavam certas. O
defeito era só na entrega, e conserto que mexesse na conta cobraria em
dobro.

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

**10. "Não sei dizer" é uma resposta, e é a terceira.**
A arte volta para a pasta com data nova e o programa pergunta se já virou
chapa. A resposta certa nem sempre é sim ou não: quando nome e tamanho
batem com um trabalho já feito mas aquela entrada do registro **não
guardou o retrato do conteúdo**, não há com o que comparar. Em 09/09/2026
eram 87 das 156 entradas — mais da metade —, e para elas a proteção
simplesmente não agia: a chapa saía de novo, com OS nova e baixa de
estoque de verdade.

Foi assim que o `49694 - Gaspar - colinha.pdf` saiu duplicado em 08/09,
com 12 segundos entre as duas chaves; e foi por um triz que o
`49695 - Radio Dente` não repetiu a dose em 09/09, voltando pelo Teams.

Agora `situacao_no_registro` responde `JA_FEITO`, `NAO_DA_PARA_SABER` ou
`TRABALHO_NOVO`, e o do meio **vira pendência** dizendo que chapa saiu e
quando. Não chuta porque os dois chutes custam: gravar arrisca chapa
duplicada, pular arrisca chapa faltando. O arquivo incerto fica na pasta
e **não entra no registro** — entrar seria dá-lo por resolvido.

Só conta quem realmente virou chapa (`saidas` preenchida): entrada de
erro não tem chapa para duplicar. E o cliente separa — dois clientes com
arte idêntica são dois serviços, cada um com a sua OS.

**11. O OneDrive mente sobre o tamanho do arquivo.**
Arquivo sincronizado que ainda não foi baixado aparece na pasta com o
tamanho **certo** — o Explorer mostra 5,9 MB — mas o conteúdo continua na
nuvem. `os.path.getsize` devolve o tamanho lógico do atalho, e
`arquivo_estavel` passa: dois tamanhos lógicos iguais.

Para saber se o conteúdo está mesmo no disco, olhe o **alocado**
(`GetCompressedFileSizeW`), que vem 0, ou o atributo
`RECALL_ON_DATA_ACCESS` (`0x400000`), que a ponte confere. Ler o arquivo
dispara o download — que trava se a internet estiver fora, e travaria
dentro do laço do vigia.

A pasta sincronizada tem de ficar marcada como **"Sempre manter neste
dispositivo"** (`attrib +p`). Sem isso a ponte espera para sempre, com
razão.

**12. Falha depois da impressão vira laço de impressão.**
Aconteceu **duas vezes em 10/09/2026**, com defeitos diferentes e a mesma
forma. No `02020 - CHAPA ZIMI` do EMPORIO, uma variável não inicializada
estourava *depois* da prova sair; o `except` da impressão entendia
qualquer falha como "impressora fora do ar", o arquivo ia para `espera`,
e espera não entra no registro — a cada 5 minutos, papel. No flyer da
AMÉRICA, o apagar do portão recusava por um detalhe da cópia guardada, o
arquivo ficava, e a cada 5 segundos o vigia refazia tudo — prova
inclusive. Três folhas até alguém ver.

Consertar cada laço conserta um laço. A rede embaixo de todos está em
`prova.imprimir()`: ela guarda em `_impressos.json` (na `PASTA_CONTROLE`)
o que já saiu, **anota com o papel já a caminho** — anotar depois *era* o
defeito —, e numa segunda chamada levanta `JaImprimiu` sem mandar nada.
Quatro detalhes que ela precisou acertar para não virar estorvo:

- quem chama trata `JaImprimiu` como **não-falha**. No processador ela
  não pode virar `espera`, senão vira nova tentativa — o próprio laço;
- **impressora fora do ar não conta como impresso**: o envio falhou,
  nada saiu, e o trabalho tem de poder sair depois;
- a chave é **por arte e por OS**: a mesma arte pode voltar num serviço
  novo, e ali a prova é legítima. O número da OS viaja colado na folha
  do verso (`_os_numero`);
- na VOPRIX a chave é o **`.cdr`** (`origem=`), não o PDF que a Corel
  gera de novo a cada passada — tamanho e data mudam, e a trava nunca
  pegaria justamente no cliente que mais reconverte.

`copias=N` manda N de uma vez; `de_novo=True` reimprime o que já saiu. A
trava é para o laço, não para o operador.

E o `conftest` isola `prova.PASTA_CONTROLE`: os testes escreveram no
livro **de verdade**, e três caíram um em cima do outro porque o primeiro
anotava e os seguintes batiam na trava. Mesma lição da armadilha 13 do
GEREMPRE — teste não toca em estado de produção.

→ **"Já imprimi?" é a primeira pergunta de todo laço**, e quem imprime
deixa dito que imprimiu antes de fazer mais qualquer coisa.

**13. Uma janela modal do CorelDRAW derruba a conversão — e a causa pode
estar no OneDrive.**
Em 11/09/2026, às 08:18, a FIA abriu o Corel por COM para converter um
`.cdr` da VOPRIX e o Corel parou numa janela: *"Não foi possível
encontrar locais de conteúdo… movidos, renomeados ou excluídos, ou sua
unidade externa está desconectada"*. Janela modal segura a inicialização;
o `Dispatch` esperou dois minutos e falhou com `-2146959355 'Falha na
execução do servidor'`. O arquivo virou pendência com `status: erro` — o
vigia não travou, mas o serviço parou.

A causa não era o Corel: o **OneDrive tinha movido a pasta Documentos**
(Known Folder Move) para `C:\Users\Eudson\OneDrive\Documents`, e o
conteúdo do Corel — 18 subpastas, 590 arquivos — foi junto. Os caminhos
gravados pelo Corel ainda apontavam para `C:\Users\Eudson\Documents\Corel\
Corel Content`, que ficou como casca vazia. "Movidos" era literal.

O conserto que não exige fechar o Corel nem mexer em opção: a casca vira
uma **junção** (`mklink /J`) para a pasta de verdade. Qualquer caminho cai
no mesmo lugar, e o Corel pode regravar as configurações ao sair que
continua valendo. **São três pastas, não uma** — `Corel\Corel Content`,
`Working Files` e `Corel Cloud`; faltando qualquer uma a janela aparece,
e a primeira rodada só cobriu a primeira. `ferramentas/consertar_corel.ps1`
cuida das três e é reexecutável; também aponta para o perfil atual os
caminhos de backup automático que estavam num `C:\Users\Administrator`
que não existe mais — essa parte só pega com o Corel fechado.

Como se prova que ficou bom: fechar o Corel, reabrir, e **esperar uns 40
segundos** antes de olhar as janelas — a modal vem *depois* da janela
principal, e um teste que para na primeira declara vitória cedo demais.
O CorelDRAW desta máquina é o do **Technical Suite**
(`...\CorelDRAW Technical Suite\27\Programs64\CorelDRW.exe`); a
configuração dele mora em `%APPDATA%\Corel\CorelDRAW Technical Suite
2026\Config`, não na pasta do Graphics Suite, que está vazia.

Dois detalhes de operação que valem além deste caso:

- **`salvar_registro` nunca remove, e o vigia guarda o registro em
  memória** (`registro.update(...)`). Apagar a entrada `erro` do JSON
  **não** faz o vigia tentar de novo. O que faz é o "salve de novo" que
  a própria FIA pede: renovar a data do arquivo muda a chave
  (`nome|tamanho|mtime`), e a guarda de regravação deixa passar porque a
  entrada velha não tem `saidas`;
- a modal só aparece **na inicialização**. Com o Corel já aberto pelo
  operador, o `Dispatch` se pendura na sessão dele e converte normal
  (armadilha 7). Então "funcionou de manhã e falhou à tarde" pode ser só
  o Corel ter sido fechado no meio.

**14. O perfil ICC esconde o preto puro — e esconde de DOIS jeitos
diferentes.**

Esta é a armadilha 1 vista de outro ângulo, e ela custou duas correções
em dois dias. A pergunta "em que canal a tinta está" **só pode ser feita
ao arquivo**, nunca ao perfil. Medido:

| | com o perfil | sem o perfil |
|---|---|---|
| `49835 - Flor Bela` (SOLIDA, **chapado**) | C=M=Y=K=0,3867 | C=M=Y=0 · K=0,3867 |
| `GRADE 3386` verso (VIVA, **meio-tom**) | C 0,1393 M 0,1435 Y 0,1435 K 0,0634 | C=M=Y=0,001 · **K 0,4131** |

Os dois são K sozinho no arquivo. No **chapado** o perfil espalha o preto
por igual, e `pagina_de_uma_cor` aceita aquilo como preto composto — a
detecção funcionava por acidente. No **meio-tom** a conta do perfil é não
linear, os canais saem desiguais, e nada passa: o verso do `GRADE 3386`
saiu com **quatro** chapas e a OS 19730 cobrou oito no lugar de cinco.

→ `preto_so_no_K` roda **sempre** sobre a leitura crua, antes de qualquer
outra pergunta. A passada a mais do `inkcov` é mais **barata** que a com
perfil — 0,9 s contra 2,3 s no próprio 3386 —, porque não há conversão de
cor a fazer.

→ O preto **composto** continua decidido pela leitura com perfil e preso
a `CLIENTES_QUE_JUNTAM_PRETO_COMPOSTO`: ali as quatro tintas estão
escritas no arquivo, e fundir quatro chapas numa é decisão bem mais
delicada.

**15. Conferir a chapa de uma cor pelo MÁXIMO é conferir nada.**

A chapa de uma cor é conferida comparando a tinta antes e depois. A
primeira versão olhava só o máximo — e o máximo **sempre** dá 100%,
porque as marcas de registro da Corel são 100% das quatro tintas e
atravessam o perfil intactas. A conferência passava enquanto a arte saía
com 87% de preto onde o arquivo tinha 100%.

→ Compare também o **chapado**: quantos mm² estão em 100% de tinta. O
perfil derrete essa área, e é ela que denuncia. Em 300 dpi, e não em 60:
vetor rasterizado em dpi baixo infla o traço fino e a conta mente.

→ E jamais leia a origem pelo mesmo perfil que estraga a chapa. Foi o
erro que me fez declarar "a chapa está boa" para uma chapa que não
estava: eu comparei a doença contra ela mesma. `-dUseFastColor=true` dos
dois lados.

**16. `OSTIT` cabe 50 letras, e dois serviços diferentes viram um só.**

14/09/2026, VOPRIX, no mesmo dia:

```
Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Colegio_Voolivre
Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Nelore_Bemach
```

As **50 primeiras letras são iguais**. A FIA lançou o Voolivre às 19:20
e, às 19:23, casou o Nelore com o título cortado do outro: *"já está
lançado, não cobrei de novo"*. A gravação do Nelore saiu **sem
cobrança**.

→ Nome que não cabe vai **partido**: começo, `..` e as últimas
**palavras** — `ENVELOPE_SACO_23X31,5_4_0_RAPHAEL..NELORE_BEMACH`.
Sempre que passa de 50, nunca só quando há colisão à vista: título que
dependesse do que já está na OS mudaria conforme a hora do dia, e a FIA
deixaria de reconhecer o que ela mesma lançou.

→ Bater só com as 50 primeiras letras **não é prova** de que o serviço já
foi lançado. Vale quando o cliente põe a nossa OS na frente do nome
(SOLIDA e EMPORIO); nos outros é dúvida, e dúvida aqui é dinheiro nos
dois sentidos. Detalhes na skill `gerempre`, armadilha 20.

**17. Dois arquivos com a mesma OS: contador é dúvida, palavra é serviço
novo.**

Três casos reais, e a regra tem de acertar os três:

| | | |
|---|---|---|
| `49728 - EDNA - COLINHAS 4MOD` e `... 4MOD 1` | mesma OS, mesmo nome, só um **contador** no fim | **para e pergunta** |
| `49854 HENRIQUE 49858 JUNIOR ... - GRADE` e `49854 - HENRIQUE CESAR` | uma **grade** com quatro OS dentro, e uma delas sozinha | **para e pergunta** |
| `49862 - MIRIA PIRES - FOLDER` e `... FOLDER CORRIGIDO` | mesma OS, e o nome diz o que mudou | **segue, e cobra os dois** |

O que separa o terceiro: ali os dois nomes carregam **exatamente** a
mesma OS — nem mais nem menos — e a descrição mudou com **palavra**, não
com contador. Regra do operador em 15/09/2026: *"é uma correção do
cliente, um novo arquivo, e tem que ser feita uma nova OS"*.

→ Isto só vale para quem traz a nossa OS no nome. No FIALHO o `2027` é o
**ano da agenda**, e procurar OS ali é procurar o que nunca esteve.

**18. Arte alguns milímetros fora entra CENTRALIZADA — mas só quem não
tem pinça.**

O `GRADE 3385` da VIVA media 510x399. Dentro da tolerância, o formato era
reconhecido, mas a chapa saía com o tamanho da **arte**: um arquivo de
510x399 com o nome dizendo 510x400. E a OS nem abria, porque a busca de
preço é exata.

Contando as 162 chapas já fechadas: **161 desviam 0,0006 mm**
(arredondamento de PDF) e **uma desvia 1,0083 mm** — do EMPORIO, saída 1
mm torta sem ninguém ver. O limiar de 0,1 mm fica no meio de duas
populações separadas por 1.700 vezes.

→ Quem tem pinça (CREATIVE, PRIME) fica de fora: para eles, arte do
tamanho da chapa quer dizer *"já montada"*, e centralizar desfaria a
montagem.

**19. Pendência que ninguém vê é pendência que não existe.**

A pendência saía em três lugares — a janela preta do programa, o
`_PENDENCIAS.txt` e o `_log_ctp.txt` — e os três pedem que alguém esteja
olhando. Quem está na máquina de chapa não vê nenhum. Em 14/09/2026
houve dezesseis pendências, e três eram serviço já gravado que ficou sem
cobrança até alguém reparar, horas depois.

Agora toda pendência abre uma janela **em tela cheia**, por cima de tudo,
na hora (`tela.py`). O gancho fica no `anotar_pendencia`, que é por onde
todas passam — pôr em cada um dos trinta e tantos lugares que geram
pendência é garantir que o próximo a ser escrito esqueça.

→ **E um avisador nunca pode falhar calado.** A primeira versão engolia o
erro e devolvia `False`: em 15/09/2026 a tela não abriu numa pendência de
verdade e não deixou rastro nenhum. A causa era o depurador do VS Code
embrulhando o `subprocess` da FIA (`"subProcess": false` no
`launch.json`), mas o defeito grave era o silêncio. Hoje ela diz no log,
confere se o processo filho vingou, e o laço tenta de novo.

**20. A pasta do CTP é a prova de que a chapa saiu. Arquivo apagado é
decisão de gente.**

15/09/2026, recuperando gravações que tinham ficado sem cobrança. O
`49854 - HENRIQUE CESAR - SANTINHOS` da SOLIDA tinha log de sucesso
(`OK em 331s: 49854.pdf, 54.2 MB`) e uma pendência da própria FIA
pedindo que fosse lançado à mão. Lancei, e cobrei 4 chapas.

O `49854.pdf` **não estava na pasta**. Os outros dezessete arquivos
daquele dia continuavam lá — só aquele sumira, apagado de propósito por
quem decidiu que a grade `49854 HENRIQUE 49858 JUNIOR...` já cobria
aquele serviço (é a armadilha 17, caso do meio). O log dizia que a chapa
fora gerada; a pasta dizia que ela não seria gravada. **A pasta estava
certa.**

→ Antes de dar andamento a serviço atrasado, **olhe se a chapa está na
pasta do dia**. Registro e log contam o que a FIA fez; a pasta conta o
que a casa decidiu depois. Quando discordam, quem manda é a pasta.

→ Vale nos dois sentidos: chapa **presente** que não está em OS é
gravação sem cobrança, e essa se lança. Foi assim que o `49903 - VALMIR
MARIA CLARA` entrou na OS 19748 no mesmo dia — a chapa estava lá, com
58,5 MB.

*(O detalhe de como isso se vê no GEREMPRE — inclusive o `OSUSR_ALT` que
denuncia mão humana — está na skill `gerempre`, armadilha 24.)*

**21. "O CorelDRAW não converteu" quase nunca é o CorelDRAW — e o
registro transforma tropeço passageiro em desistência definitiva.**

17/09/2026, 09:22. A PRIME parou com dois arquivos:

```
O.S PL DIEYME - SANTINHOS NOVO1.cdr: CorelDRAW nao converteu: module
'win32com.gen_py.95E23C91-BC5A-49F3-8CD1-1FC515597048x0x27x0' has no
attribute 'CLSIDToClassMap'

PL DIEYME - SANTINHOS_nova montagem.cdr: ... 'CLSIDToPackageMap'
```

O CorelDRAW estava aberto e são. Quem quebrou foi o **pywin32**: ele
gera invólucros Python da biblioteca COM da Corel e os guarda em

```
%LOCALAPPDATA%\Temp\gen_py\95E23C91-...x0x27x0\
```

— dentro do `%TEMP%`, que é exatamente o que o Windows limpa sozinho. A
faxina daquela manhã (pasta com data 09:03; as falhas às 09:22) levou os
arquivos `.py` e **deixou o `__pycache__` para trás**. O Python achou a
pasta, não achou fonte nenhuma, importou um módulo **vazio**, e todo
atributo que o pywin32 procurava nele faltava. Daí os dois nomes
diferentes de erro: é o mesmo defeito, em pontos diferentes da mesma
busca.

Duas coisas que enganam:

- **`Dispatch` simples também é envenenado.** Não é preciso usar
  `EnsureDispatch` para cair nisso: havendo invólucro gerado, o pywin32
  o usa, e um invólucro quebrado derruba até a ligação tardia;
- o remédio parece grande e é minúsculo: **apagar a pasta**. Aquilo é
  cache, se refaz em segundos, e não há nada a perder.

→ O `corel.py` agora se cura sozinho — pega o `AttributeError`/
`ImportError`, apaga o `gen_py`, tira `win32com.gen_py*` do
`sys.modules` e tenta **uma** vez mais. Limpa só nesses dois erros: Corel
fechada dá erro de COM, e aí apagar cache não ajuda e só esconde a causa.
Os testes estão em `tests/test_corel.py`.

→ **E a segunda metade, que é a mais cara.** Um `status: "erro"` entra no
`_processados.json` com a chave `nome|tamanho|data` — e, como o arquivo
não muda, **nunca mais é tentado**. Quer dizer: uma falha de ambiente que
durou dez minutos deixou dois serviços parados para sempre, sem chapa,
sem OS e sem ninguém avisado além da pendência. Foi preciso apagar as
duas entradas à mão (com cópia em `.antes_do_corel_1709_0935`) para a
passada seguinte pegá-las.

Antes de apagar entrada de erro, confira que ela não produziu nada —
`saidas: []`, `chapas: []`, `os: None`. Se produziu, é a armadilha 20 que
manda: quem decide é a pasta do CTP.

→ **E apagar do arquivo NÃO basta com o programa de pé.** Descoberto em
17/09/2026, às 18:28, tentando o mesmo conserto pela segunda vez no
mesmo dia. O laço faz

```python
if chave in registro: continue
registro.update(carregar_registro())     # ACRESCENTA
if chave in registro: continue
```

e `update` **acrescenta**: o que se apaga do JSON continua vivo na
memória da janela aberta, para sempre. Na primeira vez isso passou
despercebido porque houve um F5 logo depois, e pareceu que apagar tinha
bastado.

Duas saídas, e a segunda é a boa:

- **reiniciar** (F5) — funciona e custa uma parada;
- **dar ao arquivo uma CHAVE NOVA**, mexendo só na data:
  `(Get-Item $f).LastWriteTime = Get-Date`. A chave é
  `nome|tamanho|data`, então o vigia passa a vê-lo como arquivo novo e o
  processa em segundos, sem reiniciar nada e sem tocar no conteúdo. Foi
  assim que o `calend de mesa UNICIDADES 2027.cdr` andou.

*(O conserto de verdade — reavaliar sozinho o que um código velho
recusou — ainda não existe. A tentação é retentar todo erro no arranque,
e isso está ERRADO: há 43 entradas de erro no registro, e retentá-las
abriria dezenas de telas de pendência, que é justamente o que fez o
operador reiniciar a máquina na manhã de 17/09. O que cabe retentar são
as de HOJE, que ainda estão na pasta — eram 7 —, e mesmo essas sem
repetir aviso que já foi dado.)*

## Manter esta skill viva

Pedido do operador em 15/09/2026: *"essa skill irá te auxiliar para não
perder informações e nem precisar ficar pesquisando tudo novamente, essa
skill é atualizada automaticamente, quando você aprender uma informação
nova, salve nela"*.

Então: **aprendeu algo aqui, escreva aqui, no mesmo dia.** Sem esperar
que ele peça. O custo de escrever é um minuto; o custo de redescobrir foi
medido — o perfil ICC foi reaprendido três vezes, em 11, 14 e 15 de
setembro, cada vez a partir do zero, cada vez depois de uma chapa errada.

### O que merece entrar

Vale escrever quando a resposta a alguma destas for sim:

- **custou uma chapa, uma tiragem ou uma cobrança errada?** Esses são os
  caros. Vão para as Armadilhas, com o número que a arte tinha e a data;
- **o operador ditou uma regra?** Vai com as palavras dele, entre aspas.
  A frase original carrega o porquê, e o porquê é o que sobrevive quando
  o caso mudar um pouco;
- **eu medi alguma coisa?** O número vai junto. "O perfil come o preto" é
  opinião; "o K caiu de 0,0515 para 0,0060, 8,6 vezes" é fato, e quem
  ler depois pode conferir;
- **eu supus e estava errado?** Escreva a suposição também. Saber que o
  máximo sempre dá 100% vale tanto quanto saber o que fazer.

### O que NÃO entra

- **número que muda** — formato, dpi, tolerância, preço, pinça. Esses
  moram no `config.py`, com o comentário de onde vieram. Duas cópias
  envelhecem separadas, e a errada é sempre a que alguém lê;
- **o que o código já diz claramente.** Skill não é resumo do fonte: é o
  que o fonte **não** consegue dizer — a história, o erro, a decisão que
  poderia ter sido outra;
- **passo a passo de uso.** Isso é o `README.md`.

### Onde cada coisa vai

| | |
|---|---|
| custou caro, vale para todos | **Armadilhas**, aqui no `SKILL.md` |
| jeito de um cliente | `references/clientes.md` |
| cor, perfil, separação | `references/cor.md` |
| pinça, marca, giro, montagem, preflight | `references/arte.md` |
| o que ficou para a mão | `references/ainda-na-mao.md` |
| OS, estoque, banco | a skill `gerempre` |
| montagem e imposição | a skill `imposicao` |

Na dúvida entre duas gavetas, escreva na que você iria procurar primeiro
com o problema na mão — não na mais "correta".

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
| `src/finart_ctp/entrada_teams.py` | a ponte: do canal do cliente até a pasta do dia |
| `src/finart_ctp/prova.py` | a prova A4, e a **trava de cópia única** da armadilha 12 |
| `src/finart_ctp/america.py` | o sétimo cliente, que a FIA **monta** — ver a skill `imposicao` |
| `src/finart_ctp/utils.py` | `situacao_no_registro` — as três respostas da armadilha 10 |
| `src/finart_ctp/config.py` | **formatos, dpi, tolerâncias, limites, pinças** |
| `src/finart_ctp/tela.py` | a tela cheia que chama quando há pendência |
| `src/finart_ctp/estoque.py` | a folha de estoque do cliente, e a conferência com o GEREMPRE |
| `SPEC-guarda-de-regravacao.md` | por que a terceira resposta existe, com os dois acidentes |
| `tests/` | 699 testes; quase todo caso citado aqui tem um |

Os números ficam no `config.py` e não aqui: mudam, e duas cópias
envelhecem separadas. Os comentários de lá contam de onde veio cada um.
