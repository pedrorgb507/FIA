<#
    LIBERA A PORTA DA FILA DA MONTAGEM NO FIREWALL DESTA MAQUINA.
    Escrito em 18/09/2026.

    PARA QUE. A fila da montagem e uma pagina que a equipe abre DO PC
    DELA - e isso e o ponto do sistema inteiro, tirar a dependencia de
    quem senta na maquina da FIA. So que o Windows nao deixa ninguem
    entrar numa porta que nao foi pedida: o servidor sobe, a pagina abre
    NA PROPRIA maquina, e nao abre em nenhuma outra.

    E ISSO PARECE DEFEITO DO PROGRAMA, E NAO E. O sintoma engana: o
    console diz "no ar", o endereco esta certo, o navegador do outro PC
    fica girando e da tempo esgotado. Quem nao souber disto vai procurar
    erro no lugar errado.

    O QUE ESTE ARQUIVO FAZ, e o que ele custa:

    Abre a porta 8787 para ENTRADA, so em rede Particular e de Dominio -
    nao em rede Publica. Dali em diante, quem esta na rede interna da
    grafica alcanca a fila da montagem desta maquina.

    A troca, dita com todas as letras: quem estiver na rede interna
    alcanca essa porta, e nao ha senha na tela - foi escolha do operador
    ("senha em grafica vira papelzinho no monitor"), e quem decidiu fica
    gravado pelo NOME que a pessoa digita. Isto e uma tela de fila de
    servico numa rede de escritorio; nao ponha esta maquina na internet
    com essa regra ligada.

    RODE UMA VEZ, na maquina da FIA - a que roda o iniciar_montagem.bat.
    Nas outras nao precisa: elas so abrem o navegador.

    VOCE PODE NAO PRECISAR DESTE ARQUIVO. Em 18/09/2026 a liberacao saiu
    por outro caminho, e funcionou igual: na primeira vez que o Python
    escutou na porta, o Windows perguntou "permitir acesso?" e o
    operador disse que sim. Isso cria DUAS regras chamadas 'python.exe'
    - TCP e UDP -, de Entrada, perfil Particular, para AQUELE executavel
    e QUALQUER porta. Conferido de outra maquina: a fila abriu.

    A diferenca, dita para quem escolher: o pop-up libera qualquer porta
    que aquele python venha a abrir; este arquivo libera so a 8787. As
    duas resolvem hoje, e a daqui e a mais estreita.

    ARMADILHA AO CONFERIR, e ela me enganou primeiro: sem ser
    administrador, o `Get-NetFirewallRule` responde VAZIO em vez de
    recusar - 0 regras de entrada numa maquina que tem 353. Quem
    acreditar nele conclui que nao ha regra nenhuma e vai consertar o
    que nao esta quebrado. Para conferir sem elevacao, use o netsh:

        netsh advfirewall firewall show rule name=all dir=in
        netsh advfirewall firewall show rule name="python.exe" dir=in verbose

    E NAO DA PARA TESTAR DAQUI. O firewall nao se aplica a quem chama
    127.0.0.1 nem o proprio IP da maquina: um teste local responde 200
    mesmo com a porta fechada para o mundo. Quem prova e outra maquina
    abrindo o atalho do X:.

    PARA DESFAZER:
        Remove-NetFirewallRule -DisplayName 'FINART - fila da montagem'
#>

$ErrorActionPreference = 'Stop'
$REGRA = 'FINART - fila da montagem'
$PORTA = 8787

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  So administrador mexe em regra de firewall.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host "  Maquina: $env:COMPUTERNAME"
Write-Host "  Porta:   $PORTA (entrada, TCP)"
Write-Host ''

$ja = Get-NetFirewallRule -DisplayName $REGRA -ErrorAction SilentlyContinue
if ($ja) {
    Write-Host '  A regra ja existia. Nada a fazer.' -ForegroundColor Yellow
    Write-Host '  Nao abrindo de outro PC, entao o problema aqui e outro:'
    Write-Host '   - o servidor esta rodando? (iniciar_montagem.bat)'
    Write-Host '   - o outro PC esta na mesma rede?'
    Write-Host '   - ha outro firewall (antivirus proprio) nesta maquina?'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 0
}

New-NetFirewallRule -DisplayName $REGRA `
    -Description 'Fila da montagem da AMERICA, aberta pela equipe no navegador.' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort $PORTA `
    -Profile Domain,Private | Out-Null

$posta = Get-NetFirewallRule -DisplayName $REGRA -ErrorAction SilentlyContinue
Write-Host ''
if ($posta) {
    Write-Host '  Pronto. A porta esta aberta para a rede interna.' -ForegroundColor Green
    Write-Host ''
    Write-Host '  A PROVA NAO E ESTA TELA. Suba o iniciar_montagem.bat e'
    Write-Host '  abra, DE OUTRO PC, o endereco que ele imprime.'
    Write-Host ''
    Write-Host '  Enderecos desta maquina:'
    try {
        Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object { $_.IPAddress -ne '127.0.0.1' } |
            ForEach-Object { Write-Host "     http://$($_.IPAddress):$PORTA/" }
    } catch {
        Write-Host "     http://$env:COMPUTERNAME`:$PORTA/"
    }
} else {
    Write-Host '  NAO ENTROU. Algo recusou - me chame.' -ForegroundColor Red
}
Write-Host ''
Read-Host '  Enter para fechar'
