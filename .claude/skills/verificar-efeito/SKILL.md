---
name: verificar-efeito
description: Como saber se uma ação realmente aconteceu, em vez de confiar que o comando foi dado — e quanta verificação cada caso merece, já que encher de conferência o que não tem risco também custa caro. Use ao escrever ou revisar qualquer coisa que age no mundo — clicar numa tela, enviar mensagem ou arquivo, subir, baixar, apagar, marcar como feito, mover arquivo, publicar. Use ao investigar "o robô diz que funcionou mas não funcionou", "mandou mas não chegou", "processou e não apareceu". Use antes de dizer a alguém que a tarefa está pronta, e sempre que um agente for falar com cliente — afirmar a alguém que algo foi feito é uma ação com efeito, e errar nela custa mais caro que errar no código. Carregue mesmo quando o código parecer obviamente certo: esse tipo de falha é silenciosa por natureza, e quem a comete está sempre convencido de que não cometeu.
---

# Verificar o efeito, não o comando

**Confirmar que um comando foi dado não é o mesmo que confirmar que ele teve
efeito.** Essa frase parece óbvia escrita assim, e é exatamente por isso que ela
engana: quem está cometendo o erro acha que não está.

`click()` voltar sem exceção prova que o evento foi despachado, não que algo
mudou. Um HTTP 200 num endpoint de fila prova que a fila aceitou, não que a
mensagem chegou. Um `write()` numa pasta de rede pode voltar antes de o arquivo
existir de verdade do outro lado. Um `push` pode ir para uma referência velha.

A falha é silenciosa por construção: o programa segue feliz, registra sucesso e
vai para o próximo item. Ninguém descobre no momento — descobre-se dias depois,
quando alguém pergunta pelo arquivo que nunca chegou.

## Calibre o esforço pelo custo de errar

Nem toda ação merece a mesma verificação, e encher de conferência o que não
precisa tem preço: código mais difícil de ler, mais lento, e — pior — atenção
gasta onde não havia risco, que é atenção que faltou onde havia.

O que define quanto investir não é o quanto a ação parece importante. É **o que
acontece se ela falhar em silêncio**. Três perguntas, nesta ordem:

1. **O item sai da fila?** Se depois da ação ninguém mais tenta — o arquivo foi
   movido para "enviados", a mensagem foi marcada como lida, o registro foi
   gravado — a falha silenciosa é permanente e some com a própria evidência.
   Aqui vale confirmar por um caminho independente.
2. **Repetir causa dano?** Alternância que desfaz o que estava feito, envio que
   duplica, cobrança que dobra. Aqui vale distinguir "não sei" de "não" mesmo
   quando isso custa uma consulta a mais.
3. **Alguém vai agir com base nisso?** Dizer a um cliente que o arquivo chegou
   faz ele parar de procurar. A afirmação vira decisão de outra pessoa.

Se as três respostas forem não — escrever uma linha de log, gerar um arquivo
temporário, algo que a pessoa vê na tela no segundo seguinte — uma verificação
leve basta. Confira o retorno, trate o erro e siga.

E mesmo quando vale verificar: **prefira a verificação mais barata que ainda
sabe reprovar.** Uma releitura do estado que separa certo de errado vale mais
que três camadas que sempre concordam entre si.

## Quando o efeito real é inalcançável

Às vezes não existe como confirmar o que interessa de verdade. O servidor de
e-mail aceitar a mensagem não prova que ela chegou na caixa do cliente; entregar
um arquivo a um sistema de terceiros não prova que ele foi processado.

Nesses casos, três coisas, e nenhuma delas é construir uma catedral de
verificação para simular certeza que não existe:

- Use **o sinal mais forte disponível** e pare aí.
- **Diga qual é o limite dele**, no código e para a pessoa.
- **Não converta sinal fraco em afirmação forte.** "Entregue ao servidor de
  e-mail" é honesto. "Enviado ao cliente" é uma promessa que você não pode
  cumprir.

Um limite declarado é informação útil. Um limite disfarçado de garantia é o
mesmo problema deste documento, só que mais bem vestido.

## Meça por um caminho diferente do que você usou para agir

Se você agiu pela interface, confira pelos dados: recarregue do zero, leia a
resposta do servidor, consulte por outra sessão. Se escreveu um arquivo, confira
tamanho e os primeiros bytes, não só que a função não deu erro. Se mandou uma
mensagem, procure ela na lista do destino.

O motivo é simples: o mesmo caminho que mentiu na hora de agir costuma mentir
também na hora de conferir. Quando a tela é a única testemunha do que a tela fez,
não há testemunha.

Quando existir alguém que enxerga o resultado real — a pessoa que usa o sistema,
o destinatário da mensagem, o log do outro lado — essa é a melhor fonte de
verdade disponível. Não hesite em perguntar.

## A tela desenha antes de o servidor confirmar

