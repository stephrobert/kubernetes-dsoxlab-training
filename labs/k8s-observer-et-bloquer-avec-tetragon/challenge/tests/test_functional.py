"""test_functional.py : k8s-observer-et-bloquer-avec-tetragon

Ces tests lisent l'état du cluster et les événements de Tetragon, jamais les
commandes tapées.

Tetragon écrit chaque événement en JSON dans le conteneur export-stdout de son
agent, un agent par nœud. Les tests déclenchent eux-mêmes une lecture de la clé
dans le Pod vitrine, puis cherchent l'événement chez l'agent du nœud de ce Pod.

L'outil avec lequel le Pod rapport lit la clé est tiré au sort à la préparation
et gardé dans une mémoire lisible par root seulement : seul l'événement de
Tetragon le révèle.

Tous échouent avant le travail : aucune TracingPolicy n'existe, le ConfigMap
constat-tetragon non plus, et la clé se lit librement.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "comptes"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MEMOIRE = "/var/lib/dsoxlab/k8s-observer-et-bloquer-avec-tetragon.json"
CLE = "/etc/comptes/cle"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


def _agent(host, pod: str) -> str:
    """L'agent Tetragon du nœud où tourne `pod`."""
    noeud = host.run(ADMIN + " -n " + NS + " get pod " + pod + " -o jsonpath='{.spec.nodeName}'").stdout.strip()
    return host.run(
        ADMIN + " -n kube-system get pods -l app.kubernetes.io/name=tetragon "
        "--field-selector spec.nodeName=" + noeud + " -o jsonpath='{.items[0].metadata.name}'"
    ).stdout.strip()


def _evenements(host, pod: str, depuis: str = "120s") -> list[dict]:
    """Les process_kprobe récents de l'agent du nœud de `pod`, pour ce Pod."""
    agent = _agent(host, pod)
    sortie = host.run(f"{ADMIN} -n kube-system logs {agent} -c export-stdout --since={depuis}").stdout
    trouves = []
    for ligne in sortie.splitlines():
        try:
            e = json.loads(ligne).get("process_kprobe")
        except ValueError:
            continue
        if e and (e.get("process", {}).get("pod") or {}).get("name") == pod:
            trouves.append(e)
    return trouves


def _fichiers(e: dict) -> list[str]:
    return [(a.get("file_arg") or {}).get("path", "") for a in e.get("args") or []]


# ----------------------------------------------------------------------
# 1. Tetragon voit la lecture de la clé.
# ----------------------------------------------------------------------
def test_tetragon_voit_la_lecture_de_la_cle(host):
    host.run(f"{ADMIN} -n {NS} exec vitrine -- cat {CLE}")
    vus = []
    for _ in range(6):
        time.sleep(5)
        vus = [e for e in _evenements(host, "vitrine")
               if any(f.startswith("/etc/comptes/") for f in _fichiers(e))]
        if vus:
            break
    assert vus, message(
        en=f"A read of {CLE} in the Pod vitrine produces no Tetragon event within 30 seconds. A "
        "TracingPolicy on security_file_open must cover the files under /etc/comptes/: the key comes "
        "from a Secret, and the kernel sees its real path, not the one shown in the Pod.",
        fr=f"Une lecture de {CLE} dans le Pod vitrine ne produit aucun événement Tetragon en 30 secondes. "
        "Une TracingPolicy sur security_file_open doit couvrir les fichiers sous /etc/comptes/ : la clé "
        "vient d'un Secret, et le noyau voit son chemin réel, pas celui affiché dans le Pod.",
    )


# ----------------------------------------------------------------------
# 2. Le constat nomme le Pod et l'outil qui lisent la clé.
# ----------------------------------------------------------------------
def test_le_constat_nomme_le_lecteur_de_la_cle(host, memoire):
    donnees = (json.loads(host.run(f"{ADMIN} -n {NS} get configmap constat-tetragon -o json").stdout or "{}")
               .get("data") or {})
    lu = (donnees.get("pod", "").strip(), donnees.get("binaire", "").strip())
    attendu = (memoire["pod"], memoire["binaire"])
    assert lu == attendu, message(
        en=f"The ConfigMap constat-tetragon names pod={lu[0] or '?'} and binaire={lu[1] or '?'}. Expected the "
        "Pod that reads the key on its own, and the binary that Tetragon shows in its event, as a full path.",
        fr=f"Le ConfigMap constat-tetragon nomme pod={lu[0] or '?'} et binaire={lu[1] or '?'}. Attendu le Pod "
        "qui lit la clé de lui-même, et le binaire que Tetragon montre dans son événement, en chemin complet.",
    )


# ----------------------------------------------------------------------
# 3. La lecture de la clé est bloquée.
# ----------------------------------------------------------------------
def test_la_lecture_de_la_cle_est_bloquee(host):
    res = host.run(f"{ADMIN} -n {NS} exec vitrine -- cat {CLE}")
    assert res.rc == 137, message(
        en=f"Reading {CLE} in the Pod vitrine exits with {res.rc}, not 137: the process was not killed. A "
        "TracingPolicy with the Sigkill action stops the process before it reads the file.",
        fr=f"La lecture de {CLE} dans le Pod vitrine sort en {res.rc}, pas en 137 : le processus n'a pas été "
        "tué. Une TracingPolicy avec l'action Sigkill arrête le processus avant qu'il lise le fichier.",
    )


# ----------------------------------------------------------------------
# 4. Le blocage ne vise que la clé.
# ----------------------------------------------------------------------
def test_le_blocage_ne_vise_que_la_cle(host):
    """Sans blocage en place, lire /etc/hostname marche de toute façon : ce test
    passerait avant le travail, et ne mesurerait rien. Il exige donc d'abord que
    la clé soit bloquée, puis que le reste se lise."""
    cle = host.run(f"{ADMIN} -n {NS} exec vitrine -- cat {CLE}")
    assert cle.rc == 137, message(
        en="No blocking of the key is in place yet: the scope of a blocking can only be judged once it exists.",
        fr="Aucun blocage de la clé n'est encore en place : la portée d'un blocage ne se juge qu'une fois "
        "qu'il existe.",
    )
    res = host.run(f"{ADMIN} -n {NS} exec vitrine -- cat /etc/hostname")
    assert res.rc == 0 and res.stdout.strip() == "vitrine", message(
        en=f"Reading /etc/hostname in the Pod vitrine exits with {res.rc}. The blocking policy reaches beyond "
        "the key: it must only match the files under /etc/comptes/.",
        fr=f"La lecture de /etc/hostname dans le Pod vitrine sort en {res.rc}. La politique de blocage déborde "
        "de la clé : elle ne doit viser que les fichiers sous /etc/comptes/.",
    )
