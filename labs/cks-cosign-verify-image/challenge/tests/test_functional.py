"""test_functional.py : cks-cosign-verify-image

Trois affirmations qui interrogent le registre et l'outil sur le nœud, jamais
les commandes tapées.

Le dernier test est le seul qui prouve quelque chose, et il tient en une
phrase : la même clé doit **accepter** l'image signée et **refuser** l'autre.

Vérifier seulement l'acceptation ne mesurerait rien. Une vérification mal
formée, une clé absente lue comme vide, un outil qui sort en erreur avant
d'avoir regardé : tous ces cas peuvent rendre « accepté » sans qu'aucune
signature n'ait été contrôlée. C'est le refus qui donne sa valeur à
l'acceptation, et le registre porte exprès une image que personne n'a signée.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "chaine-signature"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CONFIGMAP = "cosign-pub-key"
IMAGE_SIGNEE = "localhost:5000/appli/web:1.0"
IMAGE_NUE = "localhost:5000/appli/outil:1.0"
CLE_PUBLIQUE = "/root/cosign.pub"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _verifie(host, image: str) -> bool:
    """cosign accepte-t-il cette image avec la clé publique du candidat ?

    La clé employée est celle du ConfigMap, écrite dans un fichier temporaire :
    c'est ce qu'un tiers ferait, et cela vérifie du même coup que la clé
    publiée est utilisable, pas seulement présente.
    """
    res = host.run(
        "set -e; "
        f"sudo {KUBECTL} -n {NAMESPACE} get configmap {CONFIGMAP} "
        "-o jsonpath='{.data.cosign\\.pub}' > /tmp/verif-cosign.pub; "
        f"sudo cosign verify --key /tmp/verif-cosign.pub {image} >/dev/null 2>&1; "
        "echo $?"
    )
    return res.stdout.strip().endswith("0")


# ----------------------------------------------------------------------
# 1. La clé publique est publiée, et c'est bien une clé publique.
# ----------------------------------------------------------------------
def test_la_cle_publique_est_publiee_dans_le_cluster(host):
    """Publier la clé PUBLIQUE permet à d'autres de vérifier sans jamais
    toucher à la clé privée. C'est tout l'intérêt d'une paire."""
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get configmap {CONFIGMAP} -o json"
    )
    assert rc == 0 and sortie, (
        f"Aucun ConfigMap {CONFIGMAP} dans {NAMESPACE}. Sortie : {diagnostic}"
    )
    donnees = json.loads(sortie).get("data") or {}
    contenu = "\n".join(str(v) for v in donnees.values())
    assert "BEGIN PUBLIC KEY" in contenu, (
        f"Le ConfigMap {CONFIGMAP} ne contient pas de clé publique lisible. Il "
        f"porte {sorted(donnees)}. Le fichier attendu est celui que cosign "
        "écrit sous le nom cosign.pub."
    )
    assert "PRIVATE KEY" not in contenu, (
        "Le ConfigMap contient une clé PRIVÉE. C'est exactement ce que la "
        "chaîne d'approvisionnement cherche à éviter : qui la lit peut signer "
        "n'importe quelle image en votre nom. Seule la clé publique se publie."
    )


# ----------------------------------------------------------------------
# 2. La signature existe réellement dans le registre.
# ----------------------------------------------------------------------
def test_la_signature_est_poussee_dans_le_registre(host):
    """cosign range la signature à côté de l'image, dans le même dépôt, sous
    un tag dérivé du digest.

    ATTENTION AU NOM DU TAG, et c'est un piège de version mesuré le
    2026-09-16. Les versions antérieures de cosign suffixaient ce tag par
    `.sig`, et tous les articles sur le sujet le disent encore. **cosign 3.1.3
    ne le fait plus** : le dépôt porte `sha256-<digest>`, sans suffixe. Une
    première version de ce test cherchait `.sig`, ne trouvait rien, et
    déclarait qu'aucune signature n'avait été poussée alors qu'elle était là.

    On reconnaît donc la signature à son PRÉFIXE, qui n'a pas changé.
    """
    res = host.run("sudo crane ls localhost:5000/appli/web 2>/dev/null")
    assert res.rc == 0, (
        "Le registre local ne répond pas. Le setup le monte en hostNetwork sur "
        f"le port 5000 du nœud. Sortie : {res.stderr.strip()[:200]}"
    )
    tags = res.stdout.split()
    signatures = [t for t in tags if t.startswith("sha256-")]
    assert signatures, (
        f"Le dépôt appli/web ne porte que {tags}. Aucune signature n'y a été "
        "poussée : cosign range la sienne dans le même dépôt que l'image, sous "
        "un tag dérivé de son digest, et c'est pour cela qu'un registre "
        "accessible en écriture est indispensable."
    )


# ----------------------------------------------------------------------
# 3. LE test : la même clé accepte l'une et refuse l'autre.
# ----------------------------------------------------------------------
def test_la_cle_accepte_l_image_signee_et_refuse_l_autre(host):
    """Les deux sens dans la même mesure, avec la clé publiée.

    Le registre porte exprès une seconde image que personne n'a signée. Sans
    elle, une vérification qui accepte tout passerait : un outil qui sort en
    erreur avant d'avoir regardé, une clé lue comme vide, une commande mal
    formée, tous ces cas se ressemblent vus du dehors.
    """
    assert _verifie(host, IMAGE_SIGNEE), (
        f"La clé publiée ne valide pas {IMAGE_SIGNEE}, que vous venez pourtant "
        "de signer. Vérifiez que la clé du ConfigMap est bien celle qui "
        "correspond à la clé privée employée pour signer : une paire régénérée "
        "après la signature ne validera jamais rien."
    )
    assert not _verifie(host, IMAGE_NUE), (
        f"La clé publiée valide aussi {IMAGE_NUE}, que personne n'a signée. "
        "La vérification ne mesure donc rien : c'est le cas le plus dangereux, "
        "parce qu'une chaîne qui accepte tout ressemble à une chaîne qui "
        "fonctionne."
    )
