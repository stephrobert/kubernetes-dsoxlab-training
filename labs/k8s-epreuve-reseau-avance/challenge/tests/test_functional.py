"""test_functional.py : k8s-epreuve-reseau-avance

Épreuve de fin du niveau 6. Sept états, à poids égal, dont deux bloquants
(E4, E6). Les tests lisent le cluster et font passer de vraies requêtes, par le
Gateway et entre Pods ; jamais un fichier de l'apprenant.

Ce que chaque test sait de la solution : rien d'autre que les noms que
l'énoncé fixe (boutique, vitrine, caisse, publicite, relance, le Secret
vitrine-tls, la ConfigMap diagnostic). Le Gateway est retrouvé par sa classe
(cilium) et son listener HTTPS sur 443, quel que soit son nom.

Faits mesurés le 2026-11-18 sur ce cluster, Cilium 1.20.5, qui fondent les
messages : un Gateway sans pool d'adresses reste Programmed=False
(AddressNotAssigned) ; une politique L7 qui n'autorise pas l'entité ingress
coupe le Gateway (curl 000) ; Hubble ne montre les flux L7 refusés que dans
l'agent du nœud du Pod qui reçoit.
"""

from __future__ import annotations

import base64
import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "boutique"
HOTE = "vitrine.formation.test"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CA = "/tmp/dsoxlab-ca-epreuve-n6.crt"  # noqa: S108 -- fichier jetable du test, sur le nœud
BUDGET_S = 90
PAS_S = 5


@pytest.fixture(scope="module")
def host():
    h = lab_host(lab_target_host("net-cp.lab"))
    h.run(f"sudo {KUBECTL} -n {NS} get configmap ca-boutique -o jsonpath='{{.data.ca\\.crt}}' > {CA}")
    return h


def _kubectl(host, args: str):
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str) -> dict:
    rc, sortie, _ = _kubectl(host, f"{args} -o json")
    return json.loads(sortie) if rc == 0 and sortie else {}


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _condition(conditions: list | None, type_: str) -> tuple[str, str]:
    for c in conditions or []:
        if c.get("type") == type_:
            return c.get("status", ""), c.get("reason", "")
    return "", ""


def _gateway(host) -> dict:
    """Le Gateway de classe cilium de boutique qui porte un listener HTTPS 443."""
    for gw in _json(host, f"-n {NS} get gateways.gateway.networking.k8s.io").get("items", []):
        spec = gw.get("spec", {})
        if spec.get("gatewayClassName") == "cilium" and any(
            ln.get("protocol") == "HTTPS" and ln.get("port") == 443 for ln in spec.get("listeners") or []
        ):
            return gw
    return {}


def _adresse(host) -> str:
    gw = _gateway(host)
    adresses = gw.get("status", {}).get("addresses") or []
    return adresses[0].get("value", "") if adresses else ""


def _adresse_requise(host) -> str:
    ip = _adresse(host)
    if not ip:
        pytest.fail(message(
            en="No Gateway of class cilium with an address in boutique: E1 says why.",
            fr="Aucun Gateway de classe cilium avec une adresse dans boutique : E1 dit pourquoi.",
        ))
    return ip


def _https(host, ip: str, methode: str = "GET", hote: str = HOTE) -> tuple[str, str]:
    """(code, corps) d'une requête HTTPS par le Gateway, TLS vérifié contre la CA."""
    res = host.run(
        f"curl -s -m 8 --cacert {CA} --resolve {HOTE}:443:{ip} -X {methode} "
        f"-H 'Host: {hote}' https://{HOTE}/ -w '|%{{http_code}}'"
    )
    corps, _, code = res.stdout.rpartition("|")
    return code.strip(), corps.strip()


def _depuis(host, pod: str, methode: str = "GET") -> tuple[int, str]:
    """(code de sortie de curl, code HTTP) d'une requête du Pod vers la vitrine."""
    res = host.run(
        f"sudo {KUBECTL} -n {NS} exec {pod} -- curl -s -m 5 -o /dev/null -X {methode} "
        "-w '%{http_code}' http://vitrine/"
    )
    return res.rc, res.stdout.strip()


