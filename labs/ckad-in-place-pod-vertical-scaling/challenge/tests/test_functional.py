"""test_functional.py : ckad-in-place-pod-vertical-scaling

Ces tests lisent l'état du CLUSTER et du CONTENEUR, jamais les commandes
tapées.

Trois affirmations. La première lit les ressources demandées ; la deuxième
prouve que le Pod est le même objet, par sa date de création gardée en
annotation par le setup, et que son conteneur n'a pas redémarré ; la
troisième lit la limite dans le cgroup du conteneur, là où le noyau
l'applique. Un Pod supprimé et recréé avec le bon budget aurait les bonnes
ressources et une autre date : il ne passerait pas.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "scaling-pod"
ANNOTATION = "lab.dsoxlab/cree-le"
MEMOIRE_OCTETS = 256 * 1024 * 1024
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, message(
        en=f"No Pod {POD} in {NAMESPACE}: it was not to be deleted.",
        fr=f"Aucun Pod {POD} dans {NAMESPACE} : il ne fallait pas le supprimer.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Les ressources demandées sont les nouvelles.
# ----------------------------------------------------------------------
def test_les_nouvelles_ressources_sont_demandees(host):
    res = _pod(host)["spec"]["containers"][0].get("resources") or {}
    cpu = (res.get("requests") or {}).get("cpu")
    memoire = (res.get("limits") or {}).get("memory")
    assert cpu == "200m", message(
        en=f"requests.cpu is {cpu!r}, expected '200m'. kubectl edit refuses that field on "
        "a Pod: it goes through the resize subresource, with kubectl patch.",
        fr=f"requests.cpu vaut {cpu!r}, attendu '200m'. kubectl edit refuse ce champ sur "
        "un Pod : il passe par la sous-ressource resize, avec kubectl patch.",
    )
    assert memoire == "256Mi", message(
        en=f"limits.memory is {memoire!r}, expected '256Mi'.",
        fr=f"limits.memory vaut {memoire!r}, attendu '256Mi'.",
    )


# ----------------------------------------------------------------------
# 2. Même Pod, même conteneur : rien n'a été recréé ni redémarré.
# ----------------------------------------------------------------------
def test_le_pod_n_a_ete_ni_recree_ni_redemarre(host):
    pod = _pod(host)
    creation = pod["metadata"].get("creationTimestamp")
    notee = (pod["metadata"].get("annotations") or {}).get(ANNOTATION)
    assert notee, message(
        en=f"Annotation {ANNOTATION} is gone: the Pod was recreated from scratch. Setup "
        "had placed it on the original Pod, and a recreated Pod no longer carries it.",
        fr=f"L'annotation {ANNOTATION} a disparu : le Pod a été recréé de zéro. Le setup "
        "l'avait posée sur le Pod d'origine, et un Pod recréé ne l'a plus.",
    )
    assert creation == notee, message(
        en=f"The Pod was created at {creation}, but setup had placed a Pod created at "
        f"{notee}: this is no longer the same object. Resizing in place means "
        "modifying the running Pod, not putting another one in its place.",
        fr=f"Le Pod a été créé le {creation}, mais le setup avait posé un Pod créé le "
        f"{notee} : ce n'est plus le même objet. Redimensionner en place, c'est "
        "modifier le Pod qui tourne, pas en poser un autre.",
    )
    statut = (pod["status"].get("containerStatuses") or [{}])[0]
    assert statut.get("restartCount", 0) == 0, message(
        en=f"The container restarted {statut.get('restartCount')} times. With a "
        "resizePolicy of NotRequired, a resize does not restart the container.",
        fr=f"Le conteneur a redémarré {statut.get('restartCount')} fois. Avec une "
        "resizePolicy NotRequired, un redimensionnement ne redémarre pas le conteneur.",
    )
    # Le kubelet rapporte les ressources qu'il a réellement allouées : avant
    # le travail, ce sont encore les anciennes, et ce test ne passe pas.
    allouees = (statut.get("resources") or {}).get("limits") or {}
    assert allouees.get("memory") == "256Mi", message(
        en=f"The kubelet allocated {allouees.get('memory')!r} of memory as the limit, expected "
        "256Mi: the Pod is indeed the same one, but it has not been resized yet, or "
        "the kubelet refused. The Pod's status, resize field, says so.",
        fr=f"Le kubelet a alloué {allouees.get('memory')!r} de mémoire en limite, attendu "
        "256Mi : le Pod est bien le même, mais il n'a pas encore été redimensionné, ou "
        "le kubelet a refusé. Le statut du Pod, champ resize, le dit.",
    )


# ----------------------------------------------------------------------
# 3. La preuve : le noyau applique la nouvelle limite.
# ----------------------------------------------------------------------
def test_le_noyau_applique_la_nouvelle_limite(host):
    vu = ""
    for _ in range(12):
        res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- cat /sys/fs/cgroup/memory.max")
        vu = res.stdout.strip()
        if vu == str(MEMOIRE_OCTETS):
            return
        time.sleep(5)
    assert vu == str(MEMOIRE_OCTETS), message(
        en=f"Inside the container, memory.max is {vu!r}, expected {MEMOIRE_OCTETS} bytes, "
        "that is 256Mi. The Pod asks for the new limit, but the kubelet has not "
        "applied it: the Pod's status, resize field, says whether it is pending or refused.",
        fr=f"Dans le conteneur, memory.max vaut {vu!r}, attendu {MEMOIRE_OCTETS} octets, "
        "soit 256Mi. Le Pod demande la nouvelle limite, mais le kubelet ne l'a pas "
        "appliquée : le statut du Pod, champ resize, dit s'il est en attente ou refusé.",
    )
