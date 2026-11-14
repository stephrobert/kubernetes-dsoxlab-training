"""test_functional.py : k8s-challenge-contenir-une-attaque

Le challenge du module Modèle de menaces et cadres. Ces tests lisent l'état du
CLUSTER et du nœud, jamais les commandes tapées. Un test vérifie un seul état,
dans l'ordre de la fiche.

Le constat se prouve par l'UID du DaemonSet, relevé par le setup dans un
fichier que seul root lit : un export de l'objet vivant le porte, un fichier
écrit de mémoire après la suppression ne peut pas le porter.

Le retour de l'accès se juge APRÈS un cycle complet du mécanisme (il recrée
l'accès toutes les 20 secondes) : un compte supprimé à la main sans retirer
ce qui le recrée revient aussitôt, et un test qui regarderait tout de suite
le croirait parti.

Le refus hors quota se prouve par des sondes modestes (300m et 256Mi chacune),
créées une à une jusqu'au refus : aucun maximum de LimitRange raisonnable ne
les refuse à lui seul, c'est donc bien le plafond du namespace qui doit dire
non. Les sondes sont supprimées après usage, en attendant leur disparition.

Les états 3 et 7 ne se jugent qu'une fois le travail engagé (persistance
retirée, namespace plafonné) : avant, l'application tourne et répond, et un
test vrai avant le travail ne mesure rien.

Les sept tests échouent sur l'état que pose le setup.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "reservations"
PERSISTANCE = "collecteur-noeuds"
COMPTE = "maintenance"
POD_ORIGINE = "diagnostic-reseau"
APPLICATION = "reservations"
REPLICAS_APPLICATION = 3
NS_CHARGE = "calcul-lots"
CHARGE = "moulinette"
REPLICAS_CHARGE = 2
CONSTAT = "/root/constat-attaque.yaml"
REFERENCE = "/var/lib/dsoxlab-labs/k8s-challenge-contenir-une-attaque.uid"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
SUJET = f"system:serviceaccount:{NS}:{COMPTE}"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

#: Le plafond demandé par l'énoncé : chaque valeur au plus celle-ci.
PLAFOND = {"requests.cpu": "800m", "requests.memory": "768Mi"}
#: Un cycle du mécanisme (20 s), plus le temps qu'un appel aboutisse.
CYCLE = 45

_SUFFIXES = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40,
             "k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12, "m": 10**-3}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _quantite(valeur: str | int | float | None) -> float:
    """Une quantité Kubernetes en unité de base (cœurs ou octets)."""
    texte = str(valeur or "0").strip()
    for suffixe in sorted(_SUFFIXES, key=len, reverse=True):
        if texte.endswith(suffixe):
            return float(texte[: -len(suffixe)]) * _SUFFIXES[suffixe]
    return float(texte)


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _vivant(objet: dict | None) -> bool:
    return objet is not None and not objet["metadata"].get("deletionTimestamp")


def _persistance_presente(host) -> bool:
    if _vivant(_json(host, f"-n {NS} get daemonset {PERSISTANCE}")):
        return True
    pods = (_json(host, f"-n {NS} get pods -l app={PERSISTANCE}") or {}).get("items") or []
    return any(p["status"].get("phase") == "Running" for p in pods)


def _acces_present(host) -> list[str]:
    """Ce qui reste de l'accès de l'attaquant : compte, jeton, liaisons de cluster, droit effectif."""
    restes = []
    if _vivant(_json(host, f"-n {NS} get serviceaccount {COMPTE}")):
        restes.append(message(en=f"the account {COMPTE}", fr=f"le compte {COMPTE}"))
    if _vivant(_json(host, f"-n {NS} get secret {COMPTE}-jeton")):
        restes.append(message(en=f"the token Secret {COMPTE}-jeton", fr=f"le Secret de jeton {COMPTE}-jeton"))
    liaisons = (_json(host, "get clusterrolebindings") or {}).get("items") or []
    noms = sorted(b["metadata"]["name"] for b in liaisons
                  if any(s.get("kind") == "ServiceAccount" and s.get("namespace") == NS
                         for s in b.get("subjects") or []))
    if noms:
        restes.append(message(en=f"the ClusterRoleBindings {noms}", fr=f"les ClusterRoleBindings {noms}"))
    if host.run(f"{ADMIN} auth can-i list secrets --all-namespaces --as {SUJET}").stdout.strip() == "yes":
        restes.append(message(en="reading the Secrets of the cluster", fr="la lecture des Secrets du cluster"))
    return restes


def _supprimer(host, pod: str) -> None:
    host.run(f"{ADMIN} -n {NS_CHARGE} delete pod {pod} --ignore-not-found --wait=true --timeout=90s")


def _sonde(host, nom: str, ressources: dict | None):
    conteneur = {"name": "sonde", "image": BUSYBOX, "command": ["sh", "-c", "sleep 30"]}
    if ressources:
        conteneur["resources"] = ressources
    surcharge = json.dumps({"spec": {"containers": [conteneur]}})
    _supprimer(host, nom)
    return host.run(f"{ADMIN} -n {NS_CHARGE} run {nom} --image={BUSYBOX} --restart=Never --overrides='{surcharge}'")


def _quota_plafonne(host) -> list[str]:
    """Les plafonds demandés qui manquent, le plus strict de chaque ressource retenu."""
    quotas = (_json(host, f"-n {NS_CHARGE} get resourcequotas") or {}).get("items") or []
    retenu: dict[str, float] = {}
    for q in quotas:
        for brute, valeur in ((q.get("spec") or {}).get("hard") or {}).items():
            cle = {"cpu": "requests.cpu", "memory": "requests.memory"}.get(brute, brute)
            retenu[cle] = min(retenu.get(cle, float("inf")), _quantite(valeur))
    return [f"{cle} <= {plafond}" for cle, plafond in PLAFOND.items()
            if cle not in retenu or retenu[cle] > _quantite(plafond)]


# ----------------------------------------------------------------------
# 1. L'objet de persistance est consigné, depuis l'objet vivant.
# ----------------------------------------------------------------------
def test_le_constat_nomme_l_objet_de_persistance(host):
    reference = host.run(f"sudo cat {REFERENCE}").stdout.strip()
    assert reference, message(
        en=f"The reference {REFERENCE} that the setup writes is missing: replay `dsoxlab run`.",
        fr=f"La référence {REFERENCE} que pose le setup est absente : rejouez `dsoxlab run`.",
    )
    res = host.run(f"sudo cat {CONSTAT}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No record in {CONSTAT}.",
        fr=f"Aucun constat dans {CONSTAT}.",
    )
    assert reference in res.stdout, message(
        en=f"{CONSTAT} does not carry the persistence object as the cluster knew it before its deletion.",
        fr=f"{CONSTAT} ne porte pas l'objet de persistance tel que le cluster le connaissait avant sa suppression.",
    )


# ----------------------------------------------------------------------
# 2. La persistance est supprimée et l'accès ne revient pas.
# ----------------------------------------------------------------------
def test_la_persistance_est_supprimee_et_l_acces_ne_revient_pas(host):
    assert not _persistance_presente(host), message(
        en="What recreates the attacker's access still runs.",
        fr="Ce qui recrée l'accès de l'attaquant tourne toujours.",
    )
    assert not _vivant(_json(host, f"-n {NS} get pod {POD_ORIGINE}")), message(
        en=f"The original Pod {POD_ORIGINE} still runs.",
        fr=f"Le Pod d'origine {POD_ORIGINE} tourne toujours.",
    )
    restes = _acces_present(host)
    assert not restes, message(
        en=f"The attacker's access remains: {restes}.",
        fr=f"L'accès de l'attaquant reste : {restes}.",
    )
    time.sleep(CYCLE)
    revenu = _acces_present(host)
    assert not revenu, message(
        en=f"{CYCLE} seconds later, the access came back: {revenu}.",
        fr=f"{CYCLE} secondes plus tard, l'accès est revenu : {revenu}.",
    )


# ----------------------------------------------------------------------
# 3. L'application légitime a tous ses réplicas.
# ----------------------------------------------------------------------
def test_l_application_legitime_a_tous_ses_replicas(host):
    assert not _persistance_presente(host), message(
        en="The persistence still runs: the legitimate application is judged once it is removed.",
        fr="La persistance tourne toujours : l'application légitime se juge une fois celle-ci retirée.",
    )
    dep = _json(host, f"-n {NS} get deployment {APPLICATION}")
    assert dep is not None, message(
        en=f"The Deployment {APPLICATION} is gone: it is the legitimate application.",
        fr=f"Le Deployment {APPLICATION} a disparu : c'est l'application légitime.",
    )
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert dep["spec"].get("replicas") == REPLICAS_APPLICATION and disponibles == REPLICAS_APPLICATION, message(
        en=f"{APPLICATION} has {disponibles} available replica(s) out of {dep['spec'].get('replicas')}, "
        f"{REPLICAS_APPLICATION} expected.",
        fr=f"{APPLICATION} a {disponibles} réplica(s) disponible(s) sur {dep['spec'].get('replicas')}, "
        f"{REPLICAS_APPLICATION} attendus.",
    )


# ----------------------------------------------------------------------
# 4. Le namespace de la charge porte un ResourceQuota.
# ----------------------------------------------------------------------
def test_le_namespace_de_la_charge_porte_un_resourcequota(host):
    manquants = _quota_plafonne(host)
    assert not manquants, message(
        en=f"The quota of {NS_CHARGE} does not cap what is asked: {manquants} expected.",
        fr=f"Le quota de {NS_CHARGE} ne plafonne pas ce qui est demandé : {manquants} attendus.",
    )


# ----------------------------------------------------------------------
# 5. Un LimitRange donne des valeurs par défaut.
# ----------------------------------------------------------------------
def test_un_limitrange_donne_des_valeurs_par_defaut(host):
    res = _sonde(host, "sonde-sans-ressources", None)
    assert res.rc == 0, message(
        en=f"A Pod declaring no resources was refused in {NS_CHARGE}: {res.stderr.strip()[:300]}",
        fr=f"Un Pod qui ne déclare aucune ressource a été refusé dans {NS_CHARGE} : {res.stderr.strip()[:300]}",
    )
    pod = _json(host, f"-n {NS_CHARGE} get pod sonde-sans-ressources")
    _supprimer(host, "sonde-sans-ressources")
    ressources = (pod or {}).get("spec", {}).get("containers", [{}])[0].get("resources") or {}
    complet = all(_quantite((ressources.get(cle) or {}).get(res)) > 0
                  for cle in ("requests", "limits") for res in ("cpu", "memory"))
    assert complet, message(
        en=f"A container declaring nothing comes back with {ressources or 'no resources'}: requests and "
        "limits, CPU and memory, expected by default.",
        fr=f"Un conteneur qui ne déclare rien repart avec {ressources or 'aucune ressource'} : requests et "
        "limits, processeur et mémoire, attendus par défaut.",
    )


# ----------------------------------------------------------------------
# 6. Une création au-delà du quota est refusée.
# ----------------------------------------------------------------------
def test_une_creation_hors_quota_est_refusee(host):
    ressources = {"requests": {"cpu": "300m", "memory": "256Mi"}, "limits": {"cpu": "300m", "memory": "256Mi"}}
    creees, refus = [], ""
    try:
        for rang in range(1, 5):
            nom = f"sonde-quota-{rang}"
            res = _sonde(host, nom, ressources)
            if res.rc != 0:
                refus = res.stderr.strip()
                break
            creees.append(nom)
    finally:
        for nom in creees:
            _supprimer(host, nom)
    assert refus, message(
        en=f"{NS_CHARGE} accepted {len(creees)} Pods of 300m and 256Mi each, beyond the ceiling asked.",
        fr=f"{NS_CHARGE} a accepté {len(creees)} Pods de 300m et 256Mi chacun, au-delà du plafond demandé.",
    )
    assert "exceeded quota" in refus.lower(), message(
        en=f"A Pod was refused, but not by the quota of the namespace: {refus[:300]}",
        fr=f"Un Pod a été refusé, mais pas par le quota du namespace : {refus[:300]}",
    )


# ----------------------------------------------------------------------
# 7. Pendant la charge, une application d'un autre namespace répond.
# ----------------------------------------------------------------------
def test_une_application_d_un_autre_namespace_repond_pendant_la_charge(host):
    assert not _quota_plafonne(host), message(
        en=f"{NS_CHARGE} is not capped yet: the other application is judged while the capped workload runs.",
        fr=f"{NS_CHARGE} n'est pas encore plafonné : l'autre application se juge pendant que la charge "
        "plafonnée tourne.",
    )
    dep = _json(host, f"-n {NS_CHARGE} get deployment {CHARGE}") or {}
    prets = (dep.get("status") or {}).get("readyReplicas") or 0
    assert (dep.get("spec") or {}).get("replicas", 0) >= REPLICAS_CHARGE and prets >= REPLICAS_CHARGE, message(
        en=f"The workload {CHARGE} no longer runs its {REPLICAS_CHARGE} replicas ({prets} ready): it is "
        "contained, not removed.",
        fr=f"La charge {CHARGE} ne tourne plus ses {REPLICAS_CHARGE} réplicas ({prets} prêts) : elle se "
        "contient, elle ne se retire pas.",
    )
    svc = _json(host, f"-n {NS} get service {APPLICATION}") or {}
    ip = (svc.get("spec") or {}).get("clusterIP")
    codes = [host.run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 http://{ip}/").stdout.strip()
             for _ in range(5)] if ip else []
    assert codes and all(c == "200" for c in codes), message(
        en=f"While {CHARGE} runs, {APPLICATION} answers {codes or 'nothing'} instead of five times 200.",
        fr=f"Pendant que {CHARGE} tourne, {APPLICATION} répond {codes or 'rien'} au lieu de cinq fois 200.",
    )
