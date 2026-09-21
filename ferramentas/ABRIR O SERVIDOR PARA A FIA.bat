@echo off
REM ---------------------------------------------------------------------
REM  RODA NO SERVIDOR, como ADMINISTRADOR. Uma vez so.
REM
REM  Liga o WinRM, poe a conta no grupo de administradores e - a parte
REM  que quase todo mundo esquece - desliga o rebaixamento de token que
REM  o Windows aplica a conta LOCAL administradora quando ela chega pela
REM  rede. Sem essa chave, ser administrador nao resolve nada.
REM ---------------------------------------------------------------------
title Abrir o servidor para a FIA
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0abrir_o_servidor_para_a_fia.ps1" %*
