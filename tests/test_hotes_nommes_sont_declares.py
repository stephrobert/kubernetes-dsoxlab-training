"""Un lab qui nomme un hôte doit le déclarer, sinon `start` ne le monte pas.

Depuis dsoxlab 0.8.2 (issue #358), `dsoxlab start <lab>` ne provisionne que les
hôtes **déclarés** par le lab : l'hôte de sa target résolue, plus ceux de ses
`roles`. Avant, il montait tout le catalogue, et un lab pouvait donc se servir
d'un hôte qu'il ne déclarait nulle part — le worker était là par accident.

Mesuré le 2026-11-10, **après** la correction de dsoxlab : six labs nommaient
`k8s-w1.lab` dans leurs tests sans le déclarer. Quatre passaient par deux
`targets` ALTERNATIVES, que le contrat destine au choix de l'apprenant
(`--target`) et non à un besoin cumulé ; deux n'en déclaraient qu'une seule.
Tous interrogent pourtant ce nœud par l'API du cluster, et
`cka-taints-tolerations-placement` porte même le message qui s'affichait alors :
« Node k8s-w1.lab cannot be found. »

Le contrat prévoit exactement le bon champ pour cela : `roles`, « les hôtes
additionnels utilisés simultanément par le lab ». C'est lui que `start` lit, et
c'est le socle kubeadm qui joint ensuite au cluster tout hôte dont le `meta.yml`
déclare `role: worker`.

CE QUE CE MODULE REGARDE, et pourquoi c'est étroit à dessein : les seuls FQDN
retenus sont ceux que le `meta.yml` déclare comme hôtes. Un nom de domaine qui
n'est pas un hôte du catalogue est ignoré, et ce n'est pas une tolérance : le
test de `cks-ingress-tls` nomme `vitrine.lab`, qui est le CN d'un certificat
TLS et non une machine. Un motif plus large aurait fabriqué un faux positif
portant l'autorité d'un chiffre.

    pytest tests/test_hotes_nommes_sont_declares.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"
REPERTOIRES = sorted(p.parent for p in LABS.glob("*/lab.yaml"))
IDS = [p.name for p in REPERTOIRES]

#: Un FQDN d'hôte tel que le `meta.yml` les écrit. Le motif est large, et c'est
#: le recoupement avec les hôtes déclarés qui restreint, pas lui.
FQDN = re.compile(r"""["']([a-z0-9][a-z0-9.-]*\.lab)["']""")


def _hotes_du_catalogue() -> set[str]:
    meta = yaml.safe_load((RACINE / "meta.yml").read_text(encoding="utf-8")) or {}
    hosts = ((meta.get("infra") or {}).get("hosts")) or []
    return {h["name"] for h in hosts if h.get("name")}


HOTES = _hotes_du_catalogue()


def test_le_catalogue_declare_des_hotes() -> None:
    """Le garde-fou de ce module.

    Si `HOTES` était vide, tous les tests ci-dessous passeraient sans rien
    mesurer : aucun FQDN ne serait jamais retenu. Un contrôle qui ne peut pas
    refuser ne contrôle rien.
    """
    assert len(HOTES) >= 2, (
        f"{len(HOTES)} hôte(s) lu(s) dans meta.yml : la lecture est en panne, "
        "et ce module mesurerait sa propre panne."
    )


def _par_target(lab: Path) -> list[tuple[str, set[str]]]:
    """Pour CHAQUE target, les hôtes que `start` monterait en la choisissant.

    PAR TARGET, et non en union : `start` ne monte que la target RÉSOLUE, son
    hôte et ses rôles. Une première version de ce contrôle prenait l'union de
    toutes les targets, et laissait donc passer les quatre labs qui déclarent
    `k8s-w1.lab` comme target ALTERNATIVE : joués avec leur target par défaut,
    `cp`, ils cassent quand même. Le contrôle n'en trouvait que deux sur six, et
    c'est le compte qui a révélé l'erreur, pas la relecture.

    Un lab doit donc marcher avec CHACUNE de ses targets, puisque l'apprenant
    choisit librement par `--target`.
    """
    contrat = yaml.safe_load((lab / "lab.yaml").read_text(encoding="utf-8")) or {}
    runtime = contrat.get("runtime") or {}
    sorties: list[tuple[str, set[str]]] = []
    for cible in runtime.get("targets") or []:
        montes = {cible["host"]} if cible.get("host") else set()
        montes |= {h for h in (cible.get("roles") or {}).values() if h}
        sorties.append((cible.get("name") or "?", montes))
    return sorties


def _hotes_nommes_par(lab: Path) -> set[str]:
    """Les hôtes du catalogue que les tests et les playbooks du lab nomment."""
    nommes: set[str] = set()
    fichiers = list((lab / "challenge" / "tests").glob("*.py"))
    fichiers += [p for p in (lab / "setup.yaml", lab / "cleanup.yaml") if p.is_file()]
    for f in fichiers:
        nommes |= set(FQDN.findall(f.read_text(encoding="utf-8")))
    # Le recoupement : seuls les FQDN qui sont VRAIMENT des hôtes du catalogue.
    return nommes & HOTES


@pytest.mark.parametrize("lab", REPERTOIRES, ids=IDS)
def test_tout_hote_nomme_est_declare(lab: Path) -> None:
    nommes = _hotes_nommes_par(lab)
    if not nommes:
        pytest.skip("ce lab ne nomme aucun hôte du catalogue")

    fautives = [
        (nom, sorted(nommes - montes))
        for nom, montes in _par_target(lab)
        if nommes - montes
    ]

    assert not fautives, (
        f"{lab.name} se sert d'hôtes que certaines de ses targets ne montent "
        f"pas :\n\n"
        + "".join(f"  target « {nom} » ne monterait pas {manque}\n" for nom, manque in fautives)
        + f"\n  nommé dans ses tests ou playbooks : {sorted(nommes)}\n\n"
        "Depuis dsoxlab 0.8.2, `start` ne provisionne que les hôtes déclarés : "
        "cet hôte ne sera pas monté, et le lab échouera sur un nœud introuvable. "
        "Avant, `start` montait tout le catalogue et le défaut était invisible.\n\n"
        "Déclarez-le par un rôle sur la target concernée, ce que le contrat "
        "prévoit pour « les hôtes additionnels utilisés simultanément » :\n\n"
        "    targets:\n"
        "      - name: cp\n"
        "        host: k8s-cp.lab\n"
        "        roles:\n"
        "          worker: k8s-w1.lab\n"
    )


def test_le_controle_regarde_au_moins_un_lab() -> None:
    """Sans cela, un `labs/` vide ou un glob cassé rendrait ce module muet."""
    concernes = [lab for lab in REPERTOIRES if _hotes_nommes_par(lab)]
    assert len(concernes) >= 5, (
        f"{len(concernes)} lab(s) nomment un hôte du catalogue : trop peu pour "
        "que ce contrôle mesure quoi que ce soit. Le motif ou la lecture du "
        "meta.yml est en panne."
    )
