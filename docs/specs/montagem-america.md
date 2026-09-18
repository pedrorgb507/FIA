# A montagem da AMÉRICA sem depender de uma pessoa só

Spec sintetizada da conversa de 18/09/2026, em três rodadas de entrevista
com o operador. Todas as decisões abaixo foram confirmadas por ele.

## Problem Statement

A AMÉRICA manda os arquivos pelo WhatsApp, e em cada mensagem já diz a
montagem que quer: o formato, a máquina, quantas exposições. O arquivo
chega **por montar** — é matéria-prima, não serviço pronto —, e montar é
decisão: quem escolhe chapa, arranjo e vão precisa saber a regra da casa.

Hoje só uma pessoa sabe. O operador lê o WhatsApp, decide a montagem e
passa os parâmetros à FIA. Enquanto ele não faz isso, o serviço não anda.
A equipe não consegue dar andamento sozinha, e ele virou o gargalo do
cliente inteiro.

Existe um painel que desenha a chapa e confere a montagem, mas ele é uma
página solta: não lê o arquivo que chegou, não sabe o que já está
esperando, e o botão dele só gera um texto para alguém copiar. Quem
monta de verdade continua sendo quem conhece a regra.

O resultado é que a informação que a AMÉRICA já mandou pronta — formato,
máquina, exposições — morre numa conversa de WhatsApp que só uma pessoa
lê.

## Solution

Um sistema que a equipe inteira usa, no navegador, para levar um arquivo
da chegada até a montagem gravada, sem consultar ninguém.

O arquivo entra num portão novo, a `PARA MONTAR`, irmão da `PARA CTP` que
a casa já conhece. O sistema o mede sozinho: tamanho, se tem sangria, se
é colorido, quantas páginas, se tem marca de corte. Com isso ele já
sugere a máquina pela regra da casa.

Quem for montar abre a fila no navegador e vê o que está esperando, já
medido. Escolhe um, cai no painel de montagem — o mesmo de hoje, agora
servido e com os campos já preenchidos pelo que se mediu. Digita o que
veio do WhatsApp, vê o desenho responder a cada campo, e manda montar.

A FIA monta de verdade e grava a montagem na pasta do dia. Alguém da
equipe revisa e move para a `PARA CTP` — e daí em diante é o fluxo que já
existe: OS, prova, chapa no CTP.

Fica gravado quem aprovou cada montagem, quem trocou a máquina fora da
regra e quem liberou uma montagem que não cabia. O operador vê isso numa
tela de histórico, quando escolher olhar, em vez de ser interrompido.

## User Stories

1. Como montador da equipe, quero ver numa tela tudo o que está
   esperando montagem, para saber o que fazer sem perguntar a ninguém.
2. Como montador, quero que o arquivo já chegue medido na fila, para não
   precisar abrir o PDF e conferir o tamanho na mão.
3. Como montador, quero saber se o arquivo já veio sangrado, para não
   montar como se tivesse sangria o que não tem.
4. Como montador, quero ser avisado quando as duas leituras de sangria
   discordarem, porque arquivo que declara uma coisa e mostra outra é o
   que engana.
5. Como montador, quero ver se o arquivo é colorido ou preto-e-branco,
   porque é isso que decide entre a SM 74 e a MOZP.
6. Como montador, quero que o sistema sugira a máquina pela regra da
   casa, para aprender a regra usando o sistema.
7. Como montador, quero poder trocar a máquina que o sistema sugeriu,
   porque o operador disse "geralmente" e quem manda é a mensagem da
   AMÉRICA.
8. Como montador, quero ver quantas páginas o arquivo tem antes de
   montar, para não descobrir depois que era frente e verso.
9. Como montador, quero saber se o arquivo tem marca de corte, porque sem
   ela a montagem não sabe que lado é o pé.
10. Como montador, quero digitar o que a AMÉRICA mandou no WhatsApp —
    formato, máquina, exposições — em campos claros, para não ter que
    interpretar a mensagem duas vezes.
