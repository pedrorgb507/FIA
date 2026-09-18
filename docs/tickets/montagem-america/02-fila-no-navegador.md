# 02: A fila no navegador, com o arquivo já medido

**What to build:** A equipe abre uma página no navegador e vê o que está
esperando montagem, já medido pela FIA — sem abrir o PDF, sem conferir
tamanho na mão, sem perguntar a ninguém.

De cada arquivo a fila mostra: o tamanho em milímetros, se é colorido ou
preto-e-branco, quantas páginas tem e se foi encontrada marca de corte.
A cor não é enfeite: é ela que decide entre a SM 74 e a MOZP na regra da
casa.

O servidor roda na máquina da FIA (é lá que se alcança `V:` e `W:`) e é
acessível pelos PCs da equipe, pela rede interna. Ele é processo
separado do vigia: o servidor cair não pode derrubar o fechamento dos
outros clientes.

A lógica mora num módulo próprio e a camada HTTP é casca fina — nada de
regra dentro do servidor.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A fila abre no navegador de outro PC da rede e lista o que está no
      portão
- [ ] Cada item mostra tamanho, cor, número de páginas e se há marca de
      corte
- [ ] A medição reaproveita o caminho que a FIA já usa para medir
      tamanho e tintas — não existe segunda conta na casa
- [ ] O servidor roda separado do vigia, e derrubá-lo não afeta o
      fechamento dos outros clientes
- [ ] Portão vazio mostra uma página dizendo que não há nada esperando,
      e não um erro
- [ ] Teste: as funções do módulo devolvem a fila medida sem subir HTTP
