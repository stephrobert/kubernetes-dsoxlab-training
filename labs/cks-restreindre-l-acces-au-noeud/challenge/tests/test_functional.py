"""test_functional.py : cks-restreindre-l-acces-au-noeud

Ces tests lisent l'état de k8s-w2.lab, jamais les commandes tapées. Ils
ouvrent de VRAIES sessions SSH sur 127.0.0.1 avec une clé d'essai que le setup
a posée chez stagiaire, student et ansible : c'est la décision de sshd qui est
lue, pas seulement sa configuration. Un fichier écrit mais jamais rechargé ne
passe donc pas.

Aucun test n'est vrai avant le travail : le setup ne crée pas le groupe
k8s-admins, ouvre le mot de passe et root par 05-heritage.conf, et donne à
stagiaire tous les droits sudo, par le groupe sudo et par sudoers.d.

Deux triches sont refusées par construction : fermer SSH à tout le monde
(student et ansible doivent encore entrer, et les tests eux-mêmes se
connectent par ansible), et supprimer le compte stagiaire ou tous ses droits
(il doit exister et pouvoir lire l'état du kubelet).
"""

from __future__ import annotations

import pytest

from conftest import lab_host, message

NOEUD = "k8s-w2.lab"
GROUPE = "k8s-admins"
CLE_ESSAI = "/root/.lab-acces/essai_ed25519"
OPTIONS_SSH = (
    "-o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
    "-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
)
DROIT_GARDE = "/usr/bin/systemctl status kubelet"


@pytest.fixture(scope="module")
def host():
    return lab_host(NOEUD)


def _session(host, compte: str):
    """Ouvre une session SSH par la clé d'essai : rend (code, diagnostic)."""
    # testinfra lève une exception sur le code 255, celui d'un ssh refusé : la
    # commande sort donc toujours en 0, et le code se lit dans sa sortie.
    res = host.run(
        f"sudo ssh {OPTIONS_SSH} -i {CLE_ESSAI} {compte}@127.0.0.1 true 2>&1; echo \"code=$?\""
    )
    lignes = res.stdout.strip().splitlines()
    code = int(lignes[-1].removeprefix("code=")) if lignes and lignes[-1].startswith("code=") else -1
    return code, " ".join(lignes[:-1]).strip()


def _sshd_t(host) -> dict[str, str]:
    res = host.run("sudo sshd -T")
    assert res.rc == 0, message(
        en=f"sudo sshd -T fails on {NOEUD}: the SSH configuration does not parse. Output: {res.stderr.strip()}",
        fr=f"sudo sshd -T échoue sur {NOEUD} : la configuration SSH ne se lit pas. Sortie : {res.stderr.strip()}",
    )
    valeurs: dict[str, str] = {}
    for ligne in res.stdout.splitlines():
        cle, _, valeur = ligne.partition(" ")
        valeurs.setdefault(cle.lower(), valeur.strip())
    return valeurs


def _membres(host) -> set[str]:
    res = host.run(f"getent group {GROUPE}")
    if res.rc != 0:
        return set()
    return {m for m in res.stdout.strip().split(":")[-1].split(",") if m}


def test_ssh_est_reserve_au_groupe_k8s_admins(host):
    membres = _membres(host)
    assert membres, message(
        en=f"No group {GROUPE} on {NOEUD}: create it, and put your accounts in it BEFORE restricting SSH.",
        fr=f"Aucun groupe {GROUPE} sur {NOEUD} : créez-le, et mettez-y vos comptes AVANT de restreindre SSH.",
    )
    manquants = sorted({"ansible", "student"} - membres)
    assert not manquants, message(
        en=f"{', '.join(manquants)} not in {GROUPE}: the two administration accounts must stay allowed.",
        fr=f"{', '.join(manquants)} absent(s) de {GROUPE} : les deux comptes d'administration doivent rester autorisés.",
    )
    assert "stagiaire" not in membres, message(
        en=f"stagiaire is in {GROUPE}: the on-call account must not open SSH sessions on the node.",
        fr=f"stagiaire est dans {GROUPE} : le compte d'astreinte ne doit pas ouvrir de session SSH sur le nœud.",
    )
    groupes = _sshd_t(host).get("allowgroups", "")
    assert groupes.split() == [GROUPE], message(
        en=f"sshd -T shows allowgroups « {groupes or 'none'} », expected exactly « {GROUPE} ».",
        fr=f"sshd -T affiche allowgroups « {groupes or 'aucun'} », attendu exactement « {GROUPE} ».",
    )
    for compte in ("ansible", "student"):
        rc, diag = _session(host, compte)
        assert rc == 0, message(
            en=f"An SSH session as {compte} is refused ({diag}): you would lock the administrators out.",
            fr=f"Une session SSH en {compte} est refusée ({diag}) : les administrateurs seraient enfermés dehors.",
        )
    # Cinq essais, pas un : un ancien « sshd -D [listener] » resté d'un
    # redémarrage garde l'ancienne configuration, et ne sert qu'une partie des
    # connexions (12 sur 20 mesurées le 2026-11-17).
    ouvertes = sum(1 for _ in range(5) if _session(host, "stagiaire")[0] == 0)
    assert ouvertes == 0, message(
        en=f"{ouvertes} SSH sessions out of 5 as stagiaire still open. Is sshd reloaded? Does pgrep -a sshd "
        "show a single « sshd -D [listener] »? An old one keeps the old configuration.",
        fr=f"{ouvertes} sessions SSH sur 5 s'ouvrent encore en stagiaire. sshd est-il rechargé ? pgrep -a sshd "
        "montre-t-il un seul « sshd -D [listener] » ? Un ancien garde l'ancienne configuration.",
    )


