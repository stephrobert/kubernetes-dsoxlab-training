"""test_functional.py : cks-restreindre-l-acces-anonyme

Ces tests lisent l'état de k8s-cp.lab, jamais les commandes tapées : codes
HTTP rendus à un client SANS identifiant (curl -sk) sur l'API server et sur le
kubelet, liaisons RBAC du cluster, et refus réel de NodeRestriction.

Aucun test n'est vrai avant le travail : le setup laisse l'anonyme lire
/version, donne le rôle view à system:unauthenticated, ouvre le kubelet à
l'anonyme et retire NodeRestriction. Le test de la découverte de kubeadm join
serait vrai au départ (cluster-info est lisible) : il exige donc aussi que la
restriction soit en place.

Deux triches sont refusées par construction : couper TOUT accès anonyme
(--anonymous-auth=false, ou anonymous.enabled: false sans conditions) casse
la lecture de cluster-info, donc kubeadm join ; et arrêter le kubelet ne rend
pas 401 sur le port 10250.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NOEUD = "k8s-cp.lab"
API = "https://127.0.0.1:6443"
KUBELET = "https://127.0.0.1:10250"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
CLUSTER_INFO = "/api/v1/namespaces/kube-public/configmaps/cluster-info"
SANTE = ("/livez", "/readyz", "/healthz")
FERMES = ("/version", "/api", "/api/v1/namespaces/default/pods", "/apis")
# Les deux liaisons que kubeadm pose lui-même vers les anonymes (relevé du
# 2026-11-17, kubeadm v1.37.2). Toute autre est une porte ouverte.
LIAISONS_KUBEADM = {
    ("ClusterRoleBinding", "", "system:public-info-viewer"),
    ("RoleBinding", "kube-public", "kubeadm:bootstrap-signer-clusterinfo"),
}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _code(host, url: str) -> str:
    res = host.run(f"curl -sk -m 5 -o /dev/null -w '%{{http_code}}' {url}")
    return res.stdout.strip()


def _restriction_en_place(host) -> None:
    code = _code(host, f"{API}/version")
    assert code == "401", message(
        en=f"An anonymous client still gets {code} on /version (401 expected): the anonymous access is not "
        "restricted yet. Is the API server running with --authentication-config?",
        fr=f"Un client anonyme reçoit encore {code} sur /version (401 attendu) : l'accès anonyme n'est pas "
        "encore restreint. L'API server tourne-t-il avec --authentication-config ?",
    )


def test_l_anonyme_n_atteint_que_la_sante(host):
    _restriction_en_place(host)
    for chemin in FERMES:
        code = _code(host, f"{API}{chemin}")
        assert code == "401", message(
            en=f"An anonymous client gets {code} on {chemin}, 401 expected: only health paths stay open.",
            fr=f"Un client anonyme reçoit {code} sur {chemin}, 401 attendu : seuls les chemins de santé restent ouverts.",
        )
    for chemin in SANTE:
        code = _code(host, f"{API}{chemin}")
        assert code == "200", message(
            en=f"An anonymous client gets {code} on {chemin}, 200 expected: health probes must still answer.",
            fr=f"Un client anonyme reçoit {code} sur {chemin}, 200 attendu : les sondes de santé doivent répondre.",
        )


def test_la_decouverte_de_kubeadm_join_reste_ouverte(host):
    _restriction_en_place(host)
    code = _code(host, f"{API}{CLUSTER_INFO}")
    assert code == "200", message(
        en=f"An anonymous client gets {code} on cluster-info (200 expected): kubeadm join by token reads this "
        "ConfigMap WITHOUT credentials, and would retry forever.",
        fr=f"Un client anonyme reçoit {code} sur cluster-info (200 attendu) : kubeadm join par jeton lit ce "
        "ConfigMap SANS identifiant, et réessaierait sans fin.",
    )


def test_aucun_droit_rbac_pour_les_anonymes(host):
    res = host.run(f"{KUBECTL} get clusterrolebindings,rolebindings -A -o json")
    assert res.rc == 0, message(
        en=f"Cannot list the bindings: {res.stderr.strip()}",
        fr=f"Impossible de lister les liaisons : {res.stderr.strip()}",
    )
    en_trop = []
    for objet in json.loads(res.stdout)["items"]:
        cle = (objet["kind"], objet["metadata"].get("namespace", ""), objet["metadata"]["name"])
        for sujet in objet.get("subjects") or []:
            if sujet.get("name") in ("system:anonymous", "system:unauthenticated") and cle not in LIAISONS_KUBEADM:
                en_trop.append(f"{cle[0]} {cle[2]} -> {objet['roleRef']['name']} ({sujet['name']})")
    assert not en_trop, message(
        en=f"Bindings still grant rights to anonymous clients: {en_trop}.",
        fr=f"Des liaisons donnent encore des droits aux clients anonymes : {en_trop}.",
    )
    # `kubectl auth can-i --as=system:anonymous` ne mesure rien : l'anonyme
    # usurpé n'a pas le droit de créer la SelfSubjectAccessReview que la
    # commande envoie, elle échoue donc toujours (mesuré le 2026-11-17). La
    # question se pose en admin, par une SubjectAccessReview.
    revue = json.dumps({
        "apiVersion": "authorization.k8s.io/v1",
        "kind": "SubjectAccessReview",
        "spec": {
            "user": "system:anonymous",
            "groups": ["system:unauthenticated"],
            "resourceAttributes": {"verb": "list", "resource": "pods"},
        },
    })
    res = host.run(f"echo '{revue}' | {KUBECTL} create -f - -o jsonpath='{{.status.allowed}}'")
    assert res.rc == 0 and res.stdout.strip() in ("false", ""), message(
        en=f"A SubjectAccessReview for system:anonymous on « list pods » answers allowed={res.stdout.strip()} "
        f"{res.stderr.strip()}",
        fr=f"Une SubjectAccessReview pour system:anonymous sur « list pods » répond allowed={res.stdout.strip()} "
        f"{res.stderr.strip()}",
    )


def test_le_kubelet_refuse_l_anonyme(host):
    code = _code(host, f"{KUBELET}/pods")
    assert code == "401", message(
        en=f"The kubelet of {NOEUD} answers {code} to an anonymous client on :10250/pods, 401 expected "
        "(000 means it does not answer at all).",
        fr=f"Le kubelet de {NOEUD} répond {code} à un client anonyme sur :10250/pods, 401 attendu "
        "(000 signifie qu'il ne répond pas du tout).",
    )
    res = host.run("sudo grep -A1 '^authorization:' /var/lib/kubelet/config.yaml")
    assert "AlwaysAllow" not in res.stdout, message(
        en="The kubelet still runs with authorization.mode: AlwaysAllow: any authenticated client could run "
        "commands in its Pods. Webhook delegates the decision to the API server.",
        fr="Le kubelet tourne encore en authorization.mode: AlwaysAllow : tout client authentifié pourrait "
        "lancer des commandes dans ses Pods. Webhook délègue la décision à l'API server.",
    )
    etat = host.run(
        f"{KUBECTL} get node {NOEUD} -o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'"
    ).stdout.strip()
    assert etat == "True", message(
        en=f"{NOEUD} is not Ready ({etat}): sudo journalctl -u kubelet -n 30 says why.",
        fr=f"{NOEUD} n'est pas Ready ({etat}) : sudo journalctl -u kubelet -n 30 dit pourquoi.",
    )


def test_noderestriction_refuse_les_etiquettes_reservees(host):
    res = host.run(
        f"sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf label node {NOEUD} "
        "node-restriction.kubernetes.io/essai=1 --overwrite"
    )
    if res.rc == 0:
        host.run(f"{KUBECTL} label node {NOEUD} node-restriction.kubernetes.io/essai-")
    assert res.rc != 0, message(
        en=f"The kubelet credentials of {NOEUD} could set a node-restriction.kubernetes.io/ label on their "
        "own node: the NodeRestriction admission plugin is not active.",
        fr=f"Les identifiants du kubelet de {NOEUD} ont pu poser une étiquette node-restriction.kubernetes.io/ "
        "sur leur propre nœud : le plugin d'admission NodeRestriction n'est pas actif.",
    )
    # La phrase de NodeRestriction, relevée le 2026-11-16 (série 2 CKS-A, M2) :
    # « is not allowed to modify labels: node-restriction.kubernetes.io/... ».
    assert "is not allowed to modify labels" in res.stderr, message(
        en=f"The label was refused, but not by NodeRestriction: {res.stderr.strip()}",
        fr=f"L'étiquette a été refusée, mais pas par NodeRestriction : {res.stderr.strip()}",
    )
