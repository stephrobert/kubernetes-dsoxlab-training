"""test_functional.py : k8s-challenge-composer-un-pod-multi-conteneurs

Ces tests lisent l'état du cluster et interrogent les Pods, jamais les
commandes tapées.

Le titre de la vitrine est tiré au sort à la préparation : la page servie
doit le porter, donc avoir été écrite par l'init container à partir de la
ConfigMap. Le relais des journaux se prouve par une requête au chemin tiré au
sort par le test lui-même, qui doit ressortir dans les journaux du sidecar
du Pod interrogé.

Deux tests sont bloquants, parce qu'ils portent le cœur du geste : la page
préparée par l'init container et servie par l'application, et le sidecar
natif qui relaie les accès.

Tous échouent avant le travail : le namespace ne contient que la ConfigMap.
"""

from __future__ import annotations

import json
import secrets
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "photo"
DEPLOIEMENT = "galerie"
INIT, SIDECAR, SERVEUR = "generer-page", "relais-journaux", "serveur"
PAGE, JOURNAUX = "page", "journaux"
LIMITE = "32Mi"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MEMOIRE = "/var/lib/dsoxlab/challenge-composer-un-pod-multi-conteneurs.json"
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def titre(host) -> str:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)["titre"]


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _deploiement(host) -> dict:
    d = _json(host, f"-n {NS} get deployment {DEPLOIEMENT}")
    assert d is not None, message(
        en=f"No Deployment {DEPLOIEMENT} in {NS}.",
        fr=f"Aucun Deployment {DEPLOIEMENT} dans {NS}.",
    )
    fin = time.monotonic() + ATTENTE
    while (d.get("status") or {}).get("availableReplicas", 0) < (d.get("spec") or {}).get("replicas", 1) \
            and time.monotonic() < fin:
        time.sleep(PAS)
        d = _json(host, f"-n {NS} get deployment {DEPLOIEMENT}") or d
    return d


def _pods(host, d: dict) -> list[dict]:
    selecteur = ",".join(f"{k}={v}" for k, v in d["spec"]["selector"].get("matchLabels", {}).items())
    pods = (_json(host, f"-n {NS} get pods -l {selecteur}") or {}).get("items", [])
    return [p for p in pods if p["status"].get("phase") == "Running" and not p["metadata"].get("deletionTimestamp")]


def _gabarit(d: dict) -> dict:
    return d["spec"]["template"]["spec"]


def _par_nom(conteneurs: list[dict]) -> dict[str, dict]:
    return {c["name"]: c for c in conteneurs or []}


def _page(host, ip: str, titre: str) -> str:
    """La page d'un Pod, réessayée 30 s : un Pod est déclaré prêt dès que ses
    conteneurs démarrent quand il n'a pas de sonde, avant que nginx écoute."""
    corps = ""
    fin = time.monotonic() + 30
    while time.monotonic() < fin:
        corps = host.run(f"curl -sS -m 5 http://{ip}/").stdout
        if titre in corps:
            break
        time.sleep(2)
    return corps


# ----------------------------------------------------------------------
# 1. La page préparée par l'init container est servie. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_page_preparee_par_l_init_container_est_servie(host, titre):
    d = _deploiement(host)
    gabarit = _gabarit(d)
    init = _par_nom(gabarit.get("initContainers")).get(INIT)
    assert init is not None and init.get("restartPolicy") is None, message(
        en=f"The Pods of {DEPLOIEMENT} have no ordinary init container {INIT} (one that runs to the end before "
        "the others start).",
        fr=f"Les Pods de {DEPLOIEMENT} n'ont pas d'init container ordinaire {INIT} (qui va jusqu'au bout avant "
        "le démarrage des autres).",
    )
    pods = _pods(host, d)
    assert pods, message(
        en=f"No running Pod for {DEPLOIEMENT}.",
        fr=f"Aucun Pod de {DEPLOIEMENT} ne tourne.",
    )
    for pod in pods:
        etats = {s["name"]: s.get("state") or {} for s in pod["status"].get("initContainerStatuses") or []}
        fini = (etats.get(INIT, {}).get("terminated") or {}).get("reason")
        corps = _page(host, pod["status"]["podIP"], titre)
        assert fini == "Completed" and titre in corps, message(
            en=f"Pod {pod['metadata']['name']}: {INIT} is {fini or 'not finished'}, and its home page "
            f"{'carries' if titre in corps else 'does not carry'} the title of the ConfigMap vitrine. Expected "
            "the page written by the init container from that title, served by the server.",
            fr=f"Pod {pod['metadata']['name']} : {INIT} est {fini or 'non terminé'}, et sa page d'accueil "
            f"{'porte' if titre in corps else 'ne porte pas'} le titre de la ConfigMap vitrine. Attendu : la "
            "page écrite par l'init container à partir de ce titre, servie par le serveur.",
        )


