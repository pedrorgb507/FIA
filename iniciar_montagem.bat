@echo off
REM ---------------------------------------------------------------------
REM  A FILA DA MONTAGEM DA AMERICA - e este atalho NAO a sobe mais.
REM
REM  Ele abre o VS CODE na pasta do projeto, e quem sobe a fila e a
REM  tarefa "Iniciar montagem AMERICA" do tasks.json, que esta marcada
REM  com runOn: folderOpen e roda no TERMINAL INTEGRADO.
REM
REM  ---------------------------------------------------------------------
REM  POR QUE ELE DEIXOU DE SUBIR SOZINHO - 22/09/2026
REM
REM  Ordem do operador: "te disse pra abrir tudo no terminal Iniciar
REM  montagem AMERICA do vs code". Ele nao quer janela preta na tela, e
REM  tem uma razao melhor que estetica atras disso.
REM
REM  ATE HOJE HAVIA DOIS CAMINHOS para subir a mesma fila: este .bat e a
REM  tarefa do VS Code. E nao era so redundancia - ELES BRIGAVAM. Este
REM  arquivo matava quem segurasse a porta 8787 antes de subir, e quem
REM  segurava a porta era, muitas vezes, o servidor da TAREFA. Entao
REM  clicar aqui derrubava o que estava funcionando para por outro no
REM  lugar, numa janela separada que ninguem fecha.
REM
REM  Aconteceu as 17:00 de 22/09: a equipe abriu a fila de outro PC, esta
REM  maquina ficou com DOIS servidores - o de 17:00:51 vindo de um cmd e
REM  o de 17:04:28 vindo do VS Code - e o operador viu a janela preta
REM  abrir sozinha na tela dele.
REM
REM  O IRMAO DESTE ARQUIVO JA TINHA APRENDIDO ISSO. Esta escrito no
REM  iniciar_no_arranque.bat, sobre o vigia: "NAO chama o run_ctp.py
REM  direto de proposito: assim teriamos DOIS caminhos de arranque, e um
REM  dia os dois rodariam juntos". A montagem so nao tinha recebido a
REM  mesma licao - agora recebeu.
REM
REM  ---------------------------------------------------------------------
REM  O QUE SE PERDEU, E ONDE FOI PARAR
REM
REM  Este .bat guardava tres manhas de aprendizado sobre matar o servidor
REM  anterior antes de subir: que fechar a janela preta no X nem sempre
REM  mata o python; que um servidor velho segurando a 8787 faz a pagina
REM  abrir bonita servindo codigo de uma hora atras; e que quem segura a
REM  porta as vezes tem a LINHA DE COMANDO VAZIA, entao procurar por
REM  nome nao o encontra - quem responde e o netstat.
REM
REM  Nada disso se perde, muda de dono: com UM caminho so, nao ha
REM  anterior para matar. Recarregar a janela do VS Code
REM  (Ctrl+Shift+P > Developer: Reload Window) derruba a tarefa e sobe
REM  outra, uma de cada vez, sem ninguem precisar cacar processo.
REM ---------------------------------------------------------------------
title FINART - abrindo a fila da montagem pelo VS Code
cd /d "%~dp0"

echo.
echo   A FILA DA MONTAGEM SOBE PELO VS CODE, nao por esta janela.
echo.

REM --- ja esta no ar? entao nao ha nada a fazer, e dizer isso importa:
REM     quem clicou aqui estava tentando ligar alguma coisa. ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$c = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue;" ^
  "if ($c) { Write-Host '   A fila JA ESTA NO AR na porta 8787 - nao subi outra.'; Write-Host ''; Write-Host '   Abra:  http://localhost:8787/'; exit 1 } else { exit 0 }"

if errorlevel 1 goto fim

echo   Abrindo o VS Code na pasta do projeto...
echo   A tarefa "Iniciar montagem AMERICA" sobe sozinha, no terminal de baixo.
echo.
start "" code "%~dp0."

echo   Ja com o VS Code aberto, a tarefa nao sobe de novo sozinha.
echo   Nesse caso:  Ctrl+Shift+P  ^>  Run Task  ^>  Iniciar montagem AMERICA
echo.

:fim
echo   Pressione uma tecla para fechar.
pause >nul
