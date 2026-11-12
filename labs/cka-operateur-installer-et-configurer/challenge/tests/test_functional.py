"""test_functional.py : cka-operateur-installer-et-configurer

Six tests, un par état demandé. Ils lisent l'état du cluster et interrogent
mongod lui-même, jamais les commandes tapées.

Deux d'entre eux ferment des raccourcis :
- le StatefulSet et le Service doivent APPARTENIR à la ressource registre : un
  replica set monté à la main, sans opérateur, porterait les mêmes noms ;
- le seuil de 250 ms se lit dans les options de démarrage de mongod, que
  l'opérateur écrit dans sa configuration. Un réglage posé à chaud dans mongod
  changerait la valeur courante, pas ces options, et disparaîtrait au premier
  redémarrage.

Les attentes ne s'ouvrent que si la ressource existe, et le seuil n'est attendu
que si la ressource le déclare : l'état de départ se note vite. Les deux attentes
partagent UNE échéance de 240 s, sous le délai de 300 s que dsoxlab accorde à
toute la suite : elle couvre le premier tirage de l'image du serveur (433 Mo).
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "mongodb"
CRD = "mongodbcommunity.mongodbcommunity.mongodb.com"
OPERATEUR = "mongodb-kubernetes-operator"
DIGEST_OPERATEUR = "sha256:953d43a57a5d4ebcb7f726a6d93dead23c75231ca753b68865bf098232cbce1a"
DIGEST_SERVEUR = "sha256:77351e6c8e806a5f55949212e2fe521d0866069d3348d1032414e2e256cd9651"
RESSOURCE = "registre"
SERVICE = f"{RESSOURCE}-svc"
POD = f"{RESSOURCE}-0"
CONNEXION = f"{RESSOURCE}-admin-atelier"
SEUIL_MS = 250
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

BUDGET_S = 240
PAS_S = 5
_ECHEANCE: list[float] = []


def _echeance() -> float:
    """Une seule échéance pour toute la suite, fixée à la première attente."""
    if not _ECHEANCE:
        _ECHEANCE.append(time.monotonic() + BUDGET_S)
    return _ECHEANCE[0]


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _objet(host, args: str) -> dict | None:
    res = _kubectl(host, f"{args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _ressource(host) -> dict | None:
    return _objet(host, f"-n {NAMESPACE} get mongodbcommunity {RESSOURCE}")


def _phase(ressource: dict | None) -> str:
    return ((ressource or {}).get("status") or {}).get("phase") or "(none)"


def _attendre_running(host) -> dict | None:
    ressource = _ressource(host)
    if ressource is None or _phase(ressource) in ("Running", "Failed"):
        return ressource
    fin = _echeance()
    while ressource is not None and _phase(ressource) not in ("Running", "Failed") and time.monotonic() < fin:
        time.sleep(PAS_S)
        ressource = _ressource(host) or ressource
    return ressource


# ----------------------------------------------------------------------
# 1. La CRD de l'opérateur est établie.
# ----------------------------------------------------------------------
def test_la_crd_mongodbcommunity_est_etablie(host):
    crd = _objet(host, f"get crd {CRD}")
    conditions = ((crd or {}).get("status") or {}).get("conditions") or []
    etablie = any(c.get("type") == "Established" and c.get("status") == "True" for c in conditions)
    assert etablie, message(
        en=f"The CRD {CRD} is {'absent' if crd is None else 'not Established'}. The API server does not know the "
        "MongoDBCommunity kind yet: the operator's definitions come first.",
        fr=f"La CRD {CRD} est {'absente' if crd is None else 'non établie'}. Le serveur d'API ne connaît pas encore "
        "le type MongoDBCommunity : les définitions de l'opérateur passent en premier.",
    )


# ----------------------------------------------------------------------
# 2. L'opérateur est disponible, sur son image épinglée.
# ----------------------------------------------------------------------
def test_l_operateur_est_disponible_sur_son_image_epinglee(host):
    dep = _objet(host, f"-n {NAMESPACE} get deployment {OPERATEUR}")
    assert dep is not None, message(
        en=f"No Deployment {OPERATEUR} in {NAMESPACE}.",
        fr=f"Aucun Deployment {OPERATEUR} dans {NAMESPACE}.",
    )
    conditions = (dep.get("status") or {}).get("conditions") or []
    disponible = any(c.get("type") == "Available" and c.get("status") == "True" for c in conditions)
    images = [c.get("image", "") for c in dep["spec"]["template"]["spec"]["containers"]]
    epinglee = any(i.endswith(DIGEST_OPERATEUR) for i in images)
    assert disponible and epinglee, message(
        en=f"The operator is {'available' if disponible else 'not available'} and runs {images}. Expected available, "
        f"on the 1.15.0 image pinned by its digest {DIGEST_OPERATEUR}: a tag alone can be republished.",
        fr=f"L'opérateur est {'disponible' if disponible else 'indisponible'} et lance {images}. Attendu disponible, "
        f"sur l'image 1.15.0 épinglée par son digest {DIGEST_OPERATEUR} : un tag seul peut être republié.",
    )


# ----------------------------------------------------------------------
# 3. La ressource registre est en phase Running.
# ----------------------------------------------------------------------
def test_registre_est_running(host):
    ressource = _attendre_running(host)
    assert ressource is not None, message(
        en=f"No MongoDBCommunity {RESSOURCE} in {NAMESPACE}.",
        fr=f"Aucune MongoDBCommunity {RESSOURCE} dans {NAMESPACE}.",
    )
    statut = ressource.get("status") or {}
    assert _phase(ressource) == "Running", message(
        en=f"{RESSOURCE} is in phase {_phase(ressource)} ({statut.get('message', 'no message')}). Expected Running: "
        "the operator says so once the replica set answers.",
        fr=f"{RESSOURCE} est en phase {_phase(ressource)} ({statut.get('message', 'aucun message')}). Attendu "
        "Running : l'opérateur l'écrit quand le replica set répond.",
    )


# ----------------------------------------------------------------------
# 4. Le StatefulSet et le Service appartiennent à registre.
# ----------------------------------------------------------------------
def test_le_statefulset_et_le_service_appartiennent_a_registre(host):
    ressource = _ressource(host)
    uid = ((ressource or {}).get("metadata") or {}).get("uid")
    vus = {}
    for genre, nom in (("statefulset", RESSOURCE), ("service", SERVICE)):
        objet = _objet(host, f"-n {NAMESPACE} get {genre} {nom}")
        if objet is None:
            vus[f"{genre}/{nom}"] = "absent"
            continue
        proprietaires = objet["metadata"].get("ownerReferences") or []
        vus[f"{genre}/{nom}"] = [f"{o.get('kind')}/{o.get('name')}" for o in proprietaires] or "no owner"
        if not any(o.get("uid") == uid and o.get("kind") == "MongoDBCommunity" and o.get("controller")
                   for o in proprietaires):
            vus[f"{genre}/{nom}"] = f"owners {vus[f'{genre}/{nom}']}"
        else:
            vus[f"{genre}/{nom}"] = "ok"
    assert uid and all(v == "ok" for v in vus.values()), message(
        en=f"Seen: {vus}. Expected both objects created by the operator for {RESSOURCE}, which is their controlling "
        "owner: objects made by hand carry the same names and no owner.",
        fr=f"Vu : {vus}. Attendu les deux objets créés par l'opérateur pour {RESSOURCE}, qui en est le propriétaire "
        "contrôleur : des objets faits à la main portent les mêmes noms et aucun propriétaire.",
    )


# ----------------------------------------------------------------------
# 5. mongod tourne sur l'image du serveur épinglée par digest.
# ----------------------------------------------------------------------
def test_mongod_tourne_sur_le_serveur_epingle(host):
    pod = _objet(host, f"-n {NAMESPACE} get pod {POD}")
    assert pod is not None, message(
        en=f"No Pod {POD} in {NAMESPACE}.",
        fr=f"Aucun Pod {POD} dans {NAMESPACE}.",
    )
    image = next((c.get("image", "") for c in pod["spec"]["containers"] if c["name"] == "mongod"), "")
    tourne = next((s.get("imageID", "") for s in (pod.get("status") or {}).get("containerStatuses") or []
                   if s["name"] == "mongod"), "")
    assert image.endswith(DIGEST_SERVEUR) and tourne.endswith(DIGEST_SERVEUR), message(
        en=f"The mongod container asks for {image or 'nothing'} and runs {tourne or 'nothing'}. Expected the server "
        f"pinned by {DIGEST_SERVEUR}: the operator builds the image name from the version, a tag rebuilt every day.",
        fr=f"Le conteneur mongod demande {image or 'rien'} et lance {tourne or 'rien'}. Attendu le serveur épinglé par "
        f"{DIGEST_SERVEUR} : l'opérateur compose le nom de l'image à partir de la version, un tag reconstruit chaque "
        "jour.",
    )


# ----------------------------------------------------------------------
# 6. Le seuil de 250 ms est appliqué au démarrage de mongod.
# ----------------------------------------------------------------------
def _seuil_au_demarrage(host) -> object:
    secret = _objet(host, f"-n {NAMESPACE} get secret {CONNEXION}")
    brut = ((secret or {}).get("data") or {}).get("connectionString.standard")
    if not brut:
        return "(no connection secret)"
    uri = host.run(f"echo {brut} | base64 -d").stdout.strip()
    res = _kubectl(
        host,
        f"-n {NAMESPACE} exec {POD} -c mongod -- mongosh '{uri}' --quiet --eval "
        "'JSON.stringify((db.adminCommand({getCmdLineOpts: 1}).parsed.operationProfiling || {}).slowOpThresholdMs ?? null)'",
    )
    if res.rc != 0:
        return "(mongod does not answer)"
    try:
        return json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return res.stdout.strip()


def _declare_le_seuil(config: dict) -> bool:
    """La clé s'écrit à plat (« operationProfiling.slowOpThresholdMs ») ou imbriquée."""
    if config.get("operationProfiling.slowOpThresholdMs") == SEUIL_MS:
        return True
    return (config.get("operationProfiling") or {}).get("slowOpThresholdMs") == SEUIL_MS


def test_mongod_demarre_avec_un_seuil_de_250_ms(host):
    seuil = _seuil_au_demarrage(host)
    declare = ((_ressource(host) or {}).get("spec") or {}).get("additionalMongodConfig") or {}
    # On n'attend que si la ressource déclare le seuil : l'opérateur est alors en
    # train de l'appliquer. Sinon, rien ne viendra.
    if seuil != SEUIL_MS and _declare_le_seuil(declare):
        fin = _echeance()
        while seuil != SEUIL_MS and time.monotonic() < fin:
            time.sleep(PAS_S)
            seuil = _seuil_au_demarrage(host)
    assert seuil == SEUIL_MS, message(
        en=f"mongod started with a slow operation threshold of {seuil}. Expected {SEUIL_MS} ms, written by the "
        "operator into the mongod configuration: a value set live in mongod is not part of its startup options.",
        fr=f"mongod a démarré avec un seuil d'opérations lentes de {seuil}. Attendu {SEUIL_MS} ms, écrit par "
        "l'opérateur dans la configuration de mongod : une valeur posée à chaud dans mongod ne fait pas partie de "
        "ses options de démarrage.",
    )
