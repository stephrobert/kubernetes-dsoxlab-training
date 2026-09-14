"""test_functional.py : cka-kubectl-debug

Ces tests lisent l'état du CLUSTER et du NŒUD, jamais les commandes tapées.
Le candidat arrive au résultat par le chemin qu'il veut, et seul le résultat
compte.

Quatre affirmations. La première lit la définition du Pod ; la deuxième relit
le fichier DANS le conteneur éphémère, et c'est elle qui prouve que le partage
de processus agit : un conteneur éphémère posé sans --target aurait le bon nom
et ne verrait que lui-même. La troisième cherche un Pod qui a l'accès au nœud ;
la quatrième lit le fichier témoin sur le nœud, là où seul un Pod avec la
racine du nœud montée peut l'avoir écrit.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
POD = "distroless-app"
DEBUGGER = "debugger"
NOEUD = "k8s-cp.lab"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, (
        f"Le Pod {POD} est introuvable dans le namespace {NAMESPACE}. Le setup "
        "l'avait posé : il ne fallait ni le supprimer ni le recréer, un conteneur "
        f"éphémère s'ajoute à un Pod qui tourne. Sortie : {res.stderr.strip()}"
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Le conteneur éphémère existe, vise l'application, et tourne.
# ----------------------------------------------------------------------
def test_conteneur_ephemere_rattache_a_l_application(host):
    pod = _pod(host)
    ephemeres = pod["spec"].get("ephemeralContainers") or []
    noms = [c["name"] for c in ephemeres]
    assert DEBUGGER in noms, (
        f"Aucun conteneur éphémère nommé {DEBUGGER} sur le Pod {POD}. "
        f"Conteneurs éphémères présents : {noms or 'aucun'}. kubectl debug en "
        "ajoute un sans redémarrer le Pod, et l'option -c lui donne son nom."
    )
    debugger = next(c for c in ephemeres if c["name"] == DEBUGGER)
    cible = debugger.get("targetContainerName")
    assert cible == POD, (
        f"Le conteneur {DEBUGGER} existe mais ne partage pas les processus de "
        f"{POD} : targetContainerName vaut {cible!r}. Sans --target, ps n'y "
        "verrait que le conteneur éphémère lui-même, pas l'application."
    )
    etats = {s["name"]: s for s in pod["status"].get("ephemeralContainerStatuses") or []}
    etat = (etats.get(DEBUGGER) or {}).get("state") or {}
    assert "running" in etat, (
        f"Le conteneur {DEBUGGER} n'est pas en cours d'exécution : état {etat}. "
        "Il doit rester en vie après avoir écrit la liste des processus, sinon "
        "plus personne ne peut la relire : un sleep après la commande suffit."
    )


# ----------------------------------------------------------------------
# 2. La preuve que le partage de processus agit : coredns est dans la liste.
# ----------------------------------------------------------------------
def test_la_liste_des_processus_montre_l_application(host):
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -c {DEBUGGER} -- cat /tmp/debug-output.txt")
    assert res.rc == 0, (
        f"Impossible de lire /tmp/debug-output.txt dans le conteneur {DEBUGGER} : "
        "soit le fichier n'a pas été écrit, soit le conteneur est déjà terminé. "
        f"Sortie : {(res.stdout + res.stderr).strip()}"
    )
    assert "coredns" in res.stdout, (
        "Le fichier existe mais ne montre pas le processus coredns de "
        "l'application. Le conteneur éphémère ne voit que ses propres processus : "
        "il n'a pas été rattaché à l'espace de processus de distroless-app. "
        f"Contenu : {res.stdout.strip()[:300]}"
    )


# ----------------------------------------------------------------------
# 3. Un Pod de débogage du nœud tourne.
# ----------------------------------------------------------------------
def test_un_pod_de_debogage_du_noeud_tourne(host):
    res = _kubectl(host, "get pods -A -o json")
    assert res.rc == 0, f"Lecture des Pods impossible : {res.stderr.strip()}"
    pods = json.loads(res.stdout)["items"]
    candidats = [
        p for p in pods
        if p["spec"].get("hostPID") and p["metadata"]["namespace"] != "kube-system"
    ]
    assert candidats, (
        "Aucun Pod n'a accès aux processus du nœud (hostPID). kubectl debug "
        f"node/{NOEUD} en crée un, avec l'espace de processus de l'hôte et la "
        "racine du nœud montée sous /host."
    )
    avec_racine = [
        p for p in candidats
        if any((v.get("hostPath") or {}).get("path") == "/" for v in p["spec"].get("volumes") or [])
    ]
    assert avec_racine, (
        "Un Pod a hostPID mais aucun ne monte la racine du nœud : sans ce "
        "montage, il ne peut rien écrire sur le nœud. kubectl debug node/ le "
        f"fait pour vous. Vus : {[p['metadata']['name'] for p in candidats]}"
    )
    en_marche = [p for p in avec_racine if p["status"].get("phase") == "Running"]
    assert en_marche, (
        "Le Pod de débogage du nœud existe mais ne tourne pas : phases "
        f"{[p['status'].get('phase') for p in avec_racine]}. Sa commande doit "
        "rester en vie, un sleep après l'écriture suffit ; un Pod terminé ne "
        "prouve pas qu'on sait revenir sur le nœud."
    )


# ----------------------------------------------------------------------
# 4. Le fichier témoin est SUR le nœud, pas dans le Pod.
# ----------------------------------------------------------------------
def test_le_fichier_temoin_est_sur_le_noeud(host):
    res = host.run("sudo cat /tmp/node-debug.txt")
    assert res.rc == 0, (
        f"Le fichier /tmp/node-debug.txt n'existe pas sur le nœud {NOEUD}. "
        "Écrit dans /tmp du Pod de débogage, il reste dans le Pod : la racine "
        "du nœud est montée ailleurs, sous /host, et c'est là qu'il faut écrire."
    )
    assert "node-debug-ok" in res.stdout, (
        "Le fichier existe sur le nœud mais ne contient pas node-debug-ok : "
        f"contenu {res.stdout.strip()!r}."
    )
