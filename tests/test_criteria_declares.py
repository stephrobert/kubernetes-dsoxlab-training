"""Chaque lab déclare ses `criteria`, en anglais ET en français.

CE QUE CE GARDE-FOU TIENT, et pourquoi il n'existait pas avant lui.

Le lot pilote de la PR #124 a posé la règle : un test vérifie un seul état
demandé, et les états sont regroupés en `criteria` déclarés dans `lab.yaml`
(id, label, tests, lessons) et dans `lab.fr.yaml` (id, label français, appariés
par id). Cinq labs l'ont adoptée.

Mesuré le 2026-11-10 : **aucun test du dépôt ne contrôlait cette règle.** Un lab
livré sans `criteria` passait toute la chaîne sans qu'un seul contrôle le dise,
et c'est une contre-expertise manuelle qui a dû le relever, lab par lab. Une
règle que personne ne mesure n'est pas une règle, c'est une intention.

POURQUOI UNE LISTE DE DETTE PLUTÔT QU'UN REFUS SEC. 59 des 64 labs n'ont pas
encore de `criteria` le jour où ce contrôle est écrit. Les refuser tous rendrait
ce test rouge en permanence, et un contrôle rouge en permanence, qu'on fusionne
par-dessus, ne contrôle plus rien : on apprend à l'ignorer, puis il ne voit plus
rien du tout.

La dette est donc NOMMÉE, DATÉE, et contrôlée DANS LES DEUX SENS :

  - un lab hors de la liste doit déclarer ses `criteria` : c'est le sens qui
    empêche la dette de grandir ;
  - un lab de la liste qui en déclare doit SORTIR de la liste : c'est le sens
    qui empêche la liste de se périmer. Sans lui, elle resterait pleine de noms
    qui n'ont plus rien à y faire, et elle finirait par couvrir des labs qu'elle
    n'a jamais eu à couvrir.

La liste doit donc DÉCROÎTRE, et ce fichier est le seul endroit où l'on constate
qu'elle décroît.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

RACINE = pathlib.Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"

#: Les labs qui n'ont pas encore été repris par le chantier de conformité.
#:
#: Relevé le 2026-11-10 : 59 labs sur les 64 que git suit. Descendue à 54 le
#: même jour, les cinq labs du module `ressources-de-base` ayant été repris. La liste est
#: construite sur les labs SUIVIS, délibérément : des squelettes non versionnés
#: traînaient dans l'arbre de travail ce jour-là, et les inscrire ici aurait
#: produit une dette fausse dès sa naissance, qui nomme ce qui n'existe pas.
#:
#: CHAQUE RETRAIT DE CETTE LISTE EST UN LAB MIS EN CONFORMITÉ. On n'y ajoute
#: rien : un lab nouveau naît conforme, c'est le sens même de la règle.
DETTE: set[str] = {
    "cka-capstone-portail",
    "cka-daemonset-all-nodes",
    "cka-gateway-api-httproute",
    "cka-hpa-autoscaling",
    "cka-ingress-path-routing",
    "cka-kubeadm-upgrade",
    "cka-node-affinity",
    "cka-node-drain-cordon",
    "cka-rbac-serviceaccount",
    "cka-resourcequota-limitrange",
    "cka-storageclass-provisionnement-dynamique",
    "cka-taints-tolerations-placement",
    "cka-troubleshoot-crashloopbackoff",
    "cka-troubleshoot-dns",
    "cka-troubleshoot-imagepullbackoff",
    "cka-troubleshoot-networking",
    "ckad-capstone-boutique",
    "ckad-helm-install-upgrade",
    "ckad-networkpolicy-ingress-egress",
    "ckad-rbac-role-rolebinding",
    "ckad-security-context-hardened",
    "ckad-troubleshoot-crashloop",
    "ckad-troubleshoot-missing-configmap",
    "cks-api-server-hardening",
    "cks-apparmor-confiner-un-pod",
    "cks-capstone-enclave",
    "cks-cis-benchmark-remediate",
    "cks-cosign-verify-image",
    "cks-dockerfile-static-analysis",
    "cks-image-pinned-digest",
    "cks-image-scanning-trivy",
    "cks-ingress-tls",
    "cks-istio-mtls-lockdown",
    "cks-networkpolicy-default-deny",
    "cks-pod-security-admission",
    "cks-rbac-least-privilege",
    "cks-runtime-sandbox-gvisor",
    "cks-seccomp-profile",
    "cks-secure-existing-pod",
    "cks-security-context-immutable",
    "cks-validating-admission-policy",
}


def labs() -> list[pathlib.Path]:
    return sorted(p.parent for p in LABS.glob("*/lab.yaml"))


def _contrat(lab: pathlib.Path, nom: str) -> dict:
    fichier = lab / nom
    if not fichier.is_file():
        return {}
    return yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}


def test_le_glob_regarde_quelque_chose() -> None:
    """Le garde-fou de ce garde-fou.

    Un motif cassé ne trouve aucun lab, et un contrôle qui n'itère sur rien
    passe au vert sans avoir rien mesuré. C'est la panne la plus silencieuse
    qu'un test puisse avoir, et elle ne se voit jamais dans un rapport vert.
    """
    trouves = labs()
    assert len(trouves) >= 60, (
        f"{len(trouves)} lab(s) trouvé(s) sous labs/*/lab.yaml, alors que le "
        "catalogue en porte plus de soixante. Le motif ne regarde plus au bon "
        "endroit, et ce fichier ne mesure donc rien."
    )


@pytest.mark.parametrize("lab", labs(), ids=lambda p: p.name)
def test_chaque_lab_hors_dette_declare_ses_criteres(lab: pathlib.Path) -> None:
    """Sens 1 : la dette ne grandit pas."""
    if lab.name in DETTE:
        pytest.skip(f"{lab.name} : dette de conformité déclarée, relevée le 2026-11-10")
    criteres = _contrat(lab, "lab.yaml").get("criteria")
    assert criteres, (
        f"{lab.name}/lab.yaml ne déclare aucun `criteria`.\n"
        "        Un lab sans critères ne peut rendre aucun état par exigence : "
        "l'apprenant reçoit un score et rien d'autre.\n"
        "        Si ce lab est en cours de reprise, il n'a pas sa place ici "
        "avant d'être conforme ; la liste DETTE ne s'enrichit pas."
    )


@pytest.mark.parametrize("lab", labs(), ids=lambda p: p.name)
def test_les_criteres_sont_traduits_et_apparies_par_id(lab: pathlib.Path) -> None:
    """Sens 1 bis : des critères déclarés sont des critères traduits.

    Les `id` font foi des deux côtés, et c'est l'appariement PAR ID qui est
    contrôlé, pas la position : deux listes de même longueur dans un ordre
    différent décriraient autre chose que ce qu'elles prétendent.
    """
    criteres = _contrat(lab, "lab.yaml").get("criteria")
    if not criteres:
        pytest.skip(f"{lab.name} : aucun critère, c'est l'autre test qui le juge")
    ids_en = [c.get("id") for c in criteres]
    ids_fr = [c.get("id") for c in (_contrat(lab, "lab.fr.yaml").get("criteria") or [])]
    manquants = sorted(set(ids_en) - set(ids_fr))
    assert not manquants, (
        f"{lab.name}/lab.fr.yaml ne traduit pas {len(manquants)} critère(s) : "
        f"{', '.join(manquants)}.\n"
        "        Un critère affiché en anglais à une session française est le "
        "défaut que l'i18n du moteur existe pour empêcher."
    )
    en_trop = sorted(set(ids_fr) - set(ids_en))
    assert not en_trop, (
        f"{lab.name}/lab.fr.yaml traduit {len(en_trop)} critère(s) qui n'existent "
        f"pas côté anglais : {', '.join(en_trop)}.\n"
        "        Un libellé sans critère ne s'affiche jamais : il décrit un état "
        "que le moteur ne mesure pas."
    )


def test_la_dette_ne_designe_que_des_labs_qui_en_ont_encore_une() -> None:
    """Sens 2 : la liste ne se périme pas.

    Sans ce contrôle, un lab mis en conformité resterait indéfiniment dans la
    liste, et la dette afficherait un chiffre plus gros que la réalité. Pire :
    le jour où ce lab régresserait, la liste le couvrirait encore.
    """
    presents = {p.name for p in labs()}
    fantomes = sorted(DETTE - presents)
    assert not fantomes, (
        f"DETTE nomme {len(fantomes)} lab(s) qui n'existent pas : "
        f"{', '.join(fantomes)}.\n"
        "        Une tolérance qui désigne le vide ne tolère rien ; elle fausse "
        "le compte de ce qui reste à faire."
    )
    soldes = sorted(
        nom for nom in DETTE
        if nom in presents and _contrat(LABS / nom, "lab.yaml").get("criteria")
    )
    assert not soldes, (
        f"{len(soldes)} lab(s) déclarent leurs `criteria` mais sont encore dans "
        f"DETTE : {', '.join(soldes)}.\n"
        "        Retirez-les de la liste : c'est ce retrait qui fait baisser la "
        "dette, et c'est la seule trace que le chantier avance."
    )
