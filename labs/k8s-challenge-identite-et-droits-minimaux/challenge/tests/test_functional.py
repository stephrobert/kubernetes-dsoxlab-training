"""test_functional.py : k8s-challenge-identite-et-droits-minimaux

Le challenge du module 9 (D59). Ces tests lisent l'état du CLUSTER, jamais les
commandes tapées. Un test vérifie un seul état.

Les droits de collecte se prouvent depuis SON Pod, avec SON jeton : c'est la
seule preuve que l'application, et pas l'administrateur, a ces droits. Les
refus du troisième test n'ont de sens que si collecte tourne sous sa propre
identité : sous le compte par défaut, ils seraient vrais avant tout travail.

Le sixième (décision du 2026-11-13) porte la compétence de durcissement du
module : le Pod de collecte tourne en non-root sous un UID numérique, sans
élévation de privilèges, racine en lecture seule et sans aucune capability, et
l'état 2 reste vrai. Il lit les Pods EN MARCHE du Deployment, pas le manifeste.

Seuls comptent les Pods créés par le ReplicaSet du Deployment : un Pod nu posé
à côté, avec la même étiquette, n'est pas l'application.

Les six tests échouent sur l'état que pose le setup : collecte et tableau
tournent sous le compte par défaut, qui monte un jeton dans chaque Pod et a
hérité du ClusterRole edit dans observatoire, et collecte tourne sans contexte
de sécurité.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

OBS = "observatoire"
PROD = "production"
SA = "collecte"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
JETON = "/var/run/secrets/kubernetes.io/serviceaccount"
DEFAUT = f"system:serviceaccount:{OBS}:default"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


_DEJA_LUS: dict[str, list[dict]] = {}


def _du_deployment(pod: dict, app: str) -> bool:
    """Le Pod a été créé par le ReplicaSet du Deployment app : un Pod nu posé à
    côté, avec la même étiquette, n'est pas l'application."""
    return any(o.get("kind") == "ReplicaSet" and o.get("name", "").startswith(f"{app}-")
               for o in pod["metadata"].get("ownerReferences") or [])


def _pods_en_marche(host, app: str, attendre: bool = False) -> list[dict]:
    """Les Pods en marche et prêts du Deployment app d'observatoire. Avec
    attendre, laisse au Deployment le temps de remplacer un Pod qu'on vient de
    modifier, sans attendre si aucun Pod n'existe du tout. Le résultat attendu
    est gardé pour la durée du check : un Pod qui ne démarre pas ne coûte qu'une
    attente, et dsoxlab coupe pytest au bout de 300 secondes."""
    if attendre and app in _DEJA_LUS:
        return _DEJA_LUS[app]
    prets: list[dict] = []
    for _ in range(18 if attendre else 1):
        items = (_json(host, f"-n {OBS} get pods -l app={app}") or {}).get("items") or []
        vivants = [p for p in items if not p["metadata"].get("deletionTimestamp") and _du_deployment(p, app)]
        prets = [p for p in vivants if p["status"].get("phase") == "Running"
                 and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])]
        if not vivants or (prets and len(prets) == len(vivants)):
            break
        time.sleep(5)
    if attendre:
        _DEJA_LUS[app] = prets
    return prets


def _collecte(host) -> dict:
    pods = _pods_en_marche(host, "collecte", attendre=True)
    assert pods, message(
        en=f"No running Pod of collecte in {OBS}: it is the tool to give an identity to, it stays.",
        fr=f"Aucun Pod de collecte en marche dans {OBS} : c'est l'outil à doter d'une identité, il reste.",
    )
    return pods[0]


def _code_http(host, pod: str, chemin: str, methode: str = "GET") -> str:
    """Interroge l'API depuis le Pod de collecte, avec son jeton, et rend le code HTTP."""
    commande = (
        f"D={JETON}; "
        f'curl -s -o /dev/null -w "%{{http_code}}" -X {methode} --cacert $D/ca.crt '
        f'-H "Authorization: Bearer $(cat $D/token)" https://kubernetes.default.svc{chemin}'
    )
    res = host.run(f"{KUBECTL} -n {OBS} exec {pod} -- sh -c '{commande}'")
    assert res.rc == 0, message(
        en=f"Cannot query the API from the Pod of collecte: {res.stderr.strip()[:200]}",
        fr=f"Impossible d'interroger l'API depuis le Pod de collecte : {res.stderr.strip()[:200]}",
    )
    return res.stdout.strip()


