"""test_functional.py : k8s-challenge-placer-et-plafonner

Le challenge du module Scheduling et capacité. Ces tests lisent l'état du
CLUSTER, jamais les commandes tapées. Un test vérifie un seul état, dans
l'ordre de la fiche.

Le placement se juge sur deux faits : la règle écrite dans la description du
Deployment, et l'endroit où ses Pods en marche tournent vraiment. L'un sans
l'autre passerait par hasard, ou ne prouverait rien.

Le plafond et les valeurs par défaut se jugent en dry-run côté serveur :
l'admission joue, rien n'est créé.

Le dernier état, « sous charge, le nombre de réplicas dépasse le minimum », est
le seul qui demande du temps. La charge est générée PAR LE TEST, pas par
l'apprenant : il fait tourner une boucle de calcul dans chaque Pod d'accueil
pendant une durée bornée, puis attend que le HPA fasse grossir le Deployment,
au plus deux minutes. metrics-server mesure toutes les quinze secondes et le
HPA décide toutes les quinze secondes : une montée se voit d'ordinaire en moins
d'une minute. Le test ne charge rien si le HPA ne lit encore aucune métrique :
la situation de départ se note vite, et dsoxlab coupe pytest au bout de
300 secondes.

Les huit tests échouent sur l'état que pose le setup : aucun taint ni label,
aucune règle de placement, aucun plafond, aucune valeur par défaut, aucun HPA.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/capacite.kubeconfig"
NS = "atelier"
RESERVE = "capacite-worker3"
ETIQUETE = "capacite-worker2"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
PLAFOND = {"requests.cpu": "2", "requests.memory": "2Gi", "limits.cpu": "4",
           "limits.memory": "4Gi", "pods": "15"}
DEFAUTS = {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "200m", "memory": "256Mi"}}
BORNES = (2, 5)
CIBLE_CPU = 50
ATTENTE_METRIQUE = 60
#: La charge dure un peu plus que l'attente : elle ne doit pas cesser pendant
#: qu'on regarde. Elle s'arrête seule ensuite.
ATTENTE_MONTEE = 120
DUREE_CHARGE = 130
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, ns: str | None, args: str) -> dict | None:
    portee = f"-n {ns} " if ns else ""
    res = host.run(f"{ADMIN} {portee}{args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _quantite(valeur) -> float | None:
    """Une quantité Kubernetes en nombre : 100m vaut 0.1, 128Mi vaut 134217728."""
    if valeur is None:
        return None
    texte = str(valeur).strip()
    suffixes = {"m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12,
                "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40}
    for suffixe in sorted(suffixes, key=len, reverse=True):
        if texte.endswith(suffixe):
            try:
                return float(texte[: -len(suffixe)]) * suffixes[suffixe]
            except ValueError:
                return None
    try:
        return float(texte)
    except ValueError:
        return None


def _deployment(host, nom: str) -> dict:
    dep = _json(host, NS, f"get deployment {nom}")
    assert dep is not None, message(
        en=f"No Deployment {nom} in {NS} any more: it is placed, not removed.",
        fr=f"Plus de Deployment {nom} dans {NS} : il se place, il ne se retire pas.",
    )
    return dep


def _pods_de(host, nom: str) -> list[dict]:
    """Les Pods en marche créés par le ReplicaSet du Deployment : un Pod nu posé
    à côté, avec la même étiquette, n'est pas l'application."""
    pods = (_json(host, NS, f"get pods -l app={nom}") or {}).get("items") or []
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")
            and (p.get("status") or {}).get("phase") == "Running"
            and any(o.get("kind") == "ReplicaSet" and o.get("name", "").startswith(f"{nom}-")
                    for o in p["metadata"].get("ownerReferences") or [])]


def _noeuds(pods: list[dict]) -> list[str]:
    return sorted(p["spec"].get("nodeName") or "" for p in pods)


def _termes_obligatoires(spec: dict) -> list[dict]:
    affinite = ((spec.get("affinity") or {}).get("nodeAffinity") or {})
    return (affinite.get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or []


def _exige(spec: dict, cle: str, valeur: str) -> bool:
    """Le Pod exige un nœud qui porte cle=valeur : par nodeSelector, ou par une
    affinité obligatoire dont CHAQUE terme l'exige (les termes sont des OU)."""
    if (spec.get("nodeSelector") or {}).get(cle) == valeur:
        return True
    termes = _termes_obligatoires(spec)
    return bool(termes) and all(
        any(e.get("key") == cle and e.get("operator") == "In" and valeur in (e.get("values") or [])
            for e in t.get("matchExpressions") or [])
        for t in termes)


