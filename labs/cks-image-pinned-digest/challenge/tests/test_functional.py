"""test_functional.py : cks-image-pinned-digest

Trois affirmations qui lisent l'état du CLUSTER, jamais les commandes tapées.

La dernière est la seule qui prouve quelque chose. Chercher `@sha256:` dans le
champ `image` ne prouve que la FORME de la référence : une chaîne de la bonne
tête, copiée depuis une autre image ou inventée, passerait. Ce qui compte est
que le digest déclaré soit celui que le nœud a réellement résolu, et cela ne
se lit que dans l'état des Pods.

Le lab hérité de K8sExamLab s'arrêtait au `@sha256:`. C'est le genre de check
que le CLAUDE.md dit de tenir pour suspect par défaut : il valide une
apparence.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "chaine"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
DEPLOIEMENT = "pinned-app"
SELECTEUR = "app=pinned-app"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Joue une commande kubectl sur le control plane.

    Rend (code, sortie standard, diagnostic), et les trois restent SÉPARÉS :
    décider sur la concaténation de stdout et stderr revient à décider sur
    l'avertissement que le client SSH écrit toujours.
    """
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _deploiement(host) -> dict:
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT} -o json"
    )
    assert rc == 0 and sortie, message(
        en=f"Deployment {DEPLOIEMENT} no longer exists in {NAMESPACE}. Setup "
        "had placed it there: it had to be pinned, not replaced. Output: "
        f"{diagnostic}",
        fr=f"Le Deployment {DEPLOIEMENT} n'existe plus dans {NAMESPACE}. Le setup "
        "l'avait posé : il fallait l'épingler, pas le remplacer. Sortie : "
        f"{diagnostic}",
    )
    return json.loads(sortie)


def _digest(reference: str) -> str:
    """Le digest d'une référence d'image, ou une chaîne vide.

    Une référence peut s'écrire `nginx@sha256:abc`, `docker.io/library/nginx@sha256:abc`
    ou, pour un imageID, `docker.io/library/nginx@sha256:abc` aussi. Seule la
    partie après le dernier `@` compte, et c'est elle qu'on compare.
    """
    return reference.split("@")[-1] if "@" in reference else ""


# ----------------------------------------------------------------------
# 1. La référence n'est plus un tag.
#
# Ce fichier ne porte PAS de test « les deux exemplaires tournent », et c'est
# une correction, pas un oubli. Il en avait un, et la validation l'a rendu
# ROUGE : le Deployment tourne déjà en deux exemplaires quand le lab commence,
# donc ce test passait AVANT le travail et ne mesurait rien. Son assertion
# vit maintenant dans le dernier test, où elle ne peut être vraie qu'une fois
# l'épinglage fait.
# ----------------------------------------------------------------------
def test_l_image_n_est_plus_referencee_par_un_tag(host):
    d = _deploiement(host)
    image = d["spec"]["template"]["spec"]["containers"][0]["image"]
    assert "@sha256:" in image, message(
        en=f"The Deployment still references its image by a mutable name: \"{image}\". "
        "A tag can be repointed at another image without any manifest "
        "changing. The expected form is repository@sha256:<hexadecimal>.",
        fr=f"Le Deployment référence encore son image par un nom mutable : « {image} ». "
        "Un tag peut être repointé sur une autre image sans qu'aucun manifeste "
        "ne change. La forme attendue est dépôt@sha256:<hexadécimal>.",
    )
    assert ":1.27-alpine@" not in image, message(
        en=f"The reference \"{image}\" keeps the tag next to the digest. Kubernetes "
        "accepts that form and ignores the tag, but it suggests that the "
        "tag still counts: keep only the digest.",
        fr=f"La référence « {image} » garde le tag à côté du digest. Kubernetes "
        "accepte cette forme et ignore le tag, mais elle laisse croire que le "
        "tag compte encore : ne gardez que le digest.",
    )


