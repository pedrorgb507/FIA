<#
    TRAZ PARA A PASTA DE REDE O QUE O VIGIA DO FIREBIRD ANOTOU.

    RODE NO SERVIDOR, com dois cliques no .bat ao lado.

    POR QUE ELE EXISTE. O vigia mora em C:\Finart\_rotina, e essa pasta
    nao e compartilhada - de fora nao se alcanca o C: do servidor sem
    direito de administrador, e o Windows PENDURA a conexao em vez de
    recusar, o que engana quem esta conferindo. Entao o log vem ate a
    pasta que todo mundo enxerga.

    O QUE ELE FAZ, e so isso: COPIA arquivos de log para o
    _ROTINAS_DO_SERVIDOR e imprime um resumo. Nao para servico, nao
    reinicia nada, nao apaga nada. Pode rodar com o GEREMPRE em uso.

    DUAS PERGUNTAS QUE ELE RESPONDE

    1. A instalacao pegou? Compara o vigia_firebird.ps1 que esta
       RODANDO (o de C:\Finart\_rotina) com o da pasta de rede, e diz se
       ele tem os parametros novos de 21/09/2026. Copiar para a pasta de
       rede nao basta: quem roda de minuto em minuto e a copia do C:.

    2. POR QUE a checagem do vigia falhava? E a pergunta que ficou de pe
       quando ele foi afrouxado. A resposta esta escrita no vigia.log, na
       linha que ele anota antes de reiniciar - 'banco NAO respondeu (N
       de M): <motivo>'. O motivo e o que diz se o isql saiu de lugar, se
       a consulta estourou o prazo ou se a engine travou de verdade.

    SEM ADMINISTRADOR ele ainda serve: so a consulta da tarefa agendada
    precisa de elevacao, e ele diz isso em vez de calar.
#>

$ErrorActionPreference = 'Continue'

$PASTA   = 'C:\Finart\_rotina'
$REDE    = '\\servidor\NeoGerempre\_ROTINAS_DO_SERVIDOR'
$DESTINO = Join-Path $REDE ('_log_do_vigia_' + $env:COMPUTERNAME)

function Titulo([string]$t) {
    Write-Host ''
    Write-Host ('== ' + $t) -ForegroundColor Cyan
}

Write-Host ''
Write-Host "  Maquina: $env:COMPUTERNAME"

# ------------------------------------------------ 1. a instalacao pegou?
Titulo 'O vigia que esta RODANDO (a copia do C:)'
$rodando = Join-Path $PASTA 'vigia_firebird.ps1'
if (-not (Test-Path $rodando)) {
    Write-Host "  NAO EXISTE $rodando" -ForegroundColor Red
    Write-Host '  A instalacao nao chegou a acontecer nesta maquina.'
} else {
    $i = Get-Item $rodando
    Write-Host ("  {0}  ({1:n0} bytes, de {2:dd/MM/yyyy HH:mm})" -f $rodando, $i.Length, $i.LastWriteTime)
    $txt = Get-Content $rodando -Raw
    # As tres marcas do afrouxamento de 21/09/2026. Procura-se o QUE MUDA
    # o comportamento, e nao a data no comentario: comentario se copia,
    # parametro e o que o programa obedece.
    $novo = @(
        @{ n = 'Falhas = 5 (era 2)';        tem = ($txt -match '\$Falhas\s*=\s*5') },
        @{ n = 'PrazoConsulta = 60 s';      tem = ($txt -match '\$PrazoConsulta\s*=\s*60') },
        @{ n = '"nao sei dizer" (a raiz)';  tem = ($txt -match 'naoSeiDizer') }
    )
    foreach ($m in $novo) {
        if ($m.tem) { Write-Host ("     SIM  " + $m.n) -ForegroundColor Green }
        else        { Write-Host ("     NAO  " + $m.n) -ForegroundColor Red }
    }
    if ($novo | Where-Object { -not $_.tem }) {
        Write-Host '  => A copia velha ainda esta rodando. Rode o INSTALAR ROTINAS.bat' -ForegroundColor Yellow
        Write-Host '     COMO ADMINISTRADOR, na pasta de rede.'
    } else {
        Write-Host '  => E a versao nova. A instalacao pegou.' -ForegroundColor Green
    }
}

# ------------------------------------------------------ 2. a tarefa
Titulo 'A tarefa agendada'
$t = schtasks /Query /TN 'Vigia GEREMPRE' /V /FO LIST 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host '  nao consegui consultar. Sem elevacao o schtasks responde'
    Write-Host '  "Acesso negado" - que NAO quer dizer que a tarefa sumiu.'
    Write-Host "  ($($t | Select-Object -First 1))"
} else {
    $t | Select-String -Pattern 'Nome da tarefa|TaskName|Pr.ximo|Next Run|Ultima|Last Run|Status|Result' |
        ForEach-Object { Write-Host ('     ' + $_.Line.Trim()) }
}

# --------------------------------------------------- 3. copia os logs
Titulo 'Trazendo os arquivos para a pasta de rede'
if (-not (Test-Path $REDE)) {
    Write-Host "  NAO ALCANCO $REDE" -ForegroundColor Red
    Write-Host '  O servidor consegue se enxergar pelo proprio nome?'
    Read-Host '  Enter para fechar'
    exit 1
}
if (-not (Test-Path $DESTINO)) { New-Item -ItemType Directory -Path $DESTINO -Force | Out-Null }

$quantos = 0
foreach ($n in 'vigia.log', 'vigia_estado.txt', 'vigia_reinicios.txt',
                'vigia_nao_sei_perguntar.txt', 'vigia_sem_banco.txt') {
    $de = Join-Path $PASTA $n
    if (Test-Path $de) {
        Copy-Item $de (Join-Path $DESTINO $n) -Force
        $i = Get-Item $de
        Write-Host ("     copiei {0,-30} {1:n0} bytes" -f $n, $i.Length)
        $quantos++
    } else {
        Write-Host ("     (nao existe) {0}" -f $n)
    }
}
Write-Host ''
Write-Host "  $quantos arquivo(s) em $DESTINO"

# ------------------------------------ 4. o essencial, aqui mesmo na tela
Titulo 'As ultimas linhas do vigia'
$log = Join-Path $PASTA 'vigia.log'
if (Test-Path $log) {
    Get-Content $log -Tail 20 | ForEach-Object { Write-Host ('     ' + $_) }
    Write-Host ''
    Titulo 'Por que a checagem falhava (as linhas que dizem o motivo)'
    $motivos = Get-Content $log | Select-String -Pattern 'NAO respondeu' |
               Select-Object -Last 8
    if ($motivos) { $motivos | ForEach-Object { Write-Host ('     ' + $_.Line) } }
    else { Write-Host '     nenhuma - o vigia nunca achou o banco fora.' }
} else {
    Write-Host '     nao existe vigia.log - ele nunca rodou nesta maquina.'
}

Write-Host ''
Read-Host '  Enter para fechar'
