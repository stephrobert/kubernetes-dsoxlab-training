"""test_functional.py : ckad-configmap-secret-injection

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. Les deux premières lisent le ConfigMap et le Secret ;
les deux dernières entrent dans le conteneur, et ce sont elles qui prouvent
quelque chose : un envFrom qui nomme un ConfigMap inexistant, ou un volume
déclaré mais jamais monté, laisseraient un manifeste plausible et un
conteneur vide. On refuse aussi un mot de passe écrit en clair dans le Pod.
"""

from __future__ import annotations

import base64
import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "app"
CONFIGMAP = "app-settings"
SECRET = "db-credentials"  # noqa: S105 - nom d'un Secret, pas un mot de passe
MONTAGE = "/etc/app-config"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Le ConfigMap porte les réglages et le fichier.
# ----------------------------------------------------------------------
def test_le_configmap_porte_la_configuration(host):
    cm = _json(host, f"-n {NAMESPACE} get configmap {CONFIGMAP}",
               message(
            en=f"No ConfigMap {CONFIGMAP} in {NAMESPACE}.",
            fr=f"Aucun ConfigMap {CONFIGMAP} dans {NAMESPACE}.",
        ))
    data = cm.get("data") or {}
    assert data.get("APP_MODE") == "production", message(
        en=f"APP_MODE is {data.get('APP_MODE')!r} in {CONFIGMAP}, expected 'production'.",
        fr=f"APP_MODE vaut {data.get('APP_MODE')!r} dans {CONFIGMAP}, attendu 'production'.",
    )
    assert data.get("LOG_LEVEL") == "info", message(
        en=f"LOG_LEVEL is {data.get('LOG_LEVEL')!r} in {CONFIGMAP}, expected 'info'.",
        fr=f"LOG_LEVEL vaut {data.get('LOG_LEVEL')!r} dans {CONFIGMAP}, attendu 'info'.",
    )
    assert "config.yaml" in data, message(
        en=f"{CONFIGMAP} has no config.yaml key. A whole file goes into "
        "a ConfigMap as a key whose value is the content: "
        "kubectl create configmap --from-file, or a | block in the manifest.",
        fr=f"{CONFIGMAP} n'a pas de clé config.yaml. Un fichier entier se met dans "
        "un ConfigMap comme une clé dont la valeur est le contenu : "
        "kubectl create configmap --from-file, ou un bloc | dans le manifeste.",
    )
    assert "port: 8080" in data["config.yaml"], message(
        en=f"config.yaml exists in {CONFIGMAP} but does not contain 'port: 8080'. "
        f"Contents: {data['config.yaml'][:120]!r}",
        fr=f"config.yaml existe dans {CONFIGMAP} mais ne contient pas 'port: 8080'. "
        f"Contenu : {data['config.yaml'][:120]!r}",
    )


# ----------------------------------------------------------------------
# 2. Le Secret porte les identifiants.
# ----------------------------------------------------------------------
def test_le_secret_porte_les_identifiants(host):
    secret = _json(host, f"-n {NAMESPACE} get secret {SECRET}",
                   message(
            en=f"No Secret {SECRET} in {NAMESPACE}.",
            fr=f"Aucun Secret {SECRET} dans {NAMESPACE}.",
        ))
    data = secret.get("data") or {}
    for cle in ("DB_HOST", "DB_PASSWORD"):
        assert data.get(cle), message(
            en=f"Secret {SECRET} has no {cle} key, or it is empty. "
            f"Keys present: {sorted(data)}",
            fr=f"Le Secret {SECRET} n'a pas de clé {cle}, ou elle est vide. "
            f"Clés présentes : {sorted(data)}",
        )
    hote = base64.b64decode(data["DB_HOST"]).decode()
    assert hote == "db.internal.svc", message(
        en=f"DB_HOST is {hote!r}, expected 'db.internal.svc'.",
        fr=f"DB_HOST vaut {hote!r}, attendu 'db.internal.svc'.",
    )


