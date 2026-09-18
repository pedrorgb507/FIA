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

**Status:** ready-for-agent

- [ ] A fila mostra, de cada arquivo, se tem sangria
- [ ] A leitura usa a TrimBox declarada e a tinta além da marca de corte
- [ ] Arquivo sem TrimBox é julgado pela tinta, e não vira "sem sangria"
      por omissão
- [ ] Quando as duas leituras discordam, aparece aviso dizendo o que cada
      uma achou
- [ ] Teste: arquivo sangrado, arquivo sem sangria, arquivo sem TrimBox
      e arquivo em que as duas leituras divergem
