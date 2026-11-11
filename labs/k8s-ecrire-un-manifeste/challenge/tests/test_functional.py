"""test_functional.py : k8s-ecrire-un-manifeste

Ces tests lisent le manifeste ~/commandes/api.yaml, le soumettent à l'API en
--dry-run=server, puis lisent dans le cluster « lab » ce qu'il a créé et l'état
du Deployment rapport, dont le setup a mémorisé l'uid. Un test vérifie un seul
état demandé par l'énoncé.

Tous échouent avant le travail : le fichier n'existe pas, aucun objet api
n'existe et rapport tourne sur une image introuvable. Une attente ne s'ouvre
que si l'objet attendu existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "commandes"
MEMOIRE = "/var/lib/dsoxlab/ecrire-un-manifeste.json"
IMAGE = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
KINDS = {"ConfigMap", "Deployment", "Service"}
ATTENTE = 90
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _fichier(host) -> str:
    return f"{_maison(host)}/{NS}/api.yaml"


def _documents(host) -> list[dict]:
    f = host.file(_fichier(host))
    if not f.exists:
        return []
    try:
        return [d for d in yaml.safe_load_all(f.content_string) if isinstance(d, dict)]
    except yaml.YAMLError:
        return []


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _attendre(host, args: str, pret) -> dict | None:
    objet = _json(host, args)
    fin = time.monotonic() + ATTENTE
    while objet is not None and not pret(objet) and time.monotonic() < fin:
        time.sleep(PAS)
        objet = _json(host, args) or objet
    return objet


def _disponible(d: dict, voulus: int) -> bool:
    s = d.get("status") or {}
    return s.get("observedGeneration") == d["metadata"]["generation"] \
        and s.get("updatedReplicas") == voulus and s.get("availableReplicas") == voulus


# ----------------------------------------------------------------------
# 1. Un fichier multi-documents que le serveur accepte.
# ----------------------------------------------------------------------
def test_le_fichier_porte_les_trois_objets_et_le_serveur_l_accepte(host):
    kinds = {d.get("kind") for d in _documents(host)}
    assert kinds >= KINDS, message(
        en=f"~/{NS}/api.yaml does not hold a ConfigMap, a Deployment and a Service in one file "
        f"(kinds found: {sorted(k for k in kinds if k) or 'none'}).",
        fr=f"~/{NS}/api.yaml ne porte pas une ConfigMap, un Deployment et un Service dans un même "
        f"fichier (kinds trouvés : {sorted(k for k in kinds if k) or 'aucun'}).",
    )
    res = host.run(f"{ADMIN} apply --dry-run=server -f {_fichier(host)}")
    assert res.rc == 0, message(
        en=f"The API refuses ~/{NS}/api.yaml when it validates it: {res.stderr.strip()[:300]}",
        fr=f"L'API refuse ~/{NS}/api.yaml quand elle le valide : {res.stderr.strip()[:300]}",
    )


# ----------------------------------------------------------------------
# 2. Le namespace est nommé dans le fichier, et rien ne traîne dans default.
# ----------------------------------------------------------------------
def test_le_fichier_nomme_son_namespace_et_rien_n_est_dans_default(host):
    docs = [d for d in _documents(host) if d.get("kind") in KINDS]
    sans = [f"{d.get('kind')}/{(d.get('metadata') or {}).get('name')}" for d in docs
            if (d.get("metadata") or {}).get("namespace") != NS]
    assert docs and not sans, message(
        en=f"These objects of ~/{NS}/api.yaml do not name the {NS} namespace in the file itself: "
        f"{sans or 'no object at all'}. A manifest that relies on the current context lands "
        "wherever that context points.",
        fr=f"Ces objets de ~/{NS}/api.yaml ne nomment pas le namespace {NS} dans le fichier lui-même : "
        f"{sans or 'aucun objet'}. Un manifeste qui compte sur le contexte courant atterrit là où "
        "ce contexte pointe.",
    )
    egares = [k for k in ("deployment/api", "service/api", "configmap/api-config")
              if host.run(f"{ADMIN} -n default get {k}").rc == 0]
    assert not egares, message(
        en=f"Objects of the application landed in default: {egares}.",
        fr=f"Des objets de l'application ont atterri dans default : {egares}.",
    )


# ----------------------------------------------------------------------
# 3. Le Deployment api est disponible, sur l'image demandée.
# ----------------------------------------------------------------------
def test_api_a_deux_replicas_disponibles_sur_l_image_demandee(host):
    d = _attendre(host, f"-n {NS} get deployment api", lambda o: _disponible(o, 2))
    assert d is not None, message(
        en=f"No Deployment api in {NS}.",
        fr=f"Aucun Deployment api dans {NS}.",
    )
    image = d["spec"]["template"]["spec"]["containers"][0].get("image")
    s = d.get("status") or {}
    assert image == IMAGE and d["spec"].get("replicas") == 2 and _disponible(d, 2), message(
        en=f"api runs {image!r} with {s.get('availableReplicas', 0)} available replica(s) out of "
        f"{d['spec'].get('replicas')}. Expected 2 available, on the image of the requirements, "
        "pinned by digest.",
        fr=f"api tourne en {image!r} avec {s.get('availableReplicas', 0)} réplica(s) disponible(s) "
        f"sur {d['spec'].get('replicas')}. Attendu 2 disponibles, sur l'image du cahier des charges, "
        "épinglée par digest.",
    )


# ----------------------------------------------------------------------
# 4. Le Service api trouve les Pods.
# ----------------------------------------------------------------------
def test_le_service_api_trouve_les_deux_pods(host):
    tranches = _attendre(
        host, f"-n {NS} get endpointslices -l kubernetes.io/service-name=api",
        lambda o: sum(1 for t in o.get("items", []) for e in t.get("endpoints") or []
                      if (e.get("conditions") or {}).get("ready")) >= 2,
    )
    prets = sum(1 for t in (tranches or {}).get("items", []) for e in t.get("endpoints") or []
                if (e.get("conditions") or {}).get("ready"))
    svc = _json(host, f"-n {NS} get service api") or {}
    ports = [p.get("port") for p in (svc.get("spec") or {}).get("ports") or []]
    assert prets == 2 and 80 in ports, message(
        en=f"The api Service exposes the ports {ports or 'none'} and has {prets} ready endpoint(s), "
        "expected port 80 and 2 endpoints: its selector must match the labels of the Pods.",
        fr=f"Le Service api expose les ports {ports or 'aucun'} et a {prets} endpoint(s) prêt(s), "
        "attendu le port 80 et 2 endpoints : son selector doit correspondre aux labels des Pods.",
    )


# ----------------------------------------------------------------------
# 5. Le conteneur reçoit sa configuration de la ConfigMap.
# ----------------------------------------------------------------------
def test_le_conteneur_recoit_sa_configuration_de_api_config(host):
    d = _json(host, f"-n {NS} get deployment api") or {"spec": {"template": {"spec": {"containers": [{}]}}}}
    refs = [s["configMapRef"]["name"] for s in d["spec"]["template"]["spec"]["containers"][0].get("envFrom") or []
            if s.get("configMapRef")]
    cm = _json(host, f"-n {NS} get configmap api-config") or {}
    devise = (cm.get("data") or {}).get("DEVISE")
    assert "api-config" in refs and devise == "EUR", message(
        en=f"The api container does not receive DEVISE=EUR from the api-config ConfigMap through "
        f"envFrom (references: {refs or 'none'}, DEVISE: {devise!r}).",
        fr=f"Le conteneur d'api ne reçoit pas DEVISE=EUR de la ConfigMap api-config par envFrom "
        f"(références : {refs or 'aucune'}, DEVISE : {devise!r}).",
    )


# ----------------------------------------------------------------------
# 6. rapport est corrigé en place, sans avoir été recréé.
# ----------------------------------------------------------------------
def test_rapport_est_corrige_sans_avoir_ete_recree(host):
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset k8s-ecrire-un-manifeste.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-ecrire-un-manifeste.",
        ))
    uid_initial = json.loads(res.stdout)["rapport_uid"]
    d = _attendre(host, f"-n {NS} get deployment rapport", lambda o: _disponible(o, 3))
    assert d is not None and d["metadata"]["uid"] == uid_initial, message(
        en="The rapport Deployment is not the one the lab installed: it was deleted, or deleted "
        "then recreated. It had to be corrected in place.",
        fr="Le Deployment rapport n'est plus celui que le lab a posé : il a été supprimé, ou supprimé "
        "puis recréé. Il fallait le corriger en place.",
    )
    image = d["spec"]["template"]["spec"]["containers"][0].get("image")
    s = d.get("status") or {}
    assert image == IMAGE and d["spec"].get("replicas") == 3 and _disponible(d, 3), message(
        en=f"rapport runs {image!r} with {s.get('availableReplicas', 0)} available replica(s) out of "
        f"{d['spec'].get('replicas')}. Expected 3 available, on the image of the requirements.",
        fr=f"rapport tourne en {image!r} avec {s.get('availableReplicas', 0)} réplica(s) disponible(s) "
        f"sur {d['spec'].get('replicas')}. Attendu 3 disponibles, sur l'image du cahier des charges.",
    )
