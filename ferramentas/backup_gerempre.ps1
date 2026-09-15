<#
    BACKUP DO GEREMPRE - copia a frio, com o servico parado.

    Este banco NAO aceita gbak: ha uma pagina corrompida (73787, na
    RDB$PROCEDURE_PARAMETERS) que derruba o backup em todas as variantes
    tentadas. Entao a unica copia integra possivel e a copia do ARQUIVO
    com o Firebird parado - copiar com ele no ar pega paginas de metade
    de uma escrita, e o que se guarda nao abre.

    Por isso a ordem aqui e: para, copia, sobe, CONFERE, e so entao
    apaga backup velho. Enquanto a conferencia nao passar, nada e
    apagado - um backup ruim que apaga os bons e pior que backup nenhum.

    RODA NO PROPRIO SERVIDOR, pelo Agendador de Tarefas, como SYSTEM ou
    como um administrador. Nao roda de fora: parar servico de outra
    maquina pede direito que a estacao nao tem.

    SOBRE O DESTINO: passe UNC ou caminho local, NUNCA letra mapeada.
    Tarefa agendada roda sem sessao de usuario, e Y: nao existe la -
    mapeamento de letra e por usuario, nao por maquina. Este script
    converte sozinho a UNC desta mesma maquina no caminho de disco dela.

    Uso:
        powershell -ExecutionPolicy Bypass -File backup_gerempre.ps1
        powershell ... -File backup_gerempre.ps1 -Guardar 30
#>

param(
    # onde os bancos vivos estao
    [string]$Banco   = 'C:\NeoGerempre\bdados',
    # onde guardar. \\servidor\TRABALHO\BKP-GS e o Y:\BKP-GS visto da rede
    [string]$Destino = '\\servidor\TRABALHO\BKP-GS',
    # quantos dias de backup manter
    [int]   $Guardar = 14
)

$ErrorActionPreference = 'Stop'
$ARQUIVOS = @('neobdados.fdb', 'neocep')

