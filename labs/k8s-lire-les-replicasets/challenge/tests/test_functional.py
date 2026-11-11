"""test_functional.py : k8s-lire-les-replicasets

Ces tests confrontent le relevé ~/replicasets/releve.txt à l'état réel du
cluster, puis vérifient la réparation de compte-absent. Un test vérifie un seul
état demandé par l'énoncé.

Les ReplicaSets de api sont retrouvés par leur propriétaire, le Deployment api,
et départagés par l'annotation de révision : l'actif porte la révision du
Deployment, l'ancien est gardé à zéro réplica. Les noms consignés doivent être
ceux-là exactement, casse et espaces mis à part.

compte-absent doit être RÉPARÉ, pas recréé : il garde l'uid mémorisé par le
setup. Les deux voies de réparation sont acceptées, créer le ServiceAccount
manquant ou retirer serviceAccountName du modèle de Pod. Aucune attente ne
s'ouvre tant que la cause est encore là.
"""

from __future__ import annotations

import json
import time
import unicodedata

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "replicasets"
MEMOIRE = "/var/lib/dsoxlab/lire-les-replicasets.json"
RELEVE = f"~/{NS}/releve.txt"
REVISION = "deployment.kubernetes.io/revision"
COMPTE = "compte-absent"
ATTENTE = 90
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    assert res.rc == 0, message(
        en="The memory of the initial state is missing: run dsoxlab reset k8s-lire-les-replicasets.",
        fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-lire-les-replicasets.",
    )
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/{NS}/releve.txt")
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if ligne and not ligne.startswith("#") and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


def _valeur(releve: dict[str, str], cle: str) -> str:
    valeur = releve.get(cle, "")
    assert valeur, message(
        en=f"The key {cle!r} of {RELEVE} has no value.",
        fr=f"La clé {cle!r} de {RELEVE} n'a pas de valeur.",
    )
    return valeur


def _nom(texte: str) -> str:
    """Un nom d'objet consigné : sans casse, sans espaces, sans préfixe de type
    (« replicaset/api-xxx » et « api-xxx » se valent)."""
    nom = texte.strip().strip("`'\"").lower()
    return nom.split("/", 1)[1] if "/" in nom else nom


def _compact(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if c.isalnum())


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _replicasets_de_api(host) -> tuple[dict, list[dict]]:
    """Le Deployment api et ses ReplicaSets, retrouvés par ownerReferences."""
    dep = _json(host, "get deployment api")
    assert dep is not None, message(
        en=f"No Deployment api in {NS}: run dsoxlab reset k8s-lire-les-replicasets.",
        fr=f"Aucun Deployment api dans {NS} : lancez dsoxlab reset k8s-lire-les-replicasets.",
    )
    tous = (_json(host, "get replicaset") or {}).get("items") or []
    siens = [
        rs for rs in tous
        if any(ref.get("uid") == dep["metadata"]["uid"]
               for ref in rs["metadata"].get("ownerReferences") or [])
    ]
    return dep, siens


# ----------------------------------------------------------------------
# 1. Le ReplicaSet actif de api.
# ----------------------------------------------------------------------
def test_le_replicaset_actif_de_api_est_consigne(host, releve):
    valeur = _valeur(releve, "replicaset-actif")
    dep, siens = _replicasets_de_api(host)
    revision = (dep["metadata"].get("annotations") or {}).get(REVISION)
    actifs = [rs["metadata"]["name"] for rs in siens
              if (rs["metadata"].get("annotations") or {}).get(REVISION) == revision
              and rs["spec"].get("replicas", 0) > 0]
    assert _nom(valeur) in actifs, message(
        en=f"replicaset-actif is {valeur!r}, which is not the active ReplicaSet of api. The "
        "active one carries the replicas; kubectl get replicaset -l app=api lists both, with "
        "their DESIRED column. Reread the section of the lesson on what an update creates.",
        fr=f"replicaset-actif vaut {valeur!r}, qui n'est pas le ReplicaSet actif de api. "
        "L'actif porte les réplicas ; kubectl get replicaset -l app=api liste les deux, avec "
        "leur colonne DESIRED. Relisez la section de la leçon sur ce que crée une mise à jour.",
    )


# ----------------------------------------------------------------------
# 2. L'ancien ReplicaSet de api, gardé à zéro.
# ----------------------------------------------------------------------
def test_l_ancien_replicaset_de_api_est_consigne(host, releve):
    valeur = _valeur(releve, "replicaset-ancien")
    _, siens = _replicasets_de_api(host)
    anciens = [rs["metadata"]["name"] for rs in siens if rs["spec"].get("replicas", 0) == 0]
    assert _nom(valeur) in anciens, message(
        en=f"replicaset-ancien is {valeur!r}, which is not the ReplicaSet of api kept at zero. "
        "After an update, the Deployment keeps the previous ReplicaSet at 0 replicas, for the "
        "rollback. Reread the section of the lesson on what an update creates.",
        fr=f"replicaset-ancien vaut {valeur!r}, qui n'est pas le ReplicaSet de api gardé à "
        "zéro. Après une mise à jour, le Deployment garde l'ancien ReplicaSet à 0 réplica, "
        "pour le retour arrière. Relisez la section de la leçon sur ce que crée une mise à jour.",
    )


