"""test_functional.py : ckad-troubleshoot-crashloop

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Un test par Pod, chacun avec la même exigence : Running, prêt, et un
compteur de redémarrages qui ne bouge plus entre deux lectures à quinze
secondes d'écart. C'est cet intervalle qui prouve la stabilité : un Pod
« Running » au moment de la lecture peut être entre deux morts. Pour
oom-killed, la limite de mémoire est lue en plus.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host, nom: str) -> dict:
    res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get pod {nom} -o json")
    assert res.rc == 0, f"Aucun Pod {nom} dans {NAMESPACE} : il se recrée avec le même nom."
    return json.loads(res.stdout)


def _stable(host, nom: str, cause: str) -> dict:
    pod, statut = {}, {}
    for _ in range(12):
        pod = _pod(host, nom)
        statut = (pod["status"].get("containerStatuses") or [{}])[0]
        if pod["status"].get("phase") == "Running" and statut.get("ready"):
            break
        time.sleep(5)
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    derniere = (statut.get("lastState") or {}).get("terminated") or {}
    assert pod["status"].get("phase") == "Running" and statut.get("ready"), (
        f"{nom} est en phase {pod['status'].get('phase')!r}, raison {raison}, dernière "
        f"mort : {derniere.get('reason')} code {derniere.get('exitCode')}. {cause}"
    )
    avant = statut.get("restartCount", 0)
    time.sleep(15)
    apres = (_pod(host, nom)["status"].get("containerStatuses") or [{}])[0].get("restartCount", 0)
    assert apres == avant, (
        f"{nom} a redémarré pendant l'observation, {avant} puis {apres} : il tourne "
        f"quelques secondes et meurt à nouveau. {cause}"
    )
    return pod


# ----------------------------------------------------------------------
# 1. bad-command : une commande qui existe et reste en vie.
# ----------------------------------------------------------------------
def test_bad_command_tourne(host):
    _stable(host, "bad-command",
            "Le conteneur ne trouve pas sa commande : le message de sortie du dernier "
            "état terminé le dit. Donnez-lui une commande qui existe dans l'image, "
            "et qui ne se termine pas.")


# ----------------------------------------------------------------------
# 2. missing-env : la variable exigée est là.
# ----------------------------------------------------------------------
def test_missing_env_tourne(host):
    pod = _stable(host, "missing-env",
                  "Le conteneur exige une variable et sort si elle manque : ses logs, avec "
                  "--previous, disent laquelle. Elle se déclare sous env dans le Pod.")
    variables = {e.get("name") for e in pod["spec"]["containers"][0].get("env") or []}
    assert "APP_MODE" in variables, (
        f"missing-env tourne, mais sans APP_MODE dans son env : {sorted(variables) or 'aucune'}. "
        "Il ne fallait pas retirer le contrôle, mais fournir la variable."
    )


# ----------------------------------------------------------------------
# 3. oom-killed : une limite qui suffit, et plus de mort par le noyau.
# ----------------------------------------------------------------------
def test_oom_killed_tourne_avec_une_limite_suffisante(host):
    pod = _stable(host, "oom-killed",
                  "Le kubelet rapporte OOMKilled dans le dernier état terminé : le noyau "
                  "tue nginx dès qu'il dépasse sa limite de mémoire. Relevez la limite.")
    limites = (pod["spec"]["containers"][0].get("resources") or {}).get("limits") or {}
    memoire = str(limites.get("memory", ""))
    octets = 0
    if memoire.endswith("Mi"):
        octets = int(memoire[:-2]) * 1024 * 1024
    elif memoire.endswith("Gi"):
        octets = int(memoire[:-2]) * 1024 * 1024 * 1024
    elif memoire.isdigit():
        octets = int(memoire)
    assert octets >= 64 * 1024 * 1024, (
        f"La limite de mémoire de oom-killed vaut {memoire!r}, attendu au moins 64Mi. "
        "Retirer la limite fait tourner le Pod, mais la consigne est de la relever."
    )
