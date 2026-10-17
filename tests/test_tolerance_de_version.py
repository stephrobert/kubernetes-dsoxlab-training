"""La tolérance de version du validateur ne doit aller que vers le HAUT.

POURQUOI CETTE TOLÉRANCE EXISTE

`cka-kubeadm-upgrade` est le seul lab du catalogue qui touche à la version du
cluster : son setup le rétrograde en 1.36 pour qu'il y ait quelque chose à
monter, et son cleanup le ramène à la version que le dépôt APT publie. Les
soixante-trois autres labs ne changent jamais la version de leur cluster, et la
photographie du validateur le vérifie pour tous.

Le dépôt `pkgs.k8s.io/v1.37` n'est versionné que par MINEURE : rien n'y fige le
patch. Si une 1.37.2 paraît entre le `provision` et le `clean`, la version
relevée par le setup et celle que le cleanup trouve diffèrent, sans que le lab
y soit pour rien, et le validateur rendrait un rouge inexplicable.

POURQUOI CE TEST, ET PAS SEULEMENT LA TOLÉRANCE

Une tolérance qui tolère trop ne crie plus jamais. Le défaut du 2026-10-12
était précisément une RÉTROGRADATION : un cleanup qui visait « 1.37.0-1.1 »
écrit en dur ramenait un cluster monté en 1.37.1. Si la tolérance avait couvert
les deux sens, elle aurait masqué ce défaut au lieu de le laisser voir, et le
lab serait resté cassé sans qu'aucun relevé ne le dise.

Ce test tient donc les deux moitiés : ce qui doit passer, et ce qui doit
échouer. La seconde est celle qui compte.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

#: `valider-labs.py` porte un tiret : il ne s'importe pas par `import`.
_spec = importlib.util.spec_from_file_location(
    "valider_labs", RACINE / "scripts" / "valider-labs.py"
)
assert _spec is not None and _spec.loader is not None
valider_labs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(valider_labs)

LAB_TOLERE = "cka-kubeadm-upgrade"
LAB_ORDINAIRE = "cks-istio-mtls-lockdown"


def photo(version: str) -> dict:
    """Une photographie minimale, qui ne diffère que par la version des nœuds."""
    return {
        "noeuds": {
            "k8s-cp.lab": {
                "ready": True, "unschedulable": False,
                "taints": [], "labels": {}, "version": version,
            },
        },
        "namespaces": ["default", "kube-system"],
        "terminating": [],
        "cluster": {},
        "kube-system": {},
        "objets": [],
    }


# ── La lecture d'un numéro de version ────────────────────────────────────────

@pytest.mark.parametrize(("brut", "attendu"), [
    ("v1.37.1", (1, 37, 1)),
    ("1.37.1", (1, 37, 1)),
    ("v1.37.10", (1, 37, 10)),
    ("v1.37.1-rc.0", (1, 37, 1)),
    ("v1.37.1+build7", (1, 37, 1)),
    ("  v1.37.1  ", (1, 37, 1)),
])
def test_une_version_se_lit_en_tuple(brut: str, attendu: tuple[int, ...]) -> None:
    assert valider_labs._version_en_tuple(brut) == attendu


@pytest.mark.parametrize("brut", ["", "inconnue", "v", "vX.Y.Z", "latest"])
def test_une_version_illisible_rend_none(brut: str) -> None:
    """Et None fera retomber l'appelant sur l'écart, jamais sur le vert.

    « Je n'ai pas pu comparer » n'est pas « c'est bon » : c'est la règle de fond
    du catalogue, et elle vaut ici comme pour les sondes de `doctor`.
    """
    assert valider_labs._version_en_tuple(brut) is None


def test_la_comparaison_ne_passe_pas_par_les_chaines() -> None:
    """« v1.37.9 » est supérieur à « v1.37.10 » en lexicographique.

    Ce genre d'inversion ne se voit pas tant que le patch reste à un chiffre,
    puis se paie d'un coup au dixième.
    """
    assert "v1.37.9" > "v1.37.10"
    neuf = valider_labs._version_en_tuple("v1.37.9")
    dix = valider_labs._version_en_tuple("v1.37.10")
    assert neuf is not None and dix is not None
    assert dix > neuf


# ── Ce que la tolérance doit laisser passer ──────────────────────────────────

def test_version_identique_aucun_ecart() -> None:
    assert valider_labs.ecarts(photo("v1.37.1"), photo("v1.37.1"), LAB_TOLERE) == []


def test_le_lab_d_upgrade_peut_laisser_le_cluster_plus_haut() -> None:
    """Le cas que la tolérance existe pour couvrir : un patch publié entre-temps."""
    assert valider_labs.ecarts(photo("v1.37.1"), photo("v1.37.2"), LAB_TOLERE) == []


def test_une_montee_mineure_passe_aussi() -> None:
    assert valider_labs.ecarts(photo("v1.37.1"), photo("v1.38.0"), LAB_TOLERE) == []


# ── Ce que la tolérance doit REFUSER, et qui compte le plus ──────────────────

def test_une_retrogradation_reste_un_ecart() -> None:
    """Le défaut du 2026-10-12, mot pour mot.

    Si ce test passe au vert un jour, la tolérance a été élargie et le défaut
    qu'elle laisse revenir est celui-là même : un cleanup qui ramène le cluster
    plus bas que l'état dans lequel il l'a trouvé.
    """
    trouves = valider_labs.ecarts(photo("v1.37.1"), photo("v1.37.0"), LAB_TOLERE)
    assert trouves, "une rétrogradation doit être signalée, même pour ce lab"
    assert "version" in trouves[0]
    assert "v1.37.1" in trouves[0] and "v1.37.0" in trouves[0]


def test_une_version_illisible_reste_un_ecart() -> None:
    trouves = valider_labs.ecarts(photo("v1.37.1"), photo("inconnue"), LAB_TOLERE)
    assert trouves, "une version qu'on ne sait pas lire ne se conclut pas au vert"


def test_aucun_autre_lab_n_a_droit_a_la_tolerance() -> None:
    """La tolérance est nominative, et doit le rester.

    Un lab ordinaire qui laisse le cluster à une autre version a fait quelque
    chose qu'aucun lab de ce catalogue n'a à faire.
    """
    trouves = valider_labs.ecarts(photo("v1.37.1"), photo("v1.37.2"), LAB_ORDINAIRE)
    assert trouves, "seul cka-kubeadm-upgrade peut laisser le cluster plus haut"


def test_sans_identifiant_rien_n_est_tolere() -> None:
    """L'appelant qui oublie de passer l'identifiant doit obtenir le contrôle
    strict, pas la tolérance. Un défaut de câblage ne doit pas desserrer un
    contrôle en silence."""
    assert valider_labs.ecarts(photo("v1.37.1"), photo("v1.37.2")) != []


# ── Ce que la tolérance ne touche pas ────────────────────────────────────────

@pytest.mark.parametrize(("cle", "valeur"), [
    ("ready", False),
    ("unschedulable", True),
    ("taints", [{"key": "node.kubernetes.io/unschedulable"}]),
    ("labels", {"laisse": "par-le-lab"}),
])
def test_les_autres_champs_du_noeud_restent_compares(cle: str, valeur: object) -> None:
    """Même pour le lab toléré : la tolérance porte sur la version, et sur rien
    d'autre. Un nœud laissé cordonné priverait le lab suivant d'un nœud."""
    apres = photo("v1.37.1")
    apres["noeuds"]["k8s-cp.lab"][cle] = valeur
    trouves = valider_labs.ecarts(photo("v1.37.1"), apres, LAB_TOLERE)
    assert any(cle in t for t in trouves), f"{cle} doit rester comparé"


def test_un_objet_laisse_reste_signale_pour_le_lab_tolere() -> None:
    apres = photo("v1.37.2")
    apres["objets"] = ["bac-a-sable/configmaps/traine"]
    trouves = valider_labs.ecarts(photo("v1.37.1"), apres, LAB_TOLERE)
    assert any("objet laissé" in t for t in trouves)

# ── Les ConfigMaps que `kubeadm upgrade apply` régénère ──────────────────────
#
# Mesuré le 2026-10-15 : la seule différence de contenu est l'ajout de
# `resolvConf: /run/systemd/resolve/resolv.conf`, que `kubeadm upgrade apply`
# pose en détectant systemd-resolved et que `kubeadm init` du socle n'écrit pas.
# La photographie ne porte que des empreintes, donc la tolérance accepte toute
# différence sur ces deux ConfigMaps : c'est un desserrement assumé, et ces
# tests en bornent la portée.

def photo_ks(kube_system: dict, version: str = "v1.37.1") -> dict:
    p = photo(version)
    p["kube-system"] = kube_system
    return p


@pytest.mark.parametrize("cle", ["configmap/kubelet-config", "configmap/kubeadm-config"])
def test_les_configmaps_de_kubeadm_sont_toleres_pour_le_lab_d_upgrade(cle: str) -> None:
    avant = photo_ks({cle: "73c27a184216"})
    apres = photo_ks({cle: "5075bf858537"})
    assert valider_labs.ecarts(avant, apres, LAB_TOLERE) == []


@pytest.mark.parametrize("cle", ["configmap/kubelet-config", "configmap/kubeadm-config"])
def test_aucun_autre_lab_ne_peut_les_laisser_differents(cle: str) -> None:
    avant = photo_ks({cle: "73c27a184216"})
    apres = photo_ks({cle: "5075bf858537"})
    trouves = valider_labs.ecarts(avant, apres, LAB_ORDINAIRE)
    assert trouves, f"{cle} ne doit être toléré que pour le lab d'upgrade"


@pytest.mark.parametrize("cle", [
    "configmap/coredns",
    "configmap/kube-proxy",
    "secret/bootstrap-token",
    "deployment/coredns",
])
def test_les_autres_objets_de_kube_system_restent_compares(cle: str) -> None:
    """La tolérance porte sur DEUX ConfigMaps nommés, pas sur kube-system.

    Un lab qui modifierait coredns ou kube-proxy toucherait au socle commun des
    soixante-quatre labs, et c'est exactement ce qu'il faut voir.
    """
    avant = photo_ks({cle: "avant"})
    apres = photo_ks({cle: "apres"})
    trouves = valider_labs.ecarts(avant, apres, LAB_TOLERE)
    assert trouves, f"{cle} doit rester comparé, même pour le lab d'upgrade"


def test_un_objet_de_kube_system_qui_apparait_reste_un_ecart() -> None:
    avant = photo_ks({})
    apres = photo_ks({"configmap/pose-par-le-lab": "abcdef"})
    trouves = valider_labs.ecarts(avant, apres, LAB_TOLERE)
    assert trouves, "un objet nouveau dans kube-system doit se voir"
