"""test_functional.py : cks-seccomp-profile

Trois affirmations qui lisent l'état du NŒUD et du conteneur, jamais les
commandes tapées.

Les deux premières ne prouvent rien à elles seules, et le CLAUDE.md du dépôt le
dit pour le lab AppArmor jumeau : « vérifier qu'un profil est chargé et qu'un
Pod le déclare ne prouve PAS que le confinement agit, un profil vide
passerait ». Elles sont là pour que l'échec soit diagnosticable, pas pour
constituer la preuve.

La preuve est le dernier test, et il exerce les deux côtés : ce qui est
interdit doit échouer DANS le conteneur, et ce qui reste permis doit continuer
d'y fonctionner. Un profil qui refuserait tout casserait le conteneur, et
c'est aussi faux qu'un profil qui ne refuse rien.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "confinement"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
POD = "seccomp-pod"
TEMOIN = "temoin"
RACINE_SECCOMP = "/var/lib/kubelet/seccomp"
PROFIL = f"{RACINE_SECCOMP}/profiles/restrict-chmod.json"
#: Les trois appels de la famille chmod. `chmod` seul ne suffit pas : une libc
#: moderne passe par fchmodat, et un profil qui ne filtre que le premier
#: laisse le conteneur changer les permissions sans être inquiété.
FAMILLE_CHMOD = {"chmod", "fchmod", "fchmodat"}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _dans(host, pod: str, commande: str):
    return _kubectl(host, f"-n {NAMESPACE} exec {pod} --request-timeout=30s -- sh -c '{commande}'")


# ----------------------------------------------------------------------
# 1. Le profil existe sur le nœud, et il refuse la bonne famille d'appels.
# ----------------------------------------------------------------------
def test_le_profil_refuse_la_famille_chmod(host):
    """Un profil seccomp n'est pas un objet Kubernetes : c'est un fichier du
    nœud, que le kubelet lit dans un répertoire qu'il est seul à connaître."""
    res = host.run(f"sudo cat {PROFIL}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No readable profile at {PROFIL}. The kubelet looks for local "
        f"profiles under {RACINE_SECCOMP}, and does not create that directory itself.",
        fr=f"Aucun profil lisible en {PROFIL}. Le kubelet cherche les profils "
        f"locaux sous {RACINE_SECCOMP}, et ne crée pas ce répertoire lui-même.",
    )
    try:
        profil = json.loads(res.stdout)
    except json.JSONDecodeError as erreur:
        pytest.fail(
            message(
            en=f"The profile is not valid JSON: {erreur}. The kubelet will refuse "
            "to start the Pod with an unhelpful mount error.",
            fr=f"Le profil n'est pas un JSON valide : {erreur}. Le kubelet refusera "
            "de démarrer le Pod avec une erreur de montage peu parlante.",
        )
        )

    assert profil.get("defaultAction") == "SCMP_ACT_ALLOW", message(
        en=f"defaultAction is {profil.get('defaultAction')}. The specification "
        "asks to allow by default and to refuse a single "
        "family: refusing by default would mean enumerating the hundreds "
        "of calls a container needs just to start.",
        fr=f"defaultAction vaut {profil.get('defaultAction')}. Le cahier des "
        "charges demande d'autoriser par défaut et de refuser une seule "
        "famille : refuser par défaut demanderait d'énumérer les centaines "
        "d'appels dont un conteneur a besoin pour seulement démarrer.",
    )
    refuses = {
        nom
        for regle in profil.get("syscalls") or []
        if regle.get("action") in ("SCMP_ACT_ERRNO", "SCMP_ACT_KILL")
        for nom in regle.get("names") or []
    }
    manquants = FAMILLE_CHMOD - refuses
    assert not manquants, message(
        en=f"The profile does not refuse: {', '.join(sorted(manquants))}. The family "
        "has three calls, and filtering only one lets the container change "
        "permissions: `chmod` goes through fchmodat on a modern libc.",
        fr=f"Le profil ne refuse pas : {', '.join(sorted(manquants))}. La famille "
        "compte trois appels, et n'en filtrer qu'un laisse le conteneur changer "
        "les permissions : `chmod` passe par fchmodat sur une libc moderne.",
    )


