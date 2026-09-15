# Os seis clientes

Cada um manda de um jeito e a chapa dele se chama de um jeito. A tabela
de formatos é **por cliente**: a chapa grande de um não existe no outro,
e casar a medida na tabela errada põe a arte na chapa errada.

Todos seguem a mesma árvore de pastas: `<base>\<MÊS>\<DIA>`. O programa
acha o mês mesmo escrito diferente na rede (`MARÇO`, `Marco`, `março`).

## De relance

| cliente | chega | formatos (mm) | nome da chapa |
|---|---|---|---|
| **SOLIDA** | PDF pronto, OS no nome | 510x400 · 775x635 | `49576R1` |
| **VOPRIX** | `.cdr`, convertido aqui | 510x400 | `510x400_CMYK_VOPRIX_M3RIN_panfleto` |
| **FIALHO** | PDF no tamanho da chapa | 510x400 · 730x600 | `510x400_FIALHO_CMYK_AGENDA_CADERNO 2027_ CREDI COMIGO` |
| **EMPORIO** | PDF, OS no nome | 510x400 · 660x605 | `510x400_CMYK_EMPORIO_01987_Guia` |
| **VIVA** | PDF | 510x400 | `510x400_CMYK_VIVA_GRADE 38 F` |
| **CREATIVE** | PDF **menor que a chapa** | 510x400 | `510x400_CMYK_CREATIVE_santinho cruvinel` |
| **PRIME** | `.cdr`, convertido aqui | 510x400 **com pinça** | `510x400_CMYK_PRIME_O.S 1034 - WAN` |
| **AMERICA** | PDF ou `.cdr`, **por montar** | 525x459 · 650x550 · 745x605 | `525x459_CMYK_AMERICA_Flyer Semana do Cliente` |

`TOLERANCIA_MM = 3`. Fora disso a medida não casa e vira pendência.

A **AMERICA** e a excecao do fluxo: ela nao e varrida como os
outros. O arquivo dela chega POR MONTAR e so e fechado depois
que uma pessoa o poe na subpasta `PARA CTP`.

Todas as chapas saem na mesma pasta `FIA` do dia — o próprio nome já diz
de quem é.

## SOLIDA

O caso original. PDF pronto, e o nome traz a OS na frente:
`49513 - Cliente - miolo CAD2.pdf`.

A chapa se chama **só pela OS**. A descrição (`capa`, `miolo CAD1`) não
entra:

| entra | sai |
|---|---|
| 510x400 | `49572` |
| 775x635 | `49576R1` (sufixo do formato grande) |
| 2 páginas | `49513R1 F` e `49513R1 V` |
| 3 ou mais | `49513 1`, `49513 2`, `49513 3` |
| várias OS no nome | `49581 49582 49583` |

Sem número de OS no nome, para. Duas artes do mesmo dia com a mesma OS e
o mesmo formato: a segunda sai `_v2` e o caso vira pendência.

**A SOLIDA não para por cor nem por resolução.** Arte de uma cor fecha
sozinha, como sempre fechou, e imagem abaixo de 200 dpi sai no log e
segue. A arte dela vem do cliente final e chega como chega — quem decide
o que é aceitável é quem conhece o trabalho. As outras travas continuam
valendo: fonte não incorporada, formato que não é chapa, arquivo grande
demais. Ver `arte.md`.

## VOPRIX

Manda `.cdr`, com a arte já montada no tamanho da chapa. O CorelDRAW
desta máquina publica em PDF antes de tudo, com a predefinição `FINART`.
É o único que vai pelo **caminho curto** — o PDF do Corel vai inteiro
para o CTP.

Nome de entrada: `Produto_medida_cores_Cliente.cdr`. A chapa leva o
**CLIENTE em maiúscula na frente, produto em minúscula atrás**:

| entra | sai |
|---|---|
| `Panfleto_15,0x21,0_4_0_M3RIN.cdr` | `510x400_CMYK_VOPRIX_M3RIN_panfleto` |
| `Envelope_Saco_23x31,5_Colegio_Unus.cdr` (só C e M) | `510x400_CM_VOPRIX_COLEGIO_UNUS_envelope_saco` |
| 2 páginas | `... 01` e `... 02` |

