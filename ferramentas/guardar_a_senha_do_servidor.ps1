<#
    GUARDA A SENHA DO SERVIDOR, nesta maquina, cifrada.

    RODA NA MAQUINA DA FIA (nao no servidor). Uma vez so.

    ---------------------------------------------------------------
    ONDE A SENHA FICA, e por que ali

    Num arquivo em C:\Finart\_ctp_ia, que e a PASTA_CONTROLE - a mesma
    pasta onde ja moram o registro, a fila de OS e o resto do que e
    desta maquina e nao vai para o Git. E fora do repositorio de
    proposito: a armadilha 8 do GEREMPRE conta o que acontece quando
    senha vira arquivo versionado.

    O arquivo e escrito com Export-Clixml, que cifra a senha com o
    DPAPI do Windows. Isso quer dizer uma coisa concreta: o arquivo SO
    ABRE para o MESMO USUARIO, na MESMA MAQUINA. Copiado para outro
    computador ele nao serve para nada - nem para quem o roubar.

    A SENHA NAO PASSA POR MIM. Quem digita e voce, na janela do
    Windows; eu nunca vejo o valor, e ele nao entra em log, em commit
    nem em conversa. Se um dia eu pedir a senha escrita numa mensagem,
    desconfie - nao e assim que isto funciona.

    ---------------------------------------------------------------
    O TrustedHosts, e por que ele e preciso

    Grupo de trabalho nao tem Kerberos. Sem ele o PowerShell nao tem
    como provar que 'servidor' e mesmo o servidor, e entao ele RECUSA
    conectar - a menos que voce diga, uma vez, que confia naquele nome.
    E isso o TrustedHosts.

    Este script ACRESCENTA 'servidor' a lista, sem apagar o que ja
    estiver la, e NUNCA usa '*'. Confiar em todo mundo seria o mesmo
    que nao conferir nada.

    USO
        botao direito no GUARDAR A SENHA DO SERVIDOR.bat
        -> Executar como administrador

        (precisa de administrador so por causa do TrustedHosts, que e
        configuracao da maquina)
#>

param(
    [string]$Servidor = 'servidor',
    # Conta PROPRIA da FIA no servidor, criada pelo
    # abrir_o_servidor_para_a_fia. Nao e a conta de ninguem, e a senha
    # dela nao tem relacao com a de entrar em computador nenhum - o
    # WinRM manda usuario e senha na mao. Ver o comentario de la.
    [string]$Conta    = 'fia',
    [string]$Pasta    = 'C:\Finart\_ctp_ia'
)

$ErrorActionPreference = 'Continue'
$ARQUIVO = Join-Path $Pasta 'credencial_servidor.xml'

