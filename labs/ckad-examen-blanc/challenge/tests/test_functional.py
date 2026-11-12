"""test_functional.py : ckad-examen-blanc

Vingt états, un test chacun, à 5 points : la note sur 100 suit les poids
officiels des domaines de la CKAD (Application Design and Build 20, Application
Deployment 20, Application Observability and Maintenance 15, Application
Environment, Configuration and Security 25, Services and Networking 20). Une
tâche de 10 points porte deux états.

Les tests lisent l'état du cluster et des conteneurs, et font de vraies
requêtes. Jamais les commandes tapées. Chaque état est faux au départ.
Les attentes sont courtes et ne s'ouvrent que si l'objet attendu existe déjà.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
NGINX_1306 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
JETON = "jeton-de-demonstration"
PORT_TRAEFIK = 30080
ATTENTE_S = 30
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _objet(host, args: str) -> dict | None:
    res = _kubectl(host, f"{args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _pods(host, ns: str, selecteur: str) -> list[dict]:
    items = (_objet(host, f"-n {ns} get pods -l {selecteur}") or {}).get("items", [])
    return [p for p in items if not p["metadata"].get("deletionTimestamp")]


def _ready(pod: dict | None) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in ((pod or {}).get("status") or {}).get("conditions") or [])


def _conteneur(spec: dict, nom: str | None = None) -> dict:
    conteneurs = spec.get("containers") or []
    if nom is None:
        return conteneurs[0] if conteneurs else {}
    return next((c for c in conteneurs + (spec.get("initContainers") or []) if c.get("name") == nom), {})


def _gabarit(dep: dict | None) -> dict:
    return ((dep or {}).get("spec") or {}).get("template", {}).get("spec", {})


def _exec(host, ns: str, pod: str, commande: str, conteneur: str = "") -> str:
    c = f"-c {conteneur} " if conteneur else ""
    return _kubectl(host, f"-n {ns} exec {pod} {c}-- {commande}").stdout.strip()


# ======================================================================
# Application Design and Build (20)
# ======================================================================
def test_d01_le_cronjob_purge(host):
    cj = _objet(host, "-n atelier get cronjob purge") or {}
    spec = cj.get("spec") or {}
    vu = (spec.get("schedule"), spec.get("successfulJobsHistoryLimit"), spec.get("concurrencyPolicy"))
    assert vu == ("*/10 * * * *", 2, "Forbid"), message(
        en=f"Task 1: CronJob purge has (schedule, successfulJobsHistoryLimit, concurrencyPolicy) = {vu}, expected "
        "('*/10 * * * *', 2, 'Forbid').",
        fr=f"Tâche 1 : le CronJob purge a (schedule, successfulJobsHistoryLimit, concurrencyPolicy) = {vu}, attendu "
        "('*/10 * * * *', 2, 'Forbid').",
    )


def _journal(host) -> dict:
    return _objet(host, "-n atelier get pod journal") or {}


def test_d02a_le_sidecar_partage_le_volume_du_journal(host):
    pod = _journal(host)
    spec = pod.get("spec") or {}
    vides = {v["name"] for v in spec.get("volumes") or [] if "emptyDir" in v}
    def montages(c: dict) -> set[str]:
        return {m["name"] for m in c.get("volumeMounts") or [] if m["name"] in vides}
    app, lecteur = _conteneur(spec, "app"), _conteneur(spec, "lecteur")
    commun = montages(app) & montages(lecteur)
    assert commun and _ready(pod), message(
        en=f"Task 2: Pod journal has containers app and lecteur: {bool(app) and bool(lecteur)}, an emptyDir mounted "
        f"by both: {sorted(commun) or 'none'}, ready: {_ready(pod)}. Expected one emptyDir shared by both, the Pod "
        "ready.",
        fr=f"Tâche 2 : le Pod journal a les conteneurs app et lecteur : {bool(app) and bool(lecteur)}, un emptyDir "
        f"monté par les deux : {sorted(commun) or 'aucun'}, prêt : {_ready(pod)}. Attendu un emptyDir partagé par "
        "les deux, le Pod prêt.",
    )


def test_d02b_le_sidecar_relit_le_journal_de_l_application(host):
    pod = _journal(host)
    sortie = _kubectl(host, "-n atelier logs journal -c lecteur --tail=20").stdout if pod else ""
    if pod and not sortie.strip():
        fin = time.monotonic() + ATTENTE_S
        while not sortie.strip() and time.monotonic() < fin:
            time.sleep(PAS_S)
            sortie = _kubectl(host, "-n atelier logs journal -c lecteur --tail=20").stdout
    fichier = _exec(host, "atelier", "journal", "cat /var/log/app/app.log", "app") if pod else ""
    lignes = [ligne for ligne in sortie.splitlines() if ligne.strip()]
    assert lignes and all(ligne in fichier for ligne in lignes[:3]), message(
        en=f"Task 2: the log of lecteur shows {len(lignes)} line(s), found in /var/log/app/app.log of app: "
        f"{bool(lignes) and all(ligne in fichier for ligne in lignes[:3])}. Expected lecteur to replay the lines app writes.",
        fr=f"Tâche 2 : le journal de lecteur montre {len(lignes)} ligne(s), retrouvées dans /var/log/app/app.log de "
        f"app : {bool(lignes) and all(ligne in fichier for ligne in lignes[:3])}. Attendu que lecteur relise les lignes "
        "qu'écrit app.",
    )


def test_d03_le_pod_stockage_ecrit_dans_cache(host):
    pvc = _objet(host, "-n atelier get pvc cache") or {}
    pod = _objet(host, "-n atelier get pod stockage") or {}
    monte = any((v.get("persistentVolumeClaim") or {}).get("claimName") == "cache"
                for v in (pod.get("spec") or {}).get("volumes") or [])
    contenu = _exec(host, "atelier", "stockage", "cat /cache/ok") if monte else ""
    vu = ((pvc.get("status") or {}).get("phase"), monte, contenu)
    assert vu == ("Bound", True, "ok"), message(
        en=f"Task 3: claim cache is {vu[0]}, Pod stockage mounts it: {vu[1]}, /cache/ok holds {vu[2]!r}. Expected "
        "Bound, mounted, and ok.",
        fr=f"Tâche 3 : la revendication cache est {vu[0]}, le Pod stockage la monte : {vu[1]}, /cache/ok contient "
        f"{vu[2]!r}. Attendu Bound, montée, et ok.",
    )


# ======================================================================
# Application Deployment (20)
# ======================================================================
def test_d04a_la_vitrine_sert_la_version_verte(host):
    svc = _objet(host, "-n boutique get service vitrine") or {}
    selecteur = (svc.get("spec") or {}).get("selector") or {}
    tranches = _objet(host, "-n boutique get endpointslices -l kubernetes.io/service-name=vitrine") or {}
    vises = {(e.get("targetRef") or {}).get("name") for t in tranches.get("items", [])
             for e in t.get("endpoints") or [] if (e.get("conditions") or {}).get("ready")}
    rs_vert = {r["metadata"]["name"] for r in (_objet(host, "-n boutique get replicasets") or {}).get("items", [])
               if any(o.get("name") == "vitrine-vert" for o in r["metadata"].get("ownerReferences") or [])}
    verts = {p["metadata"]["name"] for p in _pods(host, "boutique", "app=vitrine")
             if any(o.get("name") in rs_vert for o in p["metadata"].get("ownerReferences") or [])}
    ok = selecteur.get("version") == "vert" and bool(vises) and vises <= verts
    assert ok, message(
        en=f"Task 4: Service vitrine selects {selecteur} and sends to {sorted(v for v in vises if v) or 'no Pod'}. "
        "Expected the version vert, and only Pods of the vitrine-vert Deployment behind it.",
        fr=f"Tâche 4 : le Service vitrine sélectionne {selecteur} et envoie vers "
        f"{sorted(v for v in vises if v) or 'aucun Pod'}. Attendu la version vert, et seulement des Pods du "
        "Deployment vitrine-vert derrière lui.",
    )


def test_d04b_le_deploiement_vert_tourne_en_1306(host):
    dep = _objet(host, "-n boutique get deployment vitrine-vert") or {}
    image = _conteneur(_gabarit(dep)).get("image")
    dispo = (dep.get("status") or {}).get("availableReplicas", 0)
    assert image == NGINX_1306 and dispo == 3, message(
        en=f"Task 4: vitrine-vert runs {image} with {dispo} available replica(s), expected 1.30.6 with 3.",
        fr=f"Tâche 4 : vitrine-vert lance {image} avec {dispo} réplica(s) disponible(s), attendu 1.30.6 avec 3.",
    )


def test_d05_catalogue_est_mis_a_jour_sans_perte(host):
    dep = _objet(host, "-n boutique get deployment catalogue") or {}
    strat = ((dep.get("spec") or {}).get("strategy") or {}).get("rollingUpdate") or {}
    statut = dep.get("status") or {}
    vu = (str(strat.get("maxSurge")), str(strat.get("maxUnavailable")), _conteneur(_gabarit(dep)).get("image"),
          statut.get("updatedReplicas", 0), statut.get("availableReplicas", 0))
    assert vu == ("1", "0", NGINX_1306, 3, 3), message(
        en=f"Task 5: catalogue has (maxSurge, maxUnavailable, image, updated, available) = {vu}, expected "
        "(1, 0, nginx 1.30.6, 3, 3).",
        fr=f"Tâche 5 : catalogue a (maxSurge, maxUnavailable, image, à jour, disponibles) = {vu}, attendu "
        "(1, 0, nginx 1.30.6, 3, 3).",
    )


def test_d06_l_overlay_de_la_boutique_est_applique(host):
    dep = _objet(host, "-n boutique get deployment panier") or {}
    vu = ((dep.get("spec") or {}).get("replicas"), (dep.get("status") or {}).get("availableReplicas", 0),
          _conteneur(_gabarit(dep)).get("image"))
    assert vu == (2, 2, NGINX_1306), message(
        en=f"Task 6: panier in boutique has (replicas, available, image) = {vu}, expected (2, 2, nginx 1.30.6).",
        fr=f"Tâche 6 : panier dans boutique a (réplicas, disponibles, image) = {vu}, attendu (2, 2, nginx 1.30.6).",
    )


# ======================================================================
# Application Observability and Maintenance (15)
# ======================================================================
def test_d07_les_sondes_de_api(host):
    dep = _objet(host, "-n atelier get deployment api") or {}
    c = _conteneur(_gabarit(dep))
    lecture = (c.get("readinessProbe") or {}).get("httpGet") or {}
    vie = (c.get("livenessProbe") or {}).get("tcpSocket") or {}
    pods = _pods(host, "atelier", "app=api")
    ok = (lecture.get("path") == "/" and str(lecture.get("port")) == "80" and str(vie.get("port")) == "80"
          and len(pods) == 2 and all(_ready(p) for p in pods))
    assert ok, message(
        en=f"Task 7: api has readiness httpGet {lecture or 'none'}, liveness tcpSocket {vie or 'none'}, "
        f"{sum(_ready(p) for p in pods)} ready Pod(s). Expected httpGet / on 80, tcpSocket on 80, two ready Pods.",
        fr=f"Tâche 7 : api a une readiness httpGet {lecture or 'aucune'}, une liveness tcpSocket {vie or 'aucune'}, "
        f"{sum(_ready(p) for p in pods)} Pod(s) prêt(s). Attendu httpGet / sur 80, tcpSocket sur 80, deux Pods prêts.",
    )


def test_d08_le_pdb_est_reecrit_en_policy_v1(host):
    pdb = _objet(host, "-n atelier get poddisruptionbudgets.v1.policy api-pdb") or {}
    spec = pdb.get("spec") or {}
    vu = (pdb.get("apiVersion"), spec.get("minAvailable"), (spec.get("selector") or {}).get("matchLabels"))
    assert vu == ("policy/v1", 1, {"app": "api"}), message(
        en=f"Task 8: PodDisruptionBudget api-pdb reads {vu}, expected policy/v1, minAvailable 1, selector app=api.",
        fr=f"Tâche 8 : le PodDisruptionBudget api-pdb donne {vu}, attendu policy/v1, minAvailable 1, sélecteur app=api.",
    )


def test_d09_outil_tourne_sur_son_image(host):
    pod = _objet(host, "-n atelier get pod outil") or {}
    image = _conteneur(pod.get("spec") or {}).get("image")
    phase = (pod.get("status") or {}).get("phase")
    assert image == BUSYBOX and phase == "Running", message(
        en=f"Task 9: Pod outil asks for {image} and is {phase}, expected the given busybox image and Running.",
        fr=f"Tâche 9 : le Pod outil demande {image} et est {phase}, attendu l'image busybox donnée et Running.",
    )


# ======================================================================
# Application Environment, Configuration and Security (25)
# ======================================================================
def test_d10_la_configuration_arrive_en_fichier(host):
    pod = _objet(host, "-n atelier get pod lecture-config") or {}
    depuis_cm = any((v.get("configMap") or {}).get("name") == "parametres"
                    for v in (pod.get("spec") or {}).get("volumes") or [])
    contenu = _exec(host, "atelier", "lecture-config", "cat /etc/app/app.conf") if depuis_cm else ""
    assert depuis_cm and contenu == "niveau=debug", message(
        en=f"Task 10: lecture-config mounts the ConfigMap parametres: {depuis_cm}, /etc/app/app.conf holds "
        f"{contenu!r}, expected niveau=debug.",
        fr=f"Tâche 10 : lecture-config monte la ConfigMap parametres : {depuis_cm}, /etc/app/app.conf contient "
        f"{contenu!r}, attendu niveau=debug.",
    )


def test_d11_le_jeton_arrive_depuis_le_secret(host):
    pod = _objet(host, "-n atelier get pod lecture-secret") or {}
    env = {e.get("name"): e for e in _conteneur(pod.get("spec") or {}).get("env") or []}
    ref = ((env.get("JETON") or {}).get("valueFrom") or {}).get("secretKeyRef") or {}
    valeur = _exec(host, "atelier", "lecture-secret", "printenv JETON") if ref else ""
    assert ref.get("name") == "jeton" and valeur == JETON, message(
        en=f"Task 11: JETON comes from the Secret {ref.get('name') or 'none'}, the container sees the expected value: "
        f"{valeur == JETON}. Expected the Secret jeton.",
        fr=f"Tâche 11 : JETON vient du Secret {ref.get('name') or 'aucun'}, le conteneur voit la valeur attendue : "
        f"{valeur == JETON}. Attendu le Secret jeton.",
    )


def test_d12_le_pod_durci(host):
    pod = _objet(host, "-n securite get pod durci") or {}
    spec = pod.get("spec") or {}
    c = _conteneur(spec)
    sc = {**(spec.get("securityContext") or {}), **(c.get("securityContext") or {})}
    supprimees = ((c.get("securityContext") or {}).get("capabilities") or {}).get("drop") or []
    uid = _exec(host, "securite", "durci", "id -u") if pod else ""
    ok = (sc.get("runAsNonRoot") is True and sc.get("runAsUser") == 1000 and sc.get("readOnlyRootFilesystem") is True
          and sc.get("allowPrivilegeEscalation") is False and "ALL" in supprimees and uid == "1000")
    assert ok, message(
        en=f"Task 12: durci has runAsNonRoot {sc.get('runAsNonRoot')}, runAsUser {sc.get('runAsUser')}, "
        f"readOnlyRootFilesystem {sc.get('readOnlyRootFilesystem')}, allowPrivilegeEscalation "
        f"{sc.get('allowPrivilegeEscalation')}, dropped capabilities {supprimees}, and runs as uid {uid or 'none'}.",
        fr=f"Tâche 12 : durci a runAsNonRoot {sc.get('runAsNonRoot')}, runAsUser {sc.get('runAsUser')}, "
        f"readOnlyRootFilesystem {sc.get('readOnlyRootFilesystem')}, allowPrivilegeEscalation "
        f"{sc.get('allowPrivilegeEscalation')}, capacités retirées {supprimees}, et tourne sous l'uid {uid or 'aucun'}.",
    )


def test_d13_le_quota_et_le_pod_qui_y_tient(host):
    quota = _objet(host, "-n securite get resourcequota plafond") or {}
    dur = (quota.get("spec") or {}).get("hard") or {}
    pod = _objet(host, "-n securite get pod mesure") or {}
    res = _conteneur(pod.get("spec") or {}).get("resources") or {}
    ok = (dur.get("pods") == "5" and dur.get("limits.cpu") == "2" and dur.get("limits.memory") == "1Gi"
          and (res.get("requests") or {}).get("cpu") == "100m" and (res.get("limits") or {}).get("cpu") == "200m"
          and (pod.get("status") or {}).get("phase") == "Running")
    assert ok, message(
        en=f"Task 13: quota plafond is {dur or 'absent'}, Pod mesure has resources {res or 'none'} and is "
        f"{(pod.get('status') or {}).get('phase')}. Expected pods 5, limits.cpu 2, limits.memory 1Gi, and mesure "
        "Running with requests cpu 100m and limits cpu 200m.",
        fr=f"Tâche 13 : le quota plafond vaut {dur or 'absent'}, le Pod mesure a les ressources {res or 'aucune'} "
        f"et est {(pod.get('status') or {}).get('phase')}. Attendu pods 5, limits.cpu 2, limits.memory 1Gi, et "
        "mesure Running avec requests cpu 100m et limits cpu 200m.",
    )


def test_d14_le_compte_deployeur_sans_jeton_monte(host):
    sa = _objet(host, "-n securite get serviceaccount deployeur") or {}
    pod = _objet(host, "-n securite get pod outil-sa") or {}
    spec = pod.get("spec") or {}
    jeton_monte = any(v.get("projected") and any("serviceAccountToken" in s
                                                  for s in (v.get("projected") or {}).get("sources") or [])
                      for v in spec.get("volumes") or [])
    ok = bool(sa) and spec.get("serviceAccountName") == "deployeur" and not jeton_monte and bool(pod)
    assert ok, message(
        en=f"Task 14: ServiceAccount deployeur exists: {bool(sa)}, Pod outil-sa uses "
        f"{spec.get('serviceAccountName') or 'no account'}, a token is mounted: {jeton_monte}. Expected outil-sa on "
        "deployeur, with no token mounted.",
        fr=f"Tâche 14 : le ServiceAccount deployeur existe : {bool(sa)}, le Pod outil-sa utilise "
        f"{spec.get('serviceAccountName') or 'aucun compte'}, un jeton est monté : {jeton_monte}. Attendu outil-sa "
        "sur deployeur, sans jeton monté.",
    )


# ======================================================================
# Services and Networking (20)
# ======================================================================
def _joint_interne(host, pod: str) -> bool:
    ip = _kubectl(host, "-n boutique get pod interne -o jsonpath='{.status.podIP}'").stdout.strip()
    return bool(ip) and _exec(host, "boutique", pod, f"wget -qO- -T 3 http://{ip}:5678/") == "interne"


def test_d15_seul_front_joint_interne(host):
    front, autre = _joint_interne(host, "front"), _joint_interne(host, "autre")
    assert front and not autre, message(
        en=f"Task 15: front {'reaches' if front else 'does not reach'} interne, autre "
        f"{'reaches' if autre else 'does not reach'} it. Expected front allowed, autre refused.",
        fr=f"Tâche 15 : front {'joint' if front else 'ne joint pas'} interne, autre "
        f"{'le joint' if autre else 'ne le joint pas'}. Attendu front autorisé, autre refusé.",
    )


def test_d16a_le_service_stock_a_ses_endpoints(host):
    tranches = _objet(host, "-n boutique get endpointslices -l kubernetes.io/service-name=stock") or {}
    vises, ports = set(), set()
    for t in tranches.get("items", []):
        vises |= {(e.get("targetRef") or {}).get("name") for e in t.get("endpoints") or []
                  if (e.get("conditions") or {}).get("ready")}
        ports |= {p.get("port") for p in t.get("ports") or []}
    pods = {p["metadata"]["name"] for p in _pods(host, "boutique", "app=stock")}
    assert pods and vises == pods and ports == {5678}, message(
        en=f"Task 16: Service stock sends to {sorted(v for v in vises if v) or 'no Pod'} on port(s) "
        f"{sorted(p for p in ports if p) or 'none'}, expected the stock Pods on the port their container listens on.",
        fr=f"Tâche 16 : le Service stock envoie vers {sorted(v for v in vises if v) or 'aucun Pod'} sur le(s) port(s) "
        f"{sorted(p for p in ports if p) or 'aucun'}, attendu les Pods de stock sur le port où leur conteneur écoute.",
    )


def test_d16b_front_joint_stock_par_son_nom(host):
    corps = _exec(host, "boutique", "front", "wget -qO- -T 3 http://stock/")
    assert corps == "stock", message(
        en=f"Task 16: from the Pod front, http://stock/ answers {corps or 'nothing'!r} instead of \"stock\".",
        fr=f"Tâche 16 : depuis le Pod front, http://stock/ répond {corps or 'rien'!r} au lieu de « stock ».",
    )


def test_d17_l_ingress_infos_route(host):
    existe = _objet(host, "-n boutique get ingress infos") is not None
    def mesure() -> str:
        return host.run(f"curl -s --max-time 5 --resolve infos.examen:{PORT_TRAEFIK}:127.0.0.1 "
                        f"http://infos.examen:{PORT_TRAEFIK}/infos").stdout.strip()
    corps = mesure()
    if corps != "infos" and existe:
        fin = time.monotonic() + ATTENTE_S
        while corps != "infos" and time.monotonic() < fin:
            time.sleep(PAS_S)
            corps = mesure()
    assert corps == "infos", message(
        en=f"Task 17: http://infos.examen/infos answers {corps or 'nothing'!r} instead of \"infos\".",
        fr=f"Tâche 17 : http://infos.examen/infos répond {corps or 'rien'!r} au lieu de « infos ».",
    )
