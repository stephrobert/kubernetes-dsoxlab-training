"""test_functional.py : cks-falco-detecter-un-shell

Ces tests lisent l'état du NŒUD et du cluster, jamais les commandes tapées.
Falco tourne sur k8s-cp.lab (paquet officiel, pilote modern_ebpf, posé par le
setup sans aucune règle personnalisée) et écrit ses alertes en JSON dans
/var/log/falco/events.json. Le correcteur ouvre un shell dans le Pod protégé,
puis dans un Pod d'un autre namespace, et lit ce que Falco a écrit.

Trois tests, repris de la fiche du lab (P01 à P03), et aucun n'est vrai avant
le travail : le setup ne pose aucune règle, donc aucun shell ne lève l'alerte
demandée. « Un shell ailleurs ne déclenche rien » et « les règles fournies sont
intactes » seraient vrais AVANT le travail : chacun exige donc aussi que la
règle alerte pour le namespace protégé. Mêmes mécanismes que le challenge
k8s-challenge-confiner-et-detecter, validé.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NOEUD = "k8s-cp.lab"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
FALCO_SERVICE = "falco-modern-bpf.service"
FALCO_JOURNAL = "/var/log/falco/events.json"
FALCO_REGLES = "/etc/falco/falco_rules.yaml"
REGLE = "Shell dans paiements"
PRIORITE = "critical"
PROTEGE, POD_PROTEGE = "paiements", "caisse"
AILLEURS, POD_AILLEURS = "accueil", "vitrine"

_MESURE: dict[str, list[dict]] = {}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"{KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _exiger_en_marche(host, ns: str, nom: str) -> None:
    rc, sortie, _ = _kubectl(host, f"-n {ns} get pod {nom} -o json")
    assert rc == 0 and sortie, message(
        en=f"No Pod {nom} in namespace {ns}: the setup placed it, it must stay.",
        fr=f"Aucun Pod {nom} dans le namespace {ns} : le setup l'a posé, il doit rester.",
    )
    phase = json.loads(sortie)["status"].get("phase")
    assert phase == "Running", message(
        en=f"Pod {nom} of {ns} is {phase}, not Running: kubectl -n {ns} describe pod {nom} says why.",
        fr=f"Le Pod {nom} de {ns} est en {phase}, et non Running : kubectl -n {ns} describe pod {nom} "
        "dit pourquoi.",
    )


def _falco_actif(host) -> None:
    res = host.run(f"systemctl is-active {FALCO_SERVICE}")
    assert res.stdout.strip() == "active", message(
        en=f"Falco is not running on {NOEUD} ({res.stdout.strip()}). A rule file Falco cannot load "
        f"stops the service: sudo journalctl -u {FALCO_SERVICE} names the faulty line.",
        fr=f"Falco ne tourne pas sur {NOEUD} ({res.stdout.strip()}). Un fichier de règles que Falco "
        f"ne sait pas charger arrête le service : sudo journalctl -u {FALCO_SERVICE} nomme la ligne "
        "fautive.",
    )


def _lignes_du_journal(host) -> int:
    res = host.run(f"sudo sh -c 'if [ -f {FALCO_JOURNAL} ]; then wc -l < {FALCO_JOURNAL}; else echo 0; fi'")
    try:
        return int(res.stdout.strip() or 0)
    except ValueError:
        return 0


def _alertes_depuis(host, depuis: int) -> list[dict]:
    res = host.run(f"sudo tail -n +{depuis + 1} {FALCO_JOURNAL}")
    alertes = []
    for brute in res.stdout.splitlines():
        ligne = brute.strip()
        if ligne.startswith("{"):
            try:
                alertes.append(json.loads(ligne))
            except json.JSONDecodeError:
                continue
    return alertes


def _alertes_apres_un_shell(host, ns: str, pod: str, essais: int) -> list[dict]:
    depuis = _lignes_du_journal(host)
    rc, _, diagnostic = _kubectl(host, f"-n {ns} exec {pod} --request-timeout=30s -- sh -c 'echo dsoxlab-correcteur'")
    assert rc == 0, message(
        en=f"The grader cannot open a shell in Pod {pod} of {ns}. {diagnostic}",
        fr=f"Le correcteur ne peut pas ouvrir de shell dans le Pod {pod} de {ns}. {diagnostic}",
    )
    trouvees: list[dict] = []
    for _ in range(essais):
        time.sleep(2)
        trouvees = [a for a in _alertes_depuis(host, depuis) if a.get("rule") == REGLE]
        if trouvees:
            break
    return trouvees


def _alertes_du_protege(host) -> list[dict]:
    """Un shell dans le Pod protégé, et les alertes de la règle qui ont suivi.
    Mesuré une fois par check : les trois tests s'appuient dessus."""
    if "protege" not in _MESURE:
        _falco_actif(host)
        _exiger_en_marche(host, PROTEGE, POD_PROTEGE)
        _MESURE["protege"] = _alertes_apres_un_shell(host, PROTEGE, POD_PROTEGE, essais=15)
    return _MESURE["protege"]