# ----------------------------------------------------------------------
# 1. Le nœud réservé porte le taint et le label demandés.
# ----------------------------------------------------------------------
def test_le_noeud_reserve_porte_son_taint_et_son_label(host):
    noeud = _json(host, None, f"get node {RESERVE}") or {}
    taints = sorted(f"{t['key']}={t.get('value', '')}:{t['effect']}" for t in (noeud.get("spec") or {}).get("taints") or [])
    label = ((noeud.get("metadata") or {}).get("labels") or {}).get("dedie")
    assert "dedie=calcul:NoSchedule" in taints and label == "calcul", message(
        en=f"The node {RESERVE} carries the taints {taints or 'none'} and the label dedie={label}. Expected the "
        "taint dedie=calcul:NoSchedule and the label dedie=calcul.",
        fr=f"Le nœud {RESERVE} porte les taints {taints or 'aucun'} et le label dedie={label}. Attendu le taint "
        "dedie=calcul:NoSchedule et le label dedie=calcul.",
    )


# ----------------------------------------------------------------------
# 2. rendu tourne sur le nœud réservé, par tolérance et par sélection ;
#    accueil tourne ailleurs.
# ----------------------------------------------------------------------
def _tolere(spec: dict) -> bool:
    for t in spec.get("tolerations") or []:
        if t.get("effect") not in (None, "", "NoSchedule"):
            continue
        if t.get("operator") == "Exists" and t.get("key") in ("dedie", None):
            return True
        if t.get("key") == "dedie" and t.get("operator", "Equal") == "Equal" and t.get("value") == "calcul":
            return True
    return False


def test_rendu_sur_le_noeud_reserve_et_accueil_ailleurs(host):
    spec = _deployment(host, "rendu")["spec"]["template"]["spec"]
    tolere, choisit = _tolere(spec), _exige(spec, "dedie", "calcul")
    epingle = bool(spec.get("nodeName"))
    rendu = _noeuds(_pods_de(host, "rendu"))
    accueil = _noeuds(_pods_de(host, "accueil"))
    ok = (tolere and choisit and not epingle and bool(rendu) and set(rendu) == {RESERVE}
          and bool(accueil) and RESERVE not in accueil)
    assert ok, message(
        en=f"rendu {'tolerates' if tolere else 'does not tolerate'} the taint and "
        f"{'asks for' if choisit else 'does not ask for'} the node dedie=calcul"
        f"{', and is pinned by nodeName' if epingle else ''}; it runs on {rendu or 'no node'}, accueil on "
        f"{accueil or 'no node'}. Expected rendu on {RESERVE} through a toleration AND a node selection, and "
        "accueil elsewhere. A Pod placed before the taint stays where it is until it is recreated.",
        fr=f"rendu {'tolère' if tolere else 'ne tolère pas'} le taint et "
        f"{'demande' if choisit else 'ne demande pas'} le nœud dedie=calcul"
        f"{', et il est épinglé par nodeName' if epingle else ''} ; il tourne sur {rendu or 'aucun nœud'}, "
        f"accueil sur {accueil or 'aucun nœud'}. Attendu rendu sur {RESERVE} par une tolérance ET une sélection "
        "de nœud, et accueil ailleurs. Un Pod placé avant le taint reste où il est tant qu'il n'est pas recréé.",
    )


