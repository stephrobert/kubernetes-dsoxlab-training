"""test_functional.py : k8s-challenge-depanner-une-application

Le challenge du module « Diagnostiquer » du niveau 4. Ces tests lisent l'état
du CLUSTER et des NŒUDS, et les fichiers de causes de ~/incident, jamais les
commandes tapées. Un test vérifie un seul état, dans l'ordre de la fiche.

Quatre pannes sont posées par le setup : api (Deployment en CrashLoopBackOff),
vitrine (Pod en ImagePullBackOff), l'API server (flag mal orthographié dans son
manifeste statique) et le kubelet de k8s-w1.lab (arrêté, désactivé, et dont la
configuration ne se lit plus). Les dix tests échouent sur cet état : l'API ne
répond pas, le manifeste porte la faute, le kubelet est arrêté et désactivé,
et ~/incident est vide.

« Consigné avant la réparation » se lit comme dans
k8s-epreuve-livrer-et-mettre-a-jour : la date du fichier de cause est comparée
au démarrage de ce qui a été réparé. Un fichier par panne, parce qu'un fichier
unique serait impossible à tenir : tant que l'API server est tombé, les deux
pannes applicatives ne se diagnostiquent pas par kubectl.

Aucun test n'attend tant que le travail n'est pas commencé : une attente ne
s'ouvre que si la réparation est faite et converge encore (dsoxlab coupe pytest
au bout de 300 secondes, et l'état du setup doit se noter vite).
"""

from __future__ import annotations

import ipaddress
import json
import re
import time
import unicodedata
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

CONTROL_PLANE = "k8s-cp.lab"
WORKER = "k8s-w1.lab"
NS = "commerce"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf --request-timeout=15s"
MANIFESTE = "/etc/kubernetes/manifests/kube-apiserver.yaml"
POD_API_SERVER = f"kube-apiserver-{CONTROL_PLANE}"
CHEMIN = "/etc/config"
PAS = 5

#: Chaque panne, son fichier sous ~/incident, et ce qu'une cause tirée des
#: journaux, de describe ou des événements nomme forcément. Les textes sont
#: compactés (minuscules, sans accent, sans espace ni ponctuation sauf le
#: point) : « No such file » devient « nosuchfile », « --authorization-modes »
#: devient « authorizationmodes ». Le seul statut affiché par Kubernetes
#: (CrashLoopBackOff, ImagePullBackOff, NotReady) ne suffit pas : il dit qu'il y
#: a une panne, pas laquelle.
CAUSES = {
    "api": ("api.txt", ("appconfigpath", "app.conf", "nonexistent", "etcconfig", "configmap",
                        "nosuchfile", "cantopen")),
    "vitrine": ("vitrine.txt", ("alpin", "notfound", "manifestunknown", "nexistepas", "introuvable",
                                "inexistant", "doesnotexist", "doesntexist", "failedtoresolve")),
    "apiserver": ("apiserver.txt", ("authorization", "authorisation", "unknownflag", "flaginconnu",
                                    "providedbutnotdefined")),
    "kubelet": ("kubelet.txt", ("clusterdns", "999.999", "config.yaml", "yaml", "indent", "disabled",
                                "desactiv", "notenabled", "inactive", "dead", "stopped", "arret")),
}
#: Le démarrage du kubelet se lit sur l'horloge du worker, le fichier sur celle
#: du control plane : on tolère l'écart de deux horloges synchronisées.
TOLERANCE_HORLOGES = 2


@pytest.fixture(scope="module")
def cp():
    return lab_host(lab_target_host(CONTROL_PLANE))


@pytest.fixture(scope="module")
def worker():
    return lab_host(WORKER)


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _api_repond(cp) -> bool:
    res = cp.run(f"{KUBECTL} get --raw /readyz")
    return res.rc == 0 and res.stdout.strip() == "ok"


