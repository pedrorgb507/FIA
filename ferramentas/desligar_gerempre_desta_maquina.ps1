<#
    DESLIGA O QUE SOBROU DO GEREMPRE NESTA MAQUINA.
    Escrito em 17/09/2026, depois de o banco voltar para o SERVIDOR.

    O banco mudou de casa, mas as rotinas e o servico ficaram aqui,
    rodando para um banco que nao existe mais. Isto os aposenta.

    O QUE ELE NAO TOCA, e o motivo de cada um:

      C:\GEREMPRE FIA TESTE\      a copia de ENSAIO do banco, que a FIA
                                  usa para testar sem mexer em estoque de
                                  verdade. Ela ja achou dois defeitos que
                                  teriam zerado estoque. E dentro dela
                                  mora o fbclient64.dll que a FIA usa
                                  para falar com o GEREMPRE - sem ele a
                                  FIA nao abre OS nenhuma.

      o Firebird INSTALADO        fica instalado, parado e em Manual. E
                                  ele que serve a copia de ensaio quando
                                  alguem quiser testar. Desinstalar
                                  economizaria nada e custaria a rede de
                                  seguranca.

      C:\BKP-GS\                  os backups, inclusive o a frio de hoje.
                                  Agora que o banco mora no servidor,
                                  esta maquina e o lugar de FORA - a
                                  copia daqui vale mais, nao menos.

      C:\NeoGerempre\             fica para voce compactar. Nao apago
                                  pasta de ninguem.

    NAO RODE ANTES de as rotinas estarem no servidor. Ele mesmo confere.
#>

$ErrorActionPreference = 'Stop'

function Dizer($t)  { Write-Host "   $t" }
function Titulo($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================'
Write-Host '   APOSENTANDO O GEREMPRE DESTA MAQUINA'
Write-Host '  ============================================================'

# ------------------------------------------- 0. o servidor esta servindo?
#
# Desligar o que ha aqui antes de o servidor estar de pe deixaria a
# grafica sem banco e sem rede de seguranca ao mesmo tempo. A conferencia
# vem primeiro de proposito.
Titulo 'O servidor esta mesmo servindo o banco?'
$ok = $false
try {
    $c = New-Object Net.Sockets.TcpClient
    $c.Connect('servidor', 3050)
    $ok = $c.Connected
    $c.Close()
} catch { }
Dizer ("porta 3050 do servidor: {0}" -f $(if ($ok) { 'responde' } else { 'NAO RESPONDE' }))
$temBanco = Test-Path '\\servidor\NeoGerempre\bdados\neobdados.fdb'
Dizer ("o banco esta la ...... {0}" -f $(if ($temBanco) { 'sim' } else { 'NAO ACHEI' }))
if (-not ($ok -and $temBanco)) {
    Write-Host ''
    Write-Host '  PARO: o servidor nao esta pronto. Nao desligo o que ha aqui' -ForegroundColor Red
    Write-Host '  enquanto ele nao estiver servindo - seria ficar sem os dois.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 2
}

# ------------------------------------------------- 1. as tarefas daqui
Titulo 'Desligando as tarefas desta maquina'
# Desabilita, nao apaga: se um dia o banco voltar para ca, basta
# reabilitar. Tarefa apagada se refaz na mao, e a mao erra.
foreach ($nome in @('Backup GEREMPRE', 'Vigia GEREMPRE')) {
    $r = schtasks /Query /TN "$nome" 2>&1
    if ($LASTEXITCODE -ne 0) { Dizer "'$nome' nao existe aqui - nada a fazer"; continue }
    schtasks /Change /TN "$nome" /DISABLE | Out-Null
    Dizer "'$nome' desabilitada (nao apagada)"
}

# -------------------------------------------------- 2. o servico daqui
Titulo 'Parando o Firebird desta maquina'
$s = Get-Service -Name 'FirebirdServerDefaultInstance' -ErrorAction SilentlyContinue
if ($s) {
    if ($s.Status -eq 'Running') {
        Stop-Service -Name $s.Name -Force
        Dizer 'parado'
    } else { Dizer 'ja estava parado' }
    Set-Service -Name $s.Name -StartupType Manual
    Dizer 'em Manual - fica disponivel para a copia de ENSAIO, sob demanda'
} else { Dizer 'nao ha servico de Firebird aqui' }

$g = Get-Service -Name 'FirebirdGuardianDefaultInstance' -ErrorAction SilentlyContinue
if ($g) {
    Stop-Service -Name $g.Name -Force -ErrorAction SilentlyContinue
    Set-Service -Name $g.Name -StartupType Manual
    Dizer 'Guardian tambem parado e em Manual'
}

# ------------------------------------------------------------ 3. a prova
Titulo 'A prova'
Dizer ("porta 3050 AQUI: {0}   (tem de ser False)" -f
       (Test-NetConnection 127.0.0.1 -Port 3050 -WarningAction SilentlyContinue).TcpTestSucceeded)
Dizer ("porta 3050 no SERVIDOR: {0}   (tem de ser True)" -f
       (Test-NetConnection servidor -Port 3050 -WarningAction SilentlyContinue).TcpTestSucceeded)
Get-Service -Name '*irebird*' -ErrorAction SilentlyContinue |
    ForEach-Object { Dizer ("{0}  {1}  {2}" -f $_.Name, $_.Status, $_.StartType) }

Write-Host ''
Write-Host '   O que NAO foi tocado, de proposito:' -ForegroundColor Yellow
Write-Host '     C:\GEREMPRE FIA TESTE\   a copia de ensaio e o fbclient da FIA'
Write-Host '     C:\BKP-GS\               os backups, inclusive o de hoje'
Write-Host '     C:\NeoGerempre\          fica para voce compactar'
Write-Host ''
Read-Host '  Enter para fechar'