# ----------------------------------------------------------------------
# E1. Un Gateway de classe cilium est programmé, avec une adresse.
# ----------------------------------------------------------------------
def test_e1_un_gateway_cilium_est_programme(host):
    gw = _attendre(lambda: _gateway(host), lambda g: _condition(
        g.get("status", {}).get("conditions"), "Programmed")[0] == "True")
    assert gw, message(
        en="No Gateway of class cilium with an HTTPS listener on port 443 in boutique.",
        fr="Aucun Gateway de classe cilium avec un listener HTTPS sur le port 443 dans boutique.",
    )
    statut, raison = _condition(gw.get("status", {}).get("conditions"), "Programmed")
    assert statut == "True" and _adresse(host), message(
        en=f"The Gateway {gw['metadata']['name']} is not programmed: Programmed={statut or 'absent'} "
        f"({raison or 'no reason'}).",
        fr=f"Le Gateway {gw['metadata']['name']} n'est pas programmé : Programmed={statut or 'absent'} "
        f"({raison or 'sans raison'}).",
    )


# ----------------------------------------------------------------------
# E2. Le listener HTTPS présente le certificat de la vitrine.
# ----------------------------------------------------------------------
def test_e2_le_listener_https_presente_le_certificat_de_la_vitrine(host):
    ip = _adresse_requise(host)
    attendu = host.run(
        f"sudo {KUBECTL} -n {NS} get secret vitrine-tls -o jsonpath='{{.data.tls\\.crt}}'"
        " | base64 -d | openssl x509 -noout -fingerprint -sha256"
    ).stdout.strip().split("=", 1)[-1]

    def presente() -> str:
        res = host.run(
            f"echo | timeout 10 openssl s_client -connect {ip}:443 -servername {HOTE} 2>/dev/null"
            " | openssl x509 -noout -fingerprint -sha256"
        )
        return res.stdout.strip().split("=", 1)[-1] if "=" in res.stdout else ""

    vu = _attendre(presente, lambda v: v == attendu, budget=60)
    assert vu == attendu, message(
        en=f"On {ip}:443 with the name {HOTE}, the listener presents {vu or 'nothing'}, not the certificate "
        "of the Secret vitrine-tls.",
        fr=f"Sur {ip}:443 avec le nom {HOTE}, le listener présente {vu or 'rien'}, pas le certificat du "
        "Secret vitrine-tls.",
    )
    verif = host.run(
        f"echo | openssl s_client -connect {ip}:443 -servername {HOTE} -CAfile {CA} 2>/dev/null"
        " | grep -E 'Verify return code'"
    )
    assert "0 (ok)" in verif.stdout, message(
        en=f"The presented certificate does not verify against the CA of ca-boutique: {verif.stdout.strip()}",
        fr=f"Le certificat présenté ne se vérifie pas contre la CA de ca-boutique : {verif.stdout.strip()}",
    )


# ----------------------------------------------------------------------
# E3. La route mène à la vitrine, et seulement pour son nom.
# ----------------------------------------------------------------------
def test_e3_la_route_mene_a_la_vitrine_et_seulement_pour_son_nom(host):
    ip = _adresse_requise(host)
    code, corps = _attendre(lambda: _https(host, ip), lambda v: v[1] == "vitrine", budget=60)
    assert corps == "vitrine", message(
        en=f"https://{HOTE}/ through the Gateway answers code {code or 'none'}, body {corps!r}: no route "
        "sends this name to the Service vitrine.",
        fr=f"https://{HOTE}/ par le Gateway répond le code {code or 'aucun'}, corps {corps!r} : aucune route "
        "n'envoie ce nom vers le Service vitrine.",
    )
    code_autre, _ = _https(host, ip, hote="autre.formation.test")
    assert code_autre == "404", message(
        en=f"A request for another name (Host: autre.formation.test) answers {code_autre}, expected 404: the "
        "route must be limited to its hostname.",
        fr=f"Une requête pour un autre nom (Host: autre.formation.test) répond {code_autre}, attendu 404 : la "
        "route doit se limiter à son nom d'hôte.",
    )


# ----------------------------------------------------------------------
# E4 (bloquant). Par le Gateway, GET passe et POST est refusé.
# ----------------------------------------------------------------------
def test_e4_par_le_gateway_get_passe_et_post_est_refuse(host):
    ip = _adresse_requise(host)
    get = _attendre(lambda: _https(host, ip), lambda v: v[0] == "200", budget=45)
    assert get[0] == "200", message(
        en=f"GET / through the Gateway answers {get[0] or 'nothing'}. If it worked before your network policy, "
        "the policy also cuts the Gateway: its traffic arrives with a reserved identity of Cilium.",
        fr=f"GET / par le Gateway répond {get[0] or 'rien'}. Si ça marchait avant votre politique réseau, elle "
        "coupe aussi le Gateway : son trafic arrive avec une identité réservée de Cilium.",
    )
    post = _https(host, ip, methode="POST")
    assert post[0] == "403", message(
        en=f"POST / through the Gateway answers {post[0] or 'nothing'}, expected 403: writing must be refused "
        "at the HTTP level, for the Gateway's traffic too.",
        fr=f"POST / par le Gateway répond {post[0] or 'rien'}, attendu 403 : l'écriture doit être refusée au "
        "niveau HTTP, pour le trafic du Gateway aussi.",
    )


