# -*- coding: utf-8 -*-
"""A sangria inventada: o que ela nunca pode fazer.

O caso de verdade - o flyer 15x21 com a sangria do designer - e arte de
cliente e nao vai para o git. Por isso os casos sinteticos aqui embaixo
guardam as REGRAS, e o teste do flyer roda so nesta maquina, quando o
arquivo esta na pasta.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ferramentas"))

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw          # noqa: E402

import sangrar                            # noqa: E402

DPI = 300
S = int(round(3.0 / 25.4 * DPI))          # 3 mm em pixels


def _arte(cor=(235, 232, 228), tam=(900, 1200)):
    return Image.new("RGB", tam, cor)


def test_o_corte_nao_muda_de_tamanho():
    """A regra que quase todo mundo quebra: sangria nao e ampliar."""
    art = _arte()
    dec = {b: ("chapado", "") for b in ("topo", "base", "esquerda", "direita")}
    nova = sangrar.sangrar_imagem(art, S, dec)
    assert nova.size == (art.size[0] + 2 * S, art.size[1] + 2 * S)
    # e a arte original continua la dentro, do tamanho que era, sem esticar
    miolo = nova.crop((S, S, S + art.size[0], S + art.size[1]))
    assert list(miolo.get_flattened_data()) == list(art.get_flattened_data())


def test_moldura_na_linha_de_corte_trava():
    """Fio parado no corte: espelhar duplicaria. Tem de chamar gente."""
    for espessura_mm in (0.5, 1.0, 2.0):
        art = _arte()
        t = max(1, int(espessura_mm / 25.4 * DPI))
        ImageDraw.Draw(art).rectangle(
            [0, 0, art.size[0] - 1, art.size[1] - 1], outline=(20, 20, 20), width=t)
        for borda in ("topo", "base", "esquerda", "direita"):
            tecnica, porque = sangrar.decidir(art, borda, S)
            assert tecnica == "olho", (espessura_mm, borda, tecnica, porque)


def test_cor_chapada_sai_exata():
    """Borda de cor parada: o resultado e igual, nao parecido."""
    art = _arte(cor=(12, 84, 160))
    dec = {b: sangrar.decidir(art, b, S)
           for b in ("topo", "base", "esquerda", "direita")}
    assert all(t == "chapado" for t, _ in dec.values()), dec
    nova = sangrar.sangrar_imagem(art, S, dec)
    assert nova.getpixel((1, 1)) == (12, 84, 160)
    assert nova.getpixel((nova.size[0] - 2, nova.size[1] - 2)) == (12, 84, 160)


def test_arte_que_acaba_em_branco_nao_inventa_nada():
    art = _arte(cor=(255, 255, 255))
    ImageDraw.Draw(art).ellipse([300, 400, 600, 700], fill=(200, 60, 40))
    for borda in ("topo", "base", "esquerda", "direita"):
        assert sangrar.decidir(art, borda, S)[0] == "branco"


def test_degrade_nao_trava_a_toa():
    """Foto que sangra de verdade: espelha, nao chama gente."""
    art = Image.new("RGB", (900, 1200))
    px = art.load()
    for y in range(1200):
        for x in range(900):
            px[x, y] = (120 + x // 12, 90 + y // 24, 140)
    for borda in ("topo", "base", "esquerda", "direita"):
        assert sangrar.decidir(art, borda, S)[0] == "espelho"


FLYER = os.path.join(os.path.dirname(__file__), "..", "ARQUIVOS TEMP PARA TESTES",
                     "Flyer Semana do Cliente_15x21 (1).pdf")


@pytest.mark.skipif(not os.path.exists(FLYER),
                    reason="arte de cliente; nao vai para o git")
def test_flyer_contra_a_sangria_do_designer():
    """
    O gabarito. O flyer tem 3 mm de sangria feita por gente: rasteriza
    com ela, joga fora, manda a FIA reinventar, e cobra o que importa -
    onde o designer pos TINTA, a FIA nao pode ter deixado PAPEL.

    Comparar a COR com a do designer nao serve: ele pode desenhar na
    sangria coisa que nem sai no impresso, porque a guilhotina come.
    Fiapo branco, sim, aparece.
    """
    BRANCO = 246
    for pagina in (1, 2):
        real = sangrar.rasterizar(FLYER, pagina, DPI, "BleedBox")
        L, A = real.size
        sem = real.crop((S, S, L - S, A - S))        # chegando pelado
        dec = {b: sangrar.decidir(sem, b, S)
               for b in ("topo", "base", "esquerda", "direita")}
        inv = sangrar.sangrar_imagem(sem, S, dec)
        assert inv.size == real.size

        faixas = {"topo": (0, 0, L, S), "base": (0, A - S, L, A),
                  "esquerda": (0, 0, S, A), "direita": (L - S, 0, L, A)}
        for borda, cx in faixas.items():
            dr = list(real.crop(cx).convert("L").get_flattened_data())
            di = list(inv.crop(cx).convert("L").get_flattened_data())
            fiapo = sum(1 for vr, vi in zip(dr, di)
                        if vr <= BRANCO and vi > BRANCO)
            com_tinta = sum(1 for v in dr if v <= BRANCO)
            assert com_tinta, (pagina, borda, "faixa sem tinta nenhuma?")
            assert fiapo == 0, (
                "pagina %d, borda %s: a FIA deixou papel em %d dos %d pixels "
                "onde o designer pos tinta" % (pagina, borda, fiapo, com_tinta))
