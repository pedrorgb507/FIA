# Conserta o "Nao foi possivel encontrar locais de conteudo" do CorelDRAW.
#
# O QUE ACONTECEU (11/09/2026): o OneDrive moveu a pasta Documentos do
# usuario para C:\Users\Eudson\OneDrive\Documents (Known Folder Move). O
# conteudo do Corel - fills, templates, simbolos, 85 MB - foi junto. Mas
# os caminhos gravados pelo Corel apontam para o lugar VELHO,
# C:\Users\Eudson\Documents\Corel\Corel Content, que ficou como casca
# vazia. Ao abrir, o Corel nao acha nada la e mostra a janela. E a janela
# e MODAL: quando a FIA abre o Corel por COM para converter um .cdr da
# VOPRIX, a chamada fica presa dois minutos e falha com 'Falha na execucao
# do servidor' (-2146959355). O arquivo vira pendencia.
#
# O CONSERTO: a casca vazia vira uma JUNCAO para a pasta de verdade.
# Qualquer caminho - o velho ou o do OneDrive - cai no mesmo conteudo.
# Nao precisa fechar o Corel, nao precisa mexer em opcao nenhuma, e o
# Corel pode regravar as configuracoes a vontade que continua valendo.
#
# DE QUEBRA: o registro do Corel traz caminhos de um perfil que nao
# existe mais (C:\Users\Administrator, C:\Users\ADMINI~1) - as
# configuracoes vieram de outra conta. Sao as pastas de documentos,
# impressao e BACKUP AUTOMATICO. Backup apontando para pasta inexistente
# e backup que nao acontece. Este script os aponta para o perfil atual.
# ATENCAO: essa parte so pega com o Corel FECHADO - ele regrava o
# registro ao sair, com o que tinha na memoria.
#
# Pode rodar quantas vezes quiser: nao faz nada do que ja esta feito.
#
#     powershell -ExecutionPolicy Bypass -File ferramentas\consertar_corel.ps1

$ErrorActionPreference = 'Stop'

$casca = "$env:USERPROFILE\Documents\Corel\Corel Content"
$real  = "$env:USERPROFILE\OneDrive\Documents\Corel\Corel Content"

Write-Host "== 1. a juncao =="
if (-not (Test-Path $real)) {
    throw "a pasta de verdade nao existe: $real  (o OneDrive esta ligado?)"
}
if (Test-Path $casca) {
    $item = Get-Item $casca
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Host "   ja e juncao -> $($item.Target)"
    } else {
        $n = (Get-ChildItem $casca -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
        if ($n -gt 0) {
            throw "a pasta velha NAO esta vazia ($n arquivos). Nao apago sozinho - confira $casca"
        }
        Remove-Item $casca -Recurse -Force
        cmd /c mklink /J "$casca" "$real" | Out-Null
        Write-Host "   criada: $casca -> $real"
    }
} else {
    New-Item -ItemType Directory -Force (Split-Path $casca) | Out-Null
    cmd /c mklink /J "$casca" "$real" | Out-Null
    Write-Host "   criada: $casca -> $real"
}
Write-Host "   subpastas vistas pelo caminho velho: $((Get-ChildItem $casca -Directory).Count)"

Write-Host "== 2. os caminhos do perfil que nao existe =="
$corel = Get-Process CorelDRW -ErrorAction SilentlyContinue
if ($corel) {
    Write-Host "   o CorelDRAW esta ABERTO (PID $($corel.Id)). Ele regrava o registro ao"
    Write-Host "   sair e desfaria esta parte. Feche o Corel e rode de novo."
} else {
    $chave = 'HKCU:\Software\Corel\CorelDRAW\27.0\Draw\Application Preferences\Directories'
    $docs  = [Environment]::GetFolderPath('MyDocuments') + '\'
    $temp  = "$env:LOCALAPPDATA\Temp\"
    $k = Get-Item $chave
    foreach ($nome in $k.GetValueNames()) {
        $v = [string]$k.GetValue($nome)
        if ($v -match 'Administrator|ADMINI~1') {
            $novo = if ($v -match 'Temp') { $temp } else { $docs }
            Set-ItemProperty -Path $chave -Name $nome -Value $novo
            Write-Host ("   {0,-20} {1}  ->  {2}" -f $nome, $v, $novo)
        }
    }
    Write-Host "   feito."
}