# ----------------------------------------------------------------------
# E5. caisse lit sans écrire, publicite est coupée.
# ----------------------------------------------------------------------
def test_e5_caisse_lit_sans_ecrire_et_publicite_est_coupee(host):
    lecture = _attendre(lambda: _depuis(host, "caisse"), lambda v: v[1] == "200", budget=45)
    ecriture = _depuis(host, "caisse", "POST")
    assert lecture[1] == "200" and ecriture[1] == "403", message(
        en=f"From caisse, GET / answers {lecture[1] or 'nothing'} and POST / answers {ecriture[1] or 'nothing'}: "
        "expected 200 and 403.",
        fr=f"Depuis caisse, GET / répond {lecture[1] or 'rien'} et POST / répond {ecriture[1] or 'rien'} : "
        "attendu 200 et 403.",
    )
    rc, code = _depuis(host, "publicite")
    assert rc != 0 and code in ("", "000"), message(
        en=f"publicite still reaches the vitrine (HTTP {code}): it must be cut at the network level, not "
        "only refused at the HTTP level.",
        fr=f"publicite atteint encore la vitrine (HTTP {code}) : elle doit être coupée au niveau réseau, pas "
        "seulement refusée au niveau HTTP.",
    )


# ----------------------------------------------------------------------
# E6 (bloquant). Chaque agent chiffre en WireGuard.
# ----------------------------------------------------------------------
def test_e6_chaque_agent_chiffre_en_wireguard(host):
    agents = [p["metadata"]["name"] for p in _json(host, "-n kube-system get pods -l k8s-app=cilium").get("items", [])]
    assert len(agents) == 3, message(
        en=f"{len(agents)} Cilium agent(s) found, expected 3.",
        fr=f"{len(agents)} agent(s) Cilium trouvé(s), attendu 3.",
    )
    lignes = {}
    for a in agents:
        _, sortie, _ = _kubectl(host, f"-n kube-system exec {a} -c cilium-agent -- cilium-dbg status")
        lignes[a] = next((ligne for ligne in sortie.splitlines() if ligne.startswith("Encryption:")), "absente")
    mauvais = {a: ligne for a, ligne in lignes.items() if "Wireguard" not in ligne or "Peers: 2" not in ligne}
    assert not mauvais, message(
        en=f"Not every agent encrypts with WireGuard towards its two peers: {mauvais}",
        fr=f"Les agents ne chiffrent pas tous en WireGuard vers leurs deux pairs : {mauvais}",
    )


# ----------------------------------------------------------------------
# E7. Le diagnostic nomme la requête que la politique refuse à relance.
# ----------------------------------------------------------------------
def _requete_de_relance(host) -> tuple[str, str]:
    pod = _json(host, f"-n {NS} get pod relance")
    commande = " ".join((pod.get("spec", {}).get("containers") or [{}])[0].get("command") or [])
    trouve = re.search(r"echo ([A-Za-z0-9+/=]+) \| base64 -d", commande)
    if not trouve:
        return "", ""
    boucle = base64.b64decode(trouve.group(1)).decode()
    m = re.search(r"-X (\w+) http://vitrine(/\S*);", boucle)
    return (m.group(1), m.group(2)) if m else ("", "")


def test_e7_le_diagnostic_nomme_la_requete_refusee(host):
    methode, chemin = _requete_de_relance(host)
    if not methode:
        pytest.fail(message(
            en="The Pod relance is missing or was changed: run dsoxlab reset.",
            fr="Le Pod relance manque ou a été modifié : lancez dsoxlab reset.",
        ))
    cm = _json(host, f"-n {NS} get configmap diagnostic").get("data", {})
    assert cm, message(
        en="No ConfigMap diagnostic in boutique, keys methode and chemin.",
        fr="Aucune ConfigMap diagnostic dans boutique, clés methode et chemin.",
    )
    lu = ((cm.get("methode") or "").strip().upper(), (cm.get("chemin") or "").strip())
    assert lu == (methode, chemin), message(
        en=f"The diagnostic names {lu[0] or '?'} {lu[1] or '?'}, which is not the request your policy refuses "
        "to relance. Hubble shows the refused HTTP flows, in the agent of the right node.",
        fr=f"Le diagnostic nomme {lu[0] or '?'} {lu[1] or '?'}, qui n'est pas la requête que votre politique "
        "refuse à relance. Hubble montre les flux HTTP refusés, dans l'agent du bon nœud.",
    )
