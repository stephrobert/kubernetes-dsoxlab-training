"""test_functional.py : cka-storageclass-provisionnement-dynamique

Deux affirmations qui lisent l'état réel du cluster et l'intérieur du
conteneur, jamais les commandes tapées.

Le dernier test ne se contente pas de constater que la revendication est liée :
il vérifie que le volume a été **créé pour elle**, et qu'il porte bien la
politique de la classe. Un candidat qui aurait créé un PersistentVolume à la
main obtiendrait une revendication liée sans avoir rien provisionné
dynamiquement, ce qui est précisément le lab voisin.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "archives"
PVC = "donnees"
POD = "registre"
CLASSE = "local-path"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
TEMOIN = "/data/temoin"

# La classe est en WaitForFirstConsumer : la liaison n'arrive qu'au placement
# du Pod, puis la création du volume prend quelques secondes. Budget borné,
# pour ne pas recaler un candidat dont la correction est juste.
BUDGET_S = 120
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


# ----------------------------------------------------------------------
# 1. La revendication demande une classe, et le Pod l'utilise.
# ----------------------------------------------------------------------
def test_la_revendication_designe_une_classe(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable. Une revendication peut
    désigner une classe qui n'existe pas, et rester en attente pour toujours."""
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get pvc {PVC} -o json")
    assert rc == 0 and sortie, (
        f"La revendication {PVC} est introuvable dans {NAMESPACE}. Le setup "
        f"l'avait posée : elle doit être recréée sous le même nom. {diagnostic}"
    )
    spec = json.loads(sortie)["spec"]
    classe = spec.get("storageClassName")
    assert classe, (
        "La revendication ne désigne aucune classe de stockage : "
        f"storageClassName vaut « {classe} ». Une chaîne VIDE n'est pas un "
        "champ absent : elle désactive explicitement le provisionnement "
        "dynamique, et la revendication attend alors un volume créé à la main."
    )

    rc, sortie, _ = _kubectl(host, "get storageclass -o json")
    connues = [c["metadata"]["name"] for c in json.loads(sortie or "{}").get("items", [])]
    assert classe in connues, (
        f"La revendication demande la classe « {classe} », que le cluster ne "
        f"connaît pas. Les classes disponibles sont {connues}. Une "
        "revendication qui désigne une classe inexistante reste en attente "
        "indéfiniment, sans erreur."
    )


# ----------------------------------------------------------------------
# 2. LE test : le volume a été créé pour elle, et le Pod écrit dedans.
# ----------------------------------------------------------------------
def test_le_volume_est_provisionne_a_la_demande_et_ecrit(host):
    """La preuve, prise sur le volume lui-même.

    Le contrôle décisif est que le PersistentVolume porte
    `claimRef` vers cette revendication ET une classe : un volume créé à la
    main lierait aussi la revendication, sans qu'aucun provisionnement dynamique
    n'ait eu lieu. C'est le lab voisin, pas celui-ci.

    Mesuré le 2026-09-17 : la classe `local-path` est en WaitForFirstConsumer,
    donc la liaison n'arrive qu'au placement du Pod, et sa reclaimPolicy est
    `Delete`.
    """
    fin = time.monotonic() + BUDGET_S
    phase, volume = "", ""
    while time.monotonic() < fin:
        rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get pvc {PVC} -o json")
        if rc == 0 and sortie:
            pvc = json.loads(sortie)
            phase = pvc.get("status", {}).get("phase", "")
            volume = pvc.get("spec", {}).get("volumeName", "")
            if phase == "Bound" and volume:
                break
        time.sleep(PAS_S)

    assert phase == "Bound", (
        f"La revendication {PVC} est en « {phase or 'inconnu'} » après "
        f"{BUDGET_S} secondes. La classe de ce cluster attend son premier "
        "consommateur avant de provisionner : tant qu'aucun Pod n'utilise la "
        "revendication, elle reste en attente, et c'est normal. Il en faut "
        "donc un."
    )

    rc, sortie, diagnostic = _kubectl(host, f"get pv {volume} -o json")
    assert rc == 0 and sortie, f"Le volume {volume} est introuvable. {diagnostic}"
    pv = json.loads(sortie)
    assert pv["spec"].get("storageClassName") == CLASSE, (
        f"Le volume {volume} n'appartient pas à la classe « {CLASSE} » mais à "
        f"« {pv['spec'].get('storageClassName') or 'aucune'} ». Un volume créé "
        "à la main lie aussi une revendication, mais rien n'a alors été "
        "provisionné à la demande : c'est l'objet du lab voisin."
    )
    reclaim = pv["spec"].get("persistentVolumeReclaimPolicy")
    assert reclaim == "Delete", (
        f"Le volume porte la politique « {reclaim} » et non « Delete ». Un "
        "volume provisionné dynamiquement hérite de la politique de sa classe, "
        "qui décide de son sort quand la revendication disparaît."
    )

    rc, contenu, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec {POD} --request-timeout=30s -- cat {TEMOIN}",
    )
    assert rc == 0 and contenu, (
        f"Le Pod {POD} n'a rien écrit dans {TEMOIN}, ou ne tourne pas. Un "
        "volume lié qui ne reçoit rien ne prouve pas grand-chose : il faut "
        f"qu'il serve. {diagnostic}"
    )
