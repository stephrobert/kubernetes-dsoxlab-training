"""test_functional.py : ckad-volumes-partage-entre-conteneurs

Deux affirmations qui lisent l'état réel des conteneurs, jamais les commandes
tapées.

Le dernier test exerce LES DEUX CÔTÉS, et le second est celui qui compte : un
candidat qui aurait monté le volume sur la RACINE des deux conteneurs, ou qui
aurait fait écrire le producteur ailleurs, ferait passer la première moitié
sans avoir compris ce qu'un volume partage. On écrit donc un fichier HORS du
volume et on vérifie qu'il ne traverse pas.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "journalisation"
POD = "collecteur"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CHEMIN = "/var/trace/messages"
HORS_VOLUME = "/var/hors-volume"

# Kubernetes PROJETTE de lui-même le jeton du ServiceAccount dans chaque
# conteneur, sous un volume nommé `kube-api-access-xxxxx`. Un Pod qui ne
# déclare aucun volume en a donc un, monté des deux côtés.
#
# Mesuré le 2026-09-17, et c'est le validateur qui l'a trouvé : sans ce
# filtre, le premier test passait AVANT le travail, l'intersection des volumes
# montés par les deux conteneurs n'étant jamais vide.
VOLUME_AUTOMATIQUE = "kube-api-access-"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _dans(host, conteneur: str, commande: str):
    return _kubectl(
        host,
        f"-n {NAMESPACE} exec {POD} -c {conteneur} --request-timeout=30s "
        f"-- sh -c '{commande}'",
    )


# ----------------------------------------------------------------------
# 1. Un volume existe, et les deux conteneurs le montent.
# ----------------------------------------------------------------------
def test_un_volume_est_monte_dans_les_deux_conteneurs(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable. Deux conteneurs peuvent monter
    DEUX volumes différents du même Pod et ne rien partager du tout."""
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert rc == 0 and sortie, (
        f"Le Pod {POD} est introuvable dans {NAMESPACE}. Le setup l'avait "
        f"posé : il doit être recréé sous le même nom. {diagnostic}"
    )
    spec = json.loads(sortie)["spec"]
    volumes = {
        v["name"] for v in spec.get("volumes", [])
        if not v["name"].startswith(VOLUME_AUTOMATIQUE)
    }
    assert volumes, (
        f"Le Pod {POD} ne déclare aucun volume, en dehors de celui que "
        "Kubernetes projette lui-même pour le jeton du ServiceAccount. Deux "
        "conteneurs d'un même Pod "
        "partagent le réseau et peuvent partager des volumes, mais JAMAIS leur "
        "système de fichiers : chacun garde celui de son image."
    )

    montes = {}
    for c in spec.get("containers", []):
        montes[c["name"]] = {
            m["name"] for m in c.get("volumeMounts", [])
            if m["name"] in volumes
        }
    communs = set.intersection(*montes.values()) if montes else set()
    assert communs, (
        "Les deux conteneurs ne montent aucun volume EN COMMUN : "
        f"{ {k: sorted(v) for k, v in montes.items()} }. Monter deux volumes "
        "différents, un par conteneur, ne partage rien : c'est le même nom de "
        "volume qui doit apparaître des deux côtés."
    )


# ----------------------------------------------------------------------
# 2. LE test : ce qui est dans le volume passe, ce qui est à côté ne passe pas.
# ----------------------------------------------------------------------
def test_le_volume_fait_passer_et_le_reste_ne_passe_pas(host):
    """La preuve, exercée depuis les deux conteneurs.

    Le second contrôle est celui qui compte. Un candidat qui monterait le
    volume sur la racine des deux conteneurs partagerait bien plus que demandé,
    et la première moitié du test ne le verrait pas.
    """
    rc, phase, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get pod {POD} -o jsonpath='{{.status.phase}}'"
    )
    assert rc == 0 and phase == "Running", (
        f"Le Pod {POD} est en « {phase or 'absent'} ». Les deux conteneurs "
        f"doivent tourner pour que la mesure ait un sens. {diagnostic}"
    )

    rc, _, diagnostic = _dans(host, "lecteur", f"test -s {CHEMIN}")
    assert rc == 0, (
        f"Le conteneur « lecteur » ne trouve pas {CHEMIN}, ou le trouve vide, "
        "alors que le producteur y écrit toutes les cinq secondes. Vérifiez "
        "que les deux conteneurs montent le MÊME volume, et au même chemin : "
        "un volume monté ailleurs chez le lecteur ne lui montrera rien. "
        f"{diagnostic}"
    )

    _dans(host, "producteur", f"echo prive > {HORS_VOLUME}")
    rc, _, _ = _dans(host, "lecteur", f"test -f {HORS_VOLUME}")
    assert rc != 0, (
        f"Un fichier écrit par le producteur HORS du volume, dans "
        f"{HORS_VOLUME}, est visible par le lecteur. Les deux conteneurs "
        "partagent donc bien plus que le répertoire demandé : c'est la "
        "signature d'un volume monté trop haut, sur la racine ou sur /var. Un "
        "volume partagé doit l'être sur le seul répertoire qui en a besoin."
    )
