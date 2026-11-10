"""Le validateur amorce le socle, et un socle absent ne vaut pas un lab fautif.

Deux exigences, nées du même fait : **il n'y a aucun point d'accroche après le
provisionnement**. Le cluster n'existe que parce que le `setup.yaml` de chaque
lab inclut son socle, `shared/kubeadm-cluster.yml` ou `shared/kind-cluster.yml`
(dsoxlab#213, et `test_pieges_du_depot.py` le tient côté labs). La conséquence
pour le validateur n'avait pas été tirée : il photographiait le cluster
**avant** le premier `dsoxlab run`, donc avant que le socle existe.

Mesuré le 2026-11-10, sur l'hôte kind, deux échecs de nature différente :

- **hôte nu** : ni Docker, ni kind, ni kubectl, `/etc/kind/` absent, zéro cible
  pour la photographie, et le script mourait sur un `StopIteration` en une
  seconde sans rien écrire ;
- **socle du lab absent mais un autre cluster présent** : la campagne se
  jouait, le cycle `0 → 7/7 → 0` était PARFAIT, et le verdict sortait ROUGE sur
  **184 faux écarts** qui étaient le socle lui-même. Le validateur reprochait
  au challenge d'avoir laissé le cluster `boutique`, c'est-à-dire son propre
  socle, que son `cleanup.yaml` déclare expressément conserver.

Les labs kubeadm n'y échappaient que parce qu'un lab joué plus tôt avait laissé
le cluster debout : un succès qui dépend de l'ORDRE D'EXÉCUTION.

Ce module **juge dans les deux sens**, parce qu'un contrôle qui ne peut pas
refuser ne contrôle rien :

- il vérifie que `amorcer()` existe, qu'il joue `run` puis `clean --yes`, et
  qu'il échoue en `SocleAbsent` et non en `Echec` ;
- il vérifie que `verdict()` rend `SKIP` sur un socle non mesurable, **et**
  qu'il rend bien ROUGE sur une vraie erreur : si les deux rendaient SKIP, le
  premier contrôle passerait sans rien mesurer ;
- il vérifie que l'ordre du jugement est tenu, en construisant le cas qui
  portait le défaut : un résultat qui a `non_mesurable` **et** `erreur`. Dans
  l'ordre inverse, celui d'avant la correction, il sortait ROUGE.

    pytest tests/test_amorcage_du_socle.py -v
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
VALIDATEUR = RACINE / "scripts" / "valider-labs.py"

# L'idiome de ce dépôt pour atteindre `scripts/` depuis un test.
sys.path.insert(0, str(RACINE / "scripts"))


def _module():
    """Charge `valider-labs.py` malgré son tiret, qui interdit l'import normal.

    Le module est chargé pour de vrai, et non analysé : c'est ce qui attrape
    une variable supprimée par une substitution malheureuse, là où `ast.parse`
    accepterait le fichier avant de lever un `NameError` au premier appel.
    """
    spec = importlib.util.spec_from_file_location("valider_labs", VALIDATEUR)
    assert spec and spec.loader, f"{VALIDATEUR} n'est pas chargeable."
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def validateur():
    return _module()


# ----------------------------------------------------------------------
# Le garde-fou de ce module : s'il ne charge pas le validateur, il ne
# mesure rien, et tous les tests qui suivent passeraient pour de bonnes
# raisons apparentes.
# ----------------------------------------------------------------------
def test_le_validateur_se_charge(validateur) -> None:
    assert hasattr(validateur, "valider"), (
        "le module chargé n'a pas de `valider` : ce n'est pas le validateur, "
        "et tout ce fichier mesure alors sa propre panne."
    )


def test_l_amorcage_existe_et_leve_socle_absent(validateur) -> None:
    assert hasattr(validateur, "amorcer"), (
        "`amorcer()` a disparu du validateur. Sans elle, la photographie de "
        "référence est prise avant que le socle du lab existe, et le verdict "
        "reproche au lab son propre socle."
    )
    assert hasattr(validateur, "SocleAbsent"), "`SocleAbsent` a disparu."
    assert issubclass(validateur.SocleAbsent, validateur.Echec), (
        "`SocleAbsent` doit dériver d'`Echec`, sinon le `except Echec` de "
        "`valider()` ne l'attrape pas et la campagne entière s'arrête."
    )


def test_l_amorcage_joue_run_puis_clean_avec_yes(validateur) -> None:
    """`--yes` n'est pas décoratif, et l'ordre non plus.

    Hors terminal, `dsoxlab clean` demande une confirmation que l'entrée
    fermée ne peut pas donner : il sort en 2 sans rien nettoyer. Et un `clean`
    avant le `run` ne poserait aucun socle.
    """
    source = ast.parse(VALIDATEUR.read_text(encoding="utf-8"))
    fonction = next(
        (n for n in ast.walk(source)
         if isinstance(n, ast.FunctionDef) and n.name == "amorcer"),
        None,
    )
    assert fonction is not None, "`amorcer` n'est pas une fonction du module."

    appels: list[list[str]] = []
    for noeud in ast.walk(fonction):
        if not isinstance(noeud, ast.Call):
            continue
        if getattr(noeud.func, "id", "") != "dsoxlab":
            continue
        if not noeud.args or not isinstance(noeud.args[0], ast.List):
            continue
        appels.append([
            e.value for e in noeud.args[0].elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)
        ])

    assert len(appels) == 2, (
        f"`amorcer` doit appeler dsoxlab deux fois, run puis clean ; "
        f"trouvé {len(appels)} appel(s) : {appels}"
    )
    assert "run" in appels[0], f"le premier appel n'est pas un run : {appels[0]}"
    assert "clean" in appels[1], f"le second appel n'est pas un clean : {appels[1]}"
    assert "--yes" in appels[1], (
        "le `clean` de l'amorçage n'a pas `--yes`. Hors terminal, il demande "
        "une confirmation que l'entrée fermée ne peut pas donner, sort en 2 "
        "sans nettoyer, et la photographie de référence porte alors l'état de "
        "travail du lab : tous les écarts qui suivent sont faux."
    )


def test_l_amorcage_ne_leve_jamais_echec_nu(validateur) -> None:
    """Un socle qui ne monte pas ne doit pas accuser le lab.

    `raise Echec` dans `amorcer` rangerait le résultat en ROUGE, donc
    enverrait corriger un lab qui n'a pas tourné.
    """
    source = ast.parse(VALIDATEUR.read_text(encoding="utf-8"))
    fonction = next(
        n for n in ast.walk(source)
        if isinstance(n, ast.FunctionDef) and n.name == "amorcer"
    )
    leves = [
        getattr(n.exc.func, "id", "") for n in ast.walk(fonction)
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
    ]
    assert leves, "`amorcer` ne lève rien : un socle en échec passerait inaperçu."
    assert set(leves) == {"SocleAbsent"}, (
        f"`amorcer` lève {sorted(set(leves))} ; seul `SocleAbsent` convient, "
        "parce qu'`Echec` vaut ROUGE et accuse un lab qu'on n'a pas joué."
    )


# ----------------------------------------------------------------------
# `verdict()`, jugé dans les deux sens.
# ----------------------------------------------------------------------
def _resultat_sain() -> dict:
    """Un résultat de campagne parfaite, sur lequel greffer un seul écart."""
    mesure = {"passed": 0, "total": 7, "skipped": 0, "status": "failed", "score": 0}
    reussi = {"passed": 7, "total": 7, "skipped": 0, "status": "passed", "score": 100}
    return {
        "avant": dict(mesure),
        "apres": dict(reussi),
        "rejeu": dict(mesure),
        "ecarts": [],
    }


def test_un_socle_non_mesurable_rend_skip(validateur) -> None:
    r = _resultat_sain()
    r["non_mesurable"] = "le socle n'a pas pu être posé"
    assert validateur.verdict(r, rejeu=True) == validateur.verdict_check.SKIP, (
        "un socle non mesurable doit rendre SKIP : il se remesure, il ne se "
        "répare pas."
    )


def test_une_vraie_erreur_rend_toujours_rouge(validateur) -> None:
    """Le contre-témoin, sans lequel le test précédent ne mesurerait rien.

    Si `verdict()` rendait SKIP sur tout, le test du socle passerait pour une
    raison qui n'a rien à voir avec le socle.
    """
    r = _resultat_sain()
    r["erreur"] = "la solution du formateur a échoué"
    assert validateur.verdict(r, rejeu=True) == "ROUGE", (
        "une vraie erreur doit rester ROUGE, sans quoi le SKIP du socle "
        "absorberait tous les échecs."
    )


def test_le_non_mesurable_est_juge_avant_l_erreur(validateur) -> None:
    """Le cas exact que portait le défaut, et que l'ordre inverse ratait.

    Quand l'amorçage échoue, `valider()` tente quand même de rendre le
    cluster, et ce nettoyage peut échouer à son tour. Le résultat porte alors
    LES DEUX champs. Jugé dans l'ordre inverse, il sortait ROUGE et accusait un
    lab qui n'avait pas tourné.
    """
    r = _resultat_sain()
    r["non_mesurable"] = "le socle n'a pas pu être posé"
    r["erreur"] = "et le nettoyage de rattrapage a échoué aussi"
    assert validateur.verdict(r, rejeu=True) == validateur.verdict_check.SKIP, (
        "`non_mesurable` doit être jugé AVANT `erreur` : un socle qui n'a pas "
        "pu être posé n'est pas un lab fautif, c'est un lab qu'on n'a pas joué."
    )


def test_une_campagne_parfaite_reste_valide(validateur) -> None:
    """Le second contre-témoin : rien de tout cela ne doit noircir un lab sain."""
    assert validateur.verdict(_resultat_sain(), rejeu=True) == "VALIDE"


def test_l_option_sans_amorcage_existe_et_est_documentee() -> None:
    """L'échappatoire doit exister, et dire ce qu'elle coûte.

    Une option qui saute un contrôle sans expliquer le risque finit employée
    par défaut.
    """
    texte = VALIDATEUR.read_text(encoding="utf-8")
    assert "--sans-amorcage" in texte, "l'option `--sans-amorcage` a disparu."
    source = ast.parse(texte)
    aides = [
        kw.value.value
        for n in ast.walk(source)
        if isinstance(n, ast.Call)
        for kw in n.keywords
        if kw.arg == "help" and isinstance(kw.value, ast.Constant)
        and isinstance(kw.value.value, str)
        and any(
            isinstance(a, ast.Constant) and a.value == "--sans-amorcage"
            for a in n.args
        )
    ]
    assert aides, "`--sans-amorcage` n'a pas de texte d'aide."
    assert "faux rouge" in aides[0], (
        "l'aide de `--sans-amorcage` ne dit pas ce qu'on risque en l'employant. "
        f"Trouvé : {aides[0]!r}"
    )
