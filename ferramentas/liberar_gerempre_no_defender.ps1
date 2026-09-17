<#
    LIBERA A PASTA DO GEREMPRE NO WINDOWS DEFENDER.
    Escrito em 17/09/2026.

    O CASO. Depois de o banco voltar para o servidor, o neogerempre.exe
    parou de abrir no EUDSON-PC - e abria nas outras maquinas. Nao era
    banco, nem rede, nem configuracao: os processos ficavam assim,

        threads ............ 1, em Wait / Suspended
        modulos carregados . 0
        conexao na 3050 .... nenhuma
        janela ............. nenhuma

    Processo com ZERO dll carregada nunca executou uma linha. Ele foi
    criado, suspenso, e ficou - o Windows segurando antes de comecar,
    que e o que o antivirus faz para varrer o executavel. Rodando da
    pasta LOCAL, o mesmo arquivo abria na hora: mesmo tamanho, mesmo
    SHA-256, sem marca da web. O que muda e so estar na rede.

    Abre nas outras maquinas porque o resultado da varredura fica em
    cache POR MAQUINA - as que ja passaram por isso nao repetem. Ou seja,
    as outras podem cair nisto mais adiante, quando o cache virar.

    O QUE ESTE ARQUIVO FAZ, e o que ele custa:

    Poe \\servidor\NeoGerempre na lista de excecoes do Defender DESTA
    maquina. Dali em diante o Defender nao varre o que esta nessa pasta,
    aqui. Isso e uma troca de verdade, e vale dize-la: se um dia alguem
    puser coisa ruim naquela pasta, esta maquina nao vai barrar.

    A excecao e so daquela pasta - nao do servidor inteiro, nao de C:\.
    Quem escreve la e quem tem acesso ao compartilhamento, e o programa
    que roda dali e o mesmo desde 2020.

    RODE ISTO EM CADA MAQUINA que abrir o GEREMPRE pela rede.
#>

$ErrorActionPreference = 'Stop'
$PASTA = '\\servidor\NeoGerempre'

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  So administrador mexe na lista do Defender - nem LER a lista'
    Write-Host '  da, sem isso.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host "  Maquina: $env:COMPUTERNAME"
Write-Host ''
Write-Host '  == Antes'
$antes = @((Get-MpPreference).ExclusionPath)
if ($antes -and $antes[0]) { $antes | ForEach-Object { Write-Host "     $_" } }
else { Write-Host '     (nenhuma excecao)' }

if ($antes -contains $PASTA) {
    Write-Host ''
    Write-Host "  $PASTA ja estava liberada. Nada a fazer." -ForegroundColor Yellow
    Write-Host '  Entao o problema aqui e outro - me chame.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 0
}

Add-MpPreference -ExclusionPath $PASTA
# o proprio processo tambem, para o que ele abrir dali nao ser varrido
# a cada leitura - e o que deixa relatorio grande abrir sem engasgo
Add-MpPreference -ExclusionProcess 'neogerempre.exe'

Write-Host ''
Write-Host '  == Depois'
$depois = @((Get-MpPreference).ExclusionPath)
$depois | ForEach-Object {
    if ($_ -eq $PASTA) { Write-Host "     $_   <- posta agora" -ForegroundColor Green }
    else { Write-Host "     $_" }
}

Write-Host ''
if ($depois -contains $PASTA) {
    Write-Host '  Pronto. Abra o GEREMPRE pelo atalho da rede.' -ForegroundColor Green
    Write-Host ''
    Write-Host '  A prova nao e esta tela: e o programa abrir. Se ele ficar'
    Write-Host '  parado de novo, NAO clique varias vezes - cada clique deixa'
    Write-Host '  um processo preso. Me chame.'
} else {
    Write-Host '  NAO ENTROU na lista. Algo recusou - me chame.' -ForegroundColor Red
}
Write-Host ''
Read-Host '  Enter para fechar'
