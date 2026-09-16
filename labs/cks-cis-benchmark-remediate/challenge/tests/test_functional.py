"""test_functional.py : cks-cis-benchmark-remediate

Deux affirmations qui lisent les manifestes du nœud et relancent l'audit,
jamais les commandes tapées.

Le dernier test relance kube-bench et compte. C'est le seul moyen honnête de
mesurer une remédiation : un rapport qui affirme avoir corrigé quelque chose
sans relancer l'outil n'affirme rien de vérifiable, et c'est exactement ce que
le lab hérité demandait, sous la forme d'un ConfigMap de texte libre.

Le seuil n'est pas fixe. On exige que les trois contrôles visés passent ET que
le total d'échecs ait baissé, ce qui reste vrai quelle que soit la version du
référentiel : kube-bench en ajoute à chaque publication, et un nombre écrit en
dur serait faux à la prochaine.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "conformite"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
MANIFESTES = "/etc/kubernetes/manifests"
COMPOSANTS = ("kube-apiserver", "kube-controller-manager", "kube-scheduler")
#: Les trois contrôles que le référentiel reproche au control plane par
#: défaut, et qui partagent une même cause.
CONTROLES_VISES = ("1.2.15", "1.3.2", "1.4.1")
#: Mesuré le 2026-09-16 sur ce socle : dix échecs avant toute correction.
ECHECS_AU_DEPART = 10


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _audit(host) -> dict:
    """Relance kube-bench et rend son rapport, décodé.

    L'audit est REJOUÉ ici, et non lu dans un fichier que le candidat aurait
    laissé : un rapport peut être édité, un audit qui tourne sous nos yeux ne
    peut pas l'être.
    """
    _kubectl(host, f"-n {NAMESPACE} delete job kube-bench --ignore-not-found --wait=true")
    rc, _, diagnostic = _kubectl(host, "apply -f /root/kube-bench-job.yaml")
    assert rc == 0, f"Le Job kube-bench n'a pas pu être créé. {diagnostic}"

    rc, _, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} wait --for=condition=complete job/kube-bench --timeout=300s"
    )
    assert rc == 0, (
        f"L'audit kube-bench ne s'est pas terminé. {diagnostic}"
    )
    rc, pod, _ = _kubectl(
        host, f"-n {NAMESPACE} get pods -l job-name=kube-bench "
        "-o jsonpath='{.items[0].metadata.name}'"
    )
    assert rc == 0 and pod, "Le Pod de l'audit est introuvable."
    rc, journal, diagnostic = _kubectl(host, f"-n {NAMESPACE} logs {pod}")
    assert rc == 0 and journal, f"L'audit n'a rien écrit. {diagnostic}"

    debut = journal.find("{")
    assert debut >= 0, "La sortie de kube-bench ne contient pas de JSON."
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
# 1. Les trois manifestes portent la correction.
# ----------------------------------------------------------------------
def test_les_trois_composants_portent_la_correction(host):
    """Le référentiel reproche le même réglage à trois composants. En corriger
    un seul laisse deux portes ouvertes, et c'est l'erreur la plus courante :
    on lit le premier échec, on corrige, on croit avoir fini."""
    manquants = []
    for composant in COMPOSANTS:
        res = host.run(f"sudo cat {MANIFESTES}/{composant}.yaml")
        if res.rc != 0:
            manquants.append(f"{composant} (manifeste illisible)")
        elif "--profiling=false" not in res.stdout:
            manquants.append(composant)
    assert not manquants, (
        f"Ces composants n'ont pas été corrigés : {', '.join(manquants)}. Le "
        "référentiel CIS reproche le même réglage aux trois, sous trois "
        "numéros différents."
    )


# ----------------------------------------------------------------------
# 2. LE test : l'audit rejoué compte moins d'échecs.
# ----------------------------------------------------------------------
def test_l_audit_rejoue_compte_moins_d_echecs(host):
    """On relance l'outil, on ne relit pas un rapport.

    Les trois contrôles visés doivent passer, et le total d'échecs doit avoir
    baissé. Cette seconde condition attrape une correction qui en casserait
    une autre au passage, ce qu'un contrôle par contrôle ne verrait pas.
    """
    # On ATTEND que le control plane soit revenu avant de mesurer quoi que ce
    # soit. Trois Pods statiques redémarrent, et l'état de chaque objet met un
    # instant à remonter : mesuré le 2026-09-16, le test lisait « Running
    # Running Running Pending » et rendait ROUGE un travail juste. C'est le
    # même piège que le NodePort et que le Pod statique de l'audit : un état
    # correct dans l'API n'est pas encore un état stabilisé.
    #
    # Cette vérification n'a pas de test à elle : « le control plane répond »
    # est vrai AVANT le travail comme après, et un test toujours vrai ne
    # mesure rien.
    for _ in range(40):
        rc, phases, _ = _kubectl(
            host,
            "-n kube-system get pods -l tier=control-plane "
            "-o jsonpath='{.items[*].status.phase}'",
        )
        if rc == 0 and phases and "Pending" not in phases:
            break
        host.run("sleep 3")
    assert rc == 0 and phases and "Pending" not in phases, (
        f"Un Pod du control plane reste en {phases or 'état illisible'} après "
        "deux minutes. Le kubelet n'a pas réussi à le redémarrer avec les "
        "nouveaux réglages : `sudo crictl ps -a` puis `sudo crictl logs <id>` "
        "donnent la raison."
    )

    rapport = _audit(host)
    etats = _resultats(rapport)

    encore_en_echec = [c for c in CONTROLES_VISES if etats.get(c) != "PASS"]
    assert not encore_en_echec, (
        "Ces contrôles CIS échouent toujours après l'audit rejoué : "
        + ", ".join(f"{c} ({etats.get(c, 'absent du rapport')})" for c in encore_en_echec)
        + ". Le manifeste est peut-être corrigé sans que le kubelet ait repris "
        "le Pod : vérifiez que le composant a redémarré."
    )

    total = sum(int(c.get("total_fail", 0)) for c in rapport.get("Controls", []))
    assert total < ECHECS_AU_DEPART, (
        f"L'audit compte encore {total} échec(s), contre {ECHECS_AU_DEPART} au "
        "départ. Corriger un contrôle en cassant un autre ne fait pas baisser "
        "le compte, et c'est ce que cette mesure globale attrape."
    )