Aplicações modernas mostram o resultado imediatamente para parecerem rápidas, e
desfazem depois se o servidor recusar. Isso significa que **ver o resultado não
basta**. Duas defesas que funcionam:

1. **Exija identificação do servidor.** Enquanto o item existe só no desenho, ele
   não tem id, número, timestamp ou confirmação vindos de fora. Se o que você
   encontrou não tem essa marca, é rascunho.
2. **Confirme que fica.** Espere alguns segundos e confira de novo. O que foi
   recusado some nesse intervalo — e se você só olhou uma vez, olhou justamente
   na janela em que a mentira estava no ar.

## Prove que a sua verificação sabe dizer "não"

Uma verificação que nunca retornou falso não é uma verificação — é um enfeite que
sempre concorda com você.

Antes de confiar numa checagem, encontre um caso em que ela **deve** reprovar e
confirme que ela reprova. Sem esse teste, você não sabe se está medindo o
resultado ou algo que estaria lá de qualquer jeito.

Os falsos positivos mais comuns, todos já vistos na prática:

- **Texto de rótulo.** Muda com o idioma, com a versão, com o tema. Prefira
  identificadores estáveis: id, código, atributo de dados.
- **Elemento que existe nos dois estados.** Botões de menu, barras que aparecem
  ao passar o mouse, contêineres vazios. Contar isso mede a interface, não o
  resultado.
- **Recorte que não inclui o que importa.** Foto de um elemento pode cortar
  justamente a área onde o resultado apareceria.
- **O retorno da própria ação.** O mais sedutor de todos, porque parece
  autoridade e é só eco.

## "Não sei" não é "não"

Quando a verificação não consegue observar — o item saiu da tela, a rede caiu, a
resposta veio vazia — o resultado honesto é **desconhecido**, não "não feito".

Colapsar os dois é perigoso de um jeito específico: em operações que alternam
estado, repetir a ação **desfaz** o que já estava feito. Marcar o que já estava
marcado desmarca. Transferir de novo o que já foi transferido duplica.

Devolva três estados — sim, não, não sei — e deixe quem chamou decidir. Se não
souber, o certo quase sempre é não agir e tentar de novo depois.

## Não registre "feito" antes de confirmar

Gravar no registro, mover para a pasta de enviados, marcar como lido, tirar da
fila — tudo isso é **afirmar que o trabalho terminou**. Feito antes da
confirmação, some com a evidência do problema: o item sai da fila, ninguém mais
tenta, e o rastro de que faltava alguma coisa desaparece junto.

A ordem que se sustenta é **agir → confirmar → registrar**. Se a confirmação
falhar, deixe o item onde estava. Repetir na próxima passada custa pouco; perder
em silêncio custa muito.

## Antes de acusar o código, descarte a si mesmo

Quando algo falha logo depois de você mexer, a explicação mais provável não é um
defeito profundo — é o seu próprio experimento.

Pergunte, nesta ordem:

- Existe mais de uma instância rodando? Duas cópias do mesmo processo disputando
  o mesmo recurso produzem erros que parecem qualquer outra coisa.
- Sobrou processo de uma execução anterior? Encerrar o programa nem sempre
  encerra o que ele abriu.
- O dado que está falhando foi você que forçou para testar? Dado artificial falha
  de formas artificiais.
- O que está rodando é a versão que você acabou de corrigir, ou a que subiu antes
  da correção?

Perder tempo perseguindo um defeito que você mesmo criou é comum e caro. Liste o
que você mexeu e rode limpo antes de concluir qualquer coisa.

## Falhe alto

Entre errar e errar em silêncio, o silêncio é muito pior. Um erro no log alguém
lê; um item que sumiu sem reclamação ninguém procura.

Quando o programa encontrar algo que não sabe tratar — um formato inesperado, uma
resposta vazia, um caso que não previu — registre e deixe o item pendente. Não
transforme "não sei o que fazer com isso" em "nada a fazer aqui".

## Como relatar

Isso vale para o que você escreve tanto quanto para o que você programa.

- Diga **o que verificou e como**. "Enviado" é uma afirmação; "enviado, e a
  mensagem aparece na conversa com id do servidor" é um fato.
- Quando não conseguir confirmar, **diga isso**. "Rodou sem erro, mas não
  consegui confirmar que chegou" é uma frase útil. "Pronto!" no mesmo caso é uma
  mentira involuntária.
- Se afirmou e depois descobriu que estava errado, **corrija em uma linha** e
  siga. Insistir numa hipótese custa mais que medir de novo.

**Para agente que fala com cliente:** dizer a alguém que algo foi feito é em si
uma ação com efeito, e não dá para recolher. Nunca afirme ao cliente que um
arquivo foi enviado, recebido ou processado sem ter lido a confirmação. Na
dúvida, diga o que se sabe e o que ainda está sendo verificado — cliente perdoa
demora, não perdoa informação errada.
