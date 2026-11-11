"""test_functional.py : k8s-verifier-et-attendre

Ces tests comparent le dossier ~/deploiement/ au cluster « lab » avec
kubectl diff, lisent le relevé des codes de sortie, vérifient que la nouvelle
version tourne réellement (pas seulement que le Deployment se dit Available),
puis rejouent le script deployer.sh de l'apprenant sur le dossier inchangé.
Un test vérifie un seul état demandé par l'énoncé.

Tous échouent avant le travail : le Job de migration du dossier n'est pas
appliqué, le relevé et le script n'existent pas, et facturation tourne en
version 1.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
APPRENANT = 'sudo -u "${SUDO_USER:-ansible}" -H'
NS = "paiements"
V2 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
ATTENTE = 90
PAS = 3


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


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/deploiement/releve.txt")
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if ligne and not ligne.startswith("#") and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


# ----------------------------------------------------------------------
# 1. L'état du cluster correspond au dossier.
# ----------------------------------------------------------------------
def test_le_cluster_correspond_au_dossier(host):
    res = host.run(f"{ADMIN} diff -f {_maison(host)}/deploiement/ --recursive=false")
    assert res.rc == 0, message(
        en=f"Comparing ~/deploiement/ with the cluster finds differences, or cannot be made "
        f"(code {res.rc}). Every file of the folder must be applied, as it is.",
        fr=f"Comparer ~/deploiement/ au cluster trouve des différences, ou ne peut pas se faire "
        f"(code {res.rc}). Chaque fichier du dossier doit être appliqué, tel qu'il est.",
    )


# ----------------------------------------------------------------------
# 2. Le relevé donne les trois codes de sortie de kubectl diff.
# ----------------------------------------------------------------------
def test_le_releve_donne_les_codes_de_sortie_de_kubectl_diff(releve):
    attendus = {"aucune-difference": "0", "differences": "1", "erreur": "2"}
    lus = {cle: releve.get(cle, "") for cle in attendus}
    assert lus == attendus, message(
        en=f"~/deploiement/releve.txt gives {lus}. Expected the exit code of kubectl diff in each "
        "of the three cases, as you measured it.",
        fr=f"~/deploiement/releve.txt donne {lus}. Attendu le code de sortie de kubectl diff dans "
        "chacun des trois cas, tel que vous l'avez mesuré.",
    )


# ----------------------------------------------------------------------
# 3. La nouvelle version tourne vraiment, et la migration est terminée.
# ----------------------------------------------------------------------
def _nouvelle_version(d: dict, pods: list[dict]) -> bool:
    s = d.get("status") or {}
    voulus = d["spec"].get("replicas", 1)
    images = [c.get("image") for p in pods for c in p["spec"]["containers"]]
    prets = [p for p in pods if any(c.get("type") == "Ready" and c.get("status") == "True"
                                    for c in (p.get("status") or {}).get("conditions") or [])]
    return s.get("observedGeneration") == d["metadata"]["generation"] \
        and s.get("updatedReplicas") == voulus and s.get("availableReplicas") == voulus \
        and len(pods) == voulus and set(images) == {V2} and len(prets) == voulus


def test_la_version_2_tourne_et_la_migration_est_terminee(host):
    d = _json(host, f"-n {NS} get deployment facturation")
    assert d is not None, message(
        en="The facturation Deployment no longer exists.",
        fr="Le Deployment facturation n'existe plus.",
    )
    pods = [p for p in (_json(host, f"-n {NS} get pods -l app=facturation") or {}).get("items", [])
            if not p["metadata"].get("deletionTimestamp")]
    if d["spec"]["template"]["spec"]["containers"][0].get("image") == V2:
        fin = time.monotonic() + ATTENTE
        while not _nouvelle_version(d, pods) and time.monotonic() < fin:
            time.sleep(PAS)
            d = _json(host, f"-n {NS} get deployment facturation") or d
            pods = [p for p in (_json(host, f"-n {NS} get pods -l app=facturation") or {}).get("items", [])
                    if not p["metadata"].get("deletionTimestamp")]
    images = sorted({c.get("image") for p in pods for c in p["spec"]["containers"]})
    assert _nouvelle_version(d, pods), message(
        en=f"facturation is not entirely on version 2: its Pods run {images}. A Deployment can say "
        "Available while old Pods still serve.",
        fr=f"facturation n'est pas entièrement en version 2 : ses Pods tournent en {images}. Un "
        "Deployment peut se dire Available alors que d'anciens Pods servent encore.",
    )
    job = _json(host, f"-n {NS} get job migration") or {}
    fini = any(c.get("type") == "Complete" and c.get("status") == "True"
               for c in (job.get("status") or {}).get("conditions") or [])
    assert fini, message(
        en="The migration Job is not complete.",
        fr="Le Job migration n'est pas terminé.",
    )


# ----------------------------------------------------------------------
# 4. deployer.sh sait s'arrêter : 0 sur un dossier sans différence, erreur et
#    rien d'appliqué sur un dossier que kubectl diff ne peut pas comparer.
# ----------------------------------------------------------------------
#: Mesuré le 2026-11-11 : sur un dossier qui mêle un objet valide et un objet que
#: le serveur refuse, kubectl diff sort en 2, et kubectl apply crée l'objet
#: valide avant d'échouer. Un script qui applique malgré l'erreur de diff laisse
#: donc le témoin derrière lui.
TEMOIN = """apiVersion: v1
kind: ConfigMap
metadata:
  name: temoin-deployer
  namespace: paiements
