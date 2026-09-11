@echo off
REM ---------------------------------------------------------------------
REM  ARRANQUE AUTOMATICO DO CTP - chamado pelo atalho na pasta
REM  Inicializar do Windows, a cada logon.
REM
REM  Pedido do operador em 11/09/2026: ligar o computador e o programa ja
REM  estar rodando, sem ninguem clicar em nada.
REM
REM  O QUE ELE FAZ, e por que nesta ordem:
REM
REM  1. ESPERA O V: APARECER. As pastas dos clientes estao em unidade de
REM     rede, e no logon o Windows ainda esta mapeando. Abrir antes disso
REM     nao quebra nada - o programa diz "esperando a pasta do dia" e
REM     segue -, mas a primeira volta do laco sairia cega, e o log comeca
REM     com um susto que nao e susto.
REM
REM  2. ABRE O VS CODE NA PASTA DO PROJETO. A tarefa "Iniciar CTP" do
REM     tasks.json esta marcada com runOn: folderOpen, entao ela sobe
REM     sozinha no terminal integrado.
REM
REM  NAO chama o run_ctp.py direto de proposito: assim teriamos DOIS
REM  caminhos de arranque, e um dia os dois rodariam juntos. Quem sobe o
REM  programa e a tarefa do VS Code, e so ela.
REM
REM  PARA DESLIGAR: apague o atalho da pasta Inicializar. Abra o
REM  Executar (tecla Windows + R) e digite  shell:startup
REM ---------------------------------------------------------------------

cd /d "%~dp0"

REM --- espera o V: por ate 3 minutos, olhando de 5 em 5 segundos ---
set TENTATIVAS=36
:esperar
if exist "V:\" goto achou
set /a TENTATIVAS-=1
if %TENTATIVAS% LEQ 0 goto desistiu
timeout /t 5 /nobreak >nul
goto esperar

:achou
echo Unidade V: pronta. Abrindo o VS Code...
goto abrir

:desistiu
echo AVISO: o V: nao apareceu em 3 minutos. Abrindo assim mesmo -
echo o programa espera a pasta do dia sozinho e avisa no log.

:abrir
REM 'code' abre a pasta e dispara a tarefa marcada com folderOpen.
REM Ja estando aberta nesta mesma pasta, ele so traz a janela para a
REM frente e NAO roda a tarefa de novo - que e o certo.
call code "%~dp0."
exit /b 0
