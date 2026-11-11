"""test_functional.py : cka-kubectl-debug

Ces tests lisent la définition du Pod distroless-app, puis le fichier écrit
DANS le conteneur éphémère. Un test vérifie un seul état demandé par l'énoncé.

Le second test prouve que le partage de processus agit : un conteneur
éphémère posé sans cible aurait le bon nom et ne verrait que lui-même. Il ne
peut relire le fichier que si le conteneur est resté en vie.

Le débogage du nœud ne fait plus partie de ce lab (décision D42 du
2026-11-11) : la leçon « Débugger une application » ne l'enseigne pas.

Tous échouent avant le travail : distroless-app n'a aucun conteneur éphémère.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "distroless-app"
DEBUGGER = "debugger"
#: Fichier écrit DANS le conteneur éphémère, chemin imposé par le scénario :
#: ce n'est pas un fichier temporaire du banc de test.
FICHIER = "/tmp/debug-output.txt"  # noqa: S108
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict:
    res = host.run(f"{ADMIN} -n {NS} get pod {POD} -o json")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"Pod {POD} cannot be found in {NS}. The setup had placed it there: it had to be neither deleted "
        "nor recreated, an ephemeral container is added to a running Pod.",
        fr=f"Le Pod {POD} est introuvable dans {NS}. Le setup l'avait posé : il ne fallait ni le supprimer ni "
        "le recréer, un conteneur éphémère s'ajoute à un Pod qui tourne.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. debugger est un conteneur éphémère qui partage les processus de l'application.
# ----------------------------------------------------------------------
def test_debugger_partage_les_processus_de_l_application(host):
    ephemeres = {c["name"]: c for c in _pod(host)["spec"].get("ephemeralContainers") or []}
    cible = (ephemeres.get(DEBUGGER) or {}).get("targetContainerName")
    assert cible == POD, message(
        en=f"{POD} has no ephemeral container {DEBUGGER} that shares the processes of the {POD} container "
        f"(ephemeral containers: {sorted(ephemeres) or 'none'}, target: {cible!r}). Without a target, an "
        "ephemeral container only sees itself.",
        fr=f"{POD} n'a pas de conteneur éphémère {DEBUGGER} qui partage les processus du conteneur {POD} "
        f"(conteneurs éphémères : {sorted(ephemeres) or 'aucun'}, cible : {cible!r}). Sans cible, un "
        "conteneur éphémère ne voit que lui-même.",
    )


# ----------------------------------------------------------------------
# 2. La liste des processus, écrite depuis debugger, montre coredns.
# ----------------------------------------------------------------------
def test_la_liste_des_processus_montre_coredns(host):
    _pod(host)
    res = host.run(f"{ADMIN} -n {NS} exec {POD} -c {DEBUGGER} -- cat {FICHIER}")
    assert res.rc == 0 and "coredns" in res.stdout, message(
        en=f"{FICHIER} cannot be read in {DEBUGGER}, or does not show the coredns process of the application. "
        "The file must be written from the ephemeral container, which must see the application's processes "
        "and stay alive so that the file can be read back.",
        fr=f"{FICHIER} ne se lit pas dans {DEBUGGER}, ou ne montre pas le processus coredns de l'application. "
        "Le fichier doit être écrit depuis le conteneur éphémère, qui doit voir les processus de "
        "l'application et rester en vie pour qu'on puisse le relire.",
    )