data:
  ESSAI: "1"
"""
REFUSE = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: refuse-deployer
  namespace: paiements
spec:
  selector:
    matchLabels:
      app: refuse-deployer
  template:
    metadata:
      labels:
        app: refuse-deployer
    spec:
      containers:
        - name: refuse
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          resources:
            requests:
              memory: 256Mi
            limits:
              memory: 128Mi
"""


def test_deployer_sh_sait_s_arreter(host):
    maison = _maison(host)
    script = f"{maison}/deploiement/deployer.sh"
    f = host.file(script)
    assert f.exists and f.mode & 0o100, message(
        en="~/deploiement/deployer.sh does not exist or is not executable.",
        fr="~/deploiement/deployer.sh n'existe pas ou n'est pas exécutable.",
    )
    lancer = f"{APPRENANT} timeout 120 {script}"

    avant = (_json(host, f"-n {NS} get deployment facturation") or {}).get("metadata", {}).get("resourceVersion")
    res = host.run(f"{lancer} {maison}/deploiement < /dev/null")
    apres = (_json(host, f"-n {NS} get deployment facturation") or {}).get("metadata", {}).get("resourceVersion")
    assert res.rc == 0 and avant is not None and avant == apres, message(
        en=f"Run on the unchanged folder, deployer.sh exits with code {res.rc}"
        f"{'' if avant == apres else ' and modifies facturation'}. Expected code 0 when nothing differs.",
        fr=f"Lancé sur le dossier inchangé, deployer.sh sort en code {res.rc}"
        f"{'' if avant == apres else ' et modifie facturation'}. Attendu le code 0 quand rien ne diffère.",
    )

    copie = host.check_output("sudo mktemp -d /tmp/deployer-essai-XXXXXX").strip()
    try:
        host.run(f"sudo cp {maison}/deploiement/*.yaml {copie}/")
        host.run(f"echo {base64.b64encode(TEMOIN.encode()).decode()} | base64 -d "
                 f"| sudo tee {copie}/zz-temoin.yaml > /dev/null")
        host.run(f"echo {base64.b64encode(REFUSE.encode()).decode()} | base64 -d "
                 f"| sudo tee {copie}/zz-refuse.yaml > /dev/null")
        host.run(f"sudo chmod -R a+rX {copie}")
        res = host.run(f"{lancer} {copie} < /dev/null")
        temoin = host.run(f"{ADMIN} -n {NS} get configmap temoin-deployer").rc == 0
    finally:
        host.run(f"{ADMIN} -n {NS} delete configmap temoin-deployer deployment/refuse-deployer --ignore-not-found")
        host.run(f"sudo rm -rf {copie}")
    constat_fr = "a appliqué une partie du dossier" if temoin else "n'a rien appliqué"
    assert res.rc != 0 and not temoin, message(
        en=f"Run on a folder that kubectl diff cannot compare (an object refused by the server), "
        f"deployer.sh exits with code {res.rc} and {'applied part of the folder' if temoin else 'applied nothing'}. "
        "Expected: a stop on error, before applying anything.",
        fr=f"Lancé sur un dossier que kubectl diff ne peut pas comparer (un objet refusé par le serveur), "
        f"deployer.sh sort en code {res.rc} et {constat_fr}. "
        "Attendu : un arrêt en erreur, avant d'appliquer quoi que ce soit.",
    )