#: Un ServiceAccount d'un namespace qui n'existe pas : l'API le range dans
#: system:serviceaccounts et system:authenticated, rien de plus. Ce qu'il
#: reçoit, c'est ce que reçoit TOUT ServiceAccount : s'interroger sur ses
#: propres droits, lire les ClusterTrustBundles (Kubernetes 1.37), plus ce que
#: les extensions du cluster accordent à tous (l'API de Calico en ajoute).
#: Mesuré, jamais écrit en dur. Un droit donné au groupe des ServiceAccounts
#: d'observatoire, lui, reste visible.
_TEMOIN = "system:serviceaccount:dsoxlab-temoin-inexistant:sans-droit"
_BASES: dict[str, set] = {}


def _cle(regle: dict) -> tuple:
    return tuple(tuple(sorted(regle.get(champ) or [])) for champ in ("apiGroups", "resources", "resourceNames", "verbs"))


def _regles(host, sujet: str, ns: str) -> list[dict]:
    revue = ('{"apiVersion":"authorization.k8s.io/v1","kind":"SelfSubjectRulesReview",'
             f'"spec":{{"namespace":"{ns}"}}}}')
    res = host.run(f"echo '{revue}' | {KUBECTL} create --validate=false --as {sujet} -f - -o json")
    assert res.rc == 0, message(
        en=f"Cannot compute the rights of {sujet} in {ns}: {res.stderr.strip()[:200]}",
        fr=f"Impossible de calculer les droits de {sujet} dans {ns} : {res.stderr.strip()[:200]}",
    )
    return (json.loads(res.stdout).get("status") or {}).get("resourceRules") or []


def _droits_effectifs(host, sujet: str, ns: str) -> list[dict]:
    """Les règles de ressource que l'API accorde à sujet dans ns, calculées par
    une SelfSubjectRulesReview jouée sous son identité, moins ce que reçoit le
    témoin dans le même namespace. Un droit accordé pour tout le cluster y
    figure dans chaque namespace."""
    if ns not in _BASES:
        _BASES[ns] = {_cle(r) for r in _regles(host, _TEMOIN, ns)}
    return [r for r in _regles(host, sujet, ns) if _cle(r) not in _BASES[ns]]


def _sous_son_identite(pod: dict) -> bool:
    return pod["spec"].get("serviceAccountName") == SA


# ----------------------------------------------------------------------
# 1. collecte tourne sous sa propre identité.
# ----------------------------------------------------------------------
def test_collecte_tourne_sous_sa_propre_identite(host):
    assert _json(host, f"-n {OBS} get serviceaccount {SA}") is not None, message(
        en=f"No identity named {SA} in {OBS}.",
        fr=f"Aucune identité nommée {SA} dans {OBS}.",
    )
    pod = _collecte(host)
    assert _sous_son_identite(pod), message(
        en=f"The Pod of collecte runs as {pod['spec'].get('serviceAccountName')!r}, not as {SA}: an "
        "application shares no identity, not even the namespace's default one.",
        fr=f"Le Pod de collecte tourne sous {pod['spec'].get('serviceAccountName')!r}, et non sous {SA} : "
        "une application ne partage pas d'identité, pas même celle du namespace par défaut.",
    )


# ----------------------------------------------------------------------
# 2. Depuis son Pod, collecte lit le journal des Pods de production.
# ----------------------------------------------------------------------
def test_collecte_lit_les_journaux_de_production(host):
    pod = _collecte(host)
    code = _code_http(host, pod["metadata"]["name"], f"/api/v1/namespaces/{PROD}/pods/commandes/log?tailLines=1")
    assert code == "200", message(
        en=f"From the Pod of collecte, reading the log of the Pod commandes in {PROD} answers {code} "
        "instead of 200. The log of a Pod is a resource of its own, granted in the namespace where the "
        "Pods live, to the identity the Pod presents.",
        fr=f"Depuis le Pod de collecte, lire le journal du Pod commandes de {PROD} répond {code} au lieu "
        "de 200. Le journal d'un Pod est une ressource à part, accordée dans le namespace où vivent les "
        "Pods, à l'identité que le Pod présente.",
    )


