"""test_functional.py : k8s-challenge-relier-config-et-service

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Un test vérifie
un seul état demandé par l'énoncé.

La configuration et le mot de passe sont jugés sur deux faits qui concordent :
la spécification du Deployment les fait venir d'un ConfigMap et d'un Secret
(une valeur écrite en dur dans `env` ne compte pas), et la valeur est bien
celle que le conteneur voit, lue DANS un Pod par `printenv`. Le mot de passe ne
doit apparaître nulle part dans le Deployment tel que l'API le rend.

La mise à jour est jugée sur l'image des Pods qui tournent, et sur la présence
d'un ReplicaSet de l'ancienne image gardé à zéro réplica : c'est ce qui permet
le retour arrière.
"""

from __future__ import annotations

import json
import secrets

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "magasin"
V1 = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
V2 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
CLIENT = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
MESSAGE = "Bienvenue"
MOT_DE_PASSE = "Boutique-2026"
OBJETS = (("deployment", "vitrine"), ("service", "vitrine"),
          ("configmap", "vitrine-config"), ("secret", "vitrine-secret"))


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str, absent: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _deployment(host) -> dict:
    return _json(host, f"-n {NS} get deployment vitrine", message(
        en=f"No Deployment vitrine in the {NS} namespace.",
        fr=f"Aucun Deployment vitrine dans le namespace {NS}.",
    ))


def _selecteur(dep: dict) -> str:
    """Le sélecteur du Deployment, pour retrouver ses Pods et ses ReplicaSets
    quels que soient les labels que l'apprenant a choisis."""
    etiquettes = (dep["spec"].get("selector") or {}).get("matchLabels") or {}
    return ",".join(f"{k}={v}" for k, v in sorted(etiquettes.items()))


def _conteneur(dep: dict) -> dict:
    return (dep["spec"]["template"]["spec"].get("containers") or [{}])[0]


def _printenv(host, variable: str) -> str:
    res = host.run(f"{ADMIN} -n {NS} exec deploy/vitrine -- printenv {variable}")
    return res.stdout.strip() if res.rc == 0 else ""


def _vient_de(conteneur: dict, variable: str, cle_ref: str, cle_from: str) -> bool:
    """La variable vient-elle d'un ConfigMap (ou d'un Secret), par env ou envFrom ?"""
    for e in conteneur.get("env") or []:
        if e.get("name") == variable:
            return bool((e.get("valueFrom") or {}).get(cle_ref))
    return any(src.get(cle_from) for src in conteneur.get("envFrom") or [])


# ----------------------------------------------------------------------
# 1. Tout dans magasin, rien dans default.
# ----------------------------------------------------------------------
def test_les_objets_sont_dans_magasin_et_aucun_dans_default(host):
    absents = [f"{k}/{n}" for k, n in OBJETS
               if host.run(f"{ADMIN} -n {NS} get {k} {n}").rc != 0]
    assert not absents, message(
        en=f"Missing from the {NS} namespace: {', '.join(absents)}.",
        fr=f"Absent du namespace {NS} : {', '.join(absents)}.",
    )
    egares = [f"{k}/{n}" for k, n in OBJETS
              if host.run(f"{ADMIN} -n default get {k} {n}").rc == 0]
    assert not egares, message(
        en=f"Found in the default namespace: {', '.join(egares)}. Everything belongs in {NS}.",
        fr=f"Trouvé dans le namespace default : {', '.join(egares)}. Tout doit être dans {NS}.",
    )


# ----------------------------------------------------------------------
# 2. Trois réplicas disponibles.
# ----------------------------------------------------------------------
def test_la_vitrine_a_trois_replicas_disponibles(host):
    dep = _deployment(host)
    demandes = dep["spec"].get("replicas", 1)
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert demandes == 3 and disponibles == 3, message(
        en=f"vitrine has {disponibles} available replica(s) for {demandes} requested; expected 3 out of 3.",
        fr=f"vitrine a {disponibles} réplica(s) disponible(s) pour {demandes} demandé(s) ; attendu 3 sur 3.",
    )


# ----------------------------------------------------------------------
# 3. La configuration vient du ConfigMap.
# ----------------------------------------------------------------------
def test_la_configuration_arrive_depuis_le_configmap(host):
    conteneur = _conteneur(_deployment(host))
    assert _vient_de(conteneur, "MESSAGE_ACCUEIL", "configMapKeyRef", "configMapRef"), message(
        en="MESSAGE_ACCUEIL is not taken from a ConfigMap in the Deployment: "
           "a value written directly in env does not count.",
        fr="MESSAGE_ACCUEIL ne vient pas d'un ConfigMap dans le Deployment : "
           "une valeur écrite directement dans env ne compte pas.",
    )
    vue = _printenv(host, "MESSAGE_ACCUEIL")
    assert vue == MESSAGE, message(
        en=f"Inside a vitrine Pod, MESSAGE_ACCUEIL is {vue!r}; expected {MESSAGE!r}.",
        fr=f"Dans un Pod de vitrine, MESSAGE_ACCUEIL vaut {vue!r} ; attendu {MESSAGE!r}.",
    )


