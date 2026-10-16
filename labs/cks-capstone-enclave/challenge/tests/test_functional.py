"""test_functional.py : cks-capstone-enclave

Cinq affirmations, une par exigence du scénario. Toutes lisent l'état réel du
cluster ou l'exercent ; aucune ne relit ce que le candidat a tapé.

Deux d'entre elles sont des preuves ACTIVES : plutôt que de relire un label ou
une règle, le test tente ce qui doit être refusé et constate le refus. C'est
la seule façon de distinguer une protection posée d'une protection qui agit.
Un label d'admission mal orthographié est accepté sans broncher par l'API et
ne refuse rien ; une NetworkPolicy dont le selector ne désigne personne est un
objet parfaitement valide qui ne protège rien.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ENCLAVE = "enclave"
DEHORS = "dehors"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
COFFRE = "coffre"
CIBLE = "http://coffre.enclave.svc.cluster.local/"
SA_ATTENDU = "coffre"

# Calico programme la règle après notification : elle n'agit pas à la seconde
# où l'API accepte l'objet. Budget borné, pour ne pas recaler un candidat dont
# la correction est juste.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _joint(host, namespace: str, pod: str) -> bool:
    rc, _, _ = _kubectl(
        host,
        f"-n {namespace} exec {pod} -c outil --request-timeout=30s "
        f"-- wget -qO- -T 5 {CIBLE}",
    )
    return rc == 0


# ----------------------------------------------------------------------
# 1. L'espace refuse lui-même ce qui ne doit pas y entrer.
# ----------------------------------------------------------------------
def test_l_espace_refuse_une_charge_privilegiee(host):
    """Preuve ACTIVE : on tente de créer un Pod privilégié.

    Relire les labels du namespace ne suffirait pas. Un label d'admission mal
    orthographié est accepté sans broncher par l'API, ne refuse rien, et se
    lit pourtant comme les autres.

    Le Pod est supprimé s'il a été créé : un test ne laisse pas de trace.
    """
    surcharge = (
        '{"spec":{"containers":[{"name":"x","image":"busybox:1.37",'
        '"securityContext":{"privileged":true}}]}}'
    )
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {ENCLAVE} run sonde-privilege --image=busybox:1.37 --restart=Never "
        f"--overrides='{surcharge}'",
    )
    if rc == 0:
        _kubectl(host, f"-n {ENCLAVE} delete pod sonde-privilege --ignore-not-found --wait=false")

    assert rc != 0, message(
        en=f"Namespace {ENCLAVE} ACCEPTED a privileged Pod. A team that "
        "is not trusted could therefore deploy a container there that sees "
        "the whole node. The refusal must come from the cluster itself, at "
        "creation time, and not from a human review. Check the exact "
        "spelling of what you placed on the namespace: a misspelled key "
        "is accepted without error and refuses nothing.",
        fr=f"Le namespace {ENCLAVE} a ACCEPTÉ un Pod privilégié. Une équipe qui "
        "n'est pas de confiance pourrait donc y déployer un conteneur qui voit "
        "le nœud entier. Le refus doit venir du cluster lui-même, à la "
        "création, et non d'une relecture humaine. Vérifiez l'orthographe "
        "exacte de ce que vous avez posé sur le namespace : une clé mal "
        "écrite est acceptée sans erreur et ne refuse rien.",
    )
    assert "privileged" in (diagnostic + sortie).lower() or "forbidden" in (
        diagnostic + sortie
    ).lower(), message(
        en="The Pod was indeed refused, but not for the expected reason. The "
        f"message was: {diagnostic or sortie}",
        fr="Le Pod a bien été refusé, mais pas pour la raison attendue. Le "
        f"message était : {diagnostic or sortie}",
    )


# ----------------------------------------------------------------------
# 2. L'identité existe, et son jeton ne se dépose pas dans les charges.
# ----------------------------------------------------------------------
def test_l_identite_existe_et_son_jeton_ne_se_monte_pas(host):
    """Les deux moitiés sont dans le même test : une identité dont le jeton se
    monte quand même ne vaut pas mieux que pas d'identité du tout."""
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {ENCLAVE} get serviceaccount {SA_ATTENDU} -o json"
    )
    assert rc == 0 and sortie, message(
        en=f"No application identity named {SA_ATTENDU} in {ENCLAVE}. "
        "A namespace's default identity is shared by everything running "
        f"there: it cannot carry rights of its own. {diagnostic}",
        fr=f"Aucune identité applicative nommée {SA_ATTENDU} dans {ENCLAVE}. "
        "L'identité par défaut d'un namespace est partagée par tout ce qui y "
        f"tourne : elle ne peut pas porter des droits propres. {diagnostic}",
    )
    sa = json.loads(sortie)
    assert sa.get("automountServiceAccountToken") is False, message(
        en=f"Identity {SA_ATTENDU} lets its token be mounted automatically "
        "into the Pods that use it. A token present in the container is "
        "a token an attacker finds there. The field is set on the identity "
        "itself, where it applies to every Pod using it, rather than being "
        "repeated in each manifest.",
        fr=f"L'identité {SA_ATTENDU} laisse son jeton se déposer automatiquement "
        "dans les Pods qui l'emploient. Un jeton présent dans le conteneur est "
        "un jeton qu'un attaquant y trouve. Le champ se pose sur l'identité "
        "elle-même, où il vaut pour tout Pod qui l'emploie, plutôt que d'être "
        "répété dans chaque manifeste.",
    )

    rc, phase, _ = _kubectl(
        host, f"-n {ENCLAVE} get pod {COFFRE} -o jsonpath='{{.status.phase}}'"
    )
    if rc == 0 and phase == "Running":
        rc, sortie, _ = _kubectl(
            host,
            f"-n {ENCLAVE} exec {COFFRE} --request-timeout=30s "
            "-- ls /var/run/secrets/kubernetes.io/serviceaccount",
        )
        assert rc != 0, message(
            en=f"The token is present INSIDE Pod {COFFRE}, at "
            "/var/run/secrets/kubernetes.io/serviceaccount, although "
            "the identity says not to mount it. A Pod can ask for the "
            "mount for itself and override the identity's setting: "
            "check that the Pod's manifest does not do so.",
            fr=f"Le jeton est présent DANS le Pod {COFFRE}, à "
            "/var/run/secrets/kubernetes.io/serviceaccount, alors que "
            "l'identité dit ne pas le monter. Un Pod peut redemander le "
            "montage pour lui-même et annuler le réglage de l'identité : "
            "vérifiez que le manifeste du Pod ne le fait pas.",
        )


