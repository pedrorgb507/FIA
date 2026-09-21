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

    ------------------------------------------------------------------
    21/09/2026 - O VIGIA VIROU O PROBLEMA, E FOI AFROUXADO

    O operador: "o gerempre parou de funcionar nas maquinas". Nao tinha
    parado: caia e voltava. Quatro vezes em tres dias, medidas no log da
    FIA:

        18/09 20:43 -> 20:49    7 min
        19/09 14:57 -> 15:03    7 min
        21/09 01:10 -> 01:16    6 min
        21/09 08:45 -> 08:52    7 min

    Sempre 6 a 7 minutos, sempre SQLCODE -923. Queda de verdade nao tem
    duracao constante; rotina tem.

    A CONTA QUE ENTREGOU: de minuto em minuto, 2 falhas para reiniciar,
    teto de 3 por hora. Reinicios nos minutos 2, 4 e 6; no minuto 8 o
    teto fecha. Da 6 a 8 minutos de banco indo e voltando.

    E o que fecha o caso: O BANCO VOLTAVA QUANDO O VIGIA DESISTIA, e nao
    depois de nenhum reinicio. Reinicio que conserta devolve o banco no
    minuto 2. Devolver no minuto 7 - justamente quando o teto cala o
    vigia - quer dizer que quem derrubava era ele.

    TRES MUDANCAS, e a terceira e a que importa:

      Falhas 2 -> 5     dois minutos de banco mudo e um pico de
                        trabalho; cinco seguidos e banco morto;
      prazo 20 -> 60 s  engine ocupada passa de 20 s sem estar travada,
                        e era julgada travada;
      'nao sei dizer'   a checagem falhando POR ELA MESMA - isql que
                        sumiu, config que mudou, permissao que caiu -
                        nao diz uma palavra sobre o banco, e nao conta
                        mais como falha. Era por ai que um banco sadio
                        apanhava.

    O TETO DE 3 FICOU. Ele nao causou nada - foi o teto que devolvia o
    banco. Tirar so faria o laco durar mais.
    ------------------------------------------------------------------
#>

