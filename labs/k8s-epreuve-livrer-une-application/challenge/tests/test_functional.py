"""test_functional.py : k8s-epreuve-livrer-une-application

L'épreuve du niveau 3 (fiche KUBERN-EPREUVE-N3). Le cahier des charges ne
nomme aucun type d'objet : ces tests retrouvent sur le cluster ce que
l'apprenant a choisi, et font de vraies requêtes. Un test vérifie un seul
critère de la grille, dans l'ordre de la fiche, C1 à C11.

Le setup laisse un état hérité où chaque critère est faux : rien n'est exposé,
caisse n'a aucun endpoint, programme n'a pas d'adresse, la base attend faute de
tolérer le nœud réservé, le plafond provisoire bloque affiches, le HPA ne lit
rien, programme tourne en root sous le compte par défaut.

Chaque test qui porte sur un flux vérifie aussi le flux qui doit être refusé :
sans politique, presque tout passe déjà, et un test qui ne regarderait que le
flux permis passerait avant le travail.

Aucun test n'attend tant que le travail n'est pas commencé : une attente ne
s'ouvre que si l'état demandé est déjà déclaré et converge encore. dsoxlab
coupe pytest au bout de 300 secondes.
"""

from __future__ import annotations

import json
import time
import unicodedata
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/capacite.kubeconfig"
NS = "festival"
PAIEMENT = "paiement"
PARTENAIRES = "partenaires"
HOTE = "festival.local"
PORT = 30080
RESERVE = "reserve"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
JETON = "/var/run/secrets/kubernetes.io/serviceaccount"
#: Le plafond demandé, et les valeurs par défaut demandées.
PLAFOND = {"requests.cpu": "2", "requests.memory": "2Gi", "limits.cpu": "4",
           "limits.memory": "4Gi", "pods": "15"}
DEFAUTS = {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "250m", "memory": "256Mi"}}
BORNES = (2, 6)
CIBLE_CPU = 60
#: Ce qui nomme la cause de la panne de caisse (le sélecteur, ses étiquettes),
#: et ce qui dit qu'il ne correspond pas aux Pods. Formes compactées : sans
#: accent, espace ni apostrophe.
NOMME_LA_CAUSE = ("selector", "selecteur", "label", "etiquette", "version")
DIT_L_ECART = ("v1", "v2", "correspond", "match", "endpoint", "aucunpod", "nopod", "vide", "empty",
               "differ", "absent", "manqu", "missing", "introuvable", "mauvais", "wrong", "incorrect",
               "nexiste", "notfound", "aucuneinstance", "aucunbackend")
ATTENTE = 60
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, ns: str | None, args: str) -> dict | None:
    portee = f"-n {ns} " if ns else ""
    res = host.run(f"{ADMIN} {portee}{args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _compact(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if c.isalnum())


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


def _vivants(pods: list[dict]) -> list[dict]:
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")
            and (p.get("status") or {}).get("phase") == "Running"]


def _pods_de(host, ns: str, deployment: str) -> list[dict]:
    """Les Pods en marche créés par le ReplicaSet d'un Deployment : un Pod nu
    posé à côté, avec la même étiquette, n'est pas l'application."""
    dep = _json(host, ns, f"get deployment {deployment}")
    if dep is None:
        return []
    etiquettes = (dep["spec"].get("selector") or {}).get("matchLabels") or {}
    selecteur = ",".join(f"{k}={v}" for k, v in sorted(etiquettes.items()))
    pods = (_json(host, ns, f"get pods -l {selecteur}") or {}).get("items") or []
    return _vivants([p for p in pods if any(
        o.get("kind") == "ReplicaSet" and o.get("name", "").startswith(f"{deployment}-")
        for o in p["metadata"].get("ownerReferences") or [])])


def _exec(host, ns: str, pod: str, commande: str):
    return host.run(f"{ADMIN} -n {ns} exec {pod} -- {commande}")


def _premier(host, ns: str, deployment: str) -> str | None:
    pods = _pods_de(host, ns, deployment)
    return pods[0]["metadata"]["name"] if pods else None


def _instant(horodatage: str) -> float:
    return datetime.fromisoformat(horodatage.replace("Z", "+00:00")).timestamp()


