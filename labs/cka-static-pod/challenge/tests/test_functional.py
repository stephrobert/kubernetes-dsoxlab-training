"""test_functional.py : cka-static-pod

Ces tests lisent l'état du WORKER et du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le manifeste là où le kubelet du worker
le cherche, en partant de sa configuration et non d'un chemin supposé. La
deuxième lit le Pod miroir dans l'API et vérifie qu'il vient bien d'un
fichier : un Pod posé par kubectl run sous le même nom n'a ni l'annotation
config.source=file ni le Node pour propriétaire. La troisième veut le Pod
Running avec la bonne image et le bon port. La quatrième demande au runtime
du worker s'il exécute vraiment le conteneur, là où un Pod miroir seul ne
prouverait rien.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host

CONTROL_PLANE = "k8s-cp.lab"
WORKER = "k8s-w1.lab"
NAMESPACE = "default"
POD = "static-web"
MIROIR = f"{POD}-{WORKER}"
IMAGE = "nginx:1.27-alpine"
CONFIG_KUBELET = "/var/lib/kubelet/config.yaml"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def cp():
    return lab_host(CONTROL_PLANE)


@pytest.fixture(scope="module")
def worker():
    return lab_host(WORKER)


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _repertoire_statique(worker) -> str:
    res = worker.run(f"sudo cat {CONFIG_KUBELET}")
    assert res.rc == 0, f"Impossible de lire {CONFIG_KUBELET} sur {WORKER} : {res.stderr.strip()}"
    chemin = (yaml.safe_load(res.stdout) or {}).get("staticPodPath")
    assert chemin, (
        f"{CONFIG_KUBELET} n'a plus de staticPodPath : sans ce champ, le kubelet ne "
        "lit aucun manifeste. Il ne fallait pas le retirer."
    )
    return chemin


def _manifeste(worker) -> dict:
    repertoire = _repertoire_statique(worker)
    res = worker.run(f"sudo ls -1 {repertoire}")
    fichiers = [f for f in res.stdout.split() if f.endswith((".yaml", ".yml", ".json"))]
    for f in fichiers:
        contenu = worker.run(f"sudo cat {repertoire}/{f}").stdout
        try:
            doc = yaml.safe_load(contenu) or {}
        except yaml.YAMLError:
            continue
        if doc.get("kind") == "Pod" and (doc.get("metadata") or {}).get("name") == POD:
            return doc
    pytest.fail(
        f"Aucun manifeste de Pod nommé {POD} dans {repertoire} sur {WORKER} (fichiers vus : "
        f"{fichiers or 'aucun'}). C'est ce répertoire que le kubelet du worker surveille : "
        "un manifeste posé ailleurs, ou sur le control plane, n'est pas lu."
    )


# ----------------------------------------------------------------------
# 1. Le manifeste est là où le kubelet du worker le cherche.
# ----------------------------------------------------------------------
def test_le_manifeste_est_dans_le_repertoire_du_kubelet(worker):
    doc = _manifeste(worker)
    assert (doc["metadata"].get("labels") or {}).get("role") == "static", (
        "Le manifeste ne porte pas le label role=static demandé."
    )
    conteneurs = (doc.get("spec") or {}).get("containers") or []
    web = next((c for c in conteneurs if c.get("name") == "web"), None)
    assert web, f"Le manifeste n'a pas de conteneur nommé web (vus : {[c.get('name') for c in conteneurs]})."
    assert web.get("image") == IMAGE, f"Le conteneur web utilise {web.get('image')!r}, attendu {IMAGE!r}."
    ports = [p.get("containerPort") for p in web.get("ports") or []]
    assert 80 in ports, f"Le conteneur web n'expose pas le port 80 (ports déclarés : {ports})."


# ----------------------------------------------------------------------
# 2. Le Pod miroir est dans l'API, et il vient bien d'un fichier.
# ----------------------------------------------------------------------
def test_le_pod_miroir_vient_d_un_fichier(cp):
    res = None
    for _ in range(20):
        res = _kubectl(cp, f"-n {NAMESPACE} get pod {MIROIR} -o json")
        if res.rc == 0:
            break
        time.sleep(3)
    assert res is not None and res.rc == 0, (
        f"Aucun Pod {MIROIR} dans {NAMESPACE} après 60 s. Un Pod statique apparaît dans "
        "l'API sous le nom du Pod suffixé du nom du nœud. S'il n'apparaît pas, le kubelet "
        f"du worker n'a pas accepté le manifeste : journalctl -u kubelet sur {WORKER} dit pourquoi."
    )
    pod = json.loads(res.stdout)
    annotations = pod["metadata"].get("annotations") or {}
    assert annotations.get("kubernetes.io/config.source") == "file", (
        f"Le Pod {MIROIR} existe, mais son annotation kubernetes.io/config.source vaut "
        f"{annotations.get('kubernetes.io/config.source')!r} au lieu de 'file' : ce n'est pas "
        "un Pod miroir, c'est un Pod créé par l'API. Il fallait déposer un fichier sur le nœud."
    )
    proprietaires = [(o.get("kind"), o.get("name")) for o in pod["metadata"].get("ownerReferences") or []]
    assert ("Node", WORKER) in proprietaires, (
        f"Le Pod {MIROIR} n'a pas le Node {WORKER} pour propriétaire (vus : {proprietaires}). "
        "Un Pod miroir appartient au nœud dont le kubelet l'a créé."
    )
    assert pod["spec"].get("nodeName") == WORKER, (
        f"Le Pod tourne sur {pod['spec'].get('nodeName')!r}, attendu {WORKER} : le manifeste "
        "a été déposé sur le mauvais nœud."
    )


# ----------------------------------------------------------------------
# 3. Le Pod tourne, avec la bonne image et le bon port.
# ----------------------------------------------------------------------
def test_le_pod_statique_tourne(cp):
    phase, pret = "", False
    pod: dict = {}
    for _ in range(20):
        res = _kubectl(cp, f"-n {NAMESPACE} get pod {MIROIR} -o json")
        if res.rc == 0:
            pod = json.loads(res.stdout)
            phase = pod["status"].get("phase", "")
            statuts = pod["status"].get("containerStatuses") or []
            pret = bool(statuts) and all(s.get("ready") for s in statuts)
            if phase == "Running" and pret:
                break
        time.sleep(3)
    assert phase == "Running" and pret, (
        f"Le Pod {MIROIR} est en phase {phase!r}, prêt = {pret}, après 60 s. Le kubelet a lu "
        "le manifeste mais le conteneur ne tourne pas : kubectl describe pod dit ce qu'il attend."
    )
    images = [c.get("image") for c in pod["spec"]["containers"]]
    assert any(IMAGE in (i or "") for i in images), f"Le Pod utilise {images}, attendu {IMAGE}."
    ports = [p.get("containerPort") for c in pod["spec"]["containers"] for p in c.get("ports") or []]
    assert 80 in ports, f"Le Pod n'expose pas le port 80 (ports : {ports})."


# ----------------------------------------------------------------------
# 4. La preuve : le runtime du worker exécute le conteneur.
# ----------------------------------------------------------------------
def test_le_runtime_du_worker_execute_le_conteneur(worker):
    res = worker.run("sudo crictl pods -o json")
    assert res.rc == 0, f"crictl pods échoue sur {WORKER} : {res.stderr.strip()[:200]}"
    sandboxes = [
        p for p in json.loads(res.stdout).get("items") or []
        if p.get("metadata", {}).get("name") == MIROIR and p.get("state") == "SANDBOX_READY"
    ]
    assert sandboxes, (
        f"Le runtime de {WORKER} n'a aucun Pod {MIROIR} en SANDBOX_READY. L'API peut afficher "
        "un Pod que le nœud n'exécute pas ; ici c'est le conteneur réel qui compte."
    )
    res = worker.run(f"sudo crictl ps --pod {sandboxes[0]['id']} -o json")
    conteneurs = json.loads(res.stdout).get("containers") or []
    web = [c for c in conteneurs if c.get("metadata", {}).get("name") == "web" and c.get("state") == "CONTAINER_RUNNING"]
    assert web, (
        f"Le Pod {MIROIR} existe sur {WORKER} mais aucun conteneur web n'y est CONTAINER_RUNNING "
        f"(vus : {[(c.get('metadata', {}).get('name'), c.get('state')) for c in conteneurs]})."
    )
    # crictl ps ne donne que le digest de l'image ; le nom demandé est dans
    # userSpecifiedImage, ou dans crictl inspect, ou dans les tags du digest.
    noms = [web[0].get("image", {}).get("userSpecifiedImage", "")]
    inspection = worker.run(f"sudo crictl inspect -o json {web[0]['id']}")
    if inspection.rc == 0:
        statut_image = (json.loads(inspection.stdout).get("status") or {}).get("image") or {}
        noms += [statut_image.get("image", ""), statut_image.get("userSpecifiedImage", "")]
    digest = web[0].get("imageRef", "") or web[0].get("image", {}).get("image", "")
    images = worker.run("sudo crictl images -o json")
    if images.rc == 0:
        for i in json.loads(images.stdout).get("images") or []:
            if i.get("id") == digest:
                noms += i.get("repoTags") or []
    assert any(IMAGE in n for n in noms if n), (
        f"Le conteneur web tourne avec l'image {digest!r}, connue sous {[n for n in noms if n]}, "
        f"attendu {IMAGE}."
    )