# ----------------------------------------------------------------------
# 2. Le sidecar natif relaie les accès du serveur. BLOQUANT.
# ----------------------------------------------------------------------
def test_le_sidecar_natif_relaie_les_acces(host):
    d = _deploiement(host)
    sidecar = _par_nom(_gabarit(d).get("initContainers")).get(SIDECAR)
    assert sidecar is not None and sidecar.get("restartPolicy") == "Always", message(
        en=f"{SIDECAR} is not a native sidecar: it must be declared among the init containers, and keep "
        "running alongside the server.",
        fr=f"{SIDECAR} n'est pas un sidecar natif : il doit être déclaré parmi les init containers, et tourner "
        "à côté du serveur.",
    )
    pods = _pods(host, d)
    assert pods, message(
        en=f"No running Pod for {DEPLOIEMENT}.",
        fr=f"Aucun Pod de {DEPLOIEMENT} ne tourne.",
    )
    pod = pods[0]
    chemin = f"/preuve-{secrets.token_hex(4)}"
    host.run(f"curl -s -m 5 -o /dev/null http://{pod['status']['podIP']}{chemin}")
    fin = time.monotonic() + 30
    vu = False
    while not vu and time.monotonic() < fin:
        journal = host.run(f"{ADMIN} -n {NS} logs {pod['metadata']['name']} -c {SIDECAR} --tail=50").stdout
        vu = chemin in journal
        if not vu:
            time.sleep(3)
    assert vu, message(
        en=f"A request to {chemin} on Pod {pod['metadata']['name']} does not show up in the logs of {SIDECAR} "
        "within 30 seconds. The server must write its access log into a volume that the sidecar reads.",
        fr=f"Une requête vers {chemin} sur le Pod {pod['metadata']['name']} n'apparaît pas dans les journaux de "
        f"{SIDECAR} en 30 secondes. Le serveur doit écrire son journal d'accès dans un volume que le sidecar lit.",
    )


# ----------------------------------------------------------------------
# 3. Le serveur lit la page sans pouvoir l'écrire.
# ----------------------------------------------------------------------
def test_le_serveur_lit_la_page_en_lecture_seule(host):
    gabarit = _gabarit(_deploiement(host))
    serveur = _par_nom(gabarit.get("containers")).get(SERVEUR) or {}
    init = _par_nom(gabarit.get("initContainers")).get(INIT) or {}
    m_serveur = {m["name"]: m for m in serveur.get("volumeMounts") or []}.get(PAGE) or {}
    m_init = {m["name"]: m for m in init.get("volumeMounts") or []}.get(PAGE) or {}
    assert m_serveur.get("readOnly") is True and m_init and not m_init.get("readOnly"), message(
        en=f"The volume {PAGE} must be written by {INIT} and mounted read-only in {SERVEUR}: seen "
        f"{m_init or 'absent'} in {INIT}, {m_serveur or 'absent'} in {SERVEUR}.",
        fr=f"Le volume {PAGE} doit être écrit par {INIT} et monté en lecture seule dans {SERVEUR} : vu "
        f"{m_init or 'absent'} dans {INIT}, {m_serveur or 'absent'} dans {SERVEUR}.",
    )


# ----------------------------------------------------------------------
# 4. Les journaux vivent dans un volume borné, partagé par deux conteneurs.
# ----------------------------------------------------------------------
def test_les_journaux_vivent_dans_un_volume_borne_et_partage(host):
    gabarit = _gabarit(_deploiement(host))
    volume = {v["name"]: v for v in gabarit.get("volumes") or []}.get(JOURNAUX) or {}
    limite = (volume.get("emptyDir") or {}).get("sizeLimit")
    lecteurs = sorted(c["name"] for c in (gabarit.get("containers") or []) + (gabarit.get("initContainers") or [])
                      if any(m["name"] == JOURNAUX for m in c.get("volumeMounts") or []))
    assert limite == LIMITE and lecteurs == sorted([SERVEUR, SIDECAR]), message(
        en=f"The volume {JOURNAUX} has the size limit {limite!r} and is mounted in {lecteurs or 'no container'}. "
        f"Expected a temporary volume capped at {LIMITE}, shared by {SERVEUR} and {SIDECAR} only.",
        fr=f"Le volume {JOURNAUX} a la limite de taille {limite!r} et il est monté dans "
        f"{lecteurs or 'aucun conteneur'}. Attendu : un volume temporaire plafonné à {LIMITE}, partagé par "
        f"{SERVEUR} et {SIDECAR} seulement.",
    )


# ----------------------------------------------------------------------
# 5. Deux réplicas prêts, sans redémarrage.
# ----------------------------------------------------------------------
def test_deux_replicas_prets_sans_redemarrage(host):
    d = _deploiement(host)
    pods = _pods(host, d)
    prets = [p for p in pods
             if all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
             and all(s.get("restartCount", 0) == 0 for s in p["status"].get("containerStatuses") or [])]
    assert d["spec"].get("replicas") == 2 and len(prets) == 2, message(
        en=f"{DEPLOIEMENT} asks for {d['spec'].get('replicas')} replica(s) and has {len(prets)} Pod(s) ready "
        "with no restart. Expected 2 and 2.",
        fr=f"{DEPLOIEMENT} demande {d['spec'].get('replicas')} réplica(s) et compte {len(prets)} Pod(s) prêt(s) "
        "sans redémarrage. Attendu 2 et 2.",
    )