O cliente são os **dois últimos nomes** do arquivo, ou só o último quando
há um. Número solto não conta (`4_0`, a data `_31_08`); palavra de
ligação também não, senão `Campeao_Lubrificantes_e_Filtro` viraria
`E_FILTRO`. O produto é o que vem antes da medida.

As tintas do nome são **as que a arte usa de verdade**, não as do nome do
arquivo.

O cliente vem primeiro porque produto sozinho não identifica nada: dois
`Panfleto` chegaram no mesmo dia, de clientes diferentes, e foram para o
CTP como `Panfleto.pdf` e `Panfleto_v2.pdf`.

**MODELO** — mesmo cliente, mesmo produto, artes diferentes. As duas
passam a se chamar MODELO, e a que **já estava gravada é renomeada** para
`MODELO 1`. Uma com nome limpo e outra numerada esconderia que são duas.
O registro é acertado junto.

Usa **só a chapa pequena**, confirmado pelo operador. Uma arte dela em
775x635 não deveria existir; aparecendo, vira pendência em vez de OS com
preço chutado.

**Isto estava escrito aqui e o código não cumpria — até 11/09/2026.** O
VOPRIX não tinha tabela de formatos própria e caía na da SOLIDA, herdando
a 775x635 junto. O efeito não era um erro: era pior. A FIA **fechava** a
chapa grande do VOPRIX e só descobria o problema depois, na hora de
lançar — `GEREMPRE_CHAPAS` só tem a 510x400 para ele, `montar_vaga`
devolvia `None`, e a gravação ia para o CTP com uma pendência dizendo
"lance a mão". Chapa gravada, serviço entregue, e a cobrança dependendo
de alguém ler um aviso.

Agora existe `FORMATOS_VOPRIX`, e a medida para **na entrada**. A
etiqueta `VOPRIX F2` saiu junto do `ROTULOS_PROVA_VOPRIX`: etiqueta de
formato que não existe é armadilha esperando alguém devolver o formato
por engano.

**A lição vale além do VOPRIX, e virou teste.** São duas listas que
precisam andar juntas e moram em arquivos diferentes:
`FORMATOS_<cliente>` diz o que **vira chapa**, e `GEREMPRE_CHAPAS` diz o
que tem **preço**. Quando elas discordam, o serviço é gravado e não é
lançado — e ninguém vê, porque a chapa sai perfeita.
`test_todo_formato_que_a_FIA_FECHA_ela_sabe_COBRAR` varre os seis
clientes e falha se alguma medida estiver numa lista e não na outra.

## FIALHO BRINDES

Manda de tudo: PDF pronto, PDF fora de tamanho, Corel, arte por montar.

**Padrão temporário, combinado com o operador: só anda o que chega em PDF
já no tamanho final da chapa.** Qualquer outra coisa para e vira
pendência — não se dá andamento no serviço. Conforme os casos aparecerem,
amplia-se.

A chapa leva **tamanho, FIALHO, cores e o nome INTEIRO do arquivo**, sem
limite de letras:

```
AGENDA_CADERNO 2027_ CREDI COMIGO.pdf
   ->   510x400_FIALHO_CMYK_AGENDA_CADERNO 2027_ CREDI COMIGO
```

**Isto mudou em 14/09/2026, e a regra anterior era o contrário.** Até
esse dia a chapa se chamava pelo *nome principal do serviço*: jogavam-se
fora tipo de material, medida e número, e `FORRO AGENDA unicidades 2027`
virava só `UNICIDADES`.

A ideia era boa e o efeito foi ruim. O operador: *"eles estão mandando
arquivos parecidos, muda o nome, então vamos manter o padrão tamanho da
chapa, FIALHO, cmyk, só que no final coloca o nome completo do arquivo,
sem limites de caracteres"*.

**O que o resumo causava, medido no dia:** `AGENDA_2027_ CREDI COMIGO
capa.pdf` e `AGENDA_CADERNO 2027_ CREDI COMIGO.pdf` são dois serviços
diferentes e os dois viravam `510x400_FIALHO_CREDI COMIGO`. Como a
numeração olha o que já está na pasta, a segunda leva do dia saiu ` 02` e
` 03` — um serviço de **duas** páginas com numeração de **três** chapas,
e ninguém olhando a pasta saberia qual era qual.

**Por que sem limite:** quem corta perde justamente o pedaço que
distingue dois arquivos parecidos — que é o defeito que a regra veio
consertar. O `finalizar` continua tirando acento e caractere proibido,
como em todo cliente; só o comprimento é livre.

