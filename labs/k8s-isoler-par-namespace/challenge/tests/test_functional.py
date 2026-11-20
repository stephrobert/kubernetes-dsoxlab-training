"""test_functional.py : k8s-isoler-par-namespace

La préparation pose l'application inventaire dans default, par erreur. Ces
tests lisent les objets des namespaces stock et default, le relevé
~/namespaces/releve.txt, et rejouent les requêtes DANS le Pod caisse du
namespace caisse : le nom qualifié doit répondre, le nom court doit échouer.
Un test vérifie un seul état demandé par l'énoncé.

Le Pod qui répond se juge sur le cluster : le relevé doit nommer un Pod
inventaire de stock qui existe au moment du check. Cette valeur change à
chaque création des Pods, elle ne se recopie pas d'une leçon.

Le constat du nom court est jugé sur le sens, pas sur un mot exact : le message
de busybox (« bad address ») ou une phrase qui dit l'échec sont acceptés.
"""

from __future__ import annotations

import json
import unicodedata

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
STOCK = "stock"
CAISSE = "caisse"
PORT = 8080
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


def _caisse(host) -> None:
    pod = _json(host, CAISSE, "get pod caisse")
    assert pod is not None and (pod.get("status") or {}).get("phase") == "Running", message(
        en=f"No running Pod caisse in the {CAISSE} namespace: the preparation created it, and "
        "the requests are made from it. Run `dsoxlab reset k8s-isoler-par-namespace` if it was "
        "deleted.",
        fr=f"Aucun Pod caisse en marche dans le namespace {CAISSE} : la préparation l'a créé, et "
        "c'est depuis lui que se font les requêtes. Lancez `dsoxlab reset "
        "k8s-isoler-par-namespace` s'il a été supprimé.",
    )


def _wget(host, url: str) -> tuple[int, str]:
    res = host.run(f"{ADMIN} -n {CAISSE} exec caisse -- wget -qO- -T 5 {url}")
    return res.rc, res.stdout.strip()


def _pods_de_stock(host) -> list[str]:
    pods = (_json(host, STOCK, "get pods -l app=inventaire") or {}).get("items") or []
    return [p["metadata"]["name"] for p in pods
            if (p.get("status") or {}).get("phase") == "Running"
            and not p["metadata"].get("deletionTimestamp")]


# ----------------------------------------------------------------------
# 1. inventaire dans stock, plus rien dans default.
# ----------------------------------------------------------------------
def test_inventaire_est_dans_stock_et_plus_rien_dans_default(host):
    dep = _json(host, STOCK, "get deployment inventaire")
    svc = _json(host, STOCK, "get service inventaire")
    assert dep is not None and svc is not None, message(
        en=f"The Deployment inventaire and the Service inventaire must both be in the {STOCK} "
        f"namespace (Deployment: {'yes' if dep else 'no'}, Service: {'yes' if svc else 'no'}).",
        fr=f"Le Deployment inventaire et le Service inventaire doivent être tous deux dans le "
        f"namespace {STOCK} (Deployment : {'oui' if dep else 'non'}, Service : "
        f"{'oui' if svc else 'non'}).",
    )
    assert ((dep.get("status") or {}).get("availableReplicas") or 0) >= 1, message(
        en=f"The Deployment inventaire of {STOCK} has no available replica.",
        fr=f"Le Deployment inventaire de {STOCK} n'a aucun réplica disponible.",
    )
    restes = [k for k in ("deployment", "service")
              if host.run(f"{ADMIN} -n default get {k} inventaire").rc == 0]
    assert not restes, message(
        en=f"Still in the default namespace: {', '.join(restes)} inventaire. Creating the "
        "application in stock does not remove the copy created by mistake in default: delete it.",
        fr=f"Encore dans le namespace default : {', '.join(restes)} inventaire. Créer "
        "l'application dans stock ne retire pas la copie créée par erreur dans default : "
        "supprimez-la.",
    )


# ----------------------------------------------------------------------
# 2. Le nom qualifié répond depuis caisse, et le relevé nomme le Pod.
# ----------------------------------------------------------------------
def test_caisse_joint_inventaire_par_son_nom_qualifie(host, releve):
    _caisse(host)
    url = f"http://inventaire.{STOCK}:{PORT}/hostname"
    rc, reponse = _wget(host, url)
    pods = _pods_de_stock(host)
    assert rc == 0 and reponse in pods, message(
        en=f"From the caisse Pod, {url} does not answer with the name of a Pod inventaire of "
        f"{STOCK} (answer: {reponse!r}). The name <service>.<namespace> resolves from any "
        "namespace, as long as the Service exists there and has endpoints.",
        fr=f"Depuis le Pod caisse, {url} ne répond pas par le nom d'un Pod inventaire de "
        f"{STOCK} (réponse : {reponse!r}). Le nom <service>.<namespace> se résout depuis "
        "n'importe quel namespace, pourvu que le Service y existe et ait des endpoints.",
    )
    valeur = releve.get("pod-qui-repond", "")
    assert valeur in pods, message(
        en=f"pod-qui-repond is {valeur!r}: write the name of the Pod that answers the request "
        f"to the qualified name. The Pods inventaire of {STOCK} are now: {pods}. If you "
        "recreated them, the name changed: query again.",
        fr=f"pod-qui-repond vaut {valeur!r} : écrivez le nom du Pod qui répond à la requête "
        f"vers le nom qualifié. Les Pods inventaire de {STOCK} sont maintenant : {pods}. Si "
        "vous les avez recréés, le nom a changé : refaites la requête.",
    )


# ----------------------------------------------------------------------
# 3. Le nom court échoue depuis caisse.
# ----------------------------------------------------------------------
def test_le_nom_court_echoue_depuis_caisse_et_le_constat_est_consigne(host, releve):
    _caisse(host)
    rc, _ = _wget(host, f"http://inventaire:{PORT}/hostname")
    assert rc != 0, message(
        en=f"From {CAISSE}, the short name inventaire answers: a Service named inventaire "
        f"exists in {CAISSE} itself. The short name only resolves in the namespace of the "
        "client.",
        fr=f"Depuis {CAISSE}, le nom court inventaire répond : un Service inventaire existe "
        f"dans {CAISSE} lui-même. Le nom court ne se résout que dans le namespace du client.",
    )
    valeur = releve.get("nom-court", "")
    lue = _compact(valeur)
    assert valeur and any(m in lue for m in DIT_L_ECHEC), message(
        en=f"nom-court is {valeur!r}: write what the request to the short name inventaire gives "
        "from the caisse Pod, the error message or a sentence that says it fails.",
        fr=f"nom-court vaut {valeur!r} : écrivez ce que donne la requête vers le nom court "
        "inventaire depuis le Pod caisse, le message d'erreur ou une phrase qui dit l'échec.",
    )
