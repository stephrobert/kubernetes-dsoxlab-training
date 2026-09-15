"""test_functional.py : ckad-probes-all-types

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. Les deux premières lisent les sondes dans la définition
du Pod ; la troisième lit son état, et c'est elle qui prouve que les sondes
trouvent ce qu'elles cherchent : une sonde vers un mauvais chemin laisserait
un manifeste complet et un Pod jamais Ready, ou relancé en boucle.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
POD = "probed-app"
PORT = 80
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, f"Aucun Pod {POD} dans {NAMESPACE}."
    return json.loads(res.stdout)


def _conteneur(host) -> dict:
    return _pod(host)["spec"]["containers"][0]


def _http_sur_le_port(sonde: dict, nom: str) -> None:
    http = sonde.get("httpGet")
    assert http, f"La sonde {nom} n'est pas de type httpGet : {list(sonde) or 'vide'}. Un serveur web se sonde en HTTP."
    assert str(http.get("port")) in (str(PORT), "http"), (
        f"La sonde {nom} vise le port {http.get('port')!r} : nginx écoute sur {PORT}."
    )


# ----------------------------------------------------------------------
# 1. Les trois sondes existent, en HTTP sur le port du serveur.
# ----------------------------------------------------------------------
def test_les_trois_sondes_sont_declarees(host):
    c = _conteneur(host)
    ports = [p.get("containerPort") for p in c.get("ports") or []]
    assert PORT in ports, f"Le conteneur ne déclare pas le port {PORT} : ports {ports}."
    for nom in ("startupProbe", "livenessProbe", "readinessProbe"):
        assert c.get(nom), (
            f"Aucune sonde {nom} sur le conteneur. Les trois se déclarent au niveau "
            "du conteneur, chacune avec son propre bloc."
        )
        _http_sur_le_port(c[nom], nom)


# ----------------------------------------------------------------------
# 2. La sonde de démarrage tolère une minute d'échecs.
# ----------------------------------------------------------------------
def test_la_sonde_de_demarrage_tolere_un_demarrage_lent(host):
    sonde = _conteneur(host)["startupProbe"]
    periode = sonde.get("periodSeconds", 10)
    echecs = sonde.get("failureThreshold", 3)
    tolerance = periode * echecs
    assert tolerance >= 60, (
        f"La sonde de démarrage abandonne après {echecs} échecs à {periode} s, soit "
        f"{tolerance} s : une application qui met une minute à démarrer serait tuée "
        "avant d'avoir répondu. La tolérance est le produit failureThreshold "
        "multiplié par periodSeconds."
    )


# ----------------------------------------------------------------------
# 3. La preuve : Ready, sans redémarrage.
# ----------------------------------------------------------------------
def test_le_pod_est_ready_sans_redemarrage(host):
    pod, pret, redemarrages = {}, "Unknown", 0
    for _ in range(18):
        pod = _pod(host)
        conditions = {c["type"]: c["status"] for c in pod["status"].get("conditions") or []}
        pret = conditions.get("Ready", "Unknown")
        statut = (pod["status"].get("containerStatuses") or [{}])[0]
        redemarrages = statut.get("restartCount", 0)
        if pret == "True":
            break
        time.sleep(5)
    assert pod["status"].get("phase") == "Running", f"Le Pod est en phase {pod['status'].get('phase')!r}."
    assert pret == "True", (
        f"Le Pod est Running mais Ready = {pret} après 90 s : la sonde de disponibilité, "
        "ou celle de démarrage, échoue. Un mauvais chemin, un mauvais port : "
        "kubectl describe pod raconte chaque échec dans ses events."
    )
    assert redemarrages == 0, (
        f"Le conteneur a redémarré {redemarrages} fois : la sonde de vivacité le tue. "
        "Elle vise un chemin ou un port où nginx ne répond pas."
    )