# ----------------------------------------------------------------------
# 3. Cette identité ne peut presque rien.
# ----------------------------------------------------------------------
def test_l_identite_peut_lister_les_charges_et_rien_d_autre(host):
    """On interroge le moteur d'autorisation lui-même, ce qui vaut mieux que
    de relire un Role : c'est la SOMME des droits accordés qui compte, et un
    candidat peut en avoir accordé ailleurs sans s'en rendre compte."""
    sujet = f"system:serviceaccount:{ENCLAVE}:{SA_ATTENDU}"

    def _peut(verbe: str, ressource: str, namespace: str = ENCLAVE) -> bool:
        _, sortie, _ = _kubectl(
            host, f"auth can-i {verbe} {ressource} --as={sujet} -n {namespace}"
        )
        return sortie.strip() == "yes"

    assert _peut("list", "pods"), message(
        en=f"Identity {SA_ATTENDU} cannot list the workloads of its own "
        "space, which is the only right it was being granted. A right "
        "is granted in two steps: a rule that describes it, and a binding that "
        "attaches it to the subject. One without the other grants nothing.",
        fr=f"L'identité {SA_ATTENDU} ne peut pas lister les charges de son propre "
        "espace, ce qui est le seul droit qu'on lui demandait. Un droit "
        "s'accorde en deux temps : une règle qui le décrit, et un lien qui "
        "l'attache au sujet. L'un sans l'autre n'accorde rien.",
    )

    trop = [
        f"{v} {r}"
        for v, r in (
            ("get", "secrets"),
            ("list", "secrets"),
            ("create", "pods"),
            ("delete", "pods"),
        )
        if _peut(v, r)
    ]
    assert not trop, message(
        en=f"Identity {SA_ATTENDU} can do more than list the "
        f"workloads: {trop}. Least privilege is not \"the rights the "
        "application needs plus those that might come in handy one day\". "
        "Mind the SCOPE too: a cluster role applies to the whole "
        "cluster, including the spaces that are not yours.",
        fr=f"L'identité {SA_ATTENDU} peut faire plus que consulter la liste des "
        f"charges : {trop}. Le moindre privilège n'est pas « les droits dont "
        "l'application a besoin plus ceux qui pourraient servir un jour ». "
        "Attention aussi à la PORTÉE : un rôle de cluster vaut pour tout le "
        "cluster, y compris les espaces qui ne vous appartiennent pas.",
    )

    assert not _peut("list", "pods", namespace=DEHORS), message(
        en=f"Identity {SA_ATTENDU} can list the workloads of namespace "
        f"{DEHORS}, which does not belong to it. That is the signature of a role "
        "granted at CLUSTER scope where a namespaced role was enough.",
        fr=f"L'identité {SA_ATTENDU} peut lister les charges du namespace "
        f"{DEHORS}, qui ne lui appartient pas. C'est la signature d'un rôle "
        "accordé à l'échelle du CLUSTER là où un rôle d'espace suffisait.",
    )


