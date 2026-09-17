"""test_functional.py : cka-resourcequota-limitrange

Deux affirmations, et les deux sont des preuves ACTIVES : plutôt que de relire
les objets posés, le test tente ce qui doit être refusé et ce qui doit passer,
puis constate.

C'est la seule façon de distinguer une contrainte posée d'une contrainte qui
agit. Un ResourceQuota dont le champ `hard` ne porte pas sur les bonnes
ressources est un objet parfaitement valide qui ne plafonne rien ; un
LimitRange dont le `type` n'est pas le bon ne complète aucun conteneur.

Les Pods sondes sont supprimés après usage : un test ne laisse pas de trace.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "equipe-produit"
DEPLOYMENT = "catalogue"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Très au-dessus de ce qu'un nœud de ce lab peut offrir : sans quota, l'API
# l'accepte quand même et le Pod reste Pending, faute de place. C'est
# exactement la différence que ce lab fait constater, un refus À LA CRÉATION
# plutôt qu'un Pod qui attend indéfiniment.
CPU_EXCESSIF = "64"
MEM_EXCESSIVE = "8Gi"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _supprimer(host, pod: str) -> None:
    """Supprime une sonde et ATTEND sa disparition.

    L'attente n'est pas du zèle, et c'est le validateur qui l'a montré : une
    suppression lancée sans attendre laisse le Pod en cours de suppression, et
    le check suivant, qui le recrée, se heurte à « object is being deleted:
    pods "sonde-sans" already exists ». Le test échouait alors pour une course,
    pas pour ce qu'il mesure.
    """
    _kubectl(
        host,
        f"-n {NAMESPACE} delete pod {pod} --ignore-not-found "
        "--wait=true --timeout=90s",
    )


# ----------------------------------------------------------------------
# 1. Le namespace refuse ce qui dépasse son plafond.
# ----------------------------------------------------------------------
def test_le_namespace_refuse_un_pod_qui_demande_trop(host):
    """Preuve ACTIVE : on tente de créer un Pod qui demande 64 CPU.

    Sans plafond, l'API l'accepte et le Pod reste Pending faute de place : rien
    ne le refuse, il attend. Avec un plafond, il est refusé à la création, et
    c'est cette différence qui est mesurée.
    """
    surcharge = (
        '{"spec":{"containers":[{"name":"x","image":"busybox:1.37",'
        '"command":["sh","-c","sleep 5"],"resources":{'
        f'"requests":{{"cpu":"{CPU_EXCESSIF}","memory":"{MEM_EXCESSIVE}"}},'
        f'"limits":{{"cpu":"{CPU_EXCESSIF}","memory":"{MEM_EXCESSIVE}"}}'
        '}}]}}'
    )
    _supprimer(host, "sonde-trop")
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} run sonde-trop --image=busybox:1.37 --restart=Never "
        f"--overrides='{surcharge}'",
    )
    if rc == 0:
        _supprimer(host, "sonde-trop")

    assert rc != 0, (
        f"Le namespace {NAMESPACE} a ACCEPTÉ un Pod demandant {CPU_EXCESSIF} "
        "CPU. Sans plafond, l'API accepte et le Pod attend indéfiniment une "
        "place qui n'existe pas : personne ne l'a refusé, et le quota de "
        "l'équipe n'existe pas. Le refus doit venir du namespace, à la "
        "création."
    )
    assert "exceeded quota" in (diagnostic + sortie).lower(), (
        "Le Pod a bien été refusé, mais pas par le plafond du namespace. "
        "Mesuré le 2026-09-17 : un plafond atteint rend « exceeded quota: "
        "<nom>, requested: …, limited: … », tandis qu'un refus venu des "
        "valeurs par défaut rend « must be less than or equal to cpu limit ». "
        f"Le message était : {diagnostic or sortie}"
    )


# ----------------------------------------------------------------------
# 2. LE test : un Pod qui ne déclare rien passe, et repart complété.
# ----------------------------------------------------------------------
def test_un_pod_sans_requests_est_accepte_et_complete(host):
    """Preuve ACTIVE, et c'est la moitié que le plafond seul casserait.

    Un quota qui porte sur les `requests` rend invalide tout Pod qui n'en
    déclare pas : « must specify requests.cpu ». L'oubli d'un développeur
    devient alors un refus incompréhensible. Les valeurs par défaut le
    réconcilient, et ce test le vérifie dans les deux sens : le Pod est
    accepté, ET il repart avec des ressources qu'il n'avait pas déclarées.

    Le dernier contrôle vérifie que l'application posée par le setup tourne
    encore : un plafond trop bas l'empêcherait de se replacer, et ce serait une
    panne, pas une maîtrise des ressources.
    """
    _supprimer(host, "sonde-sans")
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} run sonde-sans --image=busybox:1.37 --restart=Never "
        "--command -- sh -c 'sleep 60'",
    )
    assert rc == 0, (
        "Un Pod qui ne déclare aucune ressource a été REFUSÉ par le namespace "
        f"{NAMESPACE} : {diagnostic or sortie}. C'est l'effet d'un plafond "
        "posé seul : dès qu'un quota porte sur les requests, un Pod qui n'en "
        "déclare pas devient invalide, l'API ne pouvant décompter ce qui n'est "
        "pas déclaré. Il manque de quoi compléter ces Pods à leur arrivée."
    )

    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get pod sonde-sans -o json"
    )
    assert rc == 0 and sortie, f"Le Pod sonde-sans a disparu. {diagnostic}"
    ressources = json.loads(sortie)["spec"]["containers"][0].get("resources", {})
    _supprimer(host, "sonde-sans")

    requests = ressources.get("requests", {})
    limits = ressources.get("limits", {})
    assert requests.get("cpu") and requests.get("memory"), (
        f"Le Pod a été accepté mais repart sans requests : {ressources}. Il "
        "sera donc placé à l'aveugle, et ne comptera pour rien dans le "
        "plafond. Ce qui manque n'est pas le quota mais ce qui complète un "
        "conteneur qui ne déclare rien, à son arrivée dans le namespace."
    )
    assert limits.get("cpu") and limits.get("memory"), (
        f"Le Pod repart avec des requests mais sans limits : {ressources}. "
        "Les deux se règlent au même endroit, par deux champs distincts : l'un "
        "alimente ce que le conteneur DEMANDE, l'autre ce qu'il ne pourra pas "
        "DÉPASSER."
    )

    rc, pretes, _ = _kubectl(
        host,
        f"-n {NAMESPACE} get deployment {DEPLOYMENT} "
        "-o jsonpath='{.status.readyReplicas}'",
    )
    assert rc == 0 and pretes == "1", (
        f"L'application {DEPLOYMENT} n'a plus d'exemplaire prêt "
        f"(« {pretes or 'aucun'} »). Un plafond trop bas l'empêche de se "
        "replacer quand elle redémarre : c'est une panne, pas une maîtrise des "
        "ressources. Elle demande 50m de CPU et 32Mi de mémoire."
    )
