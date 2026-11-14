"""test_functional.py : k8s-contenir-un-deni-de-service

Lab guidé de la leçon KUBERN-S-06 (déni de service). Ces tests lisent l'état
du CLUSTER, jamais les commandes tapées. Un test vérifie un seul état, dans
l'ordre de la fiche.

Trois preuves sont ACTIVES, reprises de cka-resourcequota-limitrange : plutôt
que de relire les objets posés, un test crée un Pod sonde et constate ce que le
cluster en fait. Un quota dont `hard` ne porte pas sur les bonnes ressources est
valide et ne plafonne rien ; un LimitRange du mauvais type ne complète rien.
Les sondes sont supprimées après usage, en attendant leur disparition.

Le dernier test ne juge l'application d'annuaire que pendant une charge
BORNÉE : avant le travail, elle répond aussi, et un test vrai avant le travail
ne mesure rien.

Les cinq tests échouent sur l'état que pose le setup : bac-a-sable n'a ni
quota ni LimitRange, et les Pods de gourmand tournent sans requests ni limits.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "bac-a-sable"
CHARGE = "gourmand"
REPLICAS_CHARGE = 2
AUTRE_NS = "annuaire"
APPLICATION = "annuaire"
REPLICAS_APPLICATION = 2
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

#: Le plafond demandé par l'énoncé : chaque valeur au plus celle-ci.
PLAFOND = {"requests.cpu": "1", "requests.memory": "1Gi", "limits.cpu": "2", "limits.memory": "2Gi"}
#: Les valeurs par défaut demandées par l'énoncé, exactement.
DEFAUT_REQUESTS = {"cpu": "100m", "memory": "128Mi"}
DEFAUT_LIMITS = {"cpu": "300m", "memory": "256Mi"}

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


def _supprimer(host, pod: str) -> None:
    """Supprime une sonde et ATTEND sa disparition : une sonde encore en cours
    de suppression bloque la suivante, et compte encore dans le quota."""
    host.run(f"{ADMIN} -n {NS} delete pod {pod} --ignore-not-found --wait=true --timeout=90s")


def _sonde(host, nom: str, ressources: dict | None):
    """Tente de créer un Pod sonde, et rend le résultat de la commande."""
    conteneur = {"name": "sonde", "image": BUSYBOX, "command": ["sh", "-c", "sleep 30"]}
    if ressources:
        conteneur["resources"] = ressources
    surcharge = json.dumps({"spec": {"containers": [conteneur]}})
    _supprimer(host, nom)
    return host.run(f"{ADMIN} -n {NS} run {nom} --image={BUSYBOX} --restart=Never --overrides='{surcharge}'")


_DEJA_LUS: dict[str, list[dict]] = {}


def _pods_de_la_charge(host) -> list[dict]:
    """Les Pods prêts du Deployment gourmand, créés par son ReplicaSet. Laisse
    au Deployment le temps de remplacer des Pods qu'on vient de recréer, puis
    garde le résultat pour la durée du check."""
    if CHARGE in _DEJA_LUS:
        return _DEJA_LUS[CHARGE]
    prets: list[dict] = []
    for _ in range(18):
        items = (_json(host, f"-n {NS} get pods -l app={CHARGE}") or {}).get("items") or []
        vivants = [p for p in items if not p["metadata"].get("deletionTimestamp")
                   and any(o.get("kind") == "ReplicaSet" for o in p["metadata"].get("ownerReferences") or [])]
        prets = [p for p in vivants if p["status"].get("phase") == "Running"
                 and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])]
        if not vivants or (prets and len(prets) == len(vivants)):
            break
        time.sleep(5)
    _DEJA_LUS[CHARGE] = prets
    return prets


def _non_bornes(pods: list[dict]) -> list[str]:
    """Les Pods dont un conteneur n'a pas requests ET limits, en processeur et en mémoire."""
    fautifs = []
    for p in pods:
        for c in p["spec"]["containers"]:
            r = c.get("resources") or {}
            if not all((r.get(cle) or {}).get(res) for cle in ("requests", "limits") for res in ("cpu", "memory")):
                fautifs.append(p["metadata"]["name"])
                break
    return fautifs


