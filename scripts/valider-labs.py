#!/usr/bin/env python3
"""Joue chaque lab dans les deux sens et vérifie qu'il ne laisse aucune trace.

C'est la règle non négociable de CONTRIBUTING.md, automatisée : un test qui passe
ne prouve rien tant qu'on n'a pas vu échouer ce qui doit échouer. Pour chaque
lab, dans l'ordre :

    0. photographie du cluster : nœuds, namespaces, objets cluster, kube-system
    1. dsoxlab run            l'état initial est posé
    2. dsoxlab check          DOIT rendre 0 : le travail n'est pas fait
    3. la solution du formateur, jouée sur la cible par ssh
    4. dsoxlab check          DOIT rendre 100
    5. dsoxlab clean, run, check   DOIT rendre 0 : le setup se rejoue
    6. dsoxlab clean
    7. photographie à nouveau, comparée à la première : aucun écart admis

Le point 7 répond à une exigence précise : un lab qui laisse un namespace, un
ClusterRole, un taint ou un CoreDNS à zéro replica casse le lab suivant, et
personne ne s'en aperçoit avant l'apprenant.

    python3 scripts/valider-labs.py                      # tous les labs
    python3 scripts/valider-labs.py --lab cka-troubleshoot-dns
    python3 scripts/valider-labs.py --sans-rejeu         # saute l'étape 5

Le résultat de chaque lab est écrit dans validation-labs.json, à la racine :
c'est l'attestation que le lab a été joué, avec la date, la version de
Kubernetes et les mesures. Le journal complet de chaque lab va dans
~/.cache/dsoxlab/<catalogue>/validation-<lab>.log.

Prérequis : l'infrastructure provisionnée (dsoxlab provision), et la clé
d'automatisation en place (dsoxlab instructor bootstrap).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Le module partagé, IDENTIQUE dans les douze catalogues : il lit
# `dsoxlab check --json` et en tire un verdict à trois issues. `scripts/` est
# sur `sys.path` parce que c'est le répertoire de ce fichier.
import verdict_check
import yaml

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"
RESULTATS = RACINE / "validation-labs.json"
CACHE = Path.home() / ".cache" / "dsoxlab" / RACINE.name
SSH_CONFIG = CACHE / "ssh_config"

# Exécuté SUR le nœud, en root, par ssh : il rend une photographie JSON de ce
# qu'un lab pourrait laisser derrière lui. Les noms de Pods de kube-system
# changent à chaque redémarrage, on y regarde les Deployments, DaemonSets,
# Pods statiques et ConfigMaps ; ailleurs, chaque objet compte.
PHOTOGRAPHIE = r'''
import hashlib, json, subprocess
K = ["kubectl", "--kubeconfig", "/etc/kubernetes/admin.conf"]
def get(*args):
    out = subprocess.run(K + list(args) + ["-o", "json"], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else {"items": []}
photo = {"noeuds": {}, "cluster": {}, "kube-system": {}}
for n in get("get", "nodes")["items"]:
    conds = {c["type"]: c["status"] for c in n["status"].get("conditions", [])}
    photo["noeuds"][n["metadata"]["name"]] = {
        "ready": conds.get("Ready"),
        "unschedulable": bool(n["spec"].get("unschedulable", False)),
        "taints": sorted(t["key"] + "=" + t.get("value", "") + ":" + t["effect"] for t in n["spec"].get("taints") or []),
        "labels": n["metadata"].get("labels", {}),
        "version": n["status"]["nodeInfo"]["kubeletVersion"],
    }
ns = get("get", "namespaces")["items"]
photo["namespaces"] = sorted(x["metadata"]["name"] for x in ns if x["status"].get("phase") != "Terminating")
photo["terminating"] = sorted(x["metadata"]["name"] for x in ns if x["status"].get("phase") == "Terminating")
for kind in ("clusterroles", "clusterrolebindings", "storageclasses", "persistentvolumes", "runtimeclasses",
             "priorityclasses", "crds", "validatingwebhookconfigurations", "mutatingwebhookconfigurations",
             "ingressclasses"):
    photo["cluster"][kind] = sorted(x["metadata"]["name"] for x in get("get", kind)["items"])
ks = photo["kube-system"]
for d in get("get", "deployments", "-n", "kube-system")["items"]:
    ks["deployment/" + d["metadata"]["name"]] = [d["spec"].get("replicas", 0), d["status"].get("readyReplicas", 0)]
for d in get("get", "daemonsets", "-n", "kube-system")["items"]:
    ks["daemonset/" + d["metadata"]["name"]] = [d["status"].get("desiredNumberScheduled", 0), d["status"].get("numberReady", 0)]
# Le CNI vit dans son propre namespace ; ses Pods changent de nom à chaque
# redémarrage, on ne retient que le compte de son DaemonSet.
for d in get("get", "daemonsets", "-n", "kube-flannel")["items"]:
    ks["daemonset/kube-flannel/" + d["metadata"]["name"]] = [d["status"].get("desiredNumberScheduled", 0), d["status"].get("numberReady", 0)]
for p in get("get", "pods", "-n", "kube-system")["items"]:
    if any(o.get("kind") == "Node" for o in p["metadata"].get("ownerReferences") or []):
        ks["pod-statique/" + p["metadata"]["name"]] = p["status"].get("phase")
for c in get("get", "configmaps", "-n", "kube-system")["items"]:
    empreinte = hashlib.sha256(json.dumps(c.get("data") or {}, sort_keys=True).encode()).hexdigest()[:12]
    ks["configmap/" + c["metadata"]["name"]] = empreinte
objets = []
for kind in ("pods", "services", "configmaps", "secrets", "deployments", "daemonsets", "statefulsets", "jobs",
             "cronjobs", "networkpolicies", "serviceaccounts", "roles", "rolebindings", "persistentvolumeclaims",
             "ingresses", "resourcequotas", "limitranges"):
    for x in get("get", kind, "-A")["items"]:
        nsn = x["metadata"]["namespace"]
        if nsn in ("kube-system", "kube-flannel") or nsn in photo["terminating"]:
            continue
        objets.append(nsn + "/" + kind + "/" + x["metadata"]["name"])
photo["objets"] = sorted(objets)
print(json.dumps(photo))
'''


class Echec(Exception):
    pass


def commande(args: list[str], journal, timeout: int, entree: str | None = None) -> subprocess.CompletedProcess:
    """Lance une commande, journalise tout, rend le résultat sans lever."""
    journal.write(f"\n$ {' '.join(args)}\n")
    journal.flush()
    env = dict(os.environ, LAB_HOME=str(RACINE))
    try:
        # check=False : c'est l'appelant qui juge le code de retour, et
        # une exception ici perdrait la sortie déjà journalisée.
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env,
                             stdin=subprocess.DEVNULL if entree is None else None, input=entree,
                             cwd=RACINE, check=False)
    except subprocess.TimeoutExpired as e:
        journal.write(f"DÉLAI DÉPASSÉ après {timeout}s\n")
        raise Echec(f"délai de {timeout}s dépassé : {' '.join(args[:3])}") from e
    journal.write(res.stdout)
    journal.write(res.stderr)
    return res


def dsoxlab(sous_commande: list[str], journal, timeout: int) -> subprocess.CompletedProcess:
    return commande(["dsoxlab", *sous_commande], journal, timeout)


def check(lab: str, journal) -> dict:
    """Le `check` du lab, lu dans le CONTRAT et non dans l'encadré du terminal.

    `verdict_check.lire` rend `status`, qui est le seul champ à pouvoir servir
    de verdict : `ok` dit « aucun test n'a échoué », ce qui est vrai d'une suite
    entièrement skippée, et `score` vaut alors 0 sans que rien ait tourné.
    """
    res = dsoxlab(["check", lab, "--json"], journal, 600)
    try:
        return verdict_check.lire(res.stdout)
    except verdict_check.JsonIllisible as erreur:
        raise Echec(str(erreur)) from erreur


def cible(lab: Path) -> str:
    d = yaml.safe_load((lab / "lab.yaml").read_text(encoding="utf-8"))
    runtime = d.get("runtime") or {}
    cibles = runtime.get("targets") or []
    defaut = runtime.get("default")
    for t in cibles:
        if t.get("name") == defaut:
            return t["host"]
    if cibles:
        return cibles[0]["host"]
    raise Echec("lab.yaml : aucune cible runtime.targets")


def ssh(hote: str, script: str, journal, timeout: int, root: bool = False) -> subprocess.CompletedProcess:
    interpreteur = "sudo python3 -" if root else "bash -s"
    return commande(["ssh", "-F", str(SSH_CONFIG), hote, interpreteur], journal, timeout, entree=script)


def trace_prepare(hote: str, journal) -> str:
    """La fin du journal que fixtures/prepare.sh écrit sur le nœud.

    dsoxlab ne rend que « non-zero return code » quand un script de mise en
    situation échoue. Chaque prepare.sh trace donc dans
    /var/log/dsoxlab-prepare.log, et c'est là qu'on lit la cause.
    """
    res = ssh(hote, "sudo tail -n 25 /var/log/dsoxlab-prepare.log 2>/dev/null || true", journal, 60)
    trace = res.stdout.strip()
    return f"Fin de /var/log/dsoxlab-prepare.log sur {hote} :\n{trace[-1200:]}" if trace else \
        f"Aucune trace de prepare.sh sur {hote}, voir le journal."


def photographier(hote: str, journal) -> dict:
    res = ssh(hote, PHOTOGRAPHIE, journal, 180, root=True)
    lignes = [ligne for ligne in res.stdout.splitlines() if ligne.startswith("{")]
    if res.returncode != 0 or not lignes:
        raise Echec(f"photographie du cluster impossible : {res.stderr.strip()[-300:]}")
    return json.loads(lignes[-1])


def stable(photo: dict) -> bool:
    """Plus rien en Terminating, et kube-system a tous ses replicas prêts."""
    if photo["terminating"]:
        return False
    for cle, val in photo["kube-system"].items():
        if cle.startswith(("deployment/", "daemonset/")) and val[0] != val[1]:
            return False
    return True


def attendre_stabilite(hote: str, journal, delai: int = 300) -> dict:
    debut = time.time()
    photo = photographier(hote, journal)
    while not stable(photo) and time.time() - debut < delai:
        time.sleep(10)
        photo = photographier(hote, journal)
    return photo


#: Les labs dont le cleanup a le droit de laisser le cluster à une version PLUS
#: HAUTE que celle de la photographie initiale.
#:
#: Un seul y figure, et il n'y a pas de raison d'en ajouter sans en discuter :
#: `cka-kubeadm-upgrade` est le seul lab du catalogue qui touche à la version du
#: cluster. Son setup le rétrograde pour qu'il y ait quelque chose à monter, et
#: son cleanup le ramène à la version que le dépôt APT publie.
#:
#: La fenêtre que cela couvre : `pkgs.k8s.io/v1.37` n'est versionné que par
#: MINEURE, rien n'y fige le patch. Si une 1.37.2 paraît entre le provision et le
#: clean, la version relevée par le setup et celle que le cleanup trouve
#: diffèrent, sans que le lab y soit pour rien.
#:
#: La tolérance ne va QUE vers le haut. Une version qui redescend reste un écart,
#: et c'était exactement le défaut du 2026-10-12 : un cleanup qui visait
#: « 1.37.0-1.1 » en dur rétrogradait un cluster monté en 1.37.1.
VERSION_PEUT_MONTER = frozenset({"cka-kubeadm-upgrade"})

#: Les ConfigMaps de `kube-system` que `kubeadm upgrade apply` régénère, et les
#: labs qui ont le droit de les laisser différents.
#:
#: Même raison que `VERSION_PEUT_MONTER`, et même portée nominative :
#: `cka-kubeadm-upgrade` est le seul lab dont le cleanup remonte le cluster par
#: `kubeadm upgrade apply` au lieu de `kubeadm init`. Les ConfigMaps que kubeadm
#: y écrit ne sont donc pas ceux que le socle écrit, et cela n'a rien à voir
#: avec ce que le lab laisse derrière lui.
#:
#: Mesuré le 2026-10-15 en capturant le CONTENU des deux versions, et non leurs
#: seules empreintes : la différence tient en une ligne,
#: `resolvConf: /run/systemd/resolve/resolv.conf`, que `kubeadm upgrade apply`
#: ajoute en détectant systemd-resolved et que `kubeadm init` n'écrit pas.
#:
#: Ce desserrement est plus large que celui de la version : la photographie ne
#: porte que des empreintes, donc n'importe quelle différence sur ces deux
#: ConfigMaps passe. Le supprimer plutôt que l'accepter demanderait de faire
#: écrire `resolvConf` par le socle dès l'init, ce qui touche la façon dont les
#: soixante-quatre labs montent leur cluster.
CONFIGMAPS_REGENERES_PAR_UPGRADE = frozenset({
    "configmap/kubeadm-config",
    "configmap/kubelet-config",
})


def _version_en_tuple(brut: str) -> tuple[int, ...] | None:
    """« v1.37.10 » devient (1, 37, 10). None si ce n'est pas lisible.

    La comparaison de chaînes ne convient pas : « v1.37.9 » est supérieur à
    « v1.37.10 » en lexicographique, et ce genre d'inversion se paie un jour.
    """
    morceaux = brut.strip().lstrip("vV").split("+")[0].split("-")[0].split(".")
    try:
        return tuple(int(m) for m in morceaux)
    except ValueError:
        return None


def ecarts(avant: dict, apres: dict, ident: str = "") -> list[str]:
    out: list[str] = []
    monte_permis = ident in VERSION_PEUT_MONTER
    for nom, a in avant["noeuds"].items():
        b = apres["noeuds"].get(nom)
        if b is None:
            out.append(f"nœud {nom} : disparu")
            continue
        for cle in ("ready", "unschedulable", "taints", "labels", "version"):
            if a[cle] == b[cle]:
                continue
            if cle == "version" and monte_permis:
                va, vb = _version_en_tuple(str(a[cle])), _version_en_tuple(str(b[cle]))
                # Illisible d'un côté ou de l'autre : on ne conclut pas au vert.
                # « Je n'ai pas pu comparer » n'est pas « c'est bon ».
                if va is not None and vb is not None and vb >= va:
                    continue
            out.append(f"nœud {nom} : {cle} {a[cle]!r} devenu {b[cle]!r}")
    for nom in apres["noeuds"]:
        if nom not in avant["noeuds"]:
            out.append(f"nœud {nom} : apparu")
    for nom in sorted(set(apres["namespaces"]) - set(avant["namespaces"])):
        out.append(f"namespace laissé : {nom}")
    for nom in sorted(set(avant["namespaces"]) - set(apres["namespaces"])):
        out.append(f"namespace disparu : {nom}")
    for nom in apres["terminating"]:
        out.append(f"namespace encore en Terminating : {nom}")
    for kind in avant["cluster"]:
        a, b = set(avant["cluster"][kind]), set(apres["cluster"].get(kind, []))
        for nom in sorted(b - a):
            out.append(f"{kind} laissé : {nom}")
        for nom in sorted(a - b):
            out.append(f"{kind} disparu : {nom}")
    for cle in sorted(set(avant["kube-system"]) | set(apres["kube-system"])):
        a, b = avant["kube-system"].get(cle), apres["kube-system"].get(cle)
        if a == b:
            continue
        # Le lab d'upgrade remonte le cluster par `kubeadm upgrade apply`, qui
        # régénère ces ConfigMaps autrement que `kubeadm init` du socle. La
        # tolérance ne porte QUE sur eux, et QUE pour lui : l'apparition ou la
        # disparition d'un autre objet de kube-system reste un écart.
        if monte_permis and cle in CONFIGMAPS_REGENERES_PAR_UPGRADE:
            continue
        out.append(f"kube-system {cle} : {a!r} devenu {b!r}")
    for nom in sorted(set(apres["objets"]) - set(avant["objets"])):
        out.append(f"objet laissé : {nom}")
    for nom in sorted(set(avant["objets"]) - set(apres["objets"])):
        out.append(f"objet disparu : {nom}")
    return out


def valider(lab: Path, rejeu: bool) -> dict:
    ident = lab.name
    hote = cible(lab)
    CACHE.mkdir(parents=True, exist_ok=True)
    journal_path = CACHE / f"validation-{ident}.log"
    debut = time.time()
    resultat: dict = {"date": datetime.now(tz=UTC).date().isoformat(), "cible": hote, "journal": str(journal_path)}
    etapes: list[str] = []

    def dire(msg: str) -> None:
        etapes.append(msg)
        print(f"    {msg}", flush=True)

    with journal_path.open("w", encoding="utf-8") as journal:
        try:
            avant_photo = attendre_stabilite(hote, journal)
            resultat["kubernetes"] = next(iter(avant_photo["noeuds"].values()))["version"]
            dire(f"cluster photographié, {resultat['kubernetes']}, {len(avant_photo['objets'])} objets hors kube-system")

            res = dsoxlab(["run", ident], journal, 900)
            if res.returncode != 0:
                raise Echec(f"dsoxlab run a échoué (rc={res.returncode}). {trace_prepare(hote, journal)}")
            resultat["avant"] = check(ident, journal)
            dire(f"avant le travail : {resultat['avant']['passed']}/{resultat['avant']['total']}")

            solution = lab / "challenge" / "solution.sh"
            res = ssh(hote, solution.read_text(encoding="utf-8"), journal, 600)
            if res.returncode != 0:
                raise Echec(f"la solution du formateur a échoué (rc={res.returncode}) : "
                            f"{(res.stdout + res.stderr).strip()[-400:]}")
            resultat["apres"] = check(ident, journal)
            dire(f"après la solution : {resultat['apres']['passed']}/{resultat['apres']['total']}")

            if rejeu:
                dsoxlab(["clean", ident, "--yes"], journal, 600)
                res = dsoxlab(["run", ident], journal, 900)
                if res.returncode != 0:
                    raise Echec(f"le second dsoxlab run a échoué (rc={res.returncode}) : le setup ne se "
                                f"rejoue pas. {trace_prepare(hote, journal)}")
                resultat["rejeu"] = check(ident, journal)
                dire(f"après clean et run : {resultat['rejeu']['passed']}/{resultat['rejeu']['total']}")

            res = dsoxlab(["clean", ident, "--yes"], journal, 600)
            if res.returncode != 0:
                raise Echec(f"dsoxlab clean a échoué (rc={res.returncode})")
            apres_photo = attendre_stabilite(hote, journal)
            resultat["ecarts"] = ecarts(avant_photo, apres_photo, ident)
            dire("cluster rendu intact" if not resultat["ecarts"] else f"{len(resultat['ecarts'])} écart(s) après clean")
        except Echec as e:
            resultat["erreur"] = str(e)
            dire(f"ÉCHEC : {e}")
            # On tente quand même de rendre le cluster.
            with contextlib.suppress(Echec):
                dsoxlab(["clean", ident, "--yes"], journal, 600)

    resultat["duree_s"] = round(time.time() - debut)
    resultat["verdict"] = verdict(resultat, rejeu)
    resultat["etapes"] = etapes
    return resultat


def verdict(r: dict, rejeu: bool) -> str:
    if "erreur" in r:
        return "ROUGE"
    # Trois issues, pas deux. Une exécution qui n'a RIEN mesuré n'accuse pas le
    # lab : elle dit que le poste n'était pas prêt (répertoire de travail non
    # préparé, service arrêté, machine injoignable). La peindre en rouge
    # enverrait corriger un lab qui n'a jamais tourné ; la peindre en vert
    # serait pire. Elle reste donc à mesurer.
    etapes = [("avant le travail", r["avant"]), ("après la solution", r["apres"])]
    if "rejeu" in r:
        # Le rejeu entrait dans le jugement par `passed != 0`, qui est FAUX
        # quand rien n'a tourné : un second `run` dont la suite skippe passait
        # donc pour un point de départ sain.
        etapes.append(("après clean et run", r["rejeu"]))
    for quand, c in etapes:
        if not verdict_check.a_mesure(c):
            r["raisons"] = [f"{quand}, {verdict_check.pourquoi_rien_mesure(c)}"]
            return verdict_check.SKIP
    raisons = []
    if r["avant"]["passed"] != 0:
        raisons.append(f"{r['avant']['passed']} test(s) passent avant le travail")
    if r["apres"]["passed"] != r["apres"]["total"]:
        raisons.append("la solution ne fait pas passer tous les tests")
    if rejeu and r["rejeu"]["passed"] != 0:
        raisons.append(f"{r['rejeu']['passed']} test(s) passent après clean et run")
    if r["ecarts"]:
        raisons.append("le cluster n'est pas rendu intact")
    r["raisons"] = raisons
    return "VALIDE" if not raisons else "ROUGE"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lab", action="append", help="ne jouer que ce lab (répétable)")
    ap.add_argument("--sans-rejeu", action="store_true", help="sauter l'étape clean, run, check")
    args = ap.parse_args()

    if not SSH_CONFIG.is_file():
        print(f"{SSH_CONFIG} introuvable : dsoxlab n'a pas encore résolu l'inventaire, lancez dsoxlab status.",
              file=sys.stderr)
        return 2

    labs = sorted(p for p in LABS.iterdir() if (p / "lab.yaml").is_file())
    if args.lab:
        inconnus = set(args.lab) - {p.name for p in labs}
        if inconnus:
            print(f"lab(s) inconnu(s) : {', '.join(sorted(inconnus))}", file=sys.stderr)
            return 2
        labs = [p for p in labs if p.name in args.lab]

    anciens = json.loads(RESULTATS.read_text(encoding="utf-8")) if RESULTATS.is_file() else {}
    rouges = 0
    skips = 0
    for lab in labs:
        print(f"\n{lab.name}", flush=True)
        r = valider(lab, rejeu=not args.sans_rejeu)
        anciens[lab.name] = r
        RESULTATS.write_text(json.dumps(anciens, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                             encoding="utf-8")
        if r["verdict"] != verdict_check.VALIDE:
            # Le SKIP est compté à part : il ne se répare pas, il se remesure.
            if r["verdict"] == verdict_check.SKIP:
                skips += 1
            else:
                rouges += 1
            for raison in r.get("raisons", []):
                print(f"    ✘ {raison}")
            for e in r.get("ecarts", [])[:15]:
                print(f"      {e}")
        print(f"    {r['verdict']} en {r['duree_s']} s")

    print(f"\n{len(labs) - rouges - skips} valide(s), {rouges} rouge(s), "
          f"{skips} à remesurer sur {len(labs)} lab(s). Détail : {RESULTATS}")
    if rouges:
        return verdict_check.RC_UN_ROUGE
    # Un catalogue sans rouge n'est pas prouvé pour autant : le code est
    # distinct pour qu'une construction automatisée ne confonde pas « rien à
    # réparer » avec « tout est mesuré ».
    return verdict_check.RC_UN_SKIP if skips else verdict_check.RC_TOUT_VALIDE


if __name__ == "__main__":
    sys.exit(main())
