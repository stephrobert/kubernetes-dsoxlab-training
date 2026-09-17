"""Aucun `jsonpath` d'un test de lab ne porte d'accolade doublée.

Une accolade doublée est la marque d'une f-string : `f"{{x}}"` rend `{x}`. Dans
une chaîne ORDINAIRE, elle reste telle quelle, et c'est toujours une erreur
quand elle part vers `kubectl -o jsonpath` :

    f"… -o jsonpath='{{.status.phase}}'"   # rend {.status.phase}, correct
    "… -o jsonpath='{{.status.phase}}'"    # rend {{.status.phase}}, invalide

Mesuré le 2026-09-17, et cela a coûté deux cycles de validation. kubectl ne
proteste pas contre un jsonpath de cette forme : il rend une chaîne VIDE. Le
test du lab lisait donc « aucun exemplaire prêt » et accusait l'application
d'être tombée, alors que le défaut était dans la commande.

Le piège vient de l'écriture des labs par générateur : ces fichiers sont
produits depuis une f-string, et le nombre d'accolades à écrire dépend de si la
ligne PRODUITE est elle-même une f-string. Rien ne le signale à la relecture,
les deux formes se ressemblant trait pour trait.

## Pourquoi on lit l'AST plutôt que le texte

Parce que l'analyseur a DÉJÀ résolu l'échappement. Mesuré le même jour sur les
trois formes :

| écriture | valeur du morceau après analyse |
|---|---|
| `f"… '{{.status.phase}}'"` | `… '{.status.phase}'` |
| `"… '{{.status.phase}}'"` | `… '{{.status.phase}}'` |
| `f"…{X} " "… '{{.status.phase}}'"` | `… '{{.status.phase}}'` |

La troisième est le cas réel : une f-string et une chaîne ordinaire
CONCATÉNÉES. Python en fait un seul `JoinedStr`, mais chaque littéral garde ses
propres règles, et la partie ordinaire garde ses doubles accolades. Il ne faut
donc surtout pas écarter les morceaux d'un `JoinedStr` : une première version
de ce test le faisait, et laissait passer précisément le défaut qu'il visait.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent
TESTS_DE_LABS = sorted(RACINE.glob("labs/*/challenge/tests/*.py"))

#: On ne signale QUE le jsonpath, et non toute accolade doublée.
#:
#: Éprouvé le 2026-09-17 : la forme large produit un faux positif sur un JSON
#: passé à `kubectl --overrides`, dont les accolades fermantes sont
#: légitimement doublées :
#:
#:     '{"spec":{"containers":[{"name":"x","securityContext":{…}}]}}'
#:
#: Ce lab est validé et la chaîne est juste. Le défaut mesuré porte sur le seul
#: jsonpath, où une accolade doublée est toujours une erreur.
MOTIF_FAUTIF = "jsonpath='{{"


@pytest.mark.parametrize(
    "fichier", TESTS_DE_LABS, ids=lambda p: str(p.relative_to(RACINE))
)
def test_pas_de_jsonpath_a_accolade_doublee(fichier: pathlib.Path) -> None:
    arbre = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
    fautives = [
        (noeud.lineno, noeud.value)
        for noeud in ast.walk(arbre)
        if isinstance(noeud, ast.Constant)
        and isinstance(noeud.value, str)
        and MOTIF_FAUTIF in noeud.value
    ]
    assert not fautives, (
        f"{fichier.relative_to(RACINE)} envoie un jsonpath à accolade doublée "
        "à kubectl :\n"
        + "\n".join(f"  ligne {ligne} : {valeur!r}" for ligne, valeur in fautives)
        + "\n\nCette chaîne n'est pas une f-string, ou bien elle est CONCATÉNÉE "
        "à une f-string voisine sans porter elle-même le préfixe. Ses « {{ » "
        "restent donc « {{ », et kubectl rend une chaîne VIDE sans message "
        "d'erreur : le test accuse alors le lab d'un défaut qui est dans la "
        "commande. Écrivez une seule accolade, ou mettez le préfixe f sur CETTE "
        "ligne."
    )
