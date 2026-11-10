"""test_functional.py : k8s-epreuve-livrer-et-mettre-a-jour

Épreuve de fin du niveau 1 : six états, P01 à P06, lus sur le CLUSTER. Les
quatre premiers sont critiques (`exam_blocking_checks`) et aucune moyenne ne
les compense ; le seuil est de 70 sur 100.

Le cahier des charges ne nomme aucun objet Kubernetes : les tests retrouvent le
Deployment qui porte la vitrine (le seul du namespace dont un conteneur tourne
sur nginx), et ses Pods et ReplicaSets par son sélecteur et ses
ownerReferences, quels que soient les noms et labels choisis. Seul le Service
porte un nom imposé, vitrine, parce que l'adresse demandée l'impose.

Les images sont jugées sur leur digest : c'est lui que le cahier des charges
désigne, le tag n'étant qu'un nom.
"""

from __future__ import annotations

import json
import secrets

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "boutique"
V1 = "sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
V2 = "sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
CLIENT = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
MESSAGE = "Bienvenue"
MOT_DE_PASSE = "Boutique-2026"
EN_ERREUR = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull",
             "CreateContainerConfigError", "CreateContainerError", "InvalidImageName"}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str, absent: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _vitrine(host) -> dict:
    """Le Deployment qui porte la vitrine : le seul du namespace sur nginx."""
    deps = _json(host, f"-n {NS} get deployments", message(
        en=f"Cannot list the Deployments of the {NS} namespace.",
        fr=f"Impossible de lister les Deployments du namespace {NS}.",
    )).get("items") or []
    candidats = [
        d for d in deps
        if any("nginx" in c.get("image", "") for c in d["spec"]["template"]["spec"]["containers"])
    ]
    assert len(candidats) == 1, message(
        en=f"Expected exactly one Deployment running the storefront (nginx) in {NS}; "
           f"found {len(candidats)}.",
        fr=f"Attendu exactement un Deployment qui fait tourner la vitrine (nginx) dans {NS} ; "
           f"trouvé {len(candidats)}.",
    )
    return candidats[0]


def _selecteur(dep: dict) -> str:
    etiquettes = (dep["spec"].get("selector") or {}).get("matchLabels") or {}
    return ",".join(f"{k}={v}" for k, v in sorted(etiquettes.items()))


def _pods(host, dep: dict) -> list[dict]:
    return _json(host, f"-n {NS} get pods -l {_selecteur(dep)}", message(
        en="Cannot list the Pods of the storefront.",
        fr="Impossible de lister les Pods de la vitrine.",
    )).get("items") or []


def _conteneur(dep: dict) -> dict:
    return (dep["spec"]["template"]["spec"].get("containers") or [{}])[0]


def _vient_de(conteneur: dict, variable: str, cle_ref: str, cle_from: str) -> bool:
    for e in conteneur.get("env") or []:
        if e.get("name") == variable:
            return bool((e.get("valueFrom") or {}).get(cle_ref))
    return any(src.get(cle_from) for src in conteneur.get("envFrom") or [])


# ----------------------------------------------------------------------
# P01 (critique) : trois réplicas disponibles, tous sur la version 2.
# ----------------------------------------------------------------------
def test_p01_trois_replicas_sur_la_version_2(host):
    dep = _vitrine(host)
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    prets = [
        p for p in _pods(host, dep)
        if p["status"].get("phase") == "Running"
        and all(V2 in c["image"] for c in p["spec"]["containers"])
        and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
    ]
    assert dep["spec"].get("replicas", 1) == 3 and disponibles == 3 and len(prets) == 3, message(
        en=f"The storefront has {disponibles} available replica(s) and {len(prets)} ready Pod(s) "
           "on version 2; expected 3, all on the version 2 image referenced by digest.",
        fr=f"La vitrine a {disponibles} réplica(s) disponible(s) et {len(prets)} Pod(s) prêt(s) "
           "sur la version 2 ; attendu 3, tous sur l'image version 2 référencée par digest.",
    )


# ----------------------------------------------------------------------
# P02 (critique) : le Service vitrine répond, avec trois endpoints prêts.
# ----------------------------------------------------------------------
def test_p02_le_service_repond_avec_trois_endpoints(host):
    tranches = _json(host, f"-n {NS} get endpointslices -l kubernetes.io/service-name=vitrine",
                     message(en="Cannot read the EndpointSlices of the vitrine Service.",
                             fr="Impossible de lire les EndpointSlices du Service vitrine."))
    prets = sum(
        1 for t in tranches.get("items") or [] for ep in t.get("endpoints") or []
        if (ep.get("conditions") or {}).get("ready")
    )
    assert prets == 3, message(
        en=f"The vitrine Service has {prets} ready endpoint(s), expected 3: the address "
           f"http://vitrine.{NS} requires a Service named vitrine selecting the storefront Pods.",
        fr=f"Le Service vitrine compte {prets} endpoint(s) prêt(s), attendu 3 : l'adresse "
           f"http://vitrine.{NS} exige un Service nommé vitrine qui désigne les Pods de la vitrine.",
    )
    nom = f"client-{secrets.token_hex(3)}"
    res = host.run(
        f"{ADMIN} -n {NS} run {nom} --rm -i --restart=Never --quiet --image={CLIENT} "
        f"--timeout=120s -- wget -qO- -T 10 http://vitrine.{NS}"
    )
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en=f"The storefront does not answer at http://vitrine.{NS} from a Pod of the cluster.",
        fr=f"La vitrine ne répond pas sur http://vitrine.{NS} depuis un Pod du cluster.",
    )