# ----------------------------------------------------------------------
# 3. collecte n'a aucun autre droit.
# ----------------------------------------------------------------------
def test_collecte_n_a_aucun_autre_droit(host):
    pod = _collecte(host)
    assert _sous_son_identite(pod), message(
        en=f"collecte does not run as {SA} yet: its rights cannot be judged under another identity.",
        fr=f"collecte ne tourne pas encore sous {SA} : ses droits ne se jugent pas sous une autre identité.",
    )
    nom = pod["metadata"]["name"]
    refus = {
        message(en="delete the Pod commandes of production", fr="supprimer le Pod commandes de production"):
            _code_http(host, nom, f"/api/v1/namespaces/{PROD}/pods/commandes", "DELETE"),
        message(en="read the Secrets of production", fr="lire les Secrets de production"):
            _code_http(host, nom, f"/api/v1/namespaces/{PROD}/secrets"),
        message(en="read the Pods of kube-system", fr="lire les Pods de kube-system"):
            _code_http(host, nom, "/api/v1/namespaces/kube-system/pods"),
        message(en="read the logs of a Pod of kube-system", fr="lire le journal d'un Pod de kube-system"):
            _code_http(host, nom, "/api/v1/namespaces/kube-system/pods/etcd-k8s-cp.lab/log?tailLines=1"),
    }
    passes = {k: v for k, v in refus.items() if v != "403"}
    assert not passes, message(
        en=f"These requests from collecte should answer 403 and answer: {passes}. Its identity has more "
        "than reading the logs of production: a right granted for the whole cluster, or too broad a role.",
        fr=f"Ces requêtes de collecte devraient répondre 403 et répondent : {passes}. Son identité a plus "
        "que la lecture des journaux de production : un droit accordé pour tout le cluster, ou un rôle trop large.",
    )
    # Au-delà de ces refus ponctuels, la politique EFFECTIVE de l'identité, telle
    # que l'API la calcule (audit du 2026-11-13) : dans production, rien de plus
    # que lire les Pods et leur journal ; ailleurs, rien du tout. Un droit
    # accordé pour tout le cluster apparaît dans chaque namespace.
    sujet = f"system:serviceaccount:{OBS}:{SA}"
    en_trop = {}
    for ns in (PROD, OBS, "kube-system", "default"):
        regles = _droits_effectifs(host, sujet, ns)
        if ns == PROD:
            regles = [r for r in regles if not (
                set(r.get("apiGroups") or []) <= {""}
                and set(r.get("resources") or []) <= {"pods", "pods/log"}
                and set(r.get("verbs") or []) <= {"get", "list", "watch"})]
        if regles:
            en_trop[ns] = [f"{','.join(r.get('verbs') or [])} {','.join(r.get('resources') or [])}" for r in regles]
    assert not en_trop, message(
        en=f"The identity {SA} holds more than reading the Pods of {PROD} and their logs: {en_trop}.",
        fr=f"L'identité {SA} a plus que la lecture des Pods de {PROD} et de leur journal : {en_trop}.",
    )


# ----------------------------------------------------------------------
# 4. Le Pod de tableau ne porte aucun jeton.
# ----------------------------------------------------------------------
def _porte_un_jeton(pod: dict) -> list[str]:
    projetes = {v["name"] for v in pod["spec"].get("volumes") or []
                if any("serviceAccountToken" in s for s in (v.get("projected") or {}).get("sources") or [])}
    return [c["name"] for c in (pod["spec"].get("containers") or []) + (pod["spec"].get("initContainers") or [])
            if any(m.get("mountPath", "").startswith(JETON) or m.get("name") in projetes
                   for m in c.get("volumeMounts") or [])]


def test_tableau_ne_porte_aucun_jeton(host):
    pods = _pods_en_marche(host, "tableau", attendre=True)
    assert pods, message(
        en=f"No running Pod of tableau in {OBS}: it serves its page, it is not removed.",
        fr=f"Aucun Pod de tableau en marche dans {OBS} : il sert sa page, on ne le retire pas.",
    )
    avec_jeton = {p["metadata"]["name"]: _porte_un_jeton(p) for p in pods}
    avec_jeton = {nom: c for nom, c in avec_jeton.items() if c}
    assert not avec_jeton, message(
        en=f"tableau never calls the API, yet a token is mounted in {avec_jeton}. A Pod created before the "
        "change keeps its token until it is recreated.",
        fr=f"tableau n'appelle jamais l'API, et pourtant un jeton est monté dans {avec_jeton}. Un Pod créé "
        "avant le changement garde son jeton tant qu'il n'est pas recréé.",
    )


