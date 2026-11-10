"""test_functional.py : k8s-challenge-lire-un-cluster

Ces tests confrontent le relevé de l'apprenant, ~/architecture/releve.txt, à
l'état RÉEL du cluster, lu par l'API au moment du test. Aucune valeur attendue
n'est écrite ici : le nom des Nodes, des Pods statiques et la version du
runtime viennent du cluster, ce qui laisse le lab juste quand kind change de
version.

Un test vérifie un seul état demandé par l'énoncé. Les rôles des composants
sont jugés par mots-clés tolérants, en français comme en anglais, sur
l'appariement composant et fonction : un rôle doit évoquer la fonction de SON
composant, et un même texte fourre-tout qui les évoque toutes est refusé. Le
nom du composant ne compte pas comme mot-clé : « etcd : etcd » ne dit rien.

Le dernier état est un diagnostic, sans réparation : le Deployment
file-attente désigne un ordonnanceur qui n'existe pas. Ses Pods existent,
puisque le replicaset-controller a agi, mais aucun scheduler ne les place.
L'apprenant nomme celui qui a agi et celui qui n'agit pas ; « scheduler »,
« kube-scheduler », « default-scheduler », « ordonnanceur » et
« ordonnanceur-equipe » sont acceptés, un texte qui accuse aussi un autre
composant est refusé.
"""

from __future__ import annotations

import json
import re
import unicodedata

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/architecture.kubeconfig"
NS = "architecture"
ETIQUETTE_CP = "node-role.kubernetes.io/control-plane"

# Ce que `n-agit-pas` ne doit pas nommer en plus du scheduler : un texte qui
# accuse tout le monde n'a rien diagnostiqué.
def _forme(texte: str) -> str:
    """Le texte sans accents ni casse, espaces et soulignés changés en tirets :
    « Replica Set », « replica_set » et « ReplicaSet » se comparent pareil."""
    import unicodedata
    decompose = unicodedata.normalize("NFKD", texte.lower())
    sans = "".join(c for c in decompose if not unicodedata.combining(c))
    return "-".join(sans.replace("_", " ").split())


#: Qui a créé ou recréé un Pod : le contrôleur exact, le processus qui l'héberge,
#: ou l'objet qui le porte, comme les leçons le disent (« le ReplicaSet recrée »).
CREATEURS_DE_POD = ("replicaset-controller", "kube-controller-manager",
                    "controller-manager", "replicaset", "replica-set")

AUTRES_COMPOSANTS = (
    "kubelet", "controller", "apiserver", "api-server", "api server", "etcd",
    "proxy", "containerd", "runtime", "controleur",
)

