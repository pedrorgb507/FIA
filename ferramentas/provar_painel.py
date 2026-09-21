# -*- coding: utf-8 -*-
r"""
Prova o painel de imposicao SEM runtime de JavaScript nesta maquina.

Esta maquina nao tem node, e balanco de chaves ou "a pagina abre" nao
provam regra nenhuma. O que funciona esta descrito na skill de
imposicao: uma COPIA da pagina com um script a mais no fim, que mexe
nos campos, chama o laco do painel e escreve no DOM o que ele
respondeu - e o Edge sem tela (--headless=new --dump-dom) devolve o
resultado.

A copia sai do arquivo DE VERDADE, lido na hora. Se o painel mudar e a
regra quebrar, isto quebra junto - que e o unico jeito de a prova valer
alguma coisa.

Uso:  python ferramentas/provar_painel.py
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PAINEL = os.path.join(AQUI, "painel_imposicao.html")

sys.path.insert(0, os.path.join(AQUI, "..", "src"))

# O PAINEL NAO ABRE MAIS SOLTO, e o provador tem de servi-lo como o
# servidor serve - com as chapas e os formatos do config de verdade.
#
# ISSO MELHOROU A PROVA, e nao foi so acomodacao: antes o provador
# exercitava a COPIA em JavaScript das tabelas, e uma copia errada
# passaria por aqui sem ninguem ver. Agora, se o config e o painel
# deixarem de se entender, isto quebra.
from finart_ctp import montagem, servidor          # noqa: E402

EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _edge():
    for c in EDGE:
        if os.path.exists(c):
            return c
    raise SystemExit("nao achei o Edge - sem ele nao ha como rodar o painel")


# O script que entra no fim da COPIA. Ele fala com o painel pelos mesmos
# campos que o operador usa - nada de API secreta.
SONDA = r"""
<script>
function _ficha_em(alvo, texto){
  const bs = document.querySelectorAll("#" + alvo + " button");
  for(const b of bs) if(b.textContent.trim().indexOf(texto) === 0){ b.click(); return true; }
  return false;
}
function _ficha(texto){ return _ficha_em("tipos", texto); }
function _por(id, valor){
  const c = document.getElementById(id);
  c.value = String(valor);
  c.dispatchEvent(new Event("input", {bubbles:true}));
}
function _ficha_ativa(alvo){
  const b = document.querySelector("#" + alvo + " button[aria-pressed=true]");
  return b ? b.textContent.trim() : null;
}
function _campo(id){ return document.getElementById(id).value; }
function _estado(){
  const v = document.getElementById("nverso");
  const cx = document.getElementById("cx-verso");
  /* A ORDEM SE PEDE DIRETO, e nao pelo botao: o 'Gerar imposicao' so
     destranca com arquivo na lista, e arquivo de verdade nao se
     simula num input file. ordem(contas()) e exatamente o que o
     botao chama - a mesma funcao, o mesmo estado. */
  let texto = "";
  try{ texto = ordem(contas()); }catch(err){ texto = "ERRO: " + err; }
  return {
    verso_desabilitado: v.disabled,
    verso_valor: v.value,
    caixa_apagada: cx.classList.contains("apagado"),
    frente_desabilitado: document.getElementById("nfrente").disabled,
    ordem: texto
  };
}
const OUT = {};
try{
  // --- O QUE A FILA MANDOU, antes de mexer em nada ---
  //
  // Este e o estado com que o painel ABRE: campos preenchidos do que a
  // FIA mediu e maquina sugerida pela regra da casa. Ele se le uma vez,
  // no comeco, porque os casos abaixo mexem nos campos de proposito.
  OUT.ao_abrir = {
    peca_largura: _campo("pl"),
    peca_altura: _campo("pa"),
    sangria: _campo("sangria"),
    chapa: _ficha_ativa("chapas"),
    cor: _ficha_ativa("cores"),
    tipo: _ficha_ativa("tipos"),
    nome_na_tela: document.getElementById("arq-nome").textContent,
    faixa_escondida: document.getElementById("do-arquivo").hidden,
    // as tabelas vieram do config, e nao de copia escrita na pagina
    chapas_servidas: Array.from(
      document.querySelectorAll("#chapas button")).map(b=>b.textContent.trim()),
    formato_4: JSON.stringify(formatosDaCasa(4)),
  };

  // --- ponto de partida: bate-vira, o padrao ---
  _ficha("Bate-vira");
  _por("nfrente", 2); _por("nverso", 2);
  OUT.bate_vira = _estado();

  // --- so frente: o verso nao existe ---
  _ficha("Só frente");
  _por("nfrente", 8);
  OUT.so_frente = _estado();

  // --- voltando: o que estava no verso tem de VOLTAR ---
  _ficha("Bate-vira");
  OUT.voltou = _estado();

  // --- frente e verso: o campo vale ---
  _ficha("Frente e verso");
  OUT.frente_verso = _estado();

  // --- OS AVISOS. Sao a razao de o painel existir: ele le, desenha e
  //     avisa. Cada um se arma de proposito, e o que se le e o texto
  //     que a pessoa ve.
  function _avisos(){
    return {
      veredito: document.getElementById("v-txt").textContent,
      classe: document.getElementById("veredito").className,
      grade: document.getElementById("regra-grade").textContent,
    };
  }

  // nao cabe na AREA UTIL: peca grande demais para a chapa
  _ficha("Só frente");
  _por("pl", 400); _por("pa", 400); _por("nfrente", 4);
  _por("ncols", 2); _por("nrows", 2);
  OUT.nao_cabe_util = _avisos();

  // nao cabe no FORMATO: cabe na chapa e nao na folha. A peca de
  // 200x250 em 2x1 da 500x250 - entra na PM 52 (525 x 399 util) e nao
  // entra no util do formato 4 (315x460 nos dois sentidos).
  _por("pl", 200); _por("pa", 250); _por("nfrente", 2);
  _por("ncols", 2); _por("nrows", 1); _por("formato", 4);
  OUT.nao_cabe_formato = _avisos();

  // CELULA VAZIA: menos imagens do que celulas
  _por("pl", 100); _por("pa", 150); _por("nfrente", 3);
  _por("ncols", 2); _por("nrows", 2);
  OUT.celula_vazia = _avisos();

  // --- A ORDEM QUE O BOTAO MANDA. E o contrato: tudo que a tela
  //     coletou cabe neste objeto, e e ele que vai para a FIA.
  _ficha("Bate-vira");
  _por("pl", 100); _por("pa", 150); _por("sangria", 2.5); _por("vao", 5);
  _por("nfrente", 2); _por("nverso", 2);
  _por("ncols", 2); _por("nrows", 2); _por("formato", 4);
  document.getElementById("quem").value = "Pedro";
  OUT.ordem_objeto = ordemObjeto(contas());
  OUT.botao = {
    texto: document.getElementById("gerar").textContent,
    desabilitado: document.getElementById("gerar").disabled,
    seletor_escondido: document.getElementById("entrega")
                         .classList.contains("so-o-botao"),
  };

  // trocou a maquina que a regra sugeriu: tem de ficar dito na ordem
  OUT.clicou_na_sm74 = _ficha_em("chapas", "SM 74");
  OUT.ordem_com_troca = ordemObjeto(contas());

  // --- LIBERAR O QUE NAO CABE. A peca grande estoura os dois limites;
  //     o 'dar andamento' e a resposta de gente, e ela tem de cair a
  //     cada mudanca.
  _ficha_em("chapas", "PM 52");
  _ficha("Só frente");
  _por("pl", 400); _por("pa", 400); _por("nfrente", 4);
  _por("ncols", 2); _por("nrows", 2); _por("formato", 4);
  OUT.antes_de_liberar = {
    aviso: document.getElementById("v-txt").textContent,
    pergunta_visivel: !document.getElementById("andamento").hidden,
    marcado: document.getElementById("tocar").checked,
    ordem: ordemObjeto(contas()).liberado_sem_caber,
    botao_travado: document.getElementById("gerar").disabled,
  };

  document.getElementById("tocar").click();
  OUT.depois_de_liberar = {
    marcado: document.getElementById("tocar").checked,
    ordem: ordemObjeto(contas()).liberado_sem_caber,
    botao_travado: document.getElementById("gerar").disabled,
    texto: ordem(contas()),
  };

  // MUDOU UM CAMPO: o 'pode ir' cai. Um 'pode ir' dado para uma
  // montagem nao vale para a seguinte.
  _por("nfrente", 4);       // dispara 'input' e derruba a liberacao
  OUT.depois_de_mexer = {
    marcado: document.getElementById("tocar").checked,
    ordem: ordemObjeto(contas()).liberado_sem_caber,
    botao_travado: document.getElementById("gerar").disabled,
  };

  // --- O ENCONTRO SO EXISTE ONDE HA VERSO. Escolhido no bate-vira, ele
  //     nao pode continuar valendo depois de trocar para 'so frente' -
  //     ali o seletor some da tela e o giro ficaria preso ao contrario.
  _ficha_em("chapas", "PM 52");
  _por("pl", 100); _por("pa", 150);
  _por("ncols", 2); _por("nrows", 2); _por("nfrente", 2); _por("nverso", 2);
  _ficha("Bate-vira");
  _ficha_em("encontros", "Pé com pé");
  OUT.pe_com_pe = {ordem: ordemObjeto(contas()).encontro,
                   giro: contas().giroFrente};
  _ficha("Só frente");
  _por("nfrente", 4);
  OUT.so_frente_depois_do_pe = {ordem: ordemObjeto(contas()).encontro,
                                giro: contas().giroFrente};

  // --- MARCA DE CORTE DESMARCADA nao tem como 'nao caber'.
  _ficha("Só frente");
  _por("pl", 160); _por("pa", 245); _por("nfrente", 4);
  _por("ncols", 2); _por("nrows", 2); _por("formato", 1);
  OUT.com_marca = {cabem: contas().marcasCabem,
                   classe: document.getElementById("veredito").className};
  document.getElementById("m-corte").click();
  OUT.sem_marca = {cabem: contas().marcasCabem,
                   classe: document.getElementById("veredito").className,
                   na_ordem: ordemObjeto(contas()).marca_de_corte};
  document.getElementById("m-corte").click();

  // --- O GIRO DA PECA: em pe ou deitada. O caso do operador em
  //     18/09/2026 - arte em pe que o painel deitava, sem como pedir
  //     o contrario.
  function _celula(){
    const c = contas();
    return {cw:c.cw, cah:c.cah, empe:c.empe, giro:c.giro.g,
            giro_frente:c.giroFrente, giro_verso:c.giroVerso,
            mw:+c.mw.toFixed(2), mh:+c.mh.toFixed(2),
            aviso:c.viraSemDeitar,
            regra:document.getElementById("regra-giro").textContent,
            na_ordem:ordemObjeto(contas()).giro,
            linha_peca:(ordem(contas()).split("\n")
                        .filter(l=>l.indexOf("peça")===0)[0] || "")};
  }
  _ficha("Só frente");
  _por("pl", 100); _por("pa", 150); _por("ncols", 2); _por("nrows", 2);
  _por("nfrente", 4); _por("vao", 0);
  OUT.giro_m90 = (_ficha_em("giros","−90") , _celula());
  OUT.giro_p90 = (_ficha_em("giros","+90") , _celula());
  OUT.giro_0   = (_ficha_em("giros","0°")  , _celula());
  OUT.giro_180 = (_ficha_em("giros","180") , _celula());
  // bate-vira com a peca em pe: as cabecas nao se encontram no vao
  // vertical. AVISA, e nao trava.
  _ficha("Bate-vira");
  // o ENCONTRO vem de um caso anterior e inverte o giro da frente:
  // 'pe com pe' poe a frente a meia volta. Aqui se mede a conta do
  // VERSO, entao a frente tem de partir do canonico.
  _ficha_em("encontros", "Cabeça");
  _ficha_em("giros","0°");
  OUT.vira_em_pe = _celula();
  _ficha_em("giros","−90");
  OUT.vira_deitada = _celula();
  // quem TOMBA a folha continua indo a 180 - e a outra conta
  _ficha("Frente e verso");
  _ficha_em("giros","0°");
  OUT.fv_em_pe = _celula();

  // ==================================================================
  // OS TRES PROCESSOS - 20/09/2026
  // ==================================================================
  // FLAT-WORK e o padrao e nao muda nada; canoa e hotmelt abrem o
  // livro, e o montador vai SOMANDO caderno a caderno.
  function _livro(){
    const plano = planoDoLivro();
    return {
      bloco_escondido: document.getElementById("do-livro").hidden,
      faltam: _campo("faltam"),
      regra: document.getElementById("regra-livro").textContent,
      cadernos: Array.from(document.querySelectorAll("#cadernos .caderno"))
                     .map(d=>d.querySelector("b").textContent.trim()),
      quantos: plano.cadernos.length,
      fecha: plano.fecha,
      chapas: plano.chapas,
      paginas_por_caderno: plano.cadernos.map(c=>c.do_livro),
      travado: document.getElementById("gerar").disabled,
      ordem: ordem(contas()),
      objeto: ordemObjeto(contas())
    };
  }

  // o padrao, sem tocar em nada
  _ficha_em("processos", "FLAT-WORK");
  OUT.flat_work = _livro();

  // uma volta limpa antes do livro: 2x2, bate-vira
  //
  // A GRADE SE DIGITA DEPOIS DE ESCOLHER O PROCESSO, e a ordem passou a
  // importar em 21/09/2026: clicar em CANOA agora RECALCULA a grade
  // pela chapa, entao um 2x2 digitado antes seria reescrito no mesmo
  // instante. E o comportamento que o operador pediu - a montagem
  // aparece no layout ao clicar -, e o provador tem de falar a mesma
  // lingua da tela.
  _ficha("Bate-vira");
  _por("pl", 100); _por("pa", 150);

  _ficha_em("processos", "CANOA");
  _por("ncols", 2); _por("nrows", 2);
  _por("npaginas", 12);
  OUT.canoa_vazia = _livro();

  // acrescenta um bate-vira (2x2 = 4 paginas) e um frente e verso (8)
  OUT.clicou_bv = _ficha_em("add-caderno", "Bate-vira");
  OUT.canoa_um = _livro();
  OUT.clicou_fv = _ficha_em("add-caderno", "Frente e verso");
  OUT.canoa_fecha = _livro();

  // a etiqueta que o montador digita sai em TODOS os cadernos
  const leg = document.getElementById("legenda");
  leg.value = "REVISTA UNICIDADES - 20/09/2026";
  leg.dispatchEvent(new Event("input", {bubbles:true}));
  OUT.com_etiqueta = _livro();

  // O MESMO LIVRO EM HOTMELT: os cadernos empilham, e as paginas de
  // cada um mudam - e a diferenca visivel entre os dois processos.
  _ficha_em("processos", "HOTMELT");
  OUT.hotmelt = _livro();

  // --- O CADERNO DUPLICADO, 21/09/2026 ---
  // livro de 12 numa grade 4x2: um frente e verso leva 16 - demais.
  // Duplicando, leva 8; e o que sobra fecha com um bate-vira duplicado.
  _ficha_em("processos", "CANOA");
  _por("ncols", 4); _por("nrows", 2);
  e.cadernos = []; e.repeticao = 1; montar();
  _por("npaginas", 12);
  OUT.grade_4x2 = {
    rotulos: Array.from(document.querySelectorAll("#add-caderno button"))
                  .map(b=>b.textContent.trim()),
    travados: Array.from(document.querySelectorAll("#add-caderno button"))
                   .map(b=>b.disabled)
  };
  OUT.abriu_pers = _ficha_em("add-caderno", "Personalizado");
  OUT.pers_visivel = !document.getElementById("cx-pers").hidden;
  OUT.clicou_dup = _ficha_em("repeticoes", "2×");
  OUT.com_duplicado = {
    rotulos: Array.from(document.querySelectorAll("#add-caderno button"))
                  .map(b=>b.textContent.trim()),
    recado: document.getElementById("regra-repeticao").textContent
  };
  _ficha_em("add-caderno", "Frente e verso");
  OUT.dup_1 = _livro();
  // A MARCA VOLTOU A 1, entao o proximo caderno so sai duplicado se ela
  // for escolhida DE NOVO - e e isto que o teste seguinte prova: com
  // ela em 1, o bate-vira de 8 nao cabe nas 4 paginas que sobraram.
  OUT.repeticao_voltou = e.repeticao;
  OUT.bv_sem_marca_travado = Array.from(
    document.querySelectorAll("#add-caderno button"))
      .filter(b=>b.textContent.trim().indexOf("Bate-vira") === 0)[0].disabled;
  _ficha_em("add-caderno", "Personalizado");
  _ficha_em("repeticoes", "2×");
  _ficha_em("add-caderno", "Bate-vira");
  OUT.dup_2 = _livro();

  // ==================================================================
  // A GRADE SE CALCULA SOZINHA EM CADERNO - 21/09/2026
  // ==================================================================
  // Em flat-work os numeros continuam digitados (regra de 11/09); em
  // caderno a grade e calculada, porque ali ela nao e livre - a
  // dobradeira so faz potencias de 2.
  _ficha_em("processos", "FLAT-WORK");
  _por("pl", 148); _por("pa", 210); _por("vao", 5);
  _por("ncols", 3); _por("nrows", 3);
  OUT.flat_nao_calcula = {cols: e.cols, rows: e.rows, mw: contas().mw};

  // DOBRA NAO TEM VAO, E SO UM DOS MEIOS CORTA.
  // Peca de 148x210. Em flat-work, 4x2 leva 3 vaos na largura e 1 na
  // altura. Em caderno, quem corta depende do GIRO: com a peca EM PE a
  // lombada e o vinco entre as COLUNAS (vao zero) e as cabecas se
  // encontram entre as LINHAS (vao 5). Deitando, inverte.
  _ficha_em("giros", "0°");                      // em pe
  _por("ncols", 4); _por("nrows", 2);
  OUT.flat_4x2 = {mw: contas().mw, mh: contas().mh,
                  cw: contas().cw, cah: contas().cah};
  _ficha_em("processos", "CANOA");
  e.refazerGrade = false; e.cols = 4; e.rows = 2;
  ncols_.value = 4; nrows_.value = 2; montar();
  OUT.caderno_em_pe = {mw: contas().mw, mh: contas().mh,
                       cw: contas().cw, cah: contas().cah};
  _ficha_em("giros", "−90");                     // deitada
  e.refazerGrade = false; e.cols = 4; e.rows = 2;
  ncols_.value = 4; nrows_.value = 2; montar();
  OUT.caderno_deitada = {mw: contas().mw, mh: contas().mh,
                         cw: contas().cw, cah: contas().cah};
  _ficha_em("giros", "0°");

  // e trocar a CHAPA refaz a grade sozinha
  e.cadernos = []; e.refazerGrade = true;
  _ficha_em("chapas", "PM 52");
  OUT.canoa_pm52 = {cols: e.cols, rows: e.rows,
                    campo_cols: _campo("ncols"), campo_rows: _campo("nrows"),
                    regra: document.getElementById("regra-processo").textContent};
  _ficha_em("chapas", "SM 74");
  OUT.canoa_sm74 = {cols: e.cols, rows: e.rows};

  // DIGITOU NA MAO, O CALCULO PARA DE PISAR - ate o proximo clique de
  // chapa ou de processo, que sao o pedido de refazer tudo.
  _por("ncols", 2); _por("nrows", 2);
  OUT.na_mao_manda = {cols: e.cols, rows: e.rows};
  _por("vao", 6);                       // outro campo nao refaz a grade
  OUT.depois_de_outro_campo = {cols: e.cols, rows: e.rows};
  _ficha_em("chapas", "MOZP");          // este refaz, e de proposito
  OUT.a_chapa_refaz = {cols: e.cols, rows: e.rows};

  // O FORMATO TAMBEM REFAZ, e enche as paginas - pedido de 21/09/2026.
  // Na MOZP, que e chapa grande, o formato e que vai apertar a grade.
  // ESVAZIA, e nao poe zero: pôr "0" no campo E digitar, e a marca de
  // mao sobe. O estado que se quer aqui e "o operador ainda nao disse
  // nada", e isso e campo VAZIO.
  _por("npaginas", ""); e.paginas = 0; e.paginasNaMao = false;
  _por("formato", 2);
  OUT.formato2 = {cols: e.cols, rows: e.rows,
                  paginas: _campo("npaginas"),
                  cabe: contas().cabeFormato};
  _por("formato", 4);
  OUT.formato4 = {cols: e.cols, rows: e.rows,
                  paginas: _campo("npaginas"),
                  cabe: contas().cabeFormato};
  // digitou de proposito? o formato seguinte NAO apaga
  _por("npaginas", 8);
  _por("formato", 6);
  OUT.paginas_digitadas = {paginas: _campo("npaginas")};

  // voltando para flat-work, a grade fica como estava
  e.refazerGrade = true; e.cadernos = [];
  _ficha_em("processos", "CANOA");
  _ficha_em("chapas", "PM 52");

  // tirar o ultimo caderno destrava... e destrava para tras
  _ficha_em("processos", "CANOA");
  _por("npaginas", 12);
  e.refazerGrade = false; e.cols = 4; e.rows = 2; ncols_.value = 4; nrows_.value = 2; montar();
  _ficha_em("add-caderno", "Personalizado");
  _ficha_em("repeticoes", "2×");
  _ficha_em("add-caderno", "Frente e verso");
  _ficha_em("add-caderno", "Personalizado");
  _ficha_em("repeticoes", "2×");
  _ficha_em("add-caderno", "Bate-vira");
  const xs = document.querySelectorAll("#cadernos .tirar");
  OUT.x_do_meio_travado = xs.length > 1 ? xs[0].disabled : null;
  OUT.x_do_fim_livre = xs.length > 1 ? xs[xs.length-1].disabled : null;
}catch(err){ OUT.erro = String(err) + "\n" + (err && err.stack); }
const p = document.createElement("pre");
p.id = "RESULTADO";
p.textContent = JSON.stringify(OUT);
document.body.appendChild(p);
</script>
"""


# O ARQUIVO DE MENTIRA que a fila teria mandado. Os numeros sao de um
# caso real da AMERICA - peca 100x150 com 3 mm de sangria, duas paginas,
# colorida - e e por eles que se confere o pre-preenchimento: peca de
# CORTE nos campos (nao a do papel), CMYK na cor, frente-e-verso pelas
# duas paginas, e a PM 52 sugerida pela regra da casa.
DO_ARQUIVO = {
    "arquivo": "CONVITE MEETING.pdf",
    "largura": 106.0, "altura": 156.0,
    "corte_largura": 100.0, "corte_altura": 150.0,
    "corte_de": "da TrimBox declarada no arquivo",
    "tintas": ["C", "K", "M", "Y"], "cores": "CMYK", "peb": False,
    "paginas": 2, "tem_marca": True, "marca_no_pe": 11.9,
    "sangria": True, "sangria_mm": 3.0, "sangria_declarada": 3.0,
    "sangria_pela_tinta": 2.9, "sangria_divergem": False,
    "sangria_recado": "tem sangria", "erro": None,
}


def _dados():
    """As tabelas da casa, do config, com o arquivo de mentira dentro."""
    dados = montagem.dados_do_painel(None)
    dados["arquivo"] = dict(
        DO_ARQUIVO, sugestao=montagem.sugestoes_para(DO_ARQUIVO))
    return dados


def rodar():
    # SERVIDO, como o servidor serve - e nao lido cru. O painel nao abre
    # mais solto: sem as tabelas do config ele para e diz por onde entrar.
    pagina = servidor.pagina_do_painel(_dados())
    assert "</body>" in pagina, "a pagina mudou de forma: nao achei </body>"
    copia = pagina.replace("</body>", SONDA + "\n</body>")

    pasta = tempfile.mkdtemp(prefix="provar_painel_")
    alvo = os.path.join(pasta, "copia.html")
    io.open(alvo, "w", encoding="utf-8").write(copia)

    r = subprocess.run(
        [_edge(), "--headless=new", "--disable-gpu", "--no-sandbox",
         "--virtual-time-budget=4000", "--dump-dom",
         "--user-data-dir=" + os.path.join(pasta, "perfil"),
         "file:///" + alvo.replace("\\", "/")],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180)

    m = re.search(r'<pre id="RESULTADO">(.*?)</pre>', r.stdout, re.S)
    if not m:
        raise SystemExit("o painel nao respondeu.\n"
                         + (r.stderr or r.stdout)[:1500])
    bruto = (m.group(1).replace("&quot;", '"').replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">"))
    return json.loads(bruto)


CASOS = []



def caso(f):
    CASOS.append(f)
    return f


@caso
def o_verso_so_desabilita_em_so_frente(d):
    assert d["bate_vira"]["verso_desabilitado"] is False, "bate-vira travou o verso"
    assert d["so_frente"]["verso_desabilitado"] is True, "so-frente deixou o verso editavel"
    assert d["frente_verso"]["verso_desabilitado"] is False, "frente-e-verso travou o verso"


@caso
def desabilitado_ele_aparece_VAZIO(d):
    """Numero num campo morto continua enganando quem olha."""
    assert d["so_frente"]["verso_valor"] == "", \
        "o campo ficou com %r" % d["so_frente"]["verso_valor"]
    assert d["so_frente"]["caixa_apagada"] is True, "a caixa nao foi apagada"


@caso
def o_que_estava_no_verso_VOLTA(d):
    """Trocar de tipo para conferir nao pode custar o que se digitou."""
    assert d["voltou"]["verso_desabilitado"] is False
    assert d["voltou"]["verso_valor"] == "2", \
        "o verso voltou como %r, e era 2" % d["voltou"]["verso_valor"]


@caso
def a_ORDEM_nao_fala_de_verso_em_so_frente(d):
    """Era isto que saia no papel: 'imagens frente 8 verso 2'."""
    linha = [l for l in d["so_frente"]["ordem"].splitlines()
             if l.startswith("imagens")]
    assert linha, "nao achei a linha 'imagens' na ordem"
    assert "verso" not in linha[0], "a ordem ainda diz: %r" % linha[0]
    assert "frente 8" in linha[0], "a frente sumiu: %r" % linha[0]


@caso
def a_ordem_CONTINUA_falando_de_verso_quando_ha_verso(d):
    for chave in ("bate_vira", "frente_verso"):
        linha = [l for l in d[chave]["ordem"].splitlines()
                 if l.startswith("imagens")]
        assert linha and "verso" in linha[0], \
            "%s perdeu o verso da ordem: %r" % (chave, linha)


@caso
def a_frente_nunca_se_desabilita(d):
    for chave in ("bate_vira", "so_frente", "voltou", "frente_verso"):
        assert d[chave]["frente_desabilitado"] is False, \
            "%s desabilitou a FRENTE" % chave


# ----------------------------------------------------------------------
# O QUE A FILA MANDOU - o painel chega sabendo do arquivo
# ----------------------------------------------------------------------

@caso
def a_peca_vem_preenchida_com_a_medida_do_CORTE(d):
    """
    O campo daqui e a PECA e a sangria entra separada. Preenchido com a
    medida do PAPEL (106x156), a sangria seria contada duas vezes e a
    peca sairia 6 mm maior do que o cliente pediu.
    """
    a = d["ao_abrir"]
    assert float(a["peca_largura"]) == 100.0, \
        "largura veio %r, e o corte e 100" % a["peca_largura"]
    assert float(a["peca_altura"]) == 150.0, \
        "altura veio %r, e o corte e 150" % a["peca_altura"]


@caso
def a_maquina_vem_SUGERIDA_pela_regra_da_casa(d):
    """Peca de 150 mm e ate o formato 4: PM 52, pela regra do operador."""
    assert d["ao_abrir"]["chapa"].startswith("PM 52"), \
        "a chapa escolhida veio %r" % d["ao_abrir"]["chapa"]


@caso
def a_cor_e_o_tipo_vem_do_que_se_mediu(d):
    """
    CMYK porque as quatro tintas estao la; BATE-VIRA pelas duas paginas -
    e paginas nao tem campo proprio no painel.

    Bate-vira, e nao 'frente e verso': as duas poem frente e verso na
    chapa, e a diferenca e que o bate-vira usa UMA chapa partida ao meio.
    E e o que a FIA sabe montar - sugerir o outro era oferecer um caminho
    que falhava no clique do botao.
    """
    a = d["ao_abrir"]
    assert a["cor"] == "CMYK", "a cor veio %r" % a["cor"]
    assert a["tipo"] == "Bate-vira", "o tipo veio %r" % a["tipo"]


@caso
def a_sangria_que_a_peca_JA_TEM_e_a_que_vale(d):
    """
    A regra do vao vale para arte pelada. Esta peca chegou com 3 mm
    medidos, e sobrescrever isso pela regra mudaria a montagem de um
    arquivo que ja estava certo.
    """
    assert float(d["ao_abrir"]["sangria"]) == 3.0, \
        "a sangria veio %r" % d["ao_abrir"]["sangria"]


@caso
def a_faixa_do_arquivo_aparece_com_o_nome(d):
    a = d["ao_abrir"]
    assert a["faixa_escondida"] is False, "a faixa do arquivo nao apareceu"
    assert a["nome_na_tela"] == DO_ARQUIVO["arquivo"], \
        "a tela mostra %r" % a["nome_na_tela"]


@caso
def as_tabelas_da_casa_vieram_SERVIDAS(d):
    """
    O checkbox do ticket: a copia em JavaScript morreu. As chapas que
    aparecem na tela e a tabela de formatos tem de ser as do config -
    aqui se confere que sao as MESMAS, e nao parecidas.
    """
    a = d["ao_abrir"]
    do_config = montagem.chapas_da_casa()
    assert len(a["chapas_servidas"]) == len(do_config), \
        "a tela mostra %d chapas e o config tem %d" % (
            len(a["chapas_servidas"]), len(do_config))
    for c, na_tela in zip(do_config, a["chapas_servidas"]):
        assert c["rotulo"] in na_tela, \
            "esperava %r na ficha, veio %r" % (c["rotulo"], na_tela)
        assert "%d×%d" % (c["l"], c["a"]) in na_tela, \
            "a medida de %s nao bate: %r" % (c["rotulo"], na_tela)

    servido = json.loads(a["formato_4"])
    do_config_4 = montagem.formatos_da_casa()["4"]
    assert servido == do_config_4, \
        "o formato 4 do painel e %r e o do config e %r" % (servido,
                                                           do_config_4)


# ----------------------------------------------------------------------
# OS AVISOS - a razao de o painel existir
# ----------------------------------------------------------------------
# Ele deixou de escolher e passou a ler, desenhar e AVISAR. Servi-lo com
# as tabelas de fora nao pode ter custado nenhum desses avisos: eles
# dependem justamente dos numeros que agora vem do config.

@caso
def avisa_quando_NAO_CABE_NA_AREA_UTIL(d):
    a = d["nao_cabe_util"]
    assert "Não cabe" in a["veredito"], "o veredito diz: %r" % a["veredito"]
    assert "área útil" in a["veredito"], a["veredito"]
    assert "nao" in a["classe"], "a faixa nao ficou vermelha: %r" % a["classe"]


@caso
def avisa_quando_NAO_CABE_NO_FORMATO(d):
    """
    Area util e formato sao limites DIFERENTES - a chapa e a folha - e o
    aviso tem de dizer qual dos dois estourou.
    """
    a = d["nao_cabe_formato"]
    assert "Não cabe" in a["veredito"], "o veredito diz: %r" % a["veredito"]
    assert "no formato 4" in a["veredito"], a["veredito"]
    # a area util da CHAPA cabia, e o aviso nao pode acusar as duas. Nao
    # basta procurar 'area util': o recado do formato fala da area util
    # DA FOLHA, que e outra coisa - o que acusa a chapa e 'nao cabe NA
    # area util'.
    assert "não cabe na área útil" not in a["veredito"], \
        "acusou a area util da chapa tambem, e ela cabia: %r" % a["veredito"]


@caso
def avisa_a_CELULA_VAZIA(d):
    """
    Tres imagens numa grade de quatro: a que sobra vira branco na chapa,
    e quem esta montando tem de saber antes de gravar.
    """
    a = d["celula_vazia"]
    assert "vazia" in a["grade"], "a linha da grade diz: %r" % a["grade"]
    assert "1" in a["grade"], a["grade"]
    # E ISTO NAO E 'NAO CABE': a chapa esta bem, a montagem e que esta
    # com um buraco. Confundir os dois faria a pessoa trocar de chapa
    # para resolver uma celula vazia.
    assert "Cabe" in a["veredito"], "o veredito diz: %r" % a["veredito"]


# ----------------------------------------------------------------------
# O BOTAO MONTA DE VERDADE - a ordem que ele manda
# ----------------------------------------------------------------------

@caso
def o_botao_deixou_de_ser_COPIAR_TEXTO(d):
    """
    Ele gerava um texto para alguem copiar e levar para outro programa.
    Vindo pela fila, o arquivo ja esta escolhido e ele MONTA - quem
    montou termina o trabalho sozinho.
    """
    b = d["botao"]
    assert b["texto"] == "Montar", "o botao diz %r" % b["texto"]
    assert b["desabilitado"] is False, \
        "o botao ficou travado mesmo com o arquivo vindo da fila"
    assert b["seletor_escondido"] is True, \
        "o seletor de arquivo continua na tela - escolher outro ali " \
        "montaria um e registraria outro"


@caso
def a_ordem_leva_TUDO_que_a_tela_coletou(d):
    """
    A forma da ordem e o contrato da spec. Faltando um campo, o modulo
    monta com o que nao foi pedido.
    """
    o = d["ordem_objeto"]
    for campo in ("arquivo", "chapa", "imagens_frente", "imagens_verso",
                  "colunas", "linhas", "vao", "sangria", "formato", "tipo",
                  "quem", "maquina_trocada", "liberado_sem_caber"):
        assert campo in o, "a ordem nao leva '%s'" % campo

    assert o["arquivo"] == DO_ARQUIVO["arquivo"]
    assert o["quem"] == "Pedro"
    assert o["colunas"] == 2 and o["linhas"] == 2
    assert o["vao"] == 5 and o["sangria"] == 2.5
    assert o["formato"] == 4
    assert o["tipo"] == "bate-vira"
    assert o["liberado_sem_caber"] is False
    # o encontro e as tres marcas viajam junto: sem eles a chapa saia
    # diferente do desenho que a pessoa acabou de aprovar
    assert o["encontro"] in ("cabeca", "pe")
    assert o["marca_de_corte"] is True
    assert o["marca_de_registro"] is True
    assert o["escala_de_cor"] is True


@caso
def so_frente_manda_ZERO_no_verso(d):
    """
    A mesma licao da ordem em texto, que saia 'imagens frente 8 verso 2'
    numa montagem onde os dois versos nao tinham para onde ir.
    """
    o = d["ordem_objeto"]
    assert o["imagens_verso"] == 2, "no bate-vira o verso vale"
    # (o caso de 'so frente' esta na ordem em texto, caso acima)


@caso
def a_MAQUINA_TROCADA_fora_da_regra_vai_na_ordem(d):
    """
    A regra sugeriu a PM 52 e a pessoa escolheu a SM 74. Isso tem de
    chegar registrado - e fora do 'geralmente' que a proxima regra da
    casa nasce.
    """
    sem_troca = d["ordem_objeto"]["maquina_trocada"]
    assert sem_troca is None, \
        "montando na chapa sugerida, nao ha troca a registrar: %r" % sem_troca

    assert d["clicou_na_sm74"] is True, "nao achei a ficha da SM 74"
    com_troca = d["ordem_com_troca"]
    assert com_troca["chapa"] == "SM_74", \
        "a chapa da ordem ficou %r" % com_troca["chapa"]
    assert com_troca["maquina_trocada"], "a troca nao foi registrada"
    assert "PM_52" in com_troca["maquina_trocada"], \
        "a ordem nao diz o que a regra sugeria: %r" % com_troca["maquina_trocada"]


# ----------------------------------------------------------------------
# LIBERAR O QUE NAO CABE - com nome, e caindo a cada mudanca
# ----------------------------------------------------------------------

@caso
def o_que_nao_cabe_chega_TRAVADO_e_com_a_pergunta(d):
    """
    O aviso vem com a pergunta junto, e o botao so destranca com a
    resposta de gente. Destravado de saida, 'nao cabe' viraria enfeite.
    """
    a = d["antes_de_liberar"]
    assert "Não cabe" in a["aviso"], "o veredito diz: %r" % a["aviso"]
    assert a["pergunta_visivel"] is True, "a pergunta nao apareceu"
    assert a["marcado"] is False, "ja veio marcado"
    assert a["botao_travado"] is True, "o botao destravou sozinho"
    assert a["ordem"] is False


@caso
def o_aviso_diz_QUAL_DOS_DOIS_limites_estourou(d):
    """
    Area util e da CHAPA - o que a gravadora alcanca tirada a pinca.
    Formato e da FOLHA - o que a impressora pega. Sao limites diferentes
    e e facil confundir.
    """
    aviso = d["antes_de_liberar"]["aviso"]
    assert "área útil" in aviso, aviso
    assert "formato" in aviso, aviso


@caso
def LIBERADA_a_ordem_diz_que_foi_e_POR_QUEM(d):
    a = d["depois_de_liberar"]
    assert a["marcado"] is True
    assert a["botao_travado"] is False, "liberou e o botao continuou travado"
    assert a["ordem"] is True, "a ordem nao saiu marcada como liberada"

    texto = a["texto"]
    assert "NÃO CABE" in texto, texto[-300:]
    assert "liberada à mão por Pedro" in texto, \
        "a ordem nao diz por quem: %r" % texto[-300:]


@caso
def o_PODE_IR_cai_a_cada_mudanca(d):
    """
    Sem isto, um 'dar andamento' dado para uma montagem que estourava
    2 mm continuaria valendo depois de alguem trocar a chapa, o formato
    ou a peca - e o botao ficaria destrancado para uma montagem que
    ninguem aprovou.
    """
    a = d["depois_de_mexer"]
    assert a["marcado"] is False, "o 'pode ir' sobreviveu a uma mudanca"
    assert a["ordem"] is False
    assert a["botao_travado"] is True, "o botao continuou destravado"


@caso
def o_ENCONTRO_nao_sobrevive_ao_tipo_SEM_VERSO(d):
    """
    'Pé com pé' vale no bate-vira, onde as duas metades se encontram.
    Trocando para 'só frente' o seletor SOME da tela - e o valor
    continuava valendo: TODAS as peças iam a +90, a arte de cabeça para
    baixo na chapa inteira, sem seletor para desfazer.
    """
    assert d["pe_com_pe"]["ordem"] == "pe"
    assert d["pe_com_pe"]["giro"] == 90, \
        "pe com pe tinha de girar +90: %r" % d["pe_com_pe"]["giro"]

    depois = d["so_frente_depois_do_pe"]
    assert depois["ordem"] == "cabeca", \
        "a ordem levou %r num tipo sem verso" % depois["ordem"]
    assert depois["giro"] == -90, \
        "sem verso o giro e o canonico da celula: %r" % depois["giro"]


@caso
def MARCA_DESMARCADA_nao_tem_como_nao_caber(d):
    """
    A caixinha do corte manda de verdade desde que a ordem passou a
    leva-la ao motor. O veredito ficava vermelho - e travava o botao -
    por causa de marcas que nem seriam desenhadas.
    """
    assert d["com_marca"]["cabem"] is False, \
        "o caso nao foi armado: as marcas cabiam"
    assert "nao" in d["com_marca"]["classe"]

    assert d["sem_marca"]["cabem"] is True, \
        "desmarcada, a marca continuou 'nao cabendo'"
    assert d["sem_marca"]["na_ordem"] is False
    assert "nao" not in d["sem_marca"]["classe"], \
        "a faixa continuou vermelha: %r" % d["sem_marca"]["classe"]



@caso
def o_giro_decide_se_a_peca_DEITA_ou_fica_EM_PE(d):
    """A peca e 100 x 150. A ±90 a celula sai 150 x 100; a 0 e a 180,
    100 x 150 - como o arquivo e."""
    for k in ("giro_m90", "giro_p90"):
        c = d[k]
        assert c["empe"] is False, "%s devia deitar: %s" % (k, c)
        assert (c["cw"], c["cah"]) == (150, 100), "%s: %s" % (k, c)
    for k in ("giro_0", "giro_180"):
        c = d[k]
        assert c["empe"] is True, "%s devia ficar em pe: %s" % (k, c)
        assert (c["cw"], c["cah"]) == (100, 150), "%s: %s" % (k, c)


@caso
def a_peca_em_pe_MUDA_o_tamanho_da_montagem(d):
    """Era o defeito: a montagem deitada estourava e nao havia como
    pedir a em pe."""
    assert d["giro_m90"]["mw"] == 300 and d["giro_m90"]["mh"] == 200
    assert d["giro_0"]["mw"] == 200 and d["giro_0"]["mh"] == 300


@caso
def o_giro_VAI_NA_ORDEM_que_o_motor_recebe(d):
    """Sem isto a tela mostraria em pe e o motor deitaria assim mesmo."""
    for k, g in (("giro_m90", -90), ("giro_p90", 90),
                 ("giro_0", 0), ("giro_180", 180)):
        assert d[k]["na_ordem"] == g, "%s foi na ordem como %r" % (k, d[k]["na_ordem"])


@caso
def a_ordem_escrita_diz_EM_PE_ou_DEITADA(d):
    assert "EM PÉ" in d["giro_0"]["linha_peca"], d["giro_0"]["linha_peca"]
    assert "DEITADA" in d["giro_m90"]["linha_peca"], d["giro_m90"]["linha_peca"]


@caso
def o_bate_vira_com_a_peca_em_pe_e_LEGITIMO(d):
    """
    Eu avisava aqui que estava errado, e o AVISO e que estava.

    Em 18/09/2026 o operador mostrou o CHECK-LIST A4 em pe: bate-vira
    com a peca em pe e montagem normal - as duas metades ficam no MESMO
    sentido, porque a folha vira sobre o eixo VERTICAL e o que aponta
    para cima continua apontando para cima.
    """
    assert d["vira_em_pe"]["aviso"] is False, "voltou a avisar sem motivo"
    assert d["vira_deitada"]["aviso"] is False


@caso
def o_verso_do_BATE_VIRA_e_o_ESPELHO_e_nao_180(d):
    """
    A conta que o operador corrigiu: "o verso nao pode ser 180 graus,
    tem que ficar com 0 graus como a frente".

    Bate-vira VIRA sobre o eixo vertical, e isso e um espelho (-g).
    Frente-e-verso TOMBA, e ai sim vai a 180. Com ±90 as duas contas dao
    o MESMO numero, e foi por isso que o erro passou: enquanto a peca so
    deitava, nenhuma se distinguia da outra.
    """
    assert d["vira_em_pe"]["giro_verso"] == 0, \
        "frente a 0, o verso do bate-vira saiu %r" % d["vira_em_pe"]["giro_verso"]
    assert d["vira_deitada"]["giro_verso"] == 90, \
        "frente a -90, o verso saiu %r" % d["vira_deitada"]["giro_verso"]
    assert d["fv_em_pe"]["giro_verso"] == 180, \
        "frente-e-verso a 0 TOMBA e vai a 180, saiu %r" % d["fv_em_pe"]["giro_verso"]


def main():
    d = rodar()
    if "erro" in d:
        raise SystemExit("o painel deu erro:\n" + d["erro"])
    ruim = 0
    for f in CASOS:
        try:
            f(d)
            print("  ok   %s" % f.__name__.replace("_", " "))
        except AssertionError as e:
            ruim += 1
            print("  FALHOU  %s\n          %s" % (f.__name__, e))
    print("\n%d de %d" % (len(CASOS) - ruim, len(CASOS)))
    return 1 if ruim else 0


# ----------------------------------------------------------------------
# OS TRES PROCESSOS - 20/09/2026
# ----------------------------------------------------------------------

@caso
def FLAT_WORK_e_o_padrao_e_nao_muda_nada(d):
    """
    "a opcao flat-work sera a padrao, e onde montaremos a maioria dos
    arquivos" - o operador. Quem monta folheto o dia inteiro nao pode
    pagar pelo caderno de quem monta livro.
    """
    assert d["flat_work"]["bloco_escondido"] is True, \
        "o bloco do livro apareceu em flat-work"
    assert d["flat_work"]["objeto"]["livro"] is None, \
        "flat-work mandou livro na ordem: %r" % d["flat_work"]["objeto"]["livro"]
    assert "caderno" not in d["flat_work"]["ordem"].lower(), \
        "a ordem de flat-work fala de caderno"


@caso
def a_CANOA_abre_o_livro_e_pergunta_quanto_falta(d):
    assert d["canoa_vazia"]["bloco_escondido"] is False
    assert d["canoa_vazia"]["faltam"] == "12 de 12", \
        "o campo disse %r" % d["canoa_vazia"]["faltam"]
    assert d["canoa_vazia"]["travado"] is True, \
        "livro sem caderno nenhum destravou o botao"


@caso
def o_montador_SOMA_caderno_a_caderno(d):
    """
    "a partir do momento que eu for clicando, vai criando o caderno 1, o
    2 e assim por diante, ate o ultimo caderno" - o operador.
    """
    assert d["clicou_bv"] is True and d["clicou_fv"] is True, \
        "nao achei os botoes de acrescentar caderno"
    assert d["canoa_um"]["quantos"] == 1
    assert d["canoa_um"]["faltam"] == "8 de 12", \
        "depois do bate-vira faltavam %r" % d["canoa_um"]["faltam"]
    assert d["canoa_fecha"]["quantos"] == 2
    assert d["canoa_fecha"]["fecha"] is True
    assert d["canoa_fecha"]["faltam"] == "0 de 12"


@caso
def cada_tipo_de_caderno_come_o_que_deve(d):
    """
    Numa grade 2x2: o bate-vira parte a chapa ao meio e segura 4
    paginas numa chapa; o frente e verso segura 8, em duas chapas.
    """
    assert d["canoa_fecha"]["chapas"] == 3, \
        "o livro deu %r chapas, e 1 + 2 sao 3" % d["canoa_fecha"]["chapas"]


@caso
def a_CANOA_encaixa_e_o_HOTMELT_empilha(d):
    """
    A diferenca visivel entre os dois, no mesmo livro de 12 paginas com
    um caderno de 4 e um de 8:

        canoa    caderno 1 -> 1, 2, 11, 12   (o de fora leva as pontas)
        hotmelt  caderno 1 -> 1, 2, 3, 4     (empilhado, pedaco seguido)
    """
    canoa = d["canoa_fecha"]["paginas_por_caderno"]
    hot = d["hotmelt"]["paginas_por_caderno"]
    assert canoa[0] == [1, 2, 11, 12], "a canoa deu %r" % (canoa[0],)
    assert canoa[1] == [3, 4, 5, 6, 7, 8, 9, 10], "a canoa deu %r" % (canoa[1],)
    assert hot[0] == [1, 2, 3, 4], "o hotmelt deu %r" % (hot[0],)
    assert hot[1] == [5, 6, 7, 8, 9, 10, 11, 12], "o hotmelt deu %r" % (hot[1],)


@caso
def a_ETIQUETA_padrao_ja_vem_pronta_em_cada_caderno(d):
    """'CAD 01 BATE-VIRA', 'CAD 02 FRENTE', 'CAD 02 VERSO'."""
    nomes = d["canoa_fecha"]["cadernos"]
    assert nomes[0] == "CAD 01 BATE-VIRA", "o primeiro saiu %r" % nomes[0]
    assert nomes[1] == "CAD 02 FRENTE · CAD 02 VERSO", \
        "o segundo saiu %r" % nomes[1]


@caso
def o_que_o_montador_DIGITA_sai_em_TODOS_os_cadernos(d):
    """
    "um campo para eu preencher e sair em todos os cadernos... se eu
    acrescentar mais informacoes elas virao logo depois dessas padroes"
    """
    nomes = d["com_etiqueta"]["cadernos"]
    assert nomes[0] == "CAD 01 BATE-VIRA - REVISTA UNICIDADES - 20/09/2026", \
        "saiu %r" % nomes[0]
    for n in nomes:
        assert "REVISTA UNICIDADES" in n, "faltou em %r" % n
        assert n.startswith("CAD "), "o padrao nao veio na frente: %r" % n


@caso
def a_ORDEM_leva_o_livro_inteiro(d):
    """O papel que sai da tela tem de trazer cada chapa e o que ela leva."""
    o = d["com_etiqueta"]["ordem"]
    assert "processo  CANOA" in o, "a ordem nao diz o processo"
    assert "ENCAIXADOS" in o, "a ordem nao diz como os cadernos se juntam"
    assert "num PDF só" in o, "a ordem nao diz que sai tudo num PDF"
    assert "CAD 01 BATE-VIRA" in o and "CAD 02 VERSO" in o
    assert "livro 1-2, 11-12" in o, "a ordem nao traz as paginas do caderno"


@caso
def o_OBJETO_que_vai_para_a_FIA_leva_o_plano(d):
    livro = d["com_etiqueta"]["objeto"]["livro"]
    assert livro is not None
    assert livro["paginas"] == 12 and livro["fecha"] is True
    assert livro["encaixa"] is True, "canoa tem de ir como encaixada"
    assert len(livro["cadernos"]) == 2
    assert livro["cadernos"][0]["etiquetas"] == [
        "CAD 01 BATE-VIRA - REVISTA UNICIDADES - 20/09/2026"]
    assert d["com_etiqueta"]["objeto"]["processo"] == "canoa"
    assert (d["com_etiqueta"]["objeto"]["etiqueta"]
            == "REVISTA UNICIDADES - 20/09/2026")


@caso
def o_LIVRO_VAI_SEM_CONVERTER_em_imagem(d):
    """
    O padrao do livro e NAO converter, e a ordem tem de sair dizendo.

    Regra do operador, 21/09/2026: "no caso do livro as paginas nao
    serao convertidas em imagem, pq geralmente sao mais textos e fotos
    que nao dao problema". O "converter em imagem" da folha solta existe
    para fonte que falta, transparencia que achata errado e vetor que
    engasga o RIP - e num miolo o que nao da esse problema e justamente
    o que mais perde ao virar pixel.

    Caindo para True calado, o miolo sairia rasterizado a 800 dpi: mais
    de uma hora de maquina num livro de 228 paginas, e o texto pior.
    """
    livro = d["com_etiqueta"]["objeto"]["livro"]
    assert livro["em_imagem"] is False,         "o livro saiu marcado para converter sem ninguem ter pedido"


@caso
def LIVRO_QUE_NAO_FECHA_NAO_VAI(d):
    """
    E este aviso NAO tem 'dar andamento assim mesmo'. Os outros dois
    avisos do painel sao de MEDIDA - a montagem estourou por 2 mm, e
    quem monta pode saber de algo que a regra nao sabe. Este e de CONTA:
    pagina sem caderno e pagina que nao vai ser gravada.
    """
    assert d["canoa_vazia"]["travado"] is True
    assert d["canoa_um"]["travado"] is True, \
        "livro pela metade destravou o botao"
    assert "Faltam 8" in d["canoa_um"]["regra"], \
        "a tela nao disse quanto falta: %r" % d["canoa_um"]["regra"]


@caso
def so_o_ULTIMO_caderno_sai(d):
    """
    Tirar um do meio renumeraria todos os de baixo - o CAD 03 viraria
    CAD 02 -, e a etiqueta ja conferida na tela deixaria de ser a que
    vai na chapa.
    """
    assert d["x_do_meio_travado"] is True, "o X do meio estava livre"
    assert d["x_do_fim_livre"] is False, "o X do ultimo estava travado"




# ----------------------------------------------------------------------
# O CADERNO DUPLICADO - 21/09/2026
# ----------------------------------------------------------------------

@caso
def o_PERSONALIZADO_abre_a_repeticao(d):
    """
    "na opcao de personalizado, o que eu preciso e isso: caderno
    duplicado, caderno quadruplicado" - o operador.
    """
    assert d["abriu_pers"] is True, "nao achei o botao Personalizado"
    assert d["pers_visivel"] is True, "o bloco da repeticao nao apareceu"
    assert d["clicou_dup"] is True, "nao achei a ficha 2x"


@caso
def o_DUPLICADO_come_METADE_das_paginas(d):
    """Na mesma grade 4x2: frente e verso leva 16, duplicado leva 8."""
    normal = [r for r in d["grade_4x2"]["rotulos"] if r.startswith("Frente")][0]
    dobro = [r for r in d["com_duplicado"]["rotulos"]
             if r.startswith("Frente")][0]
    assert "+16 págs" in normal, "o normal dizia %r" % normal
    assert "+8 págs" in dobro, "o duplicado dizia %r" % dobro
    assert "duplicado" in dobro, "o botao nao avisa que vai duplicado"


@caso
def repetir_NAO_gasta_chapa_a_mais(d):
    """
    E a razao de o duplicado existir: a chapa ja ia sair. O que se evita
    e ela sair com celula vazia.
    """
    normal = [r for r in d["grade_4x2"]["rotulos"] if r.startswith("Frente")][0]
    dobro = [r for r in d["com_duplicado"]["rotulos"]
             if r.startswith("Frente")][0]
    assert "2 chapas" in normal and "2 chapas" in dobro, \
        "a conta de chapas mudou: %r -> %r" % (normal, dobro)


@caso
def a_marca_de_duplicar_VOLTA_A_1_depois_de_usada(d):
    """
    Duplicar e caso do ULTIMO caderno. Deixar a marca ligada faria o
    proximo sair duplicado sem ninguem pedir - e metade do livro sairia
    repetida, sem dar erro em lugar nenhum.
    """
    assert d["repeticao_voltou"] == 1, \
        "a repeticao ficou em %r" % d["repeticao_voltou"]


@caso
def o_caderno_duplicado_APARECE_como_duplicado(d):
    """Na lista e na ordem - quem roda tem de saber que sai repetido."""
    nomes = d["dup_1"]["cadernos"]
    linha = [c for c in d["dup_1"]["ordem"].splitlines() if "CAD 01" in c]
    assert d["dup_1"]["quantos"] == 1
    assert d["dup_1"]["objeto"]["livro"]["cadernos"][0]["repeticao"] == 2, \
        "a ordem nao leva a repeticao"
    assert linha and "DUPLICADO" in linha[0], \
        "a ordem escrita nao diz duplicado: %r" % linha


@caso
def o_duplicado_FECHA_o_livro_que_sobrava(d):
    """
    12 paginas numa grade 4x2: um frente e verso duplicado leva 8, e um
    bate-vira leva os 4 que faltam. A chapa sai cheia nos dois.
    """
    assert d["dup_2"]["fecha"] is True, "o livro nao fechou"
    assert d["dup_2"]["quantos"] == 2
    assert d["dup_2"]["travado"] is False, "fechou e o botao ficou travado"


@caso
def sem_a_marca_o_caderno_seguinte_NAO_sai_duplicado(d):
    """
    A prova do outro lado: com a marca de volta em 1, o bate-vira de 8
    paginas nao cabe nas 4 que sobraram - e o botao sai cinza. Se a
    marca ficasse ligada, ele caberia (duplicado leva 4) e metade do
    livro sairia repetida sem ninguem ter pedido.
    """
    assert d["bv_sem_marca_travado"] is True, \
        "o bate-vira de 8 entrou onde so cabiam 4"



# ----------------------------------------------------------------------
# A GRADE SE CALCULA SOZINHA EM CADERNO - 21/09/2026
# ----------------------------------------------------------------------

@caso
def em_FLAT_WORK_a_grade_continua_DIGITADA(d):
    """
    A regra de 11/09/2026 nao mudou onde ela nasceu: "a montagem e
    livre, me avise somente se nao couber". Uma grade de 3x3 e valida
    em flat-work, e o painel nao a corrige.
    """
    assert d["flat_nao_calcula"]["cols"] == 3, \
        "o painel mexeu nas colunas de flat-work: %r" % d["flat_nao_calcula"]
    assert d["flat_nao_calcula"]["rows"] == 3


@caso
def DOBRA_NAO_TEM_VAO(d):
    """
    A mesma grade de 4x2 mede MENOS em caderno, porque a dobra nao abre
    espaco - as pecas se encostam.

    Medido nas montagens da casa de agosto: os tres livros A4, o Guia
    Alto Paraiso e o Guia de Bolso saem com as pecas SE ENCOSTANDO.
    """
    flat, cad = d["flat_4x2"], d["caderno_em_pe"]
    assert cad["mw"] < flat["mw"], \
        "o caderno nao encolheu: %s contra %s" % (cad["mw"], flat["mw"])
    # Em caderno as quatro colunas viram DOIS PARES DE LOMBADA: dos
    # tres vaos de 5 sobra um so, o que separa um par do outro. Medido
    # nas marcas de corte do Sapientia e dos Canticos.
    assert abs((flat["mw"] - cad["mw"]) - 10) < 0.01, \
        "a largura devia perder dois vaos de 5: %s" % (flat["mw"] - cad["mw"])


@caso
def SO_UM_DOS_MEIOS_CORTA_e_o_GIRO_decide_qual(d):
    """
    "o vao do meio na horizontal, se as paginas estiverem de pe, fica a
    dobra, e o vao que vai a cabeca com cabeca fica com 5 - ou seja, 1
    dos meios tem que ter o corte duplo; se as paginas forem deitadas a
    ordem se inverte" - o operador, 21/09/2026.

    EM PE a lombada e o vinco entre as COLUNAS, e as cabecas se
    encontram entre as LINHAS. Entao a largura nao tem vao nenhum e a
    altura tem UM. Deitando a peca, inverte.
    """
    pe = d["caderno_em_pe"]
    de = d["caderno_deitada"]

    # EM PE, e medido no Sapientia e nos Canticos: quatro colunas sao
    # DOIS pares de lombada, com um corte so entre os pares -
    # 150 | 150 |5| 150 | 150. E as duas linhas cortam, porque ali as
    # cabecas se encontram.
    assert abs(pe["mw"] - (4*pe["cw"] + 5)) < 0.01, \
        "em pe as 4 colunas sao dois pares com UM corte: %r" % pe
    assert abs(pe["mh"] - (2*pe["cah"] + 5)) < 0.01, \
        "em pe as linhas cortam (cabeca com cabeca): %r" % pe

    # deitada: inverte - a lombada passa a ser o eixo das linhas
    assert abs(de["mw"] - (4*de["cw"] + 3*5)) < 0.01, \
        "deitada as colunas cortam todas: %r" % de
    assert abs(de["mh"] - 2*de["cah"]) < 0.01, \
        "deitada as duas linhas sao um par de lombada, sem corte: %r" % de


@caso
def TROCAR_A_CHAPA_refaz_a_grade(d):
    """
    "preciso que a montagem apareca nos layout, automaticamente quando
    eu clicar no tamanho da chapa" - o operador.
    """
    pm = d["canoa_pm52"]
    sm = d["canoa_sm74"]
    assert (pm["cols"], pm["rows"]) != (sm["cols"], sm["rows"]), \
        "a grade nao mudou ao trocar de chapa: %r e %r" % (pm, sm)
    assert pm["campo_cols"] == str(pm["cols"]), \
        "o campo na tela nao acompanhou: %r" % pm
    assert sm["cols"] * sm["rows"] >= pm["cols"] * pm["rows"], \
        "a chapa maior tinha de caber pelo menos o mesmo"


@caso
def a_tela_DIZ_quantas_paginas_cabem(d):
    """A conta que o operador pediu, em palavras, junto do processo."""
    r = d["canoa_pm52"]["regra"]
    assert "cabe uma grade de" in r, "a tela nao diz a grade: %r" % r
    assert "bate-vira" in r and "frente e verso" in r, \
        "a tela nao diz quantas paginas por vira: %r" % r


@caso
def quem_DIGITA_a_grade_manda_nela(d):
    """
    A mesma regra do sangriaNaMao: quem mexeu na mao sabe de algo que a
    conta nao sabe. Trocar a chapa depois disso nao pisa no que ele
    digitou.
    """
    assert (d["na_mao_manda"]["cols"], d["na_mao_manda"]["rows"]) == (2, 2), \
        "o calculo pisou na grade digitada: %r" % d["na_mao_manda"]

# A CHAMADA FICA NO FIM DO ARQUIVO, E E POR UM MOTIVO PAGO.
#
# Ela morava no meio, logo depois do main(). Os casos escritos ABAIXO
# dela nunca chegavam a se registrar: o modulo roda de cima para baixo,
# o main() ja tinha rodado, e o provador dizia "31 de 31" com os casos
# novos parados no arquivo, sem nenhum erro em lugar nenhum.
#
# E o mesmo defeito que a casa inteira persegue - a coisa que nao da
# erro e passa por certa. Com a chamada aqui embaixo, todo caso escrito
# no arquivo entra na conta.
@caso
def TROCAR_O_FORMATO_refaz_a_grade(d):
    """
    Pedido do operador em 21/09/2026: "quando eu colocar formato 2, vc
    automaticamente ja coloca o numero maximo de paginas que vai caber
    no formato, para nao ficar digitando na montagem".

    Ate ali so a CHAPA e o PROCESSO pediam a grade de novo; o formato
    era so limite no veredito. Escolhendo F2 o operador via o aviso de
    'nao cabe' em vez de ver a montagem que cabe.
    """
    f2, f4 = d["formato2"], d["formato4"]
    assert f2["cols"] and f2["rows"], "o formato 2 nao produziu grade"
    assert (f2["cols"], f2["rows"]) != (f4["cols"], f4["rows"]),         "F2 e F4 deram a MESMA grade - o formato nao entrou na conta"


@caso
def a_grade_do_formato_CABE_no_formato(d):
    """
    Propor o que nao serve e pior que nao propor: antes o calculo olhava
    so a chapa, e podia sugerir uma montagem que acendia o aviso
    vermelho no mesmo instante em que aparecia.
    """
    for chave in ("formato2", "formato4"):
        assert d[chave]["cabe"] is not False,             "%s: a grade sugerida NAO cabe no proprio formato" % chave


@caso
def as_PAGINAS_vem_preenchidas(d):
    """O que a geometria ja sabe, o operador nao digita."""
    for chave in ("formato2", "formato4"):
        n = int(d[chave]["paginas"] or 0)
        assert n > 0, "%s: as paginas nao foram preenchidas" % chave
        assert n % 4 == 0, (
            "%s: caderno tem de ser multiplo de 4, e veio %d" % (chave, n))


@caso
def o_que_foi_DIGITADO_nao_se_apaga(d):
    """
    Trocar de formato para conferir nao pode custar o que se digitou. E
    a mesma licao da grade, que so se recalcula por PEDIDO.
    """
    assert int(d["paginas_digitadas"]["paginas"] or 0) == 8,         "o formato apagou as paginas que o operador digitou"



if __name__ == "__main__":
    sys.exit(main())
