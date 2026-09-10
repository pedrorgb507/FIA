# A chapa e a pinça de cada gráfica

O operador mantém à mão, há anos, um `CHAPAS E PINCAS.TXT`: cada gráfica
atendida, o formato da chapa dela, e quantos centímetros de pinça aquela
máquina pede. **199 gráficas, 233 pares de chapa e pinça.**

Lido em 10/09/2026 por `ferramentas/ler_chapas_e_pincas.py`, que só lê.

> **CUIDADO COM O ARQUIVO DE ORIGEM.** Ele também guarda, no meio do
> texto, senha de Teams, de e-mail, de FTP, de webmail (com URL de
> sessão), de Skype e de wi-fi. A pasta onde ele mora está no
> `.gitignore`, e a ferramenta extrai **exatamente dois padrões** —
> medida de chapa e valor de pinça — ignorando todo o resto sem olhar.
> Ao mexer nela, mantenha isso: um script que extraia "tudo" passa a
> vazar credencial.

## A regra que a lista inteira ensina

**A pinça é da MÁQUINA, não do formato.** É o achado mais importante
daqui, e ele impede um erro fácil:

| chapa | gráficas | pinças encontradas |
|---|---|---|
| 521 × 415 | 54 | 30, 35, 40, 45 mm |
| 510 × 400 | 31 | **27, 28, 29, 30, 31, 32, 35, 40 mm** |
| 745 × 605 | 29 | 50, 53, 55, 59, 60, 62, 63, 65 mm |
| 660 × 605 | 26 | 60, 65, 68, 70, 75, 80 mm |
| 660 × 530 | 25 | 30, 35, 40, 45, 50, 55 mm |

Trinta e uma gráficas usam a mesma chapa 510 × 400, com **nove valores
diferentes** de pinça. Então:

> **Nunca deduza a pinça do tamanho da chapa.** Saber o formato não é
> saber a pinça — é preciso saber em qual máquina o trabalho vai correr.

## A chapa 525 × 459 — a do flyer 15×21

Seis gráficas usam, e **todas com 6 cm**:

| gráfica | pinça |
|---|---|
| Gráfica América — `CHAPA PM 52` | 60 mm |
| Barramares | 60 mm |
| Fabiano / Coprint — *palmares* | 60 mm |
| Multimpressões | 60 mm |
| Imprensa Bíblica — `hemdeberg MS-52` | 60 mm |
| Palmares | 60 mm |

`PM 52` e `MS-52` são a **Heidelberg Printmaster 52** — chapa de
459 × 525, meio ofício. Isso confirma os 60 mm que o operador deu para o
flyer, e **desmente o 50 mm** que eu tinha lido de um modelo do Preps
(`references/preps.md`): aquele modelo é de outra máquina.

## Os clientes da FIA, conferidos contra o código

| cliente | o que o `config.py` tem | o que a lista diz |
|---|---|---|
| **CREATIVE** | 510×400, pinça **40 mm** | `GTO 52`, 510×400, pinça **4,0 cm** ✓ |
| **FIALHO** | 510×400 e 730×600 | 510×400 pinça 3 cm · 730×600 pinça 5 cm ✓ |
| **EMPORIO** | 510×400 e 660×605 | `EMPORIO PRINT` 510×400 pinça 3,0 cm |
| **SOLIDA** | 510×400 e 775×635 | 745×605 (6,5 cm) · 775×635 · 510×400 (2,8 cm) |
| VIVA · VOPRIX | 510×400 | não estão na lista |

**A CREATIVE bate exatamente**, pinça inclusive — os 40 mm que estão no
`PINCA_CREATIVE_MM` são os 4,0 cm da lista, e a máquina é uma GTO 52.
O FIALHO bate nos dois formatos.

Três coisas para olhar, que a conferência levantou:

**1. A SOLIDA tem um terceiro formato que a FIA não conhece:
745 × 605**, com pinça de 6,5 cm — e uma observação do operador junto:
*"quando tiver mancha na sangria do lado de baixo, a pinça será sempre
de 6,5 cm"*. Hoje o `config.py` só tem 510×400 e 775×635.

**2. O 2,8 cm da SOLIDA em 510×400** é a mesma pinça pedida no serviço
`MEGA MOVEIS - CUPOM1` (ver `SKILL.md`). Confere.

**3. O 775 × 635 da SOLIDA está escrito como "3 mm de pinça"** — e é o
único da lista inteira em milímetro. Todo o resto está em centímetro.
Pode ser 3 cm escrito errado, pode ser 3 mm de verdade. **Não use sem
perguntar.**

## Os formatos que aparecem

Ordenados por quantas gráficas usam: 521×415 (54), 510×400 (31),
745×605 (29), 660×605 (26), 660×530 (25), 730×600 (8), 720×557 (7),
724×615 (7), 415×279 (5), 650×550 (5).

Os dois primeiros são o **formato 4** e o **formato 2** da tabela de
papéis (ver `fundamentos.md`), e a lista toda gira em torno de meia dúzia
de máquinas comuns no mercado de Goiânia.

## Anotações do operador que valem regra

Espalhadas pela lista, e cada uma é um caso que já mordeu alguém:

- **Gráfica Leão** — chapa 485×335, mas *"cortar na 510×400
  centralizada, sem bordas azuis no canto"*; e a pinça é **vertical**,
  25 mm, *"no início da impressão"*;
- **Gráfica Nativa** — serviços da VIP Color pinçam **a partir da aba de
  cola**, não da borda; e *"para duas sacolas montadas no F2 com aba de
  cola do lado da pinça, pinçar com 2,4 cm"*;
- **Papel de seda (Nativa)** — 720×557, 3,3 cm *"pela base inferior,
  **sem marca de corte**"*;
- **RAMOS** — 745×605 com 53 mm, e *"em arquivos coloridos que sejam F2,
  deslocar 7,5 mm para a direita"*;
- **Sarel** — 415×280 **em pé**, *"pinça de baixo pra cima"*;
- **NILART** — 521×415 **dividida ao meio**, final 415 × 260,5;
- **Jornal Gazeta** — 860×605, pinça 2,0 cm, *"gravar com 130 linhas"*;
- **Poder** — 745×605, *"4 pinça **na mancha**"* — medida da mancha, não
  da borda;
- **Jornal O Hoje** · **Goskomult** · **Imprensa Bíblica** —
  **centralizado**, sem pinça declarada.

O padrão que se repete: **a pinça nem sempre se mede da borda da chapa.**
Pode ser da aba de cola, da mancha, da marca de corte (o caso da
CREATIVE, em `arte.md`), e pode vir de baixo para cima. Ao montar para
uma gráfica nova, essa é a primeira pergunta.

## Limites da leitura

A ferramenta acerta as medidas, mas **erra alguns nomes de gráfica**: o
arquivo separa as gráficas por linhas de `___`, e as entradas variam
demais de feitio — algumas trazem o nome da máquina antes da chapa, e a
heurística cola a medida na linha errada. Para consulta pontual,
**confira no arquivo**; para estatística de formato e de pinça, a leitura
é boa.

Um artefato conhecido: em `580×505` aparece uma "pinça" de 708 mm, que na
verdade veio de *"(708 × 510 mm p/ cortar)"* na mesma linha.