11. Como montador, quero ver a chapa desenhada em escala enquanto digito,
    para conferir a montagem antes de existir arquivo.
12. Como montador, quero ser avisado quando a montagem não couber na área
    útil da chapa, para não gravar chapa que não serve.
13. Como montador, quero ser avisado quando a montagem não couber no
    formato da folha, porque é um limite diferente do da chapa e é fácil
    confundir os dois.
14. Como montador, quero poder liberar uma montagem que não cabe quando
    eu souber o que estou fazendo, para o serviço não parar.
15. Como montador, quero que a liberação fique registrada no meu nome,
    para quem receber o papel saber que foi decisão de alguém.
16. Como montador, quero que o botão de montar realmente monte, em vez de
    gerar um texto para alguém copiar, para o trabalho terminar comigo.
17. Como montador, quero que a montagem saia na pasta do dia com o
    sufixo `_MONTAGEM`, para ela ficar amarrada ao arquivo que a gerou.
18. Como montador, quero que a marca de corte assente na pinça da chapa,
    porque é assim que a casa mede pinça e foi o que custou uma chapa
    fora do lugar antes.
19. Como montador, quero que o sistema confira a pinça no arquivo que
    saiu, e não só na conta que fez, para não mandar para o CTP o que não
    se conferiu.
20. Como montador, quero que o sistema pare e me pergunte quando a arte
    só couber deitada, porque girar errado põe a arte de cabeça para
    baixo na máquina.
21. Como montador, quero que o sistema pare quando a arte não couber em
    chapa nenhuma, em vez de escolher qualquer coisa.
22. Como revisor da equipe, quero revisar a montagem e movê-la para a
    `PARA CTP` eu mesmo, para o serviço não esperar uma pessoa
    específica.
23. Como revisor, quero que meu nome fique gravado na aprovação, porque
    quando sair chapa errada saber quem viu é como a regra nasce.
24. Como membro da equipe, quero usar o sistema do meu próprio PC, para
    não ter que disputar a máquina da FIA.
25. Como operador, quero uma tela de histórico que eu abro quando quiser,
    para ver o que a equipe decidiu sem ser interrompido.
26. Como operador, quero ver no histórico quem trocou máquina fora da
    regra, porque é daí que sai a próxima regra da casa.
27. Como operador, quero ver no histórico o que foi liberado sem caber,
    para entender que tipo de caso a regra ainda não cobre.
28. Como operador, quero que o `PARA MONTAR` esvazie quando a montagem é
    gravada, para o portão continuar sendo a lista do que falta.
29. Como operador, quero que o arquivo original não seja apagado, porque
    ele é a fonte da montagem.
30. Como operador, quero que o portão nunca fique com dois PDFs do mesmo
    serviço, porque a volta seguinte do vigia acharia duas chapas — duas
    gravações e duas OS.
31. Como operador, quero que o sistema aceite `.cdr`, porque a AMÉRICA
    manda, e o caminho de publicar pela Corel já existe.
32. Como operador, quero que arquivo de várias páginas seja mostrado e
    perguntado, e não adivinhado, porque a gravadora não puxa múltiplas
    páginas.
33. Como operador, quero que o sistema nunca mova nada para a `PARA CTP`
    sozinho, porque a mudança de pasta *é* a aprovação.
34. Como operador, quero que a tabela de formatos venha de um lugar só,
    para a tela e o vigia nunca decidirem coisas diferentes.
35. Como operador, quero que o sistema use a mesma regra de máquina que a
    FIA já usa, para não haver duas verdades na casa.
36. Como operador, quero que o servidor da montagem cair não derrube o
    vigia dos outros clientes.
37. Como operador, quero que o sistema espere o arquivo terminar de
    chegar antes de medi-lo, porque ler pela metade daria montagem
    errada.
38. Como operador, quero que o sistema não refaça montagem que já fez,
    para não duplicar trabalho nem arquivo.