# ----------------------------------------------------------------------
# C1 (critique) : les deux applications joignables par l'hôte, chacune sur son
# chemin.
# ----------------------------------------------------------------------
def _adresse_d_un_noeud(host) -> str:
    noeud = _json(host, None, "get node capacite-control-plane") or {}
    return next((a["address"] for a in (noeud.get("status") or {}).get("addresses") or []
                 if a.get("type") == "InternalIP"), "")


def _demander(host, ip: str, chemin: str, hote: str = HOTE) -> str:
    """Le corps de la réponse, redirections suivies, vide si rien n'a répondu."""
    res = host.run(f"curl -sL --max-redirs 3 --max-time 8 --resolve {hote}:{PORT}:{ip} "
                   f"http://{hote}:{PORT}{chemin}")
    return res.stdout.strip()


def test_c1_les_deux_applications_joignables_par_hote_et_chemin(host):
    ip = _adresse_d_un_noeud(host)
    assert ip, message(
        en="Cannot read the address of the node capacite-control-plane.",
        fr="Impossible de lire l'adresse du nœud capacite-control-plane.",
    )

    def mesure() -> dict[str, str]:
        return {
            "/billets": _demander(host, ip, "/billets"),
            "/programme": _demander(host, ip, "/programme"),
            "/autre": _demander(host, ip, "/autre"),
            "autre hôte": _demander(host, ip, "/programme", hote="ailleurs.local"),
        }

    def juste(m: dict[str, str]) -> bool:
        return (m["/billets"] == "billets" and m["/programme"] == "programme"
                and m["/autre"] not in ("billets", "programme")
                and m["autre hôte"] not in ("billets", "programme"))

    m = mesure()
    une_route = bool(host.run(f"{ADMIN} -n {NS} get ingress,httproute -o name").stdout.strip())
    if not juste(m) and une_route:
        fin = time.monotonic() + ATTENTE
        while not juste(m) and time.monotonic() < fin:
            time.sleep(PAS)
            m = mesure()
    assert juste(m), message(
        en=f"Responses received from outside the cluster: {m}. Expected the ticket office on /billets and "
        f"the programme on /programme, for the host {HOTE} only, and neither application on an undeclared "
        "path or for another host.",
        fr=f"Réponses reçues de l'extérieur du cluster : {m}. Attendu la billetterie sur /billets et le "
        f"programme sur /programme, pour l'hôte {HOTE} seulement, et aucune des deux applications sur un "
        "chemin non déclaré ni pour un autre hôte.",
    )


# ----------------------------------------------------------------------
# C2 (critique) : caisse répond de nouveau, et sa cause a été consignée avant.
# ----------------------------------------------------------------------
def test_c2_caisse_repond_et_sa_cause_a_ete_consignee_avant(host):
    fichier = f"{_maison(host)}/epreuve/cause-caisse.txt"
    cause = host.file(fichier)
    assert cause.exists, message(
        en="~/epreuve/cause-caisse.txt is missing: the cause of the failure is recorded before the repair.",
        fr="~/epreuve/cause-caisse.txt est absent : la cause de la panne se consigne avant la réparation.",
    )
    lue = _compact(cause.content_string)
    nomme = any(m in lue for m in NOMME_LA_CAUSE)
    dit = any(m in lue for m in DIT_L_ECART)
    assert nomme and dit, message(
        en="cause-caisse.txt does not say what keeps caisse from answering: it names what the address uses "
        "to find its copies, and says how that differs from what the copies carry.",
        fr="cause-caisse.txt ne dit pas ce qui empêche caisse de répondre : il nomme ce par quoi l'adresse "
        "retrouve ses exemplaires, et dit en quoi cela diffère de ce que portent les exemplaires.",
    )
    corps = _exec(host, PARTENAIRES, "partenaire", f"wget -qO- -T 5 http://caisse.{PAIEMENT}/").stdout.strip()
    assert corps == "caisse", message(
        en=f"From a client of the cluster, http://caisse.{PAIEMENT} still does not answer caisse "
        f"(received {corps[:80]!r}).",
        fr=f"Depuis un client du cluster, http://caisse.{PAIEMENT} ne répond toujours pas caisse "
        f"(reçu {corps[:80]!r}).",
    )
    # L'instant de la réparation : la dernière écriture, hors statut, sur
    # l'adresse ou sur le composant caisse. Le fichier doit lui être antérieur.
    instants = [_instant(champ["time"])
                for genre in ("service", "deployment")
                for champ in ((_json(host, PAIEMENT, f"get {genre} caisse --show-managed-fields") or {}).get("metadata") or {})
                .get("managedFields") or []
                if champ.get("time") and not champ.get("subresource")]
    ecrit = host.run(f"stat -c %Y {fichier}")
    assert instants and ecrit.rc == 0 and int(ecrit.stdout.strip()) <= int(max(instants)), message(
        en="cause-caisse.txt was written or modified after the repair of caisse: the cause is recorded "
        "BEFORE the repair, then left untouched.",
        fr="cause-caisse.txt a été écrit ou modifié après la réparation de caisse : la cause se consigne "
        "AVANT la réparation, puis on n'y touche plus.",
    )


