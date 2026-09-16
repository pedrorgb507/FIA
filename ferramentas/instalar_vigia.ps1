<#
    INSTALA A TAREFA DO VIGIA DO FIREBIRD.

    Existe porque a linha de schtasks digitada a mao e uma fonte de erro
    por si so: o ^ de quebra vale no Prompt de Comando e quebra no
    PowerShell, e foi assim que a instalacao falhou calada em 16/09/2026.
    Aqui nao ha o que digitar errado.

    E usa o schtasks, e nao o Register-ScheduledTask, por outra razao
    aprendida no mesmo dia: pedir repeticao "para sempre" pelo
    Register-ScheduledTask exige uma RepetitionDuration, e
    [TimeSpan]::MaxValue vira P99999999DT23H59M59S, que o Agendador
    recusa com "valor formatado incorretamente ou fora do intervalo".
    O schtasks tem /SC MINUTE, que ja quer dizer para sempre.

    O caminho do vigia NAO TEM ESPACOS de proposito - assim o /TR
    dispensa aspas dentro de aspas, que e a outra armadilha classica.

    COMO RODAR
      botao direito neste arquivo -> "Executar com o PowerShell"

    ou, num PowerShell ABERTO COMO ADMINISTRADOR:
      powershell -ExecutionPolicy Bypass -File C:\Finart\_rotina\instalar_vigia.ps1
#>

$ErrorActionPreference = 'Stop'
$VIGIA = 'C:\Finart\_rotina\vigia_firebird.ps1'
$NOME  = 'Vigia GEREMPRE'

$souAdm = (New-Object Security.Principal.WindowsPrincipal(
            [Security.Principal.WindowsIdentity]::GetCurrent())
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host ''
if (-not $souAdm) {
    Write-Host 'PAREI: esta janela NAO esta como administrador.' -ForegroundColor Red
    Write-Host 'A tarefa roda como SISTEMA para poder reiniciar o servico,'
    Write-Host 'e so um administrador pode cria-la assim.'
    Write-Host ''
    Write-Host 'Abra o PowerShell com o botao direito -> "Executar como'
    Write-Host 'administrador" e rode:'
    Write-Host ''
    Write-Host "   powershell -ExecutionPolicy Bypass -File $VIGIA".Replace($VIGIA, $PSCommandPath) -ForegroundColor Yellow
    Write-Host ''
    Read-Host 'Enter para fechar'
    exit 1
}

if (-not (Test-Path $VIGIA)) {
    Write-Host "PAREI: nao achei $VIGIA" -ForegroundColor Red
    Read-Host 'Enter para fechar'
    exit 1
}
if ($VIGIA -match '\s') {
    Write-Host "PAREI: o caminho do vigia tem espaco - ajuste o /TR antes." -ForegroundColor Red
    Read-Host 'Enter para fechar'
    exit 1
}

$comando = "powershell -NoProfile -ExecutionPolicy Bypass -File $VIGIA"
$argumentos = @(
    '/Create', '/TN', $NOME,
    '/SC', 'MINUTE', '/MO', '1',
    '/RU', 'SYSTEM', '/RL', 'HIGHEST',
    '/F',
    '/TR', $comando
)

Write-Host 'Criando a tarefa...'
$saida = & schtasks.exe @argumentos 2>&1
$saida | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host "O schtasks saiu com codigo $LASTEXITCODE - a tarefa NAO foi criada." -ForegroundColor Red
    Read-Host 'Enter para fechar'
    exit 1
}

$t = Get-ScheduledTask -TaskName $NOME -ErrorAction SilentlyContinue
if (-not $t) {
    Write-Host 'Estranho: o schtasks disse que criou, mas nao encontro a tarefa.' -ForegroundColor Red
    Read-Host 'Enter para fechar'
    exit 1
}
Write-Host ''
Write-Host 'TAREFA CRIADA' -ForegroundColor Green
Write-Host ("  nome    : {0}" -f $t.TaskName)
Write-Host ("  usuario : {0}" -f $t.Principal.UserId)
Write-Host ("  nivel   : {0}" -f $t.Principal.RunLevel)

Write-Host ''
Write-Host 'Rodando uma vez agora, para conferir...'
Start-ScheduledTask -TaskName $NOME
Start-Sleep -Seconds 12
$i = Get-ScheduledTaskInfo -TaskName $NOME
Write-Host ("  ultima execucao: {0}   resultado: {1}" -f $i.LastRunTime, $i.LastTaskResult)
Write-Host ''
Write-Host 'Resultado 0 = passou. O log fica em C:\Finart\_rotina\vigia.log'
Write-Host '(com o banco no ar ele nao escreve nada - silencio e boa noticia)'
Write-Host ''
Read-Host 'Enter para fechar'
