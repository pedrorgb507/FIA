#!/usr/bin/env bash
# ---------------------------------------------------------------------
# Traz do GitHub o que a outra maquina fez.
#
# Roda sozinho, pelo hook SessionStart do Claude Code, toda vez que uma
# sessao comeca. E o par do salvar_no_github.sh: aquele empurra no fim,
# este puxa no comeco. Sem os dois, sincronizar e mao unica - foi assim
# que esta maquina ficou 124 commits atras da Finart sem ninguem notar.
#
# O que ele NAO faz: resolver divergencia. Se o rebase bater de frente,
# ele desfaz e chama gente. Juntar historico e decisao de quem sabe o
# que cada lado quis dizer.
#
# Nunca derruba a sessao: qualquer erro vira aviso e o hook sai com 0.
# ---------------------------------------------------------------------

cd "$(dirname "$0")/.." 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

aviso() {
    # o Claude Code le esta linha e mostra a mensagem para o operador
    printf '{"systemMessage":"%s","suppressOutput":true}\n' "$1"
    exit 0
}

git fetch origin >/dev/null 2>&1 || aviso "GitHub: nao consegui consultar o remoto. Sem rede ou sem credencial? Trabalhando com o que esta no disco."

atras=$(git rev-list --count 'HEAD..@{u}' 2>/dev/null) || atras=0
[ "${atras:-0}" -eq 0 ] && exit 0

# trabalho sem commit no disco: o rebase recusaria, e mexer no que nao
# esta salvo e a forma mais facil de perder o dia de alguem
sujos=$(git status --porcelain 2>/dev/null | grep -c .)
if [ "${sujos:-0}" -gt 0 ]; then
    aviso "GitHub tem $atras commit(s) novos, mas ha $sujos arquivo(s) alterado(s) sem commit aqui. Nao puxei: commite antes."
fi

if git rebase FETCH_HEAD >/dev/null 2>&1; then
    aviso "GitHub: $atras commit(s) trazidos da outra maquina."
fi

# bateu de frente. Volta ao estado anterior e passa a bola.
git rebase --abort >/dev/null 2>&1
aviso "GitHub: os $atras commit(s) de la CONFLITAM com o que esta aqui. Desfiz e nao mexi em nada - me peca para resolver."
