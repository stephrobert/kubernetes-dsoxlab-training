"""test_functional.py : ckad-helm-install-upgrade

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées : l'historique
d'une release Helm y est stocké, révision par révision, avec les valeurs de
chacune.

Trois affirmations. La première lit l'historique ; la deuxième les valeurs
de chaque révision, ce qui prouve que la montée à deux replicas a bien eu
lieu avant le retour ; la troisième l'état du Deployment et la réponse du
Service, ce qui prouve que la release revenue en arrière tourne.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
RELEASE = "web"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
HELM = "KUBECONFIG=/etc/kubernetes/admin.conf /usr/local/bin/helm"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _helm_json(host, args: str, absent: str):
    res = host.run(f"sudo sh -c '{HELM} {args} -o json'")
    assert res.rc == 0, f"{absent} Sortie : {res.stderr.strip()[:200]}"
    return json.loads(res.stdout or "null")


# ----------------------------------------------------------------------
# 1. Trois révisions : install, upgrade, rollback.
# ----------------------------------------------------------------------
def test_l_historique_montre_les_trois_revisions(host):
    historique = _helm_json(host, f"history {RELEASE} -n {NAMESPACE}",
                            f"Aucune release {RELEASE} dans {NAMESPACE}, ou helm ne la trouve pas.")
    assert isinstance(historique, list) and len(historique) >= 3, (
        f"{len(historique) if isinstance(historique, list) else 0} révision(s) : install, upgrade "
        "et rollback en font trois. Un rollback crée une révision, il n'en supprime aucune."
    )
    derniere = historique[-1]
    assert derniere.get("status") == "deployed", (
        f"La dernière révision est en statut {derniere.get('status')!r}, attendu deployed."
    )
    assert "rollback" in (derniere.get("description") or "").lower(), (
        f"La dernière révision n'est pas un rollback : {derniere.get('description')!r}. "
        "L'ordre compte : install, upgrade, puis rollback vers la révision 1."
    )


# ----------------------------------------------------------------------
# 2. La révision 2 portait deux replicas, la dernière n'en porte plus qu'un.
# ----------------------------------------------------------------------
def test_la_montee_en_charge_a_eu_lieu_puis_a_ete_annulee(host):
    valeurs_2 = _helm_json(host, f"get values {RELEASE} -n {NAMESPACE} --revision 2",
                           "La révision 2 est introuvable.") or {}
    assert valeurs_2.get("replicaCount") == 2, (
        f"La révision 2 portait replicaCount {valeurs_2.get('replicaCount')!r}, attendu 2 : "
        "l'upgrade devait passer la release à deux replicas, par --set ou par un fichier de valeurs."
    )
    valeurs = _helm_json(host, f"get values {RELEASE} -n {NAMESPACE}", "Les valeurs courantes sont introuvables.") or {}
    assert valeurs.get("replicaCount", 1) == 1, (
        f"Les valeurs courantes portent replicaCount {valeurs.get('replicaCount')!r} : le "
        "rollback vers la révision 1 devait ramener un replica."
    )


# ----------------------------------------------------------------------
# 3. L'application tourne et répond, avec un replica.
# ----------------------------------------------------------------------
def test_l_application_tourne_et_repond(host):
    d = {}
    for _ in range(12):
        res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get deployment {RELEASE} -o json")
        assert res.rc == 0, f"Aucun Deployment {RELEASE} dans {NAMESPACE} : c'est ce que le chart installe."
        d = json.loads(res.stdout)
        if d["status"].get("availableReplicas", 0) == d["spec"].get("replicas"):
            break
        time.sleep(5)
    assert d["spec"].get("replicas") == 1, f"Le Deployment demande {d['spec'].get('replicas')} replica(s), attendu 1 après le rollback."
    assert d["status"].get("availableReplicas", 0) == 1, "Le replica n'est pas disponible."
    image = d["spec"]["template"]["spec"]["containers"][0].get("image", "")
    assert "nginx:1.27-alpine" in image, f"L'image déployée est {image!r} : le chart de l'équipe fixe nginx:1.27-alpine par son appVersion."
    ip = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get service {RELEASE} -o jsonpath='{{.spec.clusterIP}}'").stdout.strip()
    assert ip, f"Aucun Service {RELEASE} : le chart en installe un."
    res = host.run(f"curl -sS -m 5 http://{ip}/")
    assert res.rc == 0 and "nginx" in res.stdout.lower(), f"Le Service {RELEASE} ne sert pas la page nginx : {res.stderr.strip()[:120]}"