# ----------------------------------------------------------------------
# P01. Un shell dans le Pod protégé lève la règle, avec sa priorité.
# ----------------------------------------------------------------------
def test_un_shell_dans_paiements_leve_l_alerte(host):
    alertes = _alertes_du_protege(host)
    assert alertes, message(
        en=f"A shell opened in Pod {POD_PROTEGE} of {PROTEGE} raised no alert of rule {REGLE!r} within "
        f"30 seconds (read in {FALCO_JOURNAL}). The rule must exist under that exact name, be loaded by "
        "Falco (a file under /etc/falco/rules.d, then a restart), and match a shell process started in "
        "a container of that namespace.",
        fr=f"Un shell ouvert dans le Pod {POD_PROTEGE} de {PROTEGE} n'a levé aucune alerte de la règle "
        f"{REGLE!r} en 30 secondes (lu dans {FALCO_JOURNAL}). La règle doit exister sous ce nom exact, "
        "être chargée par Falco (un fichier sous /etc/falco/rules.d, puis un redémarrage), et reconnaître "
        "un processus shell lancé dans un conteneur de ce namespace.",
    )
    priorites = sorted({str(a.get("priority", "")).lower() for a in alertes})
    assert PRIORITE in priorites, message(
        en=f"Rule {REGLE!r} fires, but with priority {priorites} instead of {PRIORITE.upper()}.",
        fr=f"La règle {REGLE!r} alerte, mais avec la priorité {priorites} au lieu de {PRIORITE.upper()}.",
    )


# ----------------------------------------------------------------------
# P02. Un shell dans un autre namespace ne lève pas cette règle.
# ----------------------------------------------------------------------
def test_un_shell_ailleurs_ne_leve_pas_l_alerte(host):
    assert _alertes_du_protege(host), message(
        en=f"Rule {REGLE!r} does not fire for a shell in {PROTEGE}: that it stays silent elsewhere "
        "proves nothing yet.",
        fr=f"La règle {REGLE!r} n'alerte pas pour un shell dans {PROTEGE} : qu'elle se taise ailleurs "
        "ne prouve encore rien.",
    )
    _exiger_en_marche(host, AILLEURS, POD_AILLEURS)
    ailleurs = _alertes_apres_un_shell(host, AILLEURS, POD_AILLEURS, essais=6)
    assert not ailleurs, message(
        en=f"A shell opened in Pod {POD_AILLEURS} of {AILLEURS} raises rule {REGLE!r} too: its condition "
        f"does not restrict it to the {PROTEGE} namespace.",
        fr=f"Un shell ouvert dans le Pod {POD_AILLEURS} de {AILLEURS} déclenche aussi la règle "
        f"{REGLE!r} : sa condition ne la limite pas au namespace {PROTEGE}.",
    )


# ----------------------------------------------------------------------
# P03. Les règles fournies sont intactes.
# ----------------------------------------------------------------------
def test_les_regles_fournies_sont_intactes(host):
    attendu = host.run(
        "awk '$2 == \"etc/falco/falco_rules.yaml\" {print $1}' /var/lib/dpkg/info/falco.md5sums"
    ).stdout.strip()
    assert attendu, message(
        en="The Falco package no longer records the fingerprint of its rules: is it still installed?",
        fr="Le paquet Falco ne garde plus l'empreinte de ses règles : est-il toujours installé ?",
    )
    res = host.run(f"sudo md5sum {FALCO_REGLES}")
    actuel = res.stdout.split()[0] if res.rc == 0 and res.stdout.strip() else "absent"
    assert actuel == attendu, message(
        en=f"{FALCO_REGLES} differs from the file shipped with the package ({actuel} instead of {attendu}). "
        "The shipped rules are replaced at each update: a custom rule lives in its own file, which Falco "
        "also loads.",
        fr=f"{FALCO_REGLES} diffère du fichier livré par le paquet ({actuel} au lieu de {attendu}). Les "
        "règles fournies sont remplacées à chaque mise à jour : une règle personnalisée vit dans son "
        "propre fichier, que Falco charge aussi.",
    )
    assert _alertes_du_protege(host), message(
        en=f"The shipped rules are intact, but rule {REGLE!r} raises nothing: leaving the rules alone is "
        "only half of the requirement.",
        fr=f"Les règles fournies sont intactes, mais la règle {REGLE!r} ne lève rien : ne pas toucher aux "
        "règles n'est que la moitié de la demande.",
    )
