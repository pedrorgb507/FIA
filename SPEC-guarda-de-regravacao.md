# A guarda que falta: arte que volta e vira chapa de novo

> Status: pronto para implementar. Sem rastreador de issues configurado
> neste projeto — quando houver, este documento vira uma issue com a label
> `ready-for-agent`.

## O problema

Quando um arquivo que **já virou chapa** reaparece na pasta do dia, o
programa grava tudo de novo: chapa nova no CTP, OS nova no GEREMPRE de
produção com baixa de chapa no estoque de verdade, e prova impressa na
Konica. Ninguém avisa. O operador só descobre olhando o CTP e achando dois
arquivos iguais, ou o estoque no fim do mês.

Existe uma proteção, o `mesmo_trabalho_ja_feito`, e ela funciona — mas só
para metade do registro. Ela compara o **conteúdo** do arquivo com o
retrato guardado na entrada antiga (`impressao`). Entradas gravadas antes
desse recurso não têm retrato, e para elas a proteção simplesmente não age:
sem candidata, devolve `None`, e o arquivo passa a valer como novo.

Medido em 09/09/2026: **87 das 156 entradas do registro não têm impressão
digital.** Mais da metade do histórico está desprotegida.

Isso já mordeu, e mordeu duas vezes:

- **08/09/2026** — `49694 - Gaspar - colinha.pdf` foi regravado na pasta
  sem mudar. Às 08:36:18 começou a primeira chapa, às 08:37:16 a segunda. O
  CTP ficou com `49694.pdf` e `49694_v2.pdf` idênticas byte a byte, 12,4 MB
  cada. A diferença entre as duas chaves eram **12 segundos de data**. Foi
  esse caso que fez nascer o `mesmo_trabalho_ja_feito`;
- **09/09/2026** — `49695 - Radio Dente - pasta.pdf`, que já saíra como
  `49695.pdf` em 08/09, voltou pela ponte do Teams. A simulação mostrou que
  o `mesmo_trabalho_ja_feito` **não o reconheceria**: a entrada dele é uma
  das 87 sem retrato. A chapa teria saído de novo. Foi barrado à mão, no
  registro da ponte, antes de atravessar.

A ponte do Teams não criou o defeito — ela o tornou provável. Antes, para
uma arte antiga voltar à pasta do dia alguém tinha de arrastá-la para lá. A
caixa do canal guarda tudo que o cliente já mandou, para sempre.

## A solução

Quando o programa **não consegue saber** se aquela arte já virou chapa, ele
para e pergunta, em vez de chutar.

Nome e tamanho iguais aos de um trabalho já feito, sem retrato para
confirmar, é exatamente a situação em que as duas respostas erram: tratar
como "já feito" arrisca **chapa faltando**; tratar como novo arrisca
**chapa duplicada**. A regra da casa já responde isso — *o que sai do
padrão vira pendência em vez de chute*.

Então a resposta passa a ser uma terceira: **não sei dizer**. E "não sei
dizer" vira pendência, com o número da chapa que saiu antes e a data, para
o operador decidir em dois segundos olhando.

Nada disso muda o caminho normal. Arte nova continua virando chapa sem
ninguém no meio; arte reconhecidamente igual continua sendo pulada em
silêncio, como hoje.

## Histórias de usuário

1. Como operador do CTP, quero que o programa **não grave chapa** de um
   serviço que já foi feito, para não gastar chapa de metal à toa.
2. Como operador do CTP, quero que o programa **não abra OS** de um serviço
   já lançado, para o estoque no GEREMPRE não baixar duas vezes pela mesma
   coisa.
3. Como operador do CTP, quero que o programa **não imprima prova** de um
   serviço já feito, para não gastar papel e tinta da Konica sem motivo.
4. Como operador do CTP, quero que o programa **me avise quando não souber**
   se a arte já foi feita, para eu decidir em vez de descobrir depois.
5. Como operador do CTP, quero que o aviso diga **qual chapa saiu antes e
   quando**, para eu conferir sem ter de abrir o registro à mão.
6. Como operador do CTP, quero que o aviso diga **de qual cliente** é o
   arquivo, para eu saber a quem responder.
7. Como operador do CTP, quero que arte **genuinamente nova** continue
   virando chapa sozinha, para a automação não virar fila de aprovação.
