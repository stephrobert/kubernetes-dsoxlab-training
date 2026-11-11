"""Une photographie sans aucun cluster ne fait pas tomber le validateur.

POURQUOI

`k8s-creer-un-cluster-kind` est le seul lab du catalogue qui fait créer un
cluster à l'apprenant. La VM kind n'a pas la mémoire de le porter à côté des
clusters des autres labs : son setup les supprime, et son amorçage laisse donc
/etc/kind vide. Le validateur lisait alors la version du premier nœud de la
photographie sans prévoir qu'il n'y en ait aucun, et s'arrêtait sur un
StopIteration (mesuré le 2026-11-11), sans rendre de verdict.

Ce test tient les deux cas : une photographie avec des nœuds rend leur version,
une photographie vide rend « aucun cluster », et non une exception.
"""

import importlib.util
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

#: `valider-labs.py` porte un tiret : il ne s'importe pas par `import`.
_spec = importlib.util.spec_from_file_location(
    "valider_labs", RACINE / "scripts" / "valider-labs.py"
)
assert _spec is not None and _spec.loader is not None
valider_labs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(valider_labs)


def test_une_photographie_avec_des_noeuds_rend_leur_version():
    photo = {"noeuds": {"boutique:boutique-control-plane": {"version": "v1.37.0"}}}
    assert valider_labs.version_photographiee(photo) == "v1.37.0"


def test_une_photographie_sans_cluster_rend_aucun_cluster():
    assert valider_labs.version_photographiee({"noeuds": {}}) == "aucun cluster"