function CaminhoLocal([string]$caminho) {
    <#
        \\servidor\TRABALHO\BKP-GS  ->  D:\TRABALHO\BKP-GS (ou onde for)

        So converte se o compartilhamento for DESTA maquina. UNC de
        outra maquina fica como esta - e ai o SYSTEM provavelmente nao
        alcanca, e o script avisa antes de parar o banco.
    #>
    if ($caminho -notmatch '^\\\\([^\\]+)\\([^\\]+)(\\.*)?$') { return $caminho }
    $maquina = $Matches[1]; $share = $Matches[2]; $resto = $Matches[3]
    if ($maquina -ne $env:COMPUTERNAME -and
        $maquina -ne 'localhost' -and $maquina -ne '.') { return $caminho }

    $raiz = $null
    try { $raiz = (Get-SmbShare -Name $share -ErrorAction Stop).Path } catch { }
    if (-not $raiz) {
        try { $raiz = (Get-WmiObject Win32_Share -Filter "Name='$share'").Path }
        catch { }
    }
    if (-not $raiz) { return $caminho }
    if ($resto) { return (Join-Path $raiz $resto.TrimStart('\')) }
    return $raiz
}

$Destino = CaminhoLocal $Destino
$LOG = Join-Path $Destino 'backup.log'

function Anotar([string]$texto) {
    $linha = "[{0}] {1}" -f (Get-Date -Format 'dd/MM/yyyy HH:mm:ss'), $texto
    Write-Output $linha
    try { Add-Content -Path $LOG -Value $linha -Encoding utf8 } catch { }
}

function OdsDoArquivo([string]$caminho) {
    # A pagina 0 do .fdb traz a versao do formato: ODS maior em 18..19,
    # menor em 20..21, little endian. Serve de prova barata de que o que
    # foi copiado e mesmo um banco, e nao um arquivo pela metade.
    $f = [System.IO.File]::OpenRead($caminho)
    try {
        $b = New-Object byte[] 32
        if ($f.Read($b, 0, 32) -lt 32) { return $null }
        return '{0}.{1}' -f [BitConverter]::ToUInt16($b, 18),
                            [BitConverter]::ToUInt16($b, 20)
    } finally { $f.Close() }
}

# ---------------------------------------------------- destino e espaco
if ($Destino -match '^[A-Za-z]:' -and -not (Test-Path (Split-Path $Destino -Qualifier))) {
    Write-Output "PAREI: '$Destino' nao existe nesta maquina. Letra mapeada nao vale em tarefa agendada."
    exit 1
}
if (-not (Test-Path $Destino)) {
    New-Item -ItemType Directory -Path $Destino -Force | Out-Null
}
Anotar '--- comecando ---'
Anotar "destino: $Destino"

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
        Anotar ("PAREI: preciso de {0:N0} MB e ha {1:N0} MB livres" -f `
                ($precisa/1MB), ($livre/1MB))
        exit 1
    }
} catch { Anotar 'nao consegui medir o espaco livre - sigo assim mesmo' }

# ------------------------------------------------------ achar o servico
# O nome varia com a versao e a instalacao, entao procuramos em vez de
# adivinhar. O Guardian tem de parar ANTES do servidor: ele existe para
# levantar o servidor de volta, e faria isso no meio da copia.
$servicos = @(Get-Service | Where-Object { $_.Name -like '*irebird*' })
if ($servicos.Count -eq 0) { Anotar 'PAREI: nao achei servico do Firebird'; exit 1 }
$rodando = @($servicos | Where-Object { $_.Status -eq 'Running' })
if ($rodando.Count -eq 0) { Anotar 'aviso: nenhum servico do Firebird estava no ar' }
$ordemParar = @($rodando | Sort-Object { if ($_.Name -like '*uardian*') { 0 } else { 1 } })
Anotar ("servicos no ar: {0}" -f (($rodando | ForEach-Object { $_.Name }) -join ', '))

# QUEM SOBE DE VOLTA. Se havia Guardian, sobe SO o Guardian: e ele que
# levanta o fbserver, e esse e o trabalho dele. Tentar subir os dois deu
# errado na primeira execucao, em 15/09/2026 - o Start-Service do
# servidor falhou com uma mensagem que parecia grave e nao era, porque
# quando chegou a vez dele o Guardian ja o tinha levantado.
$guardioes = @($rodando | Where-Object { $_.Name -like '*uardian*' })
$subirDepois = if ($guardioes.Count) { $guardioes } else { $rodando }

# ------------------------------------------- ninguem pode estar ligado
#
# Parar o Firebird com alguem dentro nao e apenas feio: em 15/09/2026,
# as 19:38, a primeira execucao deste script pegou UMA conexao aberta
# (alguem com o neogerempre.exe na tela) e o servidor caiu com erro
# interno ao descer -
#
#   internal gds software consistency check
#   (Attempt to call GlobalRWLock::unlock() while not holding a valid lock)
#
# - e depois nao subiu de primeira. O banco nao se estragou, mas o
# backup nao saiu e o GEREMPRE ficou fora por um minuto e meio.
#
# Entao: havendo conexao, NAO SE TOCA NO SERVICO. Fica registrado e
# tenta-se amanha. Backup que derruba o banco e pior que backup que
# faltou - o que faltou aparece no log; o que derrubou aparece no
# telefone.
$ligados = @()
try {
    $ligados = @(Get-NetTCPConnection -LocalPort 3050 -State Established `
                 -ErrorAction Stop)
} catch {
    # Windows antigo nao tem Get-NetTCPConnection
    $ligados = @(netstat -an | Select-String ':3050\s' |
                 Select-String 'ESTABLISHED')
}
if ($ligados.Count -gt 0) {
    Anotar ("PAREI: ha {0} conexao(oes) aberta(s) na porta 3050. " -f $ligados.Count +
            "Nao parei o Firebird e nao copiei nada. Tento na proxima.")
    exit 2
}
Anotar 'ninguem ligado na 3050 - pode parar com seguranca'

$pasta = Join-Path $Destino (Get-Date -Format 'yyyy-MM-dd_HHmm')
$copiou = $false
try {
    foreach ($s in $ordemParar) {
        Anotar "parando $($s.Name)"
        # Parar o Guardian ja derruba o fbserver junto. Entao a segunda
        # parada costuma cair num servico que ja esta parado ou a meio
        # caminho - isso e NORMAL e nao pode derrubar o backup.
        try { Stop-Service -Name $s.Name -Force -ErrorAction Stop }
        catch { Anotar "   (ja estava parando: $($_.Exception.Message))" }
        try { (Get-Service $s.Name).WaitForStatus('Stopped', '00:02:00') }
        catch { Anotar "   (nao confirmou a parada: $($_.Exception.Message))" }
    }

    New-Item -ItemType Directory -Path $pasta -Force | Out-Null
    foreach ($o in $origens) {
        Copy-Item -Path $o.FullName -Destination (Join-Path $pasta $o.Name) -Force
        Anotar ("copiei {0} ({1:N0} MB)" -f $o.Name, ($o.Length/1MB))
    }
    $copiou = $true
}
catch {
    # SEM ISTO O MOTIVO SE PERDE. Na primeira execucao, em 15/09/2026, a
    # copia nao aconteceu e o log nao disse por que: com
    # ErrorActionPreference='Stop' o erro sobe, o finally roda, e o
    # script morre antes da linha que explicaria. Um backup que falha
    # calado e um backup que ninguem conserta.
    Anotar "FALHOU no meio da copia: $($_.Exception.Message)"
}
finally {
    # SEMPRE sobe de volta, mesmo se a copia falhou no meio. Banco
    # parado por causa de um backup e um estrago maior que o backup.
    foreach ($s in $subirDepois) {
        try {
            Start-Service -Name $s.Name
            (Get-Service $s.Name).WaitForStatus('Running', '00:02:00')
            Anotar "subi $($s.Name)"
        } catch { Anotar "NAO CONSEGUI SUBIR $($s.Name): $($_.Exception.Message)" }
    }
}
if (-not $copiou) { Anotar 'PAREI: a copia falhou. Nada foi apagado.'; exit 1 }

# ----------------------------------------------------------- conferencia
$bom = $true
foreach ($o in $origens) {
    $copia = Join-Path $pasta $o.Name
    $tam = (Get-Item $copia).Length
    if ($tam -ne $o.Length) {
        Anotar ("RUIM: {0} saiu com {1:N0} bytes, o original tem {2:N0}" -f `
                $o.Name, $tam, $o.Length)
        $bom = $false; continue
    }
    $ods = OdsDoArquivo $copia
    if (-not $ods) { Anotar "RUIM: $($o.Name) nao tem cabecalho legivel"; $bom = $false }
    else { Anotar ("confere {0}: {1:N0} bytes, ODS {2}" -f $o.Name, $tam, $ods) }
}
if (-not $bom) {
    Anotar 'PAREI: a copia nao passou na conferencia. NAO apaguei backup velho.'
    exit 1
}

# --------------------------------------------------------------- rotacao
# So chega aqui quem passou. E mesmo assim, nunca deixa menos de dois.
$todos = @(Get-ChildItem $Destino -Directory |
           Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{4}$' } |
           Sort-Object Name -Descending)
$limite = (Get-Date).AddDays(-$Guardar)
$velhos = @($todos | Select-Object -Skip 2 | Where-Object { $_.CreationTime -lt $limite })
foreach ($v in $velhos) {
    Remove-Item $v.FullName -Recurse -Force
    Anotar "apaguei o backup de $($v.Name)"
}
Anotar ("pronto. {0} backup(s) guardados em {1}" -f ($todos.Count - $velhos.Count), $Destino)
exit 0
