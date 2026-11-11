"""test_functional.py : ckad-in-place-pod-vertical-scaling

Ces tests lisent la définition du Pod scaling-pod, son identité comparée à
celle que le setup a mémorisée, les ressources que le kubelet rapporte avoir
allouées, et la limite que le noyau applique, lue dans le cgroup. Un test
vérifie un seul état demandé par l'énoncé.

Le test d'identité exige d'abord que le redimensionnement soit demandé : sans
cette précondition, un Pod qu'on n'a pas touché passerait, puisqu'il n'est ni
recréé ni redémarré.

Tous échouent avant le travail : scaling-pod demande encore 100m et 128Mi.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "scaling-pod"
MEMOIRE = "/var/lib/dsoxlab/in-place-pod-vertical-scaling.json"
CPU = "200m"
LIMITE = "256Mi"
LIMITE_OCTETS = 256 * 1024 * 1024
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 60
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict:
    res = host.run(f"{ADMIN} -n {NS} get pod {POD} -o json")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No Pod {POD} in {NS}: it had to be resized, not deleted.",
        fr=f"Aucun Pod {POD} dans {NS} : il fallait le redimensionner, pas le supprimer.",
    )
    return json.loads(res.stdout)


def _demande(pod: dict) -> tuple:
    res = pod["spec"]["containers"][0].get("resources") or {}
    return (res.get("requests") or {}).get("cpu"), (res.get("limits") or {}).get("memory")


# ----------------------------------------------------------------------
# 1. scaling-pod demande ses nouvelles ressources.
# ----------------------------------------------------------------------
def test_scaling_pod_demande_ses_nouvelles_ressources(host):
    cpu, memoire = _demande(_pod(host))
    assert (cpu, memoire) == (CPU, LIMITE), message(
        en=f"{POD} requests {cpu!r} of CPU and limits its memory to {memoire!r}, expected {CPU} and {LIMITE}.",
        fr=f"{POD} demande {cpu!r} de CPU et limite sa mémoire à {memoire!r}, attendu {CPU} et {LIMITE}.",
    )


# ----------------------------------------------------------------------
# 2. Le redimensionnement s'est fait en place : même Pod, aucun redémarrage.
# ----------------------------------------------------------------------
def test_le_redimensionnement_s_est_fait_sans_recreer_ni_redemarrer(host):
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset ckad-in-place-pod-vertical-scaling.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset ckad-in-place-pod-vertical-scaling.",
        ))
    uid_initial = json.loads(res.stdout)["uid"]
    pod = _pod(host)
    assert _demande(pod) == (CPU, LIMITE), message(
        en=f"{POD} has not been resized yet: an untouched Pod proves nothing.",
        fr=f"{POD} n'a pas encore été redimensionné : un Pod qu'on n'a pas touché ne prouve rien.",
    )
    redemarrages = (pod["status"].get("containerStatuses") or [{}])[0].get("restartCount", 0)
    meme = pod["metadata"]["uid"] == uid_initial
    constat_fr = "est le même objet" if meme else "n'est plus l'objet que le lab a posé : il a été recréé"
    assert meme and redemarrages == 0, message(
        en=f"{POD} {'is the same object' if meme else 'is no longer the object the lab installed: it was recreated'}, "
        f"and its container restarted {redemarrages} time(s). Resizing in place means changing the running "
        "Pod, without recreating it and without restarting its container.",
        fr=f"{POD} {constat_fr}, "
        f"et son conteneur a redémarré {redemarrages} fois. Redimensionner en place, c'est modifier le Pod qui "
        "tourne, sans le recréer et sans redémarrer son conteneur.",
    )


# ----------------------------------------------------------------------
# 3. La nouvelle limite est appliquée : par le kubelet, puis par le noyau.
# ----------------------------------------------------------------------
def test_la_nouvelle_limite_est_appliquee_par_le_kubelet_et_le_noyau(host):
    pod = _pod(host)
    fin = time.monotonic() + ATTENTE
    alloue = lu = None
    while True:
        statut = (pod["status"].get("containerStatuses") or [{}])[0]
        alloue = ((statut.get("resources") or {}).get("limits") or {}).get("memory")
        res = host.run(f"{ADMIN} -n {NS} exec {POD} -- cat /sys/fs/cgroup/memory.max")
        lu = res.stdout.strip() if res.rc == 0 else "illisible"
        if (alloue == LIMITE and lu == str(LIMITE_OCTETS)) or time.monotonic() >= fin:
            break
        time.sleep(PAS)
        pod = _pod(host)
    assert alloue == LIMITE and lu == str(LIMITE_OCTETS), message(
        en=f"The kubelet reports {alloue!r} allocated as the memory limit, and the kernel applies {lu!r}. "
        f"Expected {LIMITE}, that is {LIMITE_OCTETS} bytes. A resize can be accepted by the API and still "
        "be pending or refused on the node: the Pod's conditions say so.",
        fr=f"Le kubelet rapporte {alloue!r} alloué en limite de mémoire, et le noyau applique {lu!r}. Attendu "
        f"{LIMITE}, soit {LIMITE_OCTETS} octets. Un redimensionnement peut être accepté par l'API et rester en "
        "attente ou refusé sur le nœud : les conditions du Pod le disent.",
    )
