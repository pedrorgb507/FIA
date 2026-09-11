---
name: fechamento-arquivos-ctp
description: Fechar arquivo de cliente e entregar a chapa para o CTP - receber a arte, medir o formato, conferir por dentro, decidir a cor, imprimir a prova e gravar. Use sempre que aparecer chapa, CTP, gravacao, prova, quadricromia, escala de cinza, perfil de cor, separacao de tintas, resolucao de imagem, traco fino, pinca, marca de corte, sangria, CorelDRAW, Ghostscript, pendencia, chapa duplicada, a entrada pelo Teams/OneDrive, ou arquivo dos clientes SOLIDA, VOPRIX, FIALHO, EMPORIO, VIVA e CREATIVE - e tambem para entender por que uma chapa saiu errada.
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
continua valendo. `ferramentas/consertar_corel.ps1` faz isso e é
reexecutável; também aponta para o perfil atual os caminhos de backup
automático que estavam num `C:\Users\Administrator` que não existe mais —
essa parte só pega com o Corel fechado.

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
| `src/finart_ctp/config.py` | **formatos, dpi, tolerâncias, limites** |
| `SPEC-guarda-de-regravacao.md` | por que a terceira resposta existe, com os dois acidentes |
| `tests/` | 420 testes; quase todo caso citado aqui tem um |

Os números ficam no `config.py` e não aqui: mudam, e duas cópias
envelhecem separadas. Os comentários de lá contam de onde veio cada um.
