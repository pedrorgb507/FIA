<#
    A VARREDURA QUE NINGUEM INTERROMPE.

    Roda no SERVIDOR, pelo Agendador, como SISTEMA. Domingo de manha
    cedo, combinado com o operador em 21/09/2026: "pode ser domingo de
    manha cedo, onde realmente nao vai ter ninguem na grafica, sabado
    pode ter servico".

    ---------------------------------------------------------------
    O QUE ELA CONSERTA, e por que so agora

    Medido em 21/09/2026, no cabecalho do banco de producao:

        Oldest transaction       812665      nao anda
        Oldest snapshot         2030855
        vao                     1218190      61x o intervalo de 20000

    A transacao 812665 morreu ou foi desfeita ha muito tempo e o lixo
    dela nunca foi recolhido. So a varredura recolhe, e enquanto ela
    nao recolher a Oldest transaction nao anda.

    E NENHUMA VARREDURA TERMINAVA. No Firebird 1.5 a automatica corre
    DENTRO da conexao que a disparou; caindo a conexao, ela aborta e
    nada do que ja moeu e aproveitado. Entao cada reinicio do Firebird
    matava a varredura que consertaria o problema - inclusive os
    reinicios feitos para "destravar" o GEREMPRE. O remedio vinha sendo
    interrompido pela pressa, e o laco se fechava sozinho desde 2016.

    Por isso esta rotina roda quando NAO HA NINGUEM: para ninguem
    reiniciar no meio.

    O cache ja foi aumentado em 21/09 (Page buffers de 0 para 50000, de
    2 MB para 49 MB). Com o banco em 153 MB e paginas de 1024 bytes,
    isso guarda um terco dele na memoria - e era a lentidao que fazia a
    varredura passar de 25 minutos.

    ---------------------------------------------------------------
    ELA PARA SOZINHA EM VEZ DE INSISTIR

    As 5 da manha nao ha ninguem para dizer "isto esta estranho". Entao
    ela desiste em vez de improvisar:

      - nao ha copia fria de hoje?          PARA, sem tocar no banco
      - ha gente conectada?                 PARA
      - a varredura devolve erro?           PARA, e NAO desliga nada
      - a Oldest transaction NAO andou?     PARA, e NAO desliga nada

    O ultimo e o mais importante. Desligar a varredura automatica de um
    banco onde a varredura NAO funcionou seria tirar a unica coisa que
    ainda tentava limpa-lo. So se desliga o automatico depois de provar,
    com numero, que a manual deu conta.

    ---------------------------------------------------------------
    A COPIA FRIA E CONDICAO, e nao zelo

    Este banco tem uma pagina corrompida (73787, na
    RDB$PROCEDURE_PARAMETERS) e NAO ACEITA gbak. Sem backup logico nao
    ha restauracao: a unica volta possivel e o arquivo copiado a frio.

    A varredura passa por TODO registro velho do banco, e pode ser
    exatamente na 73787 que ela morra. Entao, sem copia de hoje, esta
    rotina nao comeca.

    O backup das 03:00 ja faz essa copia. Esta rotina so CONFERE que
    ela existe e e de hoje - nao duplica o trabalho nem para o servico
    de novo.
#>

param(
    [string]$Servico = 'FirebirdServerDefaultInstance',
    [string]$Arquivo = 'C:\NeoGerempre\bdados\neobdados.fdb',
    [string]$Config  = 'C:\NeoGerempre\config.txt',
    [string]$Bin     = 'C:\Firebird_1_5\bin',
    # CAMINHOS LOCAIS, E NAO UNC DA PROPRIA MAQUINA.
    #
    # Esta rotina roda como SISTEMA, e SISTEMA nao tem identidade de
    # rede para alcancar os compartilhamentos do proprio servidor. Um
    # \\servidor\TRABALHO aqui falharia as 5 da manha, sem ninguem para
    # ver. E a mesma armadilha que o backup_gerempre.ps1 ja registra, e
    # que la fez nascer o CaminhoLocal.
    #
    # Sao as MESMAS pastas, so que ditas de dentro:
    #     \\servidor\TRABALHO      =  D:\TRABALHO
    #     \\servidor\NeoGerempre   =  C:\NeoGerempre
    # Entao o relato continua chegando na estacao pelo compartilhamento.
    [string]$Copias  = 'D:\TRABALHO\BKP-GS',
    [string]$Relatos = 'C:\NeoGerempre\_ROTINAS_DO_SERVIDOR',
    [switch]$SoOlhar
)

$ErrorActionPreference = 'Continue'

$carimbo = Get-Date -Format 'yyyy-MM-dd_HHmm'
$LOG = Join-Path $Relatos ("_varredura_" + $carimbo + ".txt")
function Anotar($t) {
    $l = "[{0}] {1}" -f (Get-Date -Format 'dd/MM HH:mm:ss'), $t
    Write-Output $l
    try { Add-Content -Path $LOG -Value $l -Encoding utf8 } catch { }
}

