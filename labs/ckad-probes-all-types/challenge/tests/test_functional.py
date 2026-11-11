"""test_functional.py : ckad-probes-all-types

Ces tests lisent la définition du Pod probed-app et son état. Un test vérifie
un seul état demandé par l'énoncé.

Une sonde se juge sur ce qu'elle interroge (HTTP, port 80, nommé ou non) et,
pour la sonde de démarrage, sur sa tolérance : failureThreshold multiplié par
periodSeconds, avec les défauts de Kubernetes quand un champ est omis (3 et
10 s, mesurés en 1.37 le 2026-11-11).

Tous échouent avant le travail : le Pod n'existe pas. L'attente du Pod Ready ne
s'ouvre que s'il existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "probed-app"
PORT = 80
IMAGE = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
TOLERANCE = 60
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} get pod {POD} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _conteneur(host) -> dict:
    pod = _pod(host)
    assert pod is not None, message(en=f"No Pod {POD} in {NS}.", fr=f"Aucun Pod {POD} dans {NS}.")
    return pod["spec"]["containers"][0]


def _sonde_http_sur_80(conteneur: dict, nom: str) -> bool:
    sonde = (conteneur.get(nom) or {}).get("httpGet") or {}
    ports = {p.get("name"): p.get("containerPort") for p in conteneur.get("ports") or []}
    port = sonde.get("port")
    port = ports.get(port, port) if isinstance(port, str) else port
    return port == PORT


# ----------------------------------------------------------------------
# 1. probed-app déclare son port 80, sur l'image demandée.
# ----------------------------------------------------------------------
def test_probed_app_declare_son_port_sur_l_image_demandee(host):
    c = _conteneur(host)
    ports = [p.get("containerPort") for p in c.get("ports") or []]
    assert c.get("image") == IMAGE and PORT in ports, message(
        en=f"{POD} runs {c.get('image')!r} and declares the ports {ports or 'none'}. Expected the image of the "
        "requirements, pinned by digest, and port 80 declared.",
        fr=f"{POD} tourne en {c.get('image')!r} et déclare les ports {ports or 'aucun'}. Attendu l'image du "
        "cahier des charges, épinglée par digest, et le port 80 déclaré.",
    )


# ----------------------------------------------------------------------
# 2. La sonde de démarrage tolère une minute de démarrage lent.
# ----------------------------------------------------------------------
def test_la_sonde_de_demarrage_tolere_une_minute(host):
    c = _conteneur(host)
    sonde = c.get("startupProbe") or {}
    tolerance = sonde.get("failureThreshold", 3) * sonde.get("periodSeconds", 10)
    assert _sonde_http_sur_80(c, "startupProbe") and tolerance >= TOLERANCE, message(
        en=f"The startup probe does not query port 80 over HTTP while tolerating at least {TOLERANCE}s of "
        f"consecutive failures (found: {sonde or 'no startup probe'}, tolerance {tolerance}s if declared).",
        fr=f"La sonde de démarrage n'interroge pas le port 80 en HTTP en tolérant au moins {TOLERANCE} s "
        f"d'échecs consécutifs (trouvé : {sonde or 'aucune sonde de démarrage'}, tolérance {tolerance} s si "
        "elle est déclarée).",
    )


# ----------------------------------------------------------------------
# 3. La sonde de vivacité interroge le port 80 en HTTP.
# ----------------------------------------------------------------------
def test_la_sonde_de_vivacite_interroge_le_port_80_en_http(host):
    c = _conteneur(host)
    assert _sonde_http_sur_80(c, "livenessProbe"), message(
        en=f"The liveness probe does not query port 80 over HTTP (found: {c.get('livenessProbe') or 'none'}).",
        fr=f"La sonde de vivacité n'interroge pas le port 80 en HTTP (trouvé : "
        f"{c.get('livenessProbe') or 'aucune'}).",
    )


# ----------------------------------------------------------------------
# 4. La sonde de disponibilité interroge le port 80 en HTTP.
# ----------------------------------------------------------------------
def test_la_sonde_de_disponibilite_interroge_le_port_80_en_http(host):
    c = _conteneur(host)
    assert _sonde_http_sur_80(c, "readinessProbe"), message(
        en=f"The readiness probe does not query port 80 over HTTP (found: {c.get('readinessProbe') or 'none'}).",
        fr=f"La sonde de disponibilité n'interroge pas le port 80 en HTTP (trouvé : "
        f"{c.get('readinessProbe') or 'aucune'}).",
    )


# ----------------------------------------------------------------------
# 5. probed-app est Ready, sans redémarrage.
# ----------------------------------------------------------------------
def _pret(pod: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (pod.get("status") or {}).get("conditions") or [])


def test_probed_app_est_ready_sans_redemarrage(host):
    pod = _pod(host)
    assert pod is not None, message(en=f"No Pod {POD} in {NS}.", fr=f"Aucun Pod {POD} dans {NS}.")
    fin = time.monotonic() + ATTENTE
    while not _pret(pod) and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _pod(host) or pod
    redemarrages = sum(s.get("restartCount", 0) for s in pod["status"].get("containerStatuses") or [])
    assert _pret(pod) and redemarrages == 0, message(
        en=f"{POD} is {'Ready' if _pret(pod) else 'not Ready'} after {ATTENTE}s, with {redemarrages} restart(s). "
        "A probe aimed at the wrong path or port fails silently: the Pod never becomes Ready, or restarts. "
        "Its events tell each failure.",
        fr=f"{POD} est {'Ready' if _pret(pod) else 'non Ready'} après {ATTENTE} s, avec {redemarrages} "
        "redémarrage(s). Une sonde qui vise un mauvais chemin ou un mauvais port échoue en silence : le Pod "
        "ne devient jamais Ready, ou redémarre. Ses événements racontent chaque échec.",
    )