# ----------------------------------------------------------------------
# C3 : un client d'un autre namespace résout le nom complet de programme et le
# joint.
# ----------------------------------------------------------------------
def test_c3_un_client_d_un_autre_namespace_resout_et_joint_programme(host):
    nom = f"programme.{NS}.svc.cluster.local"
    resout = _exec(host, PARTENAIRES, "partenaire", f"nslookup {nom}").rc == 0
    corps = _exec(host, PARTENAIRES, "partenaire", f"wget -qO- -T 5 http://{nom}/").stdout.strip()
    assert resout and corps == "programme", message(
        en=f"From partenaire, in {PARTENAIRES}, the name {nom} {'resolves' if resout else 'does not resolve'}, "
        f"and HTTP on port 80 answers {corps[:80]!r}. Expected the name resolved and the programme's page.",
        fr=f"Depuis partenaire, dans {PARTENAIRES}, le nom {nom} {'se résout' if resout else 'ne se résout pas'}, "
        f"et HTTP sur le port 80 répond {corps[:80]!r}. Attendu le nom résolu et la page du programme.",
    )


# ----------------------------------------------------------------------
# C4 (critique) : seul le frontend joint la base.
# ----------------------------------------------------------------------
def test_c4_seul_le_frontend_joint_la_base(host):
    frontend = _premier(host, NS, "billets")
    application = _premier(host, NS, "programme")
    assert frontend and application, message(
        en="The ticket office and the programme must both be running to judge access to the database.",
        fr="La billetterie et le programme doivent tourner tous les deux pour juger l'accès à la base.",
    )
    depuis_frontend = _exec(host, NS, frontend, "nc -z -w 3 registre 5432").rc == 0
    depuis_application = _exec(host, NS, application, "nc -z -w 3 registre 5432").rc == 0
    depuis_partenaire = _exec(host, PARTENAIRES, "partenaire",
                              f"nc -z -w 3 registre.{NS}.svc.cluster.local 5432").rc == 0
    assert depuis_frontend and not depuis_application and not depuis_partenaire, message(
        en=f"On port 5432 of registre: the ticket office {'gets in' if depuis_frontend else 'is refused'}, "
        f"the programme {'gets in' if depuis_application else 'is refused'}, partenaire from {PARTENAIRES} "
        f"{'gets in' if depuis_partenaire else 'is refused'}. Expected the ticket office alone allowed.",
        fr=f"Sur le port 5432 de registre : la billetterie {'entre' if depuis_frontend else 'est refusée'}, "
        f"le programme {'entre' if depuis_application else 'est refusé'}, partenaire de {PARTENAIRES} "
        f"{'entre' if depuis_partenaire else 'est refusé'}. Attendu la billetterie seule autorisée.",
    )


