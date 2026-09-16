"""test_functional.py : cks-audit-log-policy

Trois affirmations qui lisent l'état du NŒUD et du cluster, jamais les
commandes tapées.

La dernière est la seule qui prouve quelque chose, et elle est la raison d'être
du lab. Une politique d'audit posée sur le disque ne prouve rien : le fichier
peut être mal formé, les flags peuvent manquer, les volumes peuvent ne pas être
montés, et l'API server tourne quand même, sans écrire une ligne. Le seul
verdict qui vaut est le JOURNAL que le cluster vient d'écrire.

Le test final déclenche donc deux opérations réelles, une sensible et une
banale, puis relit ce que l'audit en a fait. Il vérifie les deux niveaux :
corps complet pour le Secret, métadonnées seules pour le reste. Une politique
qui enregistrerait tout au niveau maximum passerait la première moitié et
échouerait la seconde, et c'est voulu : auditer tout en RequestResponse remplit
un disque en quelques heures et recopie les Secrets en clair dans le journal.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
POLITIQUE = "/etc/kubernetes/audit-policy.yaml"
JOURNAL = "/var/log/kubernetes/audit.log"
MANIFESTE = "/etc/kubernetes/manifests/kube-apiserver.yaml"
NAMESPACE = "coffre"
SECRET = "dossier-medical"  # noqa: S105 - nom d'un Secret, pas un mot de passe


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _lignes_d_audit(host, motif: str, depuis: int = 400) -> list[dict]:
    """Les dernières lignes du journal qui portent ce motif, décodées.

    Le journal est en JSON par ligne. On ne lit que la fin : il grossit vite,
    et ce qui nous intéresse vient d'être écrit.
    """
    res = host.run(f"sudo tail -n {depuis} {JOURNAL} 2>/dev/null | grep -F '{motif}' || true")
    lignes = []
    for brute in res.stdout.splitlines():
        try:
            lignes.append(json.loads(brute))
        except json.JSONDecodeError:
            continue
    return lignes


# ----------------------------------------------------------------------
# 1. La politique existe, et elle distingue deux niveaux.
# ----------------------------------------------------------------------
def test_la_politique_distingue_les_secrets_du_reste(host):
    """Une politique à un seul niveau répondrait à côté de la demande.

    On lit le fichier sur le nœud, pas dans le cluster : une politique d'audit
    n'est pas un objet Kubernetes, c'est un fichier que l'API server lit au
    démarrage.
    """
    res = host.run(f"sudo cat {POLITIQUE}")
    assert res.rc == 0 and res.stdout.strip(), (
        f"Aucune politique d'audit lisible en {POLITIQUE}. Ce n'est pas un objet "
        "du cluster : c'est un fichier du nœud, que l'API server lit au "
        "démarrage."
    )
    contenu = res.stdout
    assert "RequestResponse" in contenu, (
        "La politique ne demande nulle part le niveau RequestResponse, le seul "
        "qui enregistre le corps de la requête et de la réponse. Sans lui, on "
        "sait qu'un Secret a été lu, pas ce qu'il contenait."
    )
    assert "Metadata" in contenu, (
        "La politique ne porte pas de niveau Metadata pour le reste. Auditer "
        "tout en RequestResponse recopie chaque Secret en clair dans le journal "
        "et sature le disque : ce n'est pas ce qui est demandé."
    )
    assert "secrets" in contenu, (
        "La politique ne nomme pas la ressource secrets : rien ne distingue "
        "donc les Secrets du reste."
    )


# ----------------------------------------------------------------------
# 2. L'API server a été relancé avec cette politique, et il répond.
# ----------------------------------------------------------------------
def test_l_api_server_tourne_avec_l_audit(host):
    """Deux affirmations, et la seconde est la vraie.

    Des flags dans le manifeste ne suffisent pas : l'API server est un Pod, et
    il ne voit du nœud que ce qu'on lui monte. Des flags sans volumes donnent
    un conteneur qui boucle. On exige donc aussi que l'API réponde.
    """
    res = host.run(f"sudo cat {MANIFESTE}")
    assert res.rc == 0, "Le manifeste de l'API server est illisible."
    manquants = [
        flag
        for flag in ("--audit-policy-file", "--audit-log-path")
        if flag not in res.stdout
    ]
    assert not manquants, (
        f"Le manifeste ne porte pas : {', '.join(manquants)}. L'API server ne "
        "sait donc ni quelle politique appliquer, ni où écrire."
    )
    assert POLITIQUE in res.stdout and JOURNAL in res.stdout, (
        "Les flags sont là, mais les chemins montés ne correspondent pas à ceux "
        "de la politique et du journal : vérifiez les volumes hostPath et leurs "
        "volumeMounts."
    )

    rc, _, diagnostic = _kubectl(host, "get --raw /healthz")
    assert rc == 0, (
        "L'API server ne répond plus après la modification du manifeste. C'est "
        "presque toujours un volume manquant : le conteneur cherche un fichier "
        "que le nœud ne lui montre pas. `sudo crictl logs` sur le conteneur "
        f"kube-apiserver le dit en une ligne. Sortie : {diagnostic}"
    )


# ----------------------------------------------------------------------
# 3. LE test : le journal prouve que l'audit agit, et aux deux niveaux.
# ----------------------------------------------------------------------
def test_le_journal_enregistre_les_secrets_en_entier_et_le_reste_en_metadonnees(host):
    """On provoque les deux opérations, puis on relit ce que l'audit en a fait.

    Les deux sens dans la même mesure : le Secret doit apparaître avec son
    corps, et une lecture banale doit apparaître SANS. Une politique qui
    enregistre tout au niveau maximum échoue ici, et c'est délibéré.
    """
    rc, _, diagnostic = _kubectl(host, f"-n {NAMESPACE} get secret {SECRET}")
    assert rc == 0, f"Le Secret {SECRET} du setup est introuvable. {diagnostic}"
    _kubectl(host, f"-n {NAMESPACE} get pods")
    host.run("sleep 5")

    res = host.run(f"sudo test -s {JOURNAL}")
    assert res.rc == 0, (
        f"Le journal {JOURNAL} est vide ou absent alors que des requêtes "
        "viennent d'être faites. L'API server n'écrit donc rien : le volume du "
        "journal n'est probablement pas monté, ou le chemin du flag ne "
        "correspond pas à celui du volume."
    )

    secrets = [
        ligne
        for ligne in _lignes_d_audit(host, f'"name":"{SECRET}"')
        if (ligne.get("objectRef") or {}).get("resource") == "secrets"
    ]
    assert secrets, (
        f"Aucune trace de la lecture du Secret {SECRET} dans le journal, alors "
        "qu'elle vient d'avoir lieu. La règle qui vise les secrets n'attrape "
        "rien : vérifiez le groupe d'API, qui est la chaîne vide pour les "
        "Secrets, et l'ORDRE des règles, car l'API server retient la première "
        "qui correspond."
    )
    niveaux_secret = {ligne.get("level") for ligne in secrets}
    assert "RequestResponse" in niveaux_secret, (
        f"La lecture du Secret est enregistrée au niveau {niveaux_secret}, pas "
        "en RequestResponse. Si une règle attrape-tout est placée avant celle "
        "des Secrets, c'est elle qui gagne : l'ordre des règles décide."
    )

    banales = [
        ligne
        for ligne in _lignes_d_audit(host, '"resource":"pods"')
        if (ligne.get("objectRef") or {}).get("resource") == "pods"
    ]
    assert banales, (
        "Aucune trace des lectures de Pods : la règle attrape-tout en Metadata "
        "manque, et l'audit ne voit qu'une partie du trafic."
    )
    trop_bavardes = [ligne for ligne in banales if ligne.get("level") != "Metadata"]
    assert not trop_bavardes, (
        f"{len(trop_bavardes)} requête(s) banale(s) sont enregistrées au niveau "
        f"{ {ligne.get('level') for ligne in trop_bavardes} }, au lieu de Metadata. "
        "Tout auditer en RequestResponse recopie les corps de requête dans le "
        "journal, Secrets compris, et sature le disque : c'est précisément ce "
        "que la politique à deux niveaux évite."
    )
