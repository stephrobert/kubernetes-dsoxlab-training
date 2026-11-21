"""test_functional.py : k8s-challenge-appliquer-et-verifier-ses-manifests

Ces tests lisent les fichiers de ~/annuaire et l'état du cluster kind « lab »,
et JOUENT le script de livraison. Ils ne lisent jamais les commandes tapées.

Le délai avant qu'un exemplaire neuf soit compté disponible est tiré au sort à
la préparation et écrit dans le cahier des charges : le champ d'API qui le
porte, l'apprenant le trouve lui-même. Ce délai rend aussi le dernier test
discriminant : un script qui applique sans attendre rend la main alors que la
production n'a encore aucun exemplaire disponible.

Deux exigences sont bloquantes, parce qu'elles portent le cœur du geste : deux
variantes construites depuis une même base, et une livraison qui attend la
disponibilité avant de rendre la main.

Tous échouent avant le travail : ~/annuaire ne contient que le cahier des
charges.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
MEMOIRE = "/var/lib/dsoxlab/challenge-appliquer-et-verifier-ses-manifests.json"
ANCIENNE = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
NOUVELLE = "nginx:1.31.2@sha256:b5a9a3cfc86b81dd6f1458d53f2ad2b559cc255653d2efd6cacee5636bf2066f"
VARIANTES = {"recette": ("annuaire-recette", 1), "production": ("annuaire-production", 3)}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


@pytest.fixture(scope="module")
def dossier(host) -> str:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    return f"{maison}/annuaire"


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


def _objets(host, ns: str, sorte: str) -> list[dict]:
    res = host.run(f"{ADMIN} -n {ns} get {sorte} -o json")
    return json.loads(res.stdout).get("items", []) if res.rc == 0 and res.stdout.strip() else []


def _deploiement(host, ns: str) -> dict:
    """Le Deployment dont les Pods servent le Service annuaire de `ns`."""
    services = [s for s in _objets(host, ns, "service") if s["metadata"]["name"] == "annuaire"]
    if not services:
        return {}
    selecteur = (services[0].get("spec") or {}).get("selector") or {}
    for d in _objets(host, ns, "deployment"):
        etiquettes = (((d.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {}
        if selecteur and all(etiquettes.get(k) == v for k, v in selecteur.items()):
            return d
    return {}


def _image(d: dict) -> str:
    conteneurs = ((d.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or [{}]
    return conteneurs[0].get("image", "")


# ----------------------------------------------------------------------
# 1. Deux variantes construites depuis une même base. BLOQUANT.
# ----------------------------------------------------------------------
def test_les_deux_variantes_se_construisent_depuis_une_base(host, dossier):
    ecarts = []
    for variante, (ns, replicas) in VARIANTES.items():
        rendu = host.run(f"kubectl kustomize {dossier}/{variante}")
        kustom = host.run(f"cat {dossier}/{variante}/kustomization.yaml").stdout
        if rendu.rc != 0:
            ecarts.append(f"{variante} : kubectl kustomize échoue ({rendu.stderr.strip()[:120]})")
            continue
        documents = [d for d in rendu.stdout.split("\n---\n") if d.strip()]
        sortes = [ligne.split(":", 1)[1].strip() for doc in documents for ligne in doc.splitlines()
                  if ligne.startswith("kind:")]
        if "../base" not in kustom:
            ecarts.append(f"{variante} ne part pas de ../base")
        if "Namespace" not in sortes or f"namespace: {ns}" not in rendu.stdout:
            ecarts.append(f"{variante} ne crée pas ou ne vise pas le namespace {ns}")
        if f"replicas: {replicas}" not in rendu.stdout:
            ecarts.append(f"{variante} ne demande pas {replicas} exemplaire(s)")
    assert not ecarts, message(
        en="The two variants are not built from one base: " + "; ".join(ecarts)
        + ". Expected ~/annuaire/base, and ~/annuaire/recette and ~/annuaire/production that start from it.",
        fr="Les deux variantes ne se construisent pas depuis une même base : " + "; ".join(ecarts)
        + ". Attendu ~/annuaire/base, et ~/annuaire/recette et ~/annuaire/production qui en partent.",
    )


# ----------------------------------------------------------------------
# 2. L'annuaire tourne dans les deux namespaces, joignable sur 8080.
# ----------------------------------------------------------------------
def test_l_annuaire_tourne_dans_les_deux_variantes(host):
    ecarts = []
    for ns, replicas in VARIANTES.values():
        services = [s for s in _objets(host, ns, "service") if s["metadata"]["name"] == "annuaire"]
        ports = [(p.get("port"), p.get("targetPort")) for s in services for p in s["spec"].get("ports", [])]
        d = _deploiement(host, ns)
        dispo = (d.get("status") or {}).get("availableReplicas", 0)
        if (8080, 80) not in ports:
            ecarts.append(f"{ns} : pas de Service annuaire 8080 vers 80 (vu {ports or 'rien'})")
        if dispo != replicas:
            ecarts.append(f"{ns} : {dispo} exemplaire(s) disponible(s), attendu {replicas}")
    assert not ecarts, message(
        en="The annuaire application does not run as specified: " + "; ".join(ecarts) + ".",
        fr="L'application annuaire ne tourne pas comme le cahier le demande : " + "; ".join(ecarts) + ".",
    )


# ----------------------------------------------------------------------
# 3. Le délai de disponibilité vient du cahier des charges.
# ----------------------------------------------------------------------
def test_le_delai_de_disponibilite_vient_du_cahier(host, memoire):
    vus = {ns: (_deploiement(host, ns).get("spec") or {}).get("minReadySeconds") for ns, _ in VARIANTES.values()}
    assert all(v == memoire["delai"] for v in vus.values()), message(
        en=f"The delay before a new copy counts as available is {vus}. Expected the delay of the specification, "
        "on both variants: kubectl explain finds the Deployment field that carries it.",
        fr=f"Le délai avant qu'un exemplaire neuf compte comme disponible vaut {vus}. Attendu le délai du "
        "cahier des charges, dans les deux variantes : kubectl explain trouve le champ du Deployment qui le porte.",
    )


# ----------------------------------------------------------------------
# 4. Les objets de production sont appliqués de façon déclarative.
# ----------------------------------------------------------------------
def test_les_objets_sont_appliques_de_facon_declarative(host):
    ns = VARIANTES["production"][0]
    d = _deploiement(host, ns)
    services = [s for s in _objets(host, ns, "service") if s["metadata"]["name"] == "annuaire"]

    def declaratif(o: dict) -> bool:
        meta = o.get("metadata") or {}
        if "kubectl.kubernetes.io/last-applied-configuration" in (meta.get("annotations") or {}):
            return True
        return any(m.get("operation") == "Apply" for m in meta.get("managedFields") or [])

    assert d and services and declaratif(d) and declaratif(services[0]), message(
        en="The production Deployment and Service were not applied declaratively: they carry neither the "
        "last-applied annotation of kubectl apply nor a server-side Apply operation. kubectl create builds "
        "an object, kubectl apply keeps it in line with its file.",
        fr="Le Deployment et le Service de production n'ont pas été appliqués de façon déclarative : ils ne "
        "portent ni l'annotation last-applied de kubectl apply, ni d'opération Apply côté serveur. kubectl "
        "create fabrique un objet, kubectl apply le garde aligné sur son fichier.",
    )


# ----------------------------------------------------------------------
# 5. La production est montée de version, et le diff l'a montré avant.
# ----------------------------------------------------------------------
def test_la_production_est_montee_et_le_diff_l_a_montre(host, dossier):
    prod = _image(_deploiement(host, VARIANTES["production"][0]))
    recette = _image(_deploiement(host, VARIANTES["recette"][0]))
    diff = host.run(f"cat {dossier}/diff-production.txt").stdout
    lignes = diff.splitlines()
    montre = any(ligne.startswith("-") and "1.30.5" in ligne for ligne in lignes) and \
        any(ligne.startswith("+") and "1.31.2" in ligne for ligne in lignes)
    assert prod == NOUVELLE and recette == ANCIENNE and montre, message(
        en=f"Production runs {prod or '?'}, acceptance {recette or '?'}, and ~/annuaire/diff-production.txt "
        f"{'shows' if montre else 'does not show'} the image change. Expected production on {NOUVELLE}, "
        "acceptance still on 1.30.5, and the output of kubectl diff saved BEFORE the change was applied.",
        fr=f"La production tourne en {prod or '?'}, la recette en {recette or '?'}, et "
        f"~/annuaire/diff-production.txt {'montre' if montre else 'ne montre pas'} le changement d'image. "
        f"Attendu la production en {NOUVELLE}, la recette toujours en 1.30.5, et la sortie de kubectl diff "
        "enregistrée AVANT d'appliquer le changement.",
    )


# ----------------------------------------------------------------------
# 6. La livraison attend la disponibilité avant de rendre la main. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_livraison_attend_la_disponibilite(host, dossier):
    script = f"{dossier}/livrer.sh"
    assert host.file(script).exists, message(
        en=f"No delivery script at {script}.",
        fr=f"Aucun script de livraison en {script}.",
    )
    ns, replicas = VARIANTES["production"]
    host.run(f"{ADMIN} delete namespace {ns} --wait=true --timeout=180s")
    res = host.run(f"cd {dossier} && timeout 300 bash {script} production < /dev/null")
    d = _deploiement(host, ns)
    dispo = (d.get("status") or {}).get("availableReplicas", 0)
    assert res.rc == 0 and dispo == replicas, message(
        en=f"After `livrer.sh production` on an empty cluster, the script exits with {res.rc} and production has "
        f"{dispo} available copy(ies) out of {replicas}. The script must not hand back before production is "
        f"available. Its output: {(res.stdout + res.stderr).strip()[-200:]}",
        fr=f"Après `livrer.sh production` sur un cluster vide, le script sort en {res.rc} et la production "
        f"compte {dispo} exemplaire(s) disponible(s) sur {replicas}. Le script ne doit pas rendre la main avant "
        f"que la production soit disponible. Sa sortie : {(res.stdout + res.stderr).strip()[-200:]}",
    )
