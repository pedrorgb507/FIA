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
REM ---------------------------------------------------------------------
title FINART - Fila da montagem (AMERICA)
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_montagem.py
) else (
    python run_montagem.py
)
echo.
echo A fila da montagem parou. Pressione uma tecla para fechar.
pause >nul
