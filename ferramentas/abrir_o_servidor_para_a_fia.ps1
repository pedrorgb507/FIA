<#
    ABRE O SERVIDOR PARA A FIA TRABALHAR DE LONGE.

    RODA NO PROPRIO SERVIDOR, como ADMINISTRADOR. Uma vez so.

    Pedido do operador em 21/09/2026, depois de o GEREMPRE cair por 23
    minutos e o diagnostico travar por falta de dois arquivos que so
    existem no servidor: "como eu faco para voce ter acesso total ao
    servidor (...) sem eu precisar de ficar indo no servidor para dar
    algum comando?".

    ---------------------------------------------------------------
    POR QUE SO O ADMINISTRADOR NAO BASTA, e e aqui que quase todo
    mundo perde a tarde

    Esta rede e GRUPO DE TRABALHO (FINART), nao dominio. Cada maquina
    tem as contas dela, e nao ha Kerberos. Nisso o Windows faz uma
    coisa que nao avisa: conta LOCAL que e administradora recebe, pela
    REDE, um token REBAIXADO - com o grupo de administradores
    desativado. Entao a conta e administradora, o Windows diz que ela e
    administradora, e mesmo assim o Gerenciador de Servicos responde
    "talvez esta operacao exija outros privilegios".

    Foi exatamente o que aconteceu em 21/09/2026 as 17:47, com o banco
    fora do ar: eu nao conseguia nem LER o estado do servico.

    Quem desliga esse rebaixamento e uma chave de registro:

        LocalAccountTokenFilterPolicy = 1

    Sem ela, virar administrador NAO RESOLVE NADA. Com ela, a conta
    passa a valer inteira pela rede.

    ---------------------------------------------------------------
    O QUE ISTO LIGA, e o que cada coisa custa

      1. a conta no grupo Administradores     (quem manda)
      2. LocalAccountTokenFilterPolicy = 1    (para valer pela rede)
      3. WinRM - PowerShell remoto            (como os comandos chegam)
      4. regra de firewall SO DA REDE LOCAL   (quem pode bater na porta)

    O WinRM aqui e por HTTP, na 5985. Parece pior do que e: a conversa
    do PowerShell vai CRIPTOGRAFADA mesmo em HTTP, porque a
    autenticacao Negotiate/NTLM cifra a mensagem. O que o HTTPS daria a
    mais e provar QUEM e o servidor - e numa LAN de gráfica, com IP
    fixo, isso nao paga o custo de manter certificado.

    A regra de firewall fica presa na SUB-REDE LOCAL. Porta de comando
    aberta para a internet e outra categoria de problema, e esta
    maquina guarda o banco da empresa.

    ---------------------------------------------------------------
    O QUE ISTO NAO FAZ

    Nao mexe no Firebird, nao mexe no banco, nao cria tarefa agendada e
    nao apaga nada. So abre a porta e diz o que abriu.

    PARA DESFAZER, tudo, um dia:
        Disable-PSRemoting -Force
        Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' LocalAccountTokenFilterPolicy 0
        Remove-NetFirewallRule -DisplayName 'WinRM para a FIA (rede local)'

    USO
        botao direito no ABRIR O SERVIDOR PARA A FIA.bat
        -> Executar como administrador

        -Conta  <nome>   qual conta vai mandar (padrao: Eudson)
        -SoOlhar         mostra o que faria e nao mexe em nada
#>

param(
    [string]$Conta = 'Eudson',
    [switch]$SoOlhar
)

$ErrorActionPreference = 'Continue'

function Titulo($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }
function Ok($t)     { Write-Host "   [ok]    $t" -ForegroundColor Green }
function Aviso($t)  { Write-Host "   [olhe]  $t" -ForegroundColor Yellow }
function Dizer($t)  { Write-Host "   $t" }

# ----------------------------------------------------------- admin
$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Isto precisa ser aberto COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  So administrador mexe em conta, registro e firewall.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================'
Write-Host '   ABRIR O SERVIDOR PARA A FIA'
Write-Host ("   maquina: " + $env:COMPUTERNAME + "   conta: " + $Conta)
if ($SoOlhar) { Write-Host '   MODO OLHAR - nada sera mudado' -ForegroundColor Yellow }
Write-Host '  ============================================================'

# =========================================================== 1. a conta
Titulo '1. A conta que vai mandar'

$u = Get-LocalUser -Name $Conta -ErrorAction SilentlyContinue
if (-not $u) {
    Aviso "a conta '$Conta' NAO EXISTE nesta maquina."
    Dizer ''
    Dizer 'Em grupo de trabalho o Windows repassa sozinho o usuario e a'
    Dizer 'senha da maquina de origem. Entao o caminho mais simples e'
    Dizer "criar aqui uma conta com o MESMO nome e a MESMA senha da"
    Dizer 'maquina de onde a FIA roda.'
    Dizer ''
    if ($SoOlhar) {
        Dizer '(modo olhar: criaria a conta agora)'
    } else {
        $r = Read-Host "   Criar a conta '$Conta' agora? (S para criar)"
        if ($r -eq 'S') {
            $senha = Read-Host '   Senha para a conta nova' -AsSecureString
            try {
                New-LocalUser -Name $Conta -Password $senha -FullName "FIA - acesso remoto" `
                              -Description "Criada em $(Get-Date -Format dd/MM/yyyy) para a FIA administrar de longe" `
                              -PasswordNeverExpires -ErrorAction Stop | Out-Null
                Ok "conta '$Conta' criada"
                $u = Get-LocalUser -Name $Conta
            } catch {
                Aviso ("nao consegui criar: " + ($_.Exception.Message -replace '\s+',' '))
            }
        } else {
            Dizer 'Nao criei. Passe -Conta <nome> com uma conta que ja exista.'
        }
    }
} else {
    Ok "a conta '$Conta' existe"
}