# ----------------------------------------------------------------------
# 3. La cause du FailedCreate.
# ----------------------------------------------------------------------
def test_la_cause_du_failedcreate_est_consignee(releve):
    valeur = _valeur(releve, "cause-failedcreate")
    lue = _compact(valeur)
    nomme_le_compte = any(m in lue for m in ("serviceaccount", "comptedeservice"))
    assert nomme_le_compte, message(
        en=f"cause-failedcreate is {valeur!r}. The ReplicaSet of compte-absent says why it "
        "creates no Pod in its Events (kubectl describe replicaset -l app=compte-absent): the "
        "object it looks for and does not find must be named. Reread the section of the "
        "lesson on FailedCreate.",
        fr=f"cause-failedcreate vaut {valeur!r}. Le ReplicaSet de compte-absent dit pourquoi "
        "il ne crée aucun Pod dans ses Events (kubectl describe replicaset -l "
        "app=compte-absent) : il faut nommer l'objet qu'il cherche et ne trouve pas. Relisez "
        "la section de la leçon sur FailedCreate.",
    )


# ----------------------------------------------------------------------
# 4. compte-absent réparé, sans être recréé.
# ----------------------------------------------------------------------
def _cause_levee(host, dep: dict) -> bool:
    compte = dep["spec"]["template"]["spec"].get("serviceAccountName") or ""
    if compte in ("", "default"):
        return True
    return host.run(f"{ADMIN} -n {NS} get serviceaccount {compte}").rc == 0


def test_compte_absent_repare_a_ses_deux_replicas_disponibles(host, memoire):
    dep = _json(host, f"get deployment {COMPTE}")
    assert dep is not None, message(
        en=f"No Deployment {COMPTE} in {NS}: it was deleted. It is repaired, not recreated. "
        "Run dsoxlab reset k8s-lire-les-replicasets to start over.",
        fr=f"Aucun Deployment {COMPTE} dans {NS} : il a été supprimé. Il se répare, il ne se "
        "recrée pas. Lancez dsoxlab reset k8s-lire-les-replicasets pour repartir.",
    )
    assert dep["metadata"]["uid"] == memoire[COMPTE], message(
        en=f"{COMPTE} is a new Deployment, recreated under the same name. The repair keeps "
        "the object: create what its Pods are missing, or correct its Pod template. Run "
        "dsoxlab reset k8s-lire-les-replicasets and repair without deleting.",
        fr=f"{COMPTE} est un nouveau Deployment, recréé sous le même nom. La réparation garde "
        "l'objet : créez ce qui manque à ses Pods, ou corrigez son modèle de Pod. Lancez "
        "dsoxlab reset k8s-lire-les-replicasets et réparez sans supprimer.",
    )
    demandes = dep["spec"].get("replicas", 1)
    assert demandes == 2, message(
        en=f"{COMPTE} asks for {demandes} replica(s), expected 2: the request does not change, "
        "only what prevents it.",
        fr=f"{COMPTE} demande {demandes} réplica(s), attendu 2 : la demande ne change pas, "
        "seul ce qui l'empêche.",
    )
    assert _cause_levee(host, dep), message(
        en=f"The Pods of {COMPTE} still ask for a ServiceAccount that does not exist in {NS}. "
        "Two repairs are possible: create it, or remove the reference from the Pod template.",
        fr=f"Les Pods de {COMPTE} demandent toujours un ServiceAccount qui n'existe pas dans "
        f"{NS}. Deux réparations sont possibles : le créer, ou retirer la référence du modèle "
        "de Pod.",
    )
    # La cause est levée : le contrôleur réessaie seul, on lui en laisse le temps.
    fin = time.monotonic() + ATTENTE
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    while disponibles != 2 and time.monotonic() < fin:
        time.sleep(PAS)
        dep = _json(host, f"get deployment {COMPTE}") or dep
        disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert disponibles == 2, message(
        en=f"{COMPTE}: {disponibles} replica(s) available out of 2 after {ATTENTE}s, although "
        "the cause is removed. After many failures the controller waits longer before "
        "retrying: kubectl rollout restart deployment/compte-absent has it retry at once, "
        "and kubectl describe replicaset -l app=compte-absent says what still blocks.",
        fr=f"{COMPTE} : {disponibles} réplica(s) disponible(s) sur 2 après {ATTENTE}s, alors "
        "que la cause est levée. Après de nombreux échecs, le contrôleur attend plus "
        "longtemps avant de réessayer : kubectl rollout restart deployment/compte-absent le "
        "fait réessayer tout de suite, et kubectl describe replicaset -l app=compte-absent "
        "dit ce qui bloque encore.",
    )
