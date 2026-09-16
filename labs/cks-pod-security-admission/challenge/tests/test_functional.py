"""test_functional.py : cks-pod-security-admission

Quatre affirmations qui lisent l'état du CLUSTER, jamais les commandes tapées.

La dernière est la seule qui prouve quelque chose. Lire les labels d'un
namespace montre qu'ils sont posés, pas que l'admission les applique : un
niveau mal orthographié, un mode oublié, une version épinglée sur un standard
qui n'existe pas, et les labels sont là sans que rien ne soit refusé. On
soumet donc de vrais objets à l'API server.

`--dry-run=server` est ce qui rend cette preuve possible sans salir le
cluster : l'objet traverse toute la chaîne d'admission, le verdict est réel, et
rien n'est écrit. Un `--dry-run=client` ne quitterait jamais la machine et ne
mesurerait rien du tout.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "secure-ns"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
PREFIXE = "pod-security.kubernetes.io"
MODES = ("enforce", "warn", "audit")
NIVEAU = "restricted"

#: Un Pod que le standard restricted doit refuser, et il le doit pour
#: plusieurs raisons à la fois : partage du namespace PID de l'hôte, exécution
#: en root, aucune capability retirée, aucun profil seccomp. Une seule aurait
#: suffi ; les cumuler rend le message de refus plus instructif.
POD_INTERDIT = """apiVersion: v1
kind: Pod
metadata:
  name: sonde-interdite
  namespace: secure-ns
spec:
  hostPID: true
  containers:
    - name: outil
      image: busybox:1.37
      securityContext:
        runAsUser: 0
"""

#: Le même Pod, rendu conforme. Il sert de contre-épreuve : sans lui, un
#: namespace qui refuserait TOUT passerait le test du refus.
POD_ACCEPTABLE = """apiVersion: v1
kind: Pod
metadata:
  name: sonde-conforme
  namespace: secure-ns
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: outil
      image: busybox:1.37
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
"""


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Joue une commande kubectl sur le control plane.

    Rend (code, sortie standard, diagnostic), et les trois restent SÉPARÉS :
    le client SSH écrit un avertissement sur stderr, et un test qui déciderait
    sur la concaténation des deux conclurait toujours la même chose.
    """
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _soumettre(host, manifeste: str) -> tuple[bool, str]:
    """Soumet un Pod à l'admission SANS rien créer.

    Rend (accepté, ce que l'API server a répondu). Le refus arrive sur stderr,
    et c'est là qu'il faut le lire : c'est un message d'erreur, pas une
    donnée. Le code de retour, lui, tranche.
    """
    # Le nom du fichier est tiré par `mktemp` plutôt qu'écrit en dur : deux
    # exécutions simultanées ne se marchent pas dessus, et rien ne peut
    # préparer le chemin à l'avance.
    cree = host.run("mktemp /tmp/dsoxlab-sonde-psa.XXXXXX.yaml")
    assert cree.rc == 0 and cree.stdout.strip(), "mktemp a échoué sur le nœud."
    chemin = cree.stdout.strip()
    depose = host.run(f"cat > {chemin} <<'MANIFESTE'\n{manifeste}MANIFESTE")
    assert depose.rc == 0, "Impossible de déposer le manifeste de sonde sur le nœud."
    rc, sortie, diagnostic = _kubectl(host, f"apply --dry-run=server -f {chemin}")
    host.run(f"rm -f {chemin}")
    return rc == 0, diagnostic or sortie


# ----------------------------------------------------------------------
# 1. Le standard est déclaré, dans les trois modes.
# ----------------------------------------------------------------------
def test_le_namespace_declare_le_standard_restricted(host):
    rc, sortie, diagnostic = _kubectl(host, f"get namespace {NAMESPACE} -o json")
    assert rc == 0 and sortie, (
        f"Le namespace {NAMESPACE} n'existe plus : le setup l'avait créé. {diagnostic}"
    )
    labels = (json.loads(sortie).get("metadata") or {}).get("labels") or {}
    manquants = [
        mode for mode in MODES if labels.get(f"{PREFIXE}/{mode}") != NIVEAU
    ]
    assert not manquants, (
        f"Mode(s) absent(s) ou au mauvais niveau : {', '.join(manquants)}. "
        f"Le standard s'active par des labels sur le namespace, un par mode : "
        f"{PREFIXE}/<mode>={NIVEAU}. Les trois sont indépendants, et n'en poser "
        "qu'un laisse les deux autres sans effet."
    )