# ----------------------------------------------------------------------
# 2. C'est toujours la même image, pas une autre version épinglée.
# ----------------------------------------------------------------------
def test_c_est_toujours_l_image_demandee(host):
    """Épingler en changeant d'image au passage répondrait à côté.

    On compare au digest que le nœud connaît pour `nginx:1.27-alpine`, lu
    auprès du runtime de conteneurs. C'est containerd qui répond, et `crictl`
    est son client en ligne de commande.
    """
    d = _deploiement(host)
    image = d["spec"]["template"]["spec"]["containers"][0]["image"]
    depot = image.split("@")[0]
    assert depot.split("/")[-1].split(":")[0] == "nginx", message(
        en=f"The reference points at \"{depot}\", and the specification asks "
        "for nginx to be pinned, not swapped.",
        fr=f"La référence pointe « {depot} », et le cahier des charges demande "
        "d'épingler nginx, pas d'en changer.",
    )

    res = host.run("sudo crictl inspecti -o json nginx:1.27-alpine")
    rc, sortie, diagnostic = res.rc, res.stdout.strip(), res.stderr.strip()
    assert rc == 0 and sortie, message(
        en="The node's runtime does not know nginx:1.27-alpine: there is no way to "
        f"check that the digest is the right one. {diagnostic}",
        fr="Le runtime du nœud ne connaît pas nginx:1.27-alpine : impossible de "
        f"vérifier que le digest est le bon. {diagnostic}",
    )
    connus = {
        _digest(reference)
        for reference in (json.loads(sortie).get("status") or {}).get("repoDigests", [])
    }
    assert _digest(image) in connus, message(
        en=f"The declared digest is not the one of nginx:1.27-alpine on this node. "
        f"Declared: {_digest(image)}. Known to the runtime: "
        f"{', '.join(sorted(connus)) or 'none'}.",
        fr=f"Le digest déclaré n'est pas celui de nginx:1.27-alpine sur ce nœud. "
        f"Déclaré : {_digest(image)}. Connu(s) du runtime : "
        f"{', '.join(sorted(connus)) or 'aucun'}.",
    )


# ----------------------------------------------------------------------
# 3. LE test : ce qui est déclaré est ce que le nœud exécute.
# ----------------------------------------------------------------------
def test_le_digest_declare_est_celui_que_le_noeud_execute(host):
    """La seule preuve qui distingue un épinglage d'une chaîne bien formée.

    `status.containerStatuses[].imageID` est écrit par le kubelet après que le
    runtime a résolu l'image. Il dit ce qui tourne, pas ce qu'on a demandé.
    Les deux doivent coïncider sur TOUS les exemplaires : un Deployment
    partiellement déployé aurait un Pod resté sur l'ancienne image.

    Ce test porte aussi la santé du déploiement, qui ne peut pas faire l'objet
    d'un test à part : deux exemplaires prêts, c'est vrai avant le travail
    comme après, et un test toujours vrai ne mesure rien. Ici la même
    assertion a du sens, parce qu'elle ne peut être atteinte qu'après un
    épinglage qui n'a rien cassé.
    """
    d = _deploiement(host)
    declare = _digest(d["spec"]["template"]["spec"]["containers"][0]["image"])
    assert declare, message(
        en="The Deployment declares no digest: it still references its image "
        "by a tag, and there is nothing to compare.",
        fr="Le Deployment ne déclare aucun digest : il référence encore son image "
        "par un tag, et il n'y a rien à comparer.",
    )

    prets = d.get("status", {}).get("readyReplicas", 0)
    assert prets == 2, message(
        en=f"{prets} replica(s) out of 2 are ready after the pinning. If the digest "
        "is malformed or matches no image in the registry, the Pod stays "
        "in ImagePullBackOff: look at its events.",
        fr=f"{prets} exemplaire(s) sur 2 sont prêts après l'épinglage. Si le digest "
        "est mal formé ou ne correspond à aucune image du registre, le Pod reste "
        "en ImagePullBackOff : regardez ses events.",
    )

    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} get pods -l {SELECTEUR} "
        "-o jsonpath='{range .items[*]}{.status.containerStatuses[0].imageID}{\"\\n\"}{end}'",
    )
    assert rc == 0 and sortie, message(
        en=f"No Pod of {DEPLOIEMENT} has a readable state. {diagnostic}",
        fr=f"Aucun Pod de {DEPLOIEMENT} n'a d'état lisible. {diagnostic}",
    )

    resolus = [ligne.strip() for ligne in sortie.splitlines() if ligne.strip()]
    assert len(resolus) == 2, message(
        en=f"{len(resolus)} replica(s) return their imageID; two are expected.",
        fr=f"{len(resolus)} exemplaire(s) rendent leur imageID, on en attend deux.",
    )
    ecarts = [r for r in resolus if _digest(r) != declare]
    assert not ecarts, message(
        en=f"The Deployment declares digest {declare}, but at least one replica "
        f"runs something else: {', '.join(ecarts)}.\n\n"
        "A reference that has the shape of a digest is not a pinning: "
        "that is what this test proves, and it is all that separates a chain "
        "copied from somewhere from a real guarantee of immutability. If the gap persists "
        "while the digest is correct, the rollout is not finished.",
        fr=f"Le Deployment déclare le digest {declare}, mais un exemplaire au "
        f"moins exécute autre chose : {', '.join(ecarts)}.\n\n"
        "Une référence qui a la forme d'un digest n'est pas un épinglage : "
        "c'est ce que prouve ce test, et c'est tout ce qui sépare une chaîne "
        "recopiée d'une vraie garantie d'immuabilité. Si l'écart persiste "
        "alors que le digest est juste, le déploiement n'est pas terminé.",
    )