# ----------------------------------------------------------------------
# 4. La charge tourne, et elle emploie cette identité.
# ----------------------------------------------------------------------
def test_le_coffre_tourne_et_emploie_l_identite(host):
    rc, sortie, diagnostic = _kubectl(host, f"-n {ENCLAVE} get pod {COFFRE} -o json")
    assert rc == 0 and sortie, message(
        en=f"No workload named {COFFRE} in {ENCLAVE}. If you attempted it "
        "and it was refused, the refusal message names the field that is "
        "missing: the admission level you set applies to "
        f"you too. {diagnostic}",
        fr=f"Aucune charge nommée {COFFRE} dans {ENCLAVE}. Si vous l'avez tentée "
        "et qu'elle a été refusée, le message de refus nomme le champ qui "
        "manque : le niveau d'admission que vous avez posé s'applique aussi à "
        f"vous. {diagnostic}",
    )
    pod = json.loads(sortie)
    phase = pod.get("status", {}).get("phase")
    assert phase == "Running", message(
        en=f"Workload {COFFRE} is {phase}. `kubectl -n {ENCLAVE} describe "
        f"pod {COFFRE}` says in its events why it does not start.",
        fr=f"La charge {COFFRE} est en {phase}. `kubectl -n {ENCLAVE} describe "
        f"pod {COFFRE}` dit dans ses events pourquoi elle ne démarre pas.",
    )
    sa = pod["spec"].get("serviceAccountName")
    assert sa == SA_ATTENDU, message(
        en=f"Workload {COFFRE} uses identity \"{sa}\" and not "
        f"\"{SA_ATTENDU}\". Without naming one, a Pod receives the "
        "namespace's default identity, which is shared by everything running there.",
        fr=f"La charge {COFFRE} emploie l'identité « {sa} » et non "
        f"« {SA_ATTENDU} ». Sans l'avoir désignée, un Pod reçoit l'identité "
        "par défaut du namespace, qui est partagée par tout ce qui y tourne.",
    )


# ----------------------------------------------------------------------
# 5. LE test : rien n'atteint le coffre hors de l'enclave.
# ----------------------------------------------------------------------
def test_seul_l_appelant_declare_atteint_le_coffre(host):
    """Preuve ACTIVE, et dans les deux sens.

    Les deux mesures sont dans le MÊME test, délibérément. « L'intrus ne joint
    pas le coffre » serait vert AVANT le travail pour la plus mauvaise des
    raisons : le coffre n'existe pas encore. C'est en exigeant d'abord que
    l'appelant déclaré passe qu'on écarte ce faux vert.
    """
    fin = time.monotonic() + BUDGET_S
    passe = False
    while time.monotonic() < fin:
        passe = _joint(host, ENCLAVE, "autorise")
        if passe:
            break
        time.sleep(PAS_S)

    assert passe, message(
        en=f"Pod autorise, which is INSIDE {ENCLAVE} and carries the label "
        f"role=appelant, does not reach {CIBLE}. Either the workload does not serve "
        "yet, or the protection you set also closes what "
        "had to stay open. An ingress policy whose from clause "
        "lists two selectors as TWO entries opens far "
        "wider than as a single one; written too narrow, it lets "
        "nobody through.",
        fr=f"Le Pod autorise, qui est DANS {ENCLAVE} et porte le label "
        f"role=appelant, ne joint pas {CIBLE}. Soit la charge ne sert pas "
        "encore, soit la protection que vous avez posée ferme aussi ce qui "
        "devait rester ouvert. Une politique d'entrée dont la clause "
        "d'admission liste deux sélecteurs en DEUX entrées ouvre bien plus "
        "large qu'en une seule ; écrite trop étroite, elle ne laisse passer "
        "personne.",
    )

    fin = time.monotonic() + BUDGET_S
    intrus_passe = True
    while time.monotonic() < fin:
        intrus_passe = _joint(host, DEHORS, "intrus")
        if not intrus_passe:
            break
        time.sleep(PAS_S)

    assert not intrus_passe, message(
        en=f"Pod intrus, which is in {DEHORS} and has no business there, still "
        f"reaches {CIBLE} after {BUDGET_S} seconds. As long as no rule "
        "selects a workload, everything reaches it: that is Kubernetes' default "
        "behaviour, and that is what the enclave had to correct.",
        fr=f"Le Pod intrus, qui est dans {DEHORS} et n'a rien à faire là, joint "
        f"toujours {CIBLE} après {BUDGET_S} secondes. Tant qu'aucune règle ne "
        "désigne une charge, tout lui parvient : c'est le comportement par "
        "défaut de Kubernetes, et c'est ce que l'enclave devait corriger.",
    )