# ----------------------------------------------------------------------
# 1. Le namespace de test porte un ResourceQuota au plafond demandé.
# ----------------------------------------------------------------------
def test_le_namespace_porte_un_resourcequota(host):
    quotas = (_json(host, f"-n {NS} get resourcequotas") or {}).get("items") or []
    assert quotas, message(
        en=f"No ResourceQuota in {NS}: one workload of this namespace can take the whole node.",
        fr=f"Aucun ResourceQuota dans {NS} : une seule charge de ce namespace peut prendre tout le nœud.",
    )
    # Le plus strict de chaque ressource, tous quotas confondus : c'est lui qui s'applique.
    retenu: dict[str, float] = {}
    for q in quotas:
        for brute, valeur in ((q.get("spec") or {}).get("hard") or {}).items():
            # `cpu` et `memory` sont les formes courtes de requests.cpu et requests.memory.
            cle = {"cpu": "requests.cpu", "memory": "requests.memory"}.get(brute, brute)
            retenu[cle] = min(retenu.get(cle, float("inf")), _quantite(valeur))
    ecarts = [f"{cle} <= {plafond}" for cle, plafond in PLAFOND.items()
              if cle not in retenu or retenu[cle] > _quantite(plafond)]
    assert not ecarts, message(
        en=f"The quota of {NS} does not cap what is asked: {ecarts} expected. A quota caps only the "
        "resources it names: requests and limits are two distinct keys.",
        fr=f"Le quota de {NS} ne plafonne pas ce qui est demandé : {ecarts} attendus. Un quota ne plafonne que "
        "les ressources qu'il nomme : requests et limits sont deux clés distinctes.",
    )


# ----------------------------------------------------------------------
# 2. Un conteneur sans limites reçoit les valeurs par défaut.
# ----------------------------------------------------------------------
def test_un_conteneur_sans_limites_recoit_les_valeurs_par_defaut(host):
    res = _sonde(host, "sonde-sans-limites", None)
    assert res.rc == 0, message(
        en=f"A Pod declaring no resources was refused in {NS}: {res.stderr.strip()[:300]}. That is a quota "
        "set on its own: as soon as it covers requests, a Pod that declares none is invalid, unless "
        "something completes it on arrival.",
        fr=f"Un Pod qui ne déclare aucune ressource a été refusé dans {NS} : {res.stderr.strip()[:300]}. C'est "
        "un quota posé seul : dès qu'il porte sur les requests, un Pod qui n'en déclare pas est invalide, "
        "sauf si quelque chose le complète à son arrivée.",
    )
    pod = _json(host, f"-n {NS} get pod sonde-sans-limites")
    _supprimer(host, "sonde-sans-limites")
    ressources = (pod or {}).get("spec", {}).get("containers", [{}])[0].get("resources") or {}
    requests, limits = ressources.get("requests") or {}, ressources.get("limits") or {}
    attendu = all(_quantite(requests.get(r)) == _quantite(v) for r, v in DEFAUT_REQUESTS.items()) and \
        all(_quantite(limits.get(r)) == _quantite(v) for r, v in DEFAUT_LIMITS.items())
    assert attendu, message(
        en=f"The Pod was accepted and comes back with {ressources or 'no resources'}. Expected requests "
        f"{DEFAUT_REQUESTS} and limits {DEFAUT_LIMITS}, given by default to every container of {NS} that "
        "declares nothing.",
        fr=f"Le Pod a été accepté et repart avec {ressources or 'aucune ressource'}. Attendu des requests "
        f"{DEFAUT_REQUESTS} et des limits {DEFAUT_LIMITS}, données par défaut à tout conteneur de {NS} qui ne "
        "déclare rien.",
    )


