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

**Status:** done

- [x] Clicar num arquivo da fila abre o painel daquele arquivo
- [x] Tamanho, cor e páginas já vêm preenchidos do que foi medido
- [x] A máquina vem sugerida pela regra da casa e pode ser trocada
- [x] A tabela de formatos e as chapas vêm do `config`, e a cópia em
      JavaScript deixa de existir
- [x] Os avisos que o painel já dava continuam funcionando: não cabe na
      área útil, não cabe no formato, célula vazia
- [x] O provador do painel passa a conferir também os campos
      pré-preenchidos

**Onde ficou:** `montagem.chapas_da_casa`, `montagem.formatos_da_casa`,
`montagem.sugestoes_para` e `montagem.dados_do_painel` (a lógica),
`servidor.pagina_do_painel` + a rota `/painel?arquivo=` (a casca), a
cirurgia no `ferramentas/painel_imposicao.html`, e seis casos novos no
`ferramentas/provar_painel.py` — 15 de 15 no Edge sem tela.

**A cópia morreu.** As duas tabelas — chapas e formatos — saíam escritas
em JavaScript dentro do painel, e o comentário no config dizia "mudou
aqui, muda lá". O painel agora recebe as do `config`, e há teste que lê a
fonte dele e reprova se qualquer medida voltar a aparecer escrita à mão.

**O painel não abre mais solto, e isso é deliberado:** sem as tabelas ele
para e diz por onde entrar. Trabalhar com tabela vazia seria pior —
diria "cabe" sobre uma chapa que não existe.

**O tamanho pré-preenchido é o do CORTE, não o do papel.** O campo do
painel é a peça e a sangria entra num campo separado: um arquivo de
100x150 com 3 mm de sangria tem papel de 106x156, e preencher com 106x156
contaria a sangria duas vezes — a peça sairia 6 mm maior do que o cliente
pediu. Entrou `sangria.medida_do_corte`, que usa a TrimBox declarada
quando ela existe.

**Páginas não tem campo no painel** — viraram sugestão de tipo, que é o
único lugar onde essa medida muda uma decisão: uma página não tem verso,
duas quase sempre são frente e verso. Três ou mais não se adivinha (é o
ticket 09).

A ficha da 650x550 passou a se ler **"MOZP FT2"** em vez de "MOZP": o
rótulo agora vem do apelido que está no config, e é o mesmo nome que o
GEREMPRE usa.
