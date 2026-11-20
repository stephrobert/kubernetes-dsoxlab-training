"""test_functional.py : k8s-observer-la-reconciliation

Ces tests confrontent l'état du cluster et le relevé ~/reconciliation/releve.txt
à la mémoire de l'état initial posée par le setup (uid du ReplicaSet de départ,
génération du Deployment). Un test vérifie un seul état demandé.

Supprimer le ReplicaSet emporte ses Pods : après coup, le cluster ne garde
aucune trace du Pod supprimé à la première étape. La preuve est donc lue dans
les événements du ReplicaSet de départ, qui survivent à sa suppression : il a
annoncé plus de créations de Pods que ses trois réplicas initiaux.

Le remplacement du ReplicaSet est jugé avec la génération du Deployment : un
`kubectl rollout restart` ou une modification du template créeraient eux
aussi un nouveau ReplicaSet, mais en changeant le Deployment, ce qui n'est
plus une réconciliation.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/architecture.kubeconfig"
NS = "reconciliation"
MEMOIRE = "/var/lib/dsoxlab/observer-la-reconciliation.json"
REPLICAS_INITIAUX = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str, absent: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    assert res.rc == 0, message(
        en="The memory of the initial state is missing: run dsoxlab reset.",
        fr="La mémoire de l'état initial est absente : lancez dsoxlab reset.",
    )
    return json.loads(res.stdout)


def _releve(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/reconciliation/releve.txt")
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
        en=f"The key {cle!r} of ~/reconciliation/releve.txt has no value.",
        fr=f"La clé {cle!r} de ~/reconciliation/releve.txt n'a pas de valeur.",
    )
    return valeur


# ----------------------------------------------------------------------
# 1. Un Pod supprimé, recréé par son ReplicaSet.
# ----------------------------------------------------------------------
def test_le_pod_supprime_a_ete_recree_par_son_replicaset(host, memoire):
    evenements = _json(
        host,
        f"-n {NS} get events --field-selector "
        f"involvedObject.uid={memoire['replicaset']},reason=SuccessfulCreate",
        message(en="Cannot read the events of the initial ReplicaSet.",
                fr="Impossible de lire les événements du ReplicaSet de départ."),
    ).get("items") or []
    creations = {e.get("message", "") for e in evenements}
    assert len(creations) > REPLICAS_INITIAUX, message(
        en=f"The initial ReplicaSet created {len(creations)} Pod(s), only its initial ones: "
           "delete one Pod of vitrine and let it be recreated, before touching the ReplicaSet.",
        fr=f"Le ReplicaSet de départ a créé {len(creations)} Pod(s), seulement ses Pods initiaux : "
           "supprimez un Pod de vitrine et laissez-le se recréer, avant de toucher au ReplicaSet.",
    )


# ----------------------------------------------------------------------
# 2. Le ReplicaSet supprimé, remplacé, et vitrine revenu à l'état demandé.
# ----------------------------------------------------------------------
def test_le_replicaset_supprime_est_remplace_et_vitrine_revient_a_l_etat_demande(host, memoire):
    dep = _json(host, f"-n {NS} get deployment vitrine", message(
        en=f"No Deployment vitrine in the {NS} namespace.",
        fr=f"Aucun Deployment vitrine dans le namespace {NS}.",
    ))
    jeux = _json(host, f"-n {NS} get replicasets -l app=vitrine", message(
        en="Cannot list the ReplicaSets of vitrine.",
        fr="Impossible de lister les ReplicaSets de vitrine.",
    )).get("items") or []
    uids = {rs["metadata"]["uid"] for rs in jeux}
    assert memoire["replicaset"] not in uids and uids, message(
        en="The initial ReplicaSet of vitrine is still there: delete it.",
        fr="Le ReplicaSet de départ de vitrine est toujours là : supprimez-le.",
    )
    assert dep["metadata"].get("generation") == memoire["generation"], message(
        en="The vitrine Deployment was modified (restarted or edited): the new ReplicaSet must "
           "come from the reconciliation alone, delete the ReplicaSet and touch nothing else.",
        fr="Le Deployment vitrine a été modifié (redémarré ou édité) : le nouveau ReplicaSet doit "
           "venir de la seule réconciliation, supprimez le ReplicaSet sans rien toucher d'autre.",
    )
    demandes = dep["spec"].get("replicas", 1)
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert demandes == REPLICAS_INITIAUX and disponibles == demandes, message(
        en=f"vitrine has {disponibles} available replica(s) for {demandes} requested; expected 3 out of 3.",
        fr=f"vitrine a {disponibles} réplica(s) disponible(s) pour {demandes} demandé(s) ; attendu 3 sur 3.",
    )


# ----------------------------------------------------------------------
# 3. Le Pod que le ReplicaSet a créé pour remplacer le Pod supprimé.
# ----------------------------------------------------------------------
def test_le_pod_recree_est_consigne(host, memoire):
    evenements = _json(
        host,
        f"-n {NS} get events --field-selector "
        f"involvedObject.uid={memoire['replicaset']},reason=SuccessfulCreate",
        message(en="Cannot read the events of the initial ReplicaSet.",
                fr="Impossible de lire les événements du ReplicaSet de départ."),
    ).get("items") or []
    crees = {e.get("message", "").rpartition(" ")[2] for e in evenements}
    recrees = crees - set(memoire.get("pods") or [])
    assert recrees, message(
        en="The initial ReplicaSet recreated no Pod: delete one Pod of vitrine first.",
        fr="Le ReplicaSet de départ n'a recréé aucun Pod : supprimez d'abord un Pod de vitrine.",
    )
    valeur = _valeur(_releve(host), "pod-recree")
    assert valeur in recrees, message(
        en=f"pod-recree is {valeur!r}, which is not the Pod created to replace the deleted one "
           f"({', '.join(sorted(recrees))}). The initial ReplicaSet wrote its name in a "
           "SuccessfulCreate event.",
        fr=f"pod-recree vaut {valeur!r}, qui n'est pas le Pod créé pour remplacer le Pod supprimé "
           f"({', '.join(sorted(recrees))}). Le ReplicaSet de départ a écrit son nom dans un "
           "événement SuccessfulCreate.",
    )


# ----------------------------------------------------------------------
# 4. L'UID du ReplicaSet de remplacement.
# ----------------------------------------------------------------------
def test_l_uid_du_nouveau_replicaset_est_consigne(host, memoire):
    jeux = _json(host, f"-n {NS} get replicasets -l app=vitrine", message(
        en="Cannot list the ReplicaSets of vitrine.",
        fr="Impossible de lister les ReplicaSets de vitrine.",
    )).get("items") or []
    uids = {rs["metadata"]["uid"] for rs in jeux} - {memoire["replicaset"]}
    assert uids, message(
        en="vitrine has no replacement ReplicaSet yet: delete its ReplicaSet first.",
        fr="vitrine n'a pas encore de ReplicaSet de remplacement : supprimez d'abord son ReplicaSet.",
    )
    valeur = _valeur(_releve(host), "uid-du-nouveau-replicaset")
    assert valeur != memoire["replicaset"], message(
        en="uid-du-nouveau-replicaset is the UID of the deleted ReplicaSet. The replacement "
           "has the same name, but Kubernetes gave it a new UID.",
        fr="uid-du-nouveau-replicaset est l'UID du ReplicaSet supprimé. Le remplaçant porte le "
           "même nom, mais Kubernetes lui a donné un nouvel UID.",
    )
    assert valeur in uids, message(
        en=f"uid-du-nouveau-replicaset is {valeur!r}, which is not the UID of the current "
           "ReplicaSet of vitrine (kubectl get replicaset -o jsonpath='{.items[0].metadata.uid}').",
        fr=f"uid-du-nouveau-replicaset vaut {valeur!r}, qui n'est pas l'UID du ReplicaSet actuel "
           "de vitrine (kubectl get replicaset -o jsonpath='{.items[0].metadata.uid}').",
    )
