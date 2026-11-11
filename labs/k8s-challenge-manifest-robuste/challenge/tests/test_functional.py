"""test_functional.py : k8s-challenge-manifest-robuste

Challenge du module « Déployer ses applications ». Ces tests lisent l'état du
cluster « lab », le dossier ~/expedition/ et la cause consignée. Un test
vérifie un seul état demandé par le cahier des charges.

Trois états sont bloquants (exam_blocking_checks) : l'application disponible
sur son digest, ses sondes avec des Pods Ready sans redémarrage, et la cause de
la panne consignée avant la réparation.

Tous échouent avant le travail : expedition ne contient que le Pod etiquettes
en panne, et ~/expedition/ est vide. Une attente ne s'ouvre que si l'objet
attendu existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import shlex
import time
from datetime import datetime

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "expedition"
APP = "colis"
PROD, DEV = f"prod-{APP}", f"dev-{APP}"
IMAGE = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
LIMITE_MEMOIRE = "128Mi"
MEMOIRE = "/var/lib/dsoxlab/challenge-manifest-robuste.json"
CRONJOB, JOB, CASSE, CONFIG = "purge-colis", "inventaire", "etiquettes", "etiquettes-config"
MANQUE = re.compile(r"not found|absent|introuvable|manqu|missing|n'existe pas|inexistant|CreateContainerConfigError",
                    re.IGNORECASE)
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _disponible(d: dict) -> bool:
    s = d.get("status") or {}
    voulus = d["spec"].get("replicas", 1)
    return s.get("observedGeneration") == d["metadata"]["generation"] \
        and s.get("updatedReplicas") == voulus and s.get("availableReplicas") == voulus


def _deploiement(host, nom: str) -> dict | None:
    d = _json(host, f"-n {NS} get deployment {nom}")
    fin = time.monotonic() + ATTENTE
    while d is not None and not _disponible(d) and time.monotonic() < fin:
        time.sleep(PAS)
        d = _json(host, f"-n {NS} get deployment {nom}") or d
    return d


def _pods(host, d: dict) -> list[dict]:
    selecteur = ",".join(f"{k}={v}" for k, v in d["spec"]["selector"].get("matchLabels", {}).items())
    return [p for p in (_json(host, f"-n {NS} get pods -l {selecteur}") or {}).get("items", [])
            if not p["metadata"].get("deletionTimestamp")]


def _est_l_image(image: str | None) -> bool:
    """Même dépôt et même digest que l'image demandée ; le tag est facultatif."""
    if not image or "@" not in image:
        return False
    nom, digest = image.split("@", 1)
    nom = nom.removeprefix("docker.io/library/")
    return digest == IMAGE.split("@")[1] and nom.split(":")[0] == "nginx" \
        and (":" not in nom or nom.split(":")[1] == "1.30.5")


def _sidecars(spec: dict) -> list[dict]:
    return [c for c in spec.get("initContainers") or [] if c.get("restartPolicy") == "Always"]


def _sonde_80(c: dict, nom: str) -> bool:
    sonde = (c.get(nom) or {}).get("httpGet") or {}
    ports = {p.get("name"): p.get("containerPort") for p in c.get("ports") or []}
    port = sonde.get("port")
    return (ports.get(port, port) if isinstance(port, str) else port) == 80


def _sans_env(gabarit: dict) -> dict:
    """Le template d'un Pod, sans son label env : ce qui doit rester identique."""
    labels = {k: v for k, v in (gabarit["metadata"].get("labels") or {}).items() if k != "env"}
    return {**gabarit, "metadata": {**gabarit["metadata"], "labels": labels}}


def _absent(nom: str) -> str:
    return message(en=f"No Deployment {nom} in {NS}.", fr=f"Aucun Deployment {nom} dans {NS}.")


# ----------------------------------------------------------------------
# 1. L'application est disponible sur son image, par digest. BLOQUANT.
# ----------------------------------------------------------------------
def test_prod_colis_a_ses_trois_replicas_disponibles_sur_le_digest(host):
    d = _deploiement(host, PROD)
    assert d is not None, _absent(PROD)
    images = [c.get("image") for c in d["spec"]["template"]["spec"]["containers"]]
    s = d.get("status") or {}
    assert d["spec"].get("replicas") == 3 and _disponible(d) and _est_l_image(images[0]), message(
        en=f"{PROD} runs {images[0]!r} with {s.get('availableReplicas', 0)} available replica(s) out of "
        f"{d['spec'].get('replicas')}. Expected 3 available, on the image of the requirements referred to by digest.",
        fr=f"{PROD} tourne en {images[0]!r} avec {s.get('availableReplicas', 0)} réplica(s) disponible(s) sur "
        f"{d['spec'].get('replicas')}. Attendu 3 disponibles, sur l'image du cahier des charges référencée par digest.",
    )