8. Como operador do CTP, quero que arte **reconhecidamente igual** continue
   sendo pulada em silêncio, para o log não encher de aviso repetido.
9. Como operador do CTP, quero que arte **corrigida e regravada** com o
   mesmo nome continue virando chapa nova, porque ela É trabalho novo.
10. Como operador do CTP, quero que o arquivo incerto **fique na pasta**
    esperando minha decisão, para eu não ter de pedir ao cliente de novo.
11. Como operador do CTP, quero que, depois de eu resolver a pendência, o
    arquivo **não fique voltando** a cada varredura, para o aviso não virar
    ruído que eu aprendo a ignorar.
12. Como operador do CTP, quero que a guarda proteja **também o que eu
    salvo à mão**, porque foi assim que o Gaspar saiu duplicado.
13. Como operador do CTP, quero que a guarda proteja **o que chega pela
    ponte do Teams**, porque a caixa do canal guarda tudo para sempre.
14. Como operador do CTP, quero que trabalhos **de clientes diferentes**
    com o mesmo nome de arquivo não sejam confundidos entre si.
15. Como operador do CTP, quero que a guarda **não custe leitura de disco**
    a cada varredura, porque a pasta é de rede e a varredura passa a cada 5
    segundos.
16. Como operador do CTP, quero que arte nova cujo nome e tamanho batam
    **por coincidência** com um trabalho antigo vire pendência, e não chapa
    silenciosamente perdida.
17. Como quem cuida do programa, quero que entradas **novas** do registro
    continuem ganhando retrato, para o problema não crescer.
18. Como quem cuida do programa, quero que a mudança de contrato do
    `mesmo_trabalho_ja_feito` **quebre um teste** se alguém a desfizer sem
    perceber.
19. Como quem cuida do programa, quero poder **remover a trava manual** que
    barra hoje o Radio Dente no registro da ponte, quando esta guarda
    existir.
20. Como operador do CTP, quero que a guarda funcione mesmo com o GEREMPRE
    fora do ar, porque a chapa não para por causa disso.

## Decisões de implementação

**O contrato do `mesmo_trabalho_ja_feito` passa de dois estados para três.**
Hoje ele devolve a entrada do registro (é a mesma arte) ou `None` (não é, ou
não dá para saber — as duas coisas confundidas numa resposta só). Passa a
distinguir:

- **igual** — há retrato e ele bate. Comportamento de hoje: pula, anota a
  chave nova apontando para as chapas que já existem;
- **não sei dizer** — nome e tamanho batem com uma entrada **sem** retrato.
  Novo. Vira pendência, e o arquivo **não é processado**;
- **não é** — nada bate, ou há retrato e ele não bate. Comportamento de
  hoje: processa normalmente.

A forma exata do retorno fica a critério de quem implementar, desde que os
três estados sejam distinguíveis sem comparar texto solto. O padrão da casa
para isso já existe em `preflight`, onde a mensagem é **escrita e
reconhecida a partir da mesma constante**, com teste que cai se alguém
reescrever o texto sem mexer nela.

**O `monitor.varrer` é quem transforma "não sei dizer" em pendência.** A
decisão de parar é dele, não do `utils`: `utils` responde o que sabe,
`monitor` decide o que fazer. A pendência nomeia o cliente (o parâmetro já
existe) e traz o número da chapa anterior e a data, tirados da entrada
antiga (`saidas` e `quando`).

**O arquivo incerto não entra no registro.** Se entrasse, seria dado como
resolvido e nunca mais apareceria. Ele fica na pasta, e a pendência é
anotada **uma vez por arquivo** enquanto o programa estiver de pé — o mesmo
tratamento que `avisar_arquivo_parado` e `avisar_arquivo_estranho` já dão.

**A comparação continua barata.** Como hoje, só abre o arquivo quando há
motivo — nome e tamanho iguais. A diferença é que agora a ausência de
retrato na candidata deixa de descartá-la em silêncio e passa a ser o
próprio sinal de incerteza.

**A ponte do Teams não muda.** Ela entrega na pasta do dia e o monitor
decide. Foi assim que o desenho foi feito e a separação continua valendo.

**O cliente da entrada antiga é levado em conta.** O registro já grava
`cliente`. Nome e tamanho iguais em clientes diferentes não são o mesmo
trabalho e não devem gerar incerteza entre si.

