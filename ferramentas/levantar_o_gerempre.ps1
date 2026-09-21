<#
    LEVANTA O GEREMPRE - e, antes de levantar, GUARDA A PROVA.

    Escrito em 21/09/2026, com o banco fora do ar havia 12 minutos e
    ninguem sabendo por que. RODA NO PROPRIO SERVIDOR, como
    administrador.

    ---------------------------------------------------------------
    A ORDEM AQUI E DE PROPOSITO: MEDE, DEPOIS REINICIA.

    Reiniciar apaga a evidencia. O cabecalho do banco guarda o estado
    das transacoes NO MOMENTO EM QUE TRAVOU - quem subir o servico
    primeiro zera isso e fica sem saber de novo, que e exatamente onde
    esta casa esta ha uma semana.

    O gstat -h le a PRIMEIRA PAGINA DO ARQUIVO, direto no disco. Ele
    NAO fala com a engine, entao funciona com o banco travado - e e por
    isso que ele vem antes.

    ---------------------------------------------------------------
    O QUE SE PROCURA NO CABECALHO, e o que cada numero quer dizer

    O Firebird guarda quatro numeros de transacao:

        Oldest transaction        (OIT) a mais velha nao varrida
        Oldest active             (OAT) a mais velha ainda aberta
        Oldest snapshot
        Next transaction

    A DISTANCIA entre a Oldest transaction e a Next e o que importa.
    Ela cresce quando alguem deixa transacao aberta sem fechar - e o
    Delphi desta casa guarda a OS inteira na tela, entao e candidato
    natural. Passando do 'Sweep interval' (20.000 de fabrica), o
    Firebird dispara a VARREDURA SOZINHO, no meio do expediente.

    E varredura no 1.5 para o mundo: ela percorre todo registro velho
    para limpar, single-threaded, e enquanto corre as consultas ficam
    esperando. A cara disso no vigia e exatamente a que apareceu hoje -
    "a consulta nao voltou em 60 s - engine travada" primeiro, com a
    porta ainda aberta, e so depois a porta caindo.

    SE FOR ISSO, o conserto e conhecido e nao e reiniciar: desliga-se a
    varredura automatica (sweep interval 0) e roda-se a varredura de
    madrugada, junto do backup das 03:00. Ai ela continua acontecendo -
    o banco precisa dela - mas na hora em que nao ha ninguem.

    NAO FACA ESSE CONSERTO POR ESTE SCRIPT. Ele so mede. Mudar o
    intervalo de varredura e decisao de gente, com o numero na mao.

    ---------------------------------------------------------------
    A OUTRA COISA QUE ESTE SCRIPT TRAZ, e talvez seja a mais grave

    O firebird.log DO SERVIDOR - que nao e o mesmo que as estacoes
    escrevem na pasta compartilhada. O da pasta so tem falha de
    conexao vista de fora; o do servidor tem o que a ENGINE fez: erro
    de pagina, varredura, queda.

    E ele deve ser lido junto de uma coisa que ja se sabe e que o
    backup_gerempre.ps1 registra no cabecalho dele: ESTE BANCO NAO
    ACEITA gbak, por causa de uma pagina corrompida (73787, na
    RDB$PROCEDURE_PARAMETERS). Banco que nao faz backup logico e banco
    que nao se reconstroi - e reconstruir e o que conserta corrupcao de
    verdade. Isso e conversa de parar a grafica um sabado, nao de
    apertar um botao.

    ---------------------------------------------------------------
    USO
        botao direito no LEVANTAR O GEREMPRE.bat -> Executar como
        administrador

        -SoMedir   mede e nao reinicia nada
        -Agora     reinicia sem perguntar (para quem ja decidiu)
#>

param(
    [string]$Servico = 'FirebirdServerDefaultInstance',
    [string]$Banco   = 'C:\NeoGerempre\bdados\neobdados.fdb',
    [string]$Bin     = 'C:\Firebird_1_5\bin',
    [string]$Guardar = '\\servidor\NeoGerempre\_ROTINAS_DO_SERVIDOR',
    [switch]$SoMedir,
    [switch]$Agora
)

