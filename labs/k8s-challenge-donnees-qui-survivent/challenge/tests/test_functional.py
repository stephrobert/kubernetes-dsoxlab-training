"""test_functional.py : k8s-challenge-donnees-qui-survivent

Challenge du module « Stockage persistant ». Ces tests lisent l'état du cluster
« lab », le fichier témoin dans le volume, et la cause consignée dans
~/archives/. Un test vérifie un seul état demandé par le cahier des charges.

Trois états sont bloquants (exam_blocking_checks) : la revendication liée à un
volume créé pour elle par la StorageClass, le témoin relu intact après la
recréation du Pod, et la cause du Pending consignée avant la correction.

Tous échouent avant le travail : archives ne contient que la revendication
journal-ancien, Pending, et ~/archives/ est vide. Une attente ne s'ouvre que si
l'objet attendu existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "archives"
PVC, CLASSE, TAILLE = "registre-donnees", "conserve", "256Mi"
APP, CHEMIN = "registre", "/var/lib/registre"
TEMOIN = f"{CHEMIN}/temoin.txt"
ANCIEN, CLASSE_ABSENTE, TAILLE_ANCIEN = "journal-ancien", "rapide", "100Mi"
MEMOIRE = "/var/lib/dsoxlab/challenge-donnees-qui-survivent.json"
MANQUE = re.compile(r"not found|absent|introuvable|manqu|missing|n'existe pas|inexistant|existe pas",
                    re.IGNORECASE)
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _instant(horodatage: str) -> float:
    return datetime.fromisoformat(horodatage.replace("Z", "+00:00")).timestamp()


def _revendication(host, nom: str) -> dict | None:
    """La revendication ; si elle existe sans être liée, on lui laisse le temps de l'être."""
    pvc = _json(host, f"-n {NS} get pvc {nom}")
    fin = time.monotonic() + ATTENTE
    while pvc is not None and pvc["status"].get("phase") != "Bound" and _consommee(host, nom) \
            and time.monotonic() < fin:
        time.sleep(PAS)
        pvc = _json(host, f"-n {NS} get pvc {nom}") or pvc
    return pvc


def _consommee(host, nom: str) -> bool:
    """Un Pod du namespace monte-t-il cette revendication ? Sans lui, rien ne la liera."""
    for p in (_json(host, f"-n {NS} get pods") or {}).get("items", []):
        for v in p["spec"].get("volumes") or []:
            if (v.get("persistentVolumeClaim") or {}).get("claimName") == nom:
                return True
    return False


def _volume(host, pvc: dict | None) -> dict | None:
    nom = (pvc or {}).get("spec", {}).get("volumeName")
    return _json(host, f"get pv {nom}") if nom else None


def _disponible(d: dict) -> bool:
    s = d.get("status") or {}
    voulus = d["spec"].get("replicas", 1)
    return s.get("observedGeneration") == d["metadata"]["generation"] \
        and s.get("updatedReplicas") == voulus and s.get("availableReplicas") == voulus


def _deploiement(host) -> dict | None:
    d = _json(host, f"-n {NS} get deployment {APP}")
    fin = time.monotonic() + ATTENTE
    while d is not None and not _disponible(d) and time.monotonic() < fin:
        time.sleep(PAS)
        d = _json(host, f"-n {NS} get deployment {APP}") or d
    return d


def _pod_qui_monte(host, d: dict) -> tuple[dict | None, str | None]:
    """Le Pod Running du Deployment, et le conteneur qui monte la revendication au chemin demandé."""
    selecteur = ",".join(f"{k}={v}" for k, v in d["spec"]["selector"].get("matchLabels", {}).items())
    pods = [p for p in (_json(host, f"-n {NS} get pods -l {selecteur}") or {}).get("items", [])
            if not p["metadata"].get("deletionTimestamp") and p["status"].get("phase") == "Running"]
    for p in pods:
        volumes = {v["name"] for v in p["spec"].get("volumes") or []
                   if (v.get("persistentVolumeClaim") or {}).get("claimName") == PVC}
        for c in p["spec"]["containers"]:
            if any(m.get("mountPath") == CHEMIN and m["name"] in volumes for m in c.get("volumeMounts") or []):
                return p, c["name"]
    return (pods[0] if pods else None), None


def _dans_le_pod(host, pod: dict, conteneur: str, commande: str) -> str | None:
    res = host.run(f"{ADMIN} -n {NS} exec {pod['metadata']['name']} -c {conteneur} -- {commande}")
    return res.stdout.strip() if res.rc == 0 else None


def _absent_deploiement() -> str:
    return message(en=f"No Deployment {APP} in {NS}.", fr=f"Aucun Deployment {APP} dans {NS}.")