def _exiger_l_api(cp) -> None:
    assert _api_repond(cp), message(
        en="The API server does not answer: nothing of the cluster can be read through it. It is the "
        "failure that blinds all the others, the node itself still sees: crictl and journalctl.",
        fr="L'API server ne répond pas : rien du cluster ne se lit par lui. C'est la panne qui aveugle "
        "toutes les autres, le nœud, lui, voit encore : crictl et journalctl.",
    )


def _epoch(horodatage: str) -> float:
    return datetime.fromisoformat(horodatage.replace("Z", "+00:00")).timestamp()


def _compact(texte: str) -> str:
    sans_accent = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9.]", "", sans_accent.lower())


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _pret(pod: dict) -> bool:
    statuts = pod["status"].get("containerStatuses") or []
    return pod["status"].get("phase") == "Running" and bool(statuts) and all(s.get("ready") for s in statuts)


def _pods(cp, selecteur: str) -> list[dict]:
    """Les Pods vivants du sélecteur dans commerce, hors ceux en cours de suppression."""
    items = (_json(cp, f"-n {NS} get pods -l {selecteur}") or {}).get("items") or []
    return [p for p in items if not p["metadata"].get("deletionTimestamp")]


def _deployment(cp, nom: str) -> dict:
    dep = _json(cp, f"-n {NS} get deployment {nom}")
    assert dep is not None, message(
        en=f"The Deployment {nom} cannot be found in {NS}: the setup placed it there, it is repaired, not removed.",
        fr=f"Le Deployment {nom} est introuvable dans {NS} : le setup l'y avait posé, il se répare, il ne se retire pas.",
    )
    return dep


def _conteneur_api(dep: dict) -> dict:
    conteneurs = dep["spec"]["template"]["spec"]["containers"]
    return next((c for c in conteneurs if c["name"] == "api"), conteneurs[0])


def _env(conteneur: dict) -> dict:
    return {e["name"]: e.get("value") for e in conteneur.get("env") or []}


def _attendre_deployment(cp, nom: str, voulus: int, secondes: int) -> dict:
    """Rend le Deployment, en lui laissant le temps de finir un rollout déjà lancé."""
    dep = _deployment(cp, nom)
    fin = time.monotonic() + secondes
    while time.monotonic() < fin:
        statut = dep.get("status") or {}
        if statut.get("availableReplicas", 0) == voulus and statut.get("updatedReplicas", 0) == voulus \
                and statut.get("observedGeneration", 0) >= dep["metadata"].get("generation", 0):
            break
        time.sleep(PAS)
        dep = _deployment(cp, nom)
    return dep


# ----------------------------------------------------------------------
# 1. Le Deployment api a ses deux replicas disponibles.
# ----------------------------------------------------------------------
def test_api_a_ses_deux_replicas_disponibles(cp):
    _exiger_l_api(cp)
    dep = _deployment(cp, "api")
    voulus = dep["spec"].get("replicas", 1)
    assert voulus == 2, message(
        en=f"The Deployment api asks for {voulus} replica(s) instead of 2. Reducing the number of replicas "
        "repairs nothing, it hides the failure.",
        fr=f"Le Deployment api demande {voulus} replica(s) au lieu de 2. Réduire le nombre de replicas ne "
        "répare rien, cela cache la panne.",
    )
    # On n'attend que si la réparation est déclarée : sinon l'état du setup se
    # noterait au bout d'une minute, pour rien.
    if _env(_conteneur_api(dep)).get("APP_CONFIG_PATH") == CHEMIN:
        dep = _attendre_deployment(cp, "api", 2, 60)
    disponibles = (dep.get("status") or {}).get("availableReplicas", 0)
    assert disponibles == 2, message(
        en=f"{disponibles} replica(s) of api available out of 2. As long as the container dies at startup, no "
        "Pod becomes available: what it wrote before dying says what it is missing.",
        fr=f"{disponibles} replica(s) d'api disponible(s) sur 2. Tant que le conteneur meurt au démarrage, "
        "aucun Pod ne devient disponible : ce qu'il a écrit avant de mourir dit ce qui lui manque.",
    )


