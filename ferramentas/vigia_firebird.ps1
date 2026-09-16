<#
    VIGIA DO FIREBIRD - percebe o banco fora do ar e o levanta.

    Por que existe. Em dois dias o GEREMPRE parou duas vezes, e das duas
    ninguem percebeu ate alguem tentar abrir:

      15/09/2026  o Firebird 2.0 do SERVIDOR caiu com erro interno ao ser
                  parado com uma conexao aberta, e nao subiu de primeira;
      16/09/2026  o 1.5 desta maquina TRAVOU - processo vivo, soquete
                  segurado, cinco conexoes antigas de pe, e toda conexao
                  nova recusada. O banco ficou uma hora sem ser escrito.

    O Guardian do Firebird nao cobre o segundo caso: ele ressuscita
    processo que MORRE, nao processo que TRAVA. Este vigia cobre os dois,
    porque nao pergunta se o processo existe - pergunta se o banco
    ATENDE.

    O QUE ELE FAZ
      1. tenta abrir a porta 3050;
      2. abrindo, faz uma consulta de verdade pelo isql (com prazo);
      3. falhando DUAS vezes seguidas, reinicia o servico e anota;
      4. nunca mais que MAX_POR_HORA reinicios por hora.

    O passo 2 importa: hoje a porta recusou, mas existe o caso em que ela
    aceita e a engine esta travada atras dela. Porta aberta nao e banco
    vivo.

    O passo 4 tambem: banco que nao sobe de jeito nenhum viraria um laco
    de reinicios, e ai o vigia seria o problema.

    RODA COMO SYSTEM, pelo Agendador, de minuto em minuto. Precisa de
    direito de administrador para reiniciar servico - por isso SYSTEM, e
    nao o usuario.
#>

param(
    [string]$Servico   = 'FirebirdServerDefaultInstance',
    [string]$Banco     = 'C:\NeoGerempre\bdados\neobdados.fdb',
    [string]$Isql      = 'C:\GEREMPRE FIA TESTE\firebird\Firebird_1_5\bin\isql.exe',
    [string]$Config    = 'C:\NeoGerempre\config.txt',
    [string]$Pasta     = 'C:\Finart\_rotina',
    [int]   $Falhas    = 2,      # quantas seguidas antes de reiniciar
    [int]   $MaxPorHora = 3
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Pasta)) { New-Item -ItemType Directory -Path $Pasta -Force | Out-Null }
$LOG     = Join-Path $Pasta 'vigia.log'
$ESTADO  = Join-Path $Pasta 'vigia_estado.txt'
$TRAVA   = Join-Path $Pasta 'backup_em_curso.lock'

function Anotar([string]$t) {
    $l = "[{0}] {1}" -f (Get-Date -Format 'dd/MM/yyyy HH:mm:ss'), $t
    Write-Output $l
    try { Add-Content -Path $LOG -Value $l -Encoding utf8 } catch { }
}

# --------------------------------------------- o backup tem preferencia
#
# A rotina das 03:00 PARA o Firebird de proposito para copiar o arquivo.
# Sem esta trava o vigia veria o banco fora, o levantaria no meio da
# copia, e o backup sairia rasgado - o vigia estragaria justamente a
# unica rede de seguranca que existe.
if (Test-Path $TRAVA) {
    $idade = (Get-Date) - (Get-Item $TRAVA).LastWriteTime
    if ($idade.TotalMinutes -lt 15) { exit 0 }
    Anotar "trava de backup com $([int]$idade.TotalMinutes) min - velha demais, ignorando"
}

# ------------------------------------------------------------ 1. porta
$viva = $false
$porque = ''
try {
    $c = New-Object Net.Sockets.TcpClient
    $tarefa = $c.ConnectAsync('127.0.0.1', 3050)
    if ($tarefa.Wait(5000) -and $c.Connected) { $viva = $true } else { $porque = 'porta 3050 nao respondeu' }
    $c.Close()
} catch { $porque = "porta 3050: $($_.Exception.Message -replace '\s+',' ')" }

