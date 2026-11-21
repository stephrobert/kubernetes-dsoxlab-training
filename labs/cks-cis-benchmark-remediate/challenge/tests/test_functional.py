"""test_functional.py : cks-cis-benchmark-remediate

Deux affirmations qui relancent l'audit du worker, jamais les commandes tapées.

Depuis le 2026-11-21, le lab audite le WORKER k8s-w1.lab (cible node de
kube-bench) et non plus le control plane : le profilage qu'il faisait corriger
est le sujet de cks-api-server-hardening, et les deux labs se recouvraient.

Les deux tests relancent kube-bench et comptent. C'est le seul moyen honnête
de mesurer une remédiation : un rapport qui affirme avoir corrigé quelque
chose sans relancer l'outil n'affirme rien de vérifiable.

Le seuil n'est pas fixe au-delà des deux contrôles visés : on exige qu'ils
passent ET que le total d'échecs du nœud ait baissé, ce qui attrape une
correction qui en casserait une autre au passage.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "conformite"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-w1.lab"
#: Les deux contrôles que le référentiel reproche au worker par défaut, et qui
#: partagent une même cause : des fichiers du kubelet trop ouverts.
CONTROLES_VISES = ("4.1.1", "4.1.9")
#: Mesuré le 2026-11-21 sur ce socle avec kube-bench v0.16.0 : deux échecs sur
#: la cible node avant toute correction, 4.1.1 et 4.1.9.
ECHECS_AU_DEPART = 2


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


@pytest.fixture(scope="module")
def rapport(host) -> dict:
    """Relance kube-bench sur le worker et rend son rapport, décodé.

    L'audit est REJOUÉ ici, une fois pour les deux tests, et non lu dans un
    fichier que le candidat aurait laissé : un rapport peut être édité, un
    audit qui tourne sous nos yeux ne peut pas l'être.
    """
    _kubectl(host, f"-n {NAMESPACE} delete job kube-bench --ignore-not-found --wait=true")
    rc, _, diagnostic = _kubectl(host, "apply -f /root/kube-bench-job.yaml")
    if rc != 0:
        pytest.fail(message(
            en=f"The kube-bench Job could not be created. {diagnostic}",
            fr=f"Le Job kube-bench n'a pas pu être créé. {diagnostic}",
        ))
    rc, _, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} wait --for=condition=complete job/kube-bench --timeout=300s"
    )
    if rc != 0:
        pytest.fail(message(
            en=f"The kube-bench audit did not finish. {diagnostic}",
            fr=f"L'audit kube-bench ne s'est pas terminé. {diagnostic}",
        ))
    rc, journal, diagnostic = _kubectl(host, f"-n {NAMESPACE} logs job/kube-bench")
    debut = journal.find("{")
    if rc != 0 or debut < 0:
        pytest.fail(message(
            en=f"The audit wrote no JSON report. {diagnostic}",
            fr=f"L'audit n'a écrit aucun rapport JSON. {diagnostic}",
        ))
    return json.loads(journal[debut:])


def _resultats(rapport: dict) -> dict[str, str]:
    """Chaque contrôle du rapport, numéro vers état."""
    etats = {}
    for controle in rapport.get("Controls", []):
        for groupe in controle.get("tests", []):
            for resultat in groupe.get("results", []):
                etats[str(resultat.get("test_number"))] = str(resultat.get("status"))
    return etats


# ----------------------------------------------------------------------
# 1. Les deux contrôles visés passent à l'audit rejoué.
# ----------------------------------------------------------------------
def test_les_deux_controles_vises_passent(rapport):
    """Le référentiel reproche la même faiblesse à deux fichiers. En corriger
    un seul en laisse un ouvert, et c'est l'erreur la plus courante : on lit le
    premier échec, on corrige, on croit avoir fini."""
    etats = _resultats(rapport)
    encore = [c for c in CONTROLES_VISES if etats.get(c) != "PASS"]
    assert not encore, message(
        en="These CIS controls still fail when the audit of the worker is replayed: "
        + ", ".join(f"{c} ({etats.get(c, 'absent from the report')})" for c in encore)
        + ". The remediation is run on the audited node, k8s-w1.lab, not on the "
        "control plane.",
        fr="Ces contrôles CIS échouent toujours à l'audit rejoué du worker : "
        + ", ".join(f"{c} ({etats.get(c, 'absent du rapport')})" for c in encore)
        + ". La remédiation se joue sur le nœud audité, k8s-w1.lab, pas sur le "
        "control plane.",
    )


# ----------------------------------------------------------------------
# 2. Le total baisse, et le worker reste un nœud du cluster.
# ----------------------------------------------------------------------
def test_le_total_baisse_et_le_noeud_reste_pret(host, rapport):
    """Un nœud qui ne sert plus passe aussi l'audit de ses fichiers : on exige
    donc dans le même test que le total d'échecs ait baissé ET que le worker
    soit toujours Ready."""
    total = sum(int(c.get("total_fail", 0)) for c in rapport.get("Controls", []))
    assert total < ECHECS_AU_DEPART, message(
        en=f"The audit of the worker still counts {total} failure(s), against "
        f"{ECHECS_AU_DEPART} at the start. Fixing one control by breaking another "
        "does not bring the count down.",
        fr=f"L'audit du worker compte encore {total} échec(s), contre "
        f"{ECHECS_AU_DEPART} au départ. Corriger un contrôle en cassant un autre "
        "ne fait pas baisser le compte.",
    )
    rc, pret, _ = _kubectl(
        host,
        "get node " + NOEUD + " -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'",
    )
    assert rc == 0 and pret == "True", message(
        en=f"The worker {NOEUD} is no longer Ready ({pret or 'unreadable'}). A "
        "hardening that stops the kubelet is not one: `systemctl status kubelet` "
        "on the node gives the reason.",
        fr=f"Le worker {NOEUD} n'est plus Ready ({pret or 'illisible'}). Un "
        "durcissement qui arrête le kubelet n'en est pas un : `systemctl status "
        "kubelet` sur le nœud donne la raison.",
    )