# Composant : (valeur du label `component` du Pod statique, noms à retirer du
# rôle avant de chercher les mots-clés, mots-clés de sa fonction). Les
# mots-clés sont comparés sans accents ni majuscules, en début de mot.
COMPOSANTS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "apiserver": (
        "kube-apiserver",
        ("kube-apiserver", "apiserver", "api server", "api-server"),
        ("api", "requete", "request", "entree", "entry", "front", "rest",
         "authent", "autoris", "authoriz", "valid", "expose", "porte", "gateway",
         "interface", "communi", "demande", "recoi", "recev", "receiv", "kubectl"),
    ),
    "etcd": (
        "etcd",
        ("etcd",),
        ("stock", "store", "cle", "key", "valeur", "value", "donnee", "data",
         "persist", "base", "database", "memoire", "sauvegard", "enregistr",
         "verite", "truth", "registre"),
    ),
    "scheduler": (
        "kube-scheduler",
        ("kube-scheduler", "scheduler"),
        ("plac", "assign", "affect", "choisi", "choix", "choos", "select",
         "schedul", "ordonnanc", "planifi", "attribu", "decid", "repart", "distribu"),
    ),
    "controller-manager": (
        "kube-controller-manager",
        ("kube-controller-manager", "controller-manager", "controller manager"),
        ("controleur", "controller", "boucle", "loop", "reconcil", "replica",
         "desire", "desired", "surveill", "watch", "maintien", "maintient",
         "maintain", "ecart", "corrig", "recre", "convergen", "controle"),
    ),
}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str, absent: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire personnel de l'utilisateur du lab : testinfra agit en root
    par sudo, donc host.user().home vaudrait /root."""
    return host.check_output(
        'getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6'
    ).strip()


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
    """Le relevé, en dictionnaire clé -> valeur. Une clé sans valeur vaut ""."""
    chemin = f"{_maison(host)}/architecture/releve.txt"
    fichier = host.file(chemin)
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if not ligne or ligne.startswith("#") or ":" not in ligne:
            continue
        cle, _, valeur = ligne.partition(":")
        valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


def _valeur(releve: dict[str, str], cle: str) -> str:
    valeur = releve.get(cle, "")
    assert valeur, message(
        en=f"The key {cle!r} of ~/architecture/releve.txt has no value.",
        fr=f"La clé {cle!r} de ~/architecture/releve.txt n'a pas de valeur.",
    )
    return valeur


def _sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _familles(texte: str) -> set[str]:
    """Les composants dont la fonction est évoquée par ce texte."""
    propre = _sans_accents(texte)
    for _, noms, _ in COMPOSANTS.values():
        for nom in noms:
            propre = propre.replace(nom, " ")
    return {
        composant
        for composant, (_, _, mots) in COMPOSANTS.items()
        if any(re.search(rf"\b{re.escape(mot)}", propre) for mot in mots)
    }


def _noeuds(host) -> list[dict]:
    return _json(host, "get nodes", message(
        en="Cannot list the Nodes of the architecture cluster.",
        fr="Impossible de lister les Nodes du cluster architecture.",
    )).get("items") or []


# ----------------------------------------------------------------------
# 1. Le Node qui porte le control plane.
# ----------------------------------------------------------------------
def test_le_noeud_du_control_plane_est_consigne(host, releve):
    attendus = {
        n["metadata"]["name"] for n in _noeuds(host)
        if ETIQUETTE_CP in (n["metadata"].get("labels") or {})
    }
    assert attendus, message(
        en="No Node of the cluster carries the control-plane role: the cluster is not the expected one.",
        fr="Aucun Node du cluster ne porte le rôle control-plane : ce n'est pas le cluster attendu.",
    )
    valeur = _valeur(releve, "noeud-control-plane")
    assert valeur in attendus, message(
        en=f"noeud-control-plane is {valeur!r}, which is not the Node carrying the control plane.",
        fr=f"noeud-control-plane vaut {valeur!r}, qui n'est pas le Node qui porte le control plane.",
    )


# ----------------------------------------------------------------------
# 2. Les Pods des quatre composants, et leur rôle.
# ----------------------------------------------------------------------
def test_les_quatre_composants_du_control_plane_sont_consignes_avec_leur_role(host, releve):
    pods = _json(host, "-n kube-system get pods", message(
        en="Cannot list the Pods of kube-system.",
        fr="Impossible de lister les Pods de kube-system.",
    )).get("items") or []
    par_composant: dict[str, set[str]] = {}
    for pod in pods:
        etiquette = (pod["metadata"].get("labels") or {}).get("component")
        if etiquette:
            par_composant.setdefault(etiquette, set()).add(pod["metadata"]["name"])

    roles: dict[str, str] = {}
    for composant, (etiquette, _, _) in COMPOSANTS.items():
        reels = par_composant.get(etiquette, set())
        assert reels, message(
            en=f"No {etiquette} Pod in kube-system: the cluster is not the expected one.",
            fr=f"Aucun Pod {etiquette} dans kube-system : ce n'est pas le cluster attendu.",
        )
        nom = _valeur(releve, f"pod-{composant}")
        assert nom in reels, message(
            en=f"pod-{composant} is {nom!r}, which is not the {etiquette} Pod of kube-system.",
            fr=f"pod-{composant} vaut {nom!r}, qui n'est pas le Pod {etiquette} de kube-system.",
        )
        role = _valeur(releve, f"role-{composant}")
        assert composant in _familles(role), message(
            en=f"role-{composant} does not describe what {etiquette} does: {role!r}.",
            fr=f"role-{composant} ne décrit pas ce que fait {etiquette} : {role!r}.",
        )
        roles[composant] = role

    fourre_tout = [c for c, r in roles.items() if len(_familles(r)) == len(COMPOSANTS)]
    assert not fourre_tout, message(
        en=f"The role of {', '.join(fourre_tout)} describes all four components at once: "
           "give each component its own function.",
        fr=f"Le rôle de {', '.join(fourre_tout)} décrit les quatre composants à la fois : "
           "donnez à chaque composant sa propre fonction.",
    )
    assert len({_sans_accents(r) for r in roles.values()}) == len(roles), message(
        en="Several components have the same role: each one has its own function.",
        fr="Plusieurs composants ont le même rôle : chacun a sa propre fonction.",
    )


# ----------------------------------------------------------------------
# 3. Le runtime de conteneurs de chaque worker.
# ----------------------------------------------------------------------
def test_le_runtime_de_chaque_worker_est_consigne(host, releve):
    workers = [
        n for n in _noeuds(host)
        if ETIQUETTE_CP not in (n["metadata"].get("labels") or {})
    ]
    assert workers, message(
        en="The cluster has no worker Node: it is not the expected one.",
        fr="Le cluster n'a aucun Node worker : ce n'est pas le cluster attendu.",
    )
    for noeud in workers:
        nom = noeud["metadata"]["name"]
        runtime = noeud["status"]["nodeInfo"]["containerRuntimeVersion"]
        moteur, _, version = runtime.partition("://")
        valeur = _valeur(releve, f"runtime-{nom}")
        assert moteur.lower() in valeur.lower() and version in valeur, message(
            en=f"runtime-{nom} is {valeur!r}; it must name the runtime and the version "
               "shown by kubectl get nodes -o wide.",
            fr=f"runtime-{nom} vaut {valeur!r} ; il doit nommer le runtime et la version "
               "affichés par kubectl get nodes -o wide.",
        )


# ----------------------------------------------------------------------
# 4. Le Node du Pod témoin, prouvé par l'événement Scheduled.
# ----------------------------------------------------------------------
def test_le_noeud_du_pod_temoin_est_prouve_par_l_evenement_scheduled(host, releve):
    pod = _json(host, f"-n {NS} get pod temoin", message(
        en="The temoin Pod no longer exists in the architecture namespace: leave it in place.",
        fr="Le Pod temoin n'existe plus dans le namespace architecture : laissez-le en place.",
    ))
    noeud = pod["spec"].get("nodeName", "")
    valeur = _valeur(releve, "noeud-du-pod-temoin")
    assert valeur == noeud, message(
        en=f"noeud-du-pod-temoin is {valeur!r}, but the temoin Pod runs on another Node.",
        fr=f"noeud-du-pod-temoin vaut {valeur!r}, mais le Pod temoin tourne sur un autre Node.",
    )
    preuve = _valeur(releve, "evenement-scheduled")
    propre = preuve.lower()
    assert ("assigned" in propre or "scheduled" in propre) and f"{NS}/temoin" in propre \
            and noeud in preuve, message(
        en="evenement-scheduled must quote the Scheduled event of the temoin Pod, "
           "the one that names the Pod and the Node it was assigned to.",
        fr="evenement-scheduled doit citer l'événement Scheduled du Pod temoin, "
           "celui qui nomme le Pod et le Node auquel il a été assigné.",
    )


# ----------------------------------------------------------------------
# 5. Le Deployment qui ne revient pas : qui a agi, qui n'agit pas.
# ----------------------------------------------------------------------
def test_le_maillon_qui_n_agit_pas_est_identifie(host, releve):
    # Garde-fou : la panne posée par le setup est toujours là. Sans elle, il
    # n'y a rien à diagnostiquer, et le relevé ne serait confronté à rien.
    pods = _json(host, f"-n {NS} get pods -l app=file-attente", message(
        en="Cannot list the Pods of file-attente.",
        fr="Impossible de lister les Pods de file-attente.",
    )).get("items") or []
    en_attente = [p for p in pods if not p["spec"].get("nodeName")]
    assert en_attente, message(
        en="file-attente has no Pod waiting to be placed any more: run dsoxlab reset "
           "and leave the Deployment as it is, the challenge asks for a diagnosis only.",
        fr="file-attente n'a plus aucun Pod en attente de placement : lancez dsoxlab reset "
           "et laissez le Deployment en l'état, le challenge ne demande qu'un diagnostic.",
    )

    auteur = _valeur(releve, "cree-par")
    forme = _forme(auteur)
    nomme_le_createur = any(nom in forme for nom in CREATEURS_DE_POD)
    accuse_un_autre = any(nom in forme for nom in ("scheduler", "kubelet", "deployment", "etcd", "apiserver"))
    assert nomme_le_createur and not accuse_un_autre, message(
        en=f"cree-par is {auteur!r}; it must name the component that created the Pods "
           "of file-attente, and only that one: the From column of the SuccessfulCreate "
           "event, in kubectl describe, gives its exact name.",
        fr=f"cree-par vaut {auteur!r} ; il doit nommer le composant qui a créé les Pods "
           "de file-attente, et lui seul : la colonne From de l'événement SuccessfulCreate, "
           "dans kubectl describe, donne son nom exact.",
    )

    absent = _sans_accents(_valeur(releve, "n-agit-pas"))
    nomme_le_scheduler = "scheduler" in absent or "ordonnanceur" in absent
    autres = [nom for nom in AUTRES_COMPOSANTS if nom in absent]
    assert nomme_le_scheduler and not autres, message(
        en="n-agit-pas must name the first link of the chain that does not act on the "
           "Pods of file-attente, and only that one.",
        fr="n-agit-pas doit nommer le premier maillon de la chaîne qui n'agit pas sur les "
           "Pods de file-attente, et lui seul.",
    )