if ($u) {
    $admins = (Get-LocalGroupMember -Group 'Administradores' -ErrorAction SilentlyContinue)
    if (-not $admins) {
        # O grupo muda de nome com o idioma do Windows. O SID nao muda.
        $admins = Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue
    }
    $jaEh = $admins | Where-Object { $_.Name -like "*\$Conta" -or $_.Name -eq $Conta }
    if ($jaEh) {
        Ok "'$Conta' JA esta no grupo de administradores"
    } elseif ($SoOlhar) {
        Dizer "(modo olhar: poria '$Conta' no grupo de administradores)"
    } else {
        try {
            Add-LocalGroupMember -SID 'S-1-5-32-544' -Member $Conta -ErrorAction Stop
            Ok "'$Conta' entrou no grupo de administradores"
        } catch {
            Aviso ("nao consegui por no grupo: " + ($_.Exception.Message -replace '\s+',' '))
        }
    }
}

# ================================================ 2. o token da rede
Titulo '2. A chave que faz a conta valer PELA REDE'

$chave = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
$atual = (Get-ItemProperty -Path $chave -Name LocalAccountTokenFilterPolicy -ErrorAction SilentlyContinue).LocalAccountTokenFilterPolicy
Dizer ("LocalAccountTokenFilterPolicy agora: " + $(if ($null -eq $atual) { '(nao existe - vale 0, rebaixado)' } else { $atual }))
if ($atual -eq 1) {
    Ok 'ja esta em 1 - conta local administradora vale inteira pela rede'
} elseif ($SoOlhar) {
    Dizer '(modo olhar: poria em 1)'
} else {
    try {
        New-ItemProperty -Path $chave -Name LocalAccountTokenFilterPolicy `
                         -Value 1 -PropertyType DWord -Force -ErrorAction Stop | Out-Null
        Ok 'posta em 1 - E ESTA E A CHAVE QUE FALTAVA'
    } catch {
        Aviso ("nao consegui escrever: " + ($_.Exception.Message -replace '\s+',' '))
    }
}

# ========================================================== 3. o WinRM
Titulo '3. O WinRM - por onde os comandos chegam'

$svc = Get-Service WinRM -ErrorAction SilentlyContinue
Dizer ("servico WinRM agora: " + $(if ($svc) { $svc.Status } else { 'nao existe' }))
if ($SoOlhar) {
    Dizer '(modo olhar: ligaria o WinRM e o deixaria em automatico)'
} else {
    try {
        # -SkipNetworkProfileCheck: em grupo de trabalho a rede costuma
        # estar marcada como Publica, e sem isto o Enable-PSRemoting
        # recusa. A regra de firewall que abrimos abaixo e que limita
        # quem alcanca - e ela e por sub-rede, nao pelo perfil.
        Enable-PSRemoting -Force -SkipNetworkProfileCheck -ErrorAction Stop | Out-Null
        Set-Service WinRM -StartupType Automatic
        Ok 'WinRM ligado e em automatico'
    } catch {
        Aviso ("Enable-PSRemoting reclamou: " + ($_.Exception.Message -replace '\s+',' '))
    }
}

# ======================================================= 4. o firewall
Titulo '4. Quem pode bater na porta'

$REGRA = 'WinRM para a FIA (rede local)'
if ($SoOlhar) {
    Dizer "(modo olhar: criaria a regra '$REGRA' so para a sub-rede local)"
} else {
    try {
        Get-NetFirewallRule -DisplayName $REGRA -ErrorAction SilentlyContinue |
            Remove-NetFirewallRule -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName $REGRA -Direction Inbound -Protocol TCP `
                            -LocalPort 5985 -RemoteAddress LocalSubnet `
                            -Action Allow -Profile Any -ErrorAction Stop | Out-Null
        Ok 'porta 5985 aberta SO para a rede local'
    } catch {
        Aviso ("nao consegui criar a regra: " + ($_.Exception.Message -replace '\s+',' '))
    }
}

# ========================================================= o resultado
Titulo 'Como ficou'

$svc = Get-Service WinRM -ErrorAction SilentlyContinue
$atual = (Get-ItemProperty -Path $chave -Name LocalAccountTokenFilterPolicy -ErrorAction SilentlyContinue).LocalAccountTokenFilterPolicy
$regra = Get-NetFirewallRule -DisplayName $REGRA -ErrorAction SilentlyContinue
$ouve  = @(netstat -an | Select-String ':5985\s' | Select-String 'LISTENING')

Dizer ("WinRM                          : " + $(if ($svc) { $svc.Status } else { '-' }))
Dizer ("LocalAccountTokenFilterPolicy  : " + $(if ($null -eq $atual) { '(nao existe)' } else { $atual }))
Dizer ("regra de firewall              : " + $(if ($regra) { 'existe, so rede local' } else { 'NAO existe' }))
Dizer ("alguem ouvindo na 5985         : " + $(if ($ouve.Count) { 'sim' } else { 'NAO' }))

Write-Host ''
if ($svc -and $svc.Status -eq 'Running' -and $atual -eq 1 -and $regra -and $ouve.Count) {
    Write-Host '   PRONTO. Agora, na maquina da FIA, rode o' -ForegroundColor Green
    Write-Host '   GUARDAR A SENHA DO SERVIDOR.bat' -ForegroundColor Green
} else {
    Write-Host '   FALTOU ALGUMA COISA - olhe as linhas marcadas [olhe] acima.' -ForegroundColor Yellow
}
Write-Host ''
Read-Host '  Enter para fechar'