# ----------------------------------------------------------------------
# 2. Init container terminé avant le démarrage, sidecar natif qui relaie.
# ----------------------------------------------------------------------
def test_init_container_et_sidecar_natif_relaient_les_journaux(host):
    d = _deploiement(host, PROD)
    assert d is not None, _absent(PROD)
    spec = d["spec"]["template"]["spec"]
    ordinaires = [c["name"] for c in spec.get("initContainers") or [] if c.get("restartPolicy") != "Always"]
    sidecars = [c["name"] for c in _sidecars(spec)]
    pods = [p for p in _pods(host, d) if p["status"].get("phase") == "Running"]
    assert ordinaires and sidecars and pods, message(
        en=f"{PROD} needs an ordinary init container and a native sidecar (found: init {ordinaires or 'none'}, "
        f"sidecar {sidecars or 'none'}), and a running Pod.",
        fr=f"{PROD} doit porter un init container ordinaire et un sidecar natif (trouvé : init "
        f"{ordinaires or 'aucun'}, sidecar {sidecars or 'aucun'}), et un Pod en marche.",
    )
    pod = pods[0]
    etats = {s["name"]: s.get("state") or {} for s in pod["status"].get("initContainerStatuses") or []}
    fini = (etats.get(ordinaires[0]) or {}).get("terminated") or {}
    principal = ((pod["status"].get("containerStatuses") or [{}])[0].get("state") or {}).get("running") or {}
    avant = fini.get("reason") == "Completed" and fini.get("finishedAt", "9") <= principal.get("startedAt", "0")
    jeton = f"suivi-{int(time.time())}"
    nom = pod["metadata"]["name"]
    host.run(f"{ADMIN} -n {NS} exec {nom} -c {sidecars[0]} -- wget -q -O /dev/null -T 3 http://127.0.0.1/{jeton}")
    time.sleep(3)
    logs = host.run(f"{ADMIN} -n {NS} logs {nom} -c {sidecars[0]} --tail=100").stdout
    init_fr = "s'est terminé avant le démarrage" if avant else "ne s'est pas terminé avant le démarrage"
    assert avant and jeton in logs, message(
        en=f"In {nom}, the init container {'completed before the start' if avant else 'did not complete before the start'}, "
        f"and the sidecar {'passes on' if jeton in logs else 'does not pass on'} the lines the application writes. "
        "A request to the application must appear in the sidecar's logs, through a shared volume.",
        fr=f"Dans {nom}, l'init container {init_fr}, et le sidecar {'relaie' if jeton in logs else 'ne relaie pas'} "
        "les lignes que l'application écrit. Une requête à l'application doit apparaître dans les logs du sidecar, "
        "par un volume partagé.",
    )


# ----------------------------------------------------------------------
# 3. Chaque conteneur déclare requests et limits, limite mémoire demandée.
# ----------------------------------------------------------------------
def test_chaque_conteneur_declare_requests_et_limits(host):
    d = _json(host, f"-n {NS} get deployment {PROD}")
    assert d is not None, _absent(PROD)
    spec = d["spec"]["template"]["spec"]
    tous = spec["containers"] + _sidecars(spec)
    sans = [c["name"] for c in tous
            if not ((c.get("resources") or {}).get("requests") and (c.get("resources") or {}).get("limits"))]
    limite = ((spec["containers"][0].get("resources") or {}).get("limits") or {}).get("memory")
    assert not sans and limite == LIMITE_MEMOIRE, message(
        en=f"Containers without requests or limits: {sans or 'none'}; memory limit of the application: {limite!r}, "
        f"expected {LIMITE_MEMOIRE}.",
        fr=f"Conteneurs sans requests ou sans limits : {sans or 'aucun'} ; limite de mémoire de l'application : "
        f"{limite!r}, attendu {LIMITE_MEMOIRE}.",
    )