As **cores** entraram junto, para o Fialho ficar igual aos outros:
VOPRIX, EMPÓRIO e VIVA já traziam as tintas no nome. Elas acompanham a
**arte**, não o cliente — arte só de preto sai `_K_`.

O `PALAVRAS_MATERIAL` do `config.py` continua servindo ao **EMPÓRIO**,
que ainda resume.

**O número é por TRABALHO e por DIA, não por arquivo.** As 11 chapas de
UNICIDADES de um dia saíram 01 a 11 mesmo vindo de três PDFs diferentes.
Por isso a conta se faz olhando a pasta de saída. Chapa sozinha não leva
número; quando aparece a segunda, a primeira — que já está gravada — é
renomeada para ` 01`.

**Encaixe**, e só aqui: arte até `ENCAIXE_MAXIMO_MM` (15 mm) fora da
chapa entra centralizada, **cortando** o excesso dos dois lados. Nasceu
do `CAPA Agenda PAULISTA 2027.pdf`, que mede 520x400 numa chapa 510x400 —
os 5 mm de cada lado não têm nada. Acima do limite ninguém adivinha o que
pode ser cortado.

## EMPORIO PRINT

Só PDF. Nome `OS - descrição`: `01995 - CHAPA CAIXA 4796.pdf`.

Entra como a SOLIDA e sai como a VOPRIX — formato, cores e cliente no
nome:

```
510x400_CMYK_EMPORIO_01987_Guia
660x605_GRAY_EMPORIO_01965_Maria Flor
510x400_CMYK_EMPORIO_01995_CAIXA 4796_1     (página 1)
```

A descrição vem do arquivo, sem as palavras que só dizem que aquilo é
trabalho de chapa (`PALAVRAS_SERVICO_EMPORIO`), cortada em
`MAXIMO_DESCRICAO_EMPORIO` letras, respeitando a palavra.

**VERNIZ não entra nessa lista de propósito** — chapa de verniz precisa
aparecer no nome. E arquivo com `verniz` no nome **não fecha sozinho**:
verniz se confere antes. Vale para EMPORIO, VIVA e CREATIVE; na SOLIDA
sempre fechou e mudar isso pararia serviço que hoje anda.

## VIVA ACABAMENTOS

Manda PDF e `.cdr`, mas **só o PDF anda** — o `.cdr` para e vira
pendência, como no Fialho. Uma chapa só: 510x400.

O nome de saída usa o próprio nome do arquivo como descrição, e frente e
verso saem F e V:

```
GRADE 1637.pdf  ->  510x400_CMYK_VIVA_GRADE 1637
GRADE 38.pdf    ->  510x400_CMYK_VIVA_GRADE 38 F  e  ... V
```

**Reaproveita nome de grade.** O `GRADE 40` de 2026 casou com o `GRADE
40` da mesma cliente de 2024 e a prova saiu com o número de uma OS de
dois anos atrás impresso no verso. A busca por serviço já lançado tem
janela de dias e filtro de cliente — ver a skill `gerempre`.

Há **dois cadastros de VIVA** no GEREMPRE, e o trabalho de chapa vai no
511.

## CREATIVE

Só PDF, mesma conferência do EMPORIO. Não usa OS no nome — manda o nome
do serviço (`santinho cruvinel.pdf`).

**O que muda: a arte NÃO vem no tamanho da chapa.** Chega menor —
480x330, por exemplo — e é o programa que a monta na 510x400, trabalho
que até então era feito à mão no InDesign. Duas regras, ditadas pelo
operador:

- centralizada na largura;
- **pinça** no pé: `PINCA_CREATIVE_MM` (40 mm) da marca de corte até a
  borda da chapa.

E a arte que chega **em pé** é girada para deitar (`GIRO_CREATIVE = 270`,
para a esquerda) — "deixar da forma que sempre vem". Girar 90 graus não
mexe em nada do desenho: troca linha por coluna, e o tamanho nunca muda.

Como a pinça se mede e por que isso é delicado: `arte.md`.

## PRIME

Entrou em 14/09/2026. Cliente `502` no GEREMPRE, chapa `88`
(`510X400 - PRIME F4`), R$ 10,00, chapa **do cliente**.

```
V:\Prime  Graf\<MES>\<DIA>          note os DOIS espaços no nome da pasta
```