39. Como dono do processo, quero que a informação que a AMÉRICA manda no
    WhatsApp entre no sistema digitada por gente, por enquanto, porque
    interpretar texto livre errado vira chapa errada.
40. Como dono do processo, quero que o sistema seja preparado para, mais
    tarde, sugerir a partir da mensagem do WhatsApp com a pessoa
    confirmando.

## Implementation Decisions

**A tela vira um servidor local, e não uma página solta.** É a decisão
que sustenta todas as outras. Enquanto foi página solta, o painel não
conseguia ler arquivo, não sabia o que estava esperando, e precisava de
uma cópia da tabela de formatos em JavaScript. Com servidor, a tabela
passa a ser servida do `config` de verdade, e a cópia morre.

**Um módulo novo guarda a lógica; a camada HTTP é casca fina.** Fila,
medição, sugestão, execução da ordem e registro vivem no módulo. O
servidor só traduz requisição em chamada. Nada de regra mora no HTTP.

**A ordem de montagem é o contrato.** Tudo que a tela coleta vira um
objeto único, e uma função recebe esse objeto e faz o trabalho. Foi essa
escolha que permitiu ter um seam só. A forma da ordem, que codifica as
decisões melhor que a prosa:

```
ordem = {
  arquivo, chapa, maquina,
  imagens_frente, imagens_verso,
  colunas, linhas, vao, sangria,
  formato,                      # a folha; limite diferente do da chapa
  tipo,                         # frente-verso, bate-vira, só frente
  quem,                         # quem está montando
  maquina_trocada,              # se saiu da regra, e por quê
  liberado_sem_caber,           # se foi forçado, e por quem
}
```

**Um portão novo, a `PARA MONTAR`, irmão da `PARA CTP`.** Hoje a pasta do
dia acumula três coisas: o que chegou por montar, a montagem gravada e as
cópias que sobem do portão. Com uma pessoa só isso dava; com a equipe,
vira "qual desses é o que falta?". O portão novo se lê sozinho: o que
está lá é o que falta.

**O sistema mede cinco coisas na entrada:** tamanho, sangria, cor, número
de páginas e presença de marca de corte. A cor não é luxo — a regra de
máquina que o operador ditou depende dela: até o formato 4 vai na PM 52;
acima, colorido vai na SM 74 e preto-e-branco na MOZP.

**A sangria é lida por dois caminhos, e a divergência é dita.** Um é a
TrimBox declarada no arquivo; o outro é tinta além da marca de corte.
Muitos arquivos não trazem TrimBox, e a tinta custa rasterizar — cada um
cobre o buraco do outro. Quando discordarem, o sistema fala, em vez de
escolher um e calar.

**A regra da máquina sugere, não decide.** O operador disse "geralmente",
e quem manda é a mensagem da AMÉRICA. O sistema propõe pela regra, a
pessoa confirma ou troca, e a troca fica registrada.

**O botão monta de verdade.** Chama o caminho de montagem que a FIA já
tem: assenta a arte na chapa, centrada, com a marca de corte na pinça —
ou pela borda do arquivo quando não houver marca reconhecível. Depois
mede a pinça **no arquivo que saiu**, porque entre escrever a matriz no
PDF e ela valer há um programa inteiro.

**A montagem sai na pasta do dia, nunca na `PARA CTP`.** Escrever no
portão pularia a revisão, e a mudança de pasta *é* o "aprovado". Isso
continua sendo trava, não promessa.

**A revisão continua humana, mas deixa de ser de uma pessoa só.**
Qualquer um da equipe revisa e move, e o sistema grava quem aprovou.

**Liberar montagem que não cabe é decisão fechada da equipe.** Qualquer
um pode liberar, com o nome registrado, e o caso **não** sobe para o
operador — escolha consciente dele, contra a recomendação de mandar para
as pendências. A liberação continua escrita na própria ordem, para quem
receber o papel saber que foi decisão de alguém e não descuido.

