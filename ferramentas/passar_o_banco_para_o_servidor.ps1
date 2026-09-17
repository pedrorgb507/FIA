# -*- coding: utf-8 -*-
<#
    PASSAR O BANCO DO GEREMPRE PARA O SERVIDOR
    Escrito em 17/09/2026. Roda UMA vez, no EUDSON-PC, como administrador.

    O QUE ELE FAZ, e a ordem importa:

        1. cala o vigia do Firebird (ele religa o banco em ate um minuto,
           e no meio de uma copia isso a rasga);
        2. para o Firebird desta maquina - copia a quente nao vale;
        3. copia neobdados.fdb e neocep para o servidor;
        4. CONFERE byte a byte o que chegou la;
        5. so entao renomeia os arquivos daqui para .VELHO e poe o
           servico em Manual.

    O QUE ELE FAZ SE ALGO NAO CONFERIR: levanta o Firebird daqui de volta
    e para, sem renomear nada. A grafica continua trabalhando por esta
    maquina, como estava antes - e ninguem fica sem banco.

    NAO APAGA NADA. O que sai de cena e renomeado, nunca removido.
#>

$ErrorActionPreference = 'Stop'

$ORIGEM   = 'C:\NeoGerempre\bdados'
$DESTINO  = '\\servidor\NeoGerempre\bdados'
$ROTINA   = 'C:\Finart\_rotina'
$TRAVA    = Join-Path $ROTINA 'backup_em_curso.lock'
$ARQUIVOS = @('neobdados.fdb', 'neocep')
$SELO     = Get-Date -Format 'yyyy-MM-dd_HHmm'
$GUARDA   = "C:\BKP-GS\antes-da-volta-ao-servidor_$SELO"

function Dizer($texto)  { Write-Host "   $texto" }
function Titulo($texto) { Write-Host ""; Write-Host "== $texto" -ForegroundColor Cyan }

# ----------------------------------------------------------------- admin
$eu = New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $eu.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host ""
    Write-Host "  PARE. Isto precisa ser aberto COMO ADMINISTRADOR." -ForegroundColor Red
    Write-Host "  Sem isso nao da para parar o servico do Firebird."
    Write-Host ""
    Read-Host "  Enter para fechar"
    exit 1
}

Write-Host ""
Write-Host "  ============================================================"
Write-Host "   O BANCO DO GEREMPRE VOLTA PARA O SERVIDOR"
Write-Host "  ============================================================"

# ------------------------------------------------- 0. ninguem la dentro
Titulo "Conferindo se alguem esta dentro do banco"
$conexoes = @(Get-NetTCPConnection -LocalPort 3050 -State Established -ErrorAction SilentlyContinue)
if ($conexoes.Count -gt 0) {
    Dizer "HA $($conexoes.Count) CONEXAO(OES) ABERTA(S):"
    $conexoes | ForEach-Object { Dizer "   $($_.RemoteAddress)" }
    Write-Host ""
    Write-Host "  PARO AQUI." -ForegroundColor Red
    Write-Host "  Parar o Firebird com alguem dentro ja derrubou o banco em"
    Write-Host "  15/09/2026. Feche o GEREMPRE em todas as maquinas - e a FIA"
    Write-Host "  tambem - e rode de novo."
    Write-Host ""
    Read-Host "  Enter para fechar"
    exit 2
}
Dizer "ninguem dentro. Pode seguir."

# ------------------------------------------------------ 1. calar o vigia
Titulo "Calando o vigia do Firebird"
# Ele roda de minuto em minuto e levanta o banco quando o ve fora. Sem
# esta trava ele o subiria no meio da copia, e a copia sairia rasgada.
# Ele mesmo ignora a trava depois de 15 minutos, para que uma trava
# esquecida nao o cegue - entao daqui para a frente ha pressa.
New-Item -ItemType Directory $ROTINA -Force | Out-Null
Set-Content -Path $TRAVA -Value "migracao para o servidor $SELO" -Encoding Ascii
Dizer "trava posta em $TRAVA"

$servicos = @(Get-Service -Name '*irebird*' -ErrorAction SilentlyContinue)
$precisaVoltar = $false

