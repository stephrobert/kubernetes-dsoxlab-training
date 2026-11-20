"""test_functional.py : k8s-inspecter-et-restaurer-une-release-helm

Ces tests lisent l'état du CLUSTER et de Helm, jamais les commandes tapées. Le
setup laisse la release vitrine (chart podinfo) en échec : révision 1 saine en
6.15.0, révision 2 saine en 6.16.0 avec 2 réplicas, révisions 3 et 4 montées
en 6.17.0 avec une image introuvable.

L'apprenant cherche la dernière version 6.14 du chart (un filtre, plus la
dernière version tout court que la leçon montre), nomme les révisions en
échec, revient à la dernière révision saine, la 2, et non à la précédente,
qu'un rollback sans numéro viserait, et fait passer les tests du chart. Aucune
réponse n'est écrite ici : la version se recalcule par `helm search repo
--version`, les révisions en échec par `helm history`. Rien n'est vrai avant
le travail.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "helm-demo"
RELEASE = "vitrine"
HELM = "sudo helm --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _maison(host) -> str:
    return host.run('getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6').stdout.strip()


def _lire(host, nom: str) -> str:
    chemin = f"{_maison(host)}/vitrine/{nom}"
    res = host.run(f"cat {chemin}")
    assert res.rc == 0, message(
        en=f"No file {chemin}: write the answer there, on one line.",
        fr=f"Aucun fichier {chemin} : écrivez-y la réponse, sur une ligne.",
    )
    return res.stdout.strip()


def _historique(host) -> list[dict]:
    res = host.run(f"{HELM} history {RELEASE} -n {NAMESPACE} -o json")
    assert res.rc == 0, message(
        en=f"helm history {RELEASE} fails: {res.stderr.strip()}",
        fr=f"helm history {RELEASE} échoue : {res.stderr.strip()}",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. La dernière version 6.14 du chart, trouvée par une recherche filtrée.
# ----------------------------------------------------------------------
SERIE = "~6.14"


def test_la_derniere_version_du_chart_est_relevee(host):
    res = host.run("sudo -u \"${SUDO_USER:-$USER}\" -H helm search repo podinfo/podinfo "
                   f"--version '{SERIE}' -o json")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"helm search repo finds no podinfo chart: {res.stderr.strip()}",
        fr=f"helm search repo ne trouve aucun chart podinfo : {res.stderr.strip()}",
    )
    derniere = json.loads(res.stdout)[0]["version"]
    relevee = _lire(host, "derniere-version.txt")
    assert relevee == derniere, message(
        en=f"derniere-version.txt says {relevee!r}, but the latest 6.14 version of the podinfo chart is "
        f"{derniere}. helm search repo shows the latest version of all by default: the series is a filter.",
        fr=f"derniere-version.txt indique {relevee!r}, mais la dernière version 6.14 du chart podinfo est "
        f"{derniere}. helm search repo montre par défaut la dernière version de toutes : la série est un "
        "filtre.",
    )


# ----------------------------------------------------------------------
# 2. Les révisions en échec, lues dans l'historique.
# ----------------------------------------------------------------------
def test_les_revisions_en_echec_sont_nommees(host):
    echecs = {str(r["revision"]) for r in _historique(host) if r.get("status") == "failed"}
    assert echecs, message(
        en="The history no longer shows any failed revision: `dsoxlab reset` sets the situation back.",
        fr="L'historique ne montre plus aucune révision en échec : `dsoxlab reset` repose la situation.",
    )
    relevees = set(re.findall(r"\d+", _lire(host, "revisions-en-echec.txt")))
    assert relevees == echecs, message(
        en=f"revisions-en-echec.txt gives {sorted(relevees) or 'nothing'}; the failed revisions in helm "
        f"history are {', '.join(sorted(echecs))}. There may be more than one.",
        fr=f"revisions-en-echec.txt donne {sorted(relevees) or 'rien'} ; les révisions en échec dans helm "
        f"history sont {', '.join(sorted(echecs))}. Il peut y en avoir plusieurs.",
    )


# ----------------------------------------------------------------------
# 3. Le retour à la dernière révision saine.
# ----------------------------------------------------------------------
def test_la_release_est_revenue_a_la_revision_saine(host):
    historique = _historique(host)
    derniere = historique[-1]
    saines = [r["revision"] for r in historique if r.get("status") in ("deployed", "superseded")
              and "rollback" not in (r.get("description") or "").lower()]
    assert derniere.get("status") == "deployed" and "rollback" in (derniere.get("description") or "").lower(), message(
        en=f"The last revision is {derniere.get('revision')} ({derniere.get('status')}, "
        f"{derniere.get('description')!r}): expected a deployed rollback.",
        fr=f"La dernière révision est la {derniere.get('revision')} ({derniere.get('status')}, "
        f"{derniere.get('description')!r}) : attendu un rollback déployé.",
    )
    cible = derniere.get("description", "").split()[-1]
    assert saines and cible == str(max(saines)), message(
        en=f"The rollback goes back to revision {cible}; the last healthy revision before the failures is "
        f"{max(saines) if saines else '?'}. A rollback without a number goes back to the previous "
        "revision, whatever its status.",
        fr=f"Le rollback revient à la révision {cible} ; la dernière révision saine avant les échecs est la "
        f"{max(saines) if saines else '?'}. Un rollback sans numéro revient à la révision précédente, quel "
        "que soit son statut.",
    )
    pret = host.run(f"sudo kubectl --kubeconfig /etc/kubernetes/admin.conf -n {NAMESPACE} rollout status "
                    f"deploy/{RELEASE}-podinfo --timeout=120s")
    assert pret.rc == 0, message(
        en=f"The application of the release is not available after the rollback: {pret.stderr.strip()}",
        fr=f"L'application de la release n'est pas disponible après le rollback : {pret.stderr.strip()}",
    )


# ----------------------------------------------------------------------
# 4. Les tests du chart passent sur la révision restaurée.
# ----------------------------------------------------------------------
def test_les_tests_du_chart_passent(host):
    res = host.run(f"{HELM} status {RELEASE} -n {NAMESPACE} -o json")
    assert res.rc == 0, message(
        en=f"helm status {RELEASE} fails: {res.stderr.strip()}",
        fr=f"helm status {RELEASE} échoue : {res.stderr.strip()}",
    )
    statut = json.loads(res.stdout)
    # Mesuré le 2026-11-20 : après un rollback qui échoue, helm test réussit
    # encore, sur les Pods de l'ancienne version qui servent toujours. Les
    # tests ne valent que sur une révision courante déployée.
    etat = (statut.get("info") or {}).get("status")
    assert etat == "deployed", message(
        en=f"The current revision {statut.get('version')} of the release is {etat!r}, not deployed: "
        "the chart tests then run on the Pods of an older version that still serve.",
        fr=f"La révision courante {statut.get('version')} de la release est {etat!r}, pas deployed : "
        "les tests du chart tournent alors sur les Pods d'une ancienne version qui servent encore.",
    )
    tests = [h for h in statut.get("hooks") or [] if "test" in (h.get("events") or [])]
    phases = {h["name"]: (h.get("last_run") or {}).get("phase") for h in tests}
    assert tests and all(p == "Succeeded" for p in phases.values()), message(
        en=f"The chart tests did not pass on the current revision {statut.get('version')}: {phases or 'never run'}. "
        "`helm test` runs them.",
        fr=f"Les tests du chart n'ont pas réussi sur la révision courante {statut.get('version')} : "
        f"{phases or 'jamais lancés'}. `helm test` les lance.",
    )