# ----------------------------------------------------------------------
# C5 : la base résout toujours les noms, et ne sort vers rien d'autre.
# ----------------------------------------------------------------------
def test_c5_la_base_resout_les_noms_et_ne_sort_vers_rien_d_autre(host):
    base = _premier(host, NS, "registre")
    assert base, message(
        en="The database registre is not running: its outbound traffic cannot be judged.",
        fr="La base registre ne tourne pas : sa sortie ne peut pas être jugée.",
    )
    resout = _exec(host, NS, base, "nslookup kubernetes.default.svc.cluster.local").rc == 0
    # Le témoin d'une sortie qui devrait être refusée : un exemplaire de
    # programme, joint à son adresse de Pod. Il tourne dès l'arrivée, et il
    # répond à tout Pod que rien ne retient, adresse stable ou non.
    application = _pods_de(host, NS, "programme")
    assert application, message(
        en="programme is not running: the outbound traffic of the database has no witness to be judged on.",
        fr="programme ne tourne pas : la sortie de la base n'a aucun témoin sur lequel se juger.",
    )
    ip = application[0]["status"].get("podIP", "")
    sort = _exec(host, NS, base, f"wget -qO- -T 3 http://{ip}:8080/").stdout.strip() == "programme"
    assert resout and not sort, message(
        en=f"registre {'resolves' if resout else 'does not resolve'} names and "
        f"{'reaches' if sort else 'does not reach'} a copy of programme. Expected name resolution kept, "
        "and every other outbound flow refused.",
        fr=f"registre {'résout' if resout else 'ne résout pas'} les noms et "
        f"{'joint' if sort else 'ne joint pas'} un exemplaire de programme. Attendu la résolution gardée, et "
        "toute autre sortie refusée.",
    )


# ----------------------------------------------------------------------
# C6 : placement. La base sur le nœud réservé et seule du namespace à y
# tourner, le frontend réparti sur des nœuds différents.
# ----------------------------------------------------------------------
def _regle_de_repartition(dep: dict) -> bool:
    """Le Deployment interdit à deux exemplaires de partager un nœud : une
    anti-affinité obligatoire sur le nom d'hôte, ou une contrainte de
    répartition qui refuse de placer au-delà d'un écart de un."""
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


def test_c6_la_base_sur_le_noeud_reserve_et_le_frontend_reparti(host):
    noeuds = (_json(host, None, f"get nodes -l {RESERVE}=registre") or {}).get("items") or []
    assert len(noeuds) == 1, message(
        en=f"Expected exactly one node reserved for the database (label {RESERVE}=registre), found "
        f"{[n['metadata']['name'] for n in noeuds]}.",
        fr=f"Attendu exactement un nœud réservé à la base (label {RESERVE}=registre), trouvé "
        f"{[n['metadata']['name'] for n in noeuds]}.",
    )
    reserve = noeuds[0]["metadata"]["name"]
    base = _pods_de(host, NS, "registre")
    sur_le_reserve = bool(base) and all(p["spec"].get("nodeName") == reserve for p in base)
    tous = (_json(host, NS, "get pods") or {}).get("items") or []
    intrus = sorted(p["metadata"]["name"] for p in tous
                    if not p["metadata"].get("deletionTimestamp")
                    and p["spec"].get("nodeName") == reserve
                    and (p["metadata"].get("labels") or {}).get("app") != "registre")
    frontend = _pods_de(host, NS, "billets")
    places = sorted(p["spec"].get("nodeName") or "" for p in frontend)
    dep = _json(host, NS, "get deployment billets")
    garanti = dep is not None and _regle_de_repartition(dep)
    reparti = len(places) >= 2 and len(set(places)) == len(places) and reserve not in places
    assert sur_le_reserve and not intrus and reparti and garanti, message(
        en=f"Database running on the reserved node {reserve}: {'yes' if sur_le_reserve else 'no'}; other "
        f"Pods of {NS} on that node: {intrus or 'none'}; ticket office copies on the nodes {places}, "
        f"{'guaranteed' if garanti else 'not guaranteed'} never to share one. Expected the database alone on "
        "its node, and at least two copies of the ticket office on distinct nodes, which their description "
        "forbids to share a node.",
        fr=f"Base en marche sur le nœud réservé {reserve} : {'oui' if sur_le_reserve else 'non'} ; autres Pods "
        f"de {NS} sur ce nœud : {intrus or 'aucun'} ; exemplaires de la billetterie sur les nœuds {places}, "
        f"{'garantis' if garanti else 'non garantis'} de ne jamais en partager un. Attendu la base seule sur "
        "son nœud, et au moins deux exemplaires de la billetterie sur des nœuds distincts, que leur "
        "description interdit de partager un nœud.",
    )


