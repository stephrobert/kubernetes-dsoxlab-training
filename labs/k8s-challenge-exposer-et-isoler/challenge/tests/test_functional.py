"""test_functional.py : k8s-challenge-exposer-et-isoler

Sept tests, un par exigence du cahier des charges. Ils lisent l'état du
cluster et font de vraies requêtes, jamais les commandes tapées.

Chaque test qui porte sur un flux vérifie aussi le flux qui doit être refusé :
sans route, sans politique, presque tout passe déjà, et un test qui ne
regarderait que le flux permis passerait avant le travail.

L'énoncé laisse le choix de la route, un Ingress ou une HTTPRoute, nommée
vitrine dans les deux cas. Les deux passent par le même Traefik, sur le
NodePort 30080.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "comptoir"
VOISINAGE = "voisinage"
HOTE = "comptoir.local"
PORT = 30080
ROUTE = "vitrine"
POLITIQUE = "base-refus-par-defaut"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Le contrôleur recharge sa configuration après notification : elle n'agit pas
# à la seconde où l'API accepte l'objet. On n'attend que si une route existe,
# pour que l'état de départ se note vite.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _objet(host, args: str) -> dict | None:
    res = _kubectl(host, f"{args} -o json")
    if res.rc != 0:
        return None
    return json.loads(res.stdout)


def _demander(host, chemin: str, hote: str = HOTE) -> str:
    """Rend le corps de la réponse, vide si rien n'a répondu."""
    res = host.run(
        f"curl -s --resolve {hote}:{PORT}:127.0.0.1 http://{hote}:{PORT}{chemin} --max-time 8"
    )
    return res.stdout.strip()


def _une_route_existe(host) -> bool:
    ingress = _kubectl(host, f"-n {NAMESPACE} get ingress -o name").stdout.strip()
    httproute = _kubectl(host, f"-n {NAMESPACE} get httproute -o name").stdout.strip()
    return bool(ingress or httproute)


def _selecteur(selecteur: dict) -> str:
    """Traduit un podSelector en sélecteur de labels pour kubectl."""
    parties = [f"{k}={v}" for k, v in (selecteur.get("matchLabels") or {}).items()]
    for e in selecteur.get("matchExpressions") or []:
        cle, op, valeurs = e["key"], e["operator"], e.get("values") or []
        if op == "In":
            parties.append(f"{cle} in ({','.join(valeurs)})")
        elif op == "NotIn":
            parties.append(f"{cle} notin ({','.join(valeurs)})")
        elif op == "Exists":
            parties.append(cle)
        elif op == "DoesNotExist":
            parties.append(f"!{cle}")
    return ",".join(parties)


def _connecte(host, namespace: str, pod: str, cible: str) -> bool:
    """Une connexion TCP vers la base, trois secondes au plus."""
    return _kubectl(host, f"-n {namespace} exec {pod} -- nc -z -w 3 {cible} 5432").rc == 0


# ----------------------------------------------------------------------
# 1. Chaque chemin de comptoir.local atteint son application, et rien d'autre.
# ----------------------------------------------------------------------
def test_chaque_chemin_atteint_son_application(host):
    def mesure() -> dict[str, str]:
        return {
            "/catalogue": _demander(host, "/catalogue"),
            "/panier": _demander(host, "/panier"),
            "/autre": _demander(host, "/autre"),
            "autre hôte": _demander(host, "/catalogue", hote="ailleurs.local"),
        }

    def juste(m: dict[str, str]) -> bool:
        return (
            m["/catalogue"] == "catalogue"
            and m["/panier"] == "panier"
            and m["/autre"] not in ("catalogue", "panier")
            and m["autre hôte"] not in ("catalogue", "panier")
        )

    m = mesure()
    if not juste(m) and _une_route_existe(host):
        fin = time.monotonic() + BUDGET_S
        while not juste(m) and time.monotonic() < fin:
            time.sleep(PAS_S)
            m = mesure()
    assert juste(m), message(
        en=f"Responses received: {m}. Expected catalogue on /catalogue and panier on /panier, for the host "
        f"{HOTE} only, and neither application on an undeclared path or for another host.",
        fr=f"Réponses reçues : {m}. Attendu catalogue sur /catalogue et panier sur /panier, pour l'hôte "
        f"{HOTE} seulement, et aucune des deux applications sur un chemin non déclaré ni pour un autre hôte.",
    )


# ----------------------------------------------------------------------
# 2. La route vitrine est prise en charge par son contrôleur.
# ----------------------------------------------------------------------
def _ingress_pris_en_charge(host) -> tuple[bool, str]:
    ing = _objet(host, f"-n {NAMESPACE} get ingress {ROUTE}")
    if ing is None:
        return False, ""
    adresses = (ing.get("status", {}).get("loadBalancer") or {}).get("ingress") or []
    classe = ing["spec"].get("ingressClassName")
    return bool(adresses), f"Ingress {ROUTE} (class {classe}, address {adresses or 'none'})"


