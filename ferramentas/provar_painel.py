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
}catch(err){ OUT.erro = String(err) + "\n" + (err && err.stack); }
const p = document.createElement("pre");
p.id = "RESULTADO";
p.textContent = JSON.stringify(OUT);
document.body.appendChild(p);
</script>
"""


def rodar():
    pagina = io.open(PAINEL, encoding="utf-8").read()
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