**O registro mora num arquivo próprio, com tela de histórico.** Quem
aprovou, quem trocou máquina, quem liberou sem caber — uma linha por
montagem, mais a linha no log do dia. A tela existe porque o operador
tirou o caso difícil do caminho dele: ele precisa de um lugar onde
*escolhe* olhar.

**O painel de hoje é reaproveitado, não reescrito.** Ele já desenha a
chapa em escala, calcula sangria, vão e pinça, risca a grade que não
cabe, e sua conta bate com montagem real na terceira casa decimal. Passa
a ser servido, com o config injetado e os campos medidos pré-preenchidos.
A fila e o histórico são telas novas, porque não existem.

**O portão aceita PDF e `.cdr`.** O `.cdr` da AMÉRICA não se rasteriza:
ela manda a montagem com a imagem já dentro, e o motor da Corel publica
em PDF. Arquivo de várias páginas é mostrado e perguntado, nunca
adivinhado.

**O servidor é alcançável pela rede interna, sem senha.** É o que tira a
dependência de verdade — a equipe montando do PC dela. O nome de quem
decidiu resolve a autoria; senha em gráfica vira papelzinho no monitor.

**A entrada do WhatsApp é digitada, por enquanto.** Mensagem é texto
livre — "2 poses na 52", "roda na Mozp f4" — e interpretar errado vira
chapa errada. Quando houver uma coleção de mensagens reais contra as
quais provar, o parser entra sugerindo, com a pessoa confirmando.

**O servidor não pode derrubar o vigia.** O portão da AMÉRICA já não
estoura para cima; o mesmo vale aqui.

**O sistema espera o arquivo terminar de chegar** antes de medir, e
pergunta ao registro se já fez aquele arquivo antes de trabalhar.

## Testing Decisions

**O que faz um bom teste aqui:** provar comportamento que alguém percebe
— que a montagem saiu do tamanho da chapa, que o portão esvaziou, que o
nome de quem liberou ficou gravado. Não provar que uma função chamou
outra. O projeto já escreve assim: os testes existentes têm nomes como
"a prova que já saiu não segura o arquivo no portão" e "arte que só cabe
deitada faz a FIA parar" — cada um conta a regra que está segurando.

**Um seam novo, e só um.** O módulo da montagem é testado pelas suas
funções; a camada HTTP não é testada, porque não tem lógica própria. A
ordem de montagem ser o contrato é o que permite isso: tudo que a tela
coleta cabe num objeto, e se prova o que a função faz com ele.

**O que é novo e precisa de prova:**

- a leitura de sangria pelos dois caminhos, incluindo o caso em que eles
  discordam;
- que a montagem grave na pasta do dia e **nunca** no portão de saída;
- que o original saia do portão sem ser apagado;
- que o portão nunca fique com dois PDFs do mesmo serviço;
- que quem aprovou, quem trocou máquina e quem liberou sem caber fiquem
  gravados;
- que arquivo já montado não seja refeito.

**O que não se testa de novo, porque já tem seam e já está coberto:** a
medição de tamanho e tintas, a regra de máquina, o assentamento na chapa
com a pinça, e a conferência da pinça no arquivo que saiu. Reaproveitar
esses caminhos não é economia de teste — é a garantia de que a tela e o
vigia decidem a mesma coisa.

**Prior art:** o arquivo de testes da AMÉRICA já traz os dois feitios que
esta spec precisa. Funções puras testadas direto — a regra da máquina, as
pinças ditadas pelo operador, o limite do formato 4. E fechamentos
inteiros armados com pastas temporárias e substituição das bordas
(medição, banco, impressora, registro), que é como se prova ordem de
passos sem tocar em produção.

**O lado JavaScript continua no seam que já tem:** o provador que mexe
nos campos do painel no navegador sem tela e confere a resposta. Ele
passa a provar também os campos pré-preenchidos. Esta máquina não tem
runtime de JavaScript, e essa foi a saída encontrada antes.

## Out of Scope