# ----------------------------------------------------------------------
# 2. Plus aucun Pod d'api ne redémarre en boucle.
# ----------------------------------------------------------------------
def test_api_ne_redemarre_plus_en_boucle(cp):
    _exiger_l_api(cp)
    pods = _pods(cp, "app=api")
    assert pods, message(
        en=f"No Pod of api in {NS}.",
        fr=f"Aucun Pod d'api dans {NS}.",
    )
    fautifs = {}
    for p in pods:
        for s in p["status"].get("containerStatuses") or []:
            raison = ((s.get("state") or {}).get("waiting") or {}).get("reason")
            if raison == "CrashLoopBackOff" or s.get("restartCount", 0) > 0 or not s.get("ready"):
                fautifs[p["metadata"]["name"]] = {
                    "raison": raison, "redemarrages": s.get("restartCount", 0), "pret": s.get("ready")}
    assert not fautifs, message(
        en=f"Pods of api still restart, or are not ready: {fautifs}. A repaired Pod starts once and stays "
        "up; an old Pod lingering means the rollout is not finished.",
        fr=f"Des Pods d'api redémarrent encore, ou ne sont pas prêts : {fautifs}. Un Pod réparé démarre une "
        "fois et tient ; un Pod ancien qui traîne veut dire que le rollout n'est pas fini.",
    )


# ----------------------------------------------------------------------
# 3. api lit sa configuration sous /etc/config, et répond.
# ----------------------------------------------------------------------
def test_api_lit_sa_configuration_au_bon_endroit_et_repond(cp):
    _exiger_l_api(cp)
    valeur = _env(_conteneur_api(_deployment(cp, "api"))).get("APP_CONFIG_PATH")
    assert valeur == CHEMIN, message(
        en=f"In the Deployment api, APP_CONFIG_PATH is {valeur!r} and not {CHEMIN!r}. The team's convention "
        "puts the configuration there, and it is the Deployment that must say so, not a Pod edited by hand.",
        fr=f"Dans le Deployment api, APP_CONFIG_PATH vaut {valeur!r} et non {CHEMIN!r}. La charte de "
        "l'équipe place la configuration là, et c'est le Deployment qui doit le dire, pas un Pod édité à la main.",
    )
    prets = [p for p in _pods(cp, "app=api") if _pret(p)]
    assert prets, message(
        en="No Pod of api is ready: there is no way in to check the configuration.",
        fr="Aucun Pod d'api n'est prêt : impossible d'y entrer pour vérifier la configuration.",
    )
    nom = prets[0]["metadata"]["name"]
    lecture = cp.run(f"{KUBECTL} -n {NS} exec {nom} -- cat {CHEMIN}/app.conf")
    assert lecture.rc == 0 and "listen=8080" in lecture.stdout, message(
        en=f"{CHEMIN}/app.conf is not the team's configuration in the Pod {nom}: the configuration exists in "
        f"the namespace, it is still to be given to the container. {lecture.stderr.strip()[:200]}",
        fr=f"{CHEMIN}/app.conf n'est pas la configuration de l'équipe dans le Pod {nom} : la configuration "
        f"existe dans le namespace, il reste à la donner au conteneur. {lecture.stderr.strip()[:200]}",
    )
    reponse = cp.run(f"{KUBECTL} -n {NS} exec {nom} -- wget -qO- -T 5 http://127.0.0.1:8080/app.conf")
    assert reponse.rc == 0 and "listen=8080" in reponse.stdout, message(
        en="The Pod is ready but api does not answer on port 8080: a running container is not a serving "
        f"application. {reponse.stderr.strip()[:200]}",
        fr="Le Pod est prêt mais api ne répond pas sur le port 8080 : un conteneur qui tourne n'est pas une "
        f"application qui sert. {reponse.stderr.strip()[:200]}",
    )


