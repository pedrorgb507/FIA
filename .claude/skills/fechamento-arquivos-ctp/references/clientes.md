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
| **FIALHO** | PDF no tamanho da chapa | 510x400 · 730x600 | `510x400_FIALHO_UNICIDADES 01` |
| **EMPORIO** | PDF, OS no nome | 510x400 · 660x605 | `510x400_CMYK_EMPORIO_01987_Guia` |
| **VIVA** | PDF | 510x400 | `510x400_CMYK_VIVA_GRADE 38 F` |
| **CREATIVE** | PDF **menor que a chapa** | 510x400 | `510x400_CMYK_CREATIVE_santinho cruvinel` |

`TOLERANCIA_MM = 3`. Fora disso a medida não casa e vira pendência.

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

## FIALHO BRINDES

Manda de tudo: PDF pronto, PDF fora de tamanho, Corel, arte por montar.

**Padrão temporário, combinado com o operador: só anda o que chega em PDF
já no tamanho final da chapa.** Qualquer outra coisa para e vira
pendência — não se dá andamento no serviço. Conforme os casos aparecerem,
amplia-se.

A chapa se chama pelo **nome principal do serviço**, que quase sempre é o
cliente final. `forro`, `miolo`, `capa` são tipo de material e não
identificam trabalho nenhum:

```
FORRO AGENDA unicidades 2027.pdf   ->   510x400_FIALHO_UNICIDADES 01
```

A lista do que se joga fora é `PALAVRAS_MATERIAL`, no `config.py`, **e é
para crescer**: toda vez que uma chapa sair com nome errado, a correção
costuma ser acrescentar a palavra ali.

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
