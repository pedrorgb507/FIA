# 04: O painel abre da fila, servido e pré-preenchido

**What to build:** Quem escolhe um arquivo na fila cai no painel de
montagem — o mesmo que a casa já usa, que desenha a chapa em escala e
responde a cada campo digitado. A diferença é que agora ele já chega
sabendo do arquivo.

Os campos vêm preenchidos com o que foi medido: tamanho, cor, páginas.
E a máquina vem **sugerida** pela regra da casa — até o formato 4 na
PM 52; acima, colorido na SM 74 e preto-e-branco na MOZP. Sugerida, não
imposta: o operador disse "geralmente", e quem manda é a mensagem da
AMÉRICA. Trocar é um clique.

O resto continua digitado, como foi decidido quando o painel deixou de
escolher: exposições, colunas × linhas, vão, formato. O painel lê,
desenha e avisa.

Sendo servido, o painel passa a receber a tabela de formatos e as chapas
do `config` de verdade — **e a cópia em JavaScript morre**. Era o preço
de ser página sem servidor, e o preço acabou.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Clicar num arquivo da fila abre o painel daquele arquivo
- [ ] Tamanho, cor e páginas já vêm preenchidos do que foi medido
- [ ] A máquina vem sugerida pela regra da casa e pode ser trocada
- [ ] A tabela de formatos e as chapas vêm do `config`, e a cópia em
      JavaScript deixa de existir
- [ ] Os avisos que o painel já dava continuam funcionando: não cabe na
      área útil, não cabe no formato, célula vazia
- [ ] O provador do painel passa a conferir também os campos
      pré-preenchidos
