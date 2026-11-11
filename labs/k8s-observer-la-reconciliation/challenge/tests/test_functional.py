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


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
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


def _forme(texte: str) -> str:
    """Le texte sans accents ni casse, espaces et soulignés changés en tirets :
    « Replica Set », « replica_set » et « ReplicaSet » se comparent pareil."""
    import unicodedata
    decompose = unicodedata.normalize("NFKD", texte.lower())
    sans = "".join(c for c in decompose if not unicodedata.combining(c))
    return "-".join(sans.replace("_", " ").split())


#: L'objet de ce lab est la DISTINCTION entre deux contrôleurs : chaque champ doit
#: nommer le sien. « replicaset » couvre replicaset-controller, ReplicaSet et
#: « contrôleur des ReplicaSets » ; « deployment » couvre deployment-controller,
#: Deployment et « contrôleur des Deployments ». Le kube-controller-manager seul
#: est refusé : il héberge les deux contrôleurs, le nommer ne distingue rien.
CONTROLEUR_DU_POD = ("replicaset", "replica-set")
CONTROLEUR_DU_REPLICASET = ("deployment",)
HOTE_DES_CONTROLEURS = ("controller-manager",)


def _juge_controleur(valeur: str, attendu: tuple[str, ...], rival: tuple[str, ...]) -> str | None:
    """Rend None si la valeur nomme le bon contrôleur, sinon la raison du refus."""
    forme = _forme(valeur)
    nomme = any(nom in forme for nom in attendu)
    if not nomme and any(nom in forme for nom in HOTE_DES_CONTROLEURS):
        return "hote"
    if not nomme or any(nom in forme for nom in (*rival, "scheduler", "kubelet")):
        return "faux"
    return None


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
# 3. Le contrôleur qui a recréé le Pod.
# ----------------------------------------------------------------------
def test_le_controleur_qui_recree_le_pod_est_consigne(releve):
    valeur = _valeur(releve, "pod-recree-par")
    refus = _juge_controleur(valeur, CONTROLEUR_DU_POD, CONTROLEUR_DU_REPLICASET)
    assert refus != "hote", message(
        en=f"pod-recree-par is {valeur!r}: the kube-controller-manager hosts every controller. "
           "Name the controller itself, as shown in the From column of kubectl describe.",
        fr=f"pod-recree-par vaut {valeur!r} : le kube-controller-manager héberge tous les "
           "contrôleurs. Nommez le contrôleur lui-même, tel que l'affiche la colonne From de "
           "kubectl describe.",
    )
    assert refus is None, message(
        en=f"pod-recree-par is {valeur!r}; it must name the controller that wrote the "
           "SuccessfulCreate event of the new Pod, and only that one.",
        fr=f"pod-recree-par vaut {valeur!r} ; il doit nommer le contrôleur qui a écrit "
           "l'événement SuccessfulCreate du nouveau Pod, et lui seul.",
    )


# ----------------------------------------------------------------------
# 4. Le contrôleur qui a recréé le ReplicaSet.
# ----------------------------------------------------------------------
def test_le_controleur_qui_recree_le_replicaset_est_consigne(releve):
    valeur = _valeur(releve, "replicaset-recree-par")
    refus = _juge_controleur(valeur, CONTROLEUR_DU_REPLICASET, CONTROLEUR_DU_POD)
    assert refus != "hote", message(
        en=f"replicaset-recree-par is {valeur!r}: the kube-controller-manager hosts every "
           "controller. Name the controller itself, as shown in the From column of kubectl describe.",
        fr=f"replicaset-recree-par vaut {valeur!r} : le kube-controller-manager héberge tous les "
           "contrôleurs. Nommez le contrôleur lui-même, tel que l'affiche la colonne From de "
           "kubectl describe.",
    )
    assert refus is None, message(
        en=f"replicaset-recree-par is {valeur!r}; it must name the controller that wrote the "
           "ScalingReplicaSet event of the Deployment, and only that one.",
        fr=f"replicaset-recree-par vaut {valeur!r} ; il doit nommer le contrôleur qui a écrit "
           "l'événement ScalingReplicaSet du Deployment, et lui seul.",
    )
    assert _forme(valeur) != _forme(releve.get("pod-recree-par", "")), message(
        en="replicaset-recree-par and pod-recree-par carry the same value: two different "
           "controllers recreated the Pod and the ReplicaSet.",
        fr="replicaset-recree-par et pod-recree-par portent la même valeur : ce sont deux "
           "contrôleurs différents qui ont recréé le Pod et le ReplicaSet.",
    )