# ----------------------------------------------------------------------
# P03 (critique) : la configuration vient d'un ConfigMap, le mot de passe
# d'un Secret, sans valeur en clair dans le Deployment.
# ----------------------------------------------------------------------
def test_p03_configuration_et_secret_sans_valeur_en_clair(host):
    dep = _vitrine(host)
    assert MOT_DE_PASSE not in json.dumps(dep), message(
        en="The password appears in clear in the storefront Deployment.",
        fr="Le mot de passe apparaît en clair dans le Deployment de la vitrine.",
    )
    conteneur = _conteneur(dep)
    assert _vient_de(conteneur, "MESSAGE_ACCUEIL", "configMapKeyRef", "configMapRef"), message(
        en="MESSAGE_ACCUEIL is not taken from a ConfigMap in the Deployment.",
        fr="MESSAGE_ACCUEIL ne vient pas d'un ConfigMap dans le Deployment.",
    )
    assert _vient_de(conteneur, "DB_PASSWORD", "secretKeyRef", "secretRef"), message(
        en="DB_PASSWORD is not taken from a Secret in the Deployment.",
        fr="DB_PASSWORD ne vient pas d'un Secret dans le Deployment.",
    )
    nom = dep["metadata"]["name"]
    vus = {
        v: host.run(f"{ADMIN} -n {NS} exec deploy/{nom} -- printenv {v}").stdout.strip()
        for v in ("MESSAGE_ACCUEIL", "DB_PASSWORD")
    }
    assert vus["MESSAGE_ACCUEIL"] == MESSAGE and vus["DB_PASSWORD"] == MOT_DE_PASSE, message(
        en="Inside a storefront Pod, MESSAGE_ACCUEIL or DB_PASSWORD does not hold the "
           "value the requirements give.",
        fr="Dans un Pod de la vitrine, MESSAGE_ACCUEIL ou DB_PASSWORD ne porte pas la valeur "
           "que donne le cahier des charges.",
    )


# ----------------------------------------------------------------------
# P04 (critique) : la révision précédente porte la version 1.
# ----------------------------------------------------------------------
def test_p04_la_revision_precedente_porte_la_version_1(host):
    dep = _vitrine(host)
    jeux = _json(host, f"-n {NS} get replicasets", message(
        en="Cannot list the ReplicaSets of the namespace.",
        fr="Impossible de lister les ReplicaSets du namespace.",
    )).get("items") or []
    siens = [
        rs for rs in jeux
        if any(o.get("uid") == dep["metadata"]["uid"] for o in rs["metadata"].get("ownerReferences") or [])
    ]

    def revision(rs: dict) -> int:
        return int((rs["metadata"].get("annotations") or {}).get("deployment.kubernetes.io/revision", "0"))

    siens.sort(key=revision, reverse=True)
    assert len(siens) >= 2, message(
        en=f"The storefront Deployment has {len(siens)} revision(s); expected at least two, "
           "version 1 then version 2.",
        fr=f"Le Deployment de la vitrine a {len(siens)} révision(s) ; attendu au moins deux, "
           "la version 1 puis la version 2.",
    )
    precedente = siens[1]
    images = [c["image"] for c in precedente["spec"]["template"]["spec"]["containers"]]
    assert any(V1 in i for i in images), message(
        en=f"The previous revision ({revision(precedente)}) runs {images}, not version 1: "
           "a rollback would not bring version 1 back.",
        fr=f"La révision précédente ({revision(precedente)}) tourne sur {images}, pas sur la "
           "version 1 : un retour arrière ne ramènerait pas la version 1.",
    )


# ----------------------------------------------------------------------
# P05 : une stratégie qui interdit l'indisponibilité.
# ----------------------------------------------------------------------
def test_p05_strategie_sans_indisponibilite(host):
    strategie = _vitrine(host)["spec"].get("strategy") or {}
    max_indispo = str((strategie.get("rollingUpdate") or {}).get("maxUnavailable", "25%"))
    assert strategie.get("type") == "RollingUpdate" and max_indispo in ("0", "0%"), message(
        en=f"The update strategy is {strategie.get('type')} with maxUnavailable {max_indispo}: "
           "an update without downtime needs RollingUpdate with maxUnavailable 0.",
        fr=f"La stratégie de mise à jour est {strategie.get('type')} avec maxUnavailable "
           f"{max_indispo} : une mise à jour sans coupure demande RollingUpdate avec maxUnavailable 0.",
    )


# ----------------------------------------------------------------------
# P06 : la vitrine tourne, et aucun Pod du namespace n'est en erreur.
# ----------------------------------------------------------------------
def test_p06_aucun_pod_en_erreur(host):
    pods = _json(host, f"-n {NS} get pods", message(
        en=f"Cannot list the Pods of the {NS} namespace.",
        fr=f"Impossible de lister les Pods du namespace {NS}.",
    )).get("items") or []
    en_marche = [p for p in pods if p["status"].get("phase") == "Running"]
    # Garde-fou : un namespace vide n'a aucun Pod en erreur, et ce test
    # serait vrai avant tout travail.
    assert len(en_marche) >= 3, message(
        en=f"{len(en_marche)} Pod(s) running in {NS}: the storefront is not running.",
        fr=f"{len(en_marche)} Pod(s) en marche dans {NS} : la vitrine ne tourne pas.",
    )
    fautifs = sorted(
        f"{p['metadata']['name']} ({s['state']['waiting'].get('reason')})"
        for p in pods
        for s in (p["status"].get("containerStatuses") or []) + (p["status"].get("initContainerStatuses") or [])
        if (s.get("state") or {}).get("waiting", {}).get("reason") in EN_ERREUR
    )
    assert not fautifs, message(
        en=f"Pods in error in {NS}: {', '.join(fautifs)}.",
        fr=f"Pods en erreur dans {NS} : {', '.join(fautifs)}.",
    )
