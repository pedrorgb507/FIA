@echo off
REM ---------------------------------------------------------------------
REM  RODA NO PROPRIO SERVIDOR, como ADMINISTRADOR.
REM
REM  Mede o banco ANTES de reiniciar - o cabecalho guarda o estado das
REM  transacoes no momento em que travou, e quem sobe o servico primeiro
REM  apaga justamente a prova de que causa foi.
REM ---------------------------------------------------------------------
title Levantar o GEREMPRE
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0levantar_o_gerempre.ps1" %*