def _httproute_prise_en_charge(host) -> tuple[bool, str]:
    route = _objet(host, f"-n {NAMESPACE} get httproute {ROUTE}")
    if route is None:
        return False, ""
    parents = route.get("status", {}).get("parents") or []
    acceptee = any(
        c.get("type") == "Accepted" and c.get("status") == "True"
        for p in parents for c in p.get("conditions") or []
    )
    programmees = []
    for ref in route["spec"].get("parentRefs") or []:
        gw = _objet(host, f"-n {ref.get('namespace', NAMESPACE)} get gateway {ref['name']}")
        conditions = (gw or {}).get("status", {}).get("conditions") or []
        programmees.append(any(c.get("type") == "Programmed" and c.get("status") == "True" for c in conditions))
    ok = acceptee and bool(programmees) and all(programmees)
    return ok, f"HTTPRoute {ROUTE} (accepted: {acceptee}, Gateway programmed: {programmees or 'no parent'})"


def test_la_route_vitrine_est_prise_en_charge(host):
    def mesure() -> tuple[bool, list[str]]:
        vus = []
        for lire in (_ingress_pris_en_charge, _httproute_prise_en_charge):
            ok, vu = lire(host)
            if vu:
                vus.append(vu)
            if ok:
                return True, vus
        return False, vus

    ok, vus = mesure()
    if not ok and vus:
        fin = time.monotonic() + BUDGET_S
        while not ok and time.monotonic() < fin:
            time.sleep(PAS_S)
            ok, vus = mesure()
    assert ok, message(
        en=f"Seen: {vus or 'no Ingress and no HTTPRoute named ' + ROUTE + ' in ' + NAMESPACE}. Expected the "
        f"route {ROUTE} taken over by its controller: an Ingress that carries an address, or an HTTPRoute "
        "accepted by a programmed Gateway.",
        fr=f"Vu : {vus or 'aucun Ingress ni aucune HTTPRoute nommés ' + ROUTE + ' dans ' + NAMESPACE}. Attendu "
        f"la route {ROUTE} prise en charge par son contrôleur : un Ingress qui porte une adresse, ou une "
        "HTTPRoute acceptée par une Gateway programmée.",
    )


