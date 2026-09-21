<#
    TIRA O COMPARTILHAMENTO DA PASTA DO PROJETO.

    Pedido do operador em 21/09/2026: "tire o compartilhamento da pasta
    C:\PROJETO FECHAMENTO CHAPA, nao deixe compartilhada".

    POR QUE ELA FOI COMPARTILHADA, e por que sai. A ideia era abrir o
    mesmo projeto de outra maquina para duas pessoas trabalharem juntas.
    Pasta compartilhada nao faz isso: os dois editam OS MESMOS ARQUIVOS,
    e quem salvar por ultimo apaga o do outro - sem o Git ficar sabendo,
    porque nunca existiram duas versoes para ele comparar.

    E HA UM PERIGO MAIOR, especifico desta casa. A trava que impede duas
    FIAs rodando e um bloqueio de arquivo em PASTA_CONTROLE, que e
    C:\Finart\_ctp_ia - uma pasta LOCAL de cada maquina. Abrindo o
    projeto pela rede, o VS Code sobe a tarefa sozinho (runOn
    folderOpen) e a FIA da outra maquina procura a trava no C: DELA, onde
    nao ha nenhuma. As duas sobem, nenhuma enxerga a outra, e as duas
    gravam chapa e abrem OS do mesmo arquivo. Foi o 08/09/2026, quando
    seis arquivos sairam em duplicidade - so que a trava que consertou
    aquilo nao alcanca este caso.

    O JEITO CERTO e o que ja funciona com o notebook: cada maquina com o
    seu CLONE do GitHub, pasta propria, .venv proprio e config_local
    proprio. Ai o Git junta de verdade.

    PRECISA DE ADMINISTRADOR - so administrador mexe em compartilhamento.

    PARA DESFAZER, se um dia precisar:
        New-SmbShare -Name "PROJETO FECHAMENTO CHAPA" `
                     -Path "C:\PROJETO FECHAMENTO CHAPA"
#>

param([string]$Nome = "PROJETO FECHAMENTO CHAPA")

$ErrorActionPreference = 'Stop'

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  So administrador mexe em compartilhamento de pasta.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

$ex = Get-SmbShare -Name $Nome -ErrorAction SilentlyContinue
if (-not $ex) {
    Write-Host ''
    Write-Host "  '$Nome' ja nao esta compartilhada. Nada a fazer." -ForegroundColor Yellow
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 0
}

Write-Host ''
Write-Host "  compartilhamento : $($ex.Name)"
Write-Host "  pasta            : $($ex.Path)"

# QUEM ESTA COM ARQUIVO ABERTO DE LA. Tirar por cima de alguem
# trabalhando faz o programa dele perder o arquivo no meio de um
# 'salvar' - e isso corrompe, nao so atrapalha.
$abertos = @(Get-SmbOpenFile -ErrorAction SilentlyContinue |
             Where-Object { $_.Path -like "$($ex.Path)*" })
if ($abertos) {
    Write-Host ''
    Write-Host '  ATENCAO: ha arquivo aberto de outra maquina:' -ForegroundColor Yellow
    $abertos | ForEach-Object {
        Write-Host ("     {0}  ->  {1}" -f $_.ClientComputerName, $_.Path)
    }
    Write-Host ''
    Write-Host '  Tirando agora, quem estiver salvando perde o arquivo no meio.'
    $r = Read-Host '  Digite TIRAR para seguir assim mesmo, ou Enter para desistir'
    if ($r -ne 'TIRAR') {
        Write-Host '  Desisti. Nada foi mudado.'
        Read-Host '  Enter para fechar'
        exit 0
    }
}

Remove-SmbShare -Name $Nome -Force
Write-Host ''
Write-Host '  Pronto - a pasta nao esta mais compartilhada.' -ForegroundColor Green
Write-Host ''
Write-Host '  De outra maquina, use o CLONE do GitHub:'
Write-Host '     git clone https://github.com/pedrorgb507/FIA.git "C:\PROJETO FECHAMENTO CHAPA"'
Write-Host ''
Read-Host '  Enter para fechar'