# ----------------------------------------------------------------------
# 5. Le compte par défaut d'observatoire ne garde aucun droit.
# ----------------------------------------------------------------------
def test_le_compte_par_defaut_n_a_plus_aucun_droit(host):
    # La politique effective du compte, et non quelques can-i (audit du
    # 2026-11-13) : dans observatoire, dans production et à l'échelle du
    # cluster, il ne doit rien lui rester au-delà de ce que tout compte reçoit.
    accordes = []
    for ns in (OBS, PROD, "default"):
        accordes += [f"{ns}: {','.join(r.get('verbs') or [])} {','.join(r.get('resources') or [])}"
                     for r in _droits_effectifs(host, DEFAUT, ns)]
    assert not accordes, message(
        en=f"The default account of {OBS} can still: {accordes}. Every Pod that names no identity gets it: "
        "a right inherited by the default account is a right every forgotten Pod has.",
        fr=f"Le compte par défaut d'{OBS} peut encore : {accordes}. Tout Pod qui ne nomme pas d'identité le "
        "reçoit : un droit hérité par le compte par défaut est un droit qu'a chaque Pod oublié.",
    )


# ----------------------------------------------------------------------
# 6. Le Pod de collecte est durci, et fait toujours son travail.
# ----------------------------------------------------------------------
def _ecarts_de_durcissement(pod: dict) -> list[str]:
    """Ce qui manque au durcissement du conteneur collecte, réglages du Pod et du
    conteneur fusionnés comme le kubelet les applique (le conteneur l'emporte)."""
    spec = pod["spec"]
    conteneur = next((c for c in spec["containers"] if c["name"] == "collecte"), spec["containers"][0])
    sc_pod = spec.get("securityContext") or {}
    sc = {**{k: sc_pod[k] for k in ("runAsNonRoot", "runAsUser") if k in sc_pod},
          **(conteneur.get("securityContext") or {})}
    capacites = sc.get("capabilities") or {}
    ecarts = []
    if sc.get("runAsNonRoot") is not True:
        ecarts.append("runAsNonRoot")
    if not isinstance(sc.get("runAsUser"), int) or sc.get("runAsUser") == 0:
        ecarts.append(message(en="numeric non-zero UID", fr="UID numérique non nul"))
    if sc.get("allowPrivilegeEscalation") is not False:
        ecarts.append("allowPrivilegeEscalation: false")
    if sc.get("readOnlyRootFilesystem") is not True:
        ecarts.append("readOnlyRootFilesystem")
    if "ALL" not in (capacites.get("drop") or []):
        ecarts.append("capabilities drop ALL")
    if capacites.get("add"):
        ecarts.append(message(en=f"capabilities added back: {capacites['add']}",
                              fr=f"capabilities rajoutées : {capacites['add']}"))
    return ecarts


def test_collecte_est_durcie_et_travaille(host):
    pods = _pods_en_marche(host, "collecte", attendre=True)
    assert pods, message(
        en=f"No running Pod of the Deployment collecte in {OBS}. A hardened Pod that cannot start does not "
        "count: an image whose user is a name, not a number, is refused under runAsNonRoot.",
        fr=f"Aucun Pod du Deployment collecte en marche dans {OBS}. Un Pod durci qui ne démarre pas ne compte "
        "pas : une image dont l'utilisateur est un nom, et non un nombre, est refusée sous runAsNonRoot.",
    )
    ecarts = {p["metadata"]["name"]: e for p in pods if (e := _ecarts_de_durcissement(p))}
    assert not ecarts, message(
        en=f"The running Pods of collecte are not hardened: {ecarts}. Expected non-root under a numeric UID, "
        "no privilege escalation, a read-only root filesystem and every capability dropped.",
        fr=f"Les Pods en marche de collecte ne sont pas durcis : {ecarts}. Attendu non-root sous un UID "
        "numérique, sans élévation de privilèges, racine en lecture seule et toutes les capabilities retirées.",
    )
    code = _code_http(host, pods[0]["metadata"]["name"],
                      f"/api/v1/namespaces/{PROD}/pods/commandes/log?tailLines=1")
    assert code == "200", message(
        en=f"Hardened, collecte no longer reads the log of commandes (answer {code}): hardening must not stop "
        "the application from doing its job.",
        fr=f"Durcie, collecte ne lit plus le journal de commandes (réponse {code}) : le durcissement ne doit pas "
        "empêcher l'application de faire son travail.",
    )