# ----------------------------------------------------------------------
# 3. Le Service ancien a des endpoints, sur le port où le conteneur écoute.
# ----------------------------------------------------------------------
def test_le_service_ancien_atteint_ses_pods_sur_le_bon_port(host):
    tranches = _objet(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name=ancien") or {}
    pods_ancien = set(
        _kubectl(host, f"-n {NAMESPACE} get pods -l app=ancien -o jsonpath='{{.items[*].metadata.name}}'")
        .stdout.split()
    )
    vises, ports = set(), set()
    for t in tranches.get("items", []):
        for e in t.get("endpoints") or []:
            if (e.get("conditions") or {}).get("ready"):
                vises.add((e.get("targetRef") or {}).get("name"))
        for p in t.get("ports") or []:
            ports.add(p.get("port"))
    svc = _objet(host, f"-n {NAMESPACE} get service ancien") or {}
    ip = svc.get("spec", {}).get("clusterIP", "")
    reponse = host.run(f"curl -s --max-time 5 http://{ip}/").stdout if ip else ""
    ok = bool(vises) and vises <= pods_ancien and ports == {80} and "nginx" in reponse
    assert ok, message(
        en=f"The Service ancien sends to {sorted(v for v in vises if v) or 'no Pod'} on port(s) "
        f"{sorted(p for p in ports if p) or 'none'}, and {'answers' if 'nginx' in reponse else 'does not answer'}. "
        "Expected ready Pods of the ancien Deployment, reached on the port their container listens on.",
        fr=f"Le Service ancien envoie vers {sorted(v for v in vises if v) or 'aucun Pod'} sur le(s) port(s) "
        f"{sorted(p for p in ports if p) or 'aucun'}, et {'répond' if 'nginx' in reponse else 'ne répond pas'}. "
        "Attendu des Pods prêts du Deployment ancien, joints sur le port où leur conteneur écoute.",
    )


# ----------------------------------------------------------------------
# 4. Le Pod sonde résout le nom du Service catalogue et le joint en HTTP.
# ----------------------------------------------------------------------
def test_sonde_resout_et_joint_catalogue(host):
    # nslookup interroge le serveur DNS du Pod lui-même, sans passer par
    # /etc/hosts : une entrée posée à la main n'y suffit pas.
    resout = _kubectl(
        host, f"-n {NAMESPACE} exec sonde -- nslookup catalogue.{NAMESPACE}.svc.cluster.local"
    ).rc == 0
    corps = _kubectl(host, f"-n {NAMESPACE} exec sonde -- wget -qO- -T 3 http://catalogue/").stdout.strip()
    assert resout and corps == "catalogue", message(
        en=f"sonde {'resolves' if resout else 'does not resolve'} the name of the Service catalogue through "
        f"its DNS server, and {'reaches' if corps == 'catalogue' else 'does not reach'} it over HTTP by its "
        "short name. Expected both.",
        fr=f"sonde {'résout' if resout else 'ne résout pas'} le nom du Service catalogue par son serveur DNS, "
        f"et {'le joint' if corps == 'catalogue' else 'ne le joint pas'} en HTTP par son nom court. Attendu "
        "les deux.",
    )


# ----------------------------------------------------------------------
# 5. Un refus par défaut vise les Pods de la base, et eux seuls.
# ----------------------------------------------------------------------
def test_un_refus_par_defaut_vise_la_base(host):
    p = _objet(host, f"-n {NAMESPACE} get networkpolicy {POLITIQUE}")
    assert p is not None, message(
        en=f"No NetworkPolicy {POLITIQUE} in {NAMESPACE}.",
        fr=f"Aucune NetworkPolicy {POLITIQUE} dans {NAMESPACE}.",
    )
    spec = p["spec"]
    selecteur = _selecteur(spec.get("podSelector") or {})
    vises = sorted(
        _kubectl(host, f"-n {NAMESPACE} get pods -l '{selecteur}' -o jsonpath='{{.items[*].metadata.name}}'")
        .stdout.split()
    ) if selecteur else ["(tous les Pods)"]
    types = spec.get("policyTypes") or ["Ingress"]
    regles = (spec.get("ingress") or []) + (spec.get("egress") or [])
    ok = vises == ["base"] and "Ingress" in types and "Egress" in types and not regles
    assert ok, message(
        en=f"{POLITIQUE} selects {vises}, declares policyTypes {types} and carries {len(regles)} rule(s). "
        "Expected the base Pod alone, both directions, and no rule at all: a default refusal allows nothing, "
        "the allowed flows belong to other policies.",
        fr=f"{POLITIQUE} sélectionne {vises}, déclare policyTypes {types} et porte {len(regles)} règle(s). "
        "Attendu le Pod base seul, les deux directions, et aucune règle : un refus par défaut n'autorise rien, "
        "les flux permis relèvent d'autres politiques.",
    )


# ----------------------------------------------------------------------
# 6. Le backend joint la base ; le frontend et le rôdeur de voisinage non.
# ----------------------------------------------------------------------
def test_seul_le_backend_joint_la_base(host):
    backend = _connecte(host, NAMESPACE, "backend", "base")
    frontend = _connecte(host, NAMESPACE, "frontend", "base")
    rodeur = _connecte(host, VOISINAGE, "rodeur", f"base.{NAMESPACE}.svc.cluster.local")
    assert backend and not frontend and not rodeur, message(
        en=f"On port 5432 of base: backend {'gets in' if backend else 'is refused'}, frontend "
        f"{'gets in' if frontend else 'is refused'}, rodeur from {VOISINAGE} {'gets in' if rodeur else 'is refused'}. "
        "Expected backend allowed, the other two refused, although rodeur carries the same label as backend.",
        fr=f"Sur le port 5432 de base : backend {'entre' if backend else 'est refusé'}, frontend "
        f"{'entre' if frontend else 'est refusé'}, rodeur de {VOISINAGE} {'entre' if rodeur else 'est refusé'}. "
        "Attendu backend autorisé, les deux autres refusés, bien que rodeur porte le même label que backend.",
    )


# ----------------------------------------------------------------------
# 7. La base résout toujours un nom, et ne sort vers rien d'autre.
# ----------------------------------------------------------------------
def test_la_base_ne_sort_que_vers_le_dns(host):
    resout = _kubectl(host, f"-n {NAMESPACE} exec base -- nslookup kubernetes.default.svc.cluster.local").rc == 0
    ailleurs = _kubectl(
        host, f"-n {NAMESPACE} exec base -- wget -qO- -T 3 http://catalogue.{NAMESPACE}.svc.cluster.local/"
    ).stdout.strip() == "catalogue"
    assert resout and not ailleurs, message(
        en=f"base {'resolves' if resout else 'does not resolve'} names and {'reaches' if ailleurs else 'does not reach'} "
        "catalogue. Expected DNS still open despite the default refusal, and every other outbound flow refused.",
        fr=f"base {'résout' if resout else 'ne résout pas'} les noms et {'joint' if ailleurs else 'ne joint pas'} "
        "catalogue. Attendu le DNS toujours ouvert malgré le refus par défaut, et toute autre sortie refusée.",
    )
