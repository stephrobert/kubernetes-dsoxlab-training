"""test_functional.py : k8s-modifier-une-ressource-en-production

Ces tests lisent l'état du CLUSTER et le manifeste de l'apprenant, jamais les
commandes tapées. Le Deployment web du namespace magasin porte deux conteneurs,
web et log-agent ; son manifeste « Git » est ~/magasin/web.yaml, et le setup a
déjà créé une dérive : un opérateur a monté web à quatre réplicas pendant un
pic de charge, hors de Git.

Quatre tests, aucun vrai avant le travail : l'image est l'ancienne, l'annotation
et la variable sont absentes, et `kubectl diff` voit la dérive. Le premier
exerce les deux côtés du piège des listes : l'image a changé, ET log-agent est
toujours là, ET l'objet est le même (même uid). Un patch --type=merge
retirerait log-agent ; un replace --force recréerait l'objet sous un autre uid.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "magasin"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
IMAGE_CIBLE = "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
UID_DE_REFERENCE = "/var/lib/dsoxlab-lab/magasin-web.uid"
INCIDENT = "INC-2026-0142"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _deploy(host) -> dict:
    res = host.run(f"{KUBECTL} -n {NAMESPACE} get deployment web -o json")
    assert res.rc == 0, message(
        en=f"Deployment web cannot be found in namespace {NAMESPACE}: {res.stderr.strip()}",
        fr=f"Le Deployment web est introuvable dans le namespace {NAMESPACE} : {res.stderr.strip()}",
    )
    return json.loads(res.stdout)


def _conteneurs(deploy: dict) -> dict[str, dict]:
    return {c["name"]: c for c in deploy["spec"]["template"]["spec"]["containers"]}


def _manifeste(host) -> str:
    """Le manifeste dans le répertoire du compte de session.

    testinfra joue chaque commande sous sudo : $HOME y vaut /root. Le compte
    qui a ouvert la connexion reste dans SUDO_USER.
    """
    maison = host.run('getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6').stdout.strip()
    return f"{maison}/magasin/web.yaml"


# ----------------------------------------------------------------------
# 1. L'image change, log-agent reste, l'objet est le même.
# ----------------------------------------------------------------------
def test_web_passe_en_1_30_sans_perdre_log_agent_ni_l_objet(host):
    deploy = _deploy(host)
    conteneurs = _conteneurs(deploy)
    assert conteneurs.get("web", {}).get("image") == IMAGE_CIBLE, message(
        en=f"The web container runs {conteneurs.get('web', {}).get('image')}, not {IMAGE_CIBLE}.",
        fr=f"Le conteneur web tourne en {conteneurs.get('web', {}).get('image')}, pas en {IMAGE_CIBLE}.",
    )
    assert "log-agent" in conteneurs, message(
        en="The log-agent container is gone from the Deployment. A patch that only names web keeps log-agent "
        "in strategic merge, and removes it with --type=merge, which replaces the whole list.",
        fr="Le conteneur log-agent a disparu du Deployment. Un patch qui ne cite que web garde log-agent en "
        "strategic merge, et le supprime avec --type=merge, qui remplace toute la liste.",
    )
    reference = host.run(f"sudo cat {UID_DE_REFERENCE}").stdout.strip()
    assert reference and deploy["metadata"]["uid"] == reference, message(
        en="The Deployment web is no longer the same object (its uid changed): it was deleted and recreated, "
        "which stops every Pod at once and loses the rollout history. replace --force is only for an "
        "immutable field; changing an image is an update.",
        fr="Le Deployment web n'est plus le même objet (son uid a changé) : il a été supprimé puis recréé, ce "
        "qui arrête tous les Pods d'un coup et perd l'historique de rollout. replace --force est réservé à un "
        "champ immuable ; changer une image est une mise à jour.",
    )
    fin = time.time() + 120
    while True:
        deploy = _deploy(host)
        statut = deploy.get("status", {})
        pret = (statut.get("updatedReplicas") == statut.get("replicas") == statut.get("readyReplicas")
                and statut.get("observedGeneration", 0) >= deploy["metadata"]["generation"])
        if pret or time.time() > fin:
            break
        time.sleep(3)
    assert pret, message(
        en=f"The rollout of web is not finished: {statut}. `kubectl -n {NAMESPACE} rollout status deploy/web` "
        "says where it stands.",
        fr=f"Le rollout de web n'est pas terminé : {statut}. `kubectl -n {NAMESPACE} rollout status deploy/web` "
        "dit où il en est.",
    )


# ----------------------------------------------------------------------
# 2. L'incident est noté sur l'objet.
# ----------------------------------------------------------------------
def test_l_incident_est_annote(host):
    annotations = _deploy(host)["metadata"].get("annotations") or {}
    assert annotations.get("incident-ref") == INCIDENT, message(
        en=f"The annotation incident-ref of Deployment web is {annotations.get('incident-ref')!r}, not "
        f"{INCIDENT!r}.",
        fr=f"L'annotation incident-ref du Deployment web vaut {annotations.get('incident-ref')!r}, pas "
        f"{INCIDENT!r}.",
    )


# ----------------------------------------------------------------------
# 3. log-agent passe en LOG_LEVEL=debug.
# ----------------------------------------------------------------------
def test_log_agent_passe_en_debug(host):
    conteneurs = _conteneurs(_deploy(host))
    env = {e["name"]: e.get("value") for e in conteneurs.get("log-agent", {}).get("env") or []}
    assert env.get("LOG_LEVEL") == "debug", message(
        en=f"The log-agent container has the variables {env or 'none'}, without LOG_LEVEL=debug. It is the "
        "second container of the list: a JSON patch names it by its index.",
        fr=f"Le conteneur log-agent a les variables {env or 'aucune'}, sans LOG_LEVEL=debug. C'est le second "
        "conteneur de la liste : un JSON patch le désigne par son index.",
    )


# ----------------------------------------------------------------------
# 4. La dérive est résorbée, dans le bon sens.
# ----------------------------------------------------------------------
def test_la_derive_est_resorbee_dans_git(host):
    chemin = _manifeste(host)
    res = host.run(f"{KUBECTL} diff -f {chemin}")
    assert res.rc == 0, message(
        en=f"`kubectl diff -f {chemin}` still finds a gap between the cluster and the manifest "
        f"(code {res.rc}):\n{res.stdout.strip()[-1200:]}\nReport every change made in the cluster into the "
        "file, so that the next `kubectl apply` keeps it instead of undoing it.",
        fr=f"`kubectl diff -f {chemin}` voit encore un écart entre le cluster et le manifeste "
        f"(code {res.rc}) :\n{res.stdout.strip()[-1200:]}\nReportez dans le fichier chaque changement fait "
        "dans le cluster, pour que le prochain `kubectl apply` le garde au lieu de le défaire.",
    )
    deploy = _deploy(host)
    assert deploy["spec"].get("replicas") == 4, message(
        en=f"web runs {deploy['spec'].get('replicas')} replica(s): the load peak is still on, the four replicas "
        "the operator set must stay. The drift is resolved by changing the file, not by undoing the cluster.",
        fr=f"web tourne avec {deploy['spec'].get('replicas')} réplica(s) : le pic de charge dure, les quatre "
        "réplicas posés par l'opérateur doivent rester. La dérive se résorbe en changeant le fichier, pas en "
        "défaisant le cluster.",
    )
    assert _conteneurs(deploy).get("web", {}).get("image") == IMAGE_CIBLE, message(
        en="No gap is left, but web no longer runs nginx 1.30: was the file applied over the fix?",
        fr="Plus aucun écart, mais web ne tourne plus en nginx 1.30 : le fichier a-t-il été appliqué par-dessus "
        "la correction ?",
    )
