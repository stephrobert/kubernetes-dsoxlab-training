"""test_functional.py : ckne-capstone-relier-deux-sites

Trois tests, un par état demandé par la fiche du capstone, tous bloquants. Ils
lisent les deux clusters, le routeur de l'équipe réseau et ce que sert la
Gateway, jamais un fichier de l'apprenant. Chacun porte un contraste :

1. la vitrine répond depuis les DEUX sites, puis, le site 1 vidé par le test,
   répond encore depuis le site 2. Le test remet le réplica, même en échec ;
2. la vitrine du site 1 a une adresse du bloc donné, que le routeur a apprise
   en /32 et qui lui répond, ET le Service interne n'est pas annoncé ;
3. la vitrine est servie en HTTPS sous boutique.sites.test avec un certificat
   que vérifie l'autorité des sites et qu'a émis cert-manager, ET HTTP est
   redirigé en 301 vers HTTPS.
"""

from __future__ import annotations

import ipaddress
import json
import os
import time

import pytest

from conftest import lab_host, lab_target_host, message

SITE1 = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
SITE2 = "sudo kubectl --kubeconfig /etc/kubernetes/cluster-2.conf"
BLOC = ipaddress.ip_network("192.168.240.0/28")
NOM = "boutique.sites.test"
EMETTEUR = "autorite-des-sites"
ROUTEUR = "sudo ctr -n dsoxlab task exec --exec-id {id} routeur-frr {commande}"
BUDGET_S = 90
PAS_S = 5


@pytest.fixture(scope="module")
def site1():
    return lab_host(lab_target_host("ha-cp1.lab"))


@pytest.fixture(scope="module")
def routeur():
    return lab_host("k8s-cp.lab")


