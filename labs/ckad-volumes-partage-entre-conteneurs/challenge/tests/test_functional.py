"""test_functional.py : ckad-volumes-partage-entre-conteneurs

Ces tests lisent l'état réel des conteneurs du Pod collecteur, jamais les
commandes tapées. Un test vérifie un seul état demandé par l'énoncé.

Le dernier test est celui qui compte : un candidat qui monterait le volume sur
la RACINE des deux conteneurs ferait passer le deuxième sans avoir compris ce
qu'un volume partage. On écrit donc un fichier HORS du volume et on vérifie
qu'il ne traverse pas. Ce test exige d'abord que le partage fonctionne : sans
cette précondition, il serait vrai dès l'état de départ, où le lecteur ne voit
rien du tout.

Tous échouent avant le travail : le Pod posé par le setup n'a aucun volume.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NS = "journalisation"
POD = "collecteur"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
CHEMIN = "/var/trace/messages"
HORS_VOLUME = "/var/hors-volume"
IMAGE = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

# Kubernetes PROJETTE de lui-même le jeton du ServiceAccount dans chaque
# conteneur, sous un volume nommé `kube-api-access-xxxxx`. Un Pod qui ne
# déclare aucun volume en a donc un, monté des deux côtés. Mesuré le
# 2026-09-17 par le validateur : sans ce filtre, le premier test passait AVANT
# le travail.
VOLUME_AUTOMATIQUE = "kube-api-access-"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} get pod {POD} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _dans(host, conteneur: str, commande: str):
    return host.run(f"{ADMIN} -n {NS} exec {POD} -c {conteneur} --request-timeout=30s -- sh -c '{commande}'")


def _absent() -> str:
    return message(
        en=f"Pod {POD} cannot be found in {NS}. The setup had placed it there: it must be recreated "
        "under the same name, with the same two containers.",
        fr=f"Le Pod {POD} est introuvable dans {NS}. Le setup l'avait posé : il doit être recréé sous "
        "le même nom, avec les deux mêmes conteneurs.",
    )


# ----------------------------------------------------------------------
# 1. Un volume éphémère est monté, au même chemin, dans les deux conteneurs.
# ----------------------------------------------------------------------
def test_un_volume_ephemere_est_monte_dans_les_deux_conteneurs(host):
    pod = _pod(host)
    assert pod is not None, _absent()
    spec = pod["spec"]
    volumes = {v["name"]: v for v in spec.get("volumes") or [] if not v["name"].startswith(VOLUME_AUTOMATIQUE)}
    montes = {c["name"]: {m["name"]: m.get("mountPath") for m in c.get("volumeMounts") or [] if m["name"] in volumes}
              for c in spec.get("containers") or []}
    images = {c["name"]: c.get("image") for c in spec.get("containers") or []}
    communs = [n for n in volumes if all(n in m for m in montes.values()) and len(montes) == 2
               and len({m[n] for m in montes.values()}) == 1]
    assert set(montes) == {"producteur", "lecteur"} and set(images.values()) == {IMAGE}, message(
        en=f"{POD} must keep its two containers, producteur and lecteur, on the image of the requirements "
        f"(found: {images}).",
        fr=f"{POD} doit garder ses deux conteneurs, producteur et lecteur, sur l'image du cahier des "
        f"charges (trouvé : {images}).",
    )
    assert communs, message(
        en=f"The two containers mount no volume IN COMMON at the same path (mounts: { {k: v for k, v in montes.items()} }). "
        "Mounting two different volumes, one per container, shares nothing.",
        fr=f"Les deux conteneurs ne montent aucun volume EN COMMUN au même chemin (montages : "
        f"{ {k: v for k, v in montes.items()} }). Monter deux volumes différents, un par conteneur, ne "
        "partage rien.",
    )
    assert any("emptyDir" in volumes[n] for n in communs), message(
        en="The shared volume is not of a type that is born and dies with the Pod: nothing must be kept "
        "after the Pod disappears.",
        fr="Le volume partagé n'est pas d'un type qui naît et meurt avec le Pod : rien ne doit être "
        "conservé après la disparition du Pod.",
    )


# ----------------------------------------------------------------------
# 2. Le lecteur voit le fichier du producteur.
# ----------------------------------------------------------------------
def test_le_lecteur_voit_le_fichier_du_producteur(host):
    pod = _pod(host)
    assert pod is not None, _absent()
    assert pod["status"].get("phase") == "Running", message(
        en=f"Pod {POD} is in phase {pod['status'].get('phase')!r}: both containers must run.",
        fr=f"Le Pod {POD} est en phase {pod['status'].get('phase')!r} : les deux conteneurs doivent tourner.",
    )
    res = _dans(host, "lecteur", f"test -s {CHEMIN}")
    assert res.rc == 0, message(
        en=f"The lecteur container does not find {CHEMIN}, or finds it empty, although the producer writes "
        "into it every five seconds. A volume mounted elsewhere on the reader's side shows it nothing.",
        fr=f"Le conteneur lecteur ne trouve pas {CHEMIN}, ou le trouve vide, alors que le producteur y écrit "
        "toutes les cinq secondes. Un volume monté ailleurs chez le lecteur ne lui montre rien.",
    )


# ----------------------------------------------------------------------
# 3. Ce que le producteur écrit hors du volume reste invisible au lecteur.
# ----------------------------------------------------------------------
def test_ce_qui_est_ecrit_hors_du_volume_reste_invisible_au_lecteur(host):
    pod = _pod(host)
    assert pod is not None, _absent()
    partage = _dans(host, "lecteur", f"test -s {CHEMIN}").rc == 0
    assert partage, message(
        en=f"The lecteur does not see {CHEMIN} yet: isolation means nothing before sharing works.",
        fr=f"Le lecteur ne voit pas encore {CHEMIN} : l'isolation ne veut rien dire avant que le partage "
        "fonctionne.",
    )
    _dans(host, "producteur", f"echo prive > {HORS_VOLUME}")
    traverse = _dans(host, "lecteur", f"test -f {HORS_VOLUME}").rc == 0
    _dans(host, "producteur", f"rm -f {HORS_VOLUME}")
    assert not traverse, message(
        en=f"A file written by the producer OUTSIDE the volume, in {HORS_VOLUME}, is visible to the reader. "
        "The two containers share far more than the requested directory: that is the signature of a "
        "volume mounted too high, on the root or on /var.",
        fr=f"Un fichier écrit par le producteur HORS du volume, dans {HORS_VOLUME}, est visible par le "
        "lecteur. Les deux conteneurs partagent bien plus que le répertoire demandé : c'est la signature "
        "d'un volume monté trop haut, sur la racine ou sur /var.",
    )
