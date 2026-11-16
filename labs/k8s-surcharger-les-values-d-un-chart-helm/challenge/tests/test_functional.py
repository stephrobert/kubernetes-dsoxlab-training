"""test_functional.py : k8s-surcharger-les-values-d-un-chart-helm

Ces tests lisent l'état de Helm et du cluster, jamais les commandes tapées. Le
setup laisse la release catalogue en podinfo 6.16.0, avec deux réglages de
l'exploitation posés par --set : replicaCount=3 et ui.color=#ff6b00.

L'apprenant la monte en 6.17.0 sans perdre ces réglages, et fixe le message de
l'interface à « 2026 », qui doit rester une CHAÎNE : --set convertit un nombre
en entier. Rien n'est vrai avant le travail.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "helm-values"
RELEASE = "catalogue"
HELM = "sudo helm --kubeconfig /etc/kubernetes/admin.conf"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _valeurs(host) -> dict:
    res = host.run(f"{HELM} get values {RELEASE} -n {NAMESPACE} -o json")
    assert res.rc == 0, message(
        en=f"helm get values {RELEASE} fails: {res.stderr.strip()}",
        fr=f"helm get values {RELEASE} échoue : {res.stderr.strip()}",
    )
    return json.loads(res.stdout) or {}


# ----------------------------------------------------------------------
# 1. Le message est la chaîne « 2026 », pas l'entier 2026.
# ----------------------------------------------------------------------
def test_le_message_est_une_chaine(host):
    valeur = (_valeurs(host).get("ui") or {}).get("message")
    assert valeur == "2026" and isinstance(valeur, str), message(
        en=f"The release values give ui.message = {valeur!r} ({type(valeur).__name__}). Expected the STRING "
        "'2026': --set turns a number into an integer, --set-string or a values file keeps it a string.",
        fr=f"Les values de la release donnent ui.message = {valeur!r} ({type(valeur).__name__}). Attendu la "
        "CHAÎNE '2026' : --set convertit un nombre en entier, --set-string ou un fichier de values la garde en "
        "chaîne.",
    )


# ----------------------------------------------------------------------
# 2. La montée en 6.17.0 garde les réglages de l'exploitation.
# ----------------------------------------------------------------------
def test_la_montee_garde_les_reglages_de_l_exploitation(host):
    # `helm status -o json` ne porte pas le chart en Helm 4 (clés mesurées le
    # 2026-11-16 en 4.3.2 : apply_method, hooks, info, manifest, name,
    # namespace, version) ; `helm list -o json` le donne, « podinfo-6.17.0 ».
    res = host.run(f"{HELM} list -n {NAMESPACE} --filter '^{RELEASE}$' -o json")
    assert res.rc == 0, message(
        en=f"helm list fails: {res.stderr.strip()}",
        fr=f"helm list échoue : {res.stderr.strip()}",
    )
    releases = json.loads(res.stdout or "[]")
    assert releases, message(
        en=f"No release {RELEASE} in {NAMESPACE}: `dsoxlab reset` sets the situation back.",
        fr=f"Aucune release {RELEASE} dans {NAMESPACE} : `dsoxlab reset` repose la situation.",
    )
    chart, etat = releases[0].get("chart"), releases[0].get("status")
    assert chart == "podinfo-6.17.0" and etat == "deployed", message(
        en=f"The release runs chart {chart} ({etat}): expected podinfo-6.17.0, deployed.",
        fr=f"La release tourne avec le chart {chart} ({etat}) : attendu podinfo-6.17.0, déployé.",
    )
    valeurs = _valeurs(host)
    replicas, couleur = valeurs.get("replicaCount"), (valeurs.get("ui") or {}).get("color")
    assert replicas == 3 and couleur == "#ff6b00", message(
        en=f"After the upgrade, the values give replicaCount={replicas!r} and ui.color={couleur!r}: the operations "
        "settings (3 and #ff6b00) were lost. An upgrade without values starts again from the chart defaults; "
        "--reuse-values or a values file keeps them.",
        fr=f"Après la montée, les values donnent replicaCount={replicas!r} et ui.color={couleur!r} : les réglages "
        "de l'exploitation (3 et #ff6b00) sont perdus. Un upgrade sans values repart des défauts du chart ; "
        "--reuse-values ou un fichier de values les garde.",
    )


# ----------------------------------------------------------------------
# 3. L'application sert le message.
# ----------------------------------------------------------------------
def test_l_application_sert_le_message(host):
    pret = host.run(f"{KUBECTL} -n {NAMESPACE} rollout status deploy/{RELEASE}-podinfo --timeout=120s")
    assert pret.rc == 0, message(
        en=f"The application is not available: {pret.stderr.strip()}",
        fr=f"L'application n'est pas disponible : {pret.stderr.strip()}",
    )
    ip = host.run(
        f"{KUBECTL} -n {NAMESPACE} get service {RELEASE}-podinfo -o jsonpath='{{.spec.clusterIP}}'"
    ).stdout.strip()
    fin, recu = time.time() + 30, ""
    while time.time() < fin:
        res = host.run(f"curl -s -m 5 http://{ip}:9898/")
        try:
            recu = json.loads(res.stdout).get("message", "")
        except ValueError:
            recu = res.stdout.strip()[:80]
        if recu == "2026":
            break
        time.sleep(3)
    assert recu == "2026", message(
        en=f"podinfo answers the message {recu!r}, not '2026'.",
        fr=f"podinfo répond le message {recu!r}, et non '2026'.",
    )
