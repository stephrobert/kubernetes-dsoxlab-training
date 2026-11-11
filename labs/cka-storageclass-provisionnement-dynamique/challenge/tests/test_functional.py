"""test_functional.py : cka-storageclass-provisionnement-dynamique

Ces tests lisent l'état réel du cluster et l'intérieur du conteneur, jamais
les commandes tapées. Un test vérifie un seul état.

Le test du volume ne se contente pas de constater que la revendication est
liée : il vérifie que le volume a été **créé pour elle** par le provisionneur
de la classe. Un PersistentVolume créé à la main, même avec la bonne classe,
lie aussi la revendication sans que rien ait été provisionné à la demande :
c'est le lab voisin.

Tous échouent avant le travail : la revendication posée par le setup ne
désigne aucune classe, et aucun Pod registre n'existe. Une attente ne s'ouvre
que si un Pod monte déjà la revendication, seul cas où elle peut se lier.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "archives"
PVC = "donnees"
POD = "registre"
CLASSE = "local-path"
CHEMIN = "/data"
TEMOIN = f"{CHEMIN}/temoin"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# La classe est en WaitForFirstConsumer : la liaison n'arrive qu'au placement
# du Pod, puis la création du volume prend quelques secondes.
ATTENTE = 120
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _monte_la_revendication(pod: dict | None) -> bool:
    return any((v.get("persistentVolumeClaim") or {}).get("claimName") == PVC
               for v in (pod or {}).get("spec", {}).get("volumes") or [])


def _revendication(host) -> dict | None:
    pvc = _json(host, f"-n {NAMESPACE} get pvc {PVC}")
    fin = time.monotonic() + ATTENTE
    while pvc is not None and pvc["status"].get("phase") != "Bound" \
            and _monte_la_revendication(_json(host, f"-n {NAMESPACE} get pod {POD}")) and time.monotonic() < fin:
        time.sleep(PAS)
        pvc = _json(host, f"-n {NAMESPACE} get pvc {PVC}") or pvc
    return pvc


def _volume(host) -> dict | None:
    nom = ((_revendication(host) or {}).get("spec") or {}).get("volumeName")
    return _json(host, f"get pv {nom}") if nom else None


def _absente() -> str:
    return message(
        en=f"Claim {PVC} cannot be found in {NAMESPACE}: it must exist under this name.",
        fr=f"La revendication {PVC} est introuvable dans {NAMESPACE} : elle doit exister sous ce nom.",
    )


# ----------------------------------------------------------------------
# 1. La revendication désigne la classe du cluster.
# ----------------------------------------------------------------------
def test_la_revendication_designe_la_classe_local_path(host):
    pvc = _json(host, f"-n {NAMESPACE} get pvc {PVC}")
    assert pvc is not None, _absente()
    classe = pvc["spec"].get("storageClassName")
    assert classe == CLASSE, message(
        en=f"{PVC} names the class {classe!r}. Expected {CLASSE}, the class this cluster offers. An empty "
        "string is not an absent field: it explicitly disables provisioning on demand.",
        fr=f"{PVC} désigne la classe {classe!r}. Attendu {CLASSE}, la classe que ce cluster propose. Une chaîne "
        "vide n'est pas un champ absent : elle désactive explicitement le provisionnement à la demande.",
    )


# ----------------------------------------------------------------------
# 2. Le volume lié a été créé pour elle par le provisionneur de la classe.
# ----------------------------------------------------------------------
def test_le_volume_lie_a_ete_cree_pour_elle(host):
    pvc = _revendication(host)
    assert pvc is not None, _absente()
    assert pvc["status"].get("phase") == "Bound", message(
        en=f"{PVC} is {pvc['status'].get('phase')}. This class provisions only when a Pod uses the claim: "
        "without one, it stays Pending, and that is normal.",
        fr=f"{PVC} est {pvc['status'].get('phase')}. Cette classe ne provisionne que lorsqu'un Pod utilise la "
        "revendication : sans lui, elle reste Pending, et c'est normal.",
    )
    pv = _json(host, f"get pv {pvc['spec'].get('volumeName')}")
    classe = _json(host, f"get storageclass {CLASSE}")
    fournisseur = ((pv or {}).get("metadata", {}).get("annotations") or {}).get("pv.kubernetes.io/provisioned-by")
    assert pv is not None and classe is not None and fournisseur == classe.get("provisioner") \
        and (pv["spec"].get("claimRef") or {}).get("uid") == pvc["metadata"]["uid"], message(
        en=f"The volume bound to {PVC} was not created for it by the provisioner of {CLASSE}: it was prepared "
        "by hand. That binds a claim too, but nothing was provisioned on demand.",
        fr=f"Le volume lié à {PVC} n'a pas été créé pour elle par le provisionneur de {CLASSE} : il a été "
        "préparé à la main. Cela lie aussi une revendication, mais rien n'a été provisionné à la demande.",
    )


# ----------------------------------------------------------------------
# 3. Le volume porte la politique que la classe lui impose.
# ----------------------------------------------------------------------
def test_le_volume_porte_la_reclaim_policy_de_la_classe(host):
    pv = _volume(host)
    assert pv is not None, message(
        en=f"No volume is bound to {PVC}: there is no policy to read yet.",
        fr=f"Aucun volume n'est lié à {PVC} : il n'y a pas encore de politique à lire.",
    )
    classe = _json(host, f"get storageclass {CLASSE}") or {}
    attendue = classe.get("reclaimPolicy", "Delete")
    politique = pv["spec"].get("persistentVolumeReclaimPolicy")
    assert politique == attendue, message(
        en=f"The volume carries the policy {politique}, its class imposes {attendue}. A volume provisioned on "
        "demand inherits the policy of its class.",
        fr=f"Le volume porte la politique {politique}, sa classe impose {attendue}. Un volume provisionné à la "
        "demande hérite de la politique de sa classe.",
    )


# ----------------------------------------------------------------------
# 4. Le Pod registre monte la revendication sur /data.
# ----------------------------------------------------------------------
def test_registre_monte_la_revendication_sur_data(host):
    pod = _json(host, f"-n {NAMESPACE} get pod {POD}")
    assert pod is not None, message(en=f"No Pod {POD} in {NAMESPACE}.", fr=f"Aucun Pod {POD} dans {NAMESPACE}.")
    volumes = {v["name"] for v in pod["spec"].get("volumes") or []
               if (v.get("persistentVolumeClaim") or {}).get("claimName") == PVC}
    monte = any(m.get("mountPath") == CHEMIN and m["name"] in volumes
                for c in pod["spec"]["containers"] for m in c.get("volumeMounts") or [])
    assert monte, message(
        en=f"{POD} does not mount the claim {PVC} on {CHEMIN}.",
        fr=f"{POD} ne monte pas la revendication {PVC} sur {CHEMIN}.",
    )


# ----------------------------------------------------------------------
# 5. Le Pod a écrit le fichier témoin dans le volume.
# ----------------------------------------------------------------------
def test_registre_a_ecrit_le_temoin(host):
    pod = _json(host, f"-n {NAMESPACE} get pod {POD}")
    if pod is None:
        pytest.fail(message(en=f"No Pod {POD} in {NAMESPACE}.", fr=f"Aucun Pod {POD} dans {NAMESPACE}."))
    fin = time.monotonic() + ATTENTE
    while pod["status"].get("phase") == "Pending" and _monte_la_revendication(pod) and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _json(host, f"-n {NAMESPACE} get pod {POD}") or pod
    # Le témoin compte s'il est écrit DANS le volume : un fichier posé dans un
    # emptyDir monté au même chemin disparaîtrait avec le Pod.
    if not _monte_la_revendication(pod):
        pytest.fail(message(
            en=f"{POD} does not use the claim {PVC}: a file in {CHEMIN} would not be in the volume.",
            fr=f"{POD} n'utilise pas la revendication {PVC} : un fichier dans {CHEMIN} ne serait pas dans le volume.",
        ))
    res = host.run(f"{ADMIN} -n {NAMESPACE} exec {POD} --request-timeout=30s -- cat {TEMOIN}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"{POD} wrote nothing into {TEMOIN}, or does not run. A bound volume that receives nothing proves "
        "very little.",
        fr=f"{POD} n'a rien écrit dans {TEMOIN}, ou ne tourne pas. Un volume lié qui ne reçoit rien ne prouve "
        "pas grand-chose.",
    )