# ------------------------------------ 2. consulta de verdade, com prazo
if ($viva) {
    $viva = $false
    try {
        $senha = (Select-String -Path $Config -Pattern '^Password=(.+)$' |
                  Select-Object -First 1).Matches[0].Groups[1].Value.Trim()
        $usuario = (Select-String -Path $Config -Pattern '^User_Name=(.+)$' |
                    Select-Object -First 1).Matches[0].Groups[1].Value.Trim()
        $sql = Join-Path $env:TEMP 'vigia.sql'
        Set-Content -Path $sql -Value "SELECT COUNT(*) AS VIVO FROM RDB`$DATABASE;`nQUIT;" -Encoding ASCII
        $env:ISC_USER = $usuario; $env:ISC_PASSWORD = $senha

        # JULGA PELA RESPOSTA, NAO PELO CODIGO DE SAIDA.
        #
        # Com Start-Process -PassThru o ExitCode vem VAZIO, e a primeira
        # versao leu esse vazio como falha: em 16/09/2026 o vigia disse
        # "banco nao respondeu" com o banco sadio. Duas dessas e ele
        # reiniciaria um banco que estava bem - vigia que erra assim e
        # pior que vigia nenhum.
        #
        # Entao usamos Diagnostics.Process, que da ExitCode confiavel, e
        # ainda assim decidimos pelo que o isql IMPRIMIU: uma consulta
        # que devolve numero e prova de que a engine respondeu.
        $inf = New-Object Diagnostics.ProcessStartInfo
        $inf.FileName = $Isql
        $inf.Arguments = "-i `"$sql`" `"127.0.0.1:$Banco`""
        $inf.UseShellExecute = $false
        $inf.RedirectStandardOutput = $true
        $inf.RedirectStandardError = $true
        $inf.CreateNoWindow = $true
        $proc = [Diagnostics.Process]::Start($inf)
        $saida = $proc.StandardOutput.ReadToEndAsync()
        $erro  = $proc.StandardError.ReadToEndAsync()
        if ($proc.WaitForExit(20000)) {
            $txt = ($saida.Result + "`n" + $erro.Result)
            if ($txt -match '(?m)^\s*\d+\s*$') { $viva = $true }
            else {
                $limpo = ($txt -replace '\s+', ' ').Trim()
                $porque = "a consulta nao devolveu numero: $($limpo.Substring(0, [Math]::Min(90, $limpo.Length)))"
            }
        } else {
            try { $proc.Kill() } catch { }
            $porque = 'a consulta nao voltou em 20 s - engine travada'
        }
    } catch {
        $porque = "consulta: $($_.Exception.Message -replace '\s+',' ')"
    } finally {
        Remove-Item Env:\ISC_PASSWORD -ErrorAction SilentlyContinue
        Remove-Item Env:\ISC_USER -ErrorAction SilentlyContinue
    }
}

# ------------------------------------------------------------- 3. conta
[int]$seguidas = 0
if (Test-Path $ESTADO) { $seguidas = [int]((Get-Content $ESTADO -First 1) -replace '\D','0') }

if ($viva) {
    if ($seguidas -gt 0) { Anotar "banco respondeu de novo (vinha de $seguidas falha(s))" }
    Set-Content -Path $ESTADO -Value '0' -Encoding ASCII
    exit 0
}

$seguidas = $seguidas + 1
Set-Content -Path $ESTADO -Value "$seguidas" -Encoding ASCII
Anotar "banco NAO respondeu ($seguidas de $Falhas): $porque"
if ($seguidas -lt $Falhas) { exit 0 }

# ------------------------------------------------ 4. reiniciar, com teto
$historico = Join-Path $Pasta 'vigia_reinicios.txt'
$agora = Get-Date
$recentes = @()
if (Test-Path $historico) {
    $recentes = @(Get-Content $historico | ForEach-Object {
        try { [datetime]::Parse($_) } catch { } } | Where-Object { $_ -gt $agora.AddHours(-1) })
}
if ($recentes.Count -ge $MaxPorHora) {
    Anotar "JA REINICIEI $($recentes.Count) vez(es) nesta hora - NAO reinicio mais. Precisa de gente."
    exit 1
}

Anotar "reiniciando $Servico"
try {
    Stop-Service -Name $Servico -Force -ErrorAction Stop
    (Get-Service $Servico).WaitForStatus('Stopped', '00:01:00')
} catch {
    Anotar "   nao parou pelo servico ($($_.Exception.Message -replace '\s+',' ')) - matando o processo"
    Get-Process fbserver -ErrorAction SilentlyContinue | ForEach-Object { try { $_.Kill() } catch { } }
    Start-Sleep -Seconds 3
}
try {
    Start-Service -Name $Servico -ErrorAction Stop
    (Get-Service $Servico).WaitForStatus('Running', '00:01:00')
    Start-Sleep -Seconds 3
    $c = New-Object Net.Sockets.TcpClient
    $t = $c.ConnectAsync('127.0.0.1', 3050)
    $ok = ($t.Wait(5000) -and $c.Connected); $c.Close()
    Anotar $(if ($ok) { 'SUBIU e a porta responde' } else { 'servico iniciado mas a porta ainda nao responde' })
} catch {
    Anotar "NAO CONSEGUI SUBIR: $($_.Exception.Message -replace '\s+',' ')"
}
Add-Content -Path $historico -Value $agora.ToString('o') -Encoding ASCII
Set-Content -Path $ESTADO -Value '0' -Encoding ASCII
exit 0
