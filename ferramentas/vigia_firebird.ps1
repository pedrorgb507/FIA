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

    O CULPADO E O REINICIO, e ele e LENTO. Lido no vigia.log do
    EUDSON-PC, que guardou o caso inteiro:

        [17/09 10:35:20] banco NAO respondeu (1 de 2): a consulta nao
                         voltou em 20 s - engine travada
        [17/09 10:36:20] banco NAO respondeu (2 de 2): idem
        [17/09 10:36:20] reiniciando FirebirdServerDefaultInstance
        [17/09 10:43:54] SUBIU e a porta responde

    SETE MINUTOS E MEIO PARA UM REINICIO SO. Parar o Firebird 1.5 com
    conexao aberta nao acaba no prazo de um minuto do Stop-Service,
    cai no Kill do processo, e so entao ele sobe. Nao sao tres
    reinicios curtos: e UM reinicio caro.

    E foi o que fechou o caso. O gatilho esta na primeira linha: 'a
    consulta nao voltou em 20 s'. O banco estava bem - dois minutos
    depois ele responde -, mas estava OCUPADO, e 20 s de prazo chamavam
    isso de engine travada. Duas dessas e o vigia pagava 7 minutos de
    GEREMPRE fora para consertar o que nao estava quebrado.

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

    ------------------------------------------------------------------
    21/09/2026 - ELE PAROU DE REINICIAR. E o conserto definitivo.

    O operador: "preciso achar uma solucao definitiva para o gerempre
    parar de travar, ja afrouxamos mais nao resolveu (...) ja que isso
    nao acontecia antes de instalar ele".

    A ultima frase e a evidencia mais forte que apareceu, e ela bate com
    tudo o que foi medido antes:

    1. AS QUEDAS TEM DURACAO CONSTANTE - 6 a 7 minutos, cinco vezes em
       tres dias. Defeito nao tem duracao constante; rotina tem.

    2. O REINICIO CUSTA 7 MINUTOS E MEIO, lido no vigia.log do EUDSON-PC:

           [17/09 10:36:20] reiniciando FirebirdServerDefaultInstance
           [17/09 10:43:54] SUBIU e a porta responde

       Parar o Firebird 1.5 com conexao aberta estoura o prazo de um
       minuto do Stop-Service, cai no Kill do processo, e so entao ele
       sobe. A janela de 6 a 7 minutos E UM REINICIO.

    3. O BANCO VOLTAVA QUANDO O VIGIA DESISTIA, e nao depois de nenhum
       reinicio.

    4. AFROUXAR NAO RESOLVEU. Em 21/09 o Falhas subiu de 2 para 5 e o
       prazo da consulta de 20 s para 60 - e naquela mesma tarde o
       GEREMPRE caiu de novo. Trocar o gatilho nao ajuda quando o
       problema e o que se faz DEPOIS dele.

    E OS DOIS CASOS QUE JUSTIFICARAM O REINICIO NAO EXISTEM MAIS. Ele
    nasceu de duas travas de verdade:

        15/09  o Firebird 2.0 DO SERVIDOR caiu ao ser parado
        16/09  o Firebird 1.5 DESTA MAQUINA travou

    Hoje o banco e o 1.5 NO SERVIDOR - uma terceira combinacao, que
    nunca travou sozinha. O vigia esta consertando um problema que mudou
    de casa, e criando um que nao existia.

    ENTAO ELE SO OLHA. Continua perguntando de minuto em minuto,
    continua anotando, e quando o banco nao responde ele DIZ - e para
    ali. Quem reinicia e gente, sabendo o que esta fazendo. E a regra
    desta casa aplicada a ele mesmo: entre errar sozinho e parar para
    perguntar, pare.

    O CODIGO DO REINICIO FICOU INTEIRO, logo abaixo, e volta com
    -PodeReiniciar na tarefa agendada. No dia em que o banco travar de
    verdade e alguem decidir que vale a pena, e um parametro - nao e
    reescrever.

    O QUE SE PERDE, dito por inteiro: travando o banco de madrugada,
    ninguem levanta ate alguem chegar. Era para isso que ele existia. A
    troca e consciente - em tres dias ele derrubou o GEREMPRE cinco
    vezes em horario de trabalho, e nao levantou nada.
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

    # ELE NAO REINICIA MAIS NADA, a menos que alguem mande.
    #
    # Decisao do operador em 21/09/2026: "preciso achar uma solucao
    # definitiva para o gerempre parar de travar, ja afrouxamos mais nao
    # resolveu (...) ja que isso nao acontecia antes de instalar ele".
    #
    # A frase dele e a evidencia mais forte que apareceu, e ela bate com
    # tudo o que foi medido. Ver o cabecalho.
    [switch]$PodeReiniciar,

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

# O LOG TAMBEM VAI PARA A PASTA DE REDE, e nao so para o C: daqui.
#
# O C: do servidor nao e compartilhado. De fora, quem tenta alcanca-lo
# sem ser administrador fica PENDURADO - o Windows nao recusa, ele
# espera -, e isso enganou uma tarde inteira em 21/09/2026: eu tinha o
# diagnostico do vigia pela metade e nao conseguia ler a linha que o
# fecharia.
#
# Uma copia numa pasta que todo mundo enxerga resolve, e custa uma
# escrita por linha anotada - que sao poucas, porque o vigia so fala
# quando tem o que dizer.
#
# REDE FORA NAO PODE CALAR O VIGIA: o espelho vai dentro de um try
# proprio, depois de o log local ja ter sido escrito.
$PASTA_DE_REDE = Join-Path ([IO.Path]::Combine(
    [string][char]92 + [string][char]92 + 'servidor',
    'NeoGerempre', '_ROTINAS_DO_SERVIDOR')) ("_log_do_vigia_" + $env:COMPUTERNAME)
$ESPELHO = Join-Path $PASTA_DE_REDE 'vigia.log'


function Anotar([string]$t) {
    $l = "[{0}] {1}" -f (Get-Date -Format 'dd/MM/yyyy HH:mm:ss'), $t
    Write-Output $l
    try { Add-Content -Path $LOG -Value $l -Encoding utf8 } catch { }
    try {
        if (-not (Test-Path $PASTA_DE_REDE)) {
            New-Item -ItemType Directory -Path $PASTA_DE_REDE -Force | Out-Null
        }
        Add-Content -Path $ESPELHO -Value $l -Encoding utf8
    } catch { }
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

# ------------------------------------------- MODO DE OBSERVACAO
#
# Aqui ele PARA. Nao reinicia, nao mata processo, nao encosta no
# servico - anota alto e deixa para gente.
#
# Este e o conserto de 21/09/2026, e o raciocinio esta no cabecalho:
# reiniciar era o que derrubava, e os dois casos que justificaram o
# reinicio aconteceram em maquinas e versoes que nao existem mais.
#
# Para devolver o reinicio, passe -PodeReiniciar na tarefa agendada. O
# codigo continua inteiro logo abaixo, de proposito: no dia em que o
# banco travar de verdade e alguem decidir que vale a pena, e um
# parametro - nao e reescrever.
if (-not $PodeReiniciar) {
    Anotar "O BANCO NAO RESPONDE ha $seguidas minuto(s): $porque"
    Anotar "   NAO vou reiniciar - estou em modo de OBSERVACAO desde 21/09/2026."
    Anotar "   Se isto durar, e alguem precisar do GEREMPRE agora, reinicie o"
    Anotar "   servico $Servico a mao no Gerenciador de Servicos."
    Set-Content -Path $ESTADO -Value '0' -Encoding ASCII
    exit 0
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
