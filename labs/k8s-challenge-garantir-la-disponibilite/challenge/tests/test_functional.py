"""test_functional.py : k8s-challenge-garantir-la-disponibilite

Le challenge du module « Fiabiliser et exploiter » du niveau 4. Ces tests lisent
l'état du CLUSTER et le rapport ~/routine/rapport.txt, jamais les commandes
tapées. Un test vérifie un seul état, dans l'ordre de la fiche.

Le cluster kubeadm du catalogue a deux nœuds ordonnançables : le socle retire
le taint du control plane (décision de l'issue #2). Trois exemplaires ne
peuvent donc pas tenir sur trois nœuds distincts : le test de répartition lit
les nœuds réellement ordonnançables et exige que les exemplaires en occupent
autant que possible, min(exemplaires, nœuds). Une règle impérative (anti-
affinité requise, DoNotSchedule) n'est pas refusée en soi, mais elle peut
laisser un exemplaire en attente ou bloquer l'évacuation : les tests 1 et 5 le
voient alors.

Deux tests agissent sur le cluster, et le disent dans le scénario. Le test 4
évince un exemplaire et regarde si son remplaçant reçoit du trafic avant d'être
prêt. Le test 5 lance lui-même l'évacuation de k8s-w1.lab, mesure pendant ce
temps les exemplaires disponibles, puis remet le nœud en service dans un
finally et rééquilibre l'application, pour qu'un second check parte du même
état. L'évacuation ne vise que les Pods de l'application (--pod-selector) : le
cluster est partagé avec les autres labs, et le budget de l'application est la
seule chose mesurée.

Les six tests échouent sur l'état que pose le setup : un seul exemplaire, sans
budget, sans règle de répartition, sans sonde, et ~/routine vide.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime

import pytest

from conftest import lab_host, lab_target_host, message

NS = "paiement"
APP = "paiement"
WORKER = "k8s-w1.lab"
MINIMUM = 2
HOTE = "kubernetes.io/hostname"
ADMIN = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
KUBECTL = f"sudo {ADMIN} --request-timeout=15s"
TRACES = "/var/lib/dsoxlab"
JOURNAL = f"{TRACES}/evacuation.log"
CODE = f"{TRACES}/evacuation.rc"
DELAI_EVACUATION = 120
PAS = 3
#: Les raisons d'attente qui disent qu'un conteneur est en erreur, et non qu'il
#: démarre.
RAISONS_D_ERREUR = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError",
                    "CreateContainerError", "InvalidImageName", "RunContainerError"}
#: Les certificats que kubeadm gère sur le control plane : la date de l'un
#: d'eux, au moins, doit figurer au rapport.
CERTIFICATS = ("apiserver.crt", "apiserver-kubelet-client.crt", "apiserver-etcd-client.crt",
               "front-proxy-client.crt", "etcd/server.crt", "etcd/peer.crt", "etcd/healthcheck-client.crt")
#: Les mois tels qu'openssl les écrit, toujours en anglais : lus sans dépendre
#: de la locale de la machine qui joue le check.
MOIS_OPENSSL = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MOIS = {1: ("jan", "janv"), 2: ("feb", "fev", "fév"), 3: ("mar", "mars"), 4: ("apr", "avr"), 5: ("may", "mai"),
        6: ("jun", "juin"), 7: ("jul", "juil"), 8: ("aug", "aou", "aoû"), 9: ("sep",), 10: ("oct",),
        11: ("nov",), 12: ("dec", "déc")}


@pytest.fixture(scope="module")
def cp():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _correspond(selecteur: dict | None, etiquettes: dict) -> bool:
    """Un LabelSelector de Kubernetes appliqué à des étiquettes. Un sélecteur
    vide ou absent ne cible rien de précis : il ne compte pas."""
    if not selecteur or not (selecteur.get("matchLabels") or selecteur.get("matchExpressions")):
        return False
    if any(etiquettes.get(k) != v for k, v in (selecteur.get("matchLabels") or {}).items()):
        return False
    for expr in selecteur.get("matchExpressions") or []:
        cle, op, valeurs = expr.get("key"), expr.get("operator"), expr.get("values") or []
        if op == "In" and etiquettes.get(cle) not in valeurs:
            return False
        if op == "NotIn" and etiquettes.get(cle) in valeurs:
            return False
        if op == "Exists" and cle not in etiquettes:
            return False
        if op == "DoesNotExist" and cle in etiquettes:
            return False
    return True


def _deployment(cp) -> dict:
    dep = _json(cp, f"-n {NS} get deployment {APP}")
    assert dep is not None, message(
        en=f"The Deployment {APP} cannot be found in {NS}: it is the application to make available, it stays.",
        fr=f"Le Deployment {APP} est introuvable dans {NS} : c'est l'application à rendre disponible, il reste.",
    )
    return dep


def _etiquettes(dep: dict) -> dict:
    return dep["spec"]["template"]["metadata"].get("labels") or {}


def _selecteur(dep: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in (dep["spec"]["selector"].get("matchLabels") or {}).items())


def _pret(pod: dict) -> bool:
    conditions = {c["type"]: c.get("status") for c in pod["status"].get("conditions") or []}
    return pod["status"].get("phase") == "Running" and conditions.get("Ready") == "True"


def _pods(cp, dep: dict) -> list[dict]:
    """Les Pods vivants du Deployment : créés par l'un de ses ReplicaSets, hors
    ceux en cours de suppression. Un Pod évincé ne compte plus comme disponible
    dès qu'il est marqué pour suppression : c'est aussi ce que fait le budget."""
    items = (_json(cp, f"-n {NS} get pods -l {_selecteur(dep)}") or {}).get("items") or []
    return [p for p in items if not p["metadata"].get("deletionTimestamp")
            and any(o.get("kind") == "ReplicaSet" and o.get("name", "").startswith(f"{APP}-")
                    for o in p["metadata"].get("ownerReferences") or [])]


def _prets(cp, dep: dict) -> list[dict]:
    return [p for p in _pods(cp, dep) if _pret(p)]


def _noeuds_ordonnancables(cp) -> list[str]:
    noeuds = []
    for n in (_json(cp, "get nodes") or {}).get("items") or []:
        conditions = {c["type"]: c.get("status") for c in n["status"].get("conditions") or []}
        bloquant = [t for t in n["spec"].get("taints") or [] if t.get("effect") in ("NoSchedule", "NoExecute")]
        if conditions.get("Ready") == "True" and not n["spec"].get("unschedulable") and not bloquant:
            noeuds.append(n["metadata"]["name"])
    return noeuds


def _evincer(cp, nom: str) -> bool:
    """Évince un Pod par l'API d'éviction, qui respecte le budget de
    perturbation : refusée (429) tant que le minimum serait rompu, on réessaie."""
    corps = json.dumps({"apiVersion": "policy/v1", "kind": "Eviction",
                        "metadata": {"name": nom, "namespace": NS}})
    for _ in range(12):
        res = cp.run(f"echo '{corps}' | {KUBECTL} create --raw /api/v1/namespaces/{NS}/pods/{nom}/eviction -f -")
        if res.rc == 0:
            return True
        time.sleep(PAS)
    return False


# ----------------------------------------------------------------------
# 1. Au moins trois exemplaires disponibles.
# ----------------------------------------------------------------------
def test_au_moins_trois_exemplaires_disponibles(cp):
    dep = _deployment(cp)
    voulus = dep["spec"].get("replicas", 1)
    # On n'attend que si le travail est déclaré : l'état du setup se note vite.
    fin = time.monotonic() + 60
    while voulus >= 3 and (dep.get("status") or {}).get("availableReplicas", 0) < 3 and time.monotonic() < fin:
        time.sleep(PAS)
        dep = _deployment(cp)
    disponibles = (dep.get("status") or {}).get("availableReplicas", 0)
    assert voulus >= 3 and disponibles >= 3, message(
        en=f"{APP} asks for {voulus} copy(ies) and has {disponibles} available: at least three are expected, "
        "available. A copy that stays pending because of too strict a placement rule does not count.",
        fr=f"{APP} demande {voulus} exemplaire(s) et en a {disponibles} disponible(s) : au moins trois sont "
        "attendus, disponibles. Un exemplaire qui reste en attente à cause d'une règle de placement trop "
        "stricte ne compte pas.",
    )


# ----------------------------------------------------------------------
# 2. Un budget de perturbation cible l'application et garantit le minimum.
# ----------------------------------------------------------------------
def test_un_budget_garantit_le_minimum(cp):
    etiquettes = _etiquettes(_deployment(cp))
    budgets = [b for b in (_json(cp, f"-n {NS} get poddisruptionbudgets") or {}).get("items") or []
               if _correspond(b["spec"].get("selector"), etiquettes)]
    assert budgets, message(
        en=f"No disruption budget in {NS} targets the Pods of {APP}: nothing tells the cluster that a "
        "voluntary eviction must leave enough copies running.",
        fr=f"Aucun budget de perturbation de {NS} ne cible les Pods de {APP} : rien ne dit au cluster qu'une "
        "éviction volontaire doit laisser assez d'exemplaires en marche.",
    )
    assert len(budgets) == 1, message(
        en=f"{len(budgets)} disruption budgets target the Pods of {APP}: "
        f"{[b['metadata']['name'] for b in budgets]}. The eviction API refuses to decide between them, and "
        "every eviction then fails: keep one.",
        fr=f"{len(budgets)} budgets de perturbation ciblent les Pods de {APP} : "
        f"{[b['metadata']['name'] for b in budgets]}. L'API d'éviction refuse de choisir entre eux, et toute "
        "éviction échoue alors : n'en gardez qu'un.",
    )
    nom = budgets[0]["metadata"]["name"]
    budget = budgets[0]
    # Le contrôleur calcule le statut du budget en quelques secondes.
    for _ in range(8):
        statut = budget.get("status") or {}
        if statut.get("observedGeneration", 0) >= budget["metadata"].get("generation", 1):
            break
        time.sleep(PAS)
        budget = _json(cp, f"-n {NS} get poddisruptionbudget {nom}") or budget
    statut = budget.get("status") or {}
    voulus, attendus = statut.get("desiredHealthy", 0), statut.get("expectedPods", 0)
    assert voulus >= MINIMUM, message(
        en=f"The budget {nom} only guarantees {voulus} healthy Pod(s), for {attendus} expected: the "
        f"requirement is at least {MINIMUM} available at all times.",
        fr=f"Le budget {nom} ne garantit que {voulus} Pod(s) sain(s), pour {attendus} attendus : l'exigence "
        f"est d'au moins {MINIMUM} disponibles en toute circonstance.",
    )
    assert attendus > voulus, message(
        en=f"The budget {nom} demands {voulus} healthy Pod(s) out of {attendus}: it allows no eviction at "
        "all, and no node hosting the application can be emptied any more. A budget protects a "
        "maintenance, it does not forbid it.",
        fr=f"Le budget {nom} exige {voulus} Pod(s) sain(s) sur {attendus} : il n'autorise aucune éviction, et "
        "plus aucun nœud qui porte l'application ne peut être vidé. Un budget protège une maintenance, il "
        "ne l'interdit pas.",
    )


# ----------------------------------------------------------------------
# 3. Les exemplaires sont répartis sur des nœuds différents.
# ----------------------------------------------------------------------
def _repartition_declaree(dep: dict) -> bool:
    spec = dep["spec"]["template"]["spec"]
    etiquettes = _etiquettes(dep)
    for c in spec.get("topologySpreadConstraints") or []:
        if c.get("topologyKey") == HOTE and _correspond(c.get("labelSelector"), etiquettes):
            return True
    anti = (spec.get("affinity") or {}).get("podAntiAffinity") or {}
    termes = list(anti.get("requiredDuringSchedulingIgnoredDuringExecution") or [])
    termes += [t.get("podAffinityTerm") or {} for t in anti.get("preferredDuringSchedulingIgnoredDuringExecution") or []]
    return any(t.get("topologyKey") == HOTE and _correspond(t.get("labelSelector"), etiquettes) for t in termes)


def test_les_exemplaires_sont_repartis_sur_des_noeuds_differents(cp):
    dep = _deployment(cp)
    assert _repartition_declaree(dep), message(
        en=f"Nothing in the description of {APP} asks to spread its copies across nodes (topology spread "
        f"or anti-affinity on {HOTE}, aimed at its own Pods). A spread obtained by chance is lost at the "
        "next rescheduling.",
        fr=f"Rien dans la description de {APP} ne demande de répartir ses exemplaires sur les nœuds "
        f"(contrainte de répartition ou anti-affinité sur {HOTE}, visant ses propres Pods). Une répartition "
        "obtenue par hasard se perd au prochain réordonnancement.",
    )
    prets = _prets(cp, dep)
    noeuds = _noeuds_ordonnancables(cp)
    occupes = sorted({p["spec"].get("nodeName") for p in prets})
    attendus = min(len(prets), len(noeuds))
    assert len(prets) >= 2 and len(occupes) >= attendus, message(
        en=f"The {len(prets)} ready copy(ies) of {APP} occupy {occupes}, while {len(noeuds)} node(s) can "
        f"host them ({noeuds}): {attendus} different nodes are expected. Copies on one node fall together "
        "with it.",
        fr=f"Les {len(prets)} exemplaire(s) prêt(s) de {APP} occupent {occupes}, alors que {len(noeuds)} "
        f"nœud(s) peuvent les accueillir ({noeuds}) : {attendus} nœuds différents sont attendus. Des "
        "exemplaires sur un même nœud tombent ensemble avec lui.",
    )


# ----------------------------------------------------------------------
# 4. Les sondes sont déclarées, et le trafic n'arrive qu'une fois prêt.
# ----------------------------------------------------------------------
def _ips_servies(cp) -> list[str]:
    """Les adresses que le Service paiement sert, telles que ses EndpointSlices
    les marquent prêtes."""
    tranches = (_json(cp, f"-n {NS} get endpointslices -l kubernetes.io/service-name={APP}") or {}).get("items") or []
    return [adresse for t in tranches for e in t.get("endpoints") or []
            if (e.get("conditions") or {}).get("ready") for adresse in e.get("addresses") or []]


def _code_http(cp, ip: str) -> str:
    return cp.run(f"curl -s -o /dev/null -m 3 -w '%{{http_code}}' http://{ip}/").stdout.strip()


def test_les_sondes_sont_declarees_et_le_trafic_attend_d_etre_pret(cp):
    dep = _deployment(cp)
    conteneurs = dep["spec"]["template"]["spec"]["containers"]
    conteneur = next((c for c in conteneurs if c["name"] == APP), conteneurs[0])
    manque = [nom for nom in ("readinessProbe", "livenessProbe") if not conteneur.get(nom)]
    assert not manque, message(
        en=f"The container {conteneur['name']} declares no {', '.join(manque)}: without them, Kubernetes "
        "sends traffic to a copy that is still warming up and never restarts a frozen one.",
        fr=f"Le conteneur {conteneur['name']} ne déclare pas de {', '.join(manque)} : sans elles, Kubernetes "
        "envoie du trafic à un exemplaire encore en mise en route et ne redémarre jamais un exemplaire figé.",
    )
    prets = _prets(cp, dep)
    assert prets, message(
        en=f"No copy of {APP} is ready: a readiness probe aimed at a page that never answers keeps every "
        "copy out of traffic.",
        fr=f"Aucun exemplaire de {APP} n'est prêt : une sonde de disponibilité visant une page qui ne répond "
        "jamais garde tous les exemplaires hors du trafic.",
    )
    redemarres = {p["metadata"]["name"]: s.get("restartCount") for p in _pods(cp, dep)
                  for s in p["status"].get("containerStatuses") or [] if s.get("restartCount", 0) > 0}
    assert not redemarres, message(
        en=f"Copies of {APP} have been restarted: {redemarres}. A liveness probe that fails during the "
        "warm-up kills a healthy application: it checks that the process lives, not that it is ready.",
        fr=f"Des exemplaires de {APP} ont été redémarrés : {redemarres}. Une sonde de vivacité qui échoue "
        "pendant la mise en route tue une application saine : elle vérifie que le processus vit, pas qu'il "
        "est prêt.",
    )
    # La preuve par le comportement : un exemplaire évincé est remplacé, et
    # tant que le remplaçant se met en route, aucune adresse servie par le
    # Service ne doit répondre autre chose que la page.
    anciens = {p["metadata"]["name"] for p in _pods(cp, dep)}
    assert _evincer(cp, prets[0]["metadata"]["name"]), message(
        en=f"The test could not evict a copy of {APP} to watch its replacement start: the eviction API "
        "refused for more than 30 s.",
        fr=f"Le test n'a pas pu évincer un exemplaire de {APP} pour regarder son remplaçant démarrer : l'API "
        "d'éviction a refusé pendant plus de 30 s.",
    )
    fautes: dict[str, str] = {}
    remplacant_vu = False
    fin = time.monotonic() + 75
    while time.monotonic() < fin and not fautes and not remplacant_vu:
        servies = _ips_servies(cp)
        for ip in servies:
            code = _code_http(cp, ip)
            if code != "200":
                fautes[ip] = code
        remplacant_vu = any(p["metadata"]["name"] not in anciens and p["status"].get("podIP") in servies
                            for p in _prets(cp, dep))
        time.sleep(1)
    assert not fautes, message(
        en=f"The Service sent traffic to addresses that do not serve the page yet: {fautes} (HTTP code). "
        "A copy that is still warming up was declared ready: the readiness probe must wait for what "
        "says the application is ready.",
        fr=f"Le Service a envoyé du trafic à des adresses qui ne servent pas encore la page : {fautes} (code "
        "HTTP). Un exemplaire encore en mise en route a été déclaré prêt : la sonde de disponibilité doit "
        "attendre ce qui dit que l'application est prête.",
    )
    assert remplacant_vu, message(
        en="The replacement of the evicted copy was not ready and served after 75 s: the readiness probe "
        "may aim at a page that never answers.",
        fr="Le remplaçant de l'exemplaire évincé n'était ni prêt ni servi au bout de 75 s : la sonde de "
        "disponibilité vise peut-être une page qui ne répond jamais.",
    )


# ----------------------------------------------------------------------
# 5. Pendant l'évacuation d'un nœud, le minimum tient.
# ----------------------------------------------------------------------
def _reequilibrer(cp, dep: dict) -> None:
    """Après l'évacuation, tous les exemplaires sont sur le même nœud : on en
    évince un ou deux pour que le scheduler les répartisse de nouveau. Au mieux,
    sans rien affirmer : c'est ce qui permet de rejouer le check."""
    fin = time.monotonic() + 70
    # Le taint posé par le cordon disparaît quelques secondes après l'uncordon :
    # avant, le scheduler renverrait l'exemplaire évincé sur le même nœud.
    while WORKER not in _noeuds_ordonnancables(cp) and time.monotonic() < fin - 50:
        time.sleep(PAS)
    for _ in range(2):
        if time.monotonic() > fin:
            return
        noeuds = _noeuds_ordonnancables(cp)
        prets = _prets(cp, dep)
        if len(noeuds) < 2 or len(prets) < 2:
            return
        charge = {n: [p for p in prets if p["spec"].get("nodeName") == n] for n in noeuds}
        plein = max(charge, key=lambda n: len(charge[n]))
        if len(charge[plein]) - min(len(v) for v in charge.values()) <= 1:
            return
        if not _evincer(cp, charge[plein][0]["metadata"]["name"]):
            return
        while len(_prets(cp, dep)) < len(prets) and time.monotonic() < fin:
            time.sleep(PAS)


