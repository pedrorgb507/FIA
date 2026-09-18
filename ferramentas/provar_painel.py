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
function _ficha(texto){
  const bs = document.querySelectorAll("#tipos button");
  for(const b of bs) if(b.textContent.trim().indexOf(texto) === 0){ b.click(); return true; }
  return false;
}
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
    """CMYK porque as quatro tintas estao la; frente e verso pelas duas
    paginas - e paginas nao tem campo proprio no painel."""
    a = d["ao_abrir"]
    assert a["cor"] == "CMYK", "a cor veio %r" % a["cor"]
    assert a["tipo"] == "Frente e verso", "o tipo veio %r" % a["tipo"]


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


if __name__ == "__main__":
    sys.exit(main())
