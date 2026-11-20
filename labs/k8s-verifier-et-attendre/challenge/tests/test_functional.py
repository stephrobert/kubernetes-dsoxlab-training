"""test_functional.py : k8s-verifier-et-attendre

Ces tests comparent le dossier ~/deploiement/ au cluster « lab » avec
kubectl diff, lisent le relevé des codes de sortie, vérifient que la nouvelle
version tourne réellement (pas seulement que le Deployment se dit Available),
puis rejouent le script deployer.sh de l'apprenant sur le dossier inchangé,
sur un dossier refusé, et sur deux copies portant un Job qui réussit et un Job
qui échoue. Un test vérifie un seul état demandé par l'énoncé.

Depuis le 2026-11-20, le relevé ne demande plus les codes 0, 1 et 2 de
kubectl diff, des constantes que la leçon imprime : il demande la révision
actuelle de facturation, que la préparation rend différente à chaque fois (de 1
à 3 redémarrages). Et le script doit attendre les Jobs du dossier, en sortant
en erreur dès qu'un Job échoue : la leçon donne les pièces sans les assembler.

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
# 2. Le relevé donne la révision de facturation qui porte la version 2.
# ----------------------------------------------------------------------
def test_le_releve_donne_la_revision_de_la_version_2(host, releve):
    d = _json(host, f"-n {NS} get deployment facturation") or {}
    image = ((d.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers", [{}])[0].get("image")
    revision = ((d.get("metadata") or {}).get("annotations") or {}).get("deployment.kubernetes.io/revision", "")
    lue = releve.get("revision-v2", "")
    assert image == V2 and lue and lue == revision, message(
        en=f"~/deploiement/releve.txt gives revision-v2 {lue or '(empty)'!r}. Expected the revision "
        "facturation is at once version 2 is deployed, as the cluster gives it. It is not the "
        "same from one preparation of the lab to the next.",
        fr=f"~/deploiement/releve.txt donne revision-v2 {lue or '(vide)'!r}. Attendu la révision où "
        "en est facturation une fois la version 2 déployée, telle que le cluster la donne. Elle "
        "n'est pas la même d'une préparation du lab à l'autre.",
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


# ----------------------------------------------------------------------
# 5. deployer.sh attend les Jobs du dossier, et sort au plus tôt si l'un échoue.
# ----------------------------------------------------------------------
#: Un Job qui échoue doit arrêter le script bien avant les délais d'attente
#: habituels (120 s pour un rollout) : 60 s couvrent le démarrage du Pod.
DELAI_ECHEC = 60


def _job(nom: str, commande: str) -> str:
    return f"""apiVersion: batch/v1
kind: Job
metadata:
  name: {nom}
  namespace: paiements
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: {nom}
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "{commande}"]
"""


def _lancer_avec_job(host, nom: str, commande: str) -> tuple[int, float]:
    maison = _maison(host)
    copie = host.check_output("sudo mktemp -d /tmp/deployer-job-XXXXXX").strip()
    try:
        host.run(f"sudo cp {maison}/deploiement/*.yaml {copie}/")
        contenu = base64.b64encode(_job(nom, commande).encode()).decode()
        host.run(f"echo {contenu} | base64 -d | sudo tee {copie}/zz-{nom}.yaml > /dev/null")
        host.run(f"sudo chmod -R a+rX {copie}")
        debut = time.monotonic()
        res = host.run(f"{APPRENANT} timeout 150 {maison}/deploiement/deployer.sh {copie} < /dev/null")
        duree = time.monotonic() - debut
    finally:
        host.run(f"{ADMIN} -n {NS} delete job {nom} --ignore-not-found --wait=false")
        host.run(f"sudo rm -rf {copie}")
    return res.rc, duree


def test_deployer_sh_attend_les_jobs_et_s_arrete_sur_un_echec(host):
    script = f"{_maison(host)}/deploiement/deployer.sh"
    f = host.file(script)
    assert f.exists and f.mode & 0o100, message(
        en="~/deploiement/deployer.sh does not exist or is not executable.",
        fr="~/deploiement/deployer.sh n'existe pas ou n'est pas exécutable.",
    )
    rc, duree = _lancer_avec_job(host, "essai-deployer-echec", "echo echec; exit 1")
    assert rc != 0 and duree < DELAI_ECHEC, message(
        en=f"Run on a folder whose Job fails, deployer.sh exits with code {rc} after "
        f"{duree:.0f}s. Expected: an error, in less than {DELAI_ECHEC}s. A wait on the "
        "Complete condition alone never sees a failed Job, and only stops at its timeout.",
        fr=f"Lancé sur un dossier dont le Job échoue, deployer.sh sort en code {rc} après "
        f"{duree:.0f} s. Attendu : une erreur, en moins de {DELAI_ECHEC} s. Une attente sur la "
        "seule condition Complete ne voit jamais un Job en échec, et ne s'arrête qu'à son délai.",
    )
    rc, duree = _lancer_avec_job(host, "essai-deployer-reussite", "sleep 3; echo fini")
    assert rc == 0, message(
        en=f"Run on a folder whose Job succeeds, deployer.sh exits with code {rc} after "
        f"{duree:.0f}s. Expected code 0 once the Job is complete.",
        fr=f"Lancé sur un dossier dont le Job réussit, deployer.sh sort en code {rc} après "
        f"{duree:.0f} s. Attendu le code 0 une fois le Job terminé.",
    )