# ----------------------------------------------------------------------
# 2. Le Pod conforme existe et tourne.
# ----------------------------------------------------------------------
def test_le_pod_conforme_tourne(host):
    """Un Pod déclaré conforme mais qui ne démarre pas ne prouve rien : c'est
    l'admission qui l'a laissé passer, encore faut-il qu'il vive."""
    rc, phase, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get pod conforme -o jsonpath='{{.status.phase}}'"
    )
    assert rc == 0 and phase, (
        "Aucun Pod « conforme » dans secure-ns. Il doit satisfaire le standard "
        f"restricted pour être admis. Sortie : {diagnostic}"
    )
    assert phase == "Running", (
        f"Le Pod conforme est en {phase}. Il a donc été admis, mais il ne tourne "
        "pas : regardez ses events et ses logs."
    )


def test_le_pod_conforme_satisfait_les_quatre_exigences(host):
    """Les quatre exigences du standard restricted, lues dans le Pod ADMIS.

    Elles se déclarent à deux niveaux, et c'est le piège : l'identité vaut au
    niveau du Pod comme du conteneur, tandis que l'escalade et les capabilities
    n'existent qu'au niveau du conteneur.
    """
    rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get pod conforme -o json")
    assert rc == 0 and sortie, "Le Pod conforme est introuvable."
    spec = json.loads(sortie)["spec"]
    pod_ctx = spec.get("securityContext") or {}
    conteneur = spec["containers"][0]
    ctn_ctx = conteneur.get("securityContext") or {}

    ecarts = []
    if not (pod_ctx.get("runAsNonRoot") or ctn_ctx.get("runAsNonRoot")):
        ecarts.append("runAsNonRoot n'est déclaré ni au niveau du Pod ni du conteneur")
    if ctn_ctx.get("allowPrivilegeEscalation") is not False:
        ecarts.append("allowPrivilegeEscalation n'est pas à false sur le conteneur")
    if "ALL" not in ((ctn_ctx.get("capabilities") or {}).get("drop") or []):
        ecarts.append("les capabilities ne sont pas toutes retirées (drop: ALL)")
    seccomp = (pod_ctx.get("seccompProfile") or {}).get("type") or (
        ctn_ctx.get("seccompProfile") or {}
    ).get("type")
    if seccomp not in ("RuntimeDefault", "Localhost"):
        ecarts.append("aucun profil seccomp n'est déclaré")

    assert not ecarts, (
        "Le Pod conforme a été admis, mais il ne satisfait pas ce que le "
        "standard exige :\n  " + "\n  ".join(ecarts) + "\n\nSi l'admission l'a "
        "laissé passer malgré cela, c'est que le mode enforce ne vise pas "
        "restricted."
    )


# ----------------------------------------------------------------------
# 3. La preuve : l'admission refuse, et n'est pas simplement fermée.
# ----------------------------------------------------------------------
def test_l_admission_refuse_l_interdit_et_accepte_le_conforme(host):
    """Les deux sens, dans le même test, et c'est délibéré.

    Sans standard, tout passe : la seconde moitié seule passerait AVANT le
    travail. Avec un standard mal réglé qui refuse tout, la première moitié
    seule passerait aussi. Seule la paire dit que l'admission trie.

    Rien n'est créé : les deux Pods sont soumis en dry-run côté serveur, donc
    le cluster ressort de ce test exactement comme il y est entré.
    """
    accepte_interdit, reponse_interdit = _soumettre(host, POD_INTERDIT)
    assert not accepte_interdit, (
        "L'API server a ACCEPTÉ un Pod qui partage le namespace PID de l'hôte "
        "et tourne en root. Le standard n'est donc pas appliqué : vérifiez que "
        f"le mode enforce du namespace {NAMESPACE} vise bien restricted, et non "
        "seulement les modes warn et audit, qui n'ont jamais bloqué personne."
    )
    assert "PodSecurity" in reponse_interdit or "violate" in reponse_interdit, (
        "Le Pod a bien été refusé, mais pas par Pod Security Admission : le "
        f"refus dit « {reponse_interdit} ». Autre chose bloque, et l'exigence "
        "n'est pas satisfaite pour autant."
    )

    accepte_conforme, reponse_conforme = _soumettre(host, POD_ACCEPTABLE)
    assert accepte_conforme, (
        "Un Pod qui satisfait le standard restricted est refusé lui aussi : "
        f"« {reponse_conforme} ». Une admission qui refuse tout n'est pas une "
        "politique de sécurité, c'est une panne. Vérifiez le niveau demandé, "
        "et qu'aucune version épinglée ne pointe un standard inexistant."
    )