param(
    [string]$Servico   = 'FirebirdServerDefaultInstance',
    [string]$Banco     = 'C:\NeoGerempre\bdados\neobdados.fdb',
    [string]$Isql      = 'C:\GEREMPRE FIA TESTE\firebird\Firebird_1_5\bin\isql.exe',
    [string]$Config    = 'C:\NeoGerempre\config.txt',
    [string]$Pasta     = 'C:\Finart\_rotina',
    # QUANTAS FALHAS SEGUIDAS ANTES DE ENCOSTAR NO SERVICO.
    #
    # Era 2 - dois minutos -, e em 21/09/2026 isso se mostrou pouco. Ver
    # o cabecalho: quatro quedas de 6 a 7 minutos em tres dias, e o banco
    # voltava quando o vigia DESISTIA, nao depois de nenhum reinicio.
    #
    # 5 minutos de banco mudo e outra coisa: e banco morto. Travar por
    # cinco minutos seguidos nao acontece por acaso, e um pico de trabalho
    # nao dura tanto.
    [int]   $Falhas    = 5,
    [int]   $MaxPorHora = 3,

    # PRAZO DA CONSULTA. Eram 20 s, e uma engine OCUPADA passa disso sem
    # estar travada - foi a primeira suspeita para a checagem falhar num
    # banco sadio. Um minuto separa 'demorou' de 'nao vem'.
    [int]   $PrazoConsulta = 60
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

# --------------------------------------- ha banco NESTA maquina?
#
# Em 17/09/2026 o banco mudou para o SERVIDOR, e os arquivos daqui foram
# renomeados para .VELHO. O vigia continuou fazendo o que sabia: viu a
# porta fora do ar, reiniciou o servico, o servico subiu sem banco
# nenhum, e dois minutos depois tudo de novo - tres reinicios em quatro
# minutos, contra o que a migracao tinha acabado de fazer.
#
# Vigia que reinicia um servico para um banco que NAO EXISTE nao esta
# vigiando: esta produzindo ruido que esconde problema de verdade. Se o
# arquivo nao esta aqui, nao ha o que vigiar nesta maquina.
#
# Anota UMA vez, e nao a cada minuto - senao o log que deveria avisar
# vira o log que ninguem le.
if (-not (Test-Path $Banco)) {
    $avisado = Join-Path $Pasta 'vigia_sem_banco.txt'
    if (-not (Test-Path $avisado)) {
        Anotar "NAO HA BANCO nesta maquina ($Banco). Nao vigio nada aqui - o
 banco mudou de casa. Aponte o vigia para onde ele foi, ou desligue a tarefa."
        Set-Content -Path $avisado -Value (Get-Date -Format 'o') -Encoding Ascii
    }
    Set-Content -Path $ESTADO -Value (Get-Date -Format 'HH:mm:ss') -Encoding Ascii
    exit 0
}

# ------------------------------------------------------------ 1. porta
$viva = $false
$porque = ''

# A CHECAGEM FALHOU POR ELA MESMA, e nao pelo banco.
#
# Sao coisas diferentes e o vigia as confundia: 'o banco nao respondeu' e
# 'eu nao consegui perguntar'. isql que sumiu de lugar, config.txt que
# mudou de formato, permissao que caiu - nada disso diz UMA PALAVRA sobre
# o banco estar vivo, e mesmo assim contava como falha. Duas dessas e ele
# matava o fbserver de um banco sadio.
#
# Vigia que nao sabe perguntar nao pode decidir. Ver o passo 3.
$naoSeiDizer = $false
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
        if ($proc.WaitForExit($PrazoConsulta * 1000)) {
            $txt = ($saida.Result + "`n" + $erro.Result)
            if ($txt -match '(?m)^\s*\d+\s*$') { $viva = $true }
            else {
                $limpo = ($txt -replace '\s+', ' ').Trim()
                $porque = "a consulta nao devolveu numero: $($limpo.Substring(0, [Math]::Min(90, $limpo.Length)))"
            }
        } else {
            try { $proc.Kill() } catch { }
            $porque = "a consulta nao voltou em $PrazoConsulta s - engine travada"
        }
    } catch {
        # NAO conta como banco fora: estourou AQUI, antes de o banco ter
        # chance de responder. Ver $naoSeiDizer.
        $naoSeiDizer = $true
        $porque = "consulta: $($_.Exception.Message -replace '\s+',' ')"
    } finally {
        Remove-Item Env:\ISC_PASSWORD -ErrorAction SilentlyContinue
        Remove-Item Env:\ISC_USER -ErrorAction SilentlyContinue
    }
}

# ------------------------------------ 2b. nao sei perguntar: nao decido
#
# Anota UMA VEZ por motivo, e nao a cada minuto - senao o log que deveria
# avisar vira o log que ninguem le. Mudando o motivo, avisa de novo.
#
# E NAO MEXE NO CONTADOR: nem zera (esconderia um banco que ja vinha
# falhando de verdade) nem soma. Esta volta simplesmente nao vale.
if ($naoSeiDizer) {
    $marca = Join-Path $Pasta 'vigia_nao_sei_perguntar.txt'
    $antes = if (Test-Path $marca) { Get-Content $marca -Raw } else { '' }
    if ($antes.Trim() -ne $porque) {
        Anotar "NAO SEI DIZER se o banco esta vivo - a checagem falhou por ela mesma: $porque"
        Anotar "   nao conto como falha e nao encosto no servico. CONSERTE A CHECAGEM: enquanto ela estiver assim, ninguem esta vigiando o banco."
        Set-Content -Path $marca -Value $porque -Encoding utf8
    }
    exit 0
}
$marca = Join-Path $Pasta 'vigia_nao_sei_perguntar.txt'
if (Test-Path $marca) {
    Anotar 'voltei a conseguir perguntar ao banco'
    Remove-Item $marca -ErrorAction SilentlyContinue
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
