"""test_functional.py : k8s-installer-kubectl

Ces tests lisent l'état du nœud k8s-kind.lab, en tant qu'utilisateur du lab :
le binaire installé, sa version, son empreinte comparée à celle que publie
dl.k8s.io pour CETTE version, la complétion et l'alias tels qu'un nouveau shell
interactif les voit, puis la réponse du serveur du cluster. Un test vérifie un
seul état demandé par l'énoncé.

Tous échouent avant le travail : le setup retire kubectl, sa complétion et
l'alias k. Un faux binaire qui affiche une version passe le test de version,
jamais celui de l'empreinte.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import shlex

import pytest

from conftest import lab_host, lab_target_host, message

BINAIRE = "/usr/local/bin/kubectl"
VERSION_ATTENDUE = re.compile(r"^v1\.37\.\d+$")
EMPREINTE = re.compile(r"^[0-9a-f]{64}$")
OFFICIEL = "https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl.sha256"

#: Joue une VRAIE complétion dans un nouveau shell interactif (~/.bashrc lu) :
#: la fonction enregistrée pour `mot` est appelée comme bash l'appelle sur une
#: tabulation après « mot ver », et doit proposer `version`. Vérifier seulement
#: `complete -p` ne suffit pas : mesuré le 2026-11-11 sur Debian 13 sans le
#: paquet bash-completion, `complete -p kubectl` répond, mais __start_kubectl
#: meurt sur `_get_comp_words_by_ref: command not found` et la tabulation ne
#: complète que des noms de fichiers.
#:
#: Le chargement paresseux de bash-completion est d'abord déclenché : une
#: complétion posée dans un fichier de complétion plutôt que dans ~/.bashrc
#: n'est chargée qu'à la première tabulation d'un shell réel. Le chargeur
#: n'est appelé que si rien n'est déclaré : mesuré le 2026-11-11, sur un mot
#: sans fichier de complétion (l'alias k), le chargeur de repli de
#: bash-completion 2.16 REMPLACE `-F __start_kubectl` par
#: `_comp_complete_minimal`, et la solution juste tombait.
COMPLETER = r"""
complete -p {mot} >/dev/null 2>&1 || _comp_load {mot} >/dev/null 2>&1 || _completion_loader {mot} >/dev/null 2>&1
spec="$(complete -p {mot} 2>/dev/null)" || {{ echo SANS-COMPLETION; exit 0; }}
fn="$(sed -n 's/.*-F \([^ ]*\).*/\1/p' <<< "$spec")"
[ -n "$fn" ] || {{ echo SANS-FONCTION; exit 0; }}
COMP_WORDS=({mot} ver); COMP_CWORD=1; COMP_LINE="{mot} ver"; COMP_POINT=${{#COMP_LINE}}
COMP_TYPE=9; COMP_KEY=9; COMPREPLY=()
"$fn" {mot} ver {mot} >/dev/null 2>&1
printf 'PROPOSE:%s\n' "${{COMPREPLY[@]}}"
"""


def _propositions(host, mot: str) -> list[str]:
    """Ce que la tabulation propose après « mot ver » dans un nouveau shell."""
    res = _shell_interactif(host, COMPLETER.format(mot=mot))
    return [ligne[len("PROPOSE:"):].strip() for ligne in res.stdout.splitlines()
            if ligne.startswith("PROPOSE:")]


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


#: testinfra se connecte avec `sudo=true` : ses commandes tournent en ROOT, et
#: un `bash -ic` y lirait /root/.bashrc. Tout ce que l'apprenant voit (son
#: PATH, son ~/.bashrc, son kubeconfig) se lit donc sous son compte, celui qui
#: a ouvert la session SSH. Mesuré le 2026-11-11 : sans cela, la solution du
#: formateur rendait 4/6, alias et complétion introuvables.
APPRENANT = 'sudo -u "${SUDO_USER:-ansible}" -H'


def _en_apprenant(host, commande: str):
    """Joue `commande` sous le compte de l'apprenant, stdin fermé."""
    return host.run(f"{APPRENANT} {commande} < /dev/null")


def _shell_interactif(host, script: str):
    """Joue `script` dans un nouveau bash interactif de l'apprenant."""
    return _en_apprenant(host, f"bash -ic {shlex.quote(script)}")


def _version_client(host) -> str | None:
    res = host.run(f"{BINAIRE} version --client -o json")
    if res.rc != 0:
        return None
    try:
        return json.loads(res.stdout)["clientVersion"]["gitVersion"]
    except (ValueError, KeyError, TypeError):
        return None


# ----------------------------------------------------------------------
# 1. Installé pour tout le système, et trouvé en premier.
# ----------------------------------------------------------------------
def test_kubectl_est_installe_dans_usr_local_bin_et_appartient_a_root(host):
    fichier = host.file(BINAIRE)
    assert fichier.exists and fichier.is_file, message(
        en=f"No kubectl in {BINAIRE}. The requirements ask for a binary installed for the "
        "whole system, at the place reserved for software installed by hand.",
        fr=f"Aucun kubectl dans {BINAIRE}. Le cahier des charges demande un binaire installé "
        "pour tout le système, à l'emplacement réservé aux logiciels installés à la main.",
    )
    mode = fichier.mode
    assert fichier.user == "root" and fichier.group == "root", message(
        en=f"{BINAIRE} belongs to {fichier.user}:{fichier.group}. A binary shared by the whole "
        "system belongs to root, so that no ordinary account can replace it.",
        fr=f"{BINAIRE} appartient à {fichier.user}:{fichier.group}. Un binaire partagé par tout "
        "le système appartient à root, pour qu'aucun compte ordinaire ne puisse le remplacer.",
    )
    assert mode & 0o111 == 0o111 and mode & 0o022 == 0, message(
        en=f"{BINAIRE} has mode {mode:04o}. It must be executable by everyone and writable "
        "by its owner only.",
        fr=f"{BINAIRE} a le mode {mode:04o}. Il doit être exécutable par tous et modifiable "
        "par son seul propriétaire.",
    )
    res = _shell_interactif(host, "command -v kubectl")
    trouve = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
    assert trouve == BINAIRE, message(
        en=f"In a new shell, the command kubectl resolves to {trouve or 'nothing'}, not to "
        f"{BINAIRE}. Another copy comes first in the PATH.",
        fr=f"Dans un nouveau shell, la commande kubectl désigne {trouve or 'rien'}, et non "
        f"{BINAIRE}. Une autre copie passe avant elle dans le PATH.",
    )


# ----------------------------------------------------------------------
# 2. La version du client.
# ----------------------------------------------------------------------
def test_le_client_est_en_version_1_37(host):
    version = _version_client(host)
    assert version is not None, message(
        en=f"{BINAIRE} does not answer kubectl version --client: it is missing or it is not "
        "a working kubectl for this machine.",
        fr=f"{BINAIRE} ne répond pas à kubectl version --client : il est absent, ou ce n'est "
        "pas un kubectl qui fonctionne sur cette machine.",
    )
    assert VERSION_ATTENDUE.match(version), message(
        en=f"The client is in {version}. The cluster runs Kubernetes v1.37.0, and the "
        "requirements ask for a 1.37 client, pinned.",
        fr=f"Le client est en {version}. Le cluster tourne en Kubernetes v1.37.0, et le cahier "
        "des charges demande un client 1.37, épinglé.",
    )


# ----------------------------------------------------------------------
# 3. L'empreinte officielle de cette version.
# ----------------------------------------------------------------------
def test_le_binaire_a_l_empreinte_officielle_de_sa_version(host):
    version = _version_client(host)
    assert version is not None and VERSION_ATTENDUE.match(version), message(
        en="No working 1.37 kubectl to compare with its official fingerprint.",
        fr="Aucun kubectl 1.37 qui fonctionne, dont comparer l'empreinte à l'officielle.",
    )
    url = OFFICIEL.format(version=version)
    res = host.run(f"curl -fsSL --max-time 30 {shlex.quote(url)}")
    officielle = res.stdout.strip().split()[0] if res.rc == 0 and res.stdout.strip() else ""
    if not EMPREINTE.match(officielle):
        pytest.fail(message(
            en=f"The test could not read the official fingerprint at {url} (curl rc={res.rc}). "
            "The node must reach dl.k8s.io: rerun the check.",
            fr=f"Le test n'a pas pu lire l'empreinte officielle sur {url} (curl rc={res.rc}). "
            "Le nœud doit joindre dl.k8s.io : relancez la vérification.",
        ))
    locale = host.check_output(f"sha256sum {BINAIRE}").split()[0]
    assert locale == officielle, message(
        en=f"{BINAIRE} announces {version}, but its fingerprint is not the one published "
        f"for that version. This is not the official binary: it was altered, or it comes "
        "from somewhere else.",
        fr=f"{BINAIRE} annonce {version}, mais son empreinte n'est pas celle publiée pour "
        "cette version. Ce n'est pas le binaire officiel : il a été modifié, ou il vient "
        "d'ailleurs.",
    )


# ----------------------------------------------------------------------
# 4. La complétion bash de kubectl.
# ----------------------------------------------------------------------
def test_la_completion_bash_de_kubectl_est_active(host):
    propositions = _propositions(host, "kubectl")
    assert "version" in propositions, message(
        en="In a new interactive shell, Tab does not complete kubectl ver into kubectl version. "
        "The completion must work, not only be declared, and be active in every new session, "
        "not only in the current one.",
        fr="Dans un nouveau shell interactif, la tabulation ne complète pas kubectl ver en "
        "kubectl version. La complétion doit fonctionner, pas seulement être déclarée, et être "
        "active dans chaque nouvelle session, pas seulement dans la session en cours.",
    )


# ----------------------------------------------------------------------
# 5. L'alias k.
# ----------------------------------------------------------------------
def test_l_alias_k_lance_kubectl_et_se_complete(host):
    res = _shell_interactif(host, "alias k")
    alias = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
    assert re.fullmatch(r"alias k='(/usr/local/bin/)?kubectl'", alias), message(
        en=f"In a new interactive shell, k is not an alias of kubectl ({alias or 'no alias k'}).",
        fr=f"Dans un nouveau shell interactif, k n'est pas un alias de kubectl "
        f"({alias or 'aucun alias k'}).",
    )
    propositions = _propositions(host, "k")
    assert "version" in propositions, message(
        en="The alias k exists, but Tab does not complete k ver into k version: an alias does "
        "not inherit the completion of the command it stands for.",
        fr="L'alias k existe, mais la tabulation ne complète pas k ver en k version : un alias "
        "n'hérite pas de la complétion de la commande qu'il remplace.",
    )


# ----------------------------------------------------------------------
# 6. La connexion au serveur.
# ----------------------------------------------------------------------
def test_kubectl_atteint_le_serveur_du_cluster(host):
    res = _en_apprenant(host, f"{BINAIRE} version -o json --request-timeout=15s")
    try:
        serveur = json.loads(res.stdout).get("serverVersion", {}).get("gitVersion")
    except ValueError:
        serveur = None
    assert serveur, message(
        en="kubectl version does not show the version of the server: your kubectl does not "
        "reach the cluster prepared for you. Your kubeconfig is already in place.",
        fr="kubectl version n'affiche pas la version du serveur : votre kubectl n'atteint pas "
        "le cluster préparé pour vous. Votre kubeconfig est déjà en place.",
    )
