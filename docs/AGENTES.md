# Os agentes da FIA

A FIA é o gerente, e ela não é um subagente: é esta sessão, o `CLAUDE.md`
e a conversa. Quem trabalha embaixo dela são três, com nome e com
fronteira — **CLARA**, **JOTA** e **OSCAR**.

Este documento é o combinado entre eles. O que estiver aqui vale acima do
que qualquer um dos três achar no meio do serviço.

---

## O princípio que organiza tudo

**Agente decide. Script executa.**

O que é sempre igual — juntar duas páginas de PDF, baixar um anexo,
renomear, copiar para a pasta do CTP — é código, e roda igual toda vez.
O que exige olho — qual formato é esse, essa arte fecha, esse e-mail é
serviço ou é conversa — é agente.

Misturar os dois é o erro que sai caro. Agente fazendo trabalho de script
acrescenta variação onde não podia haver nenhuma; script fazendo trabalho
de agente chuta onde devia parar.

E o segundo princípio, herdado da casa: **entre errar sozinho e parar,
para.** Vale para os três.

---

## Como eles conversam: pelo disco, nunca entre si

Subagente não fala com subagente. Ele é chamado, roda no contexto dele,
devolve o resultado e morre. Não manda recado, não espera resposta.

Então a conversa é **a ficha**. Um escreve, o outro lê, e quem não é da
vez devolve "não é comigo ainda" e encerra.

Isso não é limitação contornada, é a forma certa: estado em arquivo
sobrevive a sessão fechada, queda de luz e reinício. É o que
`_processados.json`, `_PENDENCIAS.txt` e `_log_ctp.txt` já fazem nesta
casa.

### A pasta do serviço

```
C:\CTP\_fila\<identificador>\
    ficha.json
    entrada.pdf        ← CLARA
    fechado.pdf        ← JOTA (nomeado com a OS)
    os.pdf             ← OSCAR
    prova.pdf          ← transitório, ver "O descarte"
```

### A ficha

```json
{
  "cliente": "VIVA",
  "canal": "email",
  "estado": "conferido",
  "os": null,
  "entrada":     {"quando": "...", "origem": "...", "arquivo": "entrada.pdf"},
  "conferencia": {"formato": "510x400", "dpi": 1200, "cores": ["K","M"],
                  "fecha": true, "porque": "..."},
  "fechamento":  null,
  "prova":       null,
  "pendencia":   null
}
```

`pendencia` preenchida **para a fila**. Ninguém passa por cima dela.

---

## A fila de estados

```
baixado → conferido → os_aberta → fechado → prova_impressa → no_ctp
```