- **Ler a mensagem do WhatsApp.** Decidido adiar até haver mensagens
  reais suficientes para provar um parser contra elas. Entra depois, e
  entra sugerindo — nunca decidindo.
- **Aviso sonoro, Teams ou WhatsApp quando cai arquivo novo.** A fila
  basta para começar; o aviso vem quando a equipe disser que faz falta.
- **Preflight de resolução das imagens** na tela da fila. A FIA já sabe
  medir resolução efetiva, mas isso não decide a montagem.
- **Memória de trabalho repetido** — pré-preencher a partir da última
  montagem do mesmo nome. Bom, e não é o problema que trava a equipe.
- **Mover para a `PARA CTP` automaticamente.** Não é "ainda não": é
  decisão de nunca, porque a mudança de pasta é a aprovação.
- **Senha ou lista de quem pode.** Descartado a favor do nome registrado.
- **Girar arte que só cabe deitada.** Continua parando e perguntando.
- **Os outros clientes.** Esta spec é da AMÉRICA, que é a única que chega
  por montar.

## Further Notes

**Por que a AMÉRICA é diferente, e por que isso importa aqui.** Os outros
clientes mandam o arquivo pronto e a FIA só faz o fechamento final. Na
AMÉRICA o arquivo chega por montar. Foi por isso que o caminho dela nunca
entrou na lista de clientes vigiados, e é por isso que este sistema é
dela e não da casa toda.

**Três travas que vêm de erro já pago, e não se mexe:** sem pinça não vai
para o CTP; a montagem é conferida depois de feita, no arquivo que saiu; e
o portão nunca fica com dois PDFs do mesmo serviço. A primeira nasceu de
uma chapa 12 mm fora do lugar; a segunda, de uma conta certa que o
programa no meio podia estragar; a terceira, de duas gravações e duas OS.

**A lição das três folhas de papel, que vale para o portão novo.** Falha
depois de um passo caro vira laço: quem imprime tem de deixar dito que
imprimiu, na hora, antes de fazer mais qualquer coisa. O trabalho está
feito quando o resultado está no lugar; o que vem depois é faxina, e
faxina que falha não pode custar trabalho refeito.

**Tinta e desenho são coisas diferentes,** e é a parte que se erra. Numa
chapa de pinça 60, a tinta começa por volta de 47 mm — são as marcas de
corte e registro, que vivem dentro da pinça de propósito — e o desenho
por volta de 57. Medir a primeira tinta e perdoar folga é conta cega.

**O painel deixou de escolher, e isso foi deliberado.** Houve um dia em
que ele oferecia cinco arranjos fixos e o número 6 não cabia em nenhum.
Hoje tudo é digitado e ele lê, desenha e avisa. Este sistema não desfaz
isso: ele pré-preenche o que **mediu no arquivo**, que é fato, e continua
sem escolher o que é decisão.

**Área útil e formato são limites diferentes.** Área útil é da chapa — o
que a gravadora alcança, tirada a pinça. Formato é da folha — o que a
impressora pega. Uma montagem pode caber numa e não na outra, e o aviso
precisa dizer qual dos dois estourou.

**Um número de formato pode ter mais de uma folha,** e não é erro de
digitação: são maneiras diferentes de cortar a folha grande. Por isso a
tela pergunta qual, em vez de pegar a primeira. E a folha entra nos dois
sentidos.

**A tabela de formatos não saiu do banco da empresa** de propósito: o
campo de lá é texto livre, com cinquenta e tantas grafias, e as medidas
ao lado ora estão em milímetro, ora em centímetro, ora são a medida da
chapa em vez da folha. Uma tabela tirada dali sairia errada e ninguém
veria.

**O que o operador disse, e que orienta tudo:** *"o que eu quero é que a
minha equipe não dependa de mim pra dar andamento"*. Cada decisão desta
spec foi medida contra essa frase — inclusive a de liberar montagem que
não cabe sem passar por ele, que foi escolha dele contra a recomendação
de escalar.