$gfix  = Join-Path $Bin 'gfix.exe'
$gstat = Join-Path $Bin 'gstat.exe'
$db    = 'localhost:' + $Arquivo

function Cabecalho {
    <# Le o cabecalho do ARQUIVO, sem falar com a engine. #>
    $s = & $gstat -h $Arquivo 2>&1
    $n = @{ bruto = ($s -join "`n") }
    foreach ($l in $s) {
        if ($l -match '^\s*Oldest transaction\s+(\d+)') { $n['OIT']  = [int64]$Matches[1] }
        if ($l -match '^\s*Oldest active\s+(\d+)')      { $n['OAT']  = [int64]$Matches[1] }
        if ($l -match '^\s*Oldest snapshot\s+(\d+)')    { $n['snap'] = [int64]$Matches[1] }
        if ($l -match '^\s*Next transaction\s+(\d+)')   { $n['next'] = [int64]$Matches[1] }
        if ($l -match '^\s*Page buffers\s+(\d+)')       { $n['buf']  = [int64]$Matches[1] }
    }
    return $n
}

function Desisti($porque) {
    Anotar ''
    Anotar "PAREI: $porque"
    Anotar 'Nada foi desligado. O banco continua como estava, e a'
    Anotar 'varredura automatica continua ligada - que e o certo quando'
    Anotar 'a manual nao pode ser provada.'
    exit 1
}

Anotar '============================================================'
Anotar ' A VARREDURA DE DOMINGO'
Anotar (" maquina " + $env:COMPUTERNAME + "   como " + $env:USERNAME)
if ($SoOlhar) { Anotar ' MODO OLHAR - nao vai varrer nem desligar nada' }
Anotar '============================================================'

# ===================================================== 1. o terreno
Anotar ''
Anotar '1. Conferindo o terreno'

foreach ($f in @($gfix, $gstat, $Arquivo, $Config)) {
    if (-not (Test-Path $f)) { Desisti "nao achei $f" }
}
Anotar '   as ferramentas e o banco estao onde deviam'

$svc = Get-Service -Name $Servico -ErrorAction SilentlyContinue
if (-not $svc -or $svc.Status -ne 'Running') {
    Desisti "o servico $Servico nao esta no ar (esta '$($svc.Status)')"
}
Anotar "   servico $Servico : no ar"

# QUEM ESTA CONECTADO. Varrer com gente dentro nao e erro tecnico, mas
# e quebra de combinado: a hora foi escolhida para nao haver ninguem, e
# havendo alguem e sinal de que algo mudou e ninguem avisou.
$ligados = @(netstat -an | Select-String ':3050\s' | Select-String 'ESTABLISHED').Count
Anotar "   conexoes no banco agora: $ligados"
if ($ligados -gt 0 -and -not $SoOlhar) {
    Desisti "ha $ligados conexao(oes) no banco - a rotina so corre com a casa vazia"
}

# A COPIA FRIA DE HOJE. Sem restauracao possivel, ela e a unica volta.
$hoje = Get-Date -Format 'yyyy-MM-dd'
$copia = @(Get-ChildItem -Path $Copias -Directory -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -like "$hoje*" } |
           Sort-Object LastWriteTime -Descending) | Select-Object -First 1
if (-not $copia) {
    Desisti "nao ha copia fria de hoje em $Copias - o backup das 03:00 falhou ou nao correu"
}
$copiado = Join-Path $copia.FullName 'neobdados.fdb'
if (-not (Test-Path $copiado)) {
    Desisti "a pasta $($copia.Name) existe mas nao tem o neobdados.fdb dentro"
}
$tamCopia = (Get-Item $copiado).Length
$tamVivo  = (Get-Item $Arquivo).Length
Anotar ("   copia fria de hoje: " + $copia.Name + "  (" + [math]::Round($tamCopia/1MB,1) + " MB)")
if ($tamCopia -lt ($tamVivo * 0.9)) {
    Desisti ("a copia tem " + [math]::Round($tamCopia/1MB,1) +
             " MB e o banco vivo tem " + [math]::Round($tamVivo/1MB,1) +
             " MB - copia truncada nao serve de volta")
}
Anotar '   a copia tem tamanho compativel com o banco vivo'

# ================================================== 2. antes de varrer
Anotar ''
Anotar '2. O cabecalho ANTES'

$antes = Cabecalho
if (-not $antes.ContainsKey('OIT')) { Desisti 'nao consegui ler o cabecalho do banco' }
$vaoAntes = $antes['snap'] - $antes['OIT']
Anotar ("   Oldest transaction : " + $antes['OIT'])
Anotar ("   Oldest snapshot    : " + $antes['snap'])
Anotar ("   Next transaction   : " + $antes['next'])
Anotar ("   Page buffers       : " + $antes['buf'])
Anotar ("   VAO                : $vaoAntes   (" + [math]::Round($vaoAntes/20000) + "x o intervalo)")

if ($antes['buf'] -lt 10000) {
    Anotar '   AVISO: o cache esta baixo. Era para estar em 50000 desde 21/09.'
    Anotar '   A varredura vai correr assim mesmo, so que mais devagar.'
}

