"""test_functional.py : cks-rbac-least-privilege

Quatre affirmations qui lisent l'état du CLUSTER, jamais les commandes tapées.

Elles ne lisent pas non plus les Role et RoleBinding écrits par le candidat,
sauf une, et pour une raison précise : un droit ne se déduit pas d'un
manifeste. Les règles se cumulent, un binding oublié ailleurs peut tout
rouvrir, et le nom d'un objet ne dit rien de ce qu'il accorde. La seule
question qui compte est « que répond l'API server quand ce compte demande ? »,
et `kubectl auth can-i --as` la pose exactement.

Aucun test ne mesure un seul côté. Retirer un droit est facile si on le retire
à tout le monde : ce qui est difficile, et ce que le CKS demande, est de
retirer le superflu en gardant le nécessaire. Les tests exigent donc les deux
dans la même mesure.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "equipe-dev"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
COMPTE = "dev-sa"
SUJET = f"system:serviceaccount:{NAMESPACE}:{COMPTE}"
RACCOURCI = "dev-admin-binding"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Joue une commande kubectl sur le control plane.

    Rend (code, sortie standard, diagnostic), et les trois restent SÉPARÉS :
    `auth can-i` écrit son verdict sur la sortie standard et ses
    avertissements ailleurs, et c'est le verdict qui décide.
    """
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _peut(host, question: str, namespace: str | None = NAMESPACE) -> bool:
    """La question posée à l'API server AU NOM du compte.

    `auth can-i` rend « yes » ou « no » sur la sortie standard, et un code de
    retour non nul pour un refus. On lit la sortie : elle est explicite, et un
    code non nul peut aussi signaler une commande mal formée, ce qu'on ne veut
    surtout pas confondre avec un refus.
    """
    portee = f"-n {namespace}" if namespace else "--all-namespaces"
    _, verdict, _ = _kubectl(host, f"auth can-i {question} {portee} --as={SUJET}")
    assert verdict in ("yes", "no"), (
        f"Réponse inattendue de l'API server pour « can-i {question} » : "
        f"« {verdict} ». Ni yes ni no : la question est mal formée."
    )
    return verdict == "yes"


# ----------------------------------------------------------------------
# 1. Le pouvoir d'administration est repris.
# ----------------------------------------------------------------------
def test_le_compte_n_est_plus_administrateur_du_cluster(host):
    """Deux affirmations, et la seconde est la vraie.

    L'objet nommé `dev-admin-binding` peut avoir disparu pendant qu'un autre
    binding, créé ailleurs ou sous un autre nom, rend le même pouvoir. On
    interroge donc l'API server, qui tient compte de TOUS les bindings.
    """
    rc, _, _ = _kubectl(host, f"get clusterrolebinding {RACCOURCI}")
    assert rc != 0, (
        f"Le ClusterRoleBinding {RACCOURCI} existe encore : il lie dev-sa à "
        "cluster-admin, c'est-à-dire à tout, partout."
    )
    assert not _peut(host, "'*' '*'", namespace=None), (
        "L'API server répond encore « yes » à « peut-il tout faire, partout ? » "
        f"au nom de {COMPTE}. Un autre binding lui rend ce pouvoir : cherchez "
        "tous les ClusterRoleBindings dont il est le sujet, pas seulement celui "
        "que le scénario nomme."
    )


# ----------------------------------------------------------------------
# 2. LE test : ce qui reste permis ET ce qui ne l'est plus.
# ----------------------------------------------------------------------
def test_le_compte_a_ce_qu_il_lui_faut_et_rien_de_plus(host):
    """Les deux sens dans la même mesure, et c'est délibéré.

    Avant le travail, le compte est cluster-admin : la moitié « ce qui est
    permis » passerait donc seule, et ne mesurerait rien. Après une révocation
    brutale, la moitié « ce qui est refusé » passerait seule, et l'application
    serait cassée. Seule la paire dit que le droit a été RÉDUIT, pas supprimé
    ni laissé entier.
    """
    permis = {
        "list pods": _peut(host, "list pods"),
        "create deployments": _peut(host, "create deployments"),
        "list services": _peut(host, "list services"),
    }
    manquants = [q for q, ok in permis.items() if not ok]
    assert not manquants, (
        f"Le compte {COMPTE} ne peut plus : {', '.join(manquants)}. "
        "L'application portail-dev en a besoin : reprendre cluster-admin ne "
        "veut pas dire tout retirer. Les Deployments sont dans le groupe d'API "
        "« apps », les Pods et Services dans le groupe core, qui s'écrit comme "
        "une chaîne vide."
    )

    refuses = {
        "list secrets": _peut(host, "list secrets"),
        "get secret/jeton-de-paiement": _peut(host, "get secret/jeton-de-paiement"),
    }
    accordes = [q for q, ok in refuses.items() if ok]
    assert not accordes, (
        f"Le compte {COMPTE} peut encore : {', '.join(accordes)}. Les Secrets "
        "ne font pas partie de ce dont l'application a besoin, et un compte qui "
        "les lit peut lire tout ce que le namespace protège."
    )


# ----------------------------------------------------------------------
# 3. Le droit s'arrête au namespace.
# ----------------------------------------------------------------------
def test_le_droit_s_arrete_au_namespace(host):
    """Un ClusterRole lié par un ClusterRoleBinding donnerait les mêmes verbes
    PARTOUT. Le test précédent ne le verrait pas : il ne regarde que
    equipe-dev."""
    ailleurs = {
        "list pods dans kube-system": _peut(host, "list pods", namespace="kube-system"),
        "list pods dans default": _peut(host, "list pods", namespace="default"),
        "list nodes (ressource de cluster)": _peut(host, "list nodes", namespace=None),
    }
    debordements = [q for q, ok in ailleurs.items() if ok]
    assert not debordements, (
        f"Le compte {COMPTE} peut encore : {', '.join(debordements)}. Le droit "
        "accordé déborde de son namespace. Un Role vaut là où il est créé ; un "
        "ClusterRole lié par un ClusterRoleBinding vaut partout, même si son "
        "nom évoque une équipe."
    )


# ----------------------------------------------------------------------
# 4. Et le droit est bien porté par le namespace.
# ----------------------------------------------------------------------
def test_le_droit_est_porte_par_le_namespace(host):
    """La seule lecture de manifeste de ce fichier, et elle a un objet.

    Les trois tests précédents mesurent des effets, et un effet peut être
    obtenu autrement : un ClusterRole lié par un RoleBinding namespacé donne
    exactement le même résultat aujourd'hui. C'est acceptable, et c'est même un
    usage courant. Ce qui ne l'est pas, c'est qu'AUCUN objet du namespace ne
    porte le droit : le compte tiendrait alors ses permissions d'ailleurs, et
    personne ne le verrait en lisant le namespace.
    """
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get rolebinding -o json")
    assert rc == 0 and sortie, f"Impossible de lire les RoleBindings. {diagnostic}"

    lie = [
        rb["metadata"]["name"]
        for rb in json.loads(sortie).get("items", [])
        if any(
            sujet.get("kind") == "ServiceAccount" and sujet.get("name") == COMPTE
            for sujet in (rb.get("subjects") or [])
        )
    ]
    assert lie, (
        f"Aucun RoleBinding de {NAMESPACE} ne prend {COMPTE} pour sujet. Ses "
        "droits viennent donc d'ailleurs, et rien dans ce namespace ne le dit : "
        "c'est exactement le genre de droit qu'un audit ne retrouve pas."
    )
