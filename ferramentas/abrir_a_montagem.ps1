<#
    ABRE A TELA DA FILA DA MONTAGEM DA AMERICA.

    Pedido do operador em 18/09/2026: "crie um atalho pra que eu possa
    dar dois cliques e ja abrir a tela da montagem".

    O QUE ELE FAZ, e a ordem importa:

    1. PERGUNTA SE A FILA JA ESTA NO AR. Ela sobe sozinha com o VS Code
       (a tarefa "Iniciar montagem AMERICA"), entao na maior parte das
       vezes ja esta - e ai este arquivo so abre o navegador e sai.

    2. SO SUBINDO SE PRECISAR. Abrir uma segunda nao estragaria nada -
       quem segura e a porta, e o servidor sai avisando -, mas deixaria
       uma janela de erro aberta na cara de quem so queria ver a fila.

    3. ESPERA A PORTA RESPONDER ANTES DE ABRIR O NAVEGADOR. Subir leva
       um par de segundos; abrindo antes, o navegador mostra "nao foi
       possivel acessar" e a pessoa conclui que o sistema esta quebrado.
       Ele tenta por ate 30 segundos e, nao subindo, DIZ o que houve em
       vez de abrir uma aba morta.

    NAO PRECISA DE ADMINISTRADOR. Este arquivo nao mexe em firewall nem
    em servico - so olha uma porta e abre um navegador.

    NAS OUTRAS MAQUINAS NAO SE USA ESTE, e sim o atalho de internet que
    aponta para http://EUDSON-PC:8787/ - la nao ha nada para subir, a
    fila mora aqui. Ver 'FILA DA MONTAGEM (AMERICA).url'.
#>

$ErrorActionPreference = 'Stop'

$PORTA    = 8787
$ENDERECO = "http://localhost:$PORTA/"
$RAIZ     = Split-Path -Parent $PSScriptRoot
$SUBIR    = Join-Path $RAIZ 'iniciar_montagem.bat'

function NoAr {
    # A PORTA, e nao o processo: o que interessa e se ALGUEM atende - e
    # procurar por 'python.exe' acharia o vigia, que e outro programa.
    return [bool](Get-NetTCPConnection -LocalPort $PORTA -State Listen `
                                       -ErrorAction SilentlyContinue)
}

if (NoAr) {
    Start-Process $ENDERECO
    exit 0
}

Write-Host ''
Write-Host '  A fila da montagem nao estava no ar. Subindo...'
Write-Host ''

if (-not (Test-Path $SUBIR)) {
    Write-Host "  PARE. Nao achei o $SUBIR" -ForegroundColor Red
    Write-Host '  A pasta do projeto foi movida? Este atalho aponta para'
    Write-Host "  $RAIZ"
    Write-Host ''
    Read-Host '  Enter para fechar'
    exit 1
}

Start-Process -FilePath $SUBIR -WindowStyle Minimized

for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1
    if (NoAr) {
        Start-Process $ENDERECO
        exit 0
    }
}

Write-Host '  NAO subiu em 30 segundos.' -ForegroundColor Red
Write-Host ''
Write-Host '  Abra a janela que apareceu minimizada na barra de tarefas -'
Write-Host '  ela diz o que houve. O motivo mais comum e a porta ja estar'
Write-Host "  ocupada por outro programa."
Write-Host ''
Read-Host '  Enter para fechar'
exit 1
