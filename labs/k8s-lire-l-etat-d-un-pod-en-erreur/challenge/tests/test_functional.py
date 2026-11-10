"""test_functional.py : k8s-lire-l-etat-d-un-pod-en-erreur

Ces tests lisent l'état du CLUSTER et les fichiers de diagnostic, jamais les
commandes tapées.

Un test vérifie un seul état demandé par l'énoncé. Les trois fichiers sont
confrontés à ce que le cluster dit lui-même : la raison d'attente du conteneur
de api, le code de sortie réel de batch, la mémoire mesurée par l'API de
métriques au moment du contrôle. Le dernier test garde la consigne « sans rien
réparer » : un diagnostic qui commence par corriger l'image a détruit la panne
qu'il devait lire.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "diagnostic"
KUBECTL = "kubectl --kubeconfig /etc/kind/lab.kubeconfig"
IMAGE_API = "nginx:1.280"
IMAGE_BATCH = (
    "busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
)
RAISONS_API = ("ImagePullBackOff", "ErrImagePull")
CODE_DE_SORTIE = re.compile(
    r"(?i)(exit\s*code|code\s+de\s+sortie|exitcode|code\s+retour)\D{0,12}(\d+)"
)


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire personnel de l'utilisateur du lab : testinfra agit en root
    par sudo, donc host.user().home vaudrait /root."""
    return host.check_output(
        'getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6'
    ).strip()


def _livrable(host, nom: str) -> str:
    chemin = f"{_maison(host)}/diagnostic/{nom}"
    fichier = host.file(chemin)
    assert fichier.exists and fichier.size > 0, message(
        en=f"{chemin} is missing or empty.",
        fr=f"{chemin} est absent ou vide.",
    )
    return fichier.content_string


def _pods(host, app: str) -> list[dict]:
    data = _json(host, f"-n {NAMESPACE} get pods -l app={app}", message(
        en=f"Cannot list the Pods of {app} in {NAMESPACE}.",
        fr=f"Impossible de lister les Pods de {app} dans {NAMESPACE}.",
    ))
    return data.get("items") or []


def _deployment(host, nom: str) -> dict:
    return _json(host, f"-n {NAMESPACE} get deployment {nom}", message(
        en=f"The Deployment {nom} is missing from {NAMESPACE}: it must stay as the lab left it.",
        fr=f"Le Deployment {nom} a disparu de {NAMESPACE} : il doit rester tel que le lab l'a posé.",
    ))


# ----------------------------------------------------------------------
# 1. api : pourquoi l'image ne se télécharge pas.
# ----------------------------------------------------------------------
def test_la_cause_de_api_est_consignee(host):
    texte = _livrable(host, "api.txt")
    assert any(r.lower() in texte.lower() for r in RAISONS_API), message(
        en="api.txt does not name the reason the container is waiting "
           "(read the State and Reason lines of kubectl describe pod).",
        fr="api.txt ne nomme pas la raison pour laquelle le conteneur attend "
           "(lisez les lignes State et Reason de kubectl describe pod).",
    )
    assert IMAGE_API in texte, message(
        en=f"api.txt does not name the faulty image {IMAGE_API}.",
        fr=f"api.txt ne nomme pas l'image fautive {IMAGE_API}.",
    )


# ----------------------------------------------------------------------
# 2. batch : l'erreur écrite par l'exécution qui a planté.
# ----------------------------------------------------------------------
def test_l_erreur_de_batch_est_consignee(host):
    texte = _livrable(host, "batch.txt")
    assert "DB_HOST" in texte, message(
        en="batch.txt does not quote the error batch wrote before stopping "
           "(kubectl logs, with --previous once the container runs again).",
        fr="batch.txt ne cite pas l'erreur que batch a écrite avant de s'arrêter "
           "(kubectl logs, avec --previous une fois le conteneur relancé).",
    )


