"""test_functional.py : k8s-challenge-premier-deploiement

Ces tests lisent l'état du CLUSTER, le kubeconfig de l'apprenant et les
fichiers de la boutique, jamais les commandes tapées.

Un test vérifie un seul état demandé par l'énoncé. Deux sont bloquants
(`exam_blocking_checks`) : la vitrine qui répond, livrable du challenge, et le
kubeconfig protégé. La réparation de stock est jugée sur trois traces qui
concordent : l'image des Pods, celle du manifeste fourni, et celle que
`kubectl apply` a mémorisée dans l'annotation last-applied-configuration ; un
`kubectl set image` laisserait l'ancienne image dans cette annotation.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
IMAGE = "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
IMAGE_FAUTIVE = "nginx:1.300"
CLIENT = "busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
RAISONS = ("ImagePullBackOff", "ErrImagePull")


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str, absent: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _deployment(host, ns: str, nom: str) -> dict:
    return _json(host, f"-n {ns} get deployment {nom}", message(
        en=f"No Deployment {nom} in the {ns} namespace.",
        fr=f"Aucun Deployment {nom} dans le namespace {ns}.",
    ))


def _pods(host, ns: str, app: str) -> list[dict]:
    return _json(host, f"-n {ns} get pods -l app={app}", message(
        en=f"Cannot list the Pods of {app} in {ns}.",
        fr=f"Impossible de lister les Pods de {app} dans {ns}.",
    )).get("items") or []


def _maison(host) -> str:
    """Le répertoire personnel de l'utilisateur du lab : testinfra agit en root
    par sudo, donc host.user().home vaudrait /root."""
    return host.check_output(
        'getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6'
    ).strip()


def _horodatage(texte: str) -> float:
    return datetime.fromisoformat(texte.replace("Z", "+00:00")).timestamp()


# ----------------------------------------------------------------------
# 1. kubectl vise le bon cluster et le bon namespace.
# ----------------------------------------------------------------------
def test_le_contexte_actif_vise_la_boutique_et_la_vitrine(host):
    # Lu sous l'utilisateur du lab, avec SON kubeconfig : c'est son contexte actif
    # que l'énoncé demande, pas celui de root.
    res = host.run(
        f'sudo -u "${{SUDO_USER:-ansible}}" kubectl --kubeconfig {_maison(host)}/.kube/config '
        "config view --minify -o json"
    )
    assert res.rc == 0, message(
        en="Cannot read your active kubectl context (kubectl config view --minify).",
        fr="Impossible de lire votre contexte kubectl actif (kubectl config view --minify).",
    )
    vue = json.loads(res.stdout)
    contexte = vue.get("current-context")
    espace = ((vue.get("contexts") or [{}])[0].get("context") or {}).get("namespace")
    assert contexte == "kind-boutique" and espace == "vitrine", message(
        en=f"Your active context is {contexte!r} with namespace {espace!r}; "
           "expected kind-boutique with namespace vitrine.",
        fr=f"Votre contexte actif est {contexte!r}, namespace {espace!r} ; "
           "attendu kind-boutique, namespace vitrine.",
    )


# ----------------------------------------------------------------------
# 2. La vitrine : trois réplicas disponibles sur l'image demandée.
# ----------------------------------------------------------------------
def test_la_vitrine_a_trois_replicas_disponibles_sur_la_bonne_image(host):
    dep = _deployment(host, "vitrine", "vitrine")
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    images = {c["image"] for c in dep["spec"]["template"]["spec"]["containers"]}
    assert disponibles == 3 and images == {IMAGE}, message(
        en=f"vitrine has {disponibles} available replica(s) on {sorted(images)}; "
           f"expected 3 on {IMAGE}.",
        fr=f"vitrine a {disponibles} réplica(s) disponible(s) sur {sorted(images)} ; "
           f"attendu 3 sur {IMAGE}.",
    )


# ----------------------------------------------------------------------
# 3. Le Service vitrine désigne trois Pods prêts.
# ----------------------------------------------------------------------
def test_le_service_vitrine_compte_trois_endpoints_prets(host):
    _json(host, "-n vitrine get service vitrine", message(
        en="No Service vitrine in the vitrine namespace.",
        fr="Aucun Service vitrine dans le namespace vitrine.",
    ))
    tranches = _json(host, "-n vitrine get endpointslices -l kubernetes.io/service-name=vitrine",
                     message(en="Cannot read the EndpointSlices of vitrine.",
                             fr="Impossible de lire les EndpointSlices de vitrine."))
    prets = sum(
        1
        for tranche in tranches.get("items") or []
        for ep in tranche.get("endpoints") or []
        if (ep.get("conditions") or {}).get("ready")
    )
    assert prets == 3, message(
        en=f"The vitrine Service has {prets} ready endpoint(s), expected 3: "
           "check that its selector matches the labels of the vitrine Pods.",
        fr=f"Le Service vitrine compte {prets} endpoint(s) prêt(s), attendu 3 : "
           "vérifiez que son sélecteur correspond aux labels des Pods de vitrine.",
    )


# ----------------------------------------------------------------------
# 4. BLOQUANT : la vitrine répond depuis le cluster.
# ----------------------------------------------------------------------
def test_la_vitrine_repond_en_http_depuis_le_cluster(host):
    nom = f"controle-{secrets.token_hex(3)}"
    res = host.run(
        f"{ADMIN} -n vitrine run {nom} --rm -i --restart=Never --quiet --image={CLIENT} "
        "--timeout=120s -- wget -qO- -T 10 http://vitrine.vitrine"
    )
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en="The storefront does not answer at http://vitrine.vitrine from a Pod of the cluster.",
        fr="La vitrine ne répond pas sur http://vitrine.vitrine depuis un Pod du cluster.",
    )


# ----------------------------------------------------------------------
# 5. La cause de la panne de stock, consignée avant la réparation.
# ----------------------------------------------------------------------
def test_la_cause_de_stock_est_consignee_avant_la_reparation(host):
    chemin = f"{_maison(host)}/boutique/cause-stock.txt"
    fichier = host.file(chemin)
    assert fichier.exists and fichier.size > 0, message(
        en=f"{chemin} is missing or empty.",
        fr=f"{chemin} est absent ou vide.",
    )
    texte = fichier.content_string
    assert any(r.lower() in texte.lower() for r in RAISONS) and IMAGE_FAUTIVE in texte, message(
        en=f"cause-stock.txt must name the waiting reason read in kubectl describe "
           f"and the faulty image {IMAGE_FAUTIVE}.",
        fr=f"cause-stock.txt doit nommer la raison d'attente lue dans kubectl describe "
           f"et l'image fautive {IMAGE_FAUTIVE}.",
    )
    jeux = _json(host, "-n catalogue get replicasets -l app=stock", message(
        en="Cannot read the ReplicaSets of stock.",
        fr="Impossible de lire les ReplicaSets de stock.",
    )).get("items") or []
    corriges = [
        rs for rs in jeux
        if IMAGE in {c["image"] for c in rs["spec"]["template"]["spec"]["containers"]}
    ]
    if corriges:
        reparation = min(_horodatage(rs["metadata"]["creationTimestamp"]) for rs in corriges)
        assert fichier.mtime.timestamp() <= reparation, message(
            en="cause-stock.txt was written after stock was repaired: record the cause first.",
            fr="cause-stock.txt a été écrit après la réparation de stock : consignez la cause d'abord.",
        )


# ----------------------------------------------------------------------
# 6. stock réparé par son manifeste et kubectl apply.
# ----------------------------------------------------------------------
def test_stock_est_repare_par_son_manifeste(host):
    dep = _deployment(host, "catalogue", "stock")
    pods = _pods(host, "catalogue", "stock")
    en_marche = [
        p for p in pods
        if p["status"].get("phase") == "Running"
        and {c["image"] for c in p["spec"]["containers"]} == {IMAGE}
        and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
    ]
    manifeste = host.file(f"{_maison(host)}/boutique/stock.yaml").content_string
    memorise = (dep["metadata"].get("annotations") or {}).get(
        "kubectl.kubernetes.io/last-applied-configuration", "")
    assert en_marche and IMAGE in manifeste and IMAGE_FAUTIVE not in manifeste and IMAGE in memorise, message(
        en=f"stock is not repaired through its manifest: its Pods must run {IMAGE}, "
           "~/boutique/stock.yaml must carry this image, and the change must be applied with kubectl apply -f.",
        fr=f"stock n'est pas réparé par son manifeste : ses Pods doivent tourner sur {IMAGE}, "
           "~/boutique/stock.yaml doit porter cette image, et la modification être appliquée avec kubectl apply -f.",
    )


# ----------------------------------------------------------------------
# 7. BLOQUANT : le kubeconfig reçu n'est lisible que par son propriétaire.
# ----------------------------------------------------------------------
def test_le_kubeconfig_de_la_boutique_n_est_lisible_que_par_son_proprietaire(host):
    chemin = f"{_maison(host)}/.kube/boutique.yaml"
    fichier = host.file(chemin)
    assert fichier.exists and fichier.mode == 0o600, message(
        en=f"{chemin} must exist with mode 600 (it gives access to the cluster).",
        fr=f"{chemin} doit exister avec les droits 600 (il donne accès au cluster).",
    )