# ----------------------------------------------------------------------
# 3. Une création au-delà du quota est refusée.
# ----------------------------------------------------------------------
def test_une_creation_hors_quota_est_refusee(host):
    # 900m et 900Mi demandés : à eux seuls sous le plafond, au-delà dès que
    # gourmand tourne avec ses valeurs par défaut.
    ressources = {"requests": {"cpu": "900m", "memory": "900Mi"}, "limits": {"cpu": "1", "memory": "1Gi"}}
    res = _sonde(host, "sonde-hors-quota", ressources)
    if res.rc == 0:
        _supprimer(host, "sonde-hors-quota")
    assert res.rc != 0, message(
        en=f"{NS} ACCEPTED a Pod asking 900m of CPU and 900Mi of memory on top of gourmand. Without a "
        "ceiling, the API accepts and the node pays: nobody refused it.",
        fr=f"{NS} a ACCEPTÉ un Pod demandant 900m de processeur et 900Mi de mémoire en plus de gourmand. Sans "
        "plafond, l'API accepte et c'est le nœud qui paie : personne ne l'a refusé.",
    )
    assert "exceeded quota" in res.stderr.lower(), message(
        en="The Pod was refused, but not by the quota of the namespace. A ceiling reached answers "
        "\"exceeded quota: <name>, requested: ..., used: ..., limited: ...\"; a LimitRange maximum answers "
        f"\"must be less than or equal to\". The message was: {res.stderr.strip()[:300]}",
        fr="Le Pod a été refusé, mais pas par le quota du namespace. Un plafond atteint répond « exceeded "
        "quota: <nom>, requested: ..., used: ..., limited: ... » ; un maximum de LimitRange répond « must be "
        f"less than or equal to ». Le message était : {res.stderr.strip()[:300]}",
    )


# ----------------------------------------------------------------------
# 4. La charge abusive est bornée.
# ----------------------------------------------------------------------
def test_la_charge_abusive_est_bornee(host):
    pods = _pods_de_la_charge(host)
    assert len(pods) >= REPLICAS_CHARGE, message(
        en=f"{len(pods)} running Pod(s) of {CHARGE} instead of {REPLICAS_CHARGE}. The workload is bounded, "
        "not removed or scaled down: the lesson is to contain it while it runs.",
        fr=f"{len(pods)} Pod(s) de {CHARGE} en marche au lieu de {REPLICAS_CHARGE}. La charge se borne, elle ne "
        "se retire pas et ne se réduit pas : la leçon est de la contenir pendant qu'elle tourne.",
    )
    fautifs = _non_bornes(pods)
    assert not fautifs, message(
        en=f"These running Pods of {CHARGE} still have no requests or no limits: {fautifs}. Default values "
        "apply only when a Pod is created: Pods started before them keep running without.",
        fr=f"Ces Pods en marche de {CHARGE} n'ont toujours pas de requests ou pas de limits : {fautifs}. Les "
        "valeurs par défaut ne s'appliquent qu'à la création d'un Pod : ceux lancés avant tournent toujours sans.",
    )


# ----------------------------------------------------------------------
# 5. Pendant la charge, l'application d'un autre namespace répond.
# ----------------------------------------------------------------------
def test_l_application_d_un_autre_namespace_repond_pendant_la_charge(host):
    pods = _pods_de_la_charge(host)
    assert len(pods) >= REPLICAS_CHARGE and not _non_bornes(pods), message(
        en=f"The workload of {NS} is not running bounded yet: {AUTRE_NS} is judged while it runs, once bounded.",
        fr=f"La charge de {NS} ne tourne pas encore bornée : {AUTRE_NS} se juge pendant qu'elle tourne, une fois "
        "bornée.",
    )
    dep = _json(host, f"-n {AUTRE_NS} get deployment {APPLICATION}") or {}
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert disponibles == REPLICAS_APPLICATION, message(
        en=f"{APPLICATION} has {disponibles} available replica(s) out of {REPLICAS_APPLICATION}.",
        fr=f"{APPLICATION} a {disponibles} réplica(s) disponible(s) sur {REPLICAS_APPLICATION}.",
    )
    svc = _json(host, f"-n {AUTRE_NS} get service {APPLICATION}") or {}
    ip = (svc.get("spec") or {}).get("clusterIP")
    codes = [host.run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 http://{ip}/").stdout.strip()
             for _ in range(5)] if ip else []
    assert codes and all(c == "200" for c in codes), message(
        en=f"While {CHARGE} runs, {APPLICATION} answers {codes or 'nothing'} instead of five times 200.",
        fr=f"Pendant que {CHARGE} tourne, {APPLICATION} répond {codes or 'rien'} au lieu de cinq fois 200.",
    )