**As 87 entradas sem retrato não são preenchidas retroativamente.** Ver
"Fora de escopo".

## Decisões de teste

**O que é um bom teste aqui:** ele descreve o que o operador vê acontecer —
saiu chapa, não saiu chapa, apareceu pendência —, e não como a função
devolve. Um teste que casa com o texto exato da mensagem, ou que espia a
forma do retorno, quebra no primeiro conserto e não protege nada.

**A costura é `monitor.varrer`.** É o ponto mais alto onde o comportamento
inteiro aparece: entra um arquivo e uma lista do que já foi feito, sai
chapa ou pendência. Já existe e já é usada assim nos testes de hoje. O
`mesmo_trabalho_ja_feito` ganha testes de unidade para os três estados,
porque o contrato dele é a parte que pode ser desfeita sem ninguém notar.

**Casos a cobrir:**

- entrada sem retorno, nome e tamanho iguais → **pendência, e nada de
  chapa**. É o caso do Radio Dente;
- entrada com retrato que bate → pulado em silêncio, como hoje;
- entrada com retrato que **não** bate (arte corrigida, mesmo tamanho) →
  vira chapa nova, como hoje. É o que `test_arte_corrigida_de_verdade_e_refeita`
  já cobre, e não pode regredir;
- entrada com retrato que bate, data nova → pulado, como hoje. É o que
  `test_a_mesma_arte_com_data_nova_nao_e_refeita` já cobre;
- nenhuma entrada parecida → vira chapa, como hoje;
- mesma incerteza vista duas vezes na mesma sessão → **uma** pendência;
- nome e tamanho iguais, **clientes diferentes** → não é incerteza;
- arquivo incerto não entra no registro.

**Arte prévia no repositório:** `test_registro.py` é o vizinho direto e o
modelo a seguir — ele já monta registro à mão, adianta a data com
`os.utime` e chama `varrer` com dublês para `processar`, `log` e
`anotar_pendencia`. Os testes da ponte (`test_entrada_teams.py`) mostram o
padrão de asserção sobre pendência lida do arquivo, em vez de sobre a
chamada.

**Um teste existente muda de lado, e isso é o ponto.**
`test_registro_antigo_sem_impressao_nao_quebra` afirma hoje que entrada sem
retrato devolve `None`. Ele codifica exatamente o contrato que este spec
troca. Deve ser **reescrito**, não apagado: passa a afirmar que aquela
mesma situação agora produz incerteza. Quem implementar precisa entender
que a falha desse teste é o sinal de que acertou, e não de que quebrou.

**O `conftest.py` já garante** que nenhum teste fala com o GEREMPRE de
verdade. Nada aqui deve afrouxar isso.

## Fora de escopo

- **Preencher retroativamente as 87 entradas sem retrato.** Os arquivos de
  origem ainda existem no `V:`, então em tese daria — mas é uma varredura
  de rede sobre meses de pasta, com risco de casar arquivo errado, para
  resolver um problema que esta guarda já cobre com segurança. Se um dia
  valer a pena, é trabalho separado e com decisão própria.
- **Qualquer mudança na ponte do Teams.** Ela entrega e sai.
- **Avisar o cliente.** Decidido nesta mesma conversa: a ponte não fala com
  quem manda o arquivo.
- **Mexer no caminho de chapa, OS ou prova.** A guarda decide se o caminho
  roda, não o que ele faz.
- **Limpeza automática de arquivo antigo** em qualquer pasta.

## Notas

O número — 87 de 156 — foi medido em 09/09/2026 e só cresce para o lado
bom: toda entrada nova ganha retrato. A guarda envelhece junto, e um dia
não terá mais o que fazer. Não é motivo para adiá-la: são meses de
histórico desprotegido até lá, e cada um deles é uma chapa de metal.

Existe hoje uma **trava manual** no registro da ponte
(`_trazidos_do_teams.json`) barrando o `49695 - Radio Dente - pasta.pdf`,
com o motivo escrito por extenso na própria entrada. Ela foi posta em
09/09/2026 para impedir exatamente o acidente que este spec resolve.
Quando a guarda existir, a trava pode sair — e o arquivo passa a ser
barrado pelo motivo certo, e não por uma exceção escrita à mão.
