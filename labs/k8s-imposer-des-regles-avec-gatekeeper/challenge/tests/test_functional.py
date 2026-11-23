"""test_functional.py : k8s-imposer-des-regles-avec-gatekeeper

Trois affirmations, chacune lue sur le cluster : Gatekeeper tourne dans la
version demandée, il refuse à la création ce que la règle interdit (preuve par
de vraies soumissions en dry-run serveur), et son audit relève le Pod qui
tournait avant la règle.

Aucune n'est vraie avant le travail : au départ, Gatekeeper n'est pas installé,
tout Pod passe dans entrepot, et aucune contrainte n'existe pour porter un
audit.
"""

from __future__ import annotations

import json
import shlex
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "entrepot"
TEMOIN = "entrepot-temoin"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
VERSION = "v3.23.1"
IMAGE_INTERDITE = "docker.io/library/busybox:1.37"
IMAGE_AUTORISEE = "registry.k8s.io/pause:3.10"

# Le webhook de Gatekeeper sert une contrainte quelques secondes après sa
# création, et l'audit repasse toutes les 60 secondes par défaut. Budgets
# bornés, pour ne pas recaler un candidat dont le travail est juste.
BUDGET_ADMISSION_S = 60
BUDGET_AUDIT_S = 150
PAS_S = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    res = host.run(f"sudo {KUBECTL} {args}")
    diagnostic = "\n".join(
        ligne for ligne in res.stderr.splitlines()
        if not ligne.startswith("Warning: Permanently added")
    )
    return res.rc, res.stdout.strip(), diagnostic.strip()


def _soumettre(host, namespace: str, image: str):
    """Soumet un Pod en dry-run serveur. Rend (code, message)."""
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "sonde-registre"},
        "spec": {"containers": [{"name": "c", "image": image}]},
    }
    res = host.run(
        f"echo {shlex.quote(json.dumps(pod))} | sudo {KUBECTL} -n {namespace} "
        "create --dry-run=server -f -"
    )
    diagnostic = "\n".join(
        ligne for ligne in res.stderr.splitlines()
        if not ligne.startswith("Warning: Permanently added")
    )
    return res.rc, (diagnostic + res.stdout).strip()


# ----------------------------------------------------------------------
# 1. Gatekeeper v3.23.1 tourne.
# ----------------------------------------------------------------------
def test_gatekeeper_tourne_dans_la_version_demandee(host):
    rc, sortie, diagnostic = _kubectl(host, "-n gatekeeper-system get deployments -o json")
    deployments = {
        d["metadata"]["name"]: d for d in json.loads(sortie or "{}").get("items", [])
    } if rc == 0 else {}
    assert {"gatekeeper-controller-manager", "gatekeeper-audit"} <= set(deployments), message(
        en="Gatekeeper is not installed in gatekeeper-system: the "
        "gatekeeper-controller-manager and gatekeeper-audit Deployments are "
        f"expected, found {sorted(deployments)}. {diagnostic}",
        fr="Gatekeeper n'est pas installé dans gatekeeper-system : les "
        "Deployments gatekeeper-controller-manager et gatekeeper-audit sont "
        f"attendus, trouvés {sorted(deployments)}. {diagnostic}",
    )
    for nom, d in deployments.items():
        if nom not in ("gatekeeper-controller-manager", "gatekeeper-audit"):
            continue
        images = [c["image"] for c in d["spec"]["template"]["spec"]["containers"]]
        assert all(i.endswith(":" + VERSION) for i in images), message(
            en=f"{nom} runs {images}, not Gatekeeper {VERSION}. Install the "
            "version the team chose, pinned by its tag.",
            fr=f"{nom} fait tourner {images}, pas Gatekeeper {VERSION}. "
            "Installez la version choisie par l'équipe, épinglée par son tag.",
        )
        voulus = d["spec"].get("replicas", 1)
        prets = d["status"].get("readyReplicas", 0)
        assert prets == voulus, message(
            en=f"{nom}: {prets} replica(s) ready out of {voulus}.",
            fr=f"{nom} : {prets} réplica(s) prêt(s) sur {voulus}.",
        )