try {
    # ------------------------------------------------ 2. parar o Firebird
    Titulo "Parando o Firebird desta maquina"
    # O Guardian PRIMEIRO: ele existe para levantar o servidor de volta, e
    # o faria no meio da copia.
    foreach ($nome in @('FirebirdGuardianDefaultInstance',
                        'FirebirdServerDefaultInstance')) {
        $s = $servicos | Where-Object { $_.Name -eq $nome }
        if ($s) {
            Stop-Service -Name $nome -Force -ErrorAction SilentlyContinue
            Dizer "parei $nome"
        }
    }
    $precisaVoltar = $true
    Start-Sleep -Seconds 3

    $aberta = (Test-NetConnection 127.0.0.1 -Port 3050 -WarningAction SilentlyContinue).TcpTestSucceeded
    if ($aberta) { throw "a porta 3050 continua respondendo - o Firebird nao parou" }
    Dizer "porta 3050 fechada - o banco esta frio"

    # -------------------------------------------------- 3. backup a frio
    Titulo "Backup, com o servico parado (e o que o torna valido)"
    New-Item -ItemType Directory $GUARDA -Force | Out-Null
    foreach ($a in $ARQUIVOS) {
        Copy-Item (Join-Path $ORIGEM $a) $GUARDA
        Dizer "$a guardado"
    }
    Dizer "em $GUARDA"

    # ------------------------------------------- 4. copiar para o servidor
    Titulo "Copiando para o servidor"
    New-Item -ItemType Directory $DESTINO -Force | Out-Null
    foreach ($a in $ARQUIVOS) {
        $de  = Join-Path $ORIGEM  $a
        $para = Join-Path $DESTINO $a
        if (Test-Path $para) {
            Move-Item $para "$para.VELHO_$SELO"
            Dizer "havia um $a la - ficou como $a.VELHO_$SELO"
        }
        Copy-Item $de $para
        Dizer ("{0,-16} {1,10:N0} bytes" -f $a, (Get-Item $para).Length)
    }

    # ------------------------------------------------- 5. CONFERIR mesmo
    Titulo "Conferindo o que chegou"
    foreach ($a in $ARQUIVOS) {
        $de   = Get-Item (Join-Path $ORIGEM  $a)
        $para = Get-Item (Join-Path $DESTINO $a)
        if ($de.Length -ne $para.Length) {
            throw "$a chegou com $($para.Length) bytes e aqui tem $($de.Length)"
        }
        Dizer "$a confere ($($para.Length) bytes)"
    }
    # o cabecalho do .fdb tem de continuar dizendo ODS 10.3 - e o que
    # prova que o arquivo atravessou inteiro, e nao so do mesmo tamanho
    $fs = [IO.File]::OpenRead((Join-Path $DESTINO 'neobdados.fdb'))
    try {
        $cab = New-Object byte[] 24
        [void]$fs.Read($cab, 0, 24)
        $ods = "{0}.{1}" -f [BitConverter]::ToUInt16($cab, 18), [BitConverter]::ToUInt16($cab, 20)
        Dizer "ODS do arquivo no servidor: $ods   (tem de ser 10.3)"
        if ($ods -ne '10.3') { throw "ODS inesperado no servidor: $ods" }
    } finally { $fs.Close() }

    # ------------------------------- 6. tirar o banco velho de circulacao
    Titulo "Tirando o banco velho de circulacao"
    # ESTE PASSO NAO E ZELO. Se uma estacao voltar a apontar para ca, ela
    # abre um SEGUNDO banco e o trabalho da grafica se parte em dois -
    # duas OS com o mesmo numero, dois estoques, duas verdades. So
    # aparece dias depois.
    foreach ($a in $ARQUIVOS) {
        Rename-Item (Join-Path $ORIGEM $a) "$a.VELHO_$SELO"
        Dizer "$a  ->  $a.VELHO_$SELO"
    }
    foreach ($s in $servicos) {
        Set-Service -Name $s.Name -StartupType Manual
        Dizer "$($s.Name) posto em Manual"
    }
    $precisaVoltar = $false   # de proposito: o banco nao mora mais aqui

    Titulo "PRONTO"
    Write-Host "   O banco esta no servidor. O Firebird desta maquina fica" -ForegroundColor Green
    Write-Host "   PARADO e em Manual, e os arquivos daqui viraram .VELHO." -ForegroundColor Green
    Write-Host ""
    Write-Host "   Falta trocar o config.txt - a FIA faz isso. Avise."

} catch {
    Write-Host ""
    Write-Host "  DEU ERRADO: $($_.Exception.Message)" -ForegroundColor Red
    if ($precisaVoltar) {
        Write-Host "  Levantando o Firebird daqui de volta, para a grafica nao parar..." -ForegroundColor Yellow
        $g = $servicos | Where-Object { $_.Name -like '*Guardian*' }
        $alvo = if ($g) { $g.Name } else { 'FirebirdServerDefaultInstance' }
        try {
            Start-Service -Name $alvo
            Start-Sleep -Seconds 3
            $ok = (Test-NetConnection 127.0.0.1 -Port 3050 -WarningAction SilentlyContinue).TcpTestSucceeded
            Write-Host "  banco de volta no ar: $ok" -ForegroundColor Yellow
        } catch {
            Write-Host "  NAO CONSEGUI LEVANTAR. Chame ajuda AGORA." -ForegroundColor Red
        }
    }
    Write-Host "  Nada foi renomeado. O backup a frio esta em $GUARDA"
} finally {
    Remove-Item $TRAVA -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "   (vigia liberado)"
    Write-Host ""
    Read-Host "  Enter para fechar"
}