# ----------------------------------------------------------------------
# 3. batch : le code de sortie du dernier conteneur terminé.
# ----------------------------------------------------------------------
def test_le_code_de_sortie_de_batch_est_consigne(host):
    texte = _livrable(host, "batch.txt")
    codes = set()
    for pod in _pods(host, "batch"):
        for statut in (pod.get("status") or {}).get("containerStatuses") or []:
            termine = (statut.get("lastState") or {}).get("terminated") or \
                (statut.get("state") or {}).get("terminated")
            if termine:
                codes.add(str(termine.get("exitCode")))
    assert codes, message(
        en="No terminated batch container found: let the Pod crash at least once before checking.",
        fr="Aucun conteneur terminé de batch : laissez le Pod planter au moins une fois avant de contrôler.",
    )
    ecrits = {m.group(2) for m in CODE_DE_SORTIE.finditer(texte)}
    assert ecrits & codes, message(
        en=f"batch.txt does not give the exit code of the last terminated container "
           f"(cluster says {sorted(codes)}); write it as « exit code: N », as kubectl describe shows it.",
        fr=f"batch.txt ne donne pas le code de sortie du dernier conteneur terminé "
           f"(le cluster dit {sorted(codes)}) ; écrivez-le « code de sortie : N », comme kubectl describe l'affiche.",
    )


# ----------------------------------------------------------------------
# 4. top : le Pod qui consomme le plus de mémoire.
# ----------------------------------------------------------------------
def _memoire_mi(quantite: str) -> float:
    unites = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "k": 1 / 1048.576, "M": 1 / 1.048576}
    for suffixe, facteur in unites.items():
        if quantite.endswith(suffixe):
            return float(quantite[: -len(suffixe)]) * facteur
    return float(quantite) / 1048576


def test_le_pod_le_plus_gourmand_est_consigne(host):
    texte = _livrable(host, "top.txt")
    res = _kubectl(host, f"get --raw /apis/metrics.k8s.io/v1beta1/namespaces/{NAMESPACE}/pods")
    assert res.rc == 0, message(
        en="The metrics API does not answer: metrics-server is not ready yet, check again in a minute.",
        fr="L'API de métriques ne répond pas : metrics-server n'est pas encore prêt, recontrôlez dans une minute.",
    )
    mesures = {
        item["metadata"]["name"]: sum(_memoire_mi(c["usage"]["memory"]) for c in item["containers"])
        for item in json.loads(res.stdout).get("items") or []
    }
    assert mesures, message(
        en=f"The metrics API measures no Pod in {NAMESPACE} yet, check again in a minute.",
        fr=f"L'API de métriques ne mesure encore aucun Pod de {NAMESPACE}, recontrôlez dans une minute.",
    )
    maximum = max(mesures.values())
    acceptables = sorted(nom for nom, mi in mesures.items() if mi >= maximum * 0.9)
    assert any(nom in texte for nom in acceptables), message(
        en=f"top.txt does not name the Pod that uses the most memory right now "
           f"(one of {acceptables}, read with kubectl top pods).",
        fr=f"top.txt ne nomme pas le Pod qui consomme le plus de mémoire en ce moment "
           f"(l'un de {acceptables}, lu avec kubectl top pods).",
    )


# ----------------------------------------------------------------------
# 5. Rien n'a été réparé.
# ----------------------------------------------------------------------
def test_rien_n_a_ete_repare(host):
    # Un contrôle qui passerait sans rien faire ne mesurerait rien : le
    # diagnostic doit exister, et les pannes doivent être restées en l'état.
    for nom in ("api.txt", "batch.txt", "top.txt"):
        _livrable(host, nom)
    api = _deployment(host, "api")
    batch = _deployment(host, "batch")
    image_api = api["spec"]["template"]["spec"]["containers"][0]["image"]
    conteneur_batch = batch["spec"]["template"]["spec"]["containers"][0]
    intacts = (
        image_api == IMAGE_API
        and conteneur_batch["image"] == IMAGE_BATCH
        and "DB_HOST" in " ".join(conteneur_batch.get("command") or conteneur_batch.get("args") or [])
        and api["metadata"].get("generation") == 1
        and batch["metadata"].get("generation") == 1
    )
    assert intacts, message(
        en="api or batch was modified: the lab asks for a diagnosis only. "
           "Run « dsoxlab reset » to get the original failures back.",
        fr="api ou batch a été modifié : le lab ne demande qu'un diagnostic. "
           "Lancez « dsoxlab reset » pour retrouver les pannes d'origine.",
    )
