<#
    BACKUP DO GEREMPRE - copia a frio, com o servico parado.

    Versao do EUDSON-PC, 16/09/2026. O banco veio para ca porque o
    Firebird 2.0 do SERVIDOR recusa um INSERT com coluna repetida que o
    neogerempre.exe manda, e o 1.5 aceita. Ver a skill gerempre,
    armadilha 26.

    Este banco NAO aceita gbak (pagina 73787 corrompida), entao a unica
    copia integra possivel e a do ARQUIVO com o Firebird parado.

    DOIS DESTINOS, e a ordem importa:

      1. LOCAL    C:\BKP-GS                      sempre acontece
      2. ESPELHO  \\servidor\TRABALHO\BKP-GS     melhor esforco

    O local vem primeiro porque ele nao depende de rede nem de
    credencial: tarefa agendada roda como SYSTEM, e o SYSTEM desta
    maquina nao tem identidade no SERVIDOR. Se o espelho falhar, o
    backup do dia AINDA EXISTE - so nao saiu da maquina. O log diz.

    Ordem geral: para, copia, sobe, CONFERE, espelha, e so entao apaga
    backup velho. Backup ruim que apaga os bons e pior que nenhum.

    RODA NESTA MAQUINA, pelo Agendador de Tarefas.

    Uso:
        powershell -ExecutionPolicy Bypass -File backup_gerempre_eudson.ps1
#>

param(
    [string]$Banco   = 'C:\NeoGerempre\bdados',
    [string]$Destino = 'C:\BKP-GS',
    [string]$Espelho = '\\servidor\TRABALHO\BKP-GS',
    [int]   $Guardar = 14
)

$ErrorActionPreference = 'Stop'
$ARQUIVOS = @('neobdados.fdb', 'neocep')
if (-not (Test-Path $Destino)) { New-Item -ItemType Directory -Path $Destino -Force | Out-Null }
$LOG = Join-Path $Destino 'backup.log'

function Anotar([string]$texto) {
    $linha = "[{0}] {1}" -f (Get-Date -Format 'dd/MM/yyyy HH:mm:ss'), $texto
    Write-Output $linha
    try { Add-Content -Path $LOG -Value $linha -Encoding utf8 } catch { }
}

function OdsDoArquivo([string]$caminho) {
    # Pagina 0 do .fdb: ODS maior em 18..19, menor em 20..21. Prova
    # barata de que o que se copiou e um banco, e nao meio arquivo.
    $f = [System.IO.File]::OpenRead($caminho)
    try {
        $b = New-Object byte[] 32
        if ($f.Read($b, 0, 32) -lt 32) { return $null }
        return '{0}.{1}' -f [BitConverter]::ToUInt16($b, 18),
                            [BitConverter]::ToUInt16($b, 20)
    } finally { $f.Close() }
}

Anotar '--- comecando ---'
Anotar "banco: $Banco   destino: $Destino   espelho: $Espelho"

$origens = @()
foreach ($nome in $ARQUIVOS) {
    $c = Join-Path $Banco $nome
    if (-not (Test-Path $c)) { Anotar "PAREI: nao achei $c"; exit 1 }
    $origens += Get-Item $c
}
$precisa = ($origens | Measure-Object -Property Length -Sum).Sum
try {
    $letra = (Split-Path $Destino -Qualifier).TrimEnd(':')
    $livre = (Get-PSDrive -Name $letra).Free
    if ($livre -lt ($precisa * 1.2)) {
        Anotar ("PAREI: preciso de {0:N0} MB e ha {1:N0} MB livres" -f ($precisa/1MB), ($livre/1MB))
        exit 1
    }
} catch { Anotar 'nao consegui medir o espaco livre - sigo assim mesmo' }

