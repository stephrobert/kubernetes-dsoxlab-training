"""test_functional.py : k8s-creer-un-cluster-kind

Ces tests lisent le fichier de configuration ~/atelier/kind-atelier.yaml, puis
le cluster atelier lui-même, interrogé DANS son nœud control plane avec le
kubeconfig d'administration que kubeadm y a posé : ils ne dépendent pas du
kubeconfig de l'apprenant. Un test vérifie un seul état demandé par l'énoncé.

Aucun test n'attend tant que le cluster n'existe pas : l'attente des nœuds
Ready ne s'ouvre que si les trois nœuds sont déjà déclarés.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

CLUSTER = "atelier"
FICHIER = f"~/{CLUSTER}/kind-{CLUSTER}.yaml"
VERSION = "v1.37.0"
ROLES = ["control-plane", "worker", "worker"]
NOEUDS = f"sudo docker exec {CLUSTER}-control-plane kubectl --kubeconfig /etc/kubernetes/admin.conf get nodes -o json"
CONTROL_PLANE = "node-role.kubernetes.io/control-plane"
ATTENTE = 90
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _clusters(host) -> list[str]:
    res = host.run("sudo kind get clusters")
    return res.stdout.split() if res.rc == 0 else []


def _noeuds(host) -> list[dict]:
    if CLUSTER not in _clusters(host):
        return []
    res = host.run(NOEUDS)
    return json.loads(res.stdout).get("items", []) if res.rc == 0 else []


def _pret(noeud: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (noeud.get("status") or {}).get("conditions") or [])


# ----------------------------------------------------------------------
# 1. Le fichier de configuration.
# ----------------------------------------------------------------------
def test_le_fichier_de_configuration_decrit_un_control_plane_et_deux_workers(host):
    fichier = host.file(f"{_maison(host)}/{CLUSTER}/kind-{CLUSTER}.yaml")
    assert fichier.exists, message(
        en=f"No configuration file {FICHIER}. A multi-node cluster is described in a kind "
        "configuration file, versioned like any code. Reread the section of the lesson on a "
        "multi-node cluster.",
        fr=f"Aucun fichier de configuration {FICHIER}. Un cluster multi-nœuds se décrit dans "
        "un fichier de configuration kind, versionné comme du code. Relisez la section de la "
        "leçon sur le cluster multi-nœuds.",
    )
    try:
        conf = yaml.safe_load(fichier.content_string) or {}
    except yaml.YAMLError as erreur:
        pytest.fail(message(
            en=f"{FICHIER} is not valid YAML: {erreur}",
            fr=f"{FICHIER} n'est pas un YAML valide : {erreur}",
        ))
    assert conf.get("kind") == "Cluster" and str(conf.get("apiVersion", "")).startswith("kind.x-k8s.io/"), message(
        en=f"{FICHIER} must declare kind: Cluster and apiVersion: kind.x-k8s.io/v1alpha4, "
        f"found kind={conf.get('kind')!r}, apiVersion={conf.get('apiVersion')!r}.",
        fr=f"{FICHIER} doit déclarer kind: Cluster et apiVersion: kind.x-k8s.io/v1alpha4, "
        f"trouvé kind={conf.get('kind')!r}, apiVersion={conf.get('apiVersion')!r}.",
    )
    roles = sorted(str(n.get("role", "")) for n in conf.get("nodes") or [])
    assert roles == ROLES, message(
        en=f"{FICHIER} declares the nodes {roles}, expected one control-plane and two workers.",
        fr=f"{FICHIER} déclare les nœuds {roles}, attendu un control-plane et deux workers.",
    )


# ----------------------------------------------------------------------
# 2. Le cluster porte le nom demandé.
# ----------------------------------------------------------------------
def test_le_cluster_porte_le_nom_atelier(host):
    clusters = _clusters(host)
    assert CLUSTER in clusters, message(
        en=f"No kind cluster named {CLUSTER}: kind get clusters returns {clusters}. Without "
        "--name, kind creates the cluster named kind.",
        fr=f"Aucun cluster kind nommé {CLUSTER} : kind get clusters rend {clusters}. Sans "
        "--name, kind crée le cluster nommé kind.",
    )


# ----------------------------------------------------------------------
# 3. Trois nœuds Ready, à la version demandée.
# ----------------------------------------------------------------------
def test_les_trois_noeuds_sont_ready_en_v1_37_0(host):
    noeuds = _noeuds(host)
    assert len(noeuds) == 3, message(
        en=f"The cluster {CLUSTER} has {len(noeuds)} node(s), expected 3.",
        fr=f"Le cluster {CLUSTER} a {len(noeuds)} nœud(s), attendu 3.",
    )
    versions = sorted({n["status"]["nodeInfo"]["kubeletVersion"] for n in noeuds})
    assert versions == [VERSION], message(
        en=f"The nodes of {CLUSTER} run {versions}, expected {VERSION}. The node image sets "
        "the version: always give it, pinned by digest, with --image.",
        fr=f"Les nœuds de {CLUSTER} tournent en {versions}, attendu {VERSION}. L'image de nœud "
        "fixe la version : précisez-la toujours, épinglée par digest, avec --image.",
    )
    # Les trois nœuds existent : on laisse le réseau des Pods se poser.
    fin = time.monotonic() + ATTENTE
    while not all(_pret(n) for n in noeuds) and time.monotonic() < fin:
        time.sleep(PAS)
        noeuds = _noeuds(host) or noeuds
    pas_prets = [n["metadata"]["name"] for n in noeuds if not _pret(n)]
    assert not pas_prets, message(
        en=f"Nodes of {CLUSTER} still NotReady after {ATTENTE}s: {pas_prets}.",
        fr=f"Nœuds de {CLUSTER} toujours NotReady après {ATTENTE}s : {pas_prets}.",
    )


# ----------------------------------------------------------------------
# 4. Un control plane et deux workers.
# ----------------------------------------------------------------------
def test_les_noeuds_ont_un_control_plane_et_deux_workers(host):
    noeuds = _noeuds(host)
    plans = [n["metadata"]["name"] for n in noeuds
             if CONTROL_PLANE in (n["metadata"].get("labels") or {})]
    workers = [n["metadata"]["name"] for n in noeuds
               if CONTROL_PLANE not in (n["metadata"].get("labels") or {})]
    assert len(plans) == 1 and len(workers) == 2, message(
        en=f"{CLUSTER} has {len(plans)} control-plane node(s) {plans} and {len(workers)} "
        f"worker(s) {workers}, expected 1 and 2. The ROLES column of kubectl get nodes shows "
        "<none> for a worker, which is normal.",
        fr=f"{CLUSTER} a {len(plans)} nœud(s) control-plane {plans} et {len(workers)} "
        f"worker(s) {workers}, attendu 1 et 2. La colonne ROLES de kubectl get nodes montre "
        "<none> pour un worker, c'est normal.",
    )