# ----------------------------------------------------------------------
# C7 (critique) : le namespace refuse une charge qui dépasse son plafond.
# ----------------------------------------------------------------------
def _essai(host, nom: str, ressources: dict | None):
    """Crée un Pod en dry-run côté serveur : l'admission joue, rien n'est créé."""
    conteneur = {"name": "essai", "image": BUSYBOX, "command": ["sleep", "1"]}
    if ressources:
        conteneur["resources"] = ressources
    pod = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": nom, "namespace": NS},
           "spec": {"containers": [conteneur]}}
    return host.run(f"echo '{json.dumps(pod)}' | {ADMIN} create --dry-run=server -f - -o json")


def test_c7_le_namespace_refuse_une_charge_qui_depasse_son_plafond(host):
    quotas = (_json(host, NS, "get resourcequotas") or {}).get("items") or []
    effectif: dict[str, float] = {}
    for q in quotas:
        for brute, valeur in ((q.get("spec") or {}).get("hard") or {}).items():
            cle = "pods" if brute == "count/pods" else brute
            v = _quantite(valeur)
            if v is not None:
                effectif[cle] = min(effectif.get(cle, v), v)
    ecarts = {cle: effectif.get(cle) for cle, attendu in PLAFOND.items()
              if effectif.get(cle) is None or abs(effectif[cle] - _quantite(attendu)) > 1e-6}
    assert not ecarts, message(
        en=f"The ceiling of {NS} does not match the requirements: {ecarts or 'no ceiling'}, expected {PLAFOND}.",
        fr=f"Le plafond de {NS} ne correspond pas au cahier des charges : {ecarts or 'aucun plafond'}, "
        f"attendu {PLAFOND}.",
    )
    trop = _essai(host, "essai-plafond", {"requests": {"cpu": "2100m", "memory": "64Mi"},
                                          "limits": {"cpu": "2100m", "memory": "64Mi"}})
    assert trop.rc != 0 and "forbidden" in trop.stderr.lower(), message(
        en=f"A workload reserving 2.1 CPU is accepted in {NS}, beyond its ceiling of 2 CPU.",
        fr=f"Une charge qui réserve 2,1 CPU est acceptée dans {NS}, au-delà de son plafond de 2 CPU.",
    )


# ----------------------------------------------------------------------
# C8 : une charge sans ressources reçoit les valeurs par défaut, et affiches
# tourne.
# ----------------------------------------------------------------------
def test_c8_valeurs_par_defaut_et_affiches_tourne(host):
    res = _essai(host, "essai-defauts", None)
    assert res.rc == 0, message(
        en=f"A workload that declares no resources is refused in {NS}: {res.stderr.strip()[:200]}",
        fr=f"Une charge qui ne déclare pas ses ressources est refusée dans {NS} : {res.stderr.strip()[:200]}",
    )
    recues = json.loads(res.stdout)["spec"]["containers"][0].get("resources") or {}
    ecarts = {f"{genre}.{r}": (recues.get(genre) or {}).get(r)
              for genre, valeurs in DEFAUTS.items() for r, attendu in valeurs.items()
              if _quantite((recues.get(genre) or {}).get(r)) != _quantite(attendu)}
    assert not ecarts, message(
        en=f"A container that declares nothing receives {recues}; expected {DEFAUTS}.",
        fr=f"Un conteneur qui ne déclare rien reçoit {recues} ; attendu {DEFAUTS}.",
    )
    pods = _pods_de(host, NS, "affiches")
    if not pods:
        fin = time.monotonic() + ATTENTE
        while not pods and time.monotonic() < fin:
            time.sleep(PAS)
            pods = _pods_de(host, NS, "affiches")
    assert pods, message(
        en="The affiches workload still does not run. Its copies were refused by the ceiling: a refusal is "
        "retried less and less often, the workload may need to be relaunched.",
        fr="La charge affiches ne tourne toujours pas. Ses exemplaires étaient refusés par le plafond : un "
        "refus se retente de plus en plus rarement, la charge peut demander à être relancée.",
    )