if ($SoOlhar) {
    Anotar ''
    Anotar 'MODO OLHAR: pararia aqui. A varredura NAO foi rodada.'
    exit 0
}

# ====================================================== 3. a varredura
Anotar ''
Anotar '3. A varredura - e ela vai demorar'
Anotar '   NAO REINICIE O FIREBIRD ENQUANTO ISTO CORRE. Reiniciar aborta'
Anotar '   a varredura e joga fora tudo o que ela ja moeu - e foi isso'
Anotar '   que impediu o conserto todas as outras vezes.'

$env:ISC_USER = (Select-String -Path $Config -Pattern '^User_Name=(.+)$' |
                 ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() } | Select-Object -First 1)
$env:ISC_PASSWORD = (Select-String -Path $Config -Pattern '^Password=(.+)$' |
                     ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() } | Select-Object -First 1)

$relogio = [Diagnostics.Stopwatch]::StartNew()
$saida = & $gfix -sweep $db 2>&1
$relogio.Stop()
$codigo = $LASTEXITCODE
$env:ISC_PASSWORD = ''; $env:ISC_USER = ''

Anotar ("   levou " + [math]::Round($relogio.Elapsed.TotalMinutes,1) + " minutos")
if ($saida) { $saida | ForEach-Object { Anotar "   gfix diz: $_" } }
else        { Anotar '   gfix nao disse nada - e como ele diz que deu certo' }

if ($codigo -ne 0 -or ($saida -match 'error|corrupt|unavailable|I/O')) {
    Desisti "a varredura devolveu erro (codigo $codigo)"
}

# ================================================ 4. provar que andou
Anotar ''
Anotar '4. O cabecalho DEPOIS - e e ele que decide'

$depois = Cabecalho
if (-not $depois.ContainsKey('OIT')) { Desisti 'nao consegui reler o cabecalho' }
$vaoDepois = $depois['snap'] - $depois['OIT']
$andou = $depois['OIT'] - $antes['OIT']

Anotar ("   Oldest transaction : " + $antes['OIT'] + "  ->  " + $depois['OIT'] + "   (andou $andou)")
Anotar ("   VAO                : $vaoAntes  ->  $vaoDepois")

if ($andou -le 0) {
    Desisti ('a Oldest transaction NAO ANDOU. A varredura correu e nao ' +
             'limpou o que prendia o banco - e ai desligar a automatica ' +
             'seria tirar a unica coisa que ainda tentava.')
}

if ($vaoDepois -ge 20000) {
    Anotar ''
    Anotar "   ATENCAO: andou, mas o vao ainda esta em $vaoDepois - acima do"
    Anotar '   intervalo de 20000. Melhorou e nao resolveu. NAO vou desligar'
    Anotar '   a varredura automatica; e caso de olhar com calma.'
    Anotar ''
    Anotar 'PAREI AQUI, de proposito. Metade do conserto e melhor que'
    Anotar 'nenhum, mas nao autoriza o passo seguinte.'
    exit 0
}

Anotar '   o vao caiu para dentro do intervalo - a varredura deu conta'

# ============================== 5. so agora desligar a automatica
Anotar ''
Anotar '5. Desligando a varredura automatica'
Anotar '   So chego aqui porque o passo 4 PROVOU que a varredura manual'
Anotar '   funciona neste banco. Com ela provada, a automatica so'
Anotar '   atrapalha: ela dispara no meio do expediente.'

$env:ISC_USER = (Select-String -Path $Config -Pattern '^User_Name=(.+)$' |
                 ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() } | Select-Object -First 1)
$env:ISC_PASSWORD = (Select-String -Path $Config -Pattern '^Password=(.+)$' |
                     ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() } | Select-Object -First 1)
$s = & $gfix -housekeeping 0 $db 2>&1
$cod = $LASTEXITCODE
$env:ISC_PASSWORD = ''; $env:ISC_USER = ''

if ($s) { $s | ForEach-Object { Anotar "   gfix diz: $_" } }
if ($cod -ne 0) {
    Anotar '   NAO CONSEGUI desligar. Nao e grave: o banco esta limpo, e a'
    Anotar '   automatica so vai disparar daqui a 20000 transacoes - e ai'
    Anotar '   sera uma varredura pequena, que corre rapido.'
} else {
    Anotar '   varredura automatica desligada'
}

# ========================================================= o resultado
Anotar ''
Anotar '============================================================'
Anotar ' DEU CERTO'
Anotar ("   Oldest transaction andou " + $andou + " transacoes")
Anotar ("   vao: $vaoAntes  ->  $vaoDepois")
Anotar ("   a varredura levou " + [math]::Round($relogio.Elapsed.TotalMinutes,1) + " minutos")
Anotar ''
Anotar ' O QUE FALTA, e e para gente decidir na segunda:'
Anotar '   agendar uma varredura semanal, junto do backup das 03:00,'
Anotar '   agora que se sabe quanto ela custa.'
Anotar '============================================================'
exit 0
