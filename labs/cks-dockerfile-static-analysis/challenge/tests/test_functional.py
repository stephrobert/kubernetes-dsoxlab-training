"""test_functional.py : cks-dockerfile-static-analysis

Cinq affirmations, une par constat, qui lisent le fichier du nœud et relancent
l'analyse, jamais les commandes tapées.

Chaque test identifie son constat par leur NUMÉRO, et non par un total.
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

from conftest import lab_host, lab_target_host, message

DOCKERFILE = "/root/inventaire/Dockerfile"
REPERTOIRE = "/root/inventaire"
#: Les cinq constats que l'analyse fait sur le Dockerfile de départ, mesurés
#: le 2026-09-16 avec Trivy 0.74.0.
CONSTATS_DU_DEPART = {
    "DS-0001": ("the floating \"latest\" tag", "le tag flottant « latest »"),
    "DS-0002": ("the image runs as root", "l'image tourne en root"),
    "DS-0004": ("port 22 is exposed", "le port 22 est exposé"),
    "DS-0026": ("no HEALTHCHECK", "aucun HEALTHCHECK"),
    "DS-0029": ("apt-get without --no-install-recommends", "apt-get sans --no-install-recommends"),
}
#: L'analyse coûte plusieurs secondes : elle tourne une fois pour les cinq
#: tests. Ce n'est pas une fixture, pour qu'un échec de l'outil soit un ÉCHEC
#: du test et non une erreur de préparation.
_ANALYSE: dict[str, set[str]] = {}


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
    assert res.rc == 0 and res.stdout.strip(), message(
        en="Trivy could not analyse the application's directory. The tool is "
        f"installed by setup and is called without a prefix. Output: {res.stderr.strip()[:300]}",
        fr="Trivy n'a pas pu analyser le répertoire de l'application. L'outil est "
        f"posé par le setup et s'appelle sans préfixe. Sortie : {res.stderr.strip()[:300]}",
    )
    rapport = json.loads(res.stdout)
    return {
        str(m.get("ID"))
        for r in rapport.get("Results") or []
        for m in r.get("Misconfigurations") or []
    }


def _constats_restants(host) -> set[str]:
    """Les constats du départ que l'analyse rejouée fait encore.

    Deux vérifications précèdent l'analyse et n'ont PAS de test à elles, parce
    qu'elles sont vraies avant le travail comme après : le Dockerfile existe,
    et il part de Node pour lancer server.js. Un test toujours vrai ne mesure
    rien, et la validation a rendu ce lab ROUGE pour cette raison. Ici elles
    gardent tout leur sens : elles interdisent de faire taire l'analyse en
    supprimant le fichier, ou en changeant d'application.
    """
    res = host.run(f"sudo cat {DOCKERFILE}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No readable Dockerfile at {DOCKERFILE}. The specification "
        "asks for it to be fixed, not to be made to disappear: an analysis that "
        "has nothing to analyse holds nothing against you.",
        fr=f"Aucun Dockerfile lisible en {DOCKERFILE}. Le cahier des charges "
        "demande de le corriger, pas de le faire disparaître : une analyse qui "
        "n'a rien à analyser ne reproche rien.",
    )
    contenu = res.stdout
    assert "node" in contenu.lower() and "server.js" in contenu, message(
        en="The Dockerfile no longer starts from a Node image or no longer runs "
        "server.js. The findings had to be fixed, not the "
        "application changed.",
        fr="Le Dockerfile ne part plus d'une image Node ou ne lance plus "
        "server.js. Il fallait corriger les constats, pas changer "
        "l'application.",
    )
    if contenu not in _ANALYSE:
        _ANALYSE[contenu] = _analyse(host)
    return _ANALYSE[contenu] & set(CONSTATS_DU_DEPART)


def _corrige(host, ident: str) -> None:
    """L'analyse est rejouée, et le constat est nommé par son numéro.

    Un test qui exigerait « zéro constat » deviendrait rouge tout seul le jour
    où Trivy ajouterait une règle, sans que le Dockerfile ait changé. Le
    numéro, lui, désigne exactement ce qui était demandé.
    """
    en, fr = CONSTATS_DU_DEPART[ident]
    assert ident not in _constats_restants(host), message(
        en=f"The analysis still reports {ident}: {en}. The finding carries a "
        "`Resolution` section in the output of `trivy config`: it says what to write.",
        fr=f"L'analyse reproche encore {ident} : {fr}. Le constat porte une "
        "section `Resolution` dans la sortie de `trivy config` : elle dit quoi écrire.",
    )


# ----------------------------------------------------------------------
# 1. L'image de base est épinglée (DS-0001).
# ----------------------------------------------------------------------
def test_le_tag_latest_a_disparu(host):
    _corrige(host, "DS-0001")


# ----------------------------------------------------------------------
# 2. L'image ne tourne plus en root (DS-0002).
# ----------------------------------------------------------------------
def test_l_image_ne_tourne_plus_en_root(host):
    _corrige(host, "DS-0002")


# ----------------------------------------------------------------------
# 3. Le port 22 n'est plus exposé (DS-0004).
# ----------------------------------------------------------------------
def test_le_port_22_n_est_plus_expose(host):
    _corrige(host, "DS-0004")


# ----------------------------------------------------------------------
# 4. Un HEALTHCHECK est déclaré (DS-0026).
# ----------------------------------------------------------------------
def test_un_healthcheck_est_declare(host):
    _corrige(host, "DS-0026")


# ----------------------------------------------------------------------
# 5. apt-get n'installe plus les paquets recommandés (DS-0029).
# ----------------------------------------------------------------------
def test_apt_get_n_installe_plus_les_recommandations(host):
    _corrige(host, "DS-0029")