# ----------------------------------------------------------------------
# C9 : la mise à l'échelle de programme, bornes demandées, lit une métrique.
# ----------------------------------------------------------------------
def _lit_une_metrique(hpa: dict) -> bool:
    return any((m.get("resource") or {}).get("name") == "cpu"
               and ((m["resource"].get("current") or {}).get("averageUtilization") is not None)
               for m in (hpa.get("status") or {}).get("currentMetrics") or [])


def test_c9_la_mise_a_l_echelle_lit_une_metrique(host):
    def lire() -> list[dict]:
        tous = (_json(host, NS, "get hpa") or {}).get("items") or []
        return [h for h in tous if ((h["spec"].get("scaleTargetRef") or {}).get("kind"),
                                    (h["spec"].get("scaleTargetRef") or {}).get("name")) == ("Deployment", "programme")]

    siens = lire()
    assert len(siens) == 1, message(
        en=f"Expected exactly one scaling rule on programme, found {len(siens)}: two rules on the same "
        "target fight each other.",
        fr=f"Attendu exactement une règle de mise à l'échelle sur programme, trouvé {len(siens)} : deux "
        "règles sur la même cible se contredisent.",
    )
    hpa = siens[0]
    cpu = [m for m in hpa["spec"].get("metrics") or []
           if m.get("type") == "Resource" and (m.get("resource") or {}).get("name") == "cpu"]
    cible = (cpu[0]["resource"].get("target") or {}) if cpu else {}
    bornes = (hpa["spec"].get("minReplicas", 1), hpa["spec"].get("maxReplicas"))
    assert bornes == BORNES and cible.get("type") == "Utilization" \
        and cible.get("averageUtilization") == CIBLE_CPU, message(
        en=f"The scaling of programme goes from {bornes[0]} to {bornes[1]} copies on {cible or 'no CPU target'}; "
        f"expected {BORNES[0]} to {BORNES[1]}, aiming at {CIBLE_CPU} % of the CPU each copy reserves.",
        fr=f"La mise à l'échelle de programme va de {bornes[0]} à {bornes[1]} exemplaires sur "
        f"{cible or 'aucune cible CPU'} ; attendu {BORNES[0]} à {BORNES[1]}, en visant {CIBLE_CPU} % du CPU "
        "que réserve chaque exemplaire.",
    )
    # La déclaration est juste : on laisse aux mesures le temps d'arriver.
    fin = time.monotonic() + ATTENTE
    while not _lit_une_metrique(hpa) and time.monotonic() < fin:
        time.sleep(PAS * 2)
        hpa = (lire() or [hpa])[0]
    conditions = {c["type"]: c.get("message", "") for c in (hpa.get("status") or {}).get("conditions") or []}
    assert _lit_une_metrique(hpa), message(
        en=f"The scaling of programme reads no CPU value: its target shows <unknown>. Conditions: {conditions}.",
        fr=f"La mise à l'échelle de programme ne lit aucune valeur CPU : sa cible affiche <unknown>. "
        f"Conditions : {conditions}.",
    )


# ----------------------------------------------------------------------
# C10 (critique) : identité dédiée, sans jeton, et le seul droit demandé.
# ----------------------------------------------------------------------
_TEMOIN = "system:serviceaccount:dsoxlab-temoin-inexistant:sans-droit"
_BASES: dict[str, set] = {}


def _cle(regle: dict) -> tuple:
    return tuple(tuple(sorted(regle.get(champ) or [])) for champ in ("apiGroups", "resources", "resourceNames", "verbs"))


def _regles(host, sujet: str, ns: str) -> list[dict]:
    revue = ('{"apiVersion":"authorization.k8s.io/v1","kind":"SelfSubjectRulesReview",'
             f'"spec":{{"namespace":"{ns}"}}}}')
    res = host.run(f"echo '{revue}' | {ADMIN} create --validate=false --as {sujet} -f - -o json")
    assert res.rc == 0, message(
        en=f"Cannot compute the rights of {sujet} in {ns}: {res.stderr.strip()[:200]}",
        fr=f"Impossible de calculer les droits de {sujet} dans {ns} : {res.stderr.strip()[:200]}",
    )
    return (json.loads(res.stdout).get("status") or {}).get("resourceRules") or []