$ErrorActionPreference = 'Continue'

function Titulo($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }
function Dizer($t)  { Write-Host "   $t" }

# Tudo o que se ve na tela tambem vai para um arquivo, porque quem roda
# isto esta no servidor e quem le o resultado quase sempre nao esta.
$carimbo = Get-Date -Format 'yyyy-MM-dd_HHmm'
$pasta   = Join-Path $Guardar ("_socorro_" + $carimbo)
$relato  = $null
try {
    if (-not (Test-Path $pasta)) { New-Item -ItemType Directory -Path $pasta -Force | Out-Null }
    $relato = Join-Path $pasta 'relato.txt'
} catch { Write-Host "   (nao consegui criar $pasta - sigo so na tela)" }

function Anotar($t) {
    Write-Host $t
    if ($relato) { try { Add-Content -Path $relato -Value $t -Encoding utf8 } catch { } }
}

# ----------------------------------------------------------- admin
$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  So administrador para e sobe o servico do Firebird.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================'
Write-Host '   LEVANTAR O GEREMPRE - mede primeiro, reinicia depois'
Write-Host '  ============================================================'
Anotar ("relato de " + (Get-Date -Format 'dd/MM/yyyy HH:mm:ss') + " em " + $env:COMPUTERNAME)

# ------------------------------------------------- 1. como esta agora
Titulo 'Como esta agora'

$svc = Get-Service -Name $Servico -ErrorAction SilentlyContinue
if ($svc) { Anotar ("   servico $Servico : " + $svc.Status) }
else      { Anotar ("   servico $Servico : NAO EXISTE nesta maquina") }

$proc = Get-Process fbserver, fb_inet_server -ErrorAction SilentlyContinue
if ($proc) {
    foreach ($p in $proc) {
        # O tempo de CPU diz se ele esta TRABALHANDO ou so pendurado.
        # Varredura queima CPU; espera de trava nao queima nada.
        Anotar ("   processo $($p.ProcessName) pid $($p.Id)  desde $($p.StartTime.ToString('dd/MM HH:mm:ss'))  CPU $([math]::Round($p.CPU,1))s  memoria $([math]::Round($p.WorkingSet64/1MB))MB")
    }
} else {
    Anotar '   processo do Firebird: nenhum no ar'
}

$c = New-Object Net.Sockets.TcpClient
try {
    $t = $c.ConnectAsync('127.0.0.1', 3050)
    $portaOk = ($t.Wait(5000) -and $c.Connected)
} catch { $portaOk = $false }
try { $c.Close() } catch { }
Anotar ("   porta 3050 : " + $(if ($portaOk) { 'responde' } else { 'NAO responde' }))

if (Test-Path $Banco) {
    $b = Get-Item $Banco
    Anotar ("   banco      : " + [math]::Round($b.Length/1MB,1) + " MB, escrito " + $b.LastWriteTime.ToString('dd/MM HH:mm:ss'))
} else {
    Anotar "   banco      : NAO ACHEI em $Banco"
}

# --------------------------------------- 2. o cabecalho, ANTES de subir
Titulo 'O cabecalho do banco - a prova que o reinicio apagaria'

