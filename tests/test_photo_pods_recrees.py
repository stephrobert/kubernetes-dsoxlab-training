"""Un Pod recréé ailleurs n'est pas un écart ; un Pod en moins en est un.

POURQUOI

Le validateur photographiait chaque Pod par son NOM. Or un Pod tenu par un
ReplicaSet change de nom chaque fois qu'il est recréé : `cka-node-drain-cordon`
vide un worker, Kubernetes recrée ailleurs les Pods des autres namespaces, et
le verdict sortait ROUGE sur 28 « objets laissés / disparus » alors que le cycle
0 -> 5 -> 0 était parfait (mesuré le 2026-11-26).

Ce test tient les trois faces du correctif : le déplacement ne fait plus
d'écart, la disparition d'un Pod en fait toujours un, et un Pod sans
contrôleur se compte toujours par son nom.
"""

import importlib.util
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

_spec = importlib.util.spec_from_file_location("valider_labs", RACINE / "scripts" / "valider-labs.py")
assert _spec is not None and _spec.loader is not None
valider_labs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(valider_labs)


def _photographie() -> dict:
    """Les définitions du script exécuté sur le nœud, sans sa partie qui appelle kubectl."""
    source = valider_labs.PHOTOGRAPHIE
    definitions = source[: source.index("totale = ")]
    espace: dict = {}
    exec(definitions, espace)  # noqa: S102 - le script du dépôt lui-même, pas une entrée extérieure
    return espace


def _pod(ns: str, nom: str, maitre: tuple[str, str] | None = None) -> dict:
    meta: dict = {"namespace": ns, "name": nom}
    if maitre:
        meta["ownerReferences"] = [{"kind": maitre[0], "name": maitre[1], "controller": True}]
    return {"metadata": meta}


def test_un_pod_recree_sous_un_autre_suffixe_ne_fait_aucun_ecart():
    noms = _photographie()["noms_des_pods"]
    avant = noms([_pod("istio-system", "istiod-8547b477d9-abcde", ("ReplicaSet", "istiod-8547b477d9"))])
    apres = noms([_pod("istio-system", "istiod-8547b477d9-rjrj2", ("ReplicaSet", "istiod-8547b477d9"))])
    assert avant == apres, (avant, apres)


def test_un_pod_en_moins_reste_un_ecart():
    noms = _photographie()["noms_des_pods"]
    rs = ("ReplicaSet", "web-69bb78c4cf")
    avant = noms([_pod("vitrine", "web-69bb78c4cf-a", rs), _pod("vitrine", "web-69bb78c4cf-b", rs)])
    apres = noms([_pod("vitrine", "web-69bb78c4cf-c", rs)])
    assert set(avant) - set(apres) == {"vitrine/pods/ReplicaSet:web-69bb78c4cf#2"}


def test_un_pod_sans_controleur_ou_d_un_statefulset_garde_son_nom():
    noms = _photographie()["noms_des_pods"]
    assert noms([_pod("drain", "orphelin")]) == ["drain/pods/orphelin"]
    assert noms([_pod("base", "pg-0", ("StatefulSet", "pg"))]) == ["base/pods/pg-0"]