# ----------------------------------------------------------------------
# 3. stockage : une affinité obligatoire et une préférée, sur le nœud étiqueté.
# ----------------------------------------------------------------------
def test_stockage_affinite_obligatoire_et_preferee(host):
    spec = _deployment(host, "stockage")["spec"]["template"]["spec"]
    termes = _termes_obligatoires(spec)
    obligatoire = bool(termes) and all(
        any(e.get("key") == "disque" and e.get("operator") == "In" and "ssd" in (e.get("values") or [])
            for e in t.get("matchExpressions") or []) for t in termes)
    preferees = ((spec.get("affinity") or {}).get("nodeAffinity") or {}).get(
        "preferredDuringSchedulingIgnoredDuringExecution") or []
    preferee = any(p.get("weight") == 50 and any(
        e.get("key") == "topology.kubernetes.io/zone" and "zone-b" in (e.get("values") or [])
        for e in (p.get("preference") or {}).get("matchExpressions") or []) for p in preferees)
    etiquette = (((_json(host, None, f"get node {ETIQUETE}") or {}).get("metadata") or {})
                 .get("labels") or {}).get("disque")
    pods = _pods_de(host, "stockage")
    etiquetes = {n["metadata"]["name"] for n in (_json(host, None, "get nodes -l disque=ssd") or {}).get("items") or []}
    places = _noeuds(pods)
    ok = obligatoire and preferee and etiquette == "ssd" and bool(places) and set(places) <= etiquetes
    assert ok, message(
        en=f"stockage: required affinity on disque=ssd {'present' if obligatoire else 'missing'}, preference of "
        f"weight 50 for zone-b {'present' if preferee else 'missing'}; {ETIQUETE} carries disque={etiquette}; the "
        f"Pods run on {places or 'no node'}. Expected both affinities, the label on {ETIQUETE}, and the Pods on a "
        "node labelled disque=ssd.",
        fr=f"stockage : affinité obligatoire sur disque=ssd {'présente' if obligatoire else 'absente'}, préférence "
        f"de poids 50 pour zone-b {'présente' if preferee else 'absente'} ; {ETIQUETE} porte disque={etiquette} ; "
        f"les Pods tournent sur {places or 'aucun nœud'}. Attendu les deux affinités, le label sur {ETIQUETE}, et "
        "les Pods sur un nœud étiqueté disque=ssd.",
    )


# ----------------------------------------------------------------------
# 4. Les réplicas de galerie sont répartis sur des nœuds différents.
# ----------------------------------------------------------------------
def _regle_de_repartition(dep: dict) -> bool:
    spec = dep["spec"]["template"]["spec"]
    etiquettes = dep["spec"]["template"]["metadata"].get("labels") or {}

    def vise(selecteur: dict) -> bool:
        attendues = (selecteur or {}).get("matchLabels") or {}
        return bool(attendues) and all(etiquettes.get(k) == v for k, v in attendues.items())

    anti = ((spec.get("affinity") or {}).get("podAntiAffinity") or {}).get(
        "requiredDuringSchedulingIgnoredDuringExecution") or []
    if any(t.get("topologyKey") == "kubernetes.io/hostname" and vise(t.get("labelSelector")) for t in anti):
        return True
    return any(c.get("topologyKey") == "kubernetes.io/hostname" and c.get("whenUnsatisfiable") == "DoNotSchedule"
               and c.get("maxSkew") == 1 and vise(c.get("labelSelector"))
               for c in spec.get("topologySpreadConstraints") or [])


def test_galerie_repartie_sur_des_noeuds_differents(host):
    dep = _deployment(host, "galerie")
    regle = _regle_de_repartition(dep)
    places = _noeuds(_pods_de(host, "galerie"))
    reparti = len(places) >= 2 and len(set(places)) == len(places)
    assert regle and reparti, message(
        en=f"The replicas of galerie run on {places or 'no node'}, and its description "
        f"{'forbids' if regle else 'does not forbid'} two of them on one node. Expected at least two replicas on "
        "distinct nodes, guaranteed by a required anti-affinity or a spread constraint that refuses to place.",
        fr=f"Les réplicas de galerie tournent sur {places or 'aucun nœud'}, et sa description "
        f"{'garantit' if regle else 'ne garantit pas'} qu'aucun nœud n'en porte deux. Attendu au moins deux "
        "réplicas sur des nœuds distincts, garantis par une anti-affinité obligatoire ou une contrainte de "
        "répartition qui refuse de placer.",
    )


# ----------------------------------------------------------------------
# 5. Le namespace refuse un Pod qui dépasse le ResourceQuota (dry-run serveur).
# ----------------------------------------------------------------------
def _essai(host, nom: str, ressources: dict | None):
    """Crée un Pod en dry-run côté serveur : l'admission joue, rien n'est créé."""
    conteneur = {"name": "essai", "image": BUSYBOX, "command": ["sleep", "1"]}
    if ressources:
        conteneur["resources"] = ressources
    pod = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": nom, "namespace": NS},
           "spec": {"containers": [conteneur]}}
    return host.run(f"echo '{json.dumps(pod)}' | {ADMIN} create --dry-run=server -f - -o json")


