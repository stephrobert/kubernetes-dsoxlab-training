#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Joue chaque lab dans les deux sens et vérifie qu'il ne laisse aucune trace.

C'est la règle non négociable du CLAUDE.md, automatisée : un test qui passe
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
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

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
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env,
                             stdin=subprocess.DEVNULL if entree is None else None, input=entree, cwd=RACINE)
    except subprocess.TimeoutExpired as e:
        journal.write(f"DÉLAI DÉPASSÉ après {timeout}s\n")
        raise Echec(f"délai de {timeout}s dépassé : {' '.join(args[:3])}") from e
    journal.write(res.stdout)
    journal.write(res.stderr)
    return res


def dsoxlab(sous_commande: list[str], journal, timeout: int) -> subprocess.CompletedProcess:
    return commande(["dsoxlab", *sous_commande], journal, timeout)


def check(lab: str, journal) -> dict:
    """Rend {"passed", "total", "score"} de dsoxlab check --json."""
    res = dsoxlab(["check", lab, "--json"], journal, 600)
    try:
        d = json.loads(res.stdout)["check"]
    except (json.JSONDecodeError, KeyError) as e:
        raise Echec(f"dsoxlab check n'a pas rendu de JSON lisible : {e}") from e
    return {"passed": d.get("passed", 0), "total": d.get("total", 0), "score": d.get("score", 0)}


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
    lignes = [l for l in res.stdout.splitlines() if l.startswith("{")]
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


def ecarts(avant: dict, apres: dict) -> list[str]:
    out: list[str] = []
    for nom, a in avant["noeuds"].items():
        b = apres["noeuds"].get(nom)
        if b is None:
            out.append(f"nœud {nom} : disparu")
            continue
        for cle in ("ready", "unschedulable", "taints", "labels", "version"):
            if a[cle] != b[cle]:
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
        if a != b:
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
    resultat: dict = {"date": date.today().isoformat(), "cible": hote, "journal": str(journal_path)}
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
            resultat["ecarts"] = ecarts(avant_photo, apres_photo)
            dire("cluster rendu intact" if not resultat["ecarts"] else f"{len(resultat['ecarts'])} écart(s) après clean")
        except Echec as e:
            resultat["erreur"] = str(e)
            dire(f"ÉCHEC : {e}")
            # On tente quand même de rendre le cluster.
            try:
                dsoxlab(["clean", ident, "--yes"], journal, 600)
            except Echec:
                pass

    resultat["duree_s"] = round(time.time() - debut)
    resultat["verdict"] = verdict(resultat, rejeu)
    resultat["etapes"] = etapes
    return resultat


def verdict(r: dict, rejeu: bool) -> str:
    if "erreur" in r:
        return "ROUGE"
    raisons = []
    if r["avant"]["passed"] != 0:
        raisons.append(f"{r['avant']['passed']} test(s) passent avant le travail")
    if r["apres"]["passed"] != r["apres"]["total"] or r["apres"]["total"] == 0:
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
    for lab in labs:
        print(f"\n{lab.name}", flush=True)
        r = valider(lab, rejeu=not args.sans_rejeu)
        anciens[lab.name] = r
        RESULTATS.write_text(json.dumps(anciens, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                             encoding="utf-8")
        if r["verdict"] != "VALIDE":
            rouges += 1
            for raison in r.get("raisons", []):
                print(f"    ✘ {raison}")
            for e in r.get("ecarts", [])[:15]:
                print(f"      {e}")
        print(f"    {r['verdict']} en {r['duree_s']} s")

    print(f"\n{len(labs) - rouges} valide(s), {rouges} rouge(s) sur {len(labs)} lab(s). Détail : {RESULTATS}")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
