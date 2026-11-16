"""test_functional.py : cka-etiqueter-et-isoler-un-noeud

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. L'équipe data
se réserve k8s-w2.lab : le nœud doit porter son étiquette et son rôle, une
taint dont l'effet fait partir les Pods des autres équipes déjà installés, et
une annotation de contact.

Aucun test n'est vrai avant le travail : le setup ne pose ni étiquette, ni
rôle, ni taint, ni annotation, laisse entrepot en Pending et installe un Pod de
rapports sur k8s-w2. Le dernier test exerce les deux côtés : le Pod de l'équipe
data est sur le nœud, celui des autres en est parti ET tourne toujours ailleurs.
Une taint NoSchedule ferait démarrer entrepot et laisserait rapports en place :
c'est l'effet qui est mis à l'épreuve.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "equipes"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-w2.lab"
CONTACT = "data@formation.test"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, commande: str) -> dict:
    res = host.run(f"sudo {KUBECTL} {commande} -o json")
    assert res.rc == 0, message(
        en=f"`kubectl {commande}` failed: {res.stderr.strip()}",
        fr=f"`kubectl {commande}` a échoué : {res.stderr.strip()}",
    )
    return json.loads(res.stdout)


def _pods_prets(host, app: str, attendus: int, delai: int = 90) -> list[dict]:
    """Les Pods prêts de l'application, en attendant qu'une éviction se rejoue.

    Après une taint NoExecute, le Pod évincé est recréé par son ReplicaSet puis
    replanifié : cela prend quelques secondes, qu'on attend avec un budget
    borné plutôt que de recaler un travail juste sur une photo prise trop tôt.
    """
    fin = time.time() + delai
    while True:
        pods = _json(host, f"-n {NAMESPACE} get pods -l app={app}").get("items", [])
        prets = [
            p for p in pods
            if p["status"].get("phase") == "Running"
            and not p["metadata"].get("deletionTimestamp")
            and all(c.get("ready") for c in p["status"].get("containerStatuses") or [{}])
        ]
        if len(prets) >= attendus or time.time() > fin:
            return prets
        time.sleep(3)


# ----------------------------------------------------------------------
# 1. L'étiquette de l'équipe, sur ce nœud seulement.
# ----------------------------------------------------------------------
def test_le_noeud_porte_l_etiquette_de_l_equipe(host):
    etiquetes = sorted(
        n["metadata"]["name"] for n in _json(host, "get nodes")["items"]
        if n["metadata"].get("labels", {}).get("equipe") == "data"
    )
    assert etiquetes == [NOEUD], message(
        en=f"Nodes labelled equipe=data: {etiquetes or 'none'}. Only {NOEUD} is reserved for the data "
        "team: the label goes on that node and on no other.",
        fr=f"Nœuds étiquetés equipe=data : {etiquetes or 'aucun'}. Seul {NOEUD} est réservé à l'équipe "
        "data : l'étiquette va sur ce nœud et sur aucun autre.",
    )


# ----------------------------------------------------------------------
# 2. Le rôle, lisible dans la colonne ROLES.
# ----------------------------------------------------------------------
def test_le_noeud_affiche_le_role_data(host):
    etiquettes = _json(host, f"get node {NOEUD}")["metadata"].get("labels", {})
    assert "node-role.kubernetes.io/data" in etiquettes, message(
        en=f"{NOEUD} shows no data role: the ROLES column of `kubectl get nodes` reads the "
        "node-role.kubernetes.io/<role> labels, with an empty value by convention.",
        fr=f"{NOEUD} n'affiche aucun rôle data : la colonne ROLES de `kubectl get nodes` lit les "
        "étiquettes node-role.kubernetes.io/<rôle>, de valeur vide par convention.",
    )


# ----------------------------------------------------------------------
# 3. Une annotation de contact.
# ----------------------------------------------------------------------
def test_le_noeud_porte_le_contact_de_maintenance(host):
    annotations = _json(host, f"get node {NOEUD}")["metadata"].get("annotations", {})
    assert annotations.get("maintenance-contact") == CONTACT, message(
        en=f"The annotation maintenance-contact of {NOEUD} is {annotations.get('maintenance-contact')!r}, "
        f"not {CONTACT!r}.",
        fr=f"L'annotation maintenance-contact de {NOEUD} vaut {annotations.get('maintenance-contact')!r}, "
        f"pas {CONTACT!r}.",
    )


# ----------------------------------------------------------------------
# 4. La réserve fait partir les autres, et l'équipe data s'installe.
# ----------------------------------------------------------------------
def test_la_reserve_fait_partir_les_autres_et_accueille_l_equipe(host):
    taints = _json(host, f"get node {NOEUD}")["spec"].get("taints") or []
    effets = sorted(t.get("effect") for t in taints if t.get("key") == "equipe" and t.get("value") == "data")
    assert "NoExecute" in effets, message(
        en=f"{NOEUD} carries the taint equipe=data with effect(s) {effets or 'none'}. The other teams' "
        "Pods already on the node must leave it: NoSchedule and PreferNoSchedule only act on the Pods to "
        "come, NoExecute also evicts the ones already there.",
        fr=f"{NOEUD} porte la taint equipe=data avec le ou les effets {effets or 'aucun'}. Les Pods des "
        "autres équipes déjà sur le nœud doivent en partir : NoSchedule et PreferNoSchedule n'agissent que "
        "sur les Pods à venir, NoExecute évince aussi ceux qui sont déjà là.",
    )

    entrepot = _pods_prets(host, "entrepot", 1)
    assert entrepot and all(p["spec"].get("nodeName") == NOEUD for p in entrepot), message(
        en=f"entrepot, the data team's application, has no ready Pod on {NOEUD}. Its nodeSelector asks "
        "for equipe=data: `kubectl describe pod -n equipes -l app=entrepot` says what is missing.",
        fr=f"entrepot, l'application de l'équipe data, n'a aucun Pod prêt sur {NOEUD}. Son nodeSelector "
        "demande equipe=data : `kubectl describe pod -n equipes -l app=entrepot` dit ce qui manque.",
    )

    rapports = _pods_prets(host, "rapports", 2)
    sur_le_noeud = [p["metadata"]["name"] for p in rapports if p["spec"].get("nodeName") == NOEUD]
    assert not sur_le_noeud, message(
        en=f"rapports, which belongs to another team, still runs on {NOEUD}: {sur_le_noeud}.",
        fr=f"rapports, qui appartient à une autre équipe, tourne encore sur {NOEUD} : {sur_le_noeud}.",
    )
    assert len(rapports) >= 2, message(
        en=f"rapports has only {len(rapports)} ready Pod(s) out of 2. Isolating a node moves the other "
        "teams' Pods, it must not stop them: were they deleted, or is their Deployment scaled down?",
        fr=f"rapports n'a que {len(rapports)} Pod(s) prêt(s) sur 2. Isoler un nœud déplace les Pods des "
        "autres équipes, il ne doit pas les arrêter : ont-ils été supprimés, ou leur Deployment réduit ?",
    )