def _droits_effectifs(host, sujet: str, ns: str) -> list[dict]:
    """Les règles que l'API accorde à sujet dans ns, moins ce que reçoit tout
    compte (mesuré sur un témoin, jamais écrit en dur)."""
    if ns not in _BASES:
        _BASES[ns] = {_cle(r) for r in _regles(host, _TEMOIN, ns)}
    return [r for r in _regles(host, sujet, ns) if _cle(r) not in _BASES[ns]]


def _porte_un_jeton(pod: dict) -> bool:
    projetes = {v["name"] for v in pod["spec"].get("volumes") or []
                if any("serviceAccountToken" in s for s in (v.get("projected") or {}).get("sources") or [])}
    return any(m.get("mountPath", "").startswith(JETON) or m.get("name") in projetes
               for c in (pod["spec"].get("containers") or []) + (pod["spec"].get("initContainers") or [])
               for m in c.get("volumeMounts") or [])


def _peut(host, sujet: str, verbe: str, ressource: str, ns: str | None) -> bool:
    portee = f"-n {ns}" if ns else ""
    return host.run(f"{ADMIN} auth can-i {verbe} {ressource} {portee} --as {sujet}").stdout.strip() == "yes"


def test_c10_identite_dediee_sans_jeton_et_droit_minimal(host):
    pods = _pods_de(host, NS, "programme")
    assert pods, message(
        en=f"No running copy of programme in {NS}.",
        fr=f"Aucun exemplaire de programme en marche dans {NS}.",
    )
    comptes = {p["spec"].get("serviceAccountName") or "default" for p in pods}
    compte = next(iter(comptes))
    assert len(comptes) == 1 and compte != "default" and _json(host, NS, f"get serviceaccount {compte}"), message(
        en=f"programme runs under {sorted(comptes)}: expected one identity of its own, not the namespace's "
        "default one.",
        fr=f"programme tourne sous {sorted(comptes)} : attendu une identité qui lui est propre, et non celle "
        "du namespace par défaut.",
    )
    partages = sorted(p["metadata"]["name"] for p in _vivants((_json(host, NS, "get pods") or {}).get("items") or [])
                      if p["spec"].get("serviceAccountName") == compte
                      and (p["metadata"].get("labels") or {}).get("app") != "programme")
    avec_jeton = sorted(p["metadata"]["name"] for p in pods if _porte_un_jeton(p))
    assert not partages and not avec_jeton, message(
        en=f"The identity {compte} is shared with {partages or 'no one'}; copies of programme carrying an API "
        f"token: {avec_jeton or 'none'}. Expected an identity used by programme alone, and no token mounted "
        "since programme never calls the API.",
        fr=f"L'identité {compte} est partagée avec {partages or 'personne'} ; exemplaires de programme qui "
        f"portent un jeton d'API : {avec_jeton or 'aucun'}. Attendu une identité utilisée par programme seul, "
        "et aucun jeton monté puisque programme n'appelle jamais l'API.",
    )
    sujet = f"system:serviceaccount:{NS}:{compte}"
    accorde = _peut(host, sujet, "get", "configmaps", NS) and _peut(host, sujet, "list", "configmaps", NS)
    en_trop: dict[str, list[str]] = {}
    for ns in (NS, PAIEMENT, PARTENAIRES, "default", "kube-system"):
        regles = _droits_effectifs(host, sujet, ns)
        if ns == NS:
            regles = [r for r in regles if not (
                set(r.get("apiGroups") or []) <= {""}
                and set(r.get("resources") or []) <= {"configmaps"}
                and set(r.get("verbs") or []) <= {"get", "list", "watch"})]
        if regles:
            en_trop[ns] = [f"{','.join(r.get('verbs') or [])} {','.join(r.get('resources') or [])}" for r in regles]
    administre = [action for action, verbe, ressource in (
        ("get nodes", "get", "nodes"), ("create clusterrolebindings", "create", "clusterrolebindings"),
        ("* *", "'*'", "'*'")) if _peut(host, sujet, verbe, ressource, None)]
    assert accorde and not en_trop and not administre, message(
        en=f"The identity {compte} {'reads' if accorde else 'does not read'} the ConfigMaps of {NS}; rights "
        f"beyond that: {en_trop or 'none'}; cluster administration: {administre or 'none'}. Expected reading "
        f"the ConfigMaps of {NS}, and nothing else anywhere.",
        fr=f"L'identité {compte} {'lit' if accorde else 'ne lit pas'} les ConfigMaps de {NS} ; droits au-delà : "
        f"{en_trop or 'aucun'} ; administration du cluster : {administre or 'aucune'}. Attendu la lecture des "
        f"ConfigMaps de {NS}, et rien d'autre nulle part.",
    )


