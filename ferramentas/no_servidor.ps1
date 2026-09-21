<#
    RODA UM COMANDO NO SERVIDOR, daqui.

    E o atalho que a FIA usa depois que o ABRIR O SERVIDOR PARA A FIA e
    o GUARDAR A SENHA DO SERVIDOR ja rodaram. Ele nao configura nada -
    so usa o que aqueles dois deixaram pronto.

        .\no_servidor.ps1 { Get-Service FirebirdServerDefaultInstance }
        .\no_servidor.ps1 { & 'C:\Firebird_1_5\bin\gstat.exe' -h 'C:\NeoGerempre\bdados\neobdados.fdb' }

    ---------------------------------------------------------------
    ELE AVISA QUANDO O COMANDO ESCREVE, e isso e de proposito.

    O operador decidiu em 21/09/2026 dar acesso completo - "WinRM
    completo, tudo daqui" -, sabendo do que foi dito antes: este banco
    tem pagina corrompida, nao aceita gbak, e portanto nao tem
    restauracao. Num banco assim, engano nao e queda; e o fim do
    registro da empresa.

    Nao ha trava tecnica aqui, porque acesso completo e justamente nao
    ter. O que ha e um aviso: comando que case com a lista abaixo sai
    com um AVISO na tela antes de correr, para que quem estiver lendo
    veja o que vai acontecer. E o equivalente, para mim, da regra que
    esta casa aplica a si mesma - entre errar sozinho e parar para
    perguntar, pare.

    -Quieto tira o aviso, para quando ele ja foi visto.
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [scriptblock]$Comando,

    [string]$Servidor  = 'servidor',
    [string]$Credencial = 'C:\Finart\_ctp_ia\credencial_servidor.xml',
    [switch]$Quieto
)

$ErrorActionPreference = 'Stop'

# O que merece ser dito em voz alta antes de correr. Nao e lista de
# proibicao - e lista de "olhe isto".
$PESADOS = @(
    @{ que = 'gfix';                 por = 'mexe no banco por dentro - varredura, reparo, intervalo' },
    @{ que = 'gbak';                 por = 'backup/restauracao - e ESTE banco falha no gbak pela pagina 73787' },
    @{ que = 'Stop-Service';         por = 'derruba quem estiver com o GEREMPRE aberto' },
    @{ que = 'Restart-Service';      por = 'derruba quem estiver com o GEREMPRE aberto' },
    @{ que = 'Remove-Item';          por = 'apaga arquivo no servidor' },
    @{ que = 'Remove-LocalUser';     por = 'mexe em conta' },
    @{ que = 'Stop-Process';         por = 'mata processo no servidor' },
    @{ que = 'Set-ItemProperty';     por = 'escreve no registro' },
    @{ que = 'Format-Volume';        por = 'formata disco' }
)

if (-not (Test-Path $Credencial)) {
    Write-Host ''
    Write-Host "  Nao achei a credencial em $Credencial" -ForegroundColor Red
    Write-Host '  Rode antes o GUARDAR A SENHA DO SERVIDOR.bat nesta maquina'
    Write-Host '  (e, no servidor, o ABRIR O SERVIDOR PARA A FIA.bat).'
    Write-Host ''
    exit 1
}

$texto = $Comando.ToString()
$achados = $PESADOS | Where-Object { $texto -match [regex]::Escape($_.que) }
if ($achados -and -not $Quieto) {
    Write-Host ''
    Write-Host '  ------------------------------------------------------------' -ForegroundColor Yellow
    Write-Host '   ESTE COMANDO ESCREVE NO SERVIDOR' -ForegroundColor Yellow
    foreach ($a in $achados) {
        Write-Host ("     $($a.que)  ->  $($a.por)") -ForegroundColor Yellow
    }
    Write-Host '  ------------------------------------------------------------' -ForegroundColor Yellow
    Write-Host ''
}

$cred = Import-Clixml -Path $Credencial
Invoke-Command -ComputerName $Servidor -Credential $cred -ScriptBlock $Comando