# ----------------------------------------------------------------------
# 4. Le mot de passe vient du Secret, sans être en clair.
# ----------------------------------------------------------------------
def test_le_mot_de_passe_arrive_depuis_le_secret_sans_etre_en_clair(host):
    res = host.run(f"{ADMIN} -n {NS} get deployment vitrine -o json")
    assert res.rc == 0, message(
        en=f"No Deployment vitrine in the {NS} namespace.",
        fr=f"Aucun Deployment vitrine dans le namespace {NS}.",
    )
    assert MOT_DE_PASSE not in res.stdout, message(
        en="The password appears in clear in the vitrine Deployment: it must come from the Secret.",
        fr="Le mot de passe apparaît en clair dans le Deployment vitrine : il doit venir du Secret.",
    )
    conteneur = _conteneur(json.loads(res.stdout))
    assert _vient_de(conteneur, "DB_PASSWORD", "secretKeyRef", "secretRef"), message(
        en="DB_PASSWORD is not taken from a Secret in the Deployment.",
        fr="DB_PASSWORD ne vient pas d'un Secret dans le Deployment.",
    )
    vue = _printenv(host, "DB_PASSWORD")
    assert vue == MOT_DE_PASSE, message(
        en="Inside a vitrine Pod, DB_PASSWORD does not hold the expected password.",
        fr="Dans un Pod de vitrine, DB_PASSWORD ne porte pas le mot de passe attendu.",
    )


# ----------------------------------------------------------------------
# 5. Le Service compte trois endpoints prêts et répond.
# ----------------------------------------------------------------------
def test_le_service_compte_trois_endpoints_et_repond(host):
    tranches = _json(host, f"-n {NS} get endpointslices -l kubernetes.io/service-name=vitrine",
                     message(en="Cannot read the EndpointSlices of vitrine.",
                             fr="Impossible de lire les EndpointSlices de vitrine."))
    prets = sum(
        1 for t in tranches.get("items") or [] for ep in t.get("endpoints") or []
        if (ep.get("conditions") or {}).get("ready")
    )
    assert prets == 3, message(
        en=f"The vitrine Service has {prets} ready endpoint(s), expected 3: check that it exists "
           "and that its selector matches the labels of the vitrine Pods.",
        fr=f"Le Service vitrine compte {prets} endpoint(s) prêt(s), attendu 3 : vérifiez qu'il existe "
           "et que son sélecteur correspond aux labels des Pods de vitrine.",
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
# 6. La mise à jour garde l'ancien ReplicaSet à zéro.
# ----------------------------------------------------------------------
def test_la_mise_a_jour_garde_l_ancien_replicaset_a_zero(host):
    dep = _deployment(host)
    pods = _json(host, f"-n {NS} get pods -l {_selecteur(dep)}", message(
        en="Cannot list the Pods of vitrine.",
        fr="Impossible de lister les Pods de vitrine.",
    )).get("items") or []
    en_marche = [
        p for p in pods
        if p["status"].get("phase") == "Running"
        and all(c["image"] == V2 for c in p["spec"]["containers"])
        and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
    ]
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert len(en_marche) == 3 and disponibles == 3 and _conteneur(dep).get("image") == V2, message(
        en=f"{len(en_marche)} vitrine Pod(s) run {V2}, with {disponibles} available; "
           "expected 3 on the new image.",
        fr=f"{len(en_marche)} Pod(s) de vitrine tournent sur {V2}, {disponibles} disponible(s) ; "
           "attendu 3 sur la nouvelle image.",
    )
    jeux = _json(host, f"-n {NS} get replicasets -l {_selecteur(dep)}", message(
        en="Cannot list the ReplicaSets of vitrine.",
        fr="Impossible de lister les ReplicaSets de vitrine.",
    )).get("items") or []
    anciens = [
        rs for rs in jeux
        if any(c["image"] == V1 for c in rs["spec"]["template"]["spec"]["containers"])
        and rs["spec"].get("replicas", 1) == 0
    ]
    assert anciens, message(
        en=f"No ReplicaSet of vitrine on {V1} kept at zero replicas: the update must go "
           "through the Deployment, which keeps the previous ReplicaSet for a rollback.",
        fr=f"Aucun ReplicaSet de vitrine sur {V1} gardé à zéro réplica : la mise à jour doit passer "
           "par le Deployment, qui garde l'ancien ReplicaSet pour un retour arrière.",
    )
