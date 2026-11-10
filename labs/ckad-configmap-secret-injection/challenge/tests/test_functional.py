"""test_functional.py : ckad-configmap-secret-injection

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Un test vérifie un seul état demandé par l'énoncé. Les tests qui lisent un
objet (ConfigMap, Secret, définition du Pod) disent ce que l'apprenant a
déclaré ; les trois derniers entrent dans le conteneur et prouvent que la
déclaration produit un effet : un envFrom qui nomme un ConfigMap inexistant, ou
un volume déclaré mais jamais monté, laisseraient un manifeste plausible et un
conteneur vide. On refuse aussi un mot de passe écrit en clair dans le Pod.
"""

from __future__ import annotations

import base64
import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "app"
IMAGE = "nginx:1.27-alpine"
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


def _configmap(host) -> dict:
    cm = _json(host, f"-n {NAMESPACE} get configmap {CONFIGMAP}", message(
        en=f"No ConfigMap {CONFIGMAP} in {NAMESPACE}.",
        fr=f"Aucun ConfigMap {CONFIGMAP} dans {NAMESPACE}.",
    ))
    return cm.get("data") or {}


def _secret(host) -> dict:
    secret = _json(host, f"-n {NAMESPACE} get secret {SECRET}", message(
        en=f"No Secret {SECRET} in {NAMESPACE}.",
        fr=f"Aucun Secret {SECRET} dans {NAMESPACE}.",
    ))
    return secret.get("data") or {}


def _pod(host) -> dict:
    return _json(host, f"-n {NAMESPACE} get pod {POD}", message(
        en=f"No Pod {POD} in {NAMESPACE}.",
        fr=f"Aucun Pod {POD} dans {NAMESPACE}.",
    ))


def _conteneur(host) -> dict:
    return _pod(host)["spec"]["containers"][0]


def _cle_de_configmap(conteneur: dict, cle: str) -> bool:
    """La clé arrive par envFrom (bloc) ou par env valueFrom (clé par clé)."""
    par_bloc = any(
        (ref.get("configMapRef") or {}).get("name") == CONFIGMAP
        for ref in conteneur.get("envFrom") or []
    )
    par_cle = any(
        e["name"] == cle
        and ((e.get("valueFrom") or {}).get("configMapKeyRef") or {}).get("name") == CONFIGMAP
        for e in conteneur.get("env") or []
    )
    return par_bloc or par_cle


def _cle_de_secret(conteneur: dict, cle: str) -> bool:
    """La clé arrive par envFrom secretRef ou par env valueFrom secretKeyRef."""
    par_bloc = any(
        (ref.get("secretRef") or {}).get("name") == SECRET
        for ref in conteneur.get("envFrom") or []
    )
    par_cle = any(
        e["name"] == cle
        and ((e.get("valueFrom") or {}).get("secretKeyRef") or {}).get("name") == SECRET
        for e in conteneur.get("env") or []
    )
    return par_bloc or par_cle


# ----------------------------------------------------------------------
# 1. Le ConfigMap porte les réglages et le fichier.
# ----------------------------------------------------------------------
def test_le_configmap_porte_app_mode(host):
    data = _configmap(host)
    assert data.get("APP_MODE") == "production", message(
        en=f"APP_MODE is {data.get('APP_MODE')!r} in {CONFIGMAP}, expected 'production'.",
        fr=f"APP_MODE vaut {data.get('APP_MODE')!r} dans {CONFIGMAP}, attendu 'production'.",
    )


def test_le_configmap_porte_log_level(host):
    data = _configmap(host)
    assert data.get("LOG_LEVEL") == "info", message(
        en=f"LOG_LEVEL is {data.get('LOG_LEVEL')!r} in {CONFIGMAP}, expected 'info'.",
        fr=f"LOG_LEVEL vaut {data.get('LOG_LEVEL')!r} dans {CONFIGMAP}, attendu 'info'.",
    )


def test_le_configmap_porte_le_fichier_config_yaml(host):
    data = _configmap(host)
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
def test_le_secret_porte_db_host(host):
    data = _secret(host)
    assert data.get("DB_HOST"), message(
        en=f"Secret {SECRET} has no DB_HOST key, or it is empty. Keys present: {sorted(data)}",
        fr=f"Le Secret {SECRET} n'a pas de clé DB_HOST, ou elle est vide. Clés présentes : {sorted(data)}",
    )
    hote = base64.b64decode(data["DB_HOST"]).decode()
    assert hote == "db.internal.svc", message(
        en=f"DB_HOST is {hote!r}, expected 'db.internal.svc'.",
        fr=f"DB_HOST vaut {hote!r}, attendu 'db.internal.svc'.",
    )


