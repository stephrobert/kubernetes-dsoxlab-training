"""test_functional.py : cka-hpa-autoscaling

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le spec du HPA. La deuxième lit ses
métriques courantes : un HPA qui affiche <unknown> ne décidera jamais rien.
La troisième lit les events du contrôleur : un SuccessfulRescale vers deux
replicas ou plus, pour une utilisation au-dessus de la cible, est la trace
qu'une montée a eu lieu. La quatrième veut la charge coupée, et comme un
cluster jamais chargé n'a pas de générateur non plus, elle exige aussi que
la montée ait eu lieu.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
HPA = "php-apache-hpa"
DEPLOYMENT = "php-apache"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _hpa(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get hpa {HPA} -o json")
    assert res.rc == 0, message(
        en=f"No HorizontalPodAutoscaler {HPA} in {NAMESPACE}.",
        fr=f"Aucun HorizontalPodAutoscaler {HPA} dans {NAMESPACE}.",
    )
    return json.loads(res.stdout)


def _montees(host) -> list[str]:
    """Les messages SuccessfulRescale du contrôleur qui ont fait grossir le Deployment."""
    res = _kubectl(host, f"-n {NAMESPACE} get events --field-selector reason=SuccessfulRescale,involvedObject.name={HPA} -o json")
    if res.rc != 0:
        return []
    messages = [e.get("message", "") for e in json.loads(res.stdout).get("items") or []]
    return [m for m in messages if "above target" in m]


# ----------------------------------------------------------------------
# 1. Le HPA est déclaré comme demandé.
# ----------------------------------------------------------------------
def test_le_hpa_est_declare(host):
    hpa = _hpa(host)
    cible = hpa["spec"].get("scaleTargetRef") or {}
    assert (cible.get("kind"), cible.get("name")) == ("Deployment", DEPLOYMENT), message(
        en=f"The HPA targets {cible.get('kind')}/{cible.get('name')} instead of Deployment/{DEPLOYMENT}.",
        fr=f"Le HPA vise {cible.get('kind')}/{cible.get('name')} au lieu de Deployment/{DEPLOYMENT}.",
    )
    assert hpa["spec"].get("minReplicas") == 1 and hpa["spec"].get("maxReplicas") == 10, message(
        en=f"min {hpa['spec'].get('minReplicas')} and max {hpa['spec'].get('maxReplicas')}, expected 1 and 10.",
        fr=f"min {hpa['spec'].get('minReplicas')} et max {hpa['spec'].get('maxReplicas')}, attendu 1 et 10.",
    )
    cpu = [
        m for m in hpa["spec"].get("metrics") or []
        if m.get("type") == "Resource" and (m.get("resource") or {}).get("name") == "cpu"
    ]
    assert cpu, message(
        en="The HPA has no Resource metric on cpu: that is the metrics block of autoscaling/v2.",
        fr="Le HPA n'a pas de métrique Resource sur cpu : c'est le bloc metrics d'autoscaling/v2.",
    )
    target = (cpu[0]["resource"].get("target") or {})
    assert target.get("type") == "Utilization" and target.get("averageUtilization") == 50, message(
        en=f"The CPU target is {target}, expected type Utilization and averageUtilization 50.",
        fr=f"La cible CPU est {target}, attendu type Utilization et averageUtilization 50.",
    )


# ----------------------------------------------------------------------
# 2. Le HPA lit des métriques.
# ----------------------------------------------------------------------
def test_le_hpa_lit_des_metriques(host):
    courantes: list[dict] = []
    for _ in range(12):
        courantes = [
            m for m in (_hpa(host).get("status") or {}).get("currentMetrics") or []
            if (m.get("resource") or {}).get("name") == "cpu"
            and ((m["resource"].get("current") or {}).get("averageUtilization") is not None)
        ]
        if courantes:
            return
        time.sleep(5)
    conditions = {c["type"]: c.get("message", "") for c in (_hpa(host).get("status") or {}).get("conditions") or []}
    assert courantes, message(
        en=f"The HPA has no current CPU metric after one minute: its target reads <unknown>. "
        f"Conditions: {conditions}. The Pods need CPU requests and the metrics-server must "
        "answer: kubectl top pods -n lab tells you.",
        fr=f"Le HPA n'a pas de métrique CPU courante après une minute : sa cible est <unknown>. "
        f"Conditions : {conditions}. Il faut des requests CPU sur les Pods et un metrics-server "
        "qui répond : kubectl top pods -n lab le dit.",
    )


# ----------------------------------------------------------------------
# 3. Une montée en charge a eu lieu.
# ----------------------------------------------------------------------
def test_une_montee_a_eu_lieu(host):
    montees = _montees(host)
    assert montees, message(
        en="No SuccessfulRescale \"above target\" event on the HPA: the Deployment never scaled "
        "up under load. You have to generate load from a Pod, towards the php-apache Service, "
        "and give the controller one or two minutes. kubectl describe hpa narrates its decisions.",
        fr="Aucun event SuccessfulRescale « above target » sur le HPA : le Deployment n'est jamais "
        "monté sous charge. Il faut générer de la charge depuis un Pod, vers le Service php-apache, "
        "et laisser une à deux minutes au contrôleur. kubectl describe hpa raconte ses décisions.",
    )


# ----------------------------------------------------------------------
# 4. La charge est coupée, après avoir servi.
# ----------------------------------------------------------------------
def test_la_charge_est_coupee(host):
    assert _montees(host), message(
        en="No scale-up ever happened: nothing to cut, the work is not done.",
        fr="Aucune montée n'a eu lieu : rien à couper, le travail n'est pas fait.",
    )
    res = _kubectl(host, f"-n {NAMESPACE} get pods -o json")
    assert res.rc == 0, message(
        en=f"Listing the Pods of {NAMESPACE} failed: {res.stderr.strip()[:200]}",
        fr=f"La liste des Pods de {NAMESPACE} échoue : {res.stderr.strip()[:200]}",
    )
    generateurs = [
        p["metadata"]["name"] for p in json.loads(res.stdout)["items"]
        if not p["metadata"].get("deletionTimestamp")
        and p["status"].get("phase") == "Running"
        and (p["metadata"].get("labels") or {}).get("app") != DEPLOYMENT
    ]
    assert not generateurs, message(
        en=f"These Pods are still running in {NAMESPACE}: {generateurs}. The test load is cut "
        "once the observation is made, otherwise the Deployment stays inflated and the cluster pays.",
        fr=f"Ces Pods tournent encore dans {NAMESPACE} : {generateurs}. La charge de test se coupe "
        "quand l'observation est faite, sinon le Deployment reste gonflé et le cluster paie.",
    )