def test_le_minimum_tient_pendant_l_evacuation_d_un_noeud(cp):
    dep = _deployment(cp)
    prets = _prets(cp, dep)
    assert len(prets) > MINIMUM, message(
        en=f"{len(prets)} ready copy(ies) of {APP}: with no more than {MINIMUM}, evacuating a node that hosts "
        "one means going below the minimum. The test does not start the evacuation.",
        fr=f"{len(prets)} exemplaire(s) prêt(s) de {APP} : avec {MINIMUM} au plus, évacuer un nœud qui en "
        "porte un, c'est passer sous le minimum. Le test ne lance pas l'évacuation.",
    )
    assert any(p["spec"].get("nodeName") == WORKER for p in prets), message(
        en=f"No copy of {APP} runs on {WORKER}, the node the test evacuates: the evacuation would prove "
        "nothing. The copies are not spread.",
        fr=f"Aucun exemplaire de {APP} ne tourne sur {WORKER}, le nœud que le test évacue : l'évacuation ne "
        "prouverait rien. Les exemplaires ne sont pas répartis.",
    )
    unite = f"dsoxlab-evacuation-{int(time.time())}"
    cp.run(f"sudo install -d -m 0700 {TRACES} && sudo rm -f {JOURNAL} {CODE}")
    commande = (f"{ADMIN} drain {WORKER} --pod-selector={_selecteur(dep)} --ignore-daemonsets "
                f"--delete-emptydir-data --timeout={DELAI_EVACUATION}s > {JOURNAL} 2>&1; echo $? > {CODE}")
    minimum_vu, echantillons, code = len(prets), 0, None
    try:
        lance = cp.run(f"sudo systemd-run --unit={unite} --collect --quiet sh -c '{commande}'")
        assert lance.rc == 0, message(
            en=f"The test could not start the evacuation of {WORKER}: {lance.stderr.strip()[:200]}",
            fr=f"Le test n'a pas pu lancer l'évacuation de {WORKER} : {lance.stderr.strip()[:200]}",
        )
        fin = time.monotonic() + DELAI_EVACUATION + 20
        while time.monotonic() < fin:
            minimum_vu = min(minimum_vu, len(_prets(cp, dep)))
            echantillons += 1
            lu = cp.run(f"cat {CODE}")
            if lu.rc == 0 and lu.stdout.strip():
                code = int(lu.stdout.strip())
                break
            time.sleep(1)
        minimum_vu = min(minimum_vu, len(_prets(cp, dep)))
    finally:
        cp.run(f"sudo systemctl stop {unite}.service")
        cp.run(f"{KUBECTL} uncordon {WORKER}")
        _reequilibrer(cp, dep)
    journal = cp.run(f"tail -n 4 {JOURNAL}").stdout.strip()[-300:]
    assert minimum_vu >= MINIMUM, message(
        en=f"During the evacuation of {WORKER}, {APP} went down to {minimum_vu} available copy(ies) "
        f"({echantillons} measures), below the minimum of {MINIMUM}. The evacuation goes through the "
        "eviction API: only a budget makes it wait for a replacement to be ready.",
        fr=f"Pendant l'évacuation de {WORKER}, {APP} est descendue à {minimum_vu} exemplaire(s) disponible(s) "
        f"({echantillons} mesures), sous le minimum de {MINIMUM}. L'évacuation passe par l'API d'éviction : "
        "seul un budget la fait attendre qu'un remplaçant soit prêt.",
    )
    assert code == 0, message(
        en=f"The evacuation of {WORKER} did not complete (code {code}): the minimum held, but the node could "
        f"not be emptied. A budget that allows nothing, or a placement rule that leaves the replacements "
        f"pending, blocks the maintenance. End of the drain log: {journal}",
        fr=f"L'évacuation de {WORKER} n'a pas abouti (code {code}) : le minimum a tenu, mais le nœud n'a pas "
        "pu être vidé. Un budget qui n'autorise rien, ou une règle de placement qui laisse les remplaçants "
        f"en attente, bloque la maintenance. Fin du journal du drain : {journal}",
    )