# ----------------------------------------------------------------------
# 3. Le Pod reçoit les variables, par référence et non en clair.
# ----------------------------------------------------------------------
def test_le_pod_recoit_les_variables_par_reference(host):
    pod = _json(host, f"-n {NAMESPACE} get pod {POD}", f"Aucun Pod {POD} dans {NAMESPACE}.")
    assert pod["status"].get("phase") == "Running", message(
        en=f"Pod {POD} is in phase {pod['status'].get('phase')!r}. An envFrom or "
        "a volume naming a non-existent object leaves the Pod stuck in "
        "CreateContainerConfigError: its events say so.",
        fr=f"Le Pod {POD} est en phase {pod['status'].get('phase')!r}. Un envFrom ou "
        "un volume qui nomme un objet inexistant bloque le Pod en "
        "CreateContainerConfigError : ses events le disent.",
    )
    conteneur = pod["spec"]["containers"][0]
    sources = {
        (next(iter(ref.keys())), next(iter(ref.values())).get("name"))
        for ref in conteneur.get("envFrom") or []
    }
    en_clair = [
        e["name"] for e in conteneur.get("env") or []
        if e["name"] in ("DB_PASSWORD", "DB_HOST") and "value" in e
    ]
    assert not en_clair, message(
        en=f"{en_clair} are written in clear text in the Pod. The house rule: the "
        "Pod carries a reference to the Secret, never the value.",
        fr=f"{en_clair} sont écrits en clair dans le Pod. La règle de la maison : le "
        "Pod porte une référence au Secret, jamais la valeur.",
    )
    par_secret = ("secretRef", SECRET) in sources or any(
        e["name"] == "DB_PASSWORD"
        and ((e.get("valueFrom") or {}).get("secretKeyRef") or {}).get("name") == SECRET
        for e in conteneur.get("env") or []
    )
    assert par_secret, message(
        en=f"DB_PASSWORD does not come from Secret {SECRET}: neither envFrom secretRef nor "
        "env valueFrom secretKeyRef references it.",
        fr=f"DB_PASSWORD ne vient pas du Secret {SECRET} : ni envFrom secretRef, ni "
        "env valueFrom secretKeyRef ne le référencent.",
    )
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- printenv APP_MODE")
    assert res.rc == 0 and res.stdout.strip() == "production", message(
        en=f"Inside the container, APP_MODE is {res.stdout.strip()!r}, expected "
        "'production'. The ConfigMap exists, but its keys do not reach the "
        "container: envFrom with configMapRef, or env key by key.",
        fr=f"Dans le conteneur, APP_MODE vaut {res.stdout.strip()!r}, attendu "
        "'production'. Le ConfigMap existe, mais ses clés n'arrivent pas au "
        "conteneur : envFrom avec configMapRef, ou env clé par clé.",
    )
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- sh -c 'test -n \"$DB_PASSWORD\" && echo present'")
    assert "present" in res.stdout, message(
        en="Inside the container, DB_PASSWORD is empty or absent. The reference to "
        "the Secret is declared, but it may not be the right key.",
        fr="Dans le conteneur, DB_PASSWORD est vide ou absent. La référence au "
        "Secret est déclarée, mais ce n'est peut-être pas la bonne clé.",
    )


# ----------------------------------------------------------------------
# 4. Le fichier est monté, et c'est bien celui du ConfigMap.
# ----------------------------------------------------------------------
def test_le_fichier_de_configuration_est_monte(host):
    pod = _json(host, f"-n {NAMESPACE} get pod {POD}", f"Aucun Pod {POD} dans {NAMESPACE}.")
    volumes = {v["name"]: v for v in pod["spec"].get("volumes") or []}
    montages = {m["mountPath"]: m["name"] for m in pod["spec"]["containers"][0].get("volumeMounts") or []}
    assert MONTAGE in montages, message(
        en=f"Nothing is mounted under {MONTAGE} in the Pod. A volume of type "
        "configMap is needed, plus a volumeMount placing it at that path.",
        fr=f"Rien n'est monté sous {MONTAGE} dans le Pod. Il faut un volume de type "
        "configMap et un volumeMount qui le place à ce chemin.",
    )
    source = volumes.get(montages[MONTAGE], {}).get("configMap", {}).get("name")
    assert source == CONFIGMAP, message(
        en=f"The volume mounted under {MONTAGE} comes from {source!r}, not from ConfigMap {CONFIGMAP}.",
        fr=f"Le volume monté sous {MONTAGE} vient de {source!r}, pas du ConfigMap {CONFIGMAP}.",
    )
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- cat {MONTAGE}/config.yaml")
    assert res.rc == 0, message(
        en=f"{MONTAGE}/config.yaml does not exist in the container. A mounted ConfigMap "
        "gives one file per key: either the config.yaml key is missing, or the mount "
        f"is not the right ConfigMap's. Output: {res.stderr.strip()[:150]}",
        fr=f"{MONTAGE}/config.yaml n'existe pas dans le conteneur. Un ConfigMap monté "
        "donne un fichier par clé : la clé config.yaml manque, ou le montage "
        f"n'est pas celui du bon ConfigMap. Sortie : {res.stderr.strip()[:150]}",
    )
    assert "port: 8080" in res.stdout, message(
        en=f"{MONTAGE}/config.yaml is mounted but does not contain 'port: 8080': "
        f"{res.stdout.strip()[:120]!r}",
        fr=f"{MONTAGE}/config.yaml est monté mais ne contient pas 'port: 8080' : "
        f"{res.stdout.strip()[:120]!r}",
    )