def test_le_namespace_refuse_un_pod_au_dela_du_quota(host):
    effectif: dict[str, float] = {}
    for q in (_json(host, NS, "get resourcequotas") or {}).get("items") or []:
        for brute, valeur in ((q.get("spec") or {}).get("hard") or {}).items():
            cle = "pods" if brute == "count/pods" else brute
            v = _quantite(valeur)
            if v is not None:
                effectif[cle] = min(effectif.get(cle, v), v)
    ecarts = {cle: effectif.get(cle) for cle, attendu in PLAFOND.items()
              if effectif.get(cle) is None or abs(effectif[cle] - _quantite(attendu)) > 1e-6}
    assert not ecarts, message(
        en=f"The ResourceQuota of {NS} does not match: {ecarts or 'no ResourceQuota'}, expected {PLAFOND}.",
        fr=f"Le ResourceQuota de {NS} ne correspond pas : {ecarts or 'aucun ResourceQuota'}, attendu {PLAFOND}.",
    )
    trop = _essai(host, "essai-quota", {"requests": {"cpu": "3", "memory": "64Mi"},
                                        "limits": {"cpu": "3", "memory": "64Mi"}})
    assert trop.rc != 0 and "exceeded quota" in trop.stderr.lower(), message(
        en=f"A Pod requesting 3 CPU is not refused by the quota of {NS} in a server-side dry run "
        f"({trop.stderr.strip()[:160] or 'accepted'}).",
        fr=f"Un Pod qui demande 3 CPU n'est pas refusé par le quota de {NS} en dry-run côté serveur "
        f"({trop.stderr.strip()[:160] or 'accepté'}).",
    )


# ----------------------------------------------------------------------
# 6. Un Pod sans requests est accepté et complété par le LimitRange.
# ----------------------------------------------------------------------
def test_un_pod_sans_requests_recoit_les_valeurs_par_defaut(host):
    res = _essai(host, "essai-defauts", None)
    assert res.rc == 0, message(
        en=f"A Pod without requests is refused in {NS}: {res.stderr.strip()[:200]}. Under a quota on requests "
        "and limits, a container that declares none needs defaults to be accepted.",
        fr=f"Un Pod sans requests est refusé dans {NS} : {res.stderr.strip()[:200]}. Sous un quota qui porte sur "
        "les requests et les limits, un conteneur qui n'en déclare pas a besoin de valeurs par défaut.",
    )
    recues = json.loads(res.stdout)["spec"]["containers"][0].get("resources") or {}
    ecarts = {f"{genre}.{r}": (recues.get(genre) or {}).get(r)
              for genre, valeurs in DEFAUTS.items() for r, attendu in valeurs.items()
              if _quantite((recues.get(genre) or {}).get(r)) != _quantite(attendu)}
    assert not ecarts, message(
        en=f"A container that declares nothing receives {recues or 'nothing'}; expected {DEFAUTS}.",
        fr=f"Un conteneur qui ne déclare rien reçoit {recues or 'rien'} ; attendu {DEFAUTS}.",
    )


# ----------------------------------------------------------------------
# 7. Le HPA d'accueil, bornes demandées, lit une valeur de métrique.
# ----------------------------------------------------------------------
def _hpas_d_accueil(host) -> list[dict]:
    tous = (_json(host, NS, "get hpa") or {}).get("items") or []
    return [h for h in tous if ((h["spec"].get("scaleTargetRef") or {}).get("kind"),
                                (h["spec"].get("scaleTargetRef") or {}).get("name")) == ("Deployment", "accueil")]


def _lit_une_metrique(hpa: dict) -> bool:
    return any((m.get("resource") or {}).get("name") == "cpu"
               and ((m["resource"].get("current") or {}).get("averageUtilization") is not None)
               for m in (hpa.get("status") or {}).get("currentMetrics") or [])


