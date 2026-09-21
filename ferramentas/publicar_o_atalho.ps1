<#
    PUBLICA O ATALHO DA FILA NA PASTA QUE TODA A GRAFICA ENXERGA.

    Pedido do operador em 18/09/2026: facilitar abrir a fila da montagem
    nas OUTRAS maquinas da empresa.

    O QUE ELE FAZ. Le o `abrir_a_montagem.html` do repositorio, escreve
    nele o NOME e o IP desta maquina - a que roda o iniciar_montagem.bat
    - e grava a copia no X:, que e o \\servidor\TRABALHO ja mapeado em
    todo mundo. Dali, qualquer PC abre com dois cliques.

    POR QUE ELE ESCREVE O ENDERECO EM VEZ DE DEIXAR FIXO NO HTML: o IP
    desta maquina vem do roteador e muda quando ele quiser. Atalho com
    IP escrito a mao para de funcionar sozinho num dia qualquer, e
    ninguem liga uma coisa na outra. Rodando isto de novo, o atalho se
    conserta.

    RODE NA MAQUINA DA FIA, sempre que ela trocar de IP ou de nome:

        powershell -ExecutionPolicy Bypass -File ferramentas\publicar_o_atalho.ps1

    NAO precisa de administrador - so escreve um arquivo numa pasta de
    rede. Quem precisa de administrador e o
    `liberar_montagem_no_defender.ps1`, e esse e OUTRA coisa: sem ele a
    porta fica fechada e nenhuma outra maquina alcanca a fila, por mais
    bonito que o atalho esteja.
#>
param(
    [string]$Destino = "X:\MONTAGEM AMERICA - abrir aqui.html",
    [int]$Porta = 8787
)

$ErrorActionPreference = "Stop"
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$fonte = Join-Path $aqui "abrir_a_montagem.html"

if (-not (Test-Path $fonte)) {
    throw "nao achei o $fonte - este script mora ao lado dele"
}

# O NOME VEM DO CONFIG, e nao de quem rodou o script.
#
# Custou um dia: publiquei o atalho DAQUI, e ele saiu apontando para
# esta maquina - que nao e o servidor. A gráfica inteira clicava num
# endereco onde nao havia ninguem atendendo, e o erro nao aparecia de
# lugar nenhum, porque o atalho parecia certo.
#
# O servidor e UM SO e esta escrito no config (SERVIDOR_DA_MONTAGEM).
# Entao e de la que o nome sai, rode este script onde rodar.
$nome = $env:COMPUTERNAME
$doConfig = (Select-String -Path (Join-Path $aqui "..\src\finart_ctp\config.py") `
                          -Pattern '^SERVIDOR_DA_MONTAGEM\s*=\s*"([^"]+)"' `
             | Select-Object -First 1)
if ($doConfig) { $nome = $doConfig.Matches[0].Groups[1].Value }

# O IP E O DAQUELE NOME, e nao o desta maquina - senao o atalho diria
# um nome e um numero de computadores diferentes, e o numero e
# justamente a segunda tentativa de quem nao resolve o nome.
#
# IPv4 de proposito: o nome do servidor resolve primeiro em IPv6 nesta
# rede, e endereco IPv6 em atalho ninguem digita nem confere.
$ip = $null
if ($nome -ieq $env:COMPUTERNAME) {
    # descarta o 127.x (esta maquina falando consigo mesma, inutil para
    # os outros) e o 169.254.x (o que o Windows inventa quando NAO
    # conseguiu IP nenhum - publicar esse seria publicar um endereco
    # que nunca respondeu)
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
           Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and
                          $_.PrefixOrigin -ne 'WellKnown' } |
           Select-Object -First 1).IPAddress
} else {
    try {
        $ip = ([System.Net.Dns]::GetHostAddresses($nome) |
               Where-Object { $_.AddressFamily -eq 'InterNetwork' } |
               Select-Object -First 1).IPAddressToString
    } catch { }
}

if (-not $ip) {
    throw ("nao descobri o IPv4 de '$nome'. Ele esta ligado e na rede? " +
           "Sem o IP o atalho fica so com o nome, e se a rede nao " +
           "resolver o nome ninguem entra.")
}

$html = Get-Content $fonte -Raw -Encoding UTF8
$html = $html -replace 'var MAQUINA = "[^"]*";', ('var MAQUINA = "' + $nome + '";')
$html = $html -replace 'var IP      = "[^"]*";', ('var IP      = "' + $ip + '";')
$html = $html -replace 'var PORTA   = \d+;',     ('var PORTA   = ' + $Porta + ';')

$pasta = Split-Path -Parent $Destino
if (-not (Test-Path $pasta)) {
    throw "nao alcanco a pasta '$pasta' - o X: esta mapeado?"
}

# SEM BOM. Navegador le UTF-8 sem marca sem reclamar, e a marca ja
# apareceu como lixo no topo de pagina servida por pasta de rede.
[IO.File]::WriteAllText($Destino, $html, (New-Object Text.UTF8Encoding($false)))

Write-Output "publicado : $Destino"
Write-Output "aponta para: http://$nome`:$Porta/  (e http://$ip`:$Porta/)"
Write-Output ""
Write-Output "Em qualquer maquina: dois cliques nesse arquivo."
Write-Output "E no $nome - o servidor - o iniciar_montagem.bat tem de estar rodando."
if ($nome -ine $env:COMPUTERNAME) {
    Write-Output ""
    Write-Output ("(voce publicou de $env:COMPUTERNAME, que NAO e o servidor - " +
                  "isso e normal: o endereco sai do config, nao de quem roda.)")
}
