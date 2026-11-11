"""test_functional.py : ckad-troubleshoot-missing-configmap

Ces tests lisent le relevé de la cause et sa date, la ConfigMap créée, le Pod
broken-app comparé à celui que le setup a posé (uid mémorisé), puis la page
que l'application sert. Un test vérifie un seul état demandé par l'énoncé.

La cause doit être consignée AVANT la réparation : le relevé est comparé à la
date de création de la ConfigMap.

Tous échouent avant le travail : le relevé et la ConfigMap n'existent pas, et
broken-app reste bloqué. L'attente du Pod Running ne s'ouvre que si la
ConfigMap existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "broken-app"
CONFIGMAP = "app-settings"
MEMOIRE = "/var/lib/dsoxlab/troubleshoot-missing-configmap.json"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
#: Ce qui dit la cause : la ConfigMap nommée, et le fait qu'elle manque.
MANQUE = re.compile(r"not found|absent|introuvable|manqu|missing|n'existe pas|inexistant", re.IGNORECASE)
ATTENTE = 90
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _pret(pod: dict) -> bool:
    statut = (pod.get("status", {}).get("containerStatuses") or [{}])[0]
    return pod.get("status", {}).get("phase") == "Running" and bool(statut.get("ready"))


def _pod_debloque(host) -> dict | None:
    pod = _json(host, f"-n {NS} get pod {POD}")
    if pod is None or _json(host, f"-n {NS} get configmap {CONFIGMAP}") is None:
        return pod
    fin = time.monotonic() + ATTENTE
    while not _pret(pod) and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _json(host, f"-n {NS} get pod {POD}") or pod
    return pod


# ----------------------------------------------------------------------
# 1. La cause est consignée, avant la réparation.
# ----------------------------------------------------------------------
def test_la_cause_est_consignee_avant_la_reparation(host):
    chemin = f"{_maison(host)}/{POD}/cause.txt"
    f = host.file(chemin)
    contenu = f.content_string if f.exists else ""
    assert CONFIGMAP in contenu and MANQUE.search(contenu), message(
        en=f"~/{POD}/cause.txt does not say why {POD} is blocked: what it waits for, by its name, and that "
        "it is missing. The events of the Pod tell it.",
        fr=f"~/{POD}/cause.txt ne dit pas pourquoi {POD} est bloqué : ce qu'il attend, par son nom, et que "
        "cela manque. Les events du Pod le racontent.",
    )
    cm = _json(host, f"-n {NS} get configmap {CONFIGMAP}")
    if cm is not None:
        creee = datetime.fromisoformat(cm["metadata"]["creationTimestamp"].replace("Z", "+00:00")).timestamp()
        ecrit = int(host.check_output(f"stat -c %Y {chemin}"))
        assert ecrit <= creee, message(
            en=f"The cause was written, or rewritten, after the repair: ~/{POD}/cause.txt is more recent than "
            "the ConfigMap. The diagnosis comes first, then the file is left untouched.",
            fr=f"La cause a été écrite, ou réécrite, après la réparation : ~/{POD}/cause.txt est plus récent "
            "que la ConfigMap. Le diagnostic vient d'abord, puis on ne touche plus au fichier.",
        )


# ----------------------------------------------------------------------
# 2. La ConfigMap porte la configuration attendue.
# ----------------------------------------------------------------------
def test_la_configmap_porte_la_configuration_attendue(host):
    cm = _json(host, f"-n {NS} get configmap {CONFIGMAP}")
    data = (cm or {}).get("data") or {}
    assert "mode=production" in data.get("settings.conf", ""), message(
        en=f"The {CONFIGMAP} ConfigMap does not carry a settings.conf key containing the line "
        f"mode=production (keys found: {sorted(data) if cm else 'no ConfigMap'}).",
        fr=f"La ConfigMap {CONFIGMAP} ne porte pas de clé settings.conf contenant la ligne mode=production "
        f"(clés trouvées : {sorted(data) if cm else 'aucune ConfigMap'}).",
    )


# ----------------------------------------------------------------------
# 3. broken-app tourne, sans avoir été recréé.
# ----------------------------------------------------------------------
def test_broken_app_tourne_sans_avoir_ete_recree(host):
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset ckad-troubleshoot-missing-configmap.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset ckad-troubleshoot-missing-configmap.",
        ))
    pod = _pod_debloque(host)
    meme = pod is not None and pod["metadata"]["uid"] == json.loads(res.stdout)["uid"]
    identite_fr = "est celui que le lab a posé" if meme else "n'est plus celui que le lab a posé"
    assert meme and _pret(pod), message(
        en=f"{POD} is {'the one the lab installed' if meme else 'no longer the one the lab installed'} and "
        f"{'runs' if pod and _pret(pod) else 'does not run'}. Expected: the same Pod, Running and ready. "
        "Kubernetes retries on its own as soon as what was missing appears.",
        fr=f"{POD} {identite_fr} et {'tourne' if pod and _pret(pod) else 'ne tourne pas'}. Attendu : le même "
        "Pod, Running et prêt. Kubernetes réessaie tout seul dès que ce qui manquait apparaît.",
    )


# ----------------------------------------------------------------------
# 4. L'application sert sa configuration.
# ----------------------------------------------------------------------
def test_l_application_sert_sa_configuration(host):
    pod = _pod_debloque(host)
    ip = (pod or {}).get("status", {}).get("podIP")
    res = host.run(f"curl -sS -m 5 http://{ip}/") if ip else None
    assert res is not None and res.rc == 0 and "mode=production" in res.stdout, message(
        en=f"{POD} does not serve its configuration over HTTP: it copies /config/settings.conf into its page at "
        "startup, and its page does not show mode=production.",
        fr=f"{POD} ne sert pas sa configuration en HTTP : il recopie /config/settings.conf dans sa page au "
        "démarrage, et sa page ne montre pas mode=production.",
    )