# ----------------------------------------------------------------------
# 4. vitrine tourne sur une image publique réellement tirée, et répond.
# ----------------------------------------------------------------------
def _vitrine(cp) -> dict:
    pod = _json(cp, f"-n {NS} get pod vitrine")
    assert pod is not None, message(
        en=f"The Pod vitrine cannot be found in {NS}: it serves the shop window, it is repaired, not removed.",
        fr=f"Le Pod vitrine est introuvable dans {NS} : il sert la vitrine, il se répare, il ne se retire pas.",
    )
    return pod


def test_vitrine_tourne_sur_une_image_publique_tiree_et_repond(cp):
    _exiger_l_api(cp)
    pod = _vitrine(cp)
    statut = (pod["status"].get("containerStatuses") or [{}])[0]
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    # Une image qui vient d'être corrigée se télécharge encore : on lui laisse
    # ce temps, et seulement à elle.
    fin = time.monotonic() + 45
    while not _pret(pod) and raison in ("ContainerCreating", "PodInitializing", None) \
            and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _vitrine(cp)
        statut = (pod["status"].get("containerStatuses") or [{}])[0]
        raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    assert _pret(pod), message(
        en=f"The Pod vitrine does not run (waiting reason: {raison}). The exact message of the runtime, the "
        "one that says whether the name, the tag or the registry is wrong, is in the Pod's events.",
        fr=f"Le Pod vitrine ne tourne pas (raison d'attente : {raison}). Le message exact du runtime, celui "
        "qui dit si c'est le nom, le tag ou le registre qui cloche, est dans les événements du Pod.",
    )
    image = pod["spec"]["containers"][0].get("image", "")
    tiree = statut.get("imageID", "")
    assert "nginx" in image and "nginx" in tiree, message(
        en=f"vitrine declares {image!r} and the node pulled {tiree!r}: a public nginx image is expected, "
        "really pulled. The reference is fixed, the server is not changed.",
        fr=f"vitrine déclare {image!r} et le nœud a tiré {tiree!r} : une image nginx publique est attendue, "
        "réellement tirée. On corrige la référence, on ne change pas de serveur.",
    )
    ip = pod["status"].get("podIP")
    res = cp.run(f"curl -sS -m 5 http://{ip}/")
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en=f"Nothing answers nginx's page on {ip}:80 from the node. A Running Pod is not necessarily a "
        f"serving server. {res.stderr.strip()[:200]}",
        fr=f"Rien ne répond la page de nginx sur {ip}:80 depuis le nœud. Un Pod Running n'est pas forcément "
        f"un serveur qui sert. {res.stderr.strip()[:200]}",
    )


# ----------------------------------------------------------------------
# 5. La cause de chaque panne est consignée avant sa réparation.
# ----------------------------------------------------------------------
def _demarrage_api(cp) -> float | None:
    """Le démarrage des Pods d'api réparés, ou None s'ils ne tournent pas."""
    if not _api_repond(cp):
        return None
    debuts = [_epoch(s["state"]["running"]["startedAt"])
              for p in _pods(cp, "app=api") if _pret(p)
              for s in p["status"].get("containerStatuses") or [] if (s.get("state") or {}).get("running")]
    return min(debuts) if debuts else None


def _demarrage_vitrine(cp) -> float | None:
    if not _api_repond(cp):
        return None
    pod = _json(cp, f"-n {NS} get pod vitrine")
    if not pod or not _pret(pod):
        return None
    running = ((pod["status"].get("containerStatuses") or [{}])[0].get("state") or {}).get("running") or {}
    return _epoch(running["startedAt"]) if running.get("startedAt") else None


def _demarrage_api_server(cp) -> float | None:
    if not _api_repond(cp):
        return None
    pod = _json(cp, f"-n kube-system get pod {POD_API_SERVER}")
    running = (((pod or {}).get("status", {}).get("containerStatuses") or [{}])[0].get("state") or {}).get("running") or {}
    return _epoch(running["startedAt"]) if running.get("startedAt") else None


