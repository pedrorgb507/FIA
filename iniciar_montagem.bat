@echo off
REM ---------------------------------------------------------------------
REM  A FILA DA MONTAGEM DA AMERICA, no navegador.
REM
REM  Sobe o servidor que a equipe abre do PC dela para ver o que esta
REM  esperando montagem, ja medido.
REM
REM  E PROCESSO SEPARADO DO VIGIA, de proposito: esta janela fechar nao
REM  para o fechamento de chapa dos outros clientes, e o vigia cair nao
REM  derruba esta tela. Sao duas janelas, e cada uma cuida da sua vida.
REM
REM  Abra as duas: iniciar_ctp.bat para o vigia, esta para a montagem.
REM
REM  ---------------------------------------------------------------------
REM  ELE MATA O ANTERIOR ANTES DE SUBIR, e isso NAO e zelo demais.
REM
REM  Custou tres manhas em quatro dias, sempre igual: alguem puxa o
REM  codigo novo, abre esta janela, e o servidor VELHO continua vivo
REM  segurando a porta 8787. O novo nao consegue abrir a porta e morre;
REM  o velho segue atendendo. E o pior e que nada parece errado - a
REM  pagina abre, a fila aparece, os botoes estao la.
REM
REM  So que o painel e lido do DISCO a cada pedido e o motor mora na
REM  MEMORIA do processo. Entao a tela fica nova e quem monta fica
REM  velho: em 21/09/2026 a tela prometeu uma montagem de 425 x 310 e o
REM  motor respondeu 205 x 640 "nao cabe", porque nao sabia o que era
REM  giro de peca.
REM
REM  Fechar a janela preta no X nem sempre mata o python que ela abriu -
REM  e dai nasce o segundo. Entao aqui se mata pelo nome do que se vai
REM  subir, e nao pela janela.
REM ---------------------------------------------------------------------
title FINART - Fila da montagem (AMERICA)
cd /d "%~dp0"

echo Procurando servidor da montagem que ja esteja no ar...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ps = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'run_montagem' };" ^
  "if ($ps) { $ps | ForEach-Object { Write-Host ('   parando o anterior (pid ' + $_.ProcessId + ')'); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Seconds 2 }" ^
  "else { Write-Host '   nenhum no ar - subindo limpo' }"

echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_montagem.py
) else (
    python run_montagem.py
)
echo.
echo A fila da montagem parou. Pressione uma tecla para fechar.
pause >nul