$gstat = Join-Path $Bin 'gstat.exe'
if (-not (Test-Path $gstat)) {
    Anotar "   NAO ACHEI o gstat em $gstat - sem ele nao da para medir a varredura."
} else {
    # -h le so a primeira pagina, direto do arquivo. Nao fala com a
    # engine, entao funciona com o banco travado.
    $saida = & $gstat -h $Banco 2>&1
    $arqH = Join-Path $pasta 'gstat_header.txt'
    try { $saida | Out-File -FilePath $arqH -Encoding utf8 } catch { }
    $saida | ForEach-Object { Anotar ("   " + $_) }

    # A CONTA QUE IMPORTA, feita aqui para ninguem ter de fazer na mao.
    $n = @{}
    foreach ($l in $saida) {
        if ($l -match '^\s*Oldest transaction\s+(\d+)')  { $n['OIT']   = [int64]$Matches[1] }
        if ($l -match '^\s*Oldest active\s+(\d+)')       { $n['OAT']   = [int64]$Matches[1] }
        if ($l -match '^\s*Oldest snapshot\s+(\d+)')     { $n['snap']  = [int64]$Matches[1] }
        if ($l -match '^\s*Next transaction\s+(\d+)')    { $n['next']  = [int64]$Matches[1] }
        if ($l -match '^\s*Sweep interval:\s+(\d+)')     { $n['sweep'] = [int64]$Matches[1] }
    }
    if ($n.ContainsKey('OIT') -and $n.ContainsKey('snap')) {
        # A CONTA CERTA E snapshot MENOS oldest transaction, e nao
        # 'Next - Oldest'. Escrevi errado na primeira versao e o gstat
        # do banco de teste me mostrou: la o 'Next - Oldest' da um
        # milhao, e varredura nenhuma dispara - porque o que o Firebird
        # compara e o vao ate o SNAPSHOT mais velho. Numero errado aqui
        # daria diagnostico errado, que e o que esta casa ja pagou uma
        # vez nesta mesma investigacao.
        $vao = $n['snap'] - $n['OIT']
        Anotar ''
        Anotar ("   VAO ate a varredura : $vao   (Oldest snapshot $($n['snap']) - Oldest transaction $($n['OIT']))")

        # A linha 'Sweep interval' so aparece no gstat quando foi
        # MEXIDA. Nao aparecendo, vale o padrao de fabrica: 20.000.
        if (-not $n.ContainsKey('sweep')) {
            $n['sweep'] = 20000
            Anotar '   Sweep interval      : 20000 (padrao - o gstat nao mostra quando nunca foi mexido)'
        } else {
            Anotar ("   Sweep interval      : $($n['sweep'])")
        }
        if ($true) {
            if ($n['sweep'] -gt 0 -and $vao -ge $n['sweep']) {
                $vezes = [math]::Round($vao / $n['sweep'])
                Anotar ''
                Anotar "   >>> ACHOU. O vao esta $vezes vezes acima do intervalo."
                Anotar '   >>>'
                Anotar '   >>> O Firebird dispara a VARREDURA sozinho quando isso'
                Anotar '   >>> acontece, no meio do expediente, e a varredura do 1.5'
                Anotar '   >>> para o mundo enquanto corre.'
                Anotar '   >>>'
                Anotar '   >>> E VAO DESTE TAMANHO QUER DIZER QUE ELA NUNCA TERMINA.'
                Anotar '   >>> A Oldest transaction nao anda: ela so avanca quando uma'
                Anotar '   >>> varredura CHEGA AO FIM, e nenhuma chega. Entao toda vez'
                Anotar '   >>> se refaz a MESMA varredura, do mesmo ponto - e por isso'
                Anotar '   >>> as quedas tem sempre a mesma duracao.'
                Anotar '   >>>'
                Anotar '   >>> NAO CONCLUA DAQUI QUE HA TELA ABERTA SEGURANDO O BANCO.'
                Anotar '   >>> Era o que este texto dizia ate 21/09/2026, e a medicao'
                Anotar '   >>> daquele dia desmentiu: no meio da queda a transacao'
                Anotar '   >>> ABERTA mais velha estava 2.677 atras da Next, e depois'
                Anotar '   >>> 2. Ninguem segurava nada. Quem nao anda e a Oldest'
                Anotar '   >>> TRANSACTION, que e outra coisa - olhe a linha abaixo,'
                Anotar '   >>> que mede a aberta, antes de culpar alguem.'
                Anotar '   >>>'
                Anotar '   >>> NAO E LIMBO. Foi a suspeita seguinte, e o gfix -list'
                Anotar '   >>> voltou VAZIO em 21/09/2026: nao ha transacao presa entre'
                Anotar '   >>> commit e rollback. Fica a explicacao simples - a 812665'
                Anotar '   >>> morreu ou foi desfeita, o lixo dela nunca foi recolhido,'
                Anotar '   >>> e so a varredura recolhe.'
                Anotar '   >>>'
                Anotar '   >>> E POR QUE NENHUMA VARREDURA TERMINA: no 1.5 ela corre'
                Anotar '   >>> DENTRO da conexao que a disparou. Caindo a conexao, ela'
                Anotar '   >>> aborta e nada do que ja moeu e aproveitado. Entao cada'
                Anotar '   >>> reinicio do Firebird MATA a varredura que consertaria o'
                Anotar '   >>> problema - inclusive os reinicios feitos para "resolver"'
                Anotar '   >>> a travada. O remedio vinha sendo interrompido pela'
                Anotar '   >>> pressa, e o laco se fechava sozinho.'
                Anotar '   >>>'
                Anotar '   >>> O CONSERTO, e pede janela e o sim do operador:'
                Anotar '   >>>   1. aumentar o cache ANTES (gfix -buffers). Page buffers'
                Anotar '   >>>      em 0 da 2 MB para um banco de 153 MB, e e isso que'
                Anotar '   >>>      faz a varredura levar tanto tempo;'
                Anotar '   >>>   2. UMA varredura completa (gfix -sweep) de madrugada,'
                Anotar '   >>>      sem ninguem conectado, e DEIXAR TERMINAR;'
                Anotar '   >>>   3. conferir aqui que a Oldest transaction ANDOU;'
                Anotar '   >>>   4. so entao desligar a varredura automatica'
                Anotar '   >>>      (gfix -h 0) e agendar a varredura junto do backup'
                Anotar '   >>>      das 03:00.'
                Anotar '   >>>'
                Anotar '   >>> CUIDADO NO PASSO 2: este banco tem pagina corrompida'
                Anotar '   >>> (73787) e nao aceita gbak. Varredura passa por tudo, e'
                Anotar '   >>> pode ser ali que ela morre. Sem gbak nao ha restauracao,'
                Anotar '   >>> entao antes da varredura se faz copia FRIA do arquivo.'
                Anotar '   >>>'
                Anotar '   >>> NADA DISSO E FEITO POR ESTE SCRIPT. Ele so mede, e'
                Anotar '   >>> mexer no banco pede o sim do operador.'
            } elseif ($n['sweep'] -gt 0) {
                $falta = $n['sweep'] - $vao
                Anotar ("   faltam $falta transacoes para a varredura automatica disparar")
            } else {
                Anotar '   varredura automatica JA ESTA DESLIGADA (intervalo 0)'
            }
        }
        if ($n.ContainsKey('OAT') -and $n.ContainsKey('next')) {
            $preso = $n['next'] - $n['OAT']
            Anotar ("   transacao aberta mais velha esta $preso atras da Next")
            if ($preso -gt 10000) {
                Anotar '   >>> ha transacao ABERTA ha muito tempo segurando o banco.'
                Anotar '   >>> Isso e tela do Delphi deixada aberta, ou programa que'
                Anotar '   >>> conectou e nao fechou. E a causa RAIZ do vao crescer.'
            }
        }
    }
}

