"""test_functional.py : ckad-helm-install-upgrade

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées : l'historique
d'une release Helm y est stocké, révision par révision, avec la version du
chart et les valeurs de chacune.

Depuis le 2026-11-20, le challenge ne reprend plus le lab guidé de la leçon
(install, upgrade --set replicaCount=2, rollback) : le chart de l'équipe passe
de la version 0.1.0 à 0.2.0 entre l'install et l'upgrade, l'upgrade porte 3
réplicas et un label de Pod, et le retour à la révision 1 doit ramener le
chart 0.1.0. La colonne CHART de l'historique le prouve.

Trois affirmations. La première lit l'historique et la version du chart de
chaque révision ; la deuxième les valeurs de chaque révision ; la troisième
l'état du Deployment, l'image que le chart rend, et la réponse du Service.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
RELEASE = "web"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
HELM = "KUBECONFIG=/etc/kubernetes/admin.conf /usr/local/bin/helm"
DIGEST = "sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _helm(host, args: str):
    return host.run(f"sudo sh -c '{HELM} {args}'")


def _helm_json(host, args: str, absent: str):
    res = _helm(host, f"{args} -o json")
    assert res.rc == 0, message(
        en=f"{absent} Output: {res.stderr.strip()[:200]}",
        fr=f"{absent} Sortie : {res.stderr.strip()[:200]}",
    )
    return json.loads(res.stdout or "null")


def _historique(host) -> list[dict]:
    h = _helm_json(host, f"history {RELEASE} -n {NAMESPACE}", message(
        en=f"No release {RELEASE} in {NAMESPACE}, or helm cannot find it.",
        fr=f"Aucune release {RELEASE} dans {NAMESPACE}, ou helm ne la trouve pas.",
    ))
    return h if isinstance(h, list) else []


# ----------------------------------------------------------------------
# 1. Install en 0.1.0, upgrade en 0.2.0, retour à la révision 1.
# ----------------------------------------------------------------------
def test_l_historique_montre_les_deux_versions_du_chart_puis_le_retour(host):
    historique = _historique(host)
    charts = [r.get("chart") for r in historique]
    assert len(historique) >= 3 and charts[0] == "web-0.1.0" and charts[1] == "web-0.2.0", message(
        en=f"The history shows the charts {charts or 'none'}. Expected: revision 1 installed from "
        "web-0.1.0, revision 2 upgraded with the chart in version 0.2.0. The version of the chart "
        "is the version field of its Chart.yaml.",
        fr=f"L'historique montre les charts {charts or 'aucun'}. Attendu : la révision 1 installée "
        "depuis web-0.1.0, la révision 2 mise à jour avec le chart en version 0.2.0. La version "
        "du chart est le champ version de son Chart.yaml.",
    )
    derniere = historique[-1]
    assert derniere.get("status") == "deployed" and derniere.get("description") == "Rollback to 1" \
            and derniere.get("chart") == "web-0.1.0", message(
        en=f"The last revision is {derniere.get('revision')} ({derniere.get('status')}, "
        f"{derniere.get('chart')}, {derniere.get('description')!r}). Expected a deployed rollback "
        "to revision 1, which brings back the chart web-0.1.0. A rollback creates a revision, it "
        "deletes none.",
        fr=f"La dernière révision est la {derniere.get('revision')} ({derniere.get('status')}, "
        f"{derniere.get('chart')}, {derniere.get('description')!r}). Attendu un rollback déployé "
        "vers la révision 1, qui ramène le chart web-0.1.0. Un rollback crée une révision, il "
        "n'en supprime aucune.",
    )


# ----------------------------------------------------------------------
# 2. La révision 2 portait 3 réplicas et le label tier=front, plus maintenant.
# ----------------------------------------------------------------------
def test_la_revision_2_portait_ses_valeurs_et_le_retour_les_retire(host):
    valeurs_2 = _helm_json(host, f"get values {RELEASE} -n {NAMESPACE} --revision 2", message(
        en="Revision 2 cannot be found.",
        fr="La révision 2 est introuvable.",
    )) or {}
    tier = (valeurs_2.get("podLabels") or {}).get("tier")
    assert valeurs_2.get("replicaCount") == 3 and tier == "front", message(
        en=f"Revision 2 carried replicaCount {valeurs_2.get('replicaCount')!r} and podLabels.tier "
        f"{tier!r}, expected 3 and 'front': the upgrade passes both values, through --set or a "
        "values file. The chart's values.yaml says their names.",
        fr=f"La révision 2 portait replicaCount {valeurs_2.get('replicaCount')!r} et podLabels.tier "
        f"{tier!r}, attendu 3 et 'front' : l'upgrade passe les deux valeurs, par --set ou par un "
        "fichier de valeurs. Le values.yaml du chart dit leurs noms.",
    )
    valeurs = _helm_json(host, f"get values {RELEASE} -n {NAMESPACE}", message(
        en="The current values cannot be found.",
        fr="Les valeurs courantes sont introuvables.",
    )) or {}
    assert valeurs.get("replicaCount", 1) == 1 and not (valeurs.get("podLabels") or {}).get("tier"), message(
        en=f"The current values are {valeurs}: the rollback to revision 1 had to bring back one "
        "replica and no tier label.",
        fr=f"Les valeurs courantes sont {valeurs} : le rollback vers la révision 1 devait ramener un "
        "réplica et aucun label tier.",
    )


# ----------------------------------------------------------------------
# 3. L'application tourne et répond, avec l'image que le chart rend.
# ----------------------------------------------------------------------
def test_l_application_tourne_et_repond(host):
    d = {}
    for _ in range(12):
        res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get deployment {RELEASE} -o json")
        assert res.rc == 0, message(
            en=f"No Deployment {RELEASE} in {NAMESPACE}: that is what the chart installs.",
            fr=f"Aucun Deployment {RELEASE} dans {NAMESPACE} : c'est ce que le chart installe.",
        )
        d = json.loads(res.stdout)
        if d["status"].get("availableReplicas", 0) == d["spec"].get("replicas"):
            break
        time.sleep(5)
    assert d["spec"].get("replicas") == 1 and d["status"].get("availableReplicas", 0) == 1, message(
        en=f"The Deployment asks for {d['spec'].get('replicas')} replica(s) and has "
        f"{d['status'].get('availableReplicas', 0)} available, expected 1 and 1 after the rollback.",
        fr=f"Le Deployment demande {d['spec'].get('replicas')} réplica(s) et en a "
        f"{d['status'].get('availableReplicas', 0)} disponible(s), attendu 1 et 1 après le rollback.",
    )
    image = d["spec"]["template"]["spec"]["containers"][0].get("image", "")
    manifeste = _helm(host, f"get manifest {RELEASE} -n {NAMESPACE}").stdout
    rendues = [c.get("image") for doc in yaml.safe_load_all(manifeste) if isinstance(doc, dict)
               and doc.get("kind") == "Deployment"
               for c in doc["spec"]["template"]["spec"]["containers"]]
    assert image in rendues and DIGEST in image, message(
        en=f"The deployed image is {image!r}, the chart renders {rendues}: expected the image of the "
        "chart, pinned by digest on nginx 1.30.5.",
        fr=f"L'image déployée est {image!r}, le chart rend {rendues} : attendu l'image du chart, "
        "épinglée par digest sur nginx 1.30.5.",
    )
    ip = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get service {RELEASE} -o jsonpath='{{.spec.clusterIP}}'").stdout.strip()
    assert ip, message(
        en=f"No Service {RELEASE}: the chart installs one.",
        fr=f"Aucun Service {RELEASE} : le chart en installe un.",
    )
    res = host.run(f"curl -sS -m 5 http://{ip}/")
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en=f"Service {RELEASE} does not serve the nginx page: {res.stderr.strip()[:120]}",
        fr=f"Le Service {RELEASE} ne sert pas la page nginx : {res.stderr.strip()[:120]}",
    )
