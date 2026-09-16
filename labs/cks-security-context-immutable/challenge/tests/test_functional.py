"""test_functional.py : cks-security-context-immutable

Deux affirmations qui lisent l'état réel des conteneurs, jamais les commandes
tapées.

Le choix du chemin de preuve est le point délicat de ce lab, et il a été
mesuré plutôt que supposé. L'image tourne sous l'UID 101 : la racine lui est
déjà refusée par les DROITS POSIX, avant tout durcissement. Un test qui ferait
`touch /preuve` serait donc vert AVANT le travail, et ne mesurerait rien.

Mesuré le 2026-09-16, sur un Pod nu puis sur un Pod durci :

| chemin | Pod nu | Pod durci |
|---|---|---|
| `/preuve` | Permission denied | Read-only file system |
| `/usr/share/nginx/html` | Permission denied | Read-only file system |
| `/var/log/nginx` | Permission denied | Read-only file system |
| `/etc/nginx/conf.d` | INSCRIPTIBLE | Read-only file system |

Seul le dernier distingue les deux états : l'image le rend inscriptible à son
propre UID pour que ses scripts d'entrée y écrivent, et seul
`readOnlyRootFilesystem` le ferme.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "catalogue"
DEPLOYMENT = "vitrine"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CIBLE = "http://vitrine.catalogue.svc.cluster.local/"

# Inscriptible par l'UID de l'image tant que la racine n'est pas fermée.
CHEMIN_PREUVE = "/etc/nginx/conf.d"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _un_pod_du_deployment(host) -> str:
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} get pod -l app={DEPLOYMENT} "
        "--field-selector=status.phase=Running "
        "-o jsonpath='{.items[0].metadata.name}'",
    )
    assert rc == 0 and sortie, (
        f"Aucun Pod du Deployment {DEPLOYMENT} ne tourne dans {NAMESPACE}. "
        "Un durcissement qui empêche l'application de démarrer n'est pas un "
        "durcissement : `kubectl -n catalogue get pods` et `kubectl -n "
        "catalogue logs <pod>` diront sur quoi nginx s'est arrêté. "
        f"{diagnostic}"
    )
    return sortie


# ----------------------------------------------------------------------
# 1. Les quatre exigences sont déclarées.
# ----------------------------------------------------------------------
def test_les_quatre_exigences_sont_declarees(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable, et pour nommer celle des
    quatre exigences qui manque."""
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json"
    )
    assert rc == 0 and sortie, (
        f"Le Deployment {DEPLOYMENT} est introuvable dans {NAMESPACE}. "
        "Le setup l'avait posé : il doit être MODIFIÉ, pas remplacé par un "
        f"objet d'un autre nom. {diagnostic}"
    )
    spec = json.loads(sortie)["spec"]["template"]["spec"]
    pod_sc = spec.get("securityContext", {})
    conteneurs = spec.get("containers", [])
    assert conteneurs, "Le Deployment ne déclare aucun conteneur."

    manques = []
    for c in conteneurs:
        sc = c.get("securityContext", {})
        if sc.get("readOnlyRootFilesystem") is not True:
            manques.append(f"{c['name']} : readOnlyRootFilesystem n'est pas true")
        if sc.get("allowPrivilegeEscalation") is not False:
            manques.append(f"{c['name']} : allowPrivilegeEscalation n'est pas false")
        drop = [d.upper() for d in sc.get("capabilities", {}).get("drop", [])]
        if "ALL" not in drop:
            manques.append(f"{c['name']} : les capacités ne sont pas toutes retirées")
    if pod_sc.get("runAsNonRoot") is not True and not all(
        c.get("securityContext", {}).get("runAsNonRoot") is True for c in conteneurs
    ):
        manques.append("runAsNonRoot n'est déclaré ni au niveau du Pod ni des conteneurs")

    assert not manques, (
        "Il manque des exigences dans le securityContext :\n  - "
        + "\n  - ".join(manques)
        + "\n\nAttention au NIVEAU : ce qui concerne l'identité du processus "
        "se déclare au niveau du Pod comme du conteneur, tandis que "
        "l'escalade, les capacités et le système de fichiers ne s'acceptent "
        "qu'au niveau du CONTENEUR."
    )


# ----------------------------------------------------------------------
# 2. LE test : l'écriture est refusée, et l'application sert encore.
# ----------------------------------------------------------------------
def test_l_interieur_ne_s_ecrit_plus_et_le_site_sert_toujours(host):
    """La preuve, exercée depuis l'intérieur du conteneur et depuis le réseau.

    Les deux mesures sont dans le MÊME test, délibérément. « Le site répond »
    est déjà vrai AVANT le travail : isolée, cette assertion ferait un test
    vert qui ne mesure rien. Accolée à l'autre, elle prend tout son sens :
    elle distingue un conteneur durci d'un conteneur en panne. Un nginx qui ne
    démarre plus n'écrit nulle part, lui non plus.

    Mesuré le 2026-09-16 : sans les volumes éphémères, nginx s'arrête sur
    « mkdir() "/tmp/proxy_temp" failed (30: Read-only file system) ».
    """
    pod = _un_pod_du_deployment(host)

    rc, _, _ = _kubectl(
        host,
        f"-n {NAMESPACE} exec {pod} --request-timeout=30s "
        f"-- sh -c 'touch {CHEMIN_PREUVE}/preuve'",
    )
    assert rc != 0, (
        f"Le conteneur accepte encore d'écrire dans {CHEMIN_PREUVE}. Ce chemin "
        "est inscriptible par l'UID de l'image tant que la racine n'est pas "
        "fermée : c'est justement pourquoi il sert de preuve ici, là où la "
        "racine elle-même était déjà refusée par les droits POSIX avant tout "
        "durcissement. Seul readOnlyRootFilesystem le ferme, et il ne "
        "s'applique qu'aux Pods RECRÉÉS depuis sa déclaration."
    )

    rc, _, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec client --request-timeout=30s "
        f"-- wget -qO- -T 5 {CIBLE}",
    )
    assert rc == 0, (
        f"Le site ne répond plus sur {CIBLE}. Fermer le système de fichiers "
        "casse nginx s'il ne retrouve pas les quelques chemins où il écrit "
        "pendant son démarrage : le journal du Pod nomme le premier qui "
        "manque, `kubectl -n catalogue logs <pod>`. Ces chemins se rouvrent un "
        "à un avec des volumes éphémères, dont le contenu est perdu au "
        f"redémarrage, ce qui convient au cache et au temporaire. {diagnostic}"
    )