# ----------------------------------------------------------------------
# 2. LE test : dans entrepot, Gatekeeper refuse les registres non autorisés.
# ----------------------------------------------------------------------
def test_gatekeeper_refuse_un_registre_non_autorise_dans_entrepot_seulement(host):
    """Preuve ACTIVE, dans les deux sens et sur les deux namespaces.

    Le refus doit venir du webhook de Gatekeeper : son message commence par
    « admission webhook "validation.gatekeeper.sh" denied the request ». Une
    contrainte en dryrun ou en warn laisse passer, et ne compte donc pas.
    """
    fin = time.monotonic() + BUDGET_ADMISSION_S
    rc, refus = _soumettre(host, NAMESPACE, IMAGE_INTERDITE)
    while rc == 0 and time.monotonic() < fin:
        time.sleep(PAS_S)
        rc, refus = _soumettre(host, NAMESPACE, IMAGE_INTERDITE)

    assert rc != 0, message(
        en=f"After {BUDGET_ADMISSION_S} seconds, a Pod using {IMAGE_INTERDITE} is "
        f"still accepted in {NAMESPACE}. A constraint in dryrun or warn mode "
        "lets it through: only deny refuses.",
        fr=f"Après {BUDGET_ADMISSION_S} secondes, un Pod qui utilise "
        f"{IMAGE_INTERDITE} est toujours accepté dans {NAMESPACE}. Une "
        "contrainte en dryrun ou en warn le laisse passer : seul deny refuse.",
    )
    assert "validation.gatekeeper.sh" in refus, message(
        en=f"The Pod is refused, but not by Gatekeeper: {refus}",
        fr=f"Le Pod est refusé, mais pas par Gatekeeper : {refus}",
    )

    rc, diagnostic = _soumettre(host, NAMESPACE, IMAGE_AUTORISEE)
    assert rc == 0, message(
        en=f"A Pod using {IMAGE_AUTORISEE}, from the allowed registry, is refused "
        f"too in {NAMESPACE}: {diagnostic}. The rule must let registry.k8s.io/ "
        "through.",
        fr=f"Un Pod qui utilise {IMAGE_AUTORISEE}, du registre autorisé, est "
        f"refusé lui aussi dans {NAMESPACE} : {diagnostic}. La règle doit laisser "
        "passer registry.k8s.io/.",
    )

    rc, diagnostic = _soumettre(host, TEMOIN, IMAGE_INTERDITE)
    assert rc == 0, message(
        en=f"In {TEMOIN}, a Pod using {IMAGE_INTERDITE} is refused: {diagnostic}. "
        f"The rule must only apply to {NAMESPACE}.",
        fr=f"Dans {TEMOIN}, un Pod qui utilise {IMAGE_INTERDITE} est refusé : "
        f"{diagnostic}. La règle ne doit s'appliquer qu'à {NAMESPACE}.",
    )


# ----------------------------------------------------------------------
# 3. L'audit relève ancien-stock, qui tournait avant la règle.
# ----------------------------------------------------------------------
def test_l_audit_releve_ancien_stock(host):
    rc, phase, _ = _kubectl(
        host, f"-n {NAMESPACE} get pod ancien-stock -o jsonpath='{{.status.phase}}'"
    )
    assert rc == 0 and phase == "Running", message(
        en="The Pod ancien-stock no longer runs. Do not delete it: it is the "
        "existing resource the audit must find.",
        fr="Le Pod ancien-stock ne tourne plus. Ne le supprimez pas : c'est la "
        "ressource existante que l'audit doit trouver.",
    )

    # Pas de « kubectl get constraints » : c'est une CATÉGORIE, que kubectl
    # résout dans son cache de découverte sans le rafraîchir quand elle manque.
    # Un cache pris avant l'installation de Gatekeeper fait alors répondre
    # « doesn't have a resource type », même contraintes en place (mesuré le
    # 2026-11-23). On énumère les CRD du groupe, puis chacune par son nom
    # complet, que kubectl sait rafraîchir.
    trouve, vus = False, []
    fin = time.monotonic() + BUDGET_AUDIT_S
    while True:
        rc, noms, _ = _kubectl(
            host,
            "get crd -o jsonpath='{range .items[?(@.spec.group==\"constraints.gatekeeper.sh\")]}"
            "{.metadata.name}{\"\\n\"}{end}'",
        )
        contraintes = []
        for crd in noms.split() if rc == 0 else []:
            rc_c, sortie, _ = _kubectl(host, f"get {crd} -o json")
            if rc_c == 0:
                contraintes += json.loads(sortie or "{}").get("items", [])
        vus = [c["metadata"]["name"] for c in contraintes]
        for c in contraintes:
            for v in (c.get("status") or {}).get("violations") or []:
                if v.get("namespace") == NAMESPACE and v.get("name") == "ancien-stock":
                    trouve = True
        # Sans aucune CRD de contrainte, inutile d'attendre un audit qui ne
        # viendra jamais.
        if trouve or rc != 0 or not noms.split() or time.monotonic() > fin:
            break
        time.sleep(PAS_S)

    assert trouve, message(
        en=f"No constraint lists ancien-stock among its audit violations (constraints "
        f"seen: {vus or 'none'}). Admission only checks new requests: a Pod "
        "that was already running is only found by the audit, which runs every "
        "60 seconds and writes into the status of the constraint.",
        fr=f"Aucune contrainte ne liste ancien-stock dans les violations de son "
        f"audit (contraintes vues : {vus or 'aucune'}). L'admission ne contrôle "
        "que les nouvelles requêtes : un Pod qui tournait déjà n'est trouvé que "
        "par l'audit, qui passe toutes les 60 secondes et écrit dans le status "
        "de la contrainte.",
    )