# ----------------------------------------------------------------------
# C11 (critique) : programme sans root, racine en lecture seule, sans
# capacités, et qui répond toujours.
# ----------------------------------------------------------------------
def _ecarts_de_durcissement(pod: dict) -> list[str]:
    """Réglages du Pod et du conteneur fusionnés comme le kubelet les applique."""
    spec = pod["spec"]
    conteneur = next((c for c in spec["containers"] if c["name"] == "programme"), spec["containers"][0])
    sc_pod = spec.get("securityContext") or {}
    sc = {**{k: sc_pod[k] for k in ("runAsNonRoot", "runAsUser") if k in sc_pod},
          **(conteneur.get("securityContext") or {})}
    capacites = sc.get("capabilities") or {}
    ecarts = []
    if sc.get("runAsNonRoot") is not True:
        ecarts.append("runAsNonRoot")
    if not isinstance(sc.get("runAsUser"), int) or sc.get("runAsUser") == 0:
        ecarts.append(message(en="numeric non-zero UID", fr="UID numérique non nul"))
    if sc.get("readOnlyRootFilesystem") is not True:
        ecarts.append("readOnlyRootFilesystem")
    if "ALL" not in (capacites.get("drop") or []):
        ecarts.append("capabilities drop ALL")
    if capacites.get("add"):
        ecarts.append(message(en=f"capabilities added back: {capacites['add']}",
                              fr=f"capabilities rajoutées : {capacites['add']}"))
    return ecarts


def test_c11_programme_durci_et_qui_repond(host):
    pods = _pods_de(host, NS, "programme")
    assert pods, message(
        en=f"No running copy of programme in {NS}. A hardened copy that cannot start does not count.",
        fr=f"Aucun exemplaire de programme en marche dans {NS}. Un exemplaire durci qui ne démarre pas ne "
        "compte pas.",
    )
    ecarts = {p["metadata"]["name"]: e for p in pods if (e := _ecarts_de_durcissement(p))}
    assert not ecarts, message(
        en=f"The running copies of programme are not hardened: {ecarts}.",
        fr=f"Les exemplaires en marche de programme ne sont pas durcis : {ecarts}.",
    )
    nom = pods[0]["metadata"]["name"]
    uid = _exec(host, NS, nom, "id -u").stdout.strip()
    ecrit = _exec(host, NS, nom, "touch /essai-ecriture").rc == 0
    capacites = _exec(host, NS, nom, "grep CapEff /proc/1/status").stdout.split()
    effectives = capacites[-1] if capacites else "?"
    corps = _exec(host, NS, nom, "wget -qO- -T 3 http://127.0.0.1:8080/").stdout.strip()
    assert uid not in ("", "0") and not ecrit and effectives.strip("0") == "" and effectives != "?" \
        and corps == "programme", message(
        en=f"Inside programme: UID {uid!r}, write at the root {'succeeds' if ecrit else 'refused'}, effective "
        f"capabilities {effectives}, page {corps[:40]!r}. Expected a non-zero UID, a refused write, no "
        "capability, and the page still served.",
        fr=f"Dans programme : UID {uid!r}, écriture à la racine {'réussie' if ecrit else 'refusée'}, "
        f"capabilities effectives {effectives}, page {corps[:40]!r}. Attendu un UID non nul, une écriture "
        "refusée, aucune capability, et la page toujours servie.",
    )
