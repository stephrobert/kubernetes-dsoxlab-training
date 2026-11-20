"""test_functional.py : k8s-challenge-migrer-les-api-retirees

Ces tests lisent le dépôt ~/plateforme, le soumettent à l'API server et
lisent les objets du namespace plateforme, jamais les commandes tapées.

La préparation tire au sort quatre manifestes sur six à écrire dans une API
retirée, et garde la liste attendue dans une mémoire lisible par root
seulement : le rapport se confronte à ce tirage. Deux migrations changent
la forme des champs (le Deployment exige un selector en apps/v1, la
EndpointSlice range sa zone dans un champ propre en discovery.k8s.io/v1) :
changer la seule ligne apiVersion ne suffit pas toujours.

Deux tests sont bloquants, parce qu'ils portent le cœur du geste : le
rapport qui nomme chaque API retirée et sa remplaçante, et un dépôt dont
chaque fichier est accepté par l'API server.

Tous échouent avant le travail : pas de rapport, quatre fichiers refusés,
rien d'appliqué.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

NS = "plateforme"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MEMOIRE = "/var/lib/dsoxlab/challenge-migrer-les-api-retirees.json"
NGINX = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
RETIREES = {
    "extensions/v1beta1", "rbac.authorization.k8s.io/v1beta1", "scheduling.k8s.io/v1beta1",
    "discovery.k8s.io/v1beta1",
}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def depot(host) -> str:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    return f"{maison}/plateforme"


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Le rapport nomme chaque API retirée et sa remplaçante. BLOQUANT.
# ----------------------------------------------------------------------
def test_le_rapport_nomme_chaque_api_retiree_et_sa_remplacante(host, depot, memoire):
    res = host.run(f"sudo cat {depot}/rapport.txt")
    lu: dict[str, list[str]] = {}
    for ligne in res.stdout.splitlines() if res.rc == 0 else []:
        champs = [c.strip() for c in ligne.split(";")]
        if len(champs) == 3 and champs[0]:
            lu[champs[0]] = champs[1:]
    attendu = memoire["retires"]
    manquants = sorted(set(attendu) - set(lu))
    en_trop = sorted(set(lu) - set(attendu))
    faux = sorted(f for f in set(lu) & set(attendu) if lu[f] != attendu[f])
    assert res.rc == 0 and not (manquants or en_trop or faux), message(
        en=f"~/plateforme/rapport.txt {'is missing' if res.rc else 'does not match the repository'}: files "
        f"missing {manquants or 'none'}, files that used no removed API {en_trop or 'none'}, wrong versions "
        f"for {faux or 'none'}. Expected one line `file;removed API;replacement API` per manifest that used a "
        "removed API, and only those.",
        fr=f"~/plateforme/rapport.txt {'manque' if res.rc else 'ne correspond pas au dépôt'} : fichiers "
        f"manquants {manquants or 'aucun'}, fichiers sans API retirée {en_trop or 'aucun'}, versions fausses "
        f"pour {faux or 'aucun'}. Attendu une ligne `fichier;API retirée;API de remplacement` par manifeste "
        "qui employait une API retirée, et pour eux seuls.",
    )


# ----------------------------------------------------------------------
# 2. Chaque fichier du dépôt est accepté par l'API server. BLOQUANT.
# ----------------------------------------------------------------------
def test_chaque_manifeste_du_depot_est_accepte_par_l_api_server(host, depot, memoire):
    refuses, absents, anciens = [], [], []
    for fichier in memoire["fichiers"]:
        contenu = host.run(f"sudo cat {depot}/{fichier}")
        if contenu.rc != 0:
            absents.append(fichier)
            continue
        try:
            version = (yaml.safe_load(contenu.stdout) or {}).get("apiVersion")
        except yaml.YAMLError:
            version = None
        if version in RETIREES:
            anciens.append(fichier)
        if host.run(f"{ADMIN} apply --dry-run=server -f {depot}/{fichier}").rc != 0:
            refuses.append(fichier)
    assert not (refuses or absents or anciens), message(
        en=f"Files missing {absents or 'none'}, still in a removed API {anciens or 'none'}, refused by the API "
        f"server {refuses or 'none'}. Expected every manifest of the repository still there, migrated, and "
        "accepted. A file is migrated, never deleted.",
        fr=f"Fichiers absents {absents or 'aucun'}, encore en API retirée {anciens or 'aucun'}, refusés par "
        f"l'API server {refuses or 'aucun'}. Attendu chaque manifeste du dépôt toujours là, migré, et accepté. "
        "Un fichier se migre, il ne se supprime pas.",
    )


# ----------------------------------------------------------------------
# 3. Le dépôt est appliqué tel quel.
# ----------------------------------------------------------------------
def test_le_depot_est_applique_tel_quel(host, depot):
    res = host.run(f"{ADMIN} diff -f {depot}")
    assert res.rc == 0, message(
        en=f"`kubectl diff -f ~/plateforme` finds a gap (code {res.rc}): the migrated repository is not "
        f"applied, or the cluster differs from it. {res.stderr.strip()[:200]}",
        fr=f"`kubectl diff -f ~/plateforme` trouve un écart (code {res.rc}) : le dépôt migré n'est pas "
        f"appliqué, ou le cluster s'en écarte. {res.stderr.strip()[:200]}",
    )


# ----------------------------------------------------------------------
# 4. Les objets décrivent la même intention que les manifestes hérités.
# ----------------------------------------------------------------------
def test_les_objets_decrivent_la_meme_intention(host):
    ecarts = []
    dep = (_json(host, f"-n {NS} get deployment registre") or {}).get("spec") or {}
    conteneurs = ((dep.get("template") or {}).get("spec") or {}).get("containers") or [{}]
    if (dep.get("replicas"), (dep.get("selector") or {}).get("matchLabels"), conteneurs[0].get("image")) != \
            (2, {"app": "registre"}, NGINX):
        ecarts.append("Deployment registre")
    np_ = (_json(host, f"-n {NS} get networkpolicy registre-entrant") or {}).get("spec") or {}
    regle = (np_.get("ingress") or [{}])[0]
    if ((np_.get("podSelector") or {}).get("matchLabels"),
            [(f.get("podSelector") or {}).get("matchLabels") for f in regle.get("from") or []],
            [(p.get("protocol", "TCP"), p.get("port")) for p in regle.get("ports") or []]) != \
            ({"app": "registre"}, [{"role": "client"}], [("TCP", 80)]):
        ecarts.append("NetworkPolicy registre-entrant")
    role = (_json(host, f"-n {NS} get role deployeur") or {}).get("rules") or []
    if [(r.get("apiGroups"), r.get("resources"), sorted(r.get("verbs") or [])) for r in role] != \
            [(["apps"], ["deployments"], ["get", "list", "patch"])]:
        ecarts.append("Role deployeur")
    liaison = _json(host, f"-n {NS} get rolebinding deployeur") or {}
    if ([(s.get("kind"), s.get("name"), s.get("namespace")) for s in liaison.get("subjects") or []],
            ((liaison.get("roleRef") or {}).get("kind"), (liaison.get("roleRef") or {}).get("name"))) != \
            ([("ServiceAccount", "deployeur", NS)], ("Role", "deployeur")):
        ecarts.append("RoleBinding deployeur")
    pc = _json(host, "get priorityclass plateforme-critique") or {}
    if (pc.get("value"), pc.get("globalDefault", False)) != (900000, False):
        ecarts.append("PriorityClass plateforme-critique")
    tranche = _json(host, f"-n {NS} get endpointslice registre-externe-1") or {}
    points = tranche.get("endpoints") or [{}]
    if ([(p.get("name"), p.get("port")) for p in tranche.get("ports") or []], points[0].get("addresses"),
            points[0].get("zone")) != ([("http", 5000)], ["10.20.30.40"], "zone-ouest"):
        ecarts.append("EndpointSlice registre-externe-1")
    assert not ecarts, message(
        en=f"These objects do not describe what the inherited manifests described: {ecarts}. A migration "
        "changes the API, not the intent: same values, same targets, same zone.",
        fr=f"Ces objets ne décrivent pas ce que décrivaient les manifestes hérités : {ecarts}. Une migration "
        "change l'API, pas l'intention : mêmes valeurs, mêmes cibles, même zone.",
    )


# ----------------------------------------------------------------------
# 5. Le registre tourne avec ses deux réplicas.
# ----------------------------------------------------------------------
def test_le_registre_tourne_avec_ses_deux_replicas(host):
    statut = (_json(host, f"-n {NS} get deployment registre") or {}).get("status") or {}
    assert statut.get("availableReplicas") == 2, message(
        en=f"registre has {statut.get('availableReplicas', 0)} replica(s) available, expected 2.",
        fr=f"registre a {statut.get('availableReplicas', 0)} réplica(s) disponible(s), attendu 2.",
    )