def _demarrage_kubelet(worker) -> float | None:
    if worker.run("systemctl is-active kubelet").stdout.strip() != "active":
        return None
    res = worker.run('date -d "$(systemctl show kubelet -p ActiveEnterTimestamp --value)" +%s')
    return float(res.stdout.strip()) + TOLERANCE_HORLOGES if res.rc == 0 and res.stdout.strip() else None


def test_chaque_cause_est_consignee_avant_sa_reparation(cp, worker):
    repertoire = f"{_maison(cp)}/incident"
    reparations = {
        "api": lambda: _demarrage_api(cp),
        "vitrine": lambda: _demarrage_vitrine(cp),
        "apiserver": lambda: _demarrage_api_server(cp),
        "kubelet": lambda: _demarrage_kubelet(worker),
    }
    ecarts_en, ecarts_fr = [], []
    for panne, (nom, mots) in CAUSES.items():
        chemin = f"{repertoire}/{nom}"
        fichier = cp.file(chemin)
        if not fichier.exists:
            ecarts_en.append(f"~/incident/{nom} is missing")
            ecarts_fr.append(f"~/incident/{nom} est absent")
            continue
        if not any(m in _compact(fichier.content_string) for m in mots):
            ecarts_en.append(f"~/incident/{nom} does not name the cause, only that something fails")
            ecarts_fr.append(f"~/incident/{nom} ne nomme pas la cause, seulement que quelque chose échoue")
            continue
        repare_le = reparations[panne]()
        if repare_le is None:
            continue
        ecrit_le = int(cp.check_output(f"stat -c %Y {chemin}").strip())
        if ecrit_le > int(repare_le):
            ecarts_en.append(f"~/incident/{nom} was written or changed after the repair started")
            ecarts_fr.append(f"~/incident/{nom} a été écrit ou modifié après le démarrage de la réparation")
    assert not ecarts_en, message(
        en="The causes are not recorded as asked: " + "; ".join(ecarts_en) + ". One file per failure, "
        "written from describe, the events or the logs BEFORE the repair, then left untouched: its date "
        "is compared with the start of what was repaired.",
        fr="Les causes ne sont pas consignées comme demandé : " + " ; ".join(ecarts_fr) + ". Un fichier par "
        "panne, écrit à partir de describe, des événements ou des journaux AVANT la réparation, puis laissé "
        "tel quel : sa date est comparée au démarrage de ce qui a été réparé.",
    )


# ----------------------------------------------------------------------
# 6. L'API server répond, et son Pod statique tourne sans boucle.
# ----------------------------------------------------------------------
def test_l_api_server_repond_et_son_pod_statique_tourne(cp):
    _exiger_l_api(cp)
    noeuds = cp.run(f"{KUBECTL} get nodes --no-headers")
    assert noeuds.rc == 0 and CONTROL_PLANE in noeuds.stdout, message(
        en=f"/readyz answers but kubectl get nodes fails: {noeuds.stderr.strip()[:200]}",
        fr=f"/readyz répond mais kubectl get nodes échoue : {noeuds.stderr.strip()[:200]}",
    )
    # /readyz répond quelques secondes avant que le Pod miroir passe prêt
    # (mesuré par cka-troubleshoot-apiserver) : on laisse au kubelet sa sonde.
    pod, statut = {}, {}
    for _ in range(18):
        pod = _json(cp, f"-n kube-system get pod {POD_API_SERVER}") or {}
        statut = ((pod.get("status") or {}).get("containerStatuses") or [{}])[0]
        if pod and _pret(pod):
            break
        time.sleep(PAS)
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    assert pod and _pret(pod) and raison != "CrashLoopBackOff", message(
        en=f"The static Pod {POD_API_SERVER} is not running and ready (waiting reason: {raison}, restarts: "
        f"{statut.get('restartCount')}). Its container still exits at startup: crictl logs says why.",
        fr=f"Le Pod statique {POD_API_SERVER} ne tourne pas, prêt (raison d'attente : {raison}, "
        f"redémarrages : {statut.get('restartCount')}). Son conteneur sort encore au démarrage : crictl logs "
        "dit pourquoi.",
    )


