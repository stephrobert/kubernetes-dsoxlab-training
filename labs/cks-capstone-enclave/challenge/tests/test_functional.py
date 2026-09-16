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

from conftest import lab_host, lab_target_host

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

    assert rc != 0, (
        f"Le namespace {ENCLAVE} a ACCEPTÉ un Pod privilégié. Une équipe qui "
        "n'est pas de confiance pourrait donc y déployer un conteneur qui voit "
        "le nœud entier. Le refus doit venir du cluster lui-même, à la "
        "création, et non d'une relecture humaine. Vérifiez l'orthographe "
        "exacte de ce que vous avez posé sur le namespace : une clé mal "
        "écrite est acceptée sans erreur et ne refuse rien."
    )
    assert "privileged" in (diagnostic + sortie).lower() or "forbidden" in (
        diagnostic + sortie
    ).lower(), (
        "Le Pod a bien été refusé, mais pas pour la raison attendue. Le "
        f"message était : {diagnostic or sortie}"
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
    assert rc == 0 and sortie, (
        f"Aucune identité applicative nommée {SA_ATTENDU} dans {ENCLAVE}. "
        "L'identité par défaut d'un namespace est partagée par tout ce qui y "
        f"tourne : elle ne peut pas porter des droits propres. {diagnostic}"
    )
    sa = json.loads(sortie)
    assert sa.get("automountServiceAccountToken") is False, (
        f"L'identité {SA_ATTENDU} laisse son jeton se déposer automatiquement "
        "dans les Pods qui l'emploient. Un jeton présent dans le conteneur est "
        "un jeton qu'un attaquant y trouve. Le champ se pose sur l'identité "
        "elle-même, où il vaut pour tout Pod qui l'emploie, plutôt que d'être "
        "répété dans chaque manifeste."
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
        assert rc != 0, (
            f"Le jeton est présent DANS le Pod {COFFRE}, à "
            "/var/run/secrets/kubernetes.io/serviceaccount, alors que "
            "l'identité dit ne pas le monter. Un Pod peut redemander le "
            "montage pour lui-même et annuler le réglage de l'identité : "
            "vérifiez que le manifeste du Pod ne le fait pas."
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

    assert _peut("list", "pods"), (
        f"L'identité {SA_ATTENDU} ne peut pas lister les charges de son propre "
        "espace, ce qui est le seul droit qu'on lui demandait. Un droit "
        "s'accorde en deux temps : une règle qui le décrit, et un lien qui "
        "l'attache au sujet. L'un sans l'autre n'accorde rien."
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
    assert not trop, (
        f"L'identité {SA_ATTENDU} peut faire plus que consulter la liste des "
        f"charges : {trop}. Le moindre privilège n'est pas « les droits dont "
        "l'application a besoin plus ceux qui pourraient servir un jour ». "
        "Attention aussi à la PORTÉE : un rôle de cluster vaut pour tout le "
        "cluster, y compris les espaces qui ne vous appartiennent pas."
    )

    assert not _peut("list", "pods", namespace=DEHORS), (
        f"L'identité {SA_ATTENDU} peut lister les charges du namespace "
        f"{DEHORS}, qui ne lui appartient pas. C'est la signature d'un rôle "
        "accordé à l'échelle du CLUSTER là où un rôle d'espace suffisait."
    )


# ----------------------------------------------------------------------
# 4. La charge tourne, et elle emploie cette identité.
# ----------------------------------------------------------------------
def test_le_coffre_tourne_et_emploie_l_identite(host):
    rc, sortie, diagnostic = _kubectl(host, f"-n {ENCLAVE} get pod {COFFRE} -o json")
    assert rc == 0 and sortie, (
        f"Aucune charge nommée {COFFRE} dans {ENCLAVE}. Si vous l'avez tentée "
        "et qu'elle a été refusée, le message de refus nomme le champ qui "
        "manque : le niveau d'admission que vous avez posé s'applique aussi à "
        f"vous. {diagnostic}"
    )
    pod = json.loads(sortie)
    phase = pod.get("status", {}).get("phase")
    assert phase == "Running", (
        f"La charge {COFFRE} est en {phase}. `kubectl -n {ENCLAVE} describe "
        f"pod {COFFRE}` dit dans ses events pourquoi elle ne démarre pas."
    )
    sa = pod["spec"].get("serviceAccountName")
    assert sa == SA_ATTENDU, (
        f"La charge {COFFRE} emploie l'identité « {sa} » et non "
        f"« {SA_ATTENDU} ». Sans l'avoir désignée, un Pod reçoit l'identité "
        "par défaut du namespace, qui est partagée par tout ce qui y tourne."
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

    assert passe, (
        f"Le Pod autorise, qui est DANS {ENCLAVE} et porte le label "
        f"role=appelant, ne joint pas {CIBLE}. Soit la charge ne sert pas "
        "encore, soit la protection que vous avez posée ferme aussi ce qui "
        "devait rester ouvert. Une politique d'entrée dont la clause "
        "d'admission liste deux sélecteurs en DEUX entrées ouvre bien plus "
        "large qu'en une seule ; écrite trop étroite, elle ne laisse passer "
        "personne."
    )

    fin = time.monotonic() + BUDGET_S
    intrus_passe = True
    while time.monotonic() < fin:
        intrus_passe = _joint(host, DEHORS, "intrus")
        if not intrus_passe:
            break
        time.sleep(PAS_S)

    assert not intrus_passe, (
        f"Le Pod intrus, qui est dans {DEHORS} et n'a rien à faire là, joint "
        f"toujours {CIBLE} après {BUDGET_S} secondes. Tant qu'aucune règle ne "
        "désigne une charge, tout lui parvient : c'est le comportement par "
        "défaut de Kubernetes, et c'est ce que l'enclave devait corriger."
    )