# ----------------------------------------------------------------------
# 1. La revendication est liée à un volume créé pour elle. BLOQUANT.
# ----------------------------------------------------------------------
def test_registre_donnees_est_liee_a_un_volume_cree_par_la_classe(host):
    pvc = _revendication(host, PVC)
    assert pvc is not None, message(en=f"No claim {PVC} in {NS}.", fr=f"Aucune revendication {PVC} dans {NS}.")
    spec = pvc["spec"]
    demande = (spec.get("resources") or {}).get("requests", {}).get("storage")
    assert spec.get("storageClassName") == CLASSE and demande == TAILLE \
        and spec.get("accessModes") == ["ReadWriteOnce"], message(
        en=f"{PVC} requests class {spec.get('storageClassName')!r}, {demande!r}, {spec.get('accessModes')}. "
        f"Expected the class {CLASSE}, {TAILLE}, ReadWriteOnce only.",
        fr=f"{PVC} demande la classe {spec.get('storageClassName')!r}, {demande!r}, {spec.get('accessModes')}. "
        f"Attendu la classe {CLASSE}, {TAILLE}, ReadWriteOnce seul.",
    )
    assert pvc["status"].get("phase") == "Bound", message(
        en=f"{PVC} is {pvc['status'].get('phase')}: no volume is bound to it yet.",
        fr=f"{PVC} est {pvc['status'].get('phase')} : aucun volume ne lui est encore lié.",
    )
    pv = _volume(host, pvc)
    classe = _json(host, f"get storageclass {CLASSE}")
    fournisseur = ((pv or {}).get("metadata", {}).get("annotations") or {}).get("pv.kubernetes.io/provisioned-by")
    cree_pour_elle = pv is not None and classe is not None and fournisseur == classe.get("provisioner") \
        and (pv["spec"].get("claimRef") or {}).get("uid") == pvc["metadata"]["uid"] \
        and _instant(pv["metadata"]["creationTimestamp"]) >= _instant(pvc["metadata"]["creationTimestamp"])
    assert cree_pour_elle, message(
        en=f"The volume bound to {PVC} was not created for it by the provisioner of the class {CLASSE}: "
        "it was prepared in advance, or the class does not exist.",
        fr=f"Le volume lié à {PVC} n'a pas été créé pour elle par le provisionneur de la classe {CLASSE} : "
        "il a été préparé d'avance, ou la classe n'existe pas.",
    )


# ----------------------------------------------------------------------
# 2. Le Pod de l'application monte la revendication et a écrit le témoin.
# ----------------------------------------------------------------------
def test_registre_monte_la_revendication_et_a_ecrit_le_temoin(host):
    d = _deploiement(host)
    assert d is not None, _absent_deploiement()
    pod, conteneur = _pod_qui_monte(host, d)
    assert pod is not None and conteneur is not None, message(
        en=f"No running Pod of {APP} mounts the claim {PVC} on {CHEMIN}.",
        fr=f"Aucun Pod de {APP} en marche ne monte la revendication {PVC} sur {CHEMIN}.",
    )
    ligne = (_dans_le_pod(host, pod, conteneur, f"head -n 1 {TEMOIN}") or "").strip()
    assert ligne.startswith(f"{APP}-"), message(
        en=f"{TEMOIN} is missing, or its first line {ligne!r} is not the name of the Pod of {APP} that wrote it.",
        fr=f"{TEMOIN} manque, ou sa première ligne {ligne!r} n'est pas le nom du Pod de {APP} qui l'a écrit.",
    )


# ----------------------------------------------------------------------
# 3. Le témoin a survécu à son Pod, intact. BLOQUANT.
# ----------------------------------------------------------------------
def test_le_temoin_a_survecu_a_la_recreation_du_pod(host):
    d = _deploiement(host)
    assert d is not None, _absent_deploiement()
    pod, conteneur = _pod_qui_monte(host, d)
    assert pod is not None and conteneur is not None, message(
        en=f"No running Pod of {APP} mounts the claim {PVC} on {CHEMIN}.",
        fr=f"Aucun Pod de {APP} en marche ne monte la revendication {PVC} sur {CHEMIN}.",
    )
    actuel = pod["metadata"]["name"]
    ligne = (_dans_le_pod(host, pod, conteneur, f"head -n 1 {TEMOIN}") or "").strip()
    crees = set()
    for e in (_json(host, f"-n {NS} get events --field-selector reason=SuccessfulCreate") or {}).get("items", []):
        objet = e.get("involvedObject") or {}
        if objet.get("kind") == "ReplicaSet" and objet.get("name", "").startswith(f"{APP}-"):
            crees.add((e.get("message") or "").removeprefix("Created pod: ").strip())
    assert ligne and ligne != actuel and ligne in crees, message(
        en=f"The witness names {ligne or 'no Pod'!r}, and the running Pod is {actuel}. Expected: the file written "
        f"by an earlier Pod of {APP}, read again by the Pod its controller recreated.",
        fr=f"Le témoin nomme {ligne or 'aucun Pod'!r}, et le Pod en marche est {actuel}. Attendu : le fichier écrit "
        f"par un Pod antérieur de {APP}, relu par le Pod que son contrôleur a recréé.",
    )
    ecrit = _dans_le_pod(host, pod, conteneur, f"stat -c %Y {TEMOIN}")
    assert ecrit is not None and int(ecrit) < _instant(pod["metadata"]["creationTimestamp"]), message(
        en="The witness was modified after the current Pod was created: it is no longer intact.",
        fr="Le témoin a été modifié après la création du Pod actuel : il n'est plus intact.",
    )


