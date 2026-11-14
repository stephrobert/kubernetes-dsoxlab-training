"""test_functional.py : cks-examen-blanc

Vingt états, un test chacun, à 5 points : la note sur 100 suit donc les poids
officiels des domaines de la CKS v1.37 (Cluster Setup 15, Cluster Hardening 15,
System Hardening 10, Minimize Microservice Vulnerabilities 20, Supply Chain
Security 20, Monitoring, Logging and Runtime Security 20). Une tâche de 10
points porte deux états.

Les tests lisent l'état du cluster et des nœuds, et font de vraies requêtes :
connexions entre Pods, écritures refusées dans un conteneur, audit kube-bench
rejoué, analyse trivy rejouée, signature vérifiée, journal d'audit relu. Jamais
les commandes tapées. Chaque état est faux au départ : la préparation pose une
faille ou laisse l'objet à créer.

Les attentes sont courtes et ne s'ouvrent que si l'objet attendu existe déjà :
dsoxlab accorde 300 s à toute la suite.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
PLAN = "k8s-cp.lab"
WORKER = "k8s-w1.lab"
MANIFESTES = "/etc/kubernetes/manifests"
COMPOSANTS = ("kube-apiserver", "kube-controller-manager", "kube-scheduler")
JOB_KUBE_BENCH = "/var/lib/dsoxlab/cks-examen/kube-bench-job.yaml"
HOTE_TLS = "vitrine.lab"
PORT_TLS = 30443
CERT_PAR_DEFAUT = "TRAEFIK DEFAULT CERT"
PROFIL_APPARMOR = "k8s-refuser-ecriture"
PROFIL_SECCOMP = "profiles/restrict-chmod.json"
CLE_API = "cle-de-demonstration-7f3a"
SONDE_TAG = "busybox:1.38.0"
SONDE_DIGEST = "busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
IMAGE_SIGNEE = "localhost:5000/appli/web:1.0"
IMAGE_NUE = "localhost:5000/appli/outil:1.0"
CONSTATS_DOCKERFILE = {
    "DS-0001": "tag latest / latest tag",
    "DS-0002": "root user / utilisateur root",
    "DS-0004": "port 22 exposed / port 22 exposé",
    "DS-0026": "no HEALTHCHECK / aucun HEALTHCHECK",
    "DS-0029": "apt-get without --no-install-recommends / apt-get sans --no-install-recommends",
}
JOURNAL_AUDIT = "/var/log/kubernetes/audit.log"
SECRET_AUDITE = "dossier-medical"  # noqa: S105 - nom d'un Secret, pas un mot de passe
PROCESSUS_SUSPECT = "kdevtmpfsi"
ATELIERS = ("atelier-1", "atelier-2", "atelier-3", "atelier-4")
JETON = "/var/run/secrets/kubernetes.io/serviceaccount"
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
    items = (_objet(host, f"-n {ns} get pods -l {selecteur}") or {}).get("items", [])
    return [p for p in items if not p["metadata"].get("deletionTimestamp")]


def _ready(pod: dict | None) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in ((pod or {}).get("status") or {}).get("conditions") or [])


def _gabarit(dep: dict | None) -> dict:
    return (((dep or {}).get("spec") or {}).get("template") or {}).get("spec") or {}


def _attendre(mesure, juste, existe: bool):
    valeur = mesure()
    if not juste(valeur) and existe:
        fin = time.monotonic() + ATTENTE_S
        while not juste(valeur) and time.monotonic() < fin:
            time.sleep(PAS_S)
            valeur = mesure()
    return valeur


def _exec(host, ns: str, pod: str, commande: str):
    return _kubectl(host, f"-n {ns} exec {pod} --request-timeout=30s -- sh -c '{commande}'")


def _peut(host, question: str, sujet: str, namespace: str | None) -> bool:
    portee = f"-n {namespace}" if namespace else "--all-namespaces"
    return _kubectl(host, f"auth can-i {question} {portee} --as={sujet}").stdout.strip() == "yes"


# ======================================================================
# Cluster Setup (15)
# ======================================================================
def _joint(host, depuis: str, vers: str) -> bool:
    ip = _kubectl(host, f"-n zone get pod {vers} -o jsonpath='{{.status.podIP}}'").stdout.strip()
    if not ip:
        return False
    return _exec(host, "zone", depuis, f"wget -q -O /dev/null -T 4 http://{ip}/").rc == 0


def test_t01_seul_le_flux_prevu_passe_dans_zone(host):
    # L'intrus d'abord : avant le travail il entre, et le test s'arrête là sans
    # payer les délais des flux bloqués.
    intrus = _joint(host, "intrus", "db")
    vu = {"intrus -> db": intrus}
    if not intrus:
        vu["web -> db"] = _joint(host, "web", "db")
        vu["web -> annuaire"] = _joint(host, "web", "annuaire")
        vu["db -> annuaire"] = _joint(host, "db", "annuaire")
        vu["web DNS"] = _exec(host, "zone", "web", "nslookup kubernetes.default.svc.cluster.local").rc == 0
    attendu = {"intrus -> db": False, "web -> db": True, "web -> annuaire": False,
               "db -> annuaire": False, "web DNS": True}
    assert vu == attendu, message(
        en=f"Task 1: in zone, measured {vu}, expected {attendu}. Everything closed by default in both "
        "directions, then only web to db on port 80, and name resolution kept.",
        fr=f"Tâche 1 : dans zone, mesuré {vu}, attendu {attendu}. Tout fermé par défaut dans les deux sens, "
        "puis seulement web vers db sur le port 80, et la résolution de noms gardée.",
    )


def _certificat_presente(host) -> str:
    return host.run(
        f"echo | openssl s_client -connect 127.0.0.1:{PORT_TLS} -servername {HOTE_TLS} 2>/dev/null "
        "| openssl x509 -noout -subject -ext subjectAltName"
    ).stdout.strip()


def test_t02_le_site_sert_en_https_avec_son_certificat(host):
    ing = _objet(host, "-n vitrine get ingress site") or {}
    declares = [t.get("secretName") for t in (ing.get("spec") or {}).get("tls") or []
                if HOTE_TLS in (t.get("hosts") or [])]
    secrets = {s["metadata"]["name"]: s for s in (_objet(host, "-n vitrine get secrets") or {}).get("items", [])
               if s.get("type") == "kubernetes.io/tls"}
    retenu = next((n for n in declares if n in secrets), "")
    sujet = _attendre(lambda: _certificat_presente(host),
                      lambda v: f"DNS:{HOTE_TLS}" in v and CERT_PAR_DEFAUT not in v, bool(retenu))
    code = ""
    if retenu and f"DNS:{HOTE_TLS}" in sujet:
        crt = secrets[retenu]["data"].get("tls.crt", "")
        try:
            base64.b64decode(crt, validate=True)
        except ValueError:
            crt = ""
        chemin = "/tmp/dsoxlab-cks-examen-tls.crt"  # noqa: S108 - fichier jetable du test, sur le nœud
        host.run(f"echo {crt} | base64 -d > {chemin}")

        def requete() -> str:
            return host.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' --cacert {chemin} "
                f"--resolve {HOTE_TLS}:{PORT_TLS}:127.0.0.1 https://{HOTE_TLS}:{PORT_TLS}/ --max-time 10"
            ).stdout.strip()

        code = _attendre(requete, lambda v: v == "200", True)
        host.run(f"rm -f {chemin}")
    assert retenu and code == "200", message(
        en=f"Task 2: the Ingress site declares TLS for {HOTE_TLS} with {declares or 'no Secret'} (TLS Secrets "
        f"of vitrine: {sorted(secrets) or 'none'}), the server presents {sujet or 'nothing'!r}, a client trusting "
        f"that certificate gets {code or 'no answer'!r}. Expected a kubernetes.io/tls Secret declared by the "
        f"Ingress, a certificate whose subjectAltName names {HOTE_TLS}, and 200.",
        fr=f"Tâche 2 : l'Ingress site déclare le TLS de {HOTE_TLS} avec {declares or 'aucun Secret'} (Secrets TLS "
        f"de vitrine : {sorted(secrets) or 'aucun'}), le serveur présente {sujet or 'rien'!r}, un client qui fait "
        f"confiance à ce certificat obtient {code or 'aucune réponse'!r}. Attendu un Secret kubernetes.io/tls "
        f"déclaré par l'Ingress, un certificat dont le subjectAltName nomme {HOTE_TLS}, et 200.",
    )


def _audit_kube_bench(host) -> dict:
    _kubectl(host, "-n conformite delete job kube-bench --ignore-not-found --wait=true --timeout=60s")
    if _kubectl(host, f"apply -f {JOB_KUBE_BENCH}").rc != 0:
        return {}
    if _kubectl(host, "-n conformite wait --for=condition=complete job/kube-bench --timeout=180s").rc != 0:
        return {}
    journal = _kubectl(host, "-n conformite logs job/kube-bench").stdout
    debut = journal.find("{")
    try:
        return json.loads(journal[debut:]) if debut >= 0 else {}
    except ValueError:
        return {}


def test_t03_l_audit_cis_rejoue_ne_reproche_plus_le_profilage(host):
    # Garde rapide : sans aucun manifeste corrigé, rejouer l'audit coûterait
    # une minute pour un verdict connu.
    corriges = [c for c in COMPOSANTS
                if "--profiling=false" in host.run(f"sudo cat {MANIFESTES}/{c}.yaml").stdout]
    controles: dict[str, str] = {}
    phases = ""
    if corriges:
        for _ in range(20):
            phases = _kubectl(host, "-n kube-system get pods -l tier=control-plane "
                              "-o jsonpath='{.items[*].status.phase}'").stdout.strip()
            if phases and "Pending" not in phases:
                break
            time.sleep(PAS_S)
        rapport = _audit_kube_bench(host)
        controles = {
            f"{r.get('test_number')} {r.get('test_desc', '')[:60]}": str(r.get("status"))
            for c in rapport.get("Controls") or [] for g in c.get("tests") or []
            for r in g.get("results") or [] if "profiling" in str(r.get("test_desc", "")).lower()
        }
    echecs = {k: v for k, v in controles.items() if v != "PASS"}
    assert len(controles) >= 3 and not echecs and "Pending" not in phases, message(
        en=f"Task 3: manifests carrying --profiling=false: {corriges or 'none'}; the replayed kube-bench audit "
        f"reports the profiling checks {controles or 'not measured'}; control plane phases {phases or 'unread'}. "
        "Expected the three profiling checks (API server, controller manager, scheduler) at PASS, the control "
        "plane Running.",
        fr=f"Tâche 3 : manifestes qui portent --profiling=false : {corriges or 'aucun'} ; l'audit kube-bench "
        f"rejoué rend les contrôles de profilage {controles or 'non mesurés'} ; phases du plan de contrôle "
        f"{phases or 'illisibles'}. Attendu les trois contrôles de profilage (API server, controller manager, "
        "scheduler) à PASS, le plan de contrôle Running.",
    )


# ======================================================================
# Cluster Hardening (15)
# ======================================================================
DEV_SA = "system:serviceaccount:equipe-dev:dev-sa"


def test_t04a_dev_sa_garde_son_travail_sans_etre_administrateur(host):
    admin = _peut(host, "'*' '*'", DEV_SA, None)
    vu = {"admin": admin}
    if not admin:
        vu.update({
            "list nodes": _peut(host, "list nodes", DEV_SA, None),
            "list pods kube-system": _peut(host, "list pods", DEV_SA, "kube-system"),
            "list pods equipe-dev": _peut(host, "list pods", DEV_SA, "equipe-dev"),
            "create deployments equipe-dev": _peut(host, "create deployments", DEV_SA, "equipe-dev"),
            "list services equipe-dev": _peut(host, "list services", DEV_SA, "equipe-dev"),
        })
    attendu = {"admin": False, "list nodes": False, "list pods kube-system": False,
               "list pods equipe-dev": True, "create deployments equipe-dev": True,
               "list services equipe-dev": True}
    assert vu == attendu, message(
        en=f"Task 4: the API server answers for dev-sa {vu}, expected {attendu}. Cluster admin taken back, the "
        "rights on Pods, Deployments and Services of equipe-dev kept.",
        fr=f"Tâche 4 : l'API server répond pour dev-sa {vu}, attendu {attendu}. Le droit d'administrer le cluster "
        "repris, les droits sur les Pods, Deployments et Services de equipe-dev gardés.",
    )


def test_t04b_dev_sa_ne_lit_plus_les_secrets_et_son_droit_vit_dans_le_namespace(host):
    lit = _peut(host, "get secrets", DEV_SA, "equipe-dev")
    liaisons = (_objet(host, "-n equipe-dev get rolebindings") or {}).get("items", [])
    lie = any(s.get("kind") == "ServiceAccount" and s.get("name") == "dev-sa"
              for b in liaisons for s in b.get("subjects") or [])
    crb = _objet(host, "get clusterrolebinding dev-admin-binding") is not None
    assert not lit and lie and not crb, message(
        en=f"Task 4: dev-sa can read the Secrets of equipe-dev: {lit}, a RoleBinding of equipe-dev binds it: "
        f"{lie}, the ClusterRoleBinding dev-admin-binding still exists: {crb}. Expected no Secret read, a "
        "RoleBinding in the namespace, and the shortcut gone.",
        fr=f"Tâche 4 : dev-sa peut lire les Secrets de equipe-dev : {lit}, un RoleBinding de equipe-dev le lie : "
        f"{lie}, le ClusterRoleBinding dev-admin-binding existe encore : {crb}. Attendu aucune lecture de Secret, "
        "un RoleBinding dans le namespace, et le raccourci supprimé.",
    )


def test_t05_releveur_tourne_sans_jeton_d_api(host):
    sa = _objet(host, "-n releves get serviceaccount releveur") or {}
    defaut = _objet(host, "-n releves get serviceaccount default") or {}

    def mesure() -> tuple:
        dep = _objet(host, "-n releves get deployment releveur")
        compte = _gabarit(dep).get("serviceAccountName")
        pods = [p for p in _pods(host, "releves", "app=releveur") if _ready(p)]
        bons = [p for p in pods if (p.get("spec") or {}).get("serviceAccountName") == "releveur"]
        sans_jeton = bool(bons) and len(bons) == len(pods) and all(
            _exec(host, "releves", p["metadata"]["name"], f"ls {JETON}").rc != 0 for p in bons)
        return compte, len(bons), sans_jeton

    compte, nombre, sans_jeton = _attendre(mesure, lambda v: v[0] == "releveur" and v[2], bool(sa))
    vu = (sa.get("automountServiceAccountToken"), defaut.get("automountServiceAccountToken"), compte, sans_jeton)
    assert vu == (False, False, "releveur", True), message(
        en=f"Task 5: (automount of releveur, automount of default, account of the Deployment, Pods without a "
        f"token) = {vu}, over {nombre} ready Pod(s) on releveur. Expected (False, False, releveur, True).",
        fr=f"Tâche 5 : (montage auto de releveur, montage auto de default, compte du Deployment, Pods sans jeton) "
        f"= {vu}, sur {nombre} Pod(s) prêt(s) sous releveur. Attendu (False, False, releveur, True).",
    )


# ======================================================================
# System Hardening (10)
# ======================================================================
def test_t06_confine_est_tenu_par_apparmor_sur_le_worker(host, worker):
    res = worker.run("sudo aa-status --json")
    try:
        mode = (json.loads(res.stdout).get("profiles") or {}).get(PROFIL_APPARMOR, "") if res.rc == 0 else ""
    except ValueError:
        mode = ""
    pod = _objet(host, "-n confinement get pod confine") or {}
    spec = pod.get("spec") or {}
    profils = [(ctx.get("appArmorProfile") or {}) for ctx in
               [spec.get("securityContext") or {}] + [c.get("securityContext") or {} for c in spec.get("containers") or []]]
    declare = any(p.get("type") == "Localhost" and p.get("localhostProfile") == PROFIL_APPARMOR for p in profils)
    noeud = spec.get("nodeName", "")
    ecrit = lit = None
    if _ready(pod):
        ecrit = "CODE=0" in _exec(host, "confinement", "confine", "echo x > /tmp/preuve 2>/dev/null; echo CODE=$?").stdout
        lit = "CODE=0" in _exec(host, "confinement", "confine", "cat /etc/hostname >/dev/null; echo CODE=$?").stdout
    vu = (mode, noeud, declare, ecrit, lit)
    assert vu == ("enforce", WORKER, True, False, True), message(
        en=f"Task 6: (profile mode on {WORKER}, node of confine, profile declared in its securityContext, write "
        f"to /tmp allowed, read allowed) = {vu}. Expected (enforce, {WORKER}, True, False, True).",
        fr=f"Tâche 6 : (mode du profil sur {WORKER}, nœud de confine, profil déclaré dans son securityContext, "
        f"écriture dans /tmp permise, lecture permise) = {vu}. Attendu (enforce, {WORKER}, True, False, True).",
    )


def test_t07_seccomp_refuse_chmod_au_seul_pod_vise(host):
    pod = _objet(host, "-n confinement get pod seccomp-pod") or {}
    spec = pod.get("spec") or {}
    profils = [(ctx.get("seccompProfile") or {}) for ctx in
               [spec.get("securityContext") or {}] + [c.get("securityContext") or {} for c in spec.get("containers") or []]]
    declare = any(p.get("type") == "Localhost" and p.get("localhostProfile") == PROFIL_SECCOMP for p in profils)
    cree = refuse = temoin = None
    if _ready(pod):
        cree = _exec(host, "confinement", "seccomp-pod", "touch /tmp/preuve && echo ok").stdout.strip() == "ok"
        res = _exec(host, "confinement", "seccomp-pod", "chmod 700 /tmp/preuve 2>&1; echo CODE=$?")
        refuse = "CODE=0" not in res.stdout and "not permitted" in res.stdout.lower()
        temoin = _exec(host, "confinement", "temoin",
                       "touch /tmp/t && chmod 700 /tmp/t && echo ok").stdout.strip() == "ok"
    vu = (spec.get("nodeName", ""), declare, cree, refuse, temoin)
    assert vu == (PLAN, True, True, True, True), message(
        en=f"Task 7: (node of seccomp-pod, Localhost profile {PROFIL_SECCOMP} declared, file creation works, "
        f"chmod refused with EPERM, witness still allowed chmod) = {vu}. Expected ({PLAN}, True, True, True, True).",
        fr=f"Tâche 7 : (nœud de seccomp-pod, profil Localhost {PROFIL_SECCOMP} déclaré, création de fichier "
        f"permise, chmod refusé par EPERM, témoin toujours autorisé à chmod) = {vu}. Attendu ({PLAN}, True, True, "
        "True, True).",
    )


# ======================================================================
# Minimize Microservice Vulnerabilities (20)
# ======================================================================
POD_INTERDIT = """apiVersion: v1
kind: Pod
metadata:
  name: sonde-interdite
  namespace: durci