Manda `.cdr`, como a VOPRIX — convertido pelo CorelDRAW a 1000 dpi. Uma
chapa só: **510x400, pinça de 28 mm**.

**A pinça se mede da MARCA DE CORTE**, não da borda do arquivo — igual à
CREATIVE. E há um detalhe que o operador ditou e que não se adivinha:
*"pode acontecer de vir com duas marcas, você sempre deve pinçar a partir
do de cima"*.

**A montagem fica na pasta do dia**, com `_montagem` no fim do nome, e é
**dela** que a chapa do CTP sai — não do arquivo solto. Assim o que foi
gravado é exatamente o que está ali para ser conferido. O vigia pula os
`_montagem`: são saída nossa, não entrada.

**O número no nome não identifica o serviço.** Ela põe `O.S 1034 - ...` na
frente, mas essa O.S **se repete entre trabalhos** — por isso a PRIME
está fora de `CLIENTES_COM_OS_NO_NOME`, e por isso um nome comprido dela
vira dúvida em vez de casar com outro (armadilha 16).

Ela também descarta tinta de traço: `CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO`.

## AMERICA

O sétimo cliente, e o único que a casa **monta**. Por isso ele não é
varrido como os outros: o arquivo chega por montar, e só vira chapa
depois que uma pessoa revisa e põe no portão.

```
V:\AMERICA\<Mes>\<Dia>\             ← chega aqui. NÃO se toca.
V:\AMERICA\<Mes>\<Dia>\PARA CTP\    ← só o que está aqui é fechado
```

Três máquinas, e a pinça é da **máquina**, não do formato:

| chapa | pinça | apelido | GEREMPRE |
|---|---|---|---|
| 525x459 | 60 mm | PM_52 | 90, R$ 8,00 |
| 650x550 | 60 mm | MOZP_FT2 | 91, R$ 12,00 |
| 745x605 | 62 mm | SM_74 | 89, R$ 12,00 |

A regra de máquina: até o formato 4 vai na PM_52; acima dele, colorido
vai na SM_74 e preto-e-branco na MOZP. Mas **quem manda é caber com a
pinça** — não cabendo na da regra, procura-se outra, e o log diz por quê.

### O `.cdr` no portão — 15/09/2026

Ela também manda `.cdr`, e aqui ele **não se rasteriza**: a AMÉRICA
manda a montagem pronta, com a imagem já dentro do arquivo. O `.cdr` só é
publicado em PDF pelo motor da Corel, e esse PDF já é a chapa.

**A pinça NÃO sai da marca de corte aqui**, e isso foi medido antes de
decidir: das **oito** montagens que existiam na pasta em 15/09/2026,
**nenhuma** tem marca que o `marcas_de_corte` reconheça. Nas que já vêm
no tamanho da chapa a faixa dos 40 mm está vazia — a arte começa acima
dela.

O que as montagens de verdade mostram, medindo a **tinta**:

```
#1304-26-CONVITE-MEETING_MONTAGEM   525x459   esq 37,5  dir 37,5  pé 46,5
Flyer Semana do Cliente_MONTAGEM    525x459   esq 35,0  dir 35,0  pé 45,0
```

Centradas ao milímetro, com a tinta ~15 mm **abaixo** da pinça de 60: as
marcas de corte e registro vivem dentro da pinça. Daí a folga de 20 mm na
conferência.

Quatro caminhos, e o terceiro é o que importa:

| o que chega | o que a FIA faz |
|---|---|
| já no tamanho de uma chapa | não monta; **confere** a pinça pela tinta e só avisa |
| menor, e cabe com a pinça | monta centrada, pé da arte na pinça |
| só cabe **deitada** | **para e pergunta** |
| não cabe em nenhuma | para |

Não se gira sozinho: sem marca de corte não dá para saber que lado é o
pé, e girar errado põe a arte de cabeça para baixo na máquina.

**O portão nunca pode ficar com dois PDFs.** Montando, o PDF solto
publicado sai para a pasta do dia — ficando os dois, a volta seguinte
acharia duas chapas para o mesmo serviço, duas gravações e duas OS. O
`.cdr` também sai do portão, mas **movido e não apagado**: ele é a fonte
da montagem.

O resto do caminho dela — o apagar do portão, que é o único passo
irreversível — está em `src/finart_ctp/america.py` e na skill
`imposicao`, em `references/america.md`.
