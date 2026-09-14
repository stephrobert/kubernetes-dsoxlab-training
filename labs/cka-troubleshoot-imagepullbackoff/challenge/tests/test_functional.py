"""test_functional.py : cka-troubleshoot-imagepullbackoff

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Le candidat
arrive au résultat par le chemin qu'il veut, et seul le résultat compte :
changer l'image en place ou supprimer et recréer le Pod se valent.

Trois affirmations. La première regarde le Pod, la deuxième l'image que le
runtime a réellement tirée, et la troisième interroge le serveur depuis le
nœud : c'est elle qui prouve quelque chose, un Pod « Running » avec une image
qui n'est pas un serveur web ne répondrait pas.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
POD = "broken-pod"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict:
    res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, (
        f"Le Pod {POD} est introuvable dans le namespace {NAMESPACE}. S'il a été "
        f"supprimé pour être recréé, il doit l'être sous le même nom. {res.stderr.strip()}"
    )
    return json.loads(res.stdout)


def _statut_conteneur(pod: dict) -> dict:
    statuts = pod["status"].get("containerStatuses") or []
    return statuts[0] if statuts else {}


# ----------------------------------------------------------------------
# 1. Le Pod tourne, conteneur prêt.
# ----------------------------------------------------------------------
def test_le_pod_tourne(host):
    pod = _pod(host)
    statut = _statut_conteneur(pod)
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    assert raison not in ("ErrImagePull", "ImagePullBackOff"), (
        f"Le Pod est toujours en {raison} : l'image demandée ne se télécharge "
        "pas. Le message exact du runtime, celui qui dit si c'est le nom, le tag "
        "ou le registre qui cloche, est dans les events du Pod, pas dans son statut."
    )
    assert pod["status"].get("phase") == "Running" and statut.get("ready"), (
        f"Le Pod est en phase {pod['status'].get('phase')!r}, conteneur prêt : "
        f"{statut.get('ready')}. État du conteneur : {statut.get('state')}"
    )


# ----------------------------------------------------------------------
# 2. L'image est bien une image nginx publique, réellement tirée.
# ----------------------------------------------------------------------
def test_l_image_est_nginx_et_a_ete_tiree(host):
    pod = _pod(host)
    image = pod["spec"]["containers"][0]["image"]
    assert "nginx" in image, (
        f"L'image du Pod est {image!r} : ce n'est pas nginx. L'équipe voulait "
        "corriger la référence, pas changer de serveur."
    )
    statut = _statut_conteneur(pod)
    assert statut.get("imageID"), (
        f"Le conteneur déclare {image!r} mais aucun imageID : le runtime n'a "
        "rien téléchargé. L'image n'existe pas sous ce nom ou ce tag."
    )
    assert "nginx" in statut.get("imageID", ""), (
        f"L'image tirée est {statut.get('imageID')!r}, pas une image nginx."
    )


# ----------------------------------------------------------------------
# 3. La preuve qui compte : le serveur répond.
# ----------------------------------------------------------------------
def test_le_serveur_repond(host):
    pod = _pod(host)
    ip = pod["status"].get("podIP")
    assert ip, "Le Pod n'a pas d'adresse IP : il n'a pas encore démarré."
    res = host.run(f"curl -sS -m 5 http://{ip}/")
    assert res.rc == 0, (
        f"Le Pod a l'adresse {ip} mais rien ne répond sur le port 80 depuis le "
        f"nœud. Un Pod Running n'est pas forcément un serveur qui sert. {res.stderr.strip()}"
    )
    assert "nginx" in res.stdout.lower(), (
        f"Quelque chose répond sur {ip} mais ce n'est pas la page d'accueil de "
        f"nginx. Début de la réponse : {res.stdout[:120]!r}"
    )
