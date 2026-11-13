"""test_functional.py : k8s-detecter-les-api-depreciees

Quatre états, un par test :

1. ~/manifestes/rapport.txt nomme exactement les manifestes qui employaient une
   API retirée, un par ligne ;
2. les six manifestes du dépôt sont présents, et l'API server les accepte tous
   (dry-run côté serveur) : un fichier supprimé au lieu d'être migré ne passe
   pas ;
3. les quatre objets migrés existent dans le namespace migration ;
4. ils décrivent exactement ce que décrivaient les manifestes hérités.

Les quatre échouent sur l'état de départ : aucun rapport, quatre fichiers que
l'API refuse, un namespace vide.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS = "migration"
FICHIERS = ["deployment.yaml", "service.yaml", "pdb.yaml", "hpa.yaml", "cronjob.yaml", "ingress.yaml"]
EN_API_RETIREE = {"pdb.yaml", "hpa.yaml", "cronjob.yaml", "ingress.yaml"}
OBJETS = {"poddisruptionbudget": "web", "horizontalpodautoscaler": "web", "cronjob": "purge", "ingress": "web"}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _depot(host) -> str:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    return f"{maison}/manifestes"


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def test_le_rapport_liste_les_manifestes_en_api_retiree(host):
    rapport = host.file(f"{_depot(host)}/rapport.txt")
    assert rapport.exists, message(
        en="~/manifestes/rapport.txt is missing: it names the manifests that used a removed API.",
        fr="~/manifestes/rapport.txt est absent : il nomme les manifestes qui employaient une API retirée.",
    )
    nommes = {ligne.strip().split("/")[-1] for ligne in rapport.content_string.splitlines() if ligne.strip()}
    assert nommes == EN_API_RETIREE, message(
        en=f"The report names {sorted(nommes)}; it does not name exactly the manifests that used an API "
        "removed from Kubernetes.",
        fr=f"Le rapport nomme {sorted(nommes)} ; il ne nomme pas exactement les manifestes qui employaient une "
        "API retirée de Kubernetes.",
    )


def test_chaque_manifeste_est_accepte_par_l_api(host):
    depot = _depot(host)
    refuses = {}
    for nom in FICHIERS:
        if not host.file(f"{depot}/{nom}").exists:
            refuses[nom] = message(en="missing: migrate it, do not remove it", fr="absent : migrez-le, ne le retirez pas")
            continue
        res = host.run(f"{KUBECTL} apply --dry-run=server -f {depot}/{nom}")
        if res.rc != 0:
            refuses[nom] = res.stderr.strip().splitlines()[-1][:160] if res.stderr.strip() else "?"
    assert not refuses, message(
        en=f"Manifests the API server refuses: {refuses}.",
        fr=f"Manifestes que l'API server refuse : {refuses}.",
    )


def test_les_objets_migres_existent(host):
    absents = [f"{sorte}/{nom}" for sorte, nom in OBJETS.items() if _json(host, f"get {sorte} {nom}") is None]
    assert not absents, message(
        en=f"Objects missing from the {NS} namespace: {absents}. Once migrated, the manifests are applied.",
        fr=f"Objets absents du namespace {NS} : {absents}. Une fois migrés, les manifestes s'appliquent.",
    )


def test_les_objets_decrivent_ce_que_decrivaient_les_anciens(host):
    ecarts = []
    pdb = _json(host, "get poddisruptionbudget web") or {}
    if (pdb.get("spec") or {}).get("minAvailable") != 1 or \
            ((pdb.get("spec") or {}).get("selector") or {}).get("matchLabels") != {"app": "web"}:
        ecarts.append("PodDisruptionBudget web")
    hpa = (_json(host, "get horizontalpodautoscaler web") or {}).get("spec") or {}
    metriques = [(m.get("resource") or {}) for m in hpa.get("metrics") or []]
    if (hpa.get("minReplicas"), hpa.get("maxReplicas"), (hpa.get("scaleTargetRef") or {}).get("name")) != (2, 5, "web") \
            or not any(r.get("name") == "cpu" and (r.get("target") or {}).get("averageUtilization") == 70
                       for r in metriques):
        ecarts.append("HorizontalPodAutoscaler web")
    cj = (_json(host, "get cronjob purge") or {}).get("spec") or {}
    conteneurs = (((cj.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or [{}]
    if cj.get("schedule") != "15 3 * * *" or conteneurs[0].get("command") != ["sh", "-c", "echo purge"]:
        ecarts.append("CronJob purge")
    ing = (_json(host, "get ingress web") or {}).get("spec") or {}
    regles = ing.get("rules") or [{}]
    chemins = ((regles[0].get("http") or {}).get("paths")) or [{}]
    service = ((chemins[0].get("backend") or {}).get("service")) or {}
    if (regles[0].get("host"), chemins[0].get("path"), service.get("name"), (service.get("port") or {}).get("number")) \
            != ("web.migration.local", "/", "web", 80):
        ecarts.append("Ingress web")
    assert not ecarts, message(
        en=f"These objects no longer describe what their legacy manifest described: {ecarts}. A migration "
        "changes the API, not the intent: same values, same targets.",
        fr=f"Ces objets ne décrivent plus ce que décrivait leur manifeste hérité : {ecarts}. Une migration "
        "change l'API, pas l'intention : mêmes valeurs, mêmes cibles.",
    )