def test_ssh_accepte_la_cle_seulement(host):
    valeurs = _sshd_t(host)
    assert valeurs.get("passwordauthentication") == "no", message(
        en="sshd -T shows passwordauthentication yes: sshd keeps the FIRST value it reads, "
        "and 05-heritage.conf is read early.",
        fr="sshd -T affiche passwordauthentication yes : sshd garde la PREMIÈRE valeur lue, "
        "et 05-heritage.conf est lu tôt.",
    )
    assert valeurs.get("permitrootlogin") == "no", message(
        en=f"sshd -T shows permitrootlogin {valeurs.get('permitrootlogin')}, expected no.",
        fr=f"sshd -T affiche permitrootlogin {valeurs.get('permitrootlogin')}, attendu no.",
    )
    res = host.run(
        f"ssh {OPTIONS_SSH} -o PubkeyAuthentication=no "
        "-o PreferredAuthentications=password,keyboard-interactive student@127.0.0.1 true 2>&1; true"
    )
    methodes = res.stdout.strip()
    assert "password" not in methodes and "keyboard-interactive" not in methodes, message(
        en=f"The running sshd still offers a password ({methodes}): reload it after editing.",
        fr=f"Le sshd en marche propose encore un mot de passe ({methodes}) : rechargez-le après la modification.",
    )


def _droits(host) -> str:
    res = host.run("sudo sudo -l -U stagiaire")
    return res.stdout


def test_stagiaire_n_a_plus_les_pleins_droits(host):
    assert host.user("stagiaire").exists, message(
        en="The account stagiaire is gone: it serves the on-call duty, cut its rights instead of deleting it.",
        fr="Le compte stagiaire a disparu : il sert à l'astreinte, réduisez ses droits au lieu de le supprimer.",
    )
    groupes = host.user("stagiaire").groups
    assert not {"sudo", "admin", "wheel"} & set(groupes), message(
        en=f"stagiaire is still in {sorted({'sudo', 'admin', 'wheel'} & set(groupes))}: "
        "that group alone grants every command.",
        fr=f"stagiaire est encore dans {sorted({'sudo', 'admin', 'wheel'} & set(groupes))} : "
        "ce groupe à lui seul accorde toutes les commandes.",
    )
    droits = _droits(host)
    larges = [ligne.strip() for ligne in droits.splitlines() if ligne.strip().endswith(" ALL")]
    assert not larges, message(
        en=f"sudo -l -U stagiaire still grants every command: {larges}. Look in /etc/sudoers.d/ too.",
        fr=f"sudo -l -U stagiaire accorde encore toutes les commandes : {larges}. Regardez aussi /etc/sudoers.d/.",
    )
    res = host.run("sudo -u stagiaire sudo -n /usr/bin/cat /etc/shadow")
    assert res.rc != 0, message(
        en="stagiaire can still read /etc/shadow through sudo.",
        fr="stagiaire peut encore lire /etc/shadow par sudo.",
    )
    assert host.run("sudo visudo -c").rc == 0, message(
        en="sudo visudo -c reports an error: a broken sudoers file can lock every sudo user out.",
        fr="sudo visudo -c signale une erreur : un fichier sudoers cassé peut priver tous les comptes de sudo.",
    )


def test_stagiaire_garde_l_etat_du_kubelet(host):
    droits = _droits(host)
    assert DROIT_GARDE in droits, message(
        en=f"sudo -l -U stagiaire does not list « {DROIT_GARDE} »: the on-call duty needs exactly that command.",
        fr=f"sudo -l -U stagiaire ne liste pas « {DROIT_GARDE} » : l'astreinte a besoin de cette commande exacte.",
    )
    res = host.run(f"sudo -u stagiaire sudo -n {DROIT_GARDE}")
    assert res.rc == 0, message(
        en=f"stagiaire cannot run « sudo {DROIT_GARDE} » without a password: {res.stderr.strip()}",
        fr=f"stagiaire ne peut pas lancer « sudo {DROIT_GARDE} » sans mot de passe : {res.stderr.strip()}",
    )
