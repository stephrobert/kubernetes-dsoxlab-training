"""Capturer le trafic de trois Pods et désigner la cause de chaque échec.

## La vérité vient du cluster, pas d'un fichier

Le setup tire les trois pannes au hasard. Le test les relit dans les objets du
namespace boutique, à chaque passage :

- le client appelle un nom qui n'est pas celui de son serveur : DNS ;
- le Service du serveur vise le port 5679, où rien n'écoute : refus ;
- une NetworkPolicy d'entrée protège le serveur : perte.

Cette relecture sert aussi de TÉMOIN : un client qui n'a plus exactement une
panne, ou dont les derniers appels réussissent, veut dire que quelque chose a
été réparé, et le diagnostic ne se note pas sur un objet réparé.

## Ce que la capture doit prouver

Une capture se lit sur le control plane avec `tcpdump -nn -r`. Elle doit
venir du bon Pod (ses paquets portent l'adresse ACTUELLE du Pod : une capture
d'un passage précédent porte une adresse qui n'existe plus), puis montrer la
signature de sa panne, mesurée le 2026-11-15 sur ce cluster :

- refus : un `[R.]` revient vers le client, aussitôt après son SYN ;
- perte : le même SYN (même port source, même numéro de séquence) repart au
  moins une fois, sans SYN-ACK ;
- DNS : des réponses `NXDomain` reviennent vers le client.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from urllib.parse import urlparse

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

NAMESPACE = "boutique"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
SERVEUR_DE = {"commandes": "catalogue", "factures": "paiement", "livraisons": "transport"}
SYNONYMES = {
    "refus": "refus", "refused": "refus", "refuse": "refus", "reset": "refus",
    "perte": "perte", "dropped": "perte", "drop": "perte", "lost": "perte",
    "dns": "dns",
}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict:
    res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return {}
    return json.loads(res.stdout)


def _pod(host, client: str) -> dict:
    pods = [p for p in _json(host, f"get pods -l app={client}").get("items", [])
            if p.get("status", {}).get("phase") == "Running" and not p["metadata"].get("deletionTimestamp")]
    assert len(pods) == 1, message(
        en=f"The client {client} must have exactly one running Pod, found {len(pods)}.",
        fr=f"Le client {client} doit avoir exactement un Pod en marche, trouvé {len(pods)}.",
    )
    return pods[0]


def _panne(host, client: str) -> str:
    """La panne que les objets du cluster portent pour ce client, ou une explication."""
    serveur = SERVEUR_DE[client]
    deploiement = _json(host, f"get deployment {client}")
    conteneurs = deploiement.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    env = {e.get("name"): e.get("value") for c in conteneurs for e in c.get("env", [])}
    cible = urlparse(env.get("CIBLE") or "").hostname or ""
    pannes = []
    if cible != serveur:
        pannes.append("dns")
    service = _json(host, f"get service {serveur}")
    ports = [p.get("targetPort") for p in service.get("spec", {}).get("ports", [])]
    if 5679 in ports:
        pannes.append("refus")
    if _json(host, f"get networkpolicy {serveur}-entree"):
        pannes.append("perte")
    return pannes[0] if len(pannes) == 1 else f"altérée ({', '.join(pannes) or 'aucune panne'})"


def _captures(host) -> str:
    """Le répertoire ~/captures de la SESSION de l'apprenant.

    testinfra joue ses commandes sous sudo : `~` y vaut /root. Le compte de la
    session est celui que sudo nomme dans SUDO_USER (ansible, mesuré le
    2026-11-16), et c'est dans son répertoire que l'apprenant écrit.
    """
    session = host.run("printf %s \"${SUDO_USER:-$(id -un)}\"").stdout.strip()
    return f"/home/{session}/captures"


def _paquets(host, client: str) -> list[str]:
    chemin = f"{_captures(host)}/{client}.pcap"
    res = host.run(f"test -s {chemin} && tcpdump -nn -r {chemin} 2>/dev/null")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"{chemin} is missing, empty or not a capture that tcpdump -r can read. Write it "
        "with tcpdump -w, then bring it back to the control plane.",
        fr=f"{chemin} est absent, vide, ou n'est pas une capture lisible par tcpdump -r. "
        "Écrivez-la avec tcpdump -w, puis rapatriez-la sur le control plane.",
    )
    return res.stdout.splitlines()


def test_chaque_capture_vient_du_bon_pod(host):
    for client in SERVEUR_DE:
        pod = _pod(host, client)
        ip = pod["status"]["podIP"]
        noeud = pod["spec"].get("nodeName")
        lignes = _paquets(host, client)
        du_pod = [ligne for ligne in lignes if f" {ip}." in ligne or f" {ip} " in ligne]
        assert len(du_pod) >= 3, message(
            en=f"~/captures/{client}.pcap holds {len(du_pod)} packet(s) of the Pod {client} "
            f"({ip}, on {noeud}) out of {len(lignes)}. Capture on the interface of THIS Pod, "
            "on its node, after the last `dsoxlab run`.",
            fr=f"~/captures/{client}.pcap contient {len(du_pod)} paquet(s) du Pod {client} "
            f"({ip}, sur {noeud}) sur {len(lignes)}. Capturez sur l'interface de CE Pod, sur "
            "son nœud, après le dernier `dsoxlab run`.",
        )


def _signature(lignes: list[str], ip: str, panne: str) -> bool:
    ip_re = re.escape(ip)
    if panne == "refus":
        return any(re.search(rf"> {ip_re}\.\d+: Flags \[R", ligne) for ligne in lignes)
    if panne == "perte":
        syn = Counter(
            m.groups() for ligne in lignes
            if (m := re.search(rf"IP {ip_re}\.(\d+) > \S+: Flags \[S\], seq (\d+)", ligne))
        )
        repondu = any(re.search(rf"> {ip_re}\.\d+: Flags \[S\.\]", ligne) for ligne in lignes)
        return bool(syn) and max(syn.values()) >= 2 and not repondu
    return any(re.search(rf"> {ip_re}\.\d+: \d+ NXDomain", ligne) for ligne in lignes)


PANNES = ("refus", "perte", "dns")


def test_chaque_capture_montre_la_panne(host):
    for client in SERVEUR_DE:
        panne = _panne(host, client)
        assert panne in PANNES, message(
            en=f"The failure of {client} was changed ({panne}): nothing is to be repaired. "
            "Run `dsoxlab reset` to start again.",
            fr=f"La panne de {client} a été modifiée ({panne}) : rien n'est à réparer. "
            "Lancez `dsoxlab reset` pour repartir.",
        )
        ip = _pod(host, client)["status"]["podIP"]
        lignes = _paquets(host, client)
        # Le message ne nomme pas la signature attendue : il donnerait la cause.
        assert _signature(lignes, ip, panne), message(
            en=f"~/captures/{client}.pcap does not show the packets that prove the failure "
            f"of {client}. Capture long enough to see several whole calls (15 s at least), "
            "with no filter: the DNS queries and the TCP packets both count.",
            fr=f"~/captures/{client}.pcap ne montre pas les paquets qui prouvent la panne de "
            f"{client}. Capturez assez longtemps pour voir plusieurs appels entiers (15 s au "
            "moins), sans filtre : les requêtes DNS comme les paquets TCP comptent.",
        )


def test_le_diagnostic_designe_la_bonne_cause(host):
    fichier = host.file(f"{_captures(host)}/diagnostic.yaml")
    assert fichier.exists, message(
        en="~/captures/diagnostic.yaml is missing: one line per client, `client: cause`, "
        "with refus, perte or dns.",
        fr="~/captures/diagnostic.yaml est absent : une ligne par client, `client: cause`, "
        "avec refus, perte ou dns.",
    )
    try:
        lu = yaml.safe_load(fichier.content_string) or {}
    except yaml.YAMLError as erreur:
        pytest.fail(message(
            en=f"~/captures/diagnostic.yaml is not valid YAML: {erreur}",
            fr=f"~/captures/diagnostic.yaml n'est pas un YAML valide : {erreur}",
        ))
    assert isinstance(lu, dict), message(
        en="~/captures/diagnostic.yaml must be a mapping: `client: cause`.",
        fr="~/captures/diagnostic.yaml doit être un dictionnaire : `client: cause`.",
    )
    for client in SERVEUR_DE:
        panne = _panne(host, client)
        assert panne in PANNES, message(
            en=f"The failure of {client} was changed ({panne}): the diagnosis is read on the "
            "failures as the setup left them. Run `dsoxlab reset`.",
            fr=f"La panne de {client} a été modifiée ({panne}) : le diagnostic se lit sur les "
            "pannes telles que le setup les a laissées. Lancez `dsoxlab reset`.",
        )
        journal = host.run(f"sudo {KUBECTL} -n {NAMESPACE} logs deployment/{client} --tail=3")
        assert journal.rc == 0 and "réussi" not in journal.stdout, message(
            en=f"The last calls of {client} succeed: its failure was repaired. "
            "Run `dsoxlab reset`.",
            fr=f"Les derniers appels de {client} réussissent : sa panne a été réparée. "
            "Lancez `dsoxlab reset`.",
        )
        donne = SYNONYMES.get(str(lu.get(client, "")).strip().lower())
        assert donne == panne, message(
            en=f"The diagnosis gives `{lu.get(client)}` for {client}. Read its capture again: "
            "which packets come back to the client, and which never do?",
            fr=f"Le diagnostic donne `{lu.get(client)}` pour {client}. Relisez sa capture : "
            "quels paquets reviennent vers le client, et lesquels ne reviennent jamais ?",
        )