def _json(hote, kubectl: str, args: str) -> dict:
    res = hote.run(f"{kubectl} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return {}
    return json.loads(res.stdout)


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _serie(site1, n: int) -> list[str]:
    reponses = []
    for _ in range(n):
        res = site1.run(f"{SITE1} -n boutique exec client -- curl -s -m 3 http://vitrine.boutique/")
        reponses.append(res.stdout.strip() if res.rc == 0 else "échec")
    return reponses


def _dans_le_routeur(routeur, commande: str) -> str:
    res = routeur.run(ROUTEUR.format(id=f"test-{os.urandom(3).hex()}", commande=commande))
    return res.stdout if res.rc == 0 else ""


# ----------------------------------------------------------------------
# 1. La vitrine répond depuis les deux sites, et survit au site 1 vidé.
# ----------------------------------------------------------------------
def test_la_vitrine_repond_des_deux_sites_et_survit_au_site_1(site1):
    deux = _attendre(lambda: _serie(site1, 12),
                     lambda r: "vitrine-site-1" in r and "vitrine-site-2" in r)
    assert "vitrine-site-1" in deux and "vitrine-site-2" in deux, message(
        en=f"From the site 1 client, 12 calls to vitrine.boutique answered {sorted(set(deux))}: answers from both "
        "sites are expected. The sites must be linked, and the Service must be shared by both.",
        fr=f"Depuis le client du site 1, 12 appels à vitrine.boutique ont répondu {sorted(set(deux))} : il faut des "
        "réponses des deux sites. Les sites doivent être reliés, et le Service partagé par les deux.",
    )
    # Le Service du site 1 doit toujours désigner les Pods de la vitrine : sans
    # cela, un Pod local quelconque pourrait répondre « vitrine-site-2 ».
    selecteur = _json(site1, SITE1, "-n boutique get service vitrine").get("spec", {}).get("selector")
    assert selecteur == {"app": "vitrine"}, message(
        en=f"The Service vitrine of site 1 now selects {selecteur}: it must keep selecting the shop Pods (app: vitrine).",
        fr=f"Le Service vitrine du site 1 sélectionne maintenant {selecteur} : il doit garder les Pods de la vitrine "
        "(app: vitrine).",
    )
    try:
        site1.run(f"{SITE1} -n boutique scale deployment vitrine --replicas=0")
        site1.run(f"{SITE1} -n boutique wait --for=delete pod -l app=vitrine --timeout=120s")
        # Plus aucun Pod du site 1 ne porte app=vitrine : ce qui répond vient
        # forcément de l'autre site.
        restants = [p["metadata"]["name"] for p in
                    _json(site1, SITE1, "-n boutique get pods -l app=vitrine").get("items", [])]
        assert not restants, message(
            en=f"Site 1 still has Pods labelled app=vitrine once the Deployment is emptied ({restants}): the shop of "
            "site 2 must answer, not a local Pod.",
            fr=f"Le site 1 garde des Pods étiquetés app=vitrine une fois le Deployment vidé ({restants}) : c'est la "
            "vitrine du site 2 qui doit répondre, pas un Pod local.",
        )
        seul = _attendre(lambda: _serie(site1, 8), lambda r: set(r) == {"vitrine-site-2"})
        assert set(seul) == {"vitrine-site-2"}, message(
            en=f"With no vitrine replica left on site 1, 8 calls answered {sorted(set(seul))}: all must come from "
            "site 2. The shop must keep answering when a site stops.",
            fr=f"Sans réplica de la vitrine sur le site 1, 8 appels ont répondu {sorted(set(seul))} : tous doivent "
            "venir du site 2. La boutique doit continuer de répondre quand un site s'arrête.",
        )
    finally:
        site1.run(f"{SITE1} -n boutique scale deployment vitrine --replicas=1")
        site1.run(f"{SITE1} -n boutique rollout status deployment/vitrine --timeout=180s")


# ----------------------------------------------------------------------
# 2. La vitrine du site 1 est annoncée en BGP et répond au routeur.
# ----------------------------------------------------------------------
def _adresses_lb(site1) -> dict[str, list[str]]:
    """Les adresses LoadBalancer du site 1, par Service « namespace/nom »."""
    adresses = {}
    for s in _json(site1, SITE1, "get services -A").get("items", []):
        if s.get("spec", {}).get("type") != "LoadBalancer":
            continue
        ips = [i.get("ip", "") for i in (s.get("status", {}).get("loadBalancer", {}).get("ingress") or [])]
        adresses[f"{s['metadata']['namespace']}/{s['metadata']['name']}"] = [ip for ip in ips if ip]
    return adresses


def _vitrine_lb(site1) -> str:
    for s in _json(site1, SITE1, "get services -n boutique").get("items", []):
        if s.get("spec", {}).get("type") != "LoadBalancer" or s.get("spec", {}).get("selector") != {"app": "vitrine"}:
            continue
        for i in s.get("status", {}).get("loadBalancer", {}).get("ingress") or []:
            ip = i.get("ip", "")
            if ip and ipaddress.ip_address(ip) in BLOC:
                return ip
    return ""


def _routes(routeur) -> set[str]:
    sortie = _dans_le_routeur(routeur, "vtysh -c 'show bgp ipv4 unicast json'")
    try:
        return set((json.loads(sortie).get("routes") or {}).keys())
    except ValueError:
        return set()


def test_la_vitrine_est_annoncee_en_bgp_et_repond_au_routeur(site1, routeur):
    ip = _attendre(lambda: _vitrine_lb(site1), bool)
    assert ip, message(
        en=f"No LoadBalancer Service selecting the vitrine Pods of site 1 has an address in {BLOC} "
        f"(LoadBalancer addresses read: {_adresses_lb(site1)}).",
        fr=f"Aucun Service LoadBalancer qui sélectionne les Pods de la vitrine du site 1 n'a d'adresse dans {BLOC} "
        f"(adresses LoadBalancer lues : {_adresses_lb(site1)}).",
    )
    routes = _attendre(lambda: _routes(routeur), lambda r: f"{ip}/32" in r)
    assert f"{ip}/32" in routes, message(
        en=f"The network team's router has not learnt {ip}/32 (routes: {sorted(routes)}). The site must announce "
        "the shop's address to the router, in BGP.",
        fr=f"Le routeur de l'équipe réseau n'a pas appris {ip}/32 (routes : {sorted(routes)}). Le site doit annoncer "
        "l'adresse de la boutique au routeur, en BGP.",
    )
    page = _attendre(lambda: _dans_le_routeur(routeur, f"wget -qO- -T 5 http://{ip}/"),
                     lambda p: "vitrine-site" in p)
    assert "vitrine-site" in page, message(
        en=f"From the router, http://{ip}/ does not return the shop page (read: « {page.strip()} »).",
        fr=f"Depuis le routeur, http://{ip}/ ne rend pas la page de la boutique (lu : « {page.strip()} »).",
    )
    interne = _adresses_lb(site1).get("boutique/interne", [])
    annoncees = [a for a in interne if f"{a}/32" in routes]
    assert not annoncees, message(
        en=f"The Service interne is announced to the router ({annoncees}): only the shop may be announced.",
        fr=f"Le Service interne est annoncé au routeur ({annoncees}) : seule la boutique doit l'être.",
    )


# ----------------------------------------------------------------------
# 3. HTTPS sous boutique.sites.test, certificat de cert-manager, HTTP redirigé.
# ----------------------------------------------------------------------
def _adresses_des_gateways(site1) -> list[str]:
    adresses = []
    for g in _json(site1, SITE1, "get gateways.gateway.networking.k8s.io -A").get("items", []):
        adresses += [a.get("value", "") for a in (g.get("status", {}).get("addresses") or []) if a.get("value")]
    return adresses


def _certificat_emis(site1) -> bool:
    for c in _json(site1, SITE1, "get certificates.cert-manager.io -A").get("items", []):
        spec, statut = c.get("spec", {}), c.get("status", {})
        pret = any(x.get("type") == "Ready" and x.get("status") == "True" for x in statut.get("conditions") or [])
        if (spec.get("issuerRef", {}).get("name") == EMETTEUR and NOM in (spec.get("dnsNames") or []) and pret):
            return True
    return False


def test_la_gateway_sert_la_vitrine_en_https_et_redirige_http(site1):
    ca = _json(site1, SITE1, f"-n cert-manager get secret {EMETTEUR}").get("data", {}).get("tls.crt", "")
    assert ca, message(
        en="The certificate of the sites' authority is unreadable: run dsoxlab reset.",
        fr="Le certificat de l'autorité des sites est illisible : lancez dsoxlab reset.",
    )
    # Fichier temporaire créé SUR le nœud par mktemp, retiré dans le finally.
    fichier = site1.run("mktemp --suffix=.crt").stdout.strip()
    site1.run(f"echo {ca} | base64 -d > {fichier}")

    def essai():
        for ip in _adresses_des_gateways(site1):
            https = site1.run(f"curl -s -m 5 --cacert {fichier} --resolve {NOM}:443:{ip} https://{NOM}/")
            http = site1.run(f"curl -s -o /dev/null -m 5 -w '%{{http_code}} %{{redirect_url}}' "
                             f"--resolve {NOM}:80:{ip} http://{NOM}/")
            if https.rc == 0 and "vitrine-site" in https.stdout:
                return ip, https.stdout.strip(), http.stdout.strip()
        return "", "", ""

    try:
        ip, _page, redirection = _attendre(essai, lambda r: bool(r[0]))
    finally:
        site1.run(f"rm -f {fichier}")
    assert ip, message(
        en=f"No Gateway address of site 1 serves the shop at https://{NOM}/ with a certificate the sites' authority "
        f"verifies (Gateway addresses read: {_adresses_des_gateways(site1)}).",
        fr=f"Aucune adresse de Gateway du site 1 ne sert la boutique à https://{NOM}/ avec un certificat que vérifie "
        f"l'autorité des sites (adresses de Gateway lues : {_adresses_des_gateways(site1)}).",
    )
    assert _certificat_emis(site1), message(
        en=f"No cert-manager Certificate for {NOM}, issued by {EMETTEUR}, is Ready: the certificate must come from "
        "cert-manager.",
        fr=f"Aucun Certificate de cert-manager pour {NOM}, émis par {EMETTEUR}, n'est prêt : le certificat doit venir "
        "de cert-manager.",
    )
    code, _, cible = redirection.partition(" ")
    assert code == "301" and cible.startswith(f"https://{NOM}"), message(
        en=f"http://{NOM}/ answers « {redirection} » on {ip}: a 301 redirect to https://{NOM}/ is expected.",
        fr=f"http://{NOM}/ répond « {redirection} » sur {ip} : une redirection 301 vers https://{NOM}/ est attendue.",
    )
