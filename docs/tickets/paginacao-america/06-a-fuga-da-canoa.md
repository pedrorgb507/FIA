# 06: A fuga da canoa (o *creep*) — ESPERANDO O OPERADOR

**What to build:** Numa revista grampeada os cadernos são encaixados um
dentro do outro, e **o papel dobrado empurra**: cada caderno de dentro
fica um pouco mais comprido que o de fora. Cortado o livro no esquadro,
as páginas do miolo perdem margem interna — e se o texto estiver perto
da dobra, **a guilhotina come texto**.

A compensação é mover cada página um pouco **em direção à lombada**, e
quanto mover depende do caderno em que ela está.

**O `paginacao.py` NÃO compensa nada hoje.** Ele reparte páginas; a peça
sai do mesmo tamanho e na mesma posição em todos os cadernos.

**Blocked by:** a resposta do operador

**Status:** perguntado em 20/09/2026, sem resposta

## A pergunta que ficou de pé

> **O operador compensa a fuga hoje, e com que número?**

Ela não se chuta porque depende de duas coisas que só quem roda sabe:

- **a gramatura do papel** — papel grosso empurra mais;
- **quantos cadernos** o livro tem — a fuga é acumulada, e o caderno de
  dentro é o que mais sofre.

E há uma terceira, que é de ofício: **algumas casas não compensam** em
livro de poucos cadernos, porque a fuga fica abaixo do que a guilhotina
erra de qualquer jeito. Se for esse o caso aqui, isso também é resposta —
e vira regra escrita, não buraco.

## Enquanto não houver resposta

**Canoa de mais de um caderno pede olho de gente antes de gravar**, e o
painel avisa (ticket 04). Um caderno só não tem fuga: não há nada
encaixado dentro dele.

## O que fazer quando a resposta vier

- [ ] Escrever a regra na skill `imposicao`, com o caso de verdade e os
      números medidos
- [ ] A compensação entra por caderno, e move a página **para a lombada**
- [ ] Teste: num livro de 4 cadernos, o de dentro anda mais que o de
      fora, e o de fora não anda
- [ ] Medir num PDF que saiu — não confiar no relatório