# ----------------------------------------------------------------------
# 6. Le rapport de routine dit l'état réel du cluster.
# ----------------------------------------------------------------------
def _epoch(horodatage: str) -> float:
    return datetime.fromisoformat(horodatage.replace("Z", "+00:00")).timestamp()


def _en_erreur(pod: dict, maintenant: float) -> bool:
    if pod["metadata"].get("deletionTimestamp"):
        return False
    statut = pod["status"]
    if statut.get("phase") == "Failed":
        return True
    for s in (statut.get("containerStatuses") or []) + (statut.get("initContainerStatuses") or []):
        if ((s.get("state") or {}).get("waiting") or {}).get("reason") in RAISONS_D_ERREUR:
            return True
    return statut.get("phase") == "Pending" and maintenant - _epoch(pod["metadata"]["creationTimestamp"]) > 120


def _noms_acceptes(pod: dict) -> set[str]:
    """Un Pod en erreur se signale par son nom, ou par celui de ce qui le gère :
    le nom d'un Pod de Deployment change à chaque recréation."""
    noms = {pod["metadata"]["name"]}
    for o in pod["metadata"].get("ownerReferences") or []:
        noms.add(o.get("name", ""))
        if o.get("kind") == "ReplicaSet":
            noms.add(o.get("name", "").rsplit("-", 1)[0])
    return {n.lower() for n in noms if n}


