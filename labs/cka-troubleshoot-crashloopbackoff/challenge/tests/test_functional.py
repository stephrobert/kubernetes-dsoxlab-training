"""test_functional.py : cka-troubleshoot-crashloopbackoff

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Le candidat
arrive au résultat par le chemin qu'il veut, et seul le résultat compte.

Quatre affirmations. Les deux premières regardent le Deployment et ses Pods ;
les deux dernières entrent dans un Pod pour lire le fichier de configuration
et interroger l'application. Ce sont elles qui prouvent quelque chose : un
Deployment « réparé » en remplaçant la commande par un sleep aurait 2/2
disponibles et ne servirait rien.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "production"
DEPLOYMENT = "api-server"
SELECTEUR = "app=api-server"
VARIABLE = "APP_CONFIG_PATH"
CHEMIN = "/etc/config"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pods(host) -> list[dict]:
    res = _kubectl(host, f"-n {NAMESPACE} get pods -l {SELECTEUR} -o json")
    assert res.rc == 0, f"Lecture des Pods impossible : {res.stderr.strip()}"
    return json.loads(res.stdout)["items"]


def _un_pod_pret(host) -> str:
    prets = [
        p["metadata"]["name"] for p in _pods(host)
        if p["status"].get("phase") == "Running"
        and all(c.get("ready") for c in p["status"].get("containerStatuses") or [])
    ]
    assert prets, (
        "Aucun Pod de api-server n'est prêt : impossible d'y entrer pour "
        "vérifier la configuration. Réglez d'abord la boucle de redémarrage."
    )
    return prets[0]


# ----------------------------------------------------------------------
# 1. Le Deployment a ses deux replicas disponibles.
# ----------------------------------------------------------------------
def test_deux_replicas_disponibles(host):
    res = _kubectl(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json")
    assert res.rc == 0, (
        f"Le Deployment {DEPLOYMENT} est introuvable dans {NAMESPACE}. Le setup "
        f"l'avait posé : il se corrige, il ne se supprime pas. {res.stderr.strip()}"
    )
    d = json.loads(res.stdout)
    voulus = d["spec"].get("replicas", 1)
    disponibles = d["status"].get("availableReplicas", 0)
    assert voulus == 2, (
        f"Le Deployment demande {voulus} replica(s) au lieu de 2. Réduire le "
        "nombre de replicas ne répare rien, cela cache la panne."
    )
    assert disponibles == 2, (
        f"{disponibles} replica(s) disponible(s) sur 2. Tant que le conteneur "
        "meurt au démarrage, aucun Pod ne devient disponible : lisez ses logs, "
        "avec --previous si le conteneur vient de redémarrer."
    )


# ----------------------------------------------------------------------
# 2. Plus aucun Pod ne redémarre en boucle.
# ----------------------------------------------------------------------
def test_plus_de_boucle_de_redemarrage(host):
    pods = _pods(host)
    assert pods, f"Aucun Pod {SELECTEUR} dans {NAMESPACE}."
    en_boucle = []
    for p in pods:
        for c in p["status"].get("containerStatuses") or []:
            raison = ((c.get("state") or {}).get("waiting") or {}).get("reason")
            if raison == "CrashLoopBackOff":
                en_boucle.append(p["metadata"]["name"])
    assert not en_boucle, (
        f"Encore en CrashLoopBackOff : {en_boucle}. Le conteneur démarre puis "
        "sort en erreur. Ce qu'il a écrit avant de mourir dit ce qui lui manque."
    )
    pas_prets = [
        p["metadata"]["name"] for p in pods
        if not all(c.get("ready") for c in p["status"].get("containerStatuses") or [])
    ]
    assert not pas_prets, (
        f"Pods sans conteneur prêt : {pas_prets}. Si un Pod ancien traîne, le "
        "rollout du Deployment n'est peut-être pas terminé."
    )


# ----------------------------------------------------------------------
# 3. La variable désigne /etc/config, et le fichier y est vraiment.
# ----------------------------------------------------------------------
def test_la_configuration_est_lue_au_bon_endroit(host):
    res = _kubectl(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json")
    assert res.rc == 0, res.stderr
    conteneur = json.loads(res.stdout)["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e.get("value") for e in conteneur.get("env") or []}
    assert env.get(VARIABLE) == CHEMIN, (
        f"Dans le Deployment, {VARIABLE} vaut {env.get(VARIABLE)!r} et non "
        f"{CHEMIN!r}. La charte de l'équipe place la configuration sous "
        f"{CHEMIN}, et c'est le Deployment qui doit le dire, pas un Pod édité "
        "à la main."
    )
    pod = _un_pod_pret(host)
    lecture = _kubectl(host, f"-n {NAMESPACE} exec {pod} -- cat {CHEMIN}/app.conf")
    assert lecture.rc == 0, (
        f"{VARIABLE} désigne {CHEMIN}, mais {CHEMIN}/app.conf n'y est pas : "
        "la variable pointe vers un répertoire où rien n'est monté. La "
        "configuration existe dans le namespace, sous forme de ConfigMap : il "
        f"reste à la donner au conteneur. Sortie : {lecture.stderr.strip()}"
    )
    assert "listen=8080" in lecture.stdout, (
        f"Le fichier {CHEMIN}/app.conf existe mais ce n'est pas la configuration "
        f"de l'équipe. Contenu : {lecture.stdout.strip()[:200]}"
    )


# ----------------------------------------------------------------------
# 4. L'application sert : la preuve que le processus a démarré pour de bon.
# ----------------------------------------------------------------------
def test_l_application_repond(host):
    pod = _un_pod_pret(host)
    reponse = _kubectl(
        host, f"-n {NAMESPACE} exec {pod} -- wget -qO- --timeout=5 http://127.0.0.1:8080/app.conf"
    )
    assert reponse.rc == 0 and "listen=8080" in reponse.stdout, (
        "Le Pod est prêt mais l'application ne répond pas sur le port 8080. Un "
        "conteneur qui tourne n'est pas une application qui sert : si la "
        "commande a été remplacée par une attente, rien n'écoute. "
        f"Sortie : {(reponse.stdout + reponse.stderr).strip()[:200]}"
    )
