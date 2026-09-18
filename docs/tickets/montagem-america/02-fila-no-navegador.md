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

**Status:** done

- [x] A fila abre no navegador de outro PC da rede e lista o que está no
      portão
- [x] Cada item mostra tamanho, cor, número de páginas e se há marca de
      corte
- [x] A medição reaproveita o caminho que a FIA já usa para medir
      tamanho e tintas — não existe segunda conta na casa
- [x] O servidor roda separado do vigia, e derrubá-lo não afeta o
      fechamento dos outros clientes
- [x] Portão vazio mostra uma página dizendo que não há nada esperando,
      e não um erro
- [x] Teste: as funções do módulo devolvem a fila medida sem subir HTTP

**Onde ficou:** `montagem.medir_para_a_fila` e `montagem.fila_medida` (a
lógica), `src/finart_ctp/servidor.py` (a casca fina), `run_montagem.py` +
`iniciar_montagem.bat` (o arranque, separado do vigia),
`ferramentas/liberar_montagem_no_defender.ps1`, e
`tests/test_servidor_montagem.py`.

A medida é **guardada** em `_medidas_montagem.json`, no PC da FIA:
medir tinta roda o Ghostscript, que custa segundos por arquivo, e a tela
é atualizada à vontade por gente escolhendo o que montar. Medida que
falhou não se guarda — Ghostscript fora do ar é coisa de momento.

Arquivo que não deu para medir **continua aparecendo**, com o motivo:
sumir da fila é pior que aparecer sem medida, porque o arquivo está no
portão e é trabalho.

**Sobre a rede:** o servidor atende em `0.0.0.0`, mas na primeira vez o
Windows barra a porta — a página abre na máquina da FIA e não abre nas
outras, e isso parece defeito do programa. O `.ps1` acima abre a porta
8787 para a rede interna; roda uma vez, como administrador, só na máquina
da FIA.

Há teste que lê a fonte do servidor e reprova se aparecer Ghostscript,
pypdf ou leitura de marca ali dentro — a casca tem de continuar fina.
