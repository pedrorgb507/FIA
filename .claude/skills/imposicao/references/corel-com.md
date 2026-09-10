# Mexer no CorelDRAW por programa

O CorelDRAW se comanda por COM (`win32com.client.Dispatch("CorelDRAW.Application")`).
É o mesmo programa que o operador tem aberto na tela — então tudo aqui
acontece **na sessão dele**, e isso é a primeira coisa a respeitar.

O que o programa já usa em produção está em `src/finart_ctp/corel.py`:
abrir sem roubar o arquivo de quem está mexendo, carregar a predefinição
`FINART`, exigir os ajustes de PDF em vez de herdá-los, e publicar.

## As unidades — a que custou mais caro

```
doc.Unit = 3    milímetro
doc.Unit = 9    didot  (0,376 mm)
```

**Eu usei 9 achando que era milímetro**, em 10/09/2026. Consequência: uma
arte de 444×291 mm foi medida e relatada como **1181×773 mm**, e eu
cheguei a propor partir o trabalho em quatro chapas — de um arquivo que
cabia inteiro numa. O operador desfez na hora, olhando o arquivo.

O erro é silencioso: nada falha, os números só ficam 2,66 vezes maiores.
Foi descoberto porque o PDF exportado saía com 191,72 mm quando se pedia
510, e a razão era constante — `543,46 pt ÷ 510 = 1,0656`, que é o ponto
didot.

→ **Confira a unidade lendo uma medida conhecida de volta**, não
confiando no nome da constante. Se a página deveria ter 510 mm e o Corel
diz outra coisa, a unidade está errada.

## A ordem das operações

**Mudar o tamanho da página não mexe na arte — mexe na página.** A página
encolhe **pelo centro**, e a arte fica onde estava em coordenada
absoluta.

Então a conta da pinça só vale **depois** de a página já ser do tamanho
da chapa. Fazer antes põe a arte num lugar que deixa de existir.

```
1. agrupar o conteúdo
2. pôr a página no tamanho da chapa
3. só então posicionar o grupo
4. publicar o PDF
```

## Posicionar: use a borda que você quer mandar

`SetPosition(x, y)` **ancora pelo TOPO da forma**, não pela base. Pedir
`y = 28` põe o topo em 28 e joga a base para -745.

→ Use `LeftX` / `BottomY`, que dizem por escrito qual borda está sendo
mandada:

```python
grupo.BottomY = PINCA_MM                          # o pé
grupo.LeftX = (CHAPA_L - grupo.SizeWidth) / 2.0   # centralizado
```

E confira lendo de volta, no próprio Corel, antes de publicar.

## Exportar a PÁGINA, não o objeto

`UsePageBoundingBox = True`. Com `False`, o PDF sai do tamanho da caixa
do objeto — a arte, e não a chapa. A página inteira é o que interessa:
é ela que é a chapa.

## O que não fazer

- **não salvar o `.cdr`.** O arquivo é do cliente e está aberto na
  máquina de alguém. Mexer na página e no posicionamento é para gerar o
  PDF, não para alterar o original;
- **não carregar a predefinição `FINART` quando o pedido é não converter
  cor.** É ela que converte para CMYK. Quando o pedido for "sem converter
  nada", o que se ajusta é só o que **impede** alteração: ZIP sem perda,
  reamostragem desligada;
- **não encostar num documento que já está aberto** sem saber. O
  `corel._documento_aberto()` existe para isso — o operador pode estar
  no meio de um trabalho.

## O caso que ensinou tudo isto

`MEGA MOVEIS - CUPOM1.cdr`, 10/09/2026. Montagem de 12 cupons 6×2, cada
um **62,6 × 129,3 mm**, mais 13 marcas de corte — arte total
**443,97 × 290,65 mm**.

Pedido: página 510×400 (o tamanho da chapa), pinça de 2,8 cm **medida da
marca de corte**, agrupar o conteúdo, gerar o PDF ao lado, sem converter
nada e **sem mexer em tamanho nem em montagem**.

Resultado aceito pelo operador:

```
MEGA MOVEIS - CUPOM1.pdf     510,00 × 400,00 mm     8,74 MB
   marca de corte do pé      28,00 mm da borda de baixo
   arte centralizada na largura
```

Os traços de corte eram o objeto mais baixo do arquivo — **4,3 mm**
abaixo do cupom. Por isso `grupo.BottomY = 28` põe **a marca** em 28, que
é o que foi pedido. Medir do cupom teria posto tudo 4,3 mm fora: pouco no
papel, e o bastante para o operador ver na hora.

**Atenção ao ler medidas antigas deste caso.** Tudo que foi medido antes
de a unidade ser consertada está em **didot**, e parece 2,66 vezes maior.
Para converter: `mm = didot × 0,3759`. Confere nos dois lados — os
1181 × 773 daquela primeira leitura dão 443,9 × 290,6, que é a arte de
verdade.