# ----------------------------------------------------------------------
# 2. Le Pod tourne et déclare ce profil.
# ----------------------------------------------------------------------
def test_le_pod_tourne_et_declare_le_profil_local(host):
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert rc == 0 and sortie, message(
        en=f"No Pod {POD} in {NAMESPACE}. {diagnostic}",
        fr=f"Aucun Pod {POD} dans {NAMESPACE}. {diagnostic}",
    )
    pod = json.loads(sortie)
    assert pod["status"]["phase"] == "Running", message(
        en=f"Pod {POD} is {pod['status']['phase']}. A profile path matching "
        "no file on the node gives a mount failure: the "
        "declared path is RELATIVE to /var/lib/kubelet/seccomp.",
        fr=f"Le Pod {POD} est en {pod['status']['phase']}. Un chemin de profil qui "
        "ne correspond à aucun fichier du nœud donne un échec de montage : le "
        "chemin déclaré est RELATIF à /var/lib/kubelet/seccomp.",
    )

    contextes = [pod["spec"].get("securityContext") or {}] + [
        c.get("securityContext") or {} for c in pod["spec"]["containers"]
    ]
    profils = [ctx.get("seccompProfile") or {} for ctx in contextes]
    localhost = [p for p in profils if p.get("type") == "Localhost"]
    assert localhost, message(
        en="The Pod declares no seccompProfile of type Localhost. The "
        "RuntimeDefault type would use the runtime's profile, which is not the one "
        "you are asked to write.",
        fr="Le Pod ne déclare aucun seccompProfile de type Localhost. Le type "
        "RuntimeDefault emploierait le profil du runtime, qui n'est pas celui "
        "qu'on vous demande d'écrire.",
    )
    chemins = {p.get("localhostProfile") for p in localhost}
    assert "profiles/restrict-chmod.json" in chemins, message(
        en=f"The Pod declares {chemins}. The expected path is relative to "
        f"{RACINE_SECCOMP}, so \"profiles/restrict-chmod.json\", with no leading "
        "slash.",
        fr=f"Le Pod déclare {chemins}. Le chemin attendu est relatif à "
        f"{RACINE_SECCOMP}, donc « profiles/restrict-chmod.json », sans barre "
        "oblique initiale.",
    )


# ----------------------------------------------------------------------
# 3. LE test : le confinement agit, et n'agit pas trop.
# ----------------------------------------------------------------------
def test_le_confinement_refuse_chmod_et_laisse_le_reste(host):
    """Les deux côtés dans la même mesure.

    Un profil vide passerait les deux tests précédents. Un profil qui refuse
    tout casserait le conteneur, ce qui n'est pas non plus ce qu'on demande.
    On exerce donc ce qui est interdit ET ce qui reste permis.
    """
    rc, sortie, diagnostic = _dans(host, POD, "touch /tmp/preuve && echo ok")
    assert rc == 0 and sortie == "ok", message(
        en="The confined container can no longer even create a file. The profile "
        "refuses more than the chmod family: check that defaultAction is "
        f"SCMP_ACT_ALLOW. Output: {diagnostic}",
        fr="Le conteneur confiné ne peut même plus créer un fichier. Le profil "
        "refuse plus que la famille chmod : vérifiez que defaultAction vaut "
        f"SCMP_ACT_ALLOW. Sortie : {diagnostic}",
    )

    rc, _, diagnostic = _dans(host, POD, "chmod 700 /tmp/preuve")
    assert rc != 0, message(
        en="The confined container changed a file's permissions: the filter "
        "does not apply. A profile can be loaded, declared and without effect, "
        "and that is exactly what this test exists to catch.",
        fr="Le conteneur confiné a changé les permissions d'un fichier : le filtre "
        "ne s'applique pas. Un profil peut être chargé, déclaré et sans effet, "
        "c'est exactement ce que ce test existe pour attraper.",
    )
    assert "not permitted" in diagnostic.lower(), message(
        en=f"chmod failed, but not for the expected reason: \"{diagnostic}\". "
        "A call refused by seccomp returns EPERM, \"Operation not permitted\"; "
        "another message signals another cause, and the filter is then not "
        "proven.",
        fr=f"chmod a échoué, mais pas pour la raison attendue : « {diagnostic} ». "
        "Un appel refusé par seccomp rend EPERM, « Operation not permitted » ; "
        "un autre message signale une autre cause, et le filtre n'est alors pas "
        "prouvé.",
    )

    # Et le filtre ne vise QUE ce Pod. Cette mesure n'a pas de test à elle :
    # le témoin est créé non confiné par le setup, donc « le témoin peut
    # appeler chmod » est vrai AVANT tout travail, et un test toujours vrai ne
    # mesure rien. La validation l'a rendu ROUGE pour cette raison. Ici la même
    # assertion a du sens, parce qu'elle n'est atteinte qu'après avoir prouvé
    # que le Pod confiné, lui, est bien filtré : les deux ensemble distinguent
    # un filtre posé sur le bon Pod d'un durcissement global du nœud, qui
    # casserait tout ce qui tourne dessus.
    rc, sortie, diagnostic = _dans(host, TEMOIN, "touch /tmp/t && chmod 700 /tmp/t && echo ok")
    assert rc == 0 and sortie == "ok", message(
        en="The witness Pod, which declares no profile, can no longer call "
        "chmod. The filter was placed too broadly, on the runtime or on the whole "
        f"node, instead of the one Pod targeted. Output: {diagnostic}",
        fr="Le Pod témoin, qui ne déclare aucun profil, ne peut plus appeler "
        "chmod. Le filtre a été posé trop large, sur le runtime ou sur le nœud "
        f"entier, au lieu du seul Pod visé. Sortie : {diagnostic}",
    )
