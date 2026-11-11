"""test_functional.py : k8s-isoler-par-namespace

Ces tests lisent les objets des namespaces equipe-api et default, le relevé
~/namespaces/releve.txt, et rejouent les deux requêtes DANS le Pod client de
equipe-front : le nom qualifié doit répondre, le nom court doit échouer. Un
test vérifie un seul état demandé par l'énoncé.

Le constat du nom court est jugé sur le sens, pas sur un mot exact : le message
de busybox (« bad address ») ou une phrase qui dit l'échec sont acceptés.
"""

from __future__ import annotations

import json
import unicodedata

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
API = "equipe-api"
FRONT = "equipe-front"
RELEVE = "~/namespaces/releve.txt"
DIT_L_ECHEC = ("badaddress", "echec", "echoue", "introuvable", "neresout", "resoutpas",
               "fail", "notfound", "notresolve", "unknownhost", "impossible", "erreur", "error")


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/namespaces/releve.txt")
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if ligne and not ligne.startswith("#") and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


def _compact(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if c.isalnum())


def _json(host, ns: str, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {ns} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _client(host) -> None:
    pod = _json(host, FRONT, "get pod client")
    assert pod is not None and (pod.get("status") or {}).get("phase") == "Running", message(
        en=f"No running Pod client in the {FRONT} namespace: it is the Pod the requests are "
        "made from.",
        fr=f"Aucun Pod client en marche dans le namespace {FRONT} : c'est depuis lui que se font "
        "les requêtes.",
    )


def _wget(host, url: str) -> tuple[int, str]:
    res = host.run(f"{ADMIN} -n {FRONT} exec client -- wget -qO- -T 5 {url}")
    return res.rc, res.stdout


# ----------------------------------------------------------------------
# 1. api dans equipe-api, rien dans default.
# ----------------------------------------------------------------------
def test_api_est_dans_equipe_api_et_rien_dans_default(host):
    dep = _json(host, API, "get deployment api")
    svc = _json(host, API, "get service api")
    assert dep is not None and svc is not None, message(
        en=f"The Deployment api and the Service api must both be in the {API} namespace "
        f"(Deployment: {'yes' if dep else 'no'}, Service: {'yes' if svc else 'no'}).",
        fr=f"Le Deployment api et le Service api doivent être tous deux dans le namespace {API} "
        f"(Deployment : {'oui' if dep else 'non'}, Service : {'oui' if svc else 'non'}).",
    )
    assert ((dep.get("status") or {}).get("availableReplicas") or 0) >= 1, message(
        en=f"The Deployment api of {API} has no available replica.",
        fr=f"Le Deployment api de {API} n'a aucun réplica disponible.",
    )
    egares = [k for k in ("deployment", "service")
              if host.run(f"{ADMIN} -n default get {k} api").rc == 0]
    assert not egares, message(
        en=f"Found in the default namespace: {', '.join(egares)} api. Without -n, objects land "
        "in default: everything belongs in equipe-api.",
        fr=f"Trouvé dans le namespace default : {', '.join(egares)} api. Sans -n, les objets "
        "partent dans default : tout doit être dans equipe-api.",
    )


# ----------------------------------------------------------------------
# 2. Le nom qualifié répond depuis equipe-front.
# ----------------------------------------------------------------------
def test_un_client_d_equipe_front_joint_api_par_son_nom_qualifie(host, releve):
    _client(host)
    rc, page = _wget(host, f"http://api.{API}")
    assert rc == 0 and "welcometonginx" in _compact(page), message(
        en=f"From the client Pod of {FRONT}, http://api.{API} does not answer. The name "
        "<service>.<namespace> resolves from any namespace, as long as the Service has "
        "endpoints.",
        fr=f"Depuis le Pod client de {FRONT}, http://api.{API} ne répond pas. Le nom "
        "<service>.<namespace> se résout depuis n'importe quel namespace, pourvu que le Service "
        "ait des endpoints.",
    )
    valeur = releve.get("reponse-nom-qualifie", "")
    assert "welcometonginx" in _compact(valeur), message(
        en=f"reponse-nom-qualifie is {valeur!r}: write what the request to the qualified name "
        "answers, at least its title line.",
        fr=f"reponse-nom-qualifie vaut {valeur!r} : écrivez ce que répond la requête vers le nom "
        "qualifié, au moins sa ligne de titre.",
    )


# ----------------------------------------------------------------------
# 3. Le nom court échoue depuis equipe-front.
# ----------------------------------------------------------------------
def test_le_nom_court_echoue_depuis_equipe_front_et_le_constat_est_consigne(host, releve):
    _client(host)
    rc, _ = _wget(host, "http://api")
    assert rc != 0, message(
        en=f"From {FRONT}, the short name api answers: a Service named api exists in {FRONT} "
        "itself. The short name only resolves in the namespace of the client.",
        fr=f"Depuis {FRONT}, le nom court api répond : un Service api existe dans {FRONT} lui-même. "
        "Le nom court ne se résout que dans le namespace du client.",
    )
    valeur = releve.get("nom-court", "")
    lue = _compact(valeur)
    assert valeur and any(m in lue for m in DIT_L_ECHEC), message(
        en=f"nom-court is {valeur!r}: write what the request to http://api gives from the "
        "client Pod, the error message or a sentence that says it fails. Reread the section of "
        "the Services lesson on reaching a Service by its DNS name.",
        fr=f"nom-court vaut {valeur!r} : écrivez ce que donne la requête vers http://api depuis "
        "le Pod client, le message d'erreur ou une phrase qui dit l'échec. Relisez la section de "
        "la leçon Services sur le nom DNS d'un Service.",
    )
