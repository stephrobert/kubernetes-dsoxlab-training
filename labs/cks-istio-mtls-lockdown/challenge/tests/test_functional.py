"""test_functional.py : cks-istio-mtls-lockdown

Deux affirmations qui lisent l'état du cluster et l'effet réel sur le trafic,
jamais les commandes tapées.

Le dernier test exerce LES DEUX CÔTÉS depuis deux Pods distincts : celui qui
porte un sidecar doit continuer à joindre le service, celui qui n'en a pas ne
doit plus y arriver. Vérifier seulement que la PeerAuthentication existe ne
prouverait rien : un objet peut être posé en mode PERMISSIVE, ou viser un
selector qui ne désigne aucun Pod, et ne rien changer au trafic.

Les deux mesures sont dans le MÊME test, délibérément. « Le client maillé
passe » est déjà vrai AVANT le travail : isolée, cette assertion ferait un test
vert qui ne mesure rien. Elle n'a de sens qu'accolée à celle qui distingue.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "maillage"
NAMESPACE_NU = "dehors"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CIBLE = "http://service.maillage.svc.cluster.local/"

# Istio distribue la règle aux sidecars par istiod : elle n'agit pas à la
# seconde où l'objet entre dans l'API. Mesuré le 2026-09-16 : quelques
# secondes suffisent. Le budget est large pour ne jamais recaler un candidat
# dont la correction est juste, et borné pour que l'échec reste rapide.
BUDGET_PROPAGATION_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _joint_le_service(host, namespace: str, pod: str) -> bool:
    """Le Pod joint-il le service ? On regarde le code de retour de wget,
    pas sa sortie : un refus de connexion et une page vide se ressemblent."""
    rc, _, _ = _kubectl(
        host,
        f"-n {namespace} exec {pod} -c outil --request-timeout=30s "
        f"-- wget -qO- -T 5 {CIBLE}",
    )
    return rc == 0


# ----------------------------------------------------------------------
# 1. L'exigence est déclarée, et elle est STRICTE.
# ----------------------------------------------------------------------
def test_le_namespace_exige_le_tls_mutuel(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable. Un objet peut exister, être en
    PERMISSIVE, et laisser passer tout le trafic en clair."""
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get peerauthentication -o json"
    )
    assert rc == 0, (
        "Impossible de lire les PeerAuthentication du namespace "
        f"{NAMESPACE}. Le maillage est-il toujours installé ? {diagnostic}"
    )
    objets = json.loads(sortie).get("items", [])
    assert objets, (
        f"Aucune PeerAuthentication dans le namespace {NAMESPACE}. C'est "
        "l'objet par lequel un maillage Istio exige le TLS mutuel. Sans lui, "
        "le mode en vigueur est PERMISSIVE : le chiffré ET le clair sont "
        "acceptés, ce qui ne protège de rien."
    )

    modes = {
        o["metadata"]["name"]: o.get("spec", {}).get("mtls", {}).get("mode")
        for o in objets
    }
    pour_tout_le_namespace = [
        o
        for o in objets
        if not o.get("spec", {}).get("selector")
        and o.get("spec", {}).get("mtls", {}).get("mode") == "STRICT"
    ]
    assert pour_tout_le_namespace, (
        f"Les PeerAuthentication de {NAMESPACE} sont {modes}, et aucune "
        "n'impose STRICT à tout le namespace. PERMISSIVE accepte les deux "
        "trafics : c'est le mode de migration, pas celui d'une production. "
        "Une PeerAuthentication portant un selector ne vaut que pour les Pods "
        "qu'il désigne ; sans selector, elle vaut pour le namespace entier."
    )


# ----------------------------------------------------------------------
# 2. LE test : l'exigence agit, et elle n'a pas coupé le maillage.
# ----------------------------------------------------------------------
def test_le_client_sans_sidecar_est_bloque_et_le_client_maille_passe(host):
    """La preuve, prise des deux côtés.

    Avant le travail, les deux clients passent : ce test échoue, et c'est ce
    qui rend le lab mesurable. Après, seul celui qui présente un certificat de
    charge de travail est admis.

    Mesuré le 2026-09-16 : sans PeerAuthentication, le client nu obtient la
    page ; avec STRICT, sa connexion est refusée par le sidecar du service,
    tandis que le client maillé continue de la servir.
    """
    for pod, ns in (
        ("service", NAMESPACE),
        ("client-maille", NAMESPACE),
        ("client-nu", NAMESPACE_NU),
    ):
        rc, phase, diagnostic = _kubectl(
            host, f"-n {ns} get pod {pod} -o jsonpath='{{.status.phase}}'"
        )
        assert rc == 0 and phase == "Running", (
            f"Le Pod {pod} du namespace {ns} n'est pas Running mais "
            f"« {phase or 'absent'} ». Le setup les avait posés tous les "
            "trois : sans eux, la mesure qui suit ne veut rien dire. "
            f"{diagnostic}"
        )

    # L'effet réseau se mesure quand il est arrivé, pas quand l'objet est
    # accepté par l'API. On attend que le blocage s'installe, avec un budget
    # borné : un test qui n'attend pas recale un candidat dont la correction
    # est juste, et un faux négatif vaut pire qu'un test absent.
    fin = time.monotonic() + BUDGET_PROPAGATION_S
    nu_passe = True
    while time.monotonic() < fin:
        nu_passe = _joint_le_service(host, NAMESPACE_NU, "client-nu")
        if not nu_passe:
            break
        time.sleep(PAS_S)

    assert not nu_passe, (
        f"Après {BUDGET_PROPAGATION_S} secondes d'attente, le Pod client-nu "
        f"du namespace {NAMESPACE_NU} joint toujours {CIBLE} en clair. Il n'a "
        "pas de sidecar, donc pas de certificat de charge de travail : un "
        "namespace qui exige vraiment le TLS mutuel doit refuser sa "
        "connexion. Vérifiez que votre PeerAuthentication est bien dans le "
        f"namespace {NAMESPACE}, celui du SERVICE appelé, et qu'elle est en "
        "mode STRICT."
    )

    maille_passe = _joint_le_service(host, NAMESPACE, "client-maille")
    assert maille_passe, (
        f"Le Pod client-maille ne joint plus {CIBLE}, alors qu'il porte un "
        "sidecar et qu'il y arrivait avant votre intervention. Exiger le TLS "
        "mutuel ne doit pas couper le maillage : il doit couper ce qui est "
        "HORS du maillage. Regardez si vous n'avez pas posé l'exigence sur "
        "tout le mesh, dans le namespace d'Istio, ou ajouté une "
        "AuthorizationPolicy qui refuse au-delà de ce qui était demandé."
    )