def test_le_secret_porte_db_password(host):
    data = _secret(host)
    assert data.get("DB_PASSWORD"), message(
        en=f"Secret {SECRET} has no DB_PASSWORD key, or it is empty. Keys present: {sorted(data)}",
        fr=f"Le Secret {SECRET} n'a pas de clé DB_PASSWORD, ou elle est vide. Clés présentes : {sorted(data)}",
    )


# ----------------------------------------------------------------------
# 3. Le Pod est déclaré comme demandé.
# ----------------------------------------------------------------------
def test_le_pod_tourne_avec_la_bonne_image(host):
    pod = _pod(host)
    assert pod["status"].get("phase") == "Running", message(
        en=f"Pod {POD} is in phase {pod['status'].get('phase')!r}. An envFrom or "
        "a volume naming a non-existent object leaves the Pod stuck in "
        "CreateContainerConfigError: its events say so.",
        fr=f"Le Pod {POD} est en phase {pod['status'].get('phase')!r}. Un envFrom ou "
        "un volume qui nomme un objet inexistant bloque le Pod en "
        "CreateContainerConfigError : ses events le disent.",
    )
    image = pod["spec"]["containers"][0].get("image")
    assert image == IMAGE, message(
        en=f"Pod {POD} runs image {image!r}, expected {IMAGE!r}.",
        fr=f"Le Pod {POD} utilise l'image {image!r}, attendu {IMAGE!r}.",
    )


def test_le_pod_recoit_les_cles_du_configmap_en_variables(host):
    conteneur = _conteneur(host)
    manquantes = [c for c in ("APP_MODE", "LOG_LEVEL") if not _cle_de_configmap(conteneur, c)]
    assert not manquantes, message(
        en=f"{manquantes} of ConfigMap {CONFIGMAP} are not injected as environment variables "
        "in the Pod: envFrom with configMapRef, or env key by key with configMapKeyRef.",
        fr=f"{manquantes} du ConfigMap {CONFIGMAP} ne sont pas injectées en variables "
        "d'environnement dans le Pod : envFrom avec configMapRef, ou env clé par clé avec configMapKeyRef.",
    )


def test_le_pod_recoit_db_host_du_secret(host):
    assert _cle_de_secret(_conteneur(host), "DB_HOST"), message(
        en=f"DB_HOST does not come from Secret {SECRET}: neither envFrom secretRef nor "
        "env valueFrom secretKeyRef references it.",
        fr=f"DB_HOST ne vient pas du Secret {SECRET} : ni envFrom secretRef, ni "
        "env valueFrom secretKeyRef ne le référencent.",
    )


def test_le_pod_recoit_db_password_du_secret(host):
    assert _cle_de_secret(_conteneur(host), "DB_PASSWORD"), message(
        en=f"DB_PASSWORD does not come from Secret {SECRET}: neither envFrom secretRef nor "
        "env valueFrom secretKeyRef references it.",
        fr=f"DB_PASSWORD ne vient pas du Secret {SECRET} : ni envFrom secretRef, ni "
        "env valueFrom secretKeyRef ne le référencent.",
    )


def test_aucun_mot_de_passe_n_est_ecrit_en_clair_dans_le_pod(host):
    conteneur = _conteneur(host)
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


def test_le_configmap_est_monte_sous_etc_app_config(host):
    pod = _pod(host)
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


# ----------------------------------------------------------------------
# 4. De l'intérieur du conteneur : les effets.
# ----------------------------------------------------------------------
def test_dans_le_conteneur_app_mode_vaut_production(host):
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- printenv APP_MODE")
    assert res.rc == 0 and res.stdout.strip() == "production", message(
        en=f"Inside the container, APP_MODE is {res.stdout.strip()!r}, expected "
        "'production'. The ConfigMap exists, but its keys do not reach the "
        "container: envFrom with configMapRef, or env key by key.",
        fr=f"Dans le conteneur, APP_MODE vaut {res.stdout.strip()!r}, attendu "
        "'production'. Le ConfigMap existe, mais ses clés n'arrivent pas au "
        "conteneur : envFrom avec configMapRef, ou env clé par clé.",
    )


def test_dans_le_conteneur_db_password_est_defini(host):
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- sh -c 'test -n \"$DB_PASSWORD\" && echo present'")
    assert "present" in res.stdout, message(
        en="Inside the container, DB_PASSWORD is empty or absent. The reference to "
        "the Secret is declared, but it may not be the right key.",
        fr="Dans le conteneur, DB_PASSWORD est vide ou absent. La référence au "
        "Secret est déclarée, mais ce n'est peut-être pas la bonne clé.",
    )


def test_dans_le_conteneur_le_fichier_config_yaml_contient_le_port(host):
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
