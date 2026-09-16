"""test_functional.py : cks-networkpolicy-default-deny

Quatre affirmations qui font de VRAIES connexions entre Pods : c'est le CNI qui
applique les règles, et c'est lui qu'on interroge. Lire une politique ne prouve
rien, un `podSelector` mal écrit produit un objet valide qui ne sélectionne
personne.

Aucun test ne mesure un seul côté, et ce n'est pas un principe abstrait : sans
politique, TOUT passe. Un test qui ne vérifierait que le flux permis serait
vrai avant le travail et ne mesurerait rien ; un test qui ne vérifierait que le
flux bloqué serait satisfait par une coupure générale, qui casse
l'application. Chaque test exige donc les deux.

Le dernier est celui que ce lab existe pour poser : une sortie fermée par
défaut casse le DNS, et rien ne le signale. Il exige que la résolution passe et
que le reste de la sortie reste fermé.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "zero-confiance"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _ip(host, pod: str) -> str:
    rc, ip, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get pod {pod} -o jsonpath='{{.status.podIP}}'"
    )
    assert rc == 0 and ip, (
        f"Le Pod {pod} n'a pas d'adresse : le setup l'avait posé, il ne fallait "
        f"pas le supprimer. {diagnostic}"
    )
    return ip


def _joint(host, depuis: str, vers: str) -> bool:
    """Une requête HTTP de Pod à Pod, par ADRESSE et non par nom.

    Passer par l'adresse isole ce qu'on mesure : si le DNS est coupé, cette
    requête doit quand même aboutir quand la politique l'autorise. Mélanger
    les deux ferait échouer le test du flux pour une raison de résolution.
    """
    rc, _, _ = _kubectl(
        host,
        f"-n {NAMESPACE} exec {depuis} --request-timeout=30s -- "
        f"wget -q -O- -T 4 http://{_ip(host, vers)}/",
    )
    return rc == 0


def _resout(host, depuis: str) -> bool:
    rc, _, _ = _kubectl(
        host,
        f"-n {NAMESPACE} exec {depuis} --request-timeout=30s -- "
        "nslookup kubernetes.default.svc.cluster.local",
    )
    return rc == 0


def _politiques(host) -> list[dict]:
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get networkpolicy -o json")
    assert rc == 0 and sortie, f"Impossible de lire les NetworkPolicy. {diagnostic}"
    return json.loads(sortie).get("items", [])


# ----------------------------------------------------------------------
# 1. Le namespace est fermé par défaut, dans les DEUX directions.
# ----------------------------------------------------------------------
def test_le_namespace_est_ferme_par_defaut_dans_les_deux_sens(host):
    """Une politique par défaut se reconnaît à deux choses : elle sélectionne
    TOUS les Pods, avec un podSelector vide, et elle n'autorise rien dans la
    direction qu'elle déclare.

    On les cherche par leur FORME, pas par leur nom : le candidat nomme ses
    objets comme il veut, et deux politiques distinctes ou une seule qui
    déclare les deux directions répondent aussi bien à la demande.
    """
    directions = set()
    for politique in _politiques(host):
        spec = politique["spec"]
        if (spec.get("podSelector") or {}) != {}:
            continue  # elle vise un sous-ensemble : ce n'est pas un défaut global
        for direction in spec.get("policyTypes") or []:
            regles = spec.get(direction.lower()) or []
            if not regles:
                directions.add(direction)

    manquantes = {"Ingress", "Egress"} - directions
    assert not manquantes, (
        f"Aucune politique par défaut ne ferme : {', '.join(sorted(manquantes))}. "
        "Une politique par défaut porte un podSelector VIDE, qui sélectionne "
        "tous les Pods du namespace, déclare la direction sous policyTypes, et "
        "n'écrit AUCUNE règle pour cette direction. Déclarer une direction sans "
        "règle, c'est l'interdire entièrement ; ne pas la déclarer, c'est ne "
        "rien dire d'elle, donc tout laisser passer."
    )


# ----------------------------------------------------------------------
# 2. Le flux autorisé passe, et lui seul.
# ----------------------------------------------------------------------
def test_seul_le_flux_prevu_atteint_la_base(host):
    """Les deux sens dans la même mesure.

    Avant le travail, `web` joint `db` : cette moitié seule serait vraie sans
    qu'aucune politique n'existe. Après une coupure générale, `intrus` est
    bloqué : cette moitié seule serait vraie avec une application cassée.
    """
    assert _joint(host, "web", "db"), (
        "Le Pod web ne joint plus db sur le port 80. La fermeture par défaut a "
        "bien eu lieu, mais le flux dont l'application a besoin n'a pas été "
        "rouvert : il faut une politique d'entrée sur les Pods app=db qui "
        "autorise les Pods app=web sur ce port. Attention, l'entrée de db et la "
        "sortie de web doivent TOUTES DEUX être permises : deux politiques par "
        "défaut ferment les deux bouts du même flux."
    )
    assert not _joint(host, "intrus", "db"), (
        "Le Pod intrus joint db alors que rien ne l'y autorise. Soit aucune "
        "politique ne sélectionne db en entrée, soit la règle ouverte est plus "
        "large que demandée : vérifiez qu'elle nomme le label app=web et non "
        "un sélecteur vide, qui laisse entrer tout le namespace."
    )


# ----------------------------------------------------------------------
# 3. LE test : le DNS repasse, et rien d'autre ne sort.
# ----------------------------------------------------------------------
def test_le_dns_repasse_sans_rouvrir_le_reste_de_la_sortie(host):
    """Le piège que ce lab existe pour poser.

    Une sortie fermée par défaut coupe le DNS, et rien ne le signale : les Pods
    démarrent, les politiques semblent correctes, et les applications tombent
    sur des résolutions qui expirent. Le rouvrir est donc obligatoire.

    Mais le rouvrir sans rouvrir le reste est le vrai geste : une règle de
    sortie trop large redonne au namespace l'accès qu'on venait de lui retirer.
    C'est pourquoi ce test exige aussi qu'intrus ne joigne toujours pas db.
    """
    assert _resout(host, "web"), (
        "Le Pod web ne résout plus aucun nom. C'est l'effet direct d'une sortie "
        "fermée par défaut, et il ne se voit dans aucune spec : le résolveur du "
        "cluster vit dans kube-system et écoute le port 53, en UDP ET en TCP. "
        "Sans règle de sortie qui l'autorise, plus rien ne se résout dans ce "
        "namespace."
    )
    assert not _joint(host, "intrus", "db"), (
        "Le DNS est bien rouvert, mais la sortie l'a été trop largement : "
        "intrus joint de nouveau db. Une règle egress qui n'indique aucun `to` "
        "autorise toutes les destinations ; celle du DNS doit viser le "
        "résolveur, et seulement lui."
    )


# ----------------------------------------------------------------------
# 4. Et la base, elle, ne part pas se promener.
# ----------------------------------------------------------------------
def test_la_sortie_reste_fermee_vers_ce_qui_n_a_pas_ete_ouvert(host):
    """Le côté du zéro-confiance qu'on oublie en s'occupant des entrées.

    La cible est `annuaire`, un second serveur qui écoute vraiment. C'est
    indispensable : une requête vers un Pod qui n'écoute rien échoue de toute
    façon, et un test bâti sur une telle cible serait vrai avant le travail
    sans rien mesurer. Ici, avant le travail, les deux requêtes aboutissent.
    """
    assert not _joint(host, "db", "annuaire"), (
        "Le Pod db ouvre une connexion vers annuaire. Sa sortie n'est donc pas "
        "fermée : une politique par défaut qui déclare Egress sans aucune règle "
        "l'en empêcherait, sauf si une autre politique la lui rend."
    )
    assert not _joint(host, "web", "annuaire"), (
        "Le Pod web joint annuaire, alors que seule sa sortie vers db devait "
        "être rouverte. Une règle egress qui n'indique aucun `to` autorise "
        "toutes les destinations : nommez celle qui est permise."
    )
