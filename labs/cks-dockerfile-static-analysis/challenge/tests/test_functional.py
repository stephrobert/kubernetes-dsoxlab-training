"""test_functional.py : cks-dockerfile-static-analysis

Une seule affirmation, qui lit le fichier du nœud et relance l'analyse,
jamais les commandes tapées.

Le dernier test identifie les constats par leur NUMÉRO, et non par un total.
Ce choix est le cœur du lab : Trivy ajoute des règles à chaque version, et un
test qui exigerait « zéro constat » deviendrait rouge tout seul le jour où une
nouvelle règle sortirait, sans que le Dockerfile ait changé d'une ligne. Le
catalogue annoncerait une régression qui n'existe pas.

Les cinq numéros, eux, désignent ce que le cahier des charges demandait de
corriger, et ils resteront vrais.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

DOCKERFILE = "/root/inventaire/Dockerfile"
REPERTOIRE = "/root/inventaire"
#: Les cinq constats que l'analyse fait sur le Dockerfile de départ, mesurés
#: le 2026-09-16 avec Trivy 0.74.0.
CONSTATS_DU_DEPART = {
    "DS-0001": "le tag flottant « latest »",
    "DS-0002": "l'image tourne en root",
    "DS-0004": "le port 22 est exposé",
    "DS-0026": "aucun HEALTHCHECK",
    "DS-0029": "apt-get sans --no-install-recommends",
}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _analyse(host) -> set[str]:
    """Relance l'analyse et rend les identifiants des constats.

    L'analyse est REJOUÉE ici, et non lue dans un rapport que le candidat
    aurait laissé : un rapport s'édite, une analyse qui tourne sous nos yeux
    ne s'édite pas.
    """
    res = host.run(f"sudo trivy config --quiet --format json {REPERTOIRE} 2>/dev/null")
    assert res.rc == 0 and res.stdout.strip(), (
        "Trivy n'a pas pu analyser le répertoire de l'application. L'outil est "
        f"posé par le setup et s'appelle sans préfixe. Sortie : {res.stderr.strip()[:300]}"
    )
    rapport = json.loads(res.stdout)
    return {
        str(m.get("ID"))
        for r in rapport.get("Results") or []
        for m in r.get("Misconfigurations") or []
    }


# ----------------------------------------------------------------------
# LE test, et le seul : les cinq constats ont disparu.
# ----------------------------------------------------------------------
def test_les_cinq_constats_ont_disparu(host):
    """L'analyse est rejouée, et les constats sont nommés par leur numéro.

    Un test qui exigerait « zéro constat » deviendrait rouge tout seul le jour
    où Trivy ajouterait une règle, sans que le Dockerfile ait changé. Les cinq
    numéros, eux, désignent exactement ce qui était demandé.
    """
    # Deux vérifications qui n'ont PAS de test à elles, parce qu'elles sont
    # vraies avant le travail comme après : le Dockerfile existe, et il part
    # de Node pour lancer server.js. Un test toujours vrai ne mesure rien, et
    # la validation a rendu ce lab ROUGE pour cette raison. Ici elles gardent
    # tout leur sens : elles interdisent de faire taire l'analyse en
    # supprimant le fichier, ou en changeant d'application.
    res = host.run(f"sudo cat {DOCKERFILE}")
    assert res.rc == 0 and res.stdout.strip(), (
        f"Aucun Dockerfile lisible en {DOCKERFILE}. Le cahier des charges "
        "demande de le corriger, pas de le faire disparaître : une analyse qui "
        "n'a rien à analyser ne reproche rien."
    )
    contenu = res.stdout
    assert "node" in contenu.lower() and "server.js" in contenu, (
        "Le Dockerfile ne part plus d'une image Node ou ne lance plus "
        "server.js. Il fallait corriger les constats, pas changer "
        "l'application."
    )

    restants = _analyse(host) & set(CONSTATS_DU_DEPART)
    assert not restants, (
        "L'analyse reproche encore :\n  "
        + "\n  ".join(f"{i} : {CONSTATS_DU_DEPART[i]}" for i in sorted(restants))
        + "\n\nChaque constat porte une section `Resolution` dans la sortie de "
        "`trivy config` : elle dit quoi écrire."
    )
