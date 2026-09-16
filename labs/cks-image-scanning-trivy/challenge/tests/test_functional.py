"""test_functional.py : cks-image-scanning-trivy

Deux affirmations qui lisent l'état du CLUSTER et interrogent l'outil sur le
nœud, jamais les commandes tapées.

Le dernier test scanne DEUX images, celle d'origine et celle que le candidat a
mise en production, et exige strictement moins de failles critiques dans la
seconde. Ce choix de mesure relative est le cœur du lab, et il vaut d'être
expliqué.

Un seuil fixe, « moins de N failles critiques », serait faux dès la semaine
suivante : la base de vulnérabilités s'enrichit tous les jours, et une image
irréprochable aujourd'hui compte des failles demain sans avoir changé d'un
octet. Un test bâti sur un seuil deviendrait rouge tout seul, et le catalogue
annoncerait une régression qui n'existe pas.

Comparer les deux images, elle, reste vraie dans le temps : quelle que soit la
base du jour, une image de 2021 en portera toujours plus qu'une image récente,
puisque les deux sont mesurées avec la même base, au même instant.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "chaine-appro"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
DEPLOIEMENT = "web"
IMAGE_ORIGINE = "nginx:1.21"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _deploiement(host) -> dict:
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT} -o json"
    )
    assert rc == 0 and sortie, (
        f"Le Deployment {DEPLOIEMENT} n'existe plus dans {NAMESPACE}. Il fallait "
        f"changer son image, pas le remplacer. Sortie : {diagnostic}"
    )
    return json.loads(sortie)


def _critiques(host, image: str) -> int:
    """Le nombre de failles CRITICAL que Trivy trouve dans une image.

    Le scan se fait sur le NŒUD, avec la base que le setup a déjà téléchargée.
    Un scan qui échoue n'est pas compté comme zéro : ce serait conclure qu'une
    image est saine parce qu'on n'a pas su la lire.
    """
    res = host.run(
        f"sudo trivy image --quiet --scanners vuln --severity CRITICAL "
        f"--format json {image} 2>/dev/null"
    )
    assert res.rc == 0 and res.stdout.strip(), (
        f"Trivy n'a pas pu analyser {image} sur le nœud. L'outil est posé par "
        f"le setup et s'appelle sans préfixe. Sortie : {res.stderr.strip()[:300]}"
    )
    rapport = json.loads(res.stdout)
    return sum(len(r.get("Vulnerabilities") or []) for r in rapport.get("Results") or [])


# ----------------------------------------------------------------------
# 1. L'image de production a changé.
# ----------------------------------------------------------------------
def test_l_image_de_production_n_est_plus_celle_d_origine(host):
    image = _deploiement(host)["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image != IMAGE_ORIGINE, (
        f"Le Deployment tourne toujours sur {IMAGE_ORIGINE}. Analyser une image "
        "sans la remplacer ne réduit aucune surface d'attaque : le rapport "
        "d'analyse n'est pas le travail, il le justifie."
    )
    assert image.split(":")[0].split("/")[-1] == "nginx", (
        f"L'image est devenue « {image} ». Le cahier des charges demande de "
        "mettre à jour nginx, pas de changer d'application."
    )


# ----------------------------------------------------------------------
# 2. LE test : la nouvelle image porte strictement moins de failles.
# ----------------------------------------------------------------------
def test_la_nouvelle_image_porte_moins_de_failles_critiques(host):
    """Les deux images sont scannées MAINTENANT, avec la même base.

    C'est ce qui rend la mesure honnête et durable. Elle ne dit pas « cette
    image est sûre », affirmation qu'aucun outil ne peut tenir, mais « ce
    remplacement réduit l'exposition », qui est exactement ce que le cahier des
    charges demandait.
    """
    deploiement = _deploiement(host)
    image = deploiement["spec"]["template"]["spec"]["containers"][0]["image"]

    # La santé du déploiement n'a pas de test à elle : « deux exemplaires
    # prêts » est vrai AVANT le travail comme après, et un test toujours vrai
    # ne mesure rien. La validation l'a rendu ROUGE pour cette raison. Ici la
    # même assertion a du sens, parce qu'elle ne peut être atteinte qu'après
    # un remplacement d'image qui n'a rien cassé.
    prets = deploiement.get("status", {}).get("readyReplicas", 0)
    assert prets == 2, (
        f"{prets} exemplaire(s) sur 2 sont prêts après le changement d'image. "
        "Une image plus récente peut changer de port d'écoute ou d'utilisateur "
        "par défaut : regardez les events et les logs du Pod."
    )

    avant = _critiques(host, IMAGE_ORIGINE)
    apres = _critiques(host, image)

    assert avant > 0, (
        f"Trivy ne trouve aucune faille critique dans {IMAGE_ORIGINE}, ce qui "
        "est inattendu pour une image de 2021. La base de vulnérabilités est "
        "peut-être absente ou tronquée : le setup la télécharge, vérifiez qu'il "
        "a bien tourné."
    )
    assert apres < avant, (
        f"L'image choisie, {image}, porte {apres} faille(s) critique(s), contre "
        f"{avant} pour {IMAGE_ORIGINE}. Le remplacement ne réduit donc pas "
        "l'exposition. Scannez plusieurs candidates AVANT de déployer : une "
        "image récente n'est pas toujours celle qui porte le moins, et les "
        "variantes alpine en portent en général beaucoup moins que les "
        "variantes basées sur Debian."
    )