def _date_figure(texte: str, fin: date) -> bool:
    if fin.strftime("%Y-%m-%d") in texte or fin.strftime("%d/%m/%Y") in texte:
        return True
    for ligne in texte.lower().splitlines():
        if str(fin.year) in ligne and any(m in ligne for m in MOIS[fin.month]) \
                and re.search(rf"(?<!\d)0?{fin.day}(?!\d)", ligne):
            return True
    return False


def test_le_rapport_de_routine_dit_l_etat_reel_du_cluster(cp):
    chemin = f"{_maison(cp)}/routine/rapport.txt"
    fichier = cp.file(chemin)
    assert fichier.exists, message(
        en="~/routine/rapport.txt is missing: the routine leaves a written report, the one the next shift "
        "reads.",
        fr="~/routine/rapport.txt est absent : la routine laisse un rapport écrit, celui que lit l'équipe "
        "suivante.",
    )
    texte = fichier.content_string
    bas = texte.lower()
    manques_en, manques_fr = [], []

    noeuds = [n["metadata"]["name"] for n in (_json(cp, "get nodes") or {}).get("items") or []]
    absents = [n for n in noeuds if n.lower() not in bas]
    if absents:
        manques_en.append(f"the nodes {absents}")
        manques_fr.append(f"les nœuds {absents}")

    maintenant = float(cp.check_output("date +%s").strip())
    pods = (_json(cp, "get pods -A") or {}).get("items") or []
    en_erreur = [p for p in pods if _en_erreur(p, maintenant)]
    if not any(p["metadata"]["name"] == "facturation-batch" for p in en_erreur):
        manques_en.append("facturation-batch still in error: it belongs to another team, it is reported, "
                          "not touched")
        manques_fr.append("facturation-batch toujours en erreur : il appartient à une autre équipe, il se "
                          "signale, on n'y touche pas")
    oublies = [f"{p['metadata']['namespace']}/{p['metadata']['name']}" for p in en_erreur
               if not any(n in bas for n in _noms_acceptes(p))]
    if oublies:
        manques_en.append(f"the Pods in error {oublies}")
        manques_fr.append(f"les Pods en erreur {oublies}")

    termines = [j for j in (_json(cp, "get jobs -A") or {}).get("items") or []
                if any(c.get("type") in ("Complete", "Failed") and c.get("status") == "True"
                       for c in (j.get("status") or {}).get("conditions") or [])]
    if not any(j["metadata"]["name"] == "export-ancien" for j in termines):
        manques_en.append("the finished Job export-ancien: the report observes, the cleaning is decided apart")
        manques_fr.append("le Job terminé export-ancien : le rapport constate, le ménage se décide à part")
    orphelins = [f"{j['metadata']['namespace']}/{j['metadata']['name']}" for j in termines
                 if j["metadata"]["name"].lower() not in bas]
    if orphelins:
        manques_en.append(f"the finished Jobs still kept {orphelins}")
        manques_fr.append(f"les Jobs terminés qui restent {orphelins}")

    fins = []
    for cert in CERTIFICATS:
        res = cp.run(f"openssl x509 -enddate -noout -in /etc/kubernetes/pki/{cert}")
        if res.rc == 0 and "=" in res.stdout:
            # notAfter=Nov 14 10:12:00 2027 GMT
            mois, jour, _heure, annee = res.stdout.strip().split("=", 1)[1].split()[:4]
            fins.append(date(int(annee), MOIS_OPENSSL.index(mois) + 1, int(jour)))
    if fins and not any(_date_figure(texte, f) for f in fins):
        manques_en.append(f"the expiry date of the control plane certificates ({min(fins):%Y-%m-%d})")
        manques_fr.append(f"l'échéance des certificats du plan de contrôle ({min(fins):%Y-%m-%d})")

    assert not manques_en, message(
        en="~/routine/rapport.txt does not match the real state of the cluster; it lacks: "
        + "; ".join(manques_en) + ".",
        fr="~/routine/rapport.txt ne correspond pas à l'état réel du cluster ; il y manque : "
        + " ; ".join(manques_fr) + ".",
    )
