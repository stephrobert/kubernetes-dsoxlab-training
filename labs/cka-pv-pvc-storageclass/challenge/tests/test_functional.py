"""test_functional.py : cka-pv-pvc-storageclass

Ces tests lisent l'état du CLUSTER et du NŒUD, jamais les commandes tapées.

Quatre affirmations. La première lit le PersistentVolume : capacité, mode
d'accès, StorageClass, et le répertoire du nœud auquel il est adossé. La
deuxième lit la réclamation et sa liaison. La troisième lit le Pod, son
montage, et le fichier vu de l'intérieur. La quatrième lit le même fichier
sur le disque du nœud où le Pod tourne, par ssh : un emptyDir monté sur
/data passerait les trois premiers tests, pas celui-là.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
PV = "lab-pv"
PVC = "lab-pvc"
POD = "data-pod"
REPERTOIRE = "/mnt/lab-data"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pv(host) -> dict:
    res = _kubectl(host, f"get pv {PV} -o json")
    assert res.rc == 0, f"Aucun PersistentVolume {PV}. Sans provisionneur, c'est à vous de le créer."
    return json.loads(res.stdout)


def _chemin_du_pv(pv: dict) -> str:
    chemin = (pv["spec"].get("hostPath") or {}).get("path") or (pv["spec"].get("local") or {}).get("path")
    assert chemin, (
        f"{PV} n'est adossé ni à un hostPath ni à un volume local : {sorted(pv['spec'])}. "
        "Sur ce cluster, le seul stockage disponible est le disque d'un nœud."
    )
    return chemin


def _pod_pret(host) -> dict:
    pod: dict = {}
    for _ in range(18):
        res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
        assert res.rc == 0, f"Aucun Pod {POD} dans {NAMESPACE}."
        pod = json.loads(res.stdout)
        if pod["status"].get("phase") == "Running":
            return pod
        time.sleep(5)
    pytest.fail(
        f"{POD} est en phase {pod['status'].get('phase')!r} après 90 s. S'il est Pending, "
        "kubectl describe pod dit si la réclamation est liée, et sinon pourquoi."
    )


# ----------------------------------------------------------------------
# 1. Le PersistentVolume est ce qui est demandé.
# ----------------------------------------------------------------------
def test_le_volume_est_declare(host):
    pv = _pv(host)
    capacite = (pv["spec"].get("capacity") or {}).get("storage")
    assert capacite == "1Gi", f"{PV} a une capacité de {capacite!r}, attendu 1Gi."
    modes = pv["spec"].get("accessModes") or []
    assert "ReadWriteOnce" in modes, f"{PV} a les modes {modes}, attendu ReadWriteOnce."
    assert pv["spec"].get("storageClassName") == "manual", (
        f"{PV} a la StorageClass {pv['spec'].get('storageClassName')!r}, attendu manual. Un PVC "
        "qui demande manual ne se liera jamais à un PV qui dit autre chose."
    )
    chemin = _chemin_du_pv(pv)
    assert chemin.rstrip("/") == REPERTOIRE, f"{PV} est adossé à {chemin!r}, attendu {REPERTOIRE}."


# ----------------------------------------------------------------------
# 2. La réclamation est liée à ce volume.
# ----------------------------------------------------------------------
def test_la_reclamation_est_liee(host):
    res = _kubectl(host, f"-n {NAMESPACE} get pvc {PVC} -o json")
    assert res.rc == 0, f"Aucun PersistentVolumeClaim {PVC} dans {NAMESPACE}."
    pvc = json.loads(res.stdout)
    demande = ((pvc["spec"].get("resources") or {}).get("requests") or {}).get("storage")
    assert demande == "500Mi", f"{PVC} demande {demande!r}, attendu 500Mi."
    assert pvc["spec"].get("storageClassName") == "manual", (
        f"{PVC} demande la StorageClass {pvc['spec'].get('storageClassName')!r}, attendu manual."
    )
    phase = pvc["status"].get("phase")
    assert phase == "Bound", (
        f"{PVC} est en phase {phase!r}. Une réclamation reste Pending tant qu'aucun PV n'a la "
        "capacité, le mode d'accès ET la StorageClass qu'elle demande."
    )
    assert pvc["spec"].get("volumeName") == PV, (
        f"{PVC} est lié à {pvc['spec'].get('volumeName')!r} au lieu de {PV}."
    )


# ----------------------------------------------------------------------
# 3. Le Pod monte la réclamation et y a écrit.
# ----------------------------------------------------------------------
def test_le_pod_monte_le_volume_et_a_ecrit(host):
    pod = _pod_pret(host)
    volumes = {
        v["name"]: (v.get("persistentVolumeClaim") or {}).get("claimName")
        for v in pod["spec"].get("volumes") or []
    }
    montes = [
        m for c in pod["spec"]["containers"] for m in c.get("volumeMounts") or []
        if m.get("mountPath", "").rstrip("/") == "/data" and volumes.get(m.get("name")) == PVC
    ]
    assert montes, (
        f"{POD} ne monte pas la réclamation {PVC} sur /data (volumes : {volumes}). Le volume du "
        "Pod doit être un persistentVolumeClaim, et le conteneur le monter sur /data."
    )
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- cat /data/test.txt")
    assert res.rc == 0 and res.stdout.strip() == "hello", (
        f"/data/test.txt dans {POD} vaut {res.stdout.strip()!r} (rc {res.rc}), attendu hello."
    )


# ----------------------------------------------------------------------
# 4. La preuve : le fichier est sur le disque du nœud.
# ----------------------------------------------------------------------
def test_le_fichier_est_sur_le_disque_du_noeud(host):
    pod = _pod_pret(host)
    chemin = _chemin_du_pv(_pv(host))
    noeud = pod["spec"].get("nodeName")
    assert noeud, f"{POD} n'est planifié sur aucun nœud."
    res = lab_host(noeud).run(f"sudo cat {chemin}/test.txt")
    assert res.rc == 0 and res.stdout.strip() == "hello", (
        f"Sur {noeud}, {chemin}/test.txt vaut {res.stdout.strip()!r} (rc {res.rc}), attendu hello. "
        "Le Pod voit son fichier mais le nœud ne l'a pas : /data n'est pas adossé à ce répertoire, "
        "et ce que le Pod écrit disparaîtra avec lui."
    )