# ----------------------------------------------------------------------
# 4. Trois sondes sur le port 80, Pods Ready sans redémarrage. BLOQUANT.
# ----------------------------------------------------------------------
def test_trois_sondes_sur_le_port_80_et_pods_ready_sans_redemarrage(host):
    d = _deploiement(host, PROD)
    assert d is not None, _absent(PROD)
    c = d["spec"]["template"]["spec"]["containers"][0]
    sondes = {n: _sonde_80(c, n) for n in ("startupProbe", "livenessProbe", "readinessProbe")}
    pods = _pods(host, d)
    redemarrages = sum(s.get("restartCount", 0) for p in pods for s in p["status"].get("containerStatuses") or [])
    prets = [p for p in pods if any(x.get("type") == "Ready" and x.get("status") == "True"
                                    for x in p["status"].get("conditions") or [])]
    assert all(sondes.values()) and pods and len(prets) == len(pods) and redemarrages == 0, message(
        en=f"Probes on port 80 over HTTP: {sondes}; {len(prets)} Ready Pod(s) out of {len(pods)}, {redemarrages} "
        "restart(s). Expected the three probes, every Pod Ready, no restart.",
        fr=f"Sondes HTTP sur le port 80 : {sondes} ; {len(prets)} Pod(s) Ready sur {len(pods)}, {redemarrages} "
        "redémarrage(s). Attendu les trois sondes, chaque Pod Ready, aucun redémarrage.",
    )


# ----------------------------------------------------------------------
# 5. Le CronJob de nettoyage est planifié comme demandé.
# ----------------------------------------------------------------------
def test_le_cronjob_purge_colis_est_planifie_comme_demande(host):
    cj = _json(host, f"-n {NS} get cronjob {CRONJOB}")
    spec = (cj or {}).get("spec") or {}
    vu = (spec.get("schedule", "").split(), spec.get("successfulJobsHistoryLimit"),
          spec.get("failedJobsHistoryLimit"), spec.get("concurrencyPolicy"))
    constat_fr = f"a pour planning, historique et concurrence {vu}" if cj else "n'a pas été créé"
    assert vu == (["0", "3", "*", "*", "*"], 2, 1, "Forbid"), message(
        en=f"{CRONJOB} has {'schedule, history and concurrency ' + str(vu) if cj else 'not been created'}. "
        "Expected every day at 3:00, two successful Jobs and one failed kept, never two runs at once.",
        fr=f"{CRONJOB} {constat_fr}. Attendu chaque jour à 3 h, deux Jobs réussis et un échoué conservés, jamais "
        "deux exécutions en même temps.",
    )


# ----------------------------------------------------------------------
# 6. Le Job de traitement est terminé, avec ses trois complétions.
# ----------------------------------------------------------------------
def test_le_job_inventaire_est_termine_avec_trois_completions(host):
    job = _json(host, f"-n {NS} get job {JOB}")
    fin = time.monotonic() + ATTENTE
    while job is not None and (job.get("status") or {}).get("succeeded", 0) < 3 and time.monotonic() < fin:
        time.sleep(PAS)
        job = _json(host, f"-n {NS} get job {JOB}") or job
    s, spec = (job or {}).get("status") or {}, (job or {}).get("spec") or {}
    assert spec.get("completions") == 3 and s.get("succeeded", 0) == 3, message(
        en=f"{JOB} asks for {spec.get('completions')!r} completion(s) and counts {s.get('succeeded', 0)} success(es). "
        "Expected 3 and 3.",
        fr=f"{JOB} demande {spec.get('completions')!r} complétion(s) et compte {s.get('succeeded', 0)} réussite(s). "
        "Attendu 3 et 3.",
    )


# ----------------------------------------------------------------------
# 7. dev et prod viennent d'une même base Kustomize.
# ----------------------------------------------------------------------
def test_dev_et_prod_viennent_d_une_meme_base(host):
    maison = _maison(host)
    bases = []
    for env in ("dev", "prod"):
        dossier = f"{maison}/expedition/overlays/{env}"
        f = host.file(f"{dossier}/kustomization.yaml")
        k = yaml.safe_load(f.content_string) if f.exists else {}
        cibles = set()
        for r in (k or {}).get("resources") or []:
            chemin = host.run(f"realpath -e {shlex.quote(dossier + '/' + str(r))}").stdout.strip()
            if chemin and host.file(f"{chemin}/kustomization.yaml").exists:
                cibles.add(chemin)
        bases.append(cibles)
    dev, prod = _json(host, f"-n {NS} get deployment {DEV}"), _json(host, f"-n {NS} get deployment {PROD}")
    identiques = False
    if dev and prod:
        a, b = dev["spec"]["template"], prod["spec"]["template"]
        # Un nom d'objet qui ne diffère que par le préfixe (une ConfigMap de la
        # base, par exemple) est une différence que le cahier des charges autorise.
        identiques = json.dumps(_sans_env(a), sort_keys=True) \
            == json.dumps(_sans_env(b), sort_keys=True).replace('"prod-', '"dev-') and a["metadata"].get("labels", {}).get("env") == "dev" \
            and b["metadata"].get("labels", {}).get("env") == "prod" and dev["spec"].get("replicas") == 1
    assert bases[0] & bases[1] and identiques, message(
        en="dev and prod do not come from one and the same base, or differ by more than their replicas, their name "
        "prefix and their env label (dev with 1 replica, prod with 3).",
        fr="dev et prod ne viennent pas d'une même base, ou diffèrent par plus que leurs réplicas, leur préfixe de "
        "noms et leur label env (dev à 1 réplica, prod à 3).",
    )


