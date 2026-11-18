"""test_functional.py : k8s-challenge-reseau-avance

Quatre tests, un par état demandé par la fiche E-maitriser-les-flux-du-cluster.
Ils lisent le cluster, le journal du témoin et Hubble, jamais un fichier de
l'apprenant. Chacun porte un CONTRASTE, sans quoi il serait vrai avant le
travail ou réussi par une triche :

1. le Service répond, ET kube-proxy n'est pas revenu (remplacement intact) ;
2. panier passe, ET robot comme un Pod d'un autre namespace restent refusés
   (supprimer le refus par défaut ne suffit pas) ;
3. un Pod NEUF de facturation sort par net-w2, ET un Pod d'un autre namespace,
   sur le même nœud, sort toujours par son propre nœud (une politique qui
   attrape tout le cluster échoue) ;
4. le flux désigné est le bon, ET Hubble le voit encore refusé (retirer la
   politique pour « voir » le flux échoue).

La réponse attendue (jeton du catalogue, client refusé, port) est tirée au sort
par le setup, dans un fichier lisible par root seul sur le plan de contrôle.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
REFERENCE = "/var/lib/dsoxlab-labs/k8s-challenge-reseau-avance.ref"
JOURNAL_TEMOIN = "/var/log/dsoxlab-temoin-reseau.log"
BUSYBOX = "busybox:1.37@sha256:a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec"
PASSERELLE = "net-w2.lab"
NOEUD_W1 = "net-w1.lab"
NOEUD_API = "net-w1.lab"
BUDGET_S = 60
PAS_S = 4


@pytest.fixture(scope="module")
def cp():
    return lab_host(lab_target_host("net-cp.lab"))


@pytest.fixture(scope="module")
def temoin():
    return lab_host("k8s-cp.lab")


@pytest.fixture(scope="module")
def reference(cp) -> dict:
    lignes = cp.run(f"sudo cat {REFERENCE}").stdout.splitlines()
    return dict(ligne.split("=", 1) for ligne in lignes if "=" in ligne)


def _k(cp, args: str):
    res = cp.run(f"{KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(cp, args: str) -> dict:
    rc, sortie, _ = _k(cp, f"{args} -o json")
    if rc != 0 or not sortie:
        return {}
    return json.loads(sortie)


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _wget(cp, ns: str, pod: str, url: str) -> str:
    """Le corps rendu, ou « échec » : un refus de politique se voit en délai dépassé."""
    rc, sortie, _ = _k(cp, f"-n {ns} exec {pod} -- wget -qO- -T 3 {url}")
    return sortie if rc == 0 else "échec"


def _ip_du_noeud(cp, noeud: str) -> str:
    for a in _json(cp, f"get node {noeud}").get("status", {}).get("addresses", []):
        if a.get("type") == "InternalIP":
            return a.get("address", "")
    return ""


# ----------------------------------------------------------------------
# 1. Le Service catalogue répond, sans que kube-proxy revienne.
# ----------------------------------------------------------------------
def test_le_service_herite_repond_sans_kube_proxy(cp, reference):
    jeton = reference.get("jeton", "")
    assert jeton, message(
        en="The expected answer of the challenge is unreadable on net-cp.lab: run dsoxlab reset.",
        fr="La réponse attendue du challenge est illisible sur net-cp.lab : lancez dsoxlab reset.",
    )
    vu = _attendre(lambda: _wget(cp, "catalogue", "client", "http://catalogue.catalogue/"),
                   lambda s: s == jeton)
    assert vu == jeton, message(
        en=f"From catalogue/client, http://catalogue.catalogue/ answers « {vu} », expected the page served by "
        "the Pods of the Deployment catalogue. A Service that answers nobody has no endpoints: compare what it "
        "selects with what the Pods carry.",
        fr=f"Depuis catalogue/client, http://catalogue.catalogue/ répond « {vu} », attendu la page que servent "
        "les Pods du Deployment catalogue. Un Service qui ne répond à personne n'a pas d'endpoints : comparez ce "
        "qu'il sélectionne avec ce que portent les Pods.",
    )
    rc, _, _ = _k(cp, "-n kube-system get daemonset kube-proxy")
    remplacement = _k(cp, "-n kube-system get configmap cilium-config -o jsonpath='{.data.kube-proxy-replacement}'")[1]
    assert rc != 0 and remplacement == "true", message(
        en=f"kube-proxy must stay absent and Cilium must keep replacing it (kube-proxy DaemonSet "
        f"{'present' if rc == 0 else 'absent'}, kube-proxy-replacement={remplacement or 'absent'}). The Service "
        "is served by Cilium: reinstalling kube-proxy repairs nothing.",
        fr=f"kube-proxy doit rester absent et Cilium doit continuer à le remplacer (DaemonSet kube-proxy "
        f"{'présent' if rc == 0 else 'absent'}, kube-proxy-replacement={remplacement or 'absent'}). Le Service "
        "est servi par Cilium : réinstaller kube-proxy ne répare rien.",
    )


# ----------------------------------------------------------------------
# 2. panier atteint stock ; robot et les autres namespaces restent dehors.
# ----------------------------------------------------------------------
def test_panier_atteint_stock_et_lui_seul(cp):
    url = "http://stock.commandes/"
    panier = _attendre(lambda: _wget(cp, "boutique", "panier", url), lambda s: s == "stock")
    assert panier == "stock", message(
        en=f"boutique/panier does not reach {url} (read « {panier} »). The namespace commandes refuses all "
        "inbound traffic: open the flow from panier to stock, on port 80.",
        fr=f"boutique/panier n'atteint pas {url} (lu « {panier} »). Le namespace commandes refuse tout l'entrant : "
        "ouvrez le flux de panier vers stock, sur le port 80.",
    )
    robot = _wget(cp, "boutique", "robot", url)
    ailleurs = _wget(cp, "catalogue", "client", url)
    assert robot == "échec" and ailleurs == "échec", message(
        en=f"Only panier may reach stock: boutique/robot read « {robot} », catalogue/client read « {ailleurs} ». "
        "Both must still be refused: keep the default refusal, and open one flow, not a namespace.",
        fr=f"Seul panier doit atteindre stock : boutique/robot a lu « {robot} », catalogue/client a lu "
        f"« {ailleurs} ». Les deux doivent rester refusés : gardez le refus par défaut, et ouvrez un flux, pas un "
        "namespace.",
    )


# ----------------------------------------------------------------------
# 3. La sortie de facturation passe par net-w2, lue dans le journal du témoin.
# ----------------------------------------------------------------------
def test_la_sortie_de_facturation_passe_par_net_w2(cp, temoin):
    _, url, _ = _k(cp, "-n facturation get configmap temoin -o jsonpath='{.data.url}'")
    assert url, message(
        en="ConfigMap temoin unreadable in facturation: run dsoxlab reset.",
        fr="ConfigMap temoin illisible dans facturation : lancez dsoxlab reset.",
    )
    ip_passerelle, ip_w1 = _ip_du_noeud(cp, PASSERELLE), _ip_du_noeud(cp, NOEUD_W1)
    marque = os.urandom(4).hex()
    sonde = f"sonde-{marque}"
    # Un Pod NEUF du namespace, créé par le test : la politique doit viser le
    # namespace, pas seulement le Pod export qui existait déjà.
    _k(cp, f"-n facturation run {sonde} --image={BUSYBOX} --restart=Never "
           f"--overrides='{{\"spec\":{{\"nodeName\":\"{NOEUD_W1}\"}}}}' -- sleep 600")
    try:
        _k(cp, f"-n facturation wait --for=condition=Ready pod/{sonde} --timeout=120s")

        def source_vue(ns: str, pod: str, chemin: str) -> str:
            _k(cp, f"-n {ns} exec {pod} -- wget -qO- -T 5 {url}/{chemin}")
            ligne = temoin.run(f"sudo grep -F ' /{chemin} ' {JOURNAL_TEMOIN} | tail -1").stdout.split()
            return ligne[-1] if ligne else "absente du journal"

        compteur = iter(range(1000))
        vue = _attendre(lambda: source_vue("facturation", sonde, f"facturation-{marque}-{next(compteur)}"),
                        lambda s: s == ip_passerelle)
        assert vue == ip_passerelle, message(
            en=f"The witness logs a new Pod of facturation coming from {vue}, expected the exit node {PASSERELLE} "
            f"({ip_passerelle}). The policy must catch every Pod of the namespace, including one created after it.",
            fr=f"Le témoin note un Pod neuf de facturation arrivant de {vue}, attendu le nœud de sortie "
            f"{PASSERELLE} ({ip_passerelle}). La politique doit attraper tout Pod du namespace, y compris un Pod "
            "créé après elle.",
        )
        autre = source_vue("catalogue", "client", f"autre-{marque}")
        assert autre == ip_w1, message(
            en=f"The witness logs catalogue/client, on {NOEUD_W1} too, coming from {autre}, expected its own node "
            f"({ip_w1}): the policy must not catch the other namespaces.",
            fr=f"Le témoin note catalogue/client, lui aussi sur {NOEUD_W1}, arrivant de {autre}, attendu son propre "
            f"nœud ({ip_w1}) : la politique ne doit pas attraper les autres namespaces.",
        )
    finally:
        _k(cp, f"-n facturation delete pod {sonde} --wait=false")


# ----------------------------------------------------------------------
# 4. Le flux refusé est désigné, et Hubble le voit encore refusé.
# ----------------------------------------------------------------------
def _sans_namespace(valeur: str) -> str:
    return valeur.strip().split("/")[-1]


def _drops_vus(cp) -> list[dict]:
    pods = _json(cp, "-n kube-system get pods -l k8s-app=cilium").get("items", [])
    agent = next((p["metadata"]["name"] for p in pods
                  if p["spec"].get("nodeName") == NOEUD_API and p.get("status", {}).get("phase") == "Running"), "")
    if not agent:
        return []
    _, sortie, _ = _k(cp, f"-n kube-system exec {agent} -c cilium-agent -- "
                          "hubble observe --namespace paiement --verdict DROPPED --since 2m -o json")
    flux = []
    for ligne in sortie.splitlines():
        try:
            evenement = json.loads(ligne)
        except ValueError:
            continue
        if isinstance(evenement, dict) and isinstance(evenement.get("flow"), dict):
            flux.append(evenement["flow"])
    return flux


def test_le_flux_refuse_est_designe_et_vu_par_hubble(cp, reference):
    reponse = _json(cp, "-n paiement get configmap flux-refuse").get("data", {})
    lu = {cle: _sans_namespace(reponse.get(cle, "")) for cle in ("source", "destination", "port")}
    attendu = {"source": reference.get("refuse", ""), "destination": "api", "port": reference.get("port", "")}
    assert lu == attendu, message(
        en=f"ConfigMap flux-refuse of paiement reads source={lu['source'] or '?'}, destination="
        f"{lu['destination'] or '?'}, port={lu['port'] or '?'}: it does not name the flow the policy refuses. "
        "Keys source, destination and port, read from the flows Hubble marks DROPPED.",
        fr=f"La ConfigMap flux-refuse de paiement porte source={lu['source'] or '?'}, destination="
        f"{lu['destination'] or '?'}, port={lu['port'] or '?'} : elle ne désigne pas le flux que la politique "
        "refuse. Clés source, destination et port, lues dans les flux que Hubble marque DROPPED.",
    )

    def vu_refuse() -> bool:
        for f in _drops_vus(cp):
            port = str(((f.get("l4") or {}).get("TCP") or {}).get("destination_port", ""))
            if ((f.get("source") or {}).get("pod_name") == attendu["source"]
                    and (f.get("destination") or {}).get("pod_name") == "api" and port == attendu["port"]):
                return True
        return False

    assert _attendre(vu_refuse, bool), message(
        en=f"Hubble shows no DROPPED flow from {attendu['source']} to api on port {attendu['port']} in the last two "
        "minutes. The flow must still be refused: name it, do not open it.",
        fr=f"Hubble ne montre aucun flux DROPPED de {attendu['source']} vers api sur le port {attendu['port']} dans "
        "les deux dernières minutes. Le flux doit rester refusé : désignez-le, ne l'ouvrez pas.",
    )