# ------------------------------------------- ninguem pode estar ligado
#
# Parar o Firebird com alguem dentro nao e so feio: em 15/09/2026, as
# 19:38, pegou UMA conexao aberta e o servidor caiu com erro interno
# (GlobalRWLock::unlock while not holding a valid lock) e nao subiu de
# primeira. Havendo conexao, NAO SE TOCA NO SERVICO.
$ligados = @()
try { $ligados = @(Get-NetTCPConnection -LocalPort 3050 -State Established -ErrorAction Stop) }
catch { $ligados = @(netstat -an | Select-String ':3050\s' | Select-String 'ESTABLISHED') }
if ($ligados.Count -gt 0) {
    Anotar ("PAREI: ha {0} conexao(oes) na porta 3050. Nao parei nada. Tento na proxima." -f $ligados.Count)
    exit 2
}
Anotar 'ninguem ligado na 3050 - pode parar com seguranca'

# ------------------------------------------------- avisar o vigia
#
# O vigia_firebird.ps1 roda de minuto em minuto e levanta o banco quando
# ele nao responde. Sem este aviso ele veria o Firebird parado POR NOSSA
# CAUSA, o subiria no meio da copia, e o backup sairia rasgado - o vigia
# estragaria justamente a rede de seguranca. Ele pula enquanto este
# arquivo existir e for recente.
$TRAVA = 'C:\Finart\_rotina\backup_em_curso.lock'
try {
    New-Item -ItemType Directory -Path (Split-Path $TRAVA) -Force | Out-Null
    Set-Content -Path $TRAVA -Value (Get-Date).ToString('o') -Encoding ASCII
    Anotar 'avisei o vigia (trava posta)'
} catch { Anotar "nao consegui por a trava do vigia: $($_.Exception.Message)" }

# ------------------------------------------------------ achar o servico
$servicos = @(Get-Service | Where-Object { $_.Name -like '*irebird*' })
if ($servicos.Count -eq 0) { Anotar 'PAREI: nao achei servico do Firebird'; exit 1 }
$rodando = @($servicos | Where-Object { $_.Status -eq 'Running' })
$ordemParar = @($rodando | Sort-Object { if ($_.Name -like '*uardian*') { 0 } else { 1 } })
Anotar ("servicos no ar: {0}" -f (($rodando | ForEach-Object { $_.Name }) -join ', '))
# Havendo Guardian, sobe SO ele: e ele que levanta o fbserver.
$guardioes = @($rodando | Where-Object { $_.Name -like '*uardian*' })
$subirDepois = if ($guardioes.Count) { $guardioes } else { $rodando }

$pasta = Join-Path $Destino (Get-Date -Format 'yyyy-MM-dd_HHmm')
$copiou = $false
try {
    foreach ($s in $ordemParar) {
        Anotar "parando $($s.Name)"
        try { Stop-Service -Name $s.Name -Force -ErrorAction Stop }
        catch { Anotar "   (ja estava parando: $($_.Exception.Message))" }
        try { (Get-Service $s.Name).WaitForStatus('Stopped', '00:02:00') }
        catch { Anotar "   (nao confirmou a parada: $($_.Exception.Message))" }
    }
    # PAROU MESMO? Esta pergunta nao e formalidade.
    #
    # Sem direito de administrador, o Stop-Service falha com "acesso
    # negado", o catch acima anota e a vida segue - e ai o script
    # copiaria o banco EM FUNCIONAMENTO. A conferencia la embaixo nao
    # pegaria: o tamanho do .fdb nao muda e o cabecalho continua legivel.
    # Guardaria uma copia rasgada como boa e apagaria as boas na
    # rotacao. Entao: se algum servico ainda estiver de pe, nao se copia
    # NADA.
    $teimosos = @($ordemParar | ForEach-Object { Get-Service $_.Name } |
                  Where-Object { $_.Status -ne 'Stopped' })
    if ($teimosos.Count -gt 0) {
        throw ("nao consegui parar: {0}. Sem parar, a copia sai rasgada - nao copiei nada. (Falta rodar como administrador?)" -f
               (($teimosos | ForEach-Object { $_.Name }) -join ', '))
    }

    New-Item -ItemType Directory -Path $pasta -Force | Out-Null
    foreach ($o in $origens) {
        Copy-Item -Path $o.FullName -Destination (Join-Path $pasta $o.Name) -Force
        Anotar ("copiei {0} ({1:N0} MB)" -f $o.Name, ($o.Length/1MB))
    }
    $copiou = $true
}
catch { Anotar "FALHOU no meio da copia: $($_.Exception.Message)" }
finally {
    # SEMPRE sobe de volta. Banco parado por causa do backup e estrago
    # maior que o backup.
    foreach ($s in $subirDepois) {
        try {
            Start-Service -Name $s.Name
            (Get-Service $s.Name).WaitForStatus('Running', '00:02:00')
            Anotar "subi $($s.Name)"
        } catch { Anotar "NAO CONSEGUI SUBIR $($s.Name): $($_.Exception.Message)" }
    }
    # E SEMPRE solta a trava, mesmo tendo dado errado no meio. Trava
    # esquecida cega o vigia - por isso ele tambem a ignora depois de 15
    # minutos, mas quinze minutos cego ja e tempo demais.
    try { Remove-Item $TRAVA -Force -ErrorAction SilentlyContinue; Anotar 'soltei a trava do vigia' } catch { }
}
if (-not $copiou) { Anotar 'PAREI: a copia falhou. Nada foi apagado.'; exit 1 }