def _hpa_declare(host) -> dict:
    siens = _hpas_d_accueil(host)
    assert len(siens) == 1, message(
        en=f"Expected exactly one HPA on the Deployment accueil, found {len(siens)}.",
        fr=f"Attendu exactement un HPA sur le Deployment accueil, trouvé {len(siens)}.",
    )
    hpa = siens[0]
    cpu = [m for m in hpa["spec"].get("metrics") or []
           if m.get("type") == "Resource" and (m.get("resource") or {}).get("name") == "cpu"]
    cible = (cpu[0]["resource"].get("target") or {}) if cpu else {}
    bornes = (hpa["spec"].get("minReplicas", 1), hpa["spec"].get("maxReplicas"))
    assert bornes == BORNES and cible.get("type") == "Utilization" \
        and cible.get("averageUtilization") == CIBLE_CPU, message(
        en=f"The HPA of accueil goes from {bornes[0]} to {bornes[1]} replicas on {cible or 'no CPU target'}; "
        f"expected {BORNES[0]} to {BORNES[1]}, at {CIBLE_CPU} % average CPU utilization.",
        fr=f"Le HPA d'accueil va de {bornes[0]} à {bornes[1]} réplicas sur {cible or 'aucune cible CPU'} ; "
        f"attendu {BORNES[0]} à {BORNES[1]}, à {CIBLE_CPU} % d'utilisation CPU moyenne.",
    )
    return hpa


def test_le_hpa_d_accueil_lit_une_metrique(host):
    hpa = _hpa_declare(host)
    fin = time.monotonic() + ATTENTE_METRIQUE
    while not _lit_une_metrique(hpa) and time.monotonic() < fin:
        time.sleep(PAS)
        hpa = (_hpas_d_accueil(host) or [hpa])[0]
    conditions = {c["type"]: c.get("message", "") for c in (hpa.get("status") or {}).get("conditions") or []}
    assert _lit_une_metrique(hpa), message(
        en=f"The HPA of accueil reads no CPU value: its target shows <unknown>. Conditions: {conditions}. "
        "The Pods need CPU requests, and a Pod created before they were set does not have them.",
        fr=f"Le HPA d'accueil ne lit aucune valeur CPU : sa cible affiche <unknown>. Conditions : {conditions}. "
        "Il faut des requests CPU aux Pods, et un Pod créé avant qu'elles soient posées ne les a pas.",
    )


# ----------------------------------------------------------------------
# 8. Sous la charge que génère le test, les réplicas dépassent le minimum.
# ----------------------------------------------------------------------
def test_sous_charge_les_replicas_depassent_le_minimum(host):
    hpa = _hpa_declare(host)
    assert _lit_une_metrique(hpa), message(
        en="The HPA of accueil reads no metric yet: no load can make it act.",
        fr="Le HPA d'accueil ne lit encore aucune métrique : aucune charge ne peut le faire agir.",
    )
    pods = [p["metadata"]["name"] for p in _pods_de(host, "accueil")]
    assert pods, message(
        en="No running Pod of accueil to put under load.",
        fr="Aucun Pod d'accueil en marche à mettre sous charge.",
    )
    # La charge : une boucle de calcul dans chaque Pod, bornée dans le temps,
    # lancée en arrière-plan sur le nœud pour que le test puisse regarder.
    for pod in pods:
        host.run(f"nohup {ADMIN} -n {NS} exec {pod} -- timeout {DUREE_CHARGE} sh -c 'while :; do :; done' "
                 "</dev/null >/dev/null 2>&1 &")
    minimum = BORNES[0]
    fin = time.monotonic() + ATTENTE_MONTEE
    replicas, voulus = 0, 0
    while time.monotonic() < fin:
        time.sleep(PAS)
        replicas = (_json(host, NS, "get deployment accueil") or {}).get("spec", {}).get("replicas") or 0
        voulus = ((_hpas_d_accueil(host) or [{}])[0].get("status") or {}).get("desiredReplicas") or 0
        if replicas > minimum:
            break
    assert replicas > minimum, message(
        en=f"After {ATTENTE_MONTEE}s under a CPU load in every Pod of accueil, the Deployment asks for {replicas} "
        f"replica(s) (HPA recommendation: {voulus}); expected more than the minimum of {minimum}. A quota too "
        "tight or a limit too low can also keep it from growing.",
        fr=f"Après {ATTENTE_MONTEE} s d'une charge CPU dans chaque Pod d'accueil, le Deployment demande {replicas} "
        f"réplica(s) (recommandation du HPA : {voulus}) ; attendu plus que le minimum de {minimum}. Un quota trop "
        "serré ou une limite trop basse peuvent aussi l'empêcher de grossir.",
    )