spec:
  hostPID: true
  containers:
    - name: outil
      image: busybox:1.38.0
      securityContext:
        runAsUser: 0
"""

POD_ACCEPTABLE = """apiVersion: v1
kind: Pod
metadata:
  name: sonde-conforme
  namespace: durci
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: outil
      image: busybox:1.38.0
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
"""


def _soumettre(host, manifeste: str) -> tuple[bool, str]:
    chemin = host.run("mktemp /tmp/dsoxlab-sonde-psa.XXXXXX.yaml").stdout.strip()
    host.run(f"cat > {chemin} <<'MANIFESTE'\n{manifeste}MANIFESTE")
    res = _kubectl(host, f"apply --dry-run=server -f {chemin}")
    host.run(f"rm -f {chemin}")
    return res.rc == 0, res.stderr.strip()


def test_t08a_durci_refuse_a_l_admission_ce_que_restricted_interdit(host):
    labels = ((_objet(host, "get namespace durci") or {}).get("metadata") or {}).get("labels") or {}
    modes = {m: labels.get(f"pod-security.kubernetes.io/{m}") for m in ("enforce", "warn", "audit")}
    refuse = accepte = None
    reponse = ""
    if modes["enforce"]:
        accepte_interdit, reponse = _soumettre(host, POD_INTERDIT)
        refuse = not accepte_interdit and ("PodSecurity" in reponse or "violate" in reponse)
        accepte = _soumettre(host, POD_ACCEPTABLE)[0]
    attendu = {"enforce": "restricted", "warn": "restricted", "audit": "restricted"}
    assert modes == attendu and refuse and accepte, message(
        en=f"Task 8: the labels of durci give {modes}, a privileged Pod refused by Pod Security Admission: "
        f"{refuse}, a compliant Pod accepted: {accepte}. Expected restricted in all three modes, the first "
        "refused, the second accepted.",
        fr=f"Tâche 8 : les labels de durci donnent {modes}, un Pod privilégié refusé par Pod Security Admission : "
        f"{refuse}, un Pod conforme accepté : {accepte}. Attendu restricted dans les trois modes, le premier "
        "refusé, le second accepté.",
    )


def test_t08b_le_pod_conforme_tourne_sous_restricted(host):
    pod = _objet(host, "-n durci get pod conforme") or {}
    spec = pod.get("spec") or {}
    ctx_pod = spec.get("securityContext") or {}
    ctx = ((spec.get("containers") or [{}])[0].get("securityContext")) or {}
    seccomp = (ctx_pod.get("seccompProfile") or ctx.get("seccompProfile") or {}).get("type")
    vu = {
        "Running": (pod.get("status") or {}).get("phase") == "Running",
        "runAsNonRoot": bool(ctx_pod.get("runAsNonRoot") or ctx.get("runAsNonRoot")),
        "allowPrivilegeEscalation=false": ctx.get("allowPrivilegeEscalation") is False,
        "drop ALL": "ALL" in ((ctx.get("capabilities") or {}).get("drop") or []),
        "seccomp": seccomp in ("RuntimeDefault", "Localhost"),
    }
    vu_en = f"gives {vu}" if pod else "does not exist"
    vu_fr = f"donne {vu}" if pod else "n'existe pas"
    assert pod and all(vu.values()), message(
        en=f"Task 8: the Pod conforme in durci {vu_en}. Expected it Running, non-root, without privilege "
        "escalation, every capability dropped, and a seccomp profile.",
        fr=f"Tâche 8 : le Pod conforme de durci {vu_fr}. Attendu qu'il tourne, en non-root, sans escalade de "
        "privilèges, toutes les capabilities retirées, et un profil seccomp.",
    )


def test_t09_secure_app_remplace_insecure_app_sans_ses_defauts(host):
    fautif = _objet(host, "-n production get pod insecure-app") is not None
    pod = _objet(host, "-n production get pod secure-app") or {}
    spec = pod.get("spec") or {}
    ctx_pod = spec.get("securityContext") or {}
    conteneur = (spec.get("containers") or [{}])[0]
    ctx = conteneur.get("securityContext") or {}
    image = conteneur.get("image", "")
    identites = [ctx_pod.get("runAsUser"), ctx.get("runAsUser")]
    restants = []
    if not pod:
        restants.append("secure-app absent")
    else:
        if spec.get("hostPID") or spec.get("hostNetwork") or spec.get("hostIPC"):
            restants.append("host namespaces")
        if ctx.get("privileged"):
            restants.append("privileged")
        if ctx.get("allowPrivilegeEscalation") is not False:
            restants.append("allowPrivilegeEscalation")
        if 0 in identites or not any(identites):
            restants.append("runAsUser")
        if "ALL" not in ((ctx.get("capabilities") or {}).get("drop") or []):
            restants.append("capabilities")
        if image.endswith(":latest") or (":" not in image.rsplit("/", 1)[-1] and "@" not in image):
            restants.append(f"image {image}")
        if _ready(pod):
            processus = _exec(host, "production", "secure-app", "ps -eo pid | wc -l").stdout.strip()
            uid = _exec(host, "production", "secure-app", "id -u").stdout.strip()
            if not processus.isdigit() or int(processus) > 30:
                restants.append(f"sees {processus or '?'} processes")
            if uid in ("", "0"):
                restants.append(f"uid {uid or '?'}")
        else:
            restants.append("not ready")
    if fautif:
        restants.append("insecure-app still exists")
    assert not restants, message(
        en=f"Task 9: what remains wrong: {', '.join(restants)}. Expected secure-app running without host "
        "namespaces, privilege, escalation, root user, capabilities nor floating tag, and insecure-app deleted.",
        fr=f"Tâche 9 : ce qui reste faux : {', '.join(restants)}. Attendu secure-app qui tourne sans namespace de "
        "l'hôte, ni privilège, ni escalade, ni root, ni capability, ni tag flottant, et insecure-app supprimé.",
    )


def test_t10_la_cle_d_api_arrive_par_un_secret_en_fichier(host):
    secret = _objet(host, "-n tresor get secret cle-api") or {}
    valeur = ""
    try:
        valeur = base64.b64decode(((secret.get("data") or {}).get("cle")) or "").decode()
    except ValueError:
        valeur = ""

    def mesure() -> dict:
        gabarit = _gabarit(_objet(host, "-n tresor get deployment facturation"))
        conteneur = (gabarit.get("containers") or [{}])[0]
        en_clair = any(CLE_API in str(e.get("value", "")) or e.get("name") == "CLE_API"
                       for e in conteneur.get("env") or [])
        volumes = {v.get("name") for v in gabarit.get("volumes") or []
                   if (v.get("secret") or {}).get("secretName") == "cle-api"}
        monte = any(m.get("name") in volumes and m.get("mountPath", "").rstrip("/") == "/etc/tresor"
                    and m.get("readOnly") is True for m in conteneur.get("volumeMounts") or [])
        pods = [p for p in _pods(host, "tresor", "app=facturation") if _ready(p)]
        fichier = env = None
        if pods:
            nom = pods[0]["metadata"]["name"]
            fichier = _exec(host, "tresor", nom, "cat /etc/tresor/cle").stdout.strip() == CLE_API
            env = _exec(host, "tresor", nom, "printenv CLE_API").stdout.strip() != ""
        return {"secret": valeur == CLE_API, "no literal env": not en_clair, "read-only mount": monte,
                "file": fichier, "env still set": env}

    attendu = {"secret": True, "no literal env": True, "read-only mount": True, "file": True,
               "env still set": False}
    vu = _attendre(mesure, lambda v: v == attendu, bool(secret))
    assert vu == attendu, message(
        en=f"Task 10: measured {vu}, expected {attendu}. The key in the Secret cle-api, given to the container "
        "as the read-only file /etc/tresor/cle, and no environment variable carrying it any more.",
        fr=f"Tâche 10 : mesuré {vu}, attendu {attendu}. La clé dans le Secret cle-api, remise au conteneur comme "
        "fichier en lecture seule /etc/tresor/cle, et plus aucune variable d'environnement qui la porte.",
    )


# ======================================================================
# Supply Chain Security (20)
# ======================================================================
def _digest(reference: str) -> str:
    return reference.split("@")[-1] if "@" in reference else ""


def test_t11a_pinned_app_tourne_sur_le_digest_de_nginx_1305(host):
    def mesure() -> tuple:
        dep = _objet(host, "-n chaine get deployment pinned-app") or {}
        image = (_gabarit(dep).get("containers") or [{}])[0].get("image", "")
        depot = image.split("@")[0]
        forme = bool(_digest(image)) and ":" not in depot.rsplit("/", 1)[-1] and depot.rsplit("/", 1)[-1] == "nginx"
        pods = [p for p in _pods(host, "chaine", "app=pinned-app") if _ready(p)]
        resolus = {_digest((p.get("status") or {}).get("containerStatuses", [{}])[0].get("imageID", ""))
                   for p in pods}
        version = ""
        if pods:
            version = _exec(host, "chaine", pods[0]["metadata"]["name"], "nginx -v 2>&1").stdout.strip()
        return image, forme, len(pods), resolus == {_digest(image)}, "nginx/1.30.5" in version

    declare = (_gabarit(_objet(host, "-n chaine get deployment pinned-app")).get("containers") or [{}])[0]
    image, forme, prets, coincide, version = _attendre(
        mesure, lambda v: v[1] and v[2] == 2 and v[3] and v[4], bool(_digest(declare.get("image", ""))))
    assert forme and prets == 2 and coincide and version, message(
        en=f"Task 11: pinned-app declares {image!r} (nginx by digest only: {forme}), {prets} ready Pod(s), the "
        f"digest is the one they run: {coincide}, they serve nginx 1.30.5: {version}. Expected nginx@sha256:..., "
        "two ready Pods running that very digest, still 1.30.5.",
        fr=f"Tâche 11 : pinned-app déclare {image!r} (nginx par digest seul : {forme}), {prets} Pod(s) prêt(s), le "
        f"digest est celui qu'ils exécutent : {coincide}, ils servent nginx 1.30.5 : {version}. Attendu "
        "nginx@sha256:..., deux Pods prêts sur ce digest, toujours en 1.30.5.",
    )


def _tenter(host, ns: str, image: str) -> tuple[bool, str]:
    res = _kubectl(host, f"-n {ns} run sonde-image --image={image} --restart=Never --dry-run=server -o name "
                   "--command -- sleep 5")
    return res.rc == 0, res.stderr.strip()


def test_t11b_chaine_refuse_toute_image_non_epinglee(host):
    liaisons = (_objet(host, "get validatingadmissionpolicybinding") or {}).get("items", [])
    refusante = any("Deny" in (b.get("spec") or {}).get("validationActions") or []
                    for b in liaisons if not b["metadata"]["name"].startswith("safe-upgrades"))
    tag_passe, refus = _attendre(lambda: _tenter(host, "chaine", SONDE_TAG), lambda v: not v[0], refusante)
    par_politique = "validatingadmissionpolicy" in refus.lower() or "denied request" in refus.lower()
    digest_passe = _tenter(host, "chaine", SONDE_DIGEST)[0]
    ailleurs = _tenter(host, "default", SONDE_TAG)[0]
    vu = (tag_passe, par_politique, digest_passe, ailleurs)
    assert vu == (False, True, True, True), message(
        en=f"Task 11: in chaine, an image by tag accepted: {tag_passe} (refused by an admission policy: "
        f"{par_politique}), an image by digest accepted: {digest_passe}; in default, an image by tag accepted: "
        f"{ailleurs}. Expected the tag refused by a ValidatingAdmissionPolicy in chaine only, the digest accepted.",
        fr=f"Tâche 11 : dans chaine, une image par tag acceptée : {tag_passe} (refusée par une politique "
        f"d'admission : {par_politique}), une image par digest acceptée : {digest_passe} ; dans default, une image "
        f"par tag acceptée : {ailleurs}. Attendu le tag refusé par une ValidatingAdmissionPolicy dans chaine "
        "seulement, le digest accepté.",
    )


def test_t12_le_dockerfile_d_inventaire_passe_l_analyse(host):
    repertoire = f"{_maison(host)}/examen/inventaire"
    contenu = host.run(f"sudo cat {repertoire}/Dockerfile").stdout
    restants: set[str] = set(CONSTATS_DOCKERFILE)
    if contenu.strip():
        res = host.run(f"sudo trivy config --quiet --format json {repertoire} 2>/dev/null")
        if res.rc == 0 and res.stdout.strip():
            rapport = json.loads(res.stdout)
            trouves = {str(m.get("ID")) for r in rapport.get("Results") or []
                       for m in r.get("Misconfigurations") or []}
            restants = trouves & set(CONSTATS_DOCKERFILE)
    meme_appli = "node" in contenu.lower() and "server.js" in contenu
    assert meme_appli and not restants, message(
        en=f"Task 12: the Dockerfile still starts from Node and runs server.js: {meme_appli}; trivy config still "
        f"reports {sorted(restants) or 'none of the five'} "
        f"({', '.join(CONSTATS_DOCKERFILE[i].split(' / ')[0] for i in sorted(restants))}).",
        fr=f"Tâche 12 : le Dockerfile part toujours de Node et lance server.js : {meme_appli} ; trivy config "
        f"reproche encore {sorted(restants) or 'aucun des cinq'} "
        f"({', '.join(CONSTATS_DOCKERFILE[i].split(' / ')[1] for i in sorted(restants))}).",
    )


def _verifie(host, cle: str, image: str) -> bool:
    res = host.run(f"sudo cosign verify --key {cle} {image} >/dev/null 2>&1; echo CODE=$?")
    return res.stdout.strip().endswith("CODE=0")


def test_t13_la_cle_publiee_valide_web_et_refuse_outil(host):
    cm = _objet(host, "-n chaine-signature get configmap cosign-pub-key") or {}
    donnees = cm.get("data") or {}
    publique = donnees.get("cosign.pub", "")
    privee = any("PRIVATE KEY" in str(v) for v in donnees.values())
    signee = nue = None
    if "BEGIN PUBLIC KEY" in publique:
        cle = "/tmp/dsoxlab-cks-examen-cosign.pub"  # noqa: S108 - fichier jetable du test, sur le nœud
        host.run(f"sudo {KUBECTL} -n chaine-signature get configmap cosign-pub-key "
                 f"-o jsonpath='{{.data.cosign\\.pub}}' > {cle}")
        signee = _verifie(host, cle, IMAGE_SIGNEE)
        nue = _verifie(host, cle, IMAGE_NUE)
        host.run(f"rm -f {cle}")
    vu = ("BEGIN PUBLIC KEY" in publique, privee, signee, nue)
    assert vu == (True, False, True, False), message(
        en=f"Task 13: (public key under cosign.pub, a private key published, {IMAGE_SIGNEE} verified, "
        f"{IMAGE_NUE} verified) = {vu}. Expected (True, False, True, False).",
        fr=f"Tâche 13 : (clé publique sous cosign.pub, une clé privée publiée, {IMAGE_SIGNEE} vérifiée, "
        f"{IMAGE_NUE} vérifiée) = {vu}. Attendu (True, False, True, False).",
    )


# ======================================================================
# Monitoring, Logging and Runtime Security (20)
# ======================================================================
def _lignes_d_audit(host, motif: str) -> list[dict]:
    res = host.run(f"sudo tail -n 5000 {JOURNAL_AUDIT} 2>/dev/null | grep -F '{motif}' || true")
    lignes = []
    for brute in res.stdout.splitlines():
        try:
            lignes.append(json.loads(brute))
        except ValueError:
            continue
    return lignes


def _provoquer_deux_lectures(host) -> None:
    _kubectl(host, f"-n coffre get secret {SECRET_AUDITE}")
    _kubectl(host, "-n coffre get pods")
    time.sleep(5)


def test_t14a_la_lecture_du_secret_est_journalisee_avec_son_corps(host):
    _provoquer_deux_lectures(host)
    lignes = [ligne for ligne in _lignes_d_audit(host, f'"name":"{SECRET_AUDITE}"')
              if (ligne.get("objectRef") or {}).get("resource") == "secrets"]
    niveaux = sorted({str(ligne.get("level")) for ligne in lignes})
    assert "RequestResponse" in niveaux, message(
        en=f"Task 14: the read of Secret {SECRET_AUDITE} appears in {JOURNAL_AUDIT} at level(s) "
        f"{niveaux or 'none'}. Expected RequestResponse.",
        fr=f"Tâche 14 : la lecture du Secret {SECRET_AUDITE} apparaît dans {JOURNAL_AUDIT} au(x) niveau(x) "
        f"{niveaux or 'aucun'}. Attendu RequestResponse.",
    )


def test_t14b_une_lecture_banale_est_journalisee_en_metadata_seulement(host):
    _provoquer_deux_lectures(host)
    lignes = [ligne for ligne in _lignes_d_audit(host, '"resource":"pods"')
              if (ligne.get("objectRef") or {}).get("resource") == "pods"]
    niveaux = sorted({str(ligne.get("level")) for ligne in lignes})
    assert niveaux == ["Metadata"], message(
        en=f"Task 14: the Pod reads appear in {JOURNAL_AUDIT} at level(s) {niveaux or 'none'}. Expected Metadata "
        "only: the body of ordinary requests has nothing to do in the log.",
        fr=f"Tâche 14 : les lectures de Pods apparaissent dans {JOURNAL_AUDIT} au(x) niveau(x) "
        f"{niveaux or 'aucun'}. Attendu Metadata seulement : le corps des requêtes banales n'a rien à faire dans "
        "le journal.",
    )


def test_t15_vitrine_ne_s_ecrit_plus_et_sert_toujours(host):
    def mesure() -> dict:
        gabarit = _gabarit(_objet(host, "-n catalogue get deployment vitrine"))
        ctx_pod = gabarit.get("securityContext") or {}
        conteneurs = gabarit.get("containers") or [{}]
        ctx = [c.get("securityContext") or {} for c in conteneurs]
        pods = [p for p in _pods(host, "catalogue", "app=vitrine") if _ready(p)
                and all((c.get("securityContext") or {}).get("readOnlyRootFilesystem") is True
                        for c in (p.get("spec") or {}).get("containers") or [])]
        ecrit = None
        if pods:
            ecrit = _exec(host, "catalogue", pods[0]["metadata"]["name"],
                          "touch /etc/nginx/conf.d/preuve").rc == 0
        sert = _kubectl(host, "-n catalogue exec client --request-timeout=30s -- "
                        "wget -q -O /dev/null -T 5 http://vitrine.catalogue.svc.cluster.local/").rc == 0
        return {
            "readOnlyRootFilesystem": all(c.get("readOnlyRootFilesystem") is True for c in ctx),
            "allowPrivilegeEscalation=false": all(c.get("allowPrivilegeEscalation") is False for c in ctx),
            "drop ALL": all("ALL" in ((c.get("capabilities") or {}).get("drop") or []) for c in ctx),
            "runAsNonRoot": ctx_pod.get("runAsNonRoot") is True or all(c.get("runAsNonRoot") is True for c in ctx),
            "write refused": ecrit is False,
            "site answers": sert,
        }

    conteneurs = _gabarit(_objet(host, "-n catalogue get deployment vitrine")).get("containers") or []
    declare = any((c.get("securityContext") or {}).get("readOnlyRootFilesystem") is True for c in conteneurs)
    vu = _attendre(mesure, lambda v: all(v.values()), declare)
    assert all(vu.values()), message(
        en=f"Task 15: measured {vu}. Expected the four settings declared on the Deployment vitrine, a write "
        "into /etc/nginx/conf.d refused in its container, and the site still answering.",
        fr=f"Tâche 15 : mesuré {vu}. Attendu les quatre réglages déclarés sur le Deployment vitrine, une écriture "
        "dans /etc/nginx/conf.d refusée dans son conteneur, et le site qui répond toujours.",
    )


def test_t16_le_pod_compromis_est_retire_et_lui_seul(host):
    presents = {p["metadata"]["name"]: p for p in _pods(host, "atelier", "app=atelier")
                if p["metadata"]["name"] in ATELIERS}
    debout = sorted(n for n, p in presents.items() if _ready(p))
    infectes = sorted(n for n in debout
                      if PROCESSUS_SUSPECT in _kubectl(host, f"-n atelier exec {n} --request-timeout=30s -- ps").stdout)
    assert len(debout) == 3 and len(presents) == 3 and not infectes, message(
        en=f"Task 16: {len(presents)} atelier Pod(s) remain, {len(debout)} ready ({debout}); still running the "
        f"suspicious process: {infectes or 'none'}. Expected the compromised Pod deleted, and the three others "
        "untouched.",
        fr=f"Tâche 16 : il reste {len(presents)} Pod(s) atelier, {len(debout)} prêt(s) ({debout}) ; font encore "
        f"tourner le processus suspect : {infectes or 'aucun'}. Attendu le Pod compromis supprimé, et les trois "
        "autres intacts.",
    )
