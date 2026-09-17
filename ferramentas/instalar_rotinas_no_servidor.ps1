<#
    INSTALA AS ROTINAS DO GEREMPRE NO SERVIDOR.
    Escrito em 17/09/2026, logo depois de o banco voltar para ca.

    AS ROTINAS MORAM ONDE O BANCO MORA. Ate hoje elas rodavam no
    EUDSON-PC, porque o banco estava la. Com o banco aqui, o backup de
    la copia uma pasta sem banco nenhum e o vigia vigia um servico que
    nao serve mais - as duas continuariam "funcionando" e nao
    protegeriam nada. Rotina que parece rodar e nao protege e pior que
    rotina nenhuma.

    O QUE ELA CRIA, as duas como SISTEMA e em nivel mais alto - sem isso
    nenhuma consegue parar ou subir o servico do Firebird:

      Backup GEREMPRE   03:00 todo dia   para o banco a frio, copia,
                                         confere e sobe de volta
      Vigia GEREMPRE    de minuto em     levanta o Firebird se ele
                        minuto           morrer ou travar

    COMO RODAR
      botao direito no INSTALAR ROTINAS.bat -> "Executar como administrador"
#>

$ErrorActionPreference = 'Stop'

$PASTA   = 'C:\Finart\_rotina'          # sem espacos, de proposito
$ORIGEM  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP  = Join-Path $PASTA 'backup_gerempre.ps1'
$VIGIA   = Join-Path $PASTA 'vigia_firebird.ps1'
$ISQL    = 'C:\Firebird_1_5\bin\isql.exe'
$BANCO   = 'C:\NeoGerempre\bdados'
$DESTINO = '\\servidor\TRABALHO\BKP-GS'

function Dizer($t)  { Write-Host "   $t" }
function Titulo($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }

# ------------------------------------------------------------- admin
$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  As tarefas rodam como SISTEMA para poder parar e subir o'
    Write-Host '  servico do Firebird, e so um administrador as cria assim.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================'
Write-Host '   AS ROTINAS DO GEREMPRE VEM MORAR ONDE O BANCO MORA'
Write-Host '  ============================================================'

# ------------------------------------------------- 1. confere o terreno
Titulo 'Conferindo o que existe nesta maquina'
$faltou = @()
foreach ($par in @(@{n='o banco';      c=(Join-Path $BANCO 'neobdados.fdb')},
                   @{n='o isql';       c=$ISQL})) {
    $ok = Test-Path $par.c
    Dizer ("{0,-12} {1}  {2}" -f $par.n, $par.c, $(if ($ok) {'ok'} else {'NAO ACHEI'}))
    if (-not $ok) { $faltou += $par.c }
}
if ($faltou.Count) {
    Write-Host ''
    Write-Host '  PARO: sem isso as rotinas nao teriam o que fazer.' -ForegroundColor Red
    Read-Host '  Enter para fechar'
    exit 2
}

# --------------------------------------------------- 2. levar os scripts
Titulo 'Copiando os scripts'
New-Item -ItemType Directory $PASTA -Force | Out-Null
foreach ($n in @('backup_gerempre.ps1', 'vigia_firebird.ps1')) {
    Copy-Item (Join-Path $ORIGEM $n) (Join-Path $PASTA $n) -Force
    Dizer "$n"
}

# ----------------------------------------------------- 3. as duas tarefas
# schtasks, e nao Register-ScheduledTask: pedir repeticao "para sempre"
# pelo Register exige uma RepetitionDuration, e [TimeSpan]::MaxValue vira
# P99999999DT23H59M59S, que o Agendador recusa. O /SC MINUTE ja quer
# dizer para sempre. Licao de 16/09/2026.
Titulo 'Criando as tarefas'

$cmdBackup = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BACKUP -Banco $BANCO -Destino $DESTINO"
schtasks /Create /TN "Backup GEREMPRE" /TR "$cmdBackup" /SC DAILY /ST 03:00 `
         /RU SYSTEM /RL HIGHEST /F | Out-Null
Dizer 'Backup GEREMPRE ...... todo dia as 03:00'

$cmdVigia = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $VIGIA -Isql `"$ISQL`" -Banco $BANCO\neobdados.fdb"
schtasks /Create /TN "Vigia GEREMPRE" /TR "$cmdVigia" /SC MINUTE /MO 1 `
         /RU SYSTEM /RL HIGHEST /F | Out-Null
Dizer 'Vigia GEREMPRE ....... de minuto em minuto'

# ---------------------------------------------------------- 4. a prova
Titulo 'A prova'
# schtasks /Query mente para quem nao e administrador - responde "acesso
# negado", que ja foi lido como "nao existe" em 16/09/2026. Aqui somos
# administrador, entao a resposta vale.
schtasks /Query /TN "Backup GEREMPRE" /FO LIST 2>&1 |
    Select-String -Pattern 'Nome da tarefa|TaskName|Pr.ximo|Next Run|Status' |
    ForEach-Object { Dizer $_.Line.Trim() }
schtasks /Query /TN "Vigia GEREMPRE" /FO LIST 2>&1 |
    Select-String -Pattern 'Nome da tarefa|TaskName|Pr.ximo|Next Run|Status' |
    ForEach-Object { Dizer $_.Line.Trim() }

Write-Host ''
Write-Host '   A prova que vale nao e esta tela.' -ForegroundColor Yellow
Write-Host '   E o vigia_estado.txt em C:\Finart\_rotina: o carimbo dele tem'
Write-Host '   de andar de minuto em minuto. Confira daqui a dois minutos.'
Write-Host ''
Write-Host '   E amanha de manha, olhe se nasceu uma pasta com a data de'
Write-Host "   hoje em $DESTINO - e o backup das 03:00."
Write-Host ''
Read-Host '  Enter para fechar'
