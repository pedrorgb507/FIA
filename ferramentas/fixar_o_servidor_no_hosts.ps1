<#
    FIXA O NOME 'SERVIDOR' NO IPv4, NO ARQUIVO hosts.

    O PROBLEMA, medido nesta casa em 17/09/2026:

        o Windows entrega SERVIDOR nesta ordem
          IPv6  fe80::83bb:112b:788f:3ca7               8,004 s  tempo esgotado
          IPv6  2804:3d90:71:3c90:6cad:493a:7acf:130f   8,013 s  tempo esgotado
          IPv4  192.168.15.150                          0,001 s  conectou

    O nome resolve por mDNS (repare no 'SERVIDOR.local'), e o mDNS
    responde IPv6 primeiro. Quem liga pelo nome - o GEREMPRE, os
    relatorios, qualquer coisa - espera dois enderecos mortos antes de
    chegar no que funciona. Medido numa ligacao de banco: 63 segundos.

    Uma linha no hosts resolve, porque o hosts vem antes do mDNS.

    O QUE ISSO CUSTA, e e real: no dia em que o servidor trocar de
    numero, esta linha passa a mentir - e ai os DOIS caminhos quebram,
    porque o atalho pelo IP tambem sai daqui. Hoje, com o nome errado, o
    Windows pelo menos acharia o servidor sozinho.

    Por isso a linha vai ASSINADA e com a data: quem trocar o IP do
    servidor tem de trocar aqui tambem, e o comentario diz isso.

    Este arquivo e reversivel: rodando com -Tirar, a linha sai.
#>

param([switch]$Tirar)

$ErrorActionPreference = 'Stop'
$HOSTS  = "$env:SystemRoot\System32\drivers\etc\hosts"
$NOME   = 'SERVIDOR'
$IP     = '192.168.15.150'
$MARCA  = '# FINART - o GEREMPRE mora aqui. Trocou o IP do servidor? troque esta linha.'

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  O arquivo hosts e do Windows, e so administrador escreve nele.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

function Medir([string]$alvo) {
    $c = New-Object Net.Sockets.TcpClient
    $t0 = Get-Date
    try { $c.Connect($alvo, 3050); return [math]::Round(((Get-Date)-$t0).TotalMilliseconds) }
    catch { return -1 } finally { $c.Close() }
}

Write-Host ''
Write-Host "  Maquina: $env:COMPUTERNAME"
Write-Host ''
Write-Host '  == Como o nome resolve HOJE'
try {
    [Net.Dns]::GetHostAddresses($NOME) | ForEach-Object {
        $fam = if ($_.AddressFamily -eq 'InterNetworkV6') { 'IPv6' } else { 'IPv4' }
        Write-Host ("     {0,-5} {1}" -f $fam, $_.IPAddressToString)
    }
} catch { Write-Host "     nao resolveu: $($_.Exception.Message)" }
$antes = Medir $NOME
Write-Host ("     alcancar {0}:3050 -> {1}" -f $NOME,
            $(if ($antes -lt 0) { 'falhou' } else { "$antes ms" }))

# ------------------------------------------------------------ a linha
$linhas = @(Get-Content $HOSTS -ErrorAction SilentlyContinue)
$nossas = $linhas | Where-Object { $_ -match "^\s*\S+\s+$NOME\s*$" -or $_ -eq $MARCA }
$backup = "$HOSTS.ANTES-" + (Get-Date -Format 'yyyy-MM-dd_HHmm')

if ($Tirar) {
    if (-not $nossas) { Write-Host ''; Write-Host '  Nao ha linha nossa para tirar.'; Read-Host '  Enter'; exit 0 }
    Copy-Item $HOSTS $backup
    ($linhas | Where-Object { $_ -notin $nossas }) | Set-Content $HOSTS -Encoding Ascii
    Write-Host ''
    Write-Host "  Tirei. Copia do anterior em $backup" -ForegroundColor Yellow
    Read-Host '  Enter para fechar'
    exit 0
}

if ($nossas -contains "$IP`t$NOME") {
    Write-Host ''
    Write-Host "  Ja esta fixado em $IP. Nada a fazer." -ForegroundColor Yellow
    Read-Host '  Enter para fechar'
    exit 0
}

Copy-Item $HOSTS $backup
$novas = @($linhas | Where-Object { $_ -notin $nossas }) + @('', $MARCA, "$IP`t$NOME")
$novas | Set-Content $HOSTS -Encoding Ascii
Write-Host ''
Write-Host "  == Escrevi (copia do anterior em $backup)"
Write-Host "     $IP`t$NOME"

ipconfig /flushdns | Out-Null

Write-Host ''
Write-Host '  == Como resolve AGORA'
[Net.Dns]::GetHostAddresses($NOME) | ForEach-Object {
    $fam = if ($_.AddressFamily -eq 'InterNetworkV6') { 'IPv6' } else { 'IPv4' }
    Write-Host ("     {0,-5} {1}" -f $fam, $_.IPAddressToString)
}
$depois = Medir $NOME
Write-Host ("     alcancar {0}:3050 -> {1}" -f $NOME,
            $(if ($depois -lt 0) { 'falhou' } else { "$depois ms" }))

Write-Host ''
if ($depois -ge 0 -and ($antes -lt 0 -or $depois -le $antes)) {
    Write-Host '  Pronto.' -ForegroundColor Green
} else {
    Write-Host '  NAO melhorou. Rode de novo com -Tirar e me chame.' -ForegroundColor Red
}
Write-Host ''
Write-Host '  Se um dia o servidor trocar de numero, esta linha passa a'
Write-Host '  mentir e o GEREMPRE para. Ela esta assinada no hosts para'
Write-Host '  quem for mexer saber que existe.'
Write-Host ''
Read-Host '  Enter para fechar'