function Titulo($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }
function Ok($t)     { Write-Host "   [ok]    $t" -ForegroundColor Green }
function Aviso($t)  { Write-Host "   [olhe]  $t" -ForegroundColor Yellow }
function Dizer($t)  { Write-Host "   $t" }

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $souAdm) {
    Write-Host ''
    Write-Host '  PARE. Abra COMO ADMINISTRADOR.' -ForegroundColor Red
    Write-Host '  O TrustedHosts e configuracao da maquina, e so'
    Write-Host '  administrador a escreve.'
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================'
Write-Host '   GUARDAR A SENHA DO SERVIDOR'
Write-Host ("   servidor: $Servidor    conta: $Conta")
Write-Host '  ============================================================'

# ==================================================== 1. o WinRM daqui
Titulo '1. O WinRM desta maquina'

$svc = Get-Service WinRM -ErrorAction SilentlyContinue
if ($svc.Status -ne 'Running') {
    # Para SAIR daqui tambem e preciso o servico no ar - ele guarda a
    # configuracao do cliente, inclusive o TrustedHosts.
    try {
        Set-Service WinRM -StartupType Automatic
        Start-Service WinRM -ErrorAction Stop
        Ok 'WinRM local ligado (ele guarda a configuracao do cliente)'
    } catch {
        Aviso ("nao consegui subir o WinRM local: " + ($_.Exception.Message -replace '\s+',' '))
    }
} else {
    Ok 'WinRM local ja esta no ar'
}

# ================================================= 2. o TrustedHosts
Titulo '2. Dizer que confiamos neste servidor'

$cam = 'WSMan:\localhost\Client\TrustedHosts'
try {
    $antes = (Get-Item $cam -ErrorAction Stop).Value
} catch { $antes = '' }
Dizer ("TrustedHosts agora: " + $(if ($antes) { $antes } else { '(vazio)' }))

if ($antes -eq '*') {
    Aviso 'esta em "*" - confia em QUALQUER maquina. Nao mexi, mas olhe isso.'
} else {
    $lista = @()
    if ($antes) { $lista = $antes -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
    if ($lista -contains $Servidor) {
        Ok "'$Servidor' ja esta na lista"
    } else {
        $lista += $Servidor
        try {
            Set-Item $cam -Value ($lista -join ',') -Force -ErrorAction Stop
            Ok ("'$Servidor' acrescentado - lista agora: " + ($lista -join ','))
        } catch {
            Aviso ("nao consegui escrever o TrustedHosts: " + ($_.Exception.Message -replace '\s+',' '))
        }
    }
}

# ====================================================== 3. a senha
Titulo '3. A senha'

if (Test-Path $ARQUIVO) {
    Dizer "ja existe uma credencial guardada em $ARQUIVO"
    $r = Read-Host '   Trocar por uma nova? (S para trocar, Enter para manter)'
    if ($r -ne 'S') { Dizer 'mantive a que estava' }
    else { Remove-Item $ARQUIVO -Force -ErrorAction SilentlyContinue }
}

if (-not (Test-Path $ARQUIVO)) {
    if (-not (Test-Path $Pasta)) { New-Item -ItemType Directory -Path $Pasta -Force | Out-Null }
    Dizer ''
    Dizer 'Vai abrir a janela do Windows pedindo a senha.'
    Dizer "O usuario ja vem preenchido como  $Servidor\$Conta  - deixe assim."
    Dizer ''
    Dizer "A senha e a que voce ACABOU DE CRIAR para a conta '$Conta' no"
    Dizer 'servidor. Nao e a sua senha de entrar no Windows - a conta da'
    Dizer 'FIA e dela, e a senha dela tambem.'
    Dizer ''
    $cred = Get-Credential -UserName "$Servidor\$Conta" -Message "Senha da conta $Conta no $Servidor"
    if (-not $cred) {
        Aviso 'nada foi digitado - parei aqui'
        Read-Host '  Enter para fechar'
        exit 1
    }
    try {
        # Export-Clixml cifra com DPAPI: so abre para este usuario,
        # nesta maquina. Copiado para outro PC nao serve para nada.
        $cred | Export-Clixml -Path $ARQUIVO -Force -ErrorAction Stop
        Ok "guardada cifrada em $ARQUIVO"
    } catch {
        Aviso ("nao consegui guardar: " + ($_.Exception.Message -replace '\s+',' '))
        Read-Host '  Enter para fechar'
        exit 1
    }
}

# ======================================================= 4. provar
Titulo '4. Provar que funciona'

try {
    $cred = Import-Clixml -Path $ARQUIVO -ErrorAction Stop
    $r = Invoke-Command -ComputerName $Servidor -Credential $cred -ErrorAction Stop -ScriptBlock {
        [pscustomobject]@{
            Maquina  = $env:COMPUTERNAME
            Usuario  = "$env:USERDOMAIN\$env:USERNAME"
            Admin    = (New-Object Security.Principal.WindowsPrincipal(
                          [Security.Principal.WindowsIdentity]::GetCurrent())
                        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
            Firebird = (Get-Service FirebirdServerDefaultInstance -ErrorAction SilentlyContinue).Status
            Banco    = $(if (Test-Path 'C:\NeoGerempre\bdados\neobdados.fdb') {
                            [math]::Round((Get-Item 'C:\NeoGerempre\bdados\neobdados.fdb').Length/1MB,1).ToString() + ' MB'
                         } else { 'nao achei' })
            Gstat    = (Test-Path 'C:\Firebird_1_5\bin\gstat.exe')
        }
    }
    Write-Host ''
    Ok 'CONECTOU NO SERVIDOR'
    Dizer ("   maquina la : " + $r.Maquina)
    Dizer ("   entrei como: " + $r.Usuario)
    Dizer ("   sou admin? : " + $r.Admin)
    Dizer ("   Firebird   : " + $r.Firebird)
    Dizer ("   banco      : " + $r.Banco)
    Dizer ("   gstat la?  : " + $r.Gstat)
    Write-Host ''
    if ($r.Admin) {
        Write-Host '   PRONTO DE VERDADE. A FIA ja alcanca o servidor daqui.' -ForegroundColor Green
    } else {
        Write-Host '   CONECTOU MAS NAO COMO ADMINISTRADOR.' -ForegroundColor Yellow
        Write-Host '   E a chave LocalAccountTokenFilterPolicy - rode no servidor'
        Write-Host '   o ABRIR O SERVIDOR PARA A FIA.bat antes deste.'
    }
} catch {
    Write-Host ''
    Aviso ("nao conectou: " + ($_.Exception.Message -replace '\s+',' '))
    Dizer ''
    Dizer 'O que conferir, nesta ordem:'
    Dizer '  1. rodou o ABRIR O SERVIDOR PARA A FIA.bat no SERVIDOR, como admin?'
    Dizer '  2. a senha digitada e a da conta NO SERVIDOR (nao a daqui)?'
    Dizer '  3. a porta 5985 do servidor responde? Test-NetConnection servidor -Port 5985'
}

Write-Host ''
Read-Host '  Enter para fechar'