# ----------------------------------------------------------------------
# 4. La reclaim policy du volume, lue sur le PersistentVolume.
# ----------------------------------------------------------------------
def test_le_volume_de_registre_donnees_est_en_retain(host):
    pv = _volume(host, _json(host, f"-n {NS} get pvc {PVC}"))
    assert pv is not None, message(
        en=f"No volume is bound to {PVC}: there is no reclaim policy to read.",
        fr=f"Aucun volume n'est lié à {PVC} : il n'y a pas de reclaim policy à lire.",
    )
    politique = pv["spec"].get("persistentVolumeReclaimPolicy")
    assert politique == "Retain", message(
        en=f"The volume {pv['metadata']['name']} has the reclaim policy {politique}: its data would go with "
        "the claim. Expected Retain.",
        fr=f"Le volume {pv['metadata']['name']} a la reclaim policy {politique} : ses données partiraient avec "
        "la revendication. Attendu Retain.",
    )


# ----------------------------------------------------------------------
# 5. La cause du Pending est consignée avant la correction. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_cause_du_pending_est_consignee_avant_la_correction(host):
    chemin = f"{_maison(host)}/archives/cause.txt"
    f = host.file(chemin)
    contenu = f.content_string if f.exists else ""
    assert CLASSE_ABSENTE in contenu and MANQUE.search(contenu), message(
        en=f"~/archives/cause.txt does not say why {ANCIEN} stays Pending: what it asks for without finding it, "
        "by its name, and that it is missing.",
        fr=f"~/archives/cause.txt ne dit pas pourquoi {ANCIEN} reste Pending : ce qu'elle demande sans le trouver, "
        "par son nom, et que cela manque.",
    )
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset k8s-challenge-donnees-qui-survivent.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-challenge-donnees-qui-survivent.",
        ))
    corrections = []
    classe = _json(host, f"get storageclass {CLASSE_ABSENTE}")
    if classe is not None:
        corrections.append(_instant(classe["metadata"]["creationTimestamp"]))
    pvc = _json(host, f"-n {NS} get pvc {ANCIEN}")
    if pvc is not None and pvc["metadata"]["uid"] != json.loads(res.stdout)["journal_uid"]:
        corrections.append(_instant(pvc["metadata"]["creationTimestamp"]))
    pv = _volume(host, pvc)
    if pv is not None:
        corrections.append(_instant(pv["metadata"]["creationTimestamp"]))
    if corrections:
        assert int(host.check_output(f"stat -c %Y {chemin}")) <= min(corrections), message(
            en="The cause was written, or rewritten, after the correction: the diagnosis comes first.",
            fr="La cause a été écrite, ou réécrite, après la correction : le diagnostic vient d'abord.",
        )


# ----------------------------------------------------------------------
# 6. La revendication préinstallée est Bound après correction.
# ----------------------------------------------------------------------
def test_journal_ancien_est_bound(host):
    pvc = _revendication(host, ANCIEN)
    assert pvc is not None, message(en=f"No claim {ANCIEN} in {NS}.", fr=f"Aucune revendication {ANCIEN} dans {NS}.")
    demande = (pvc["spec"].get("resources") or {}).get("requests", {}).get("storage")
    assert pvc["status"].get("phase") == "Bound" and demande == TAILLE_ANCIEN, message(
        en=f"{ANCIEN} is {pvc['status'].get('phase')} and requests {demande!r}. Expected Bound, still requesting "
        f"{TAILLE_ANCIEN}.",
        fr=f"{ANCIEN} est {pvc['status'].get('phase')} et demande {demande!r}. Attendu Bound, en demandant toujours "
        f"{TAILLE_ANCIEN}.",
    )