# ----------------------------------------------------------------------
# 8. Le cluster correspond au dossier versionné.
# ----------------------------------------------------------------------
def test_le_cluster_correspond_aux_overlays(host):
    maison = _maison(host)
    codes = {env: host.run(f"{ADMIN} diff -k {maison}/expedition/overlays/{env}").rc for env in ("dev", "prod")}
    assert codes == {"dev": 0, "prod": 0}, message(
        en=f"Comparing each overlay of ~/expedition/ with the cluster gives the codes {codes}: differences, or a "
        "comparison that cannot be made.",
        fr=f"Comparer chaque overlay de ~/expedition/ au cluster donne les codes {codes} : des différences, ou une "
        "comparaison impossible.",
    )


# ----------------------------------------------------------------------
# 9. La cause de la panne est consignée avant la réparation. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_cause_de_la_panne_est_consignee_avant_la_reparation(host):
    chemin = f"{_maison(host)}/expedition/cause.txt"
    f = host.file(chemin)
    contenu = f.content_string if f.exists else ""
    assert CONFIG in contenu and MANQUE.search(contenu), message(
        en=f"~/expedition/cause.txt does not say why {CASSE} does not start: what it looks for without finding "
        "it, by its name, and that it is missing.",
        fr=f"~/expedition/cause.txt ne dit pas pourquoi {CASSE} ne démarre pas : ce qu'il cherche sans le trouver, "
        "par son nom, et que cela manque.",
    )
    cm = _json(host, f"-n {NS} get configmap {CONFIG}")
    if cm is not None:
        creee = datetime.fromisoformat(cm["metadata"]["creationTimestamp"].replace("Z", "+00:00")).timestamp()
        assert int(host.check_output(f"stat -c %Y {chemin}")) <= creee, message(
            en="The cause was written, or rewritten, after the repair: the diagnosis comes first.",
            fr="La cause a été écrite, ou réécrite, après la réparation : le diagnostic vient d'abord.",
        )


# ----------------------------------------------------------------------
# 10. Le Pod en panne tourne, sans avoir été recréé.
# ----------------------------------------------------------------------
def test_etiquettes_tourne_sans_avoir_ete_recree(host):
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset k8s-challenge-manifest-robuste.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-challenge-manifest-robuste.",
        ))
    pod = _json(host, f"-n {NS} get pod {CASSE}")
    if pod is not None and _json(host, f"-n {NS} get configmap {CONFIG}") is not None:
        fin = time.monotonic() + ATTENTE
        while pod["status"].get("phase") != "Running" and time.monotonic() < fin:
            time.sleep(PAS)
            pod = _json(host, f"-n {NS} get pod {CASSE}") or pod
    meme = pod is not None and pod["metadata"]["uid"] == json.loads(res.stdout)["etiquettes_uid"]
    identite_fr = "est" if meme else "n'est plus"
    assert meme and pod["status"].get("phase") == "Running", message(
        en=f"{CASSE} {'is' if meme else 'is no longer'} the Pod the lab installed, and it "
        f"{'runs' if pod and pod['status'].get('phase') == 'Running' else 'does not run'}. Expected: the same Pod, "
        "Running. Kubernetes retries on its own once what was missing appears.",
        fr=f"{CASSE} {identite_fr} le Pod que le lab a posé, et il "
        f"{'tourne' if pod and pod['status'].get('phase') == 'Running' else 'ne tourne pas'}. Attendu : le même Pod, "
        "Running. Kubernetes réessaie tout seul dès que ce qui manquait apparaît.",
    )
