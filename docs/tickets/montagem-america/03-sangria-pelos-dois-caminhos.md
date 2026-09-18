# 03: A sangria, lida pelos dois caminhos

**What to build:** A fila passa a dizer se o arquivo já veio sangrado —
para ninguém montar como se tivesse sangria o que não tem.

A leitura é feita por dois caminhos, porque cada um cobre o buraco do
outro: a TrimBox declarada dentro do arquivo, e a tinta que passa além
da marca de corte. Muitos arquivos não trazem TrimBox; medir tinta custa
rasterizar.

Quando os dois discordarem, o sistema **fala**, em vez de escolher um e
calar. Arquivo que declara uma coisa e mostra outra é justamente o que
engana.

**Blocked by:** 02

**Status:** done

- [x] A fila mostra, de cada arquivo, se tem sangria
- [x] A leitura usa a TrimBox declarada e a tinta além da marca de corte
- [x] Arquivo sem TrimBox é julgado pela tinta, e não vira "sem sangria"
      por omissão
- [x] Quando as duas leituras discordam, aparece aviso dizendo o que cada
      uma achou
- [x] Teste: arquivo sangrado, arquivo sem sangria, arquivo sem TrimBox
      e arquivo em que as duas leituras divergem

**Onde ficou:** `src/finart_ctp/sangria.py` (as duas leituras e a
divergência), a coluna e o aviso no `servidor.py`, os campos na
`montagem.medir_para_a_fila`, e `tests/test_sangria.py`.

**A armadilha que este ticket existe para evitar:** faltando a TrimBox, a
especificação do PDF manda ela valer o MediaBox — então a conta acha zero
e responde "pelado" com toda a confiança. Não é pelado: é **não
declarado**. Por isso `sangria_declarada` devolve `None`, e não `0`,
quando a caixa não está lá — é a diferença que decide se a tinta é
consultada.

**A segunda armadilha:** a marca de corte *é* tinta, e mora fora da linha
de corte de propósito. Contando "qualquer tinta além da linha", todo
arquivo com marca pareceria sangrado. O que conta é o desenho — faixa
larga —, com os mesmos números (`RISCO_MM`, `PX_POR_MM`) que o
`america.medir_o_pe` usa para a pinça.

**A coluna tem três respostas, não duas:** "sim", "não veio sangrada" e
"não dá para saber". A terceira é resposta, não falha — acontece quando
nenhuma das leituras respondeu, ou quando as duas responderam coisas
diferentes. Na divergência a tela abre uma linha de aviso com os dois
números, porque quem decide é gente.

A conta de quanto o arquivo já tem de sangria **saiu de
`ferramentas/sangrar.py`** e passou a morar em `src`: a fila precisava
dela e `src` não importa de `ferramentas`. O `sangrar.py` a importa de
volta, com os mesmos nomes — uma conta só na casa, e há teste que confere
que são o mesmo objeto.
