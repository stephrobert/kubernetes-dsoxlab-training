"""test_functional.py : cka-examen-blanc

Vingt états, un test chacun, à 5 points : la note sur 100 suit donc les poids
officiels des domaines de la CKA (Storage 10, Troubleshooting 30, Workloads and
Scheduling 15, Cluster Architecture 25, Servicing and Networking 20). Une tâche
de 10 points porte deux états.

Les tests lisent l'état du cluster, des nœuds et des fichiers, et font de
vraies requêtes. Jamais les commandes tapées. Chaque état est faux au départ :
la préparation pose une panne ou laisse l'objet à créer.

Les attentes sont courtes et ne s'ouvrent que si l'objet attendu existe déjà :
dsoxlab accorde 300 s à toute la suite.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
WORKER = "k8s-w1.lab"
PLAN = "k8s-cp.lab"
NGINX_1305 = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
NGINX_1306 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
MOT_DE_PASSE = "jeton-de-demonstration"
PORT_TRAEFIK = 30080
NODEPORT = 30092
SNAPSHOT = "/var/lib/etcd/sauvegarde-examen.db"
ATTENTE_S = 30
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(PLAN))


@pytest.fixture(scope="module")
def worker():
    return lab_host(WORKER)


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _objet(host, args: str) -> dict | None:
    res = _kubectl(host, f"{args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _pods(host, ns: str, selecteur: str) -> list[dict]:
    return (_objet(host, f"-n {ns} get pods -l {selecteur}") or {}).get("items", [])


def _ready(pod: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (pod.get("status") or {}).get("conditions") or [])


def _condition(objet: dict | None, type_: str) -> str:
    return next((c.get("status", "") for c in ((objet or {}).get("status") or {}).get("conditions") or []
                 if c.get("type") == type_), "")


def _curl_traefik(host, hote: str, chemin: str) -> str:
    return host.run(
        f"curl -s --max-time 5 --resolve {hote}:{PORT_TRAEFIK}:127.0.0.1 http://{hote}:{PORT_TRAEFIK}{chemin}"
    ).stdout.strip()


def _attendre(mesure, juste, existe: bool):
    valeur = mesure()
    if not juste(valeur) and existe:
        fin = time.monotonic() + ATTENTE_S
        while not juste(valeur) and time.monotonic() < fin:
            time.sleep(PAS_S)
            valeur = mesure()
    return valeur


def _ip(host, noeud: str) -> str:
    n = _objet(host, f"get node {noeud}") or {}
    return next((a["address"] for a in (n.get("status") or {}).get("addresses") or []
                 if a.get("type") == "InternalIP"), "")


# ======================================================================
# Storage (10)
# ======================================================================
def test_t01_la_classe_rapide(host):
    sc = _objet(host, "get storageclass rapide") or {}
    vu = (sc.get("provisioner"), sc.get("reclaimPolicy"), sc.get("volumeBindingMode"))
    attendu = ("rancher.io/local-path", "Retain", "WaitForFirstConsumer")
    assert vu == attendu, message(
        en=f"Task 1: StorageClass rapide has provisioner, reclaimPolicy and volumeBindingMode {vu}, expected {attendu}.",
        fr=f"Tâche 1 : la StorageClass rapide a pour provisionneur, reclaimPolicy et volumeBindingMode {vu}, "
        f"attendu {attendu}.",
    )


def test_t02_la_revendication_donnees_sert_ecrivain(host):
    pvc = _objet(host, "-n appli get pvc donnees") or {}
    pod = _objet(host, "-n appli get pod ecrivain") or {}
    monte = any((v.get("persistentVolumeClaim") or {}).get("claimName") == "donnees"
                for v in (pod.get("spec") or {}).get("volumes") or [])
    contenu = _kubectl(host, "-n appli exec ecrivain -- cat /data/ok").stdout.strip() if monte else ""
    vu = ((pvc.get("spec") or {}).get("storageClassName"), (pvc.get("status") or {}).get("phase"), monte, contenu)
    assert vu == ("rapide", "Bound", True, "ok"), message(
        en=f"Task 2: claim donnees (class, phase) = {vu[:2]}, Pod ecrivain mounts it: {vu[2]}, /data/ok holds "
        f"{vu[3]!r}. Expected class rapide, Bound, mounted, and the file holding ok.",
        fr=f"Tâche 2 : revendication donnees (classe, phase) = {vu[:2]}, le Pod ecrivain la monte : {vu[2]}, "
        f"/data/ok contient {vu[3]!r}. Attendu classe rapide, Bound, montée, et le fichier contenant ok.",
    )


# ======================================================================
# Troubleshooting (30)
# ======================================================================
def test_t03a_le_worker_est_ready(host):
    noeud = _objet(host, f"get node {WORKER}")
    assert noeud is not None and _condition(noeud, "Ready") == "True", message(
        en=f"Task 3: node {WORKER} is not Ready.",
        fr=f"Tâche 3 : le nœud {WORKER} n'est pas Ready.",
    )


def test_t03b_le_kubelet_du_worker_demarre_au_boot(worker):
    service = worker.service("kubelet")
    assert service.is_running and service.is_enabled, message(
        en=f"Task 3: the kubelet of {WORKER} runs: {service.is_running}, starts at boot: {service.is_enabled}. "
        "Expected both: a node that comes back only until its next reboot is not repaired.",
        fr=f"Tâche 3 : le kubelet de {WORKER} tourne : {service.is_running}, démarre au boot : {service.is_enabled}. "
        "Attendu les deux : un nœud qui ne revient que jusqu'au prochain redémarrage n'est pas réparé.",
    )


def test_t04_facture_tourne_sans_redemarrer(host):
    dep = _objet(host, "-n appli get deployment facture") or {}
    pods = [p for p in _pods(host, "appli", "app=facture") if not p["metadata"].get("deletionTimestamp")]
    debout = [p for p in pods if _ready(p)]
    disponibles = (dep.get("status") or {}).get("availableReplicas", 0)
    assert disponibles == 2 and len(debout) == 2, message(
        en=f"Task 4: facture has {disponibles} available replica(s) and {len(debout)} ready Pod(s), expected 2 and 2.",
        fr=f"Tâche 4 : facture a {disponibles} réplica(s) disponible(s) et {len(debout)} Pod(s) prêt(s), attendu 2 et 2.",
    )


def test_t05a_l_annuaire_a_ses_endpoints(host):
    tranches = _objet(host, "-n appli get endpointslices -l kubernetes.io/service-name=annuaire") or {}
    vises = {(e.get("targetRef") or {}).get("name") for t in tranches.get("items", [])
             for e in t.get("endpoints") or [] if (e.get("conditions") or {}).get("ready")}
    pods = {p["metadata"]["name"] for p in _pods(host, "appli", "app=annuaire")}
    assert pods and vises == pods, message(
        en=f"Task 5: Service annuaire sends to {sorted(v for v in vises if v) or 'no Pod'}, expected the Pods of the "
        f"annuaire Deployment {sorted(pods)}.",
        fr=f"Tâche 5 : le Service annuaire envoie vers {sorted(v for v in vises if v) or 'aucun Pod'}, attendu les Pods "
        f"du Deployment annuaire {sorted(pods)}.",
    )


def test_t05b_le_client_joint_l_annuaire_par_son_nom(host):
    corps = _kubectl(host, "-n appli exec client -- wget -qO- -T 3 http://annuaire/").stdout.strip()
    assert corps == "annuaire", message(
        en=f"Task 5: from the Pod client, http://annuaire/ answers {corps or 'nothing'!r} instead of \"annuaire\".",
        fr=f"Tâche 5 : depuis le Pod client, http://annuaire/ répond {corps or 'rien'!r} au lieu de « annuaire ».",
    )


def test_t06_les_erreurs_du_journal_sont_consignees(host):
    journal = _kubectl(host, "-n appli logs journal -c app").stdout
    attendues = sorted(ligne.strip() for ligne in journal.splitlines() if "ERROR" in ligne)
    res = host.run(f"cat {_maison(host)}/examen/erreurs.txt")
    ecrites = sorted(ligne.strip() for ligne in res.stdout.splitlines() if ligne.strip()) if res.rc == 0 else []
    assert attendues and ecrites == attendues, message(
        en=f"Task 6: ~/examen/erreurs.txt holds {len(ecrites)} line(s); the app container of journal logged "
        f"{len(attendues)} line(s) containing ERROR. Expected exactly those lines.",
        fr=f"Tâche 6 : ~/examen/erreurs.txt contient {len(ecrites)} ligne(s) ; le conteneur app de journal a écrit "
        f"{len(attendues)} ligne(s) contenant ERROR. Attendu exactement ces lignes.",
    )


# ======================================================================
# Workloads and Scheduling (15)
# ======================================================================
def test_t07_vitrine_est_revenue_en_1305(host):
    dep = _objet(host, "-n appli get deployment vitrine") or {}
    image = ((dep.get("spec") or {}).get("template", {}).get("spec", {}).get("containers") or [{}])[0].get("image")
    revision = int(((dep.get("metadata") or {}).get("annotations") or {}).get("deployment.kubernetes.io/revision", 0))
    rs = (_objet(host, "-n appli get replicasets -l app=vitrine") or {}).get("items", [])
    passe_par_1306 = any(r["spec"]["template"]["spec"]["containers"][0].get("image") == NGINX_1306 for r in rs)
    assert image == NGINX_1305 and revision >= 3 and passe_par_1306, message(
        en=f"Task 7: vitrine runs {image}, revision {revision}, a ReplicaSet in 1.30.6 in its history: {passe_par_1306}. "
        "Expected 1.30.5 again, after an update to 1.30.6 followed by a rollback (revision 3 or more).",
        fr=f"Tâche 7 : vitrine lance {image}, révision {revision}, un ReplicaSet en 1.30.6 dans son historique : "
        f"{passe_par_1306}. Attendu de nouveau 1.30.5, après une mise à jour en 1.30.6 suivie d'un retour arrière "
        "(révision 3 ou plus).",
    )


def test_t08_api_lit_sa_configuration_et_son_secret(host):
    dep = _objet(host, "-n appli get deployment api") or {}
    env = ((dep.get("spec") or {}).get("template", {}).get("spec", {}).get("containers") or [{}])[0].get("env") or []
    refs = {e.get("name"): e.get("valueFrom") or {} for e in env}
    depuis_cm = (refs.get("MODE", {}).get("configMapKeyRef") or {}).get("name") == "reglages"
    depuis_secret = (refs.get("MOT_DE_PASSE", {}).get("secretKeyRef") or {}).get("name") == "acces"
    pods = [p for p in _pods(host, "appli", "app=api") if _ready(p) and not p["metadata"].get("deletionTimestamp")]
    valeurs = ""
    if pods:
        valeurs = _kubectl(host, f"-n appli exec {pods[0]['metadata']['name']} -- printenv MODE MOT_DE_PASSE").stdout
    vu = valeurs.split()
    assert depuis_cm and depuis_secret and vu == ["production", MOT_DE_PASSE], message(
        en=f"Task 8: MODE comes from the ConfigMap reglages: {depuis_cm}, MOT_DE_PASSE from the Secret acces: "
        f"{depuis_secret}, the container sees {len(vu)} of the two values as expected. Expected both references, and "
        "MODE=production in the container with the given password.",
        fr=f"Tâche 8 : MODE vient de la ConfigMap reglages : {depuis_cm}, MOT_DE_PASSE du Secret acces : "
        f"{depuis_secret}, le conteneur voit {len(vu)} des deux valeurs attendues. Attendu les deux références, et "
        "MODE=production dans le conteneur avec le mot de passe donné.",
    )


def test_t09_rapport_tourne_seulement_sur_le_worker(host):
    dep = _objet(host, "-n appli get deployment rapport") or {}
    spec = (dep.get("spec") or {}).get("template", {}).get("spec", {})
    tolere = any(t.get("key") == "examen" for t in spec.get("tolerations") or [])
    termes = (((spec.get("affinity") or {}).get("nodeAffinity") or {})
              .get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or []
    affinite = any(e.get("key") == "role-examen" for t in termes for e in t.get("matchExpressions") or [])
    noeud = _objet(host, f"get node {WORKER}") or {}
    taint = any(t.get("key") == "examen" and t.get("effect") == "NoSchedule"
                for t in (noeud.get("spec") or {}).get("taints") or [])
    pods = [p for p in _pods(host, "appli", "app=rapport") if not p["metadata"].get("deletionTimestamp")]
    places = {(p.get("spec") or {}).get("nodeName") for p in pods}
    tous = bool(pods) and places == {WORKER} and all(_ready(p) for p in pods)
    ok = tolere and affinite and taint and tous and not spec.get("nodeName")
    assert ok, message(
        en=f"Task 9: toleration {tolere}, required nodeAffinity on role-examen {affinite}, taint still on {WORKER} "
        f"{taint}, Pods placed on {sorted(n for n in places if n) or 'no node'}, nodeName in the template "
        f"{bool(spec.get('nodeName'))}. Expected every Pod ready on {WORKER} through toleration and affinity, the "
        "taint kept. This task requires the node repaired (task 3).",
        fr=f"Tâche 9 : toleration {tolere}, nodeAffinity requise sur role-examen {affinite}, taint toujours sur "
        f"{WORKER} {taint}, Pods placés sur {sorted(n for n in places if n) or 'aucun nœud'}, nodeName dans le "
        f"gabarit {bool(spec.get('nodeName'))}. Attendu tous les Pods prêts sur {WORKER} par toleration et "
        "affinité, le taint gardé. Cette tâche suppose le nœud réparé (tâche 3).",
    )


# ======================================================================
# Cluster Architecture, Installation and Configuration (25)
# ======================================================================
def _peut(host, verbe: str, ressource: str) -> bool:
    res = _kubectl(host, f"auth can-i {verbe} {ressource} -n appli --as system:serviceaccount:appli:lecteur")
    return res.stdout.strip() == "yes"


def test_t10a_lecteur_peut_lister_les_pods(host):
    assert _peut(host, "list", "pods") and _peut(host, "watch", "pods"), message(
        en="Task 10: the ServiceAccount lecteur of appli cannot list and watch Pods in appli.",
        fr="Tâche 10 : le ServiceAccount lecteur de appli ne peut pas lister et surveiller les Pods de appli.",
    )


def test_t10b_lecteur_ne_peut_rien_de_plus(host):
    sa = _objet(host, "-n appli get serviceaccount lecteur")
    liaisons = (_objet(host, "-n appli get rolebindings") or {}).get("items", [])
    lie = any(s.get("kind") == "ServiceAccount" and s.get("name") == "lecteur"
              for b in liaisons for s in b.get("subjects") or [])
    trop = [f"{v} {r}" for v, r in (("delete", "pods"), ("get", "secrets"), ("create", "deployments")) if _peut(host, v, r)]
    assert sa is not None and lie and not trop, message(
        en=f"Task 10: ServiceAccount lecteur exists: {sa is not None}, bound by a RoleBinding of appli: {lie}, "
        f"rights beyond reading Pods: {trop or 'none'}. Expected the account bound, and nothing beyond reading Pods.",
        fr=f"Tâche 10 : le ServiceAccount lecteur existe : {sa is not None}, lié par un RoleBinding de appli : {lie}, "
        f"droits au-delà de la lecture des Pods : {trop or 'aucun'}. Attendu le compte lié, et rien de plus que la "
        "lecture des Pods.",
    )


def test_t11_le_snapshot_etcd_est_valide(host):
    res = _kubectl(host, f"-n kube-system exec etcd-{PLAN} -- etcdutl snapshot status {SNAPSHOT} -w json")
    try:
        statut = json.loads(res.stdout) if res.rc == 0 else {}
    except ValueError:
        statut = {}
    assert statut.get("totalKey", 0) > 0, message(
        en=f"Task 11: {SNAPSHOT} is not a valid etcd snapshot: {res.stderr.strip()[:200] or 'empty status'}.",
        fr=f"Tâche 11 : {SNAPSHOT} n'est pas un snapshot etcd valide : {res.stderr.strip()[:200] or 'statut vide'}.",
    )


def test_t12_la_sauvegarde_quotidienne_existe(host):
    crd = _objet(host, "get crd sauvegardes.examen.formation.k8s")
    cr = _objet(host, "-n appli get sauvegarde quotidienne") or {}
    spec = cr.get("spec") or {}
    ok = _condition(crd, "Established") == "True" and spec.get("source") == "base" and spec.get("retentionJours") == 7
    assert ok, message(
        en=f"Task 12: CRD Established: {_condition(crd, 'Established') or 'absent'}, Sauvegarde quotidienne in appli "
        f"has the spec {spec or 'none'}. Expected the CRD installed and source base, retentionJours 7.",
        fr=f"Tâche 12 : CRD établie : {_condition(crd, 'Established') or 'absente'}, la Sauvegarde quotidienne de "
        f"appli a la spec {spec or 'aucune'}. Attendu la CRD installée, et source base, retentionJours 7.",
    )


def test_t13_l_overlay_prod_est_applique(host):
    dep = _objet(host, "-n prod get deployment inventaire") or {}
    labels = (dep.get("metadata") or {}).get("labels") or {}
    gabarit = ((dep.get("spec") or {}).get("template", {}).get("metadata") or {}).get("labels") or {}
    vu = ((dep.get("spec") or {}).get("replicas"), (dep.get("status") or {}).get("availableReplicas", 0),
          labels.get("env"), gabarit.get("env"))
    assert vu == (3, 3, "prod", "prod"), message(
        en=f"Task 13: inventaire in prod has (replicas, available, env label, env label of its Pods) = {vu}, "
        "expected (3, 3, prod, prod), set by the overlay.",
        fr=f"Tâche 13 : inventaire dans prod a (réplicas, disponibles, label env, label env de ses Pods) = {vu}, "
        "attendu (3, 3, prod, prod), posés par l'overlay.",
    )


# ======================================================================
# Servicing and Networking (20)
# ======================================================================
def _joint_la_base(host, pod: str) -> bool:
    return _kubectl(host, f"-n reseau exec {pod} -- nc -z -w 3 db 5432").rc == 0


def test_t14_seul_front_joint_la_base(host):
    front, autre = _joint_la_base(host, "front"), _joint_la_base(host, "autre")
    assert front and not autre, message(
        en=f"Task 14: on port 5432 of db, front {'gets in' if front else 'is refused'}, autre "
        f"{'gets in' if autre else 'is refused'}. Expected front allowed, autre refused.",
        fr=f"Tâche 14 : sur le port 5432 de db, front {'entre' if front else 'est refusé'}, autre "
        f"{'entre' if autre else 'est refusé'}. Attendu front autorisé, autre refusé.",
    )


def test_t15_l_ingress_boutique_route_l_api(host):
    existe = _objet(host, "-n reseau get ingress boutique") is not None
    corps = _attendre(lambda: _curl_traefik(host, "boutique.examen", "/api"), lambda v: v == "api", existe)
    assert corps == "api", message(
        en=f"Task 15: http://boutique.examen/api answers {corps or 'nothing'!r} instead of \"api\".",
        fr=f"Tâche 15 : http://boutique.examen/api répond {corps or 'rien'!r} au lieu de « api ».",
    )


def test_t16_la_route_du_magasin_sert_le_web(host):
    route = _objet(host, "-n reseau get httproute magasin") or {}
    acceptee = any(c.get("type") == "Accepted" and c.get("status") == "True"
                   for p in (route.get("status") or {}).get("parents") or [] for c in p.get("conditions") or [])
    corps = _attendre(lambda: _curl_traefik(host, "magasin.examen", "/"), lambda v: v == "web", bool(route))
    assert acceptee and corps == "web", message(
        en=f"Task 16: HTTPRoute magasin accepted: {acceptee}, http://magasin.examen/ answers {corps or 'nothing'!r}. "
        "Expected the route accepted by its Gateway, and \"web\".",
        fr=f"Tâche 16 : HTTPRoute magasin acceptée : {acceptee}, http://magasin.examen/ répond {corps or 'rien'!r}. "
        "Attendu la route acceptée par sa Gateway, et « web ».",
    )


def test_t17_accueil_repond_sur_son_nodeport(host):
    svc = _objet(host, "-n reseau get service accueil") or {}
    ports = (svc.get("spec") or {}).get("ports") or [{}]
    genre = (svc.get("spec") or {}).get("type")
    ip = _ip(host, PLAN)

    def mesure() -> str:
        return host.run(f"curl -s --max-time 4 http://{ip}:{NODEPORT}/").stdout.strip()

    corps = _attendre(mesure, lambda v: v == "accueil", bool(svc))
    assert genre == "NodePort" and ports[0].get("nodePort") == NODEPORT and corps == "accueil", message(
        en=f"Task 17: Service accueil is {genre} on NodePort {ports[0].get('nodePort')}, http://{ip}:{NODEPORT}/ "
        f"answers {corps or 'nothing'!r}. Expected a NodePort Service on {NODEPORT} answering accueil.",
        fr=f"Tâche 17 : le Service accueil est {genre} sur le NodePort {ports[0].get('nodePort')}, "
        f"http://{ip}:{NODEPORT}/ répond {corps or 'rien'!r}. Attendu un Service NodePort sur {NODEPORT} qui "
        "répond accueil.",
    )