# ------------------------------------- 3. o log da engine, e o que ha
Titulo 'O log da engine, e o resto da prova'

foreach ($cand in @((Join-Path (Split-Path -Parent $Bin) 'firebird.log'),
                    'C:\Firebird_1_5\firebird.log',
                    (Join-Path $Bin 'firebird.log'))) {
    if (Test-Path $cand) {
        try {
            Copy-Item $cand (Join-Path $pasta 'firebird_DO_SERVIDOR.log') -Force
            $t = Get-Item $cand
            Anotar ("   firebird.log da engine copiado: $cand (" + [math]::Round($t.Length/1KB) + " KB, escrito " + $t.LastWriteTime.ToString('dd/MM HH:mm') + ")")
        } catch { Anotar "   nao consegui copiar $cand" }
        break
    }
}

# As tarefas agendadas: queda que se repete em horario e ROTINA, nao
# defeito. Se houver alguma perto das 17:38, ela e suspeita.
try {
    $tarefas = schtasks /query /fo LIST /v 2>&1
    $tarefas | Out-File -FilePath (Join-Path $pasta 'tarefas_agendadas.txt') -Encoding utf8
    Anotar '   tarefas agendadas guardadas em tarefas_agendadas.txt'
} catch { Anotar '   nao consegui listar as tarefas agendadas' }