# ----------------------------------------------------------------------
# 7. Le manifeste est sain, et autorise toujours avec Node,RBAC.
# ----------------------------------------------------------------------
def test_le_manifeste_de_l_api_server_est_sain_et_autorise_node_rbac(cp):
    res = cp.run(f"sudo cat {MANIFESTE}")
    assert res.rc == 0, message(
        en=f"Cannot read {MANIFESTE}: {res.stderr.strip()[:200]}",
        fr=f"Impossible de lire {MANIFESTE} : {res.stderr.strip()[:200]}",
    )
    assert "--authorization-modes=" not in res.stdout, message(
        en="The manifest still carries the misspelled flag --authorization-modes: the API server does not "
        "know it and exits at startup. Compare it, letter by letter, with the documented flag.",
        fr="Le manifeste porte encore le flag mal orthographié --authorization-modes : l'API server ne le "
        "connaît pas et sort au démarrage. Comparez-le, lettre par lettre, au flag documenté.",
    )
    assert "--authorization-mode=Node,RBAC" in res.stdout, message(
        en="The manifest no longer declares --authorization-mode=Node,RBAC. Deleting the line does restart "
        "the API server, but without an authorization mode it lets every authenticated request through: "
        "that is an open door, not a repair.",
        fr="Le manifeste ne déclare plus --authorization-mode=Node,RBAC. Supprimer la ligne fait bien "
        "redémarrer l'API server, mais sans mode d'autorisation il laisse passer toute requête "
        "authentifiée : c'est une porte ouverte, pas une réparation.",
    )


# ----------------------------------------------------------------------
# 8. Le worker est Ready, avec un kubelet qui garde le DNS du cluster.
# ----------------------------------------------------------------------
def _pret_noeud(cp) -> str:
    noeud = _json(cp, f"get node {WORKER}") or {}
    conditions = {c["type"]: c for c in (noeud.get("status") or {}).get("conditions") or []}
    return conditions.get("Ready", {}).get("status", "Unknown")


def test_le_worker_est_ready_avec_un_kubelet_qui_garde_le_dns(cp, worker):
    _exiger_l_api(cp)
    statut = _pret_noeud(cp)
    # Le control plane met jusqu'à une minute à revoir un nœud : on l'attend,
    # mais seulement si son kubelet tourne.
    if statut != "True" and worker.run("systemctl is-active kubelet").stdout.strip() == "active":
        for _ in range(18):
            time.sleep(PAS)
            statut = _pret_noeud(cp)
            if statut == "True":
                break
    assert statut == "True", message(
        en=f"The node {WORKER} is not Ready (Ready = {statut}). On the node, systemctl status kubelet says "
        "whether the service runs, and journalctl -u kubelet what it holds against its configuration.",
        fr=f"Le nœud {WORKER} n'est pas Ready (Ready = {statut}). Sur le nœud, systemctl status kubelet dit "
        "si le service tourne, et journalctl -u kubelet ce qu'il reproche à sa configuration.",
    )
    # La configuration que le kubelet applique VRAIMENT, telle qu'il la sert à
    # l'API, et non le fichier : c'est elle que reçoivent les Pods.
    res = cp.run(f"{KUBECTL} get --raw /api/v1/nodes/{WORKER}/proxy/configz")
    assert res.rc == 0, message(
        en=f"Cannot read the running configuration of the kubelet of {WORKER}: {res.stderr.strip()[:200]}",
        fr=f"Impossible de lire la configuration en service du kubelet de {WORKER} : {res.stderr.strip()[:200]}",
    )
    resolveurs = (json.loads(res.stdout).get("kubeletconfig") or {}).get("clusterDNS") or []
    service = _json(cp, "-n kube-system get service kube-dns") or {}
    dns = (service.get("spec") or {}).get("clusterIP", "")
    invalides = []
    for r in resolveurs:
        try:
            ipaddress.ip_address(r)
        except ValueError:
            invalides.append(r)
    assert dns and dns in resolveurs and not invalides, message(
        en=f"The kubelet of {WORKER} runs with clusterDNS = {resolveurs}; expected the address of the kube-dns "
        f"Service, {dns}, and nothing that is not an address{f' (here: {invalides})' if invalides else ''}. "
        "Re-indenting the added line or emptying the field makes the kubelet start, but the Pods of the "
        "node then resolve badly or not at all: the added line goes, the field stays.",
        fr=f"Le kubelet de {WORKER} tourne avec clusterDNS = {resolveurs} ; attendu l'adresse du Service "
        f"kube-dns, {dns}, et rien qui ne soit pas une adresse{f' (ici : {invalides})' if invalides else ''}. "
        "Réindenter la ligne ajoutée ou vider le champ fait démarrer le kubelet, mais les Pods du nœud "
        "résolvent alors mal ou plus du tout : la ligne ajoutée part, le champ reste.",
    )