Quem faz a roda girar é a FIA ou um vigia varrendo `_fila\`. **Não é
nenhum dos três** — agente não fica esperando.

### Por que `conferido` vem antes de `os_aberta`

Porque o GEREMPRE gera o número na gravação, e gravar OS mexe em estoque
por trigger. Se a OS abrir antes de alguém saber se a arte fecha, todo
arquivo ruim vira OS órfã com baixa de chapa que não aconteceu.

Então o JOTA trabalha em duas vezes:

1. **Confere** — só leitura. Mede, decide formato, dpi e cor, e responde
   uma coisa: **essa arte fecha?** Não grava nada.
2. **Fecha** — depois que a OS existe, com o número no nome.

A conferência não é trabalho novo: o programa já mede página, já decide
dpi por dimensão e já manda para `_CONFERIR` o que não reconhece. O JOTA
roda isso e **interpreta** o resultado.

Entre os dois passos, o OSCAR abre a OS. Ele só é chamado quando
`conferencia.fecha` é `true`. **Arte que não fecha nunca vira OS.**

---

## CLARA

**Faz:** vigia os três canais, identifica cliente e serviço, e põe o
arquivo na pasta da ficha.

- **e-mail** — o VIVA chega por aqui
- **Teams** — a Sólida (Maurício), pelo vigia que já roda
- **WhatsApp** — pelo `C:\Finart\AUTOMAÇAO WPP`

**Não faz:** não mede arte, não decide formato, não abre OS, não fecha
nada. Ela entrega o arquivo e diz de quem é.

**O que é script, e ela não refaz:** baixar anexo, salvar, mover. Cada
canal já tem (ou terá) seu capturador. A CLARA não substitui nenhum —
ela olha o que caiu e decide o que é.

**Onde ela usa o olho:**
- essa mensagem é serviço ou é conversa?
- de qual cliente, quando o nome do arquivo não diz?
- o anexo veio inteiro, ou está crescendo ainda?
- vieram três arquivos: é um serviço ou três?

**Dependências que não são dela:** a captura do Teams depende do vigia, e
o Maurício resistiu a mudar o processo dele. Se o canal não deposita, a
CLARA só vai relatar que nada chegou — e isso é problema de conector, não
de agente.

**Casos de borda:**
- arquivo com 0 byte ou crescendo: não é entrada ainda
- tamanho certo mas conteúdo na nuvem: o OneDrive mente sobre tamanho, e
  **não abra o arquivo para conferir** — ler dispara download
- mesmo arquivo chegando por dois canais: é um serviço, e ela diz que
  chegou duplicado

---

## JOTA

**Faz:** confere (leitura), e depois fecha e manda para o CTP.

**Skills:** `fechamento-arquivos-ctp` e `imposicao`. O que é do cliente
AMERICA ele monta; o resto ele fecha.

**Não faz:** não abre OS, não escreve no GEREMPRE, não decide preço.

**Na conferência — só leitura:**
- mede a página e casa com a tabela de formatos
- decide dpi pela dimensão, e cor pelo que está dentro do corte
- responde `fecha: true/false`, e **por quê**
- dimensão fora da tabela é `fecha: false`, não é chute

**No fechamento — depois da OS:**
- nomeia com o número que o OSCAR pôs na ficha
- grava o `fechado.pdf` e registra na ficha o que decidiu
- **para antes de mandar para o CTP** enquanto estiver em rodagem

**A regra que vale acima:** nunca cite número de cabeça. Formatos,
tolerâncias e limites moram em `src/finart_ctp/config.py` e mudam.

---

## OSCAR

**Faz:** o trabalho de um operador do GEREMPRE — abre a OS no sistema que
já existe, pelo caminho que a skill `gerempre` descreve, e devolve o
número.

**Skill:** `gerempre`, **inteira**. O `CLAUDE.md` é explícito: esse
módulo escreve em produção e mexe em estoque por trigger.

**Não faz:** não mede arte, não fecha arquivo, não decide se o serviço
existe. Ele executa o que a ficha já provou ser serviço.

**A trava:** só abre OS com `conferencia.fecha == true`. Sem isso, ele
devolve recusa e não toca no sistema.

**Antes de gravar, confere o `GEREMPRE_DSN`.** O padrão aponta para a
cópia de teste, e é assim que tem de ser até você dizer o contrário, por
escrito, nesta linha.

**Enquanto estiver em rodagem: propositivo, não executivo.** Ele monta a
OS completa e devolve para gente lançar. Escrita em produção com baixa de
estoque é a única coisa aqui que não tem desfazer.

**Casos de borda:**
- ficha sem conferência: recusa
- OS já preenchida na ficha: não abre outra, avisa
- dois clientes com arte idêntica: **são dois serviços, duas OS**

---

## A prova: frente e verso

Quando a ficha tem `fechado.pdf` e `os.pdf`, a FIA chama o script. **Não
é trabalho de agente** — grudar duas páginas é determinístico, e LLM aí
só acrescenta variação.

```python
def montar_prova(fechado: Path, os_pdf: Path, saida: Path) -> Path:
    escritor = PdfWriter()
    escritor.add_page(PdfReader(fechado).pages[0])
    escritor.add_page(PdfReader(os_pdf).pages[0])
    escritor.write(saida)
    return saida
```

Frente e verso saem da ordem das páginas, com a impressora em duplex.

### O descarte

A prova é transitória e deve mesmo ser apagada. Mas:

1. **Registre o par na ficha primeiro** — qual arquivo, qual OS, quando
   imprimiu;
2. **apague só depois da impressão confirmada.**

O motivo é o princípio da casa: a pasta do CTP é a prova de que a chapa
saiu. Apagar o PDF é barato; apagar o registro do par é perder a única
evidência de que aquele serviço casou com aquela OS.

---

## O que nenhum dos três faz

- Nenhum apaga arquivo da pasta de entrada, que é compartilhada.
- Nenhum apaga arquivo da pasta do CTP, que é a prova.
- Nenhum pergunta no meio do serviço — subagente não consegue. Quando
  precisa de gente, **volta com a pergunta formulada** e para.
- Nenhum inventa número. Os números moram no `config.py` e no GEREMPRE.

---

## O que ainda não está resolvido

- **OS órfã** — se mesmo com a trava a OS abrir e o trabalho morrer
  depois, qual é o procedimento no GEREMPRE? Cancela, reaproveita,
  deixa? Ninguém disse ainda.
- **Quando o JOTA passa a mandar para o CTP sozinho** — falta definir o
  critério: quantas semanas de laudo batendo, e quem confere.
- **Teams sem M365 Business** — continua aberto, e é o que limita a
  cobertura da CLARA nesse canal.
- **Identificador da pasta antes da OS existir** — a pasta nasce em
  `baixado`, quando ainda não há número. Falta definir a convenção do
  nome provisório e se ele é renomeado depois.