# ------------------------------------------------- 4. subir, se for o caso
if ($SoMedir) {
    Titulo 'Parei aqui'
    Anotar '   -SoMedir: nada foi reiniciado.'
    Anotar ("   O relato esta em $pasta")
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 0
}

if ($portaOk) {
    Titulo 'O banco esta respondendo'
    Anotar '   A porta 3050 responde. NAO vou reiniciar um banco que esta de pe -'
    Anotar '   reiniciar por precaucao derruba quem esta trabalhando agora.'
    Anotar ("   O relato esta em $pasta")
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 0
}

Titulo 'Reiniciar o Firebird'
Anotar '   A porta nao responde. Reiniciar vai DERRUBAR quem estiver com o'
Anotar '   GEREMPRE aberto - quem tiver OS na tela sem salvar perde o que'
Anotar '   digitou. Parar o 1.5 com conexao aberta costuma levar alguns'
Anotar '   minutos, porque estoura o prazo e cai no encerramento forcado.'
if (-not $Agora) {
    Write-Host ''
    $r = Read-Host '   Digite SUBIR para reiniciar, ou Enter para desistir'
    if ($r -ne 'SUBIR') {
        Anotar '   Desisti. Nada foi reiniciado - a medicao continua guardada.'
        Write-Host ''
        Read-Host '  Enter para fechar'
        exit 0
    }
}

Anotar ("   [" + (Get-Date -Format 'HH:mm:ss') + "] parando $Servico")
try {
    Stop-Service -Name $Servico -Force -ErrorAction Stop
    (Get-Service $Servico).WaitForStatus('Stopped', '00:02:00')
    Anotar ("   [" + (Get-Date -Format 'HH:mm:ss') + "] parou pelo servico")
} catch {
    Anotar ("   nao parou pelo servico (" + ($_.Exception.Message -replace '\s+',' ') + ") - matando o processo")
    Get-Process fbserver, fb_inet_server -ErrorAction SilentlyContinue |
        ForEach-Object { try { $_.Kill() } catch { } }
    Start-Sleep -Seconds 3
}

Anotar ("   [" + (Get-Date -Format 'HH:mm:ss') + "] subindo $Servico")
try {
    Start-Service -Name $Servico -ErrorAction Stop
    (Get-Service $Servico).WaitForStatus('Running', '00:02:00')
} catch {
    Anotar ("   NAO CONSEGUI SUBIR: " + ($_.Exception.Message -replace '\s+',' '))
}

Start-Sleep -Seconds 3
$c = New-Object Net.Sockets.TcpClient
try {
    $t = $c.ConnectAsync('127.0.0.1', 3050)
    $ok = ($t.Wait(8000) -and $c.Connected)
} catch { $ok = $false }
try { $c.Close() } catch { }

Anotar ''
if ($ok) {
    Anotar ("   [" + (Get-Date -Format 'HH:mm:ss') + "] SUBIU e a porta responde.")
    Anotar '   A FIA lanca sozinha as OS que ficaram na fila, na proxima volta.'
} else {
    Anotar ("   [" + (Get-Date -Format 'HH:mm:ss') + "] o servico iniciou mas a PORTA AINDA NAO RESPONDE.")
    Anotar '   Se demorar, olhe o firebird_DO_SERVIDOR.log que este script copiou.'
}

# O cabecalho DEPOIS, para comparar. Se o vao zerou, a varredura correu
# no reinicio - e isso confirma de uma vez de quem era a culpa.
if (Test-Path $gstat) {
    Titulo 'O cabecalho depois, para comparar'
    $depois = & $gstat -h $Banco 2>&1
    try { $depois | Out-File -FilePath (Join-Path $pasta 'gstat_header_DEPOIS.txt') -Encoding utf8 } catch { }
    $depois | Where-Object { $_ -match 'Oldest|Next transaction|Sweep' } |
        ForEach-Object { Anotar ("   " + $_) }
}

Write-Host ''
Anotar ("   O relato inteiro esta em $pasta")
Anotar '   Mande essa pasta para a FIA - e com ela que se acha a causa.'
Write-Host ''
Read-Host '  Enter para fechar'