# ----------------------------------------------------------------------
# 9. Le kubelet est actif, et activé au démarrage de la machine.
# ----------------------------------------------------------------------
def test_le_kubelet_est_actif_et_active_au_demarrage(worker):
    actif = worker.run("systemctl is-active kubelet").stdout.strip()
    active = worker.run("systemctl is-enabled kubelet").stdout.strip()
    assert actif == "active", message(
        en=f"The kubelet of {WORKER} is {actif!r}, not active. If it stops as soon as it starts, it refuses "
        "its configuration: the journal names the file and the line.",
        fr=f"Le kubelet de {WORKER} est {actif!r}, pas actif. S'il s'arrête aussitôt lancé, il refuse sa "
        "configuration : le journal nomme le fichier et la ligne.",
    )
    assert active == "enabled", message(
        en=f"The kubelet of {WORKER} runs, but is {active!r} at boot: the next reboot of the machine takes "
        "the node out of the cluster again. Starting a service and enabling it are two different things.",
        fr=f"Le kubelet de {WORKER} tourne, mais il est {active!r} au démarrage : le prochain redémarrage de "
        "la machine sortira de nouveau le nœud du cluster. Démarrer un service et l'activer sont deux choses.",
    )


# ----------------------------------------------------------------------
# 10. entrepot a de nouveau ses trois replicas, sur le worker.
# ----------------------------------------------------------------------
def test_entrepot_a_ses_trois_replicas_sur_le_worker(cp):
    _exiger_l_api(cp)
    dep = _deployment(cp, "entrepot")
    voulus = dep["spec"].get("replicas", 0)
    assert voulus == 3, message(
        en=f"The Deployment entrepot asks for {voulus} replica(s) instead of 3: it was not to be touched.",
        fr=f"Le Deployment entrepot demande {voulus} replica(s) au lieu de 3 : il ne fallait pas y toucher.",
    )
    if _pret_noeud(cp) == "True":
        dep = _attendre_deployment(cp, "entrepot", 3, 90)
    disponibles = (dep.get("status") or {}).get("availableReplicas", 0)
    assert disponibles == 3, message(
        en=f"{disponibles} replica(s) of entrepot available out of 3. It is reserved for {WORKER}: as long as "
        "that node cannot host it, it stays degraded.",
        fr=f"{disponibles} replica(s) d'entrepot disponible(s) sur 3. Il est réservé à {WORKER} : tant que ce "
        "nœud ne peut pas l'accueillir, il reste dégradé.",
    )
    prets = [p for p in _pods(cp, "app=entrepot") if _pret(p)]
    ailleurs = [p["metadata"]["name"] for p in prets if p["spec"].get("nodeName") != WORKER]
    assert len(prets) >= 3 and not ailleurs, message(
        en=f"{len(prets)} ready Pod(s) of entrepot, and these run somewhere other than {WORKER}: {ailleurs}. "
        "Moving the application is not repairing the node.",
        fr=f"{len(prets)} Pod(s) d'entrepot prêt(s), et ceux-ci tournent ailleurs que sur {WORKER} : "
        f"{ailleurs}. Déplacer l'application n'est pas réparer le nœud.",
    )
