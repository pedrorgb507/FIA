@echo off
REM ---------------------------------------------------------------------
REM  RODA NA MAQUINA DA FIA, como ADMINISTRADOR. Uma vez so.
REM
REM  A senha e digitada por VOCE, na janela do Windows, e guardada
REM  cifrada pelo DPAPI em C:\Finart\_ctp_ia - fora do Git. O arquivo so
REM  abre para este usuario nesta maquina: copiado para outro PC nao
REM  serve nem para quem o roubar.
REM ---------------------------------------------------------------------
title Guardar a senha do servidor
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0guardar_a_senha_do_servidor.ps1" %*