# ----------------------------------------------------------- conferencia
$bom = $true
foreach ($o in $origens) {
    $copia = Join-Path $pasta $o.Name
    $tam = (Get-Item $copia).Length
    if ($tam -ne $o.Length) {
        Anotar ("RUIM: {0} saiu com {1:N0} bytes, o original tem {2:N0}" -f $o.Name, $tam, $o.Length)
        $bom = $false; continue
    }
    $ods = OdsDoArquivo $copia
    if (-not $ods) { Anotar "RUIM: $($o.Name) sem cabecalho legivel"; $bom = $false }
    else { Anotar ("confere {0}: {1:N0} bytes, ODS {2}" -f $o.Name, $tam, $ods) }
}
if (-not $bom) { Anotar 'PAREI: nao passou na conferencia. NAO apaguei backup velho.'; exit 1 }

# --------------------------------------------------------------- espelho
# Melhor esforco: falhar aqui NAO invalida o backup, so o deixa preso a
# esta maquina. E um aviso, nao um erro.
try {
    if (-not (Test-Path $Espelho)) { New-Item -ItemType Directory -Path $Espelho -Force -ErrorAction Stop | Out-Null }
    $la = Join-Path $Espelho (Split-Path $pasta -Leaf)
    Copy-Item -Path $pasta -Destination $la -Recurse -Force -ErrorAction Stop
    Anotar "espelhei em $la"
} catch {
    Anotar "AVISO: nao espelhei no servidor ($($_.Exception.Message)). O backup local esta feito."
}

# --------------------------------------------------------------- rotacao
# So chega aqui quem passou. E nunca deixa menos de dois.
foreach ($onde in @($Destino, $Espelho)) {
    try {
        $todos = @(Get-ChildItem $onde -Directory -ErrorAction Stop |
                   Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{4}$' } |
                   Sort-Object Name -Descending)
        $limite = (Get-Date).AddDays(-$Guardar)
        $velhos = @($todos | Select-Object -Skip 2 | Where-Object { $_.CreationTime -lt $limite })
        foreach ($v in $velhos) { Remove-Item $v.FullName -Recurse -Force; Anotar "apaguei $($v.Name) de $onde" }
        Anotar ("{0}: {1} backup(s)" -f $onde, ($todos.Count - $velhos.Count))
    } catch { Anotar "nao rodei a rotacao em $onde ($($_.Exception.Message))" }
}
Anotar 'pronto.'
exit 0
