"""test_functional.py : k8s-epreuve-securiser-un-cluster

L'épreuve du niveau 5 (fiche KUBERN-EPREUVE-N5). Dix-neuf tests, un par état
de la fiche (P01 à P19), dans l'ordre de la fiche. Ils lisent l'état du NŒUD et
du CLUSTER, jamais les commandes tapées ni les fichiers de l'apprenant, à deux
exceptions que la fiche nomme : le Dockerfile, que trivy config analyse (P18),
et les règles livrées avec Falco, comparées à l'empreinte du paquet (P14).

D34 : l'énoncé ne nomme aucun type d'objet. Les tests retrouvent donc ce que
l'apprenant a choisi : le profil AppArmor et le profil seccomp que les Pods
déclarent, la classe de runtime que le Pod emploie, les chemins d'audit que
l'API server reçoit, la clé publique publiée dans l'espace de la boutique.

Les preuves actives exercent les deux côtés, comme dans les labs cks-* dont
elles viennent : un Pod refusé ET un Pod accepté, un client bloqué ET un client
qui passe, une écriture refusée ET une lecture permise, une image signée
acceptée ET une autre refusée. Une moitié seule serait vraie avant le travail.

dsoxlab coupe pytest au bout de 300 secondes : les attentes sont bornées, et un
état visiblement absent échoue tout de suite au lieu d'attendre.

Les dix-neuf tests échouent sur l'état hérité que pose le setup.
"""

from __future__ import annotations

import base64
import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-cp.lab"
ETAT = "/var/lib/dsoxlab/epreuve-securiser-un-cluster"
MANIFESTE_API = "/etc/kubernetes/manifests/kube-apiserver.yaml"

BOUTIQUE = "boutique"
FACTURATION = "facturation"
COMMANDES = "commandes"
PARTENAIRES = "partenaires"
PAIEMENT = "paiement"
CONFORMITE = "conformite"

DEPLOIEMENT = "catalogue"
SERVICE = "catalogue-svc"
SECRET = "catalogue-db"  # noqa: S105 - nom d'un Secret, pas un mot de passe
IMAGE_ORIGINE = "nginxinc/nginx-unprivileged:1.21"
DEPOT_PROD = "nginxinc/nginx-unprivileged"
REGISTRE_SIGNE = "localhost:5000/boutique/catalogue"
IMAGE_NON_SIGNEE = "localhost:5000/boutique/outil:1.0"

#: Une image épinglée, déjà tirée par cks-validating-admission-policy.
BUSYBOX_EPINGLEE = "busybox@sha256:ab33eacc8251e3807b85bb6dba570e4698c3998eca6f0fc2ccb60575a563ea74"
BUSYBOX_TAG = "busybox:1.37"

CONTROLES_PROFILAGE = ("1.2.15", "1.3.2", "1.4.1")
FAMILLE_CHOWN = {"chown", "fchown", "fchownat", "lchown"}
#: /dev/shm est un tmpfs ouvert en écriture à tous dans chaque conteneur, root
#: ou non, système de fichiers racine en lecture seule ou non : seul le profil
#: AppArmor peut y refuser une écriture.
REPERTOIRE_INTERDIT = "/dev/shm"  # noqa: S108 - chemin DANS le Pod, que le test doit voir refusé

FALCO_SERVICE = "falco-modern-bpf.service"
FALCO_JOURNAL = "/var/log/falco/events.json"
FALCO_REGLES = "/etc/falco/falco_rules.yaml"
REGLE = "outil-reseau-en-facturation"
PRIORITE = "warning"
#: Le déclencheur : un binaire réseau lancé DIRECTEMENT par l'exec, sans shell,
#: vers un port où rien n'écoute. Son échec est attendu, son lancement suffit.
OUTIL_RESEAU = "wget -q -T 2 -O /dev/null http://127.0.0.1:9/"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


# ======================================================================
# Outils communs
# ======================================================================
def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"{KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str) -> dict | None:
    rc, sortie, _ = _kubectl(host, f"{args} -o json")
    return json.loads(sortie) if rc == 0 and sortie else None


def _envoyer(host, manifeste: dict, verbe: str):
    """Envoie un objet à l'API par l'entrée standard, encodé en base64 pour
    échapper à toute interprétation du shell. Rend (code, sortie, diagnostic)."""
    b64 = base64.b64encode(json.dumps(manifeste).encode()).decode()
    res = host.run(f"echo {b64} | base64 -d | {KUBECTL} {verbe} -f -")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _pod_sonde(nom: str, ns: str, image: str, conforme: bool = True) -> dict:
    """Un Pod sonde. Conforme : il satisfait le standard restricted. Sinon : il
    tourne en root sans aucun autre réglage, ce que le standard baseline
    accepte et que seul restricted refuse. Le délai de grâce d'une seconde
    évite d'attendre trente secondes à chaque suppression."""
    if conforme:
        spec = {
            "terminationGracePeriodSeconds": 1,
            "securityContext": {"runAsNonRoot": True, "runAsUser": 1000,
                                "seccompProfile": {"type": "RuntimeDefault"}},
            "containers": [{"name": "outil", "image": image, "command": ["sh", "-c", "sleep 30"],
                            "securityContext": {"allowPrivilegeEscalation": False,
                                                "capabilities": {"drop": ["ALL"]}}}],
        }
    else:
        spec = {
            "terminationGracePeriodSeconds": 1,
            "containers": [{"name": "outil", "image": image, "command": ["sh", "-c", "sleep 30"],
                            "securityContext": {"runAsUser": 0}}],
        }
    return {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": nom, "namespace": ns}, "spec": spec}


def _exiger_en_marche(host, ns: str, nom: str) -> dict:
    pod = _json(host, f"-n {ns} get pod {nom}")
    assert pod is not None, message(
        en=f"No Pod {nom} in the {ns} space.",
        fr=f"Aucun Pod {nom} dans l'espace {ns}.",
    )
    phase = pod["status"].get("phase")
    assert phase == "Running", message(
        en=f"Pod {nom} of {ns} is {phase}, not Running: kubectl -n {ns} describe pod {nom} says why.",
        fr=f"Le Pod {nom} de {ns} est en {phase}, et non Running : kubectl -n {ns} describe pod {nom} dit pourquoi.",
    )
    return pod


def _dans(host, ns: str, pod: str, commande: str, conteneur: str = ""):
    option = f"-c {conteneur} " if conteneur else ""
    return _kubectl(host, f"-n {ns} exec {pod} {option}--request-timeout=30s -- sh -c '{commande}'")


def _profils_du_pod(pod: dict, champ: str) -> list[dict]:
    contextes = [pod["spec"].get("securityContext") or {}] + [
        c.get("securityContext") or {} for c in pod["spec"].get("containers") or []
    ]
    return [ctx[champ] for ctx in contextes if ctx.get(champ)]


def _digest(reference: str) -> str:
    return reference.split("@")[-1] if "@" in reference else ""


def _depot(reference: str) -> str:
    """Le dépôt d'une référence, sans tag ni digest ni préfixe docker.io."""
    depot = reference.split("@")[0]
    if ":" in depot.rsplit("/", 1)[-1]:
        depot = depot.rsplit(":", 1)[0]
    for prefixe in ("docker.io/", "index.docker.io/"):
        if depot.startswith(prefixe):
            depot = depot[len(prefixe):]
    return depot


def _attendre_le_plan_de_controle(host) -> str:
    phases = ""
    for _ in range(20):
        rc, phases, _ = _kubectl(host, "-n kube-system get pods -l tier=control-plane "
                                       "-o jsonpath='{.items[*].status.phase}'")
        if rc == 0 and phases and "Pending" not in phases:
            return phases
        time.sleep(3)
    return phases


# ======================================================================
# P01 : le profileur est fermé, l'API répond.
# ======================================================================
def test_p01_le_profileur_est_ferme_et_l_api_repond(host):
    rc, sortie, _ = _kubectl(host, "get --raw /debug/pprof/")
    assert rc != 0, message(
        en="The API server's profiler still answers on /debug/pprof/: it reports the memory, "
        f"goroutines and load of the cluster's most sensitive component. Output: {sortie[:100]}",
        fr="Le profileur de l'API server répond encore sur /debug/pprof/ : il renseigne sur la "
        f"mémoire, les goroutines et la charge du composant le plus sensible. Sortie : {sortie[:100]}",
    )
    phases = _attendre_le_plan_de_controle(host)
    assert phases and "Pending" not in phases, message(
        en=f"A control plane Pod is {phases or 'unreadable'}: the kubelet could not restart it.",
        fr=f"Un Pod du plan de contrôle est en {phases or 'état illisible'} : le kubelet n'a pas pu le redémarrer.",
    )
    rc, version, diagnostic = _kubectl(host, "get --raw /version")
    assert rc == 0 and "gitVersion" in version, message(
        en="The profiler is closed, but the API no longer serves ordinary requests either: a "
        f"stopped component closes every door, that is not hardening. {diagnostic}",
        fr="Le profileur est fermé, mais l'API ne sert plus les requêtes ordinaires non plus : un "
        f"composant arrêté ferme toutes ses portes, ce n'est pas un durcissement. {diagnostic}",
    )


# ======================================================================
# P02 : un audit kube-bench rejoué compte moins d'échecs qu'au départ.
# ======================================================================
def _job_kube_bench() -> dict:
    """Le Job de cks-cis-benchmark-remediate, écrit ici : le correcteur ne
    relance pas un fichier que l'apprenant aurait pu modifier."""
    montages = [("var-lib-etcd", "/var/lib/etcd", "/var/lib/etcd"),
                ("var-lib-kubelet", "/var/lib/kubelet", "/var/lib/kubelet"),
                ("etc-kubernetes", "/etc/kubernetes", "/etc/kubernetes"),
                ("usr-bin", "/usr/local/mount-from-host/bin", "/usr/bin")]
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": "kube-bench-correcteur", "namespace": CONFORMITE},
        "spec": {"backoffLimit": 1, "template": {"spec": {
            "nodeName": NOEUD, "hostPID": True, "restartPolicy": "Never",
            "containers": [{
                "name": "kube-bench", "image": "aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679",
                "command": ["kube-bench", "run", "--targets", "master", "--json"],
                "volumeMounts": [{"name": n, "mountPath": m, "readOnly": True} for n, m, _ in montages],
            }],
            "volumes": [{"name": n, "hostPath": {"path": h}} for n, _, h in montages],
        }}},
    }


def test_p02_un_audit_cis_rejoue_compte_moins_d_echecs(host):
    res = host.run(f"sudo cat {ETAT}/echecs-cis-depart")
    assert res.rc == 0 and res.stdout.strip().isdigit(), message(
        en="The starting CIS audit, measured by the setup, cannot be found on the node: replay the setup.",
        fr="L'audit CIS de départ, mesuré par le setup, est introuvable sur le nœud : rejouez le setup.",
    )
    depart = int(res.stdout.strip())
    _attendre_le_plan_de_controle(host)
    _kubectl(host, f"-n {CONFORMITE} delete job kube-bench-correcteur --ignore-not-found --wait=true")
    rc, _, diagnostic = _envoyer(host, _job_kube_bench(), "create")
    assert rc == 0, message(
        en=f"The grader cannot start the CIS audit in the {CONFORMITE} space: {diagnostic}",
        fr=f"Le correcteur ne peut pas lancer l'audit CIS dans l'espace {CONFORMITE} : {diagnostic}",
    )
    try:
        rc, _, diagnostic = _kubectl(host, f"-n {CONFORMITE} wait --for=condition=complete "
                                           "job/kube-bench-correcteur --timeout=180s")
        assert rc == 0, message(
            en=f"The CIS audit did not finish. {diagnostic}",
            fr=f"L'audit CIS ne s'est pas terminé. {diagnostic}",
        )
        rc, journal, diagnostic = _kubectl(host, f"-n {CONFORMITE} logs job/kube-bench-correcteur")
        debut = journal.find("{")
        assert rc == 0 and debut >= 0, message(
            en=f"The CIS audit wrote no report. {diagnostic}",
            fr=f"L'audit CIS n'a écrit aucun rapport. {diagnostic}",
        )
        rapport = json.loads(journal[debut:])
    finally:
        _kubectl(host, f"-n {CONFORMITE} delete job kube-bench-correcteur --ignore-not-found --wait=false")
    etats = {str(r.get("test_number")): str(r.get("status"))
             for c in rapport.get("Controls", []) for g in c.get("tests", []) for r in g.get("results", [])}
    en_echec = [c for c in CONTROLES_PROFILAGE if etats.get(c) != "PASS"]
    assert not en_echec, message(
        en="These profiling checks still fail in the replayed audit: "
        + ", ".join(f"{c} ({etats.get(c, 'absent')})" for c in en_echec)
        + ". The benchmark holds the same setting against three control plane components.",
        fr="Ces contrôles de profilage échouent toujours dans l'audit rejoué : "
        + ", ".join(f"{c} ({etats.get(c, 'absent')})" for c in en_echec)
        + ". Le référentiel reproche le même réglage à trois composants du plan de contrôle.",
    )
    total = sum(int(c.get("total_fail", 0)) for c in rapport.get("Controls", []))
    assert total < depart, message(
        en=f"The replayed audit counts {total} failure(s), against {depart} at the start: fixing one "
        "check while breaking another does not bring the count down.",
        fr=f"L'audit rejoué compte {total} échec(s), contre {depart} au départ : corriger un contrôle "
        "en en cassant un autre ne fait pas baisser le compte.",
    )


# ======================================================================
# P03 : l'audit est activé, politique et journal montés.
# ======================================================================
_FLAG = re.compile(r"--audit-(policy-file|log-path)=([^\s\"']+)")


def _chemins_d_audit(texte: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _FLAG.finditer(texte)}


def _monte(conteneur: dict, volumes: dict, chemin: str) -> bool:
    for m in conteneur.get("volumeMounts") or []:
        point = m.get("mountPath", "").rstrip("/")
        if (chemin == point or chemin.startswith(point + "/")) and "hostPath" in volumes.get(m.get("name"), {}):
            return True
    return False


def test_p03_l_api_server_tourne_avec_l_audit_monte(host):
    res = host.run(f"sudo cat {MANIFESTE_API}")
    assert res.rc == 0, message(
        en=f"{MANIFESTE_API} cannot be read.",
        fr=f"{MANIFESTE_API} est illisible.",
    )
    chemins = _chemins_d_audit(res.stdout)
    manquants = [f"--audit-{k}" for k in ("policy-file", "log-path") if k not in chemins]
    assert not manquants, message(
        en=f"The API server's manifest does not carry {', '.join(manquants)}: it applies no audit "
        "policy, or writes its log nowhere.",
        fr=f"Le manifeste de l'API server ne porte pas {', '.join(manquants)} : il n'applique aucune "
        "politique d'audit, ou n'écrit son journal nulle part.",
    )
    _attendre_le_plan_de_controle(host)
    pod = _json(host, f"-n kube-system get pod kube-apiserver-{NOEUD}")
    assert pod is not None and pod["status"].get("phase") == "Running", message(
        en="The API server's static Pod is not Running: the kubelet could not restart it.",
        fr="Le Pod statique de l'API server n'est pas Running : le kubelet n'a pas pu le redémarrer.",
    )
    conteneur = next(c for c in pod["spec"]["containers"] if c["name"] == "kube-apiserver")
    en_marche = _chemins_d_audit(" ".join(conteneur.get("command") or []))
    assert en_marche == chemins, message(
        en=f"The running API server does not carry the manifest's audit flags yet ({en_marche}): "
        "the kubelet has not picked the file up.",
        fr=f"L'API server en marche ne porte pas encore les flags d'audit du manifeste ({en_marche}) : "
        "le kubelet n'a pas repris le fichier.",
    )
    volumes = {v["name"]: v for v in pod["spec"].get("volumes") or []}
    non_montes = [c for c in chemins.values() if not _monte(conteneur, volumes, c)]
    assert not non_montes, message(
        en=f"These paths are not mounted from the node into the API server's container: {non_montes}. "
        "The API server is a Pod: it only sees what is mounted, and a log written inside the "
        "container disappears with it.",
        fr=f"Ces chemins ne sont pas montés depuis le nœud dans le conteneur de l'API server : "
        f"{non_montes}. L'API server est un Pod : il ne voit que ce qu'on lui monte, et un journal "
        "écrit dans le conteneur disparaît avec lui.",
    )


# ======================================================================
# P04 : le journal trace un Secret en entier, le reste en métadonnées.
# ======================================================================
def _lignes_d_audit(host, journal: str, motif: str) -> list[dict]:
    res = host.run(f"sudo tail -n 20000 {journal} 2>/dev/null | grep -F '{motif}' || true")
    lignes = []
    for brute in res.stdout.splitlines():
        try:
            lignes.append(json.loads(brute))
        except json.JSONDecodeError:
            continue
    return lignes


def test_p04_le_journal_trace_un_secret_en_entier_et_le_reste_en_metadonnees(host):
    res = host.run(f"sudo cat {MANIFESTE_API}")
    journal = _chemins_d_audit(res.stdout).get("log-path")
    assert journal, message(
        en="The API server writes no audit log: there is nothing to read.",
        fr="L'API server n'écrit aucun journal d'audit : il n'y a rien à lire.",
    )
    _attendre_le_plan_de_controle(host)
    rc, _, diagnostic = _kubectl(host, f"-n {BOUTIQUE} get secret {SECRET} -o name")
    assert rc == 0, message(
        en=f"The Secret {SECRET} of the shop cannot be read: {diagnostic}",
        fr=f"Le Secret {SECRET} de la boutique est illisible : {diagnostic}",
    )
    _kubectl(host, f"-n {BOUTIQUE} get pods -o name")
    time.sleep(5)
    secrets = [ligne for ligne in _lignes_d_audit(host, journal, f'"name":"{SECRET}"')
               if (ligne.get("objectRef") or {}).get("resource") == "secrets"]
    assert secrets, message(
        en=f"No trace of the read of Secret {SECRET} in {journal}, although it just happened. "
        "Either the log stays empty, or the rules catch nothing for Secrets.",
        fr=f"Aucune trace de la lecture du Secret {SECRET} dans {journal}, alors qu'elle vient "
        "d'avoir lieu. Soit le journal reste vide, soit les règles n'attrapent rien pour les Secrets.",
    )
    niveaux = {ligne.get("level") for ligne in secrets}
    assert "RequestResponse" in niveaux, message(
        en=f"The Secret read is recorded at level {niveaux}, not in full (RequestResponse). The "
        "API server keeps the FIRST rule that matches: a catch-all placed before wins.",
        fr=f"La lecture du Secret est enregistrée au niveau {niveaux}, et non en entier "
        "(RequestResponse). L'API server retient la PREMIÈRE règle qui correspond : une règle "
        "attrape-tout placée avant l'emporte.",
    )
    banales = [ligne for ligne in _lignes_d_audit(host, journal, '"resource":"pods"')
               if (ligne.get("objectRef") or {}).get("resource") == "pods"
               and (ligne.get("objectRef") or {}).get("namespace") == BOUTIQUE]
    assert banales, message(
        en="No trace of the ordinary read of the shop's Pods: nothing records the rest of the "
        "traffic, not even as metadata.",
        fr="Aucune trace de la lecture banale des Pods de la boutique : rien n'enregistre le reste du "
        "trafic, pas même en métadonnées.",
    )
    trop = sorted({str(ligne.get("level")) for ligne in banales if ligne.get("level") != "Metadata"})
    assert not trop, message(
        en=f"Ordinary reads are recorded at level {trop} instead of Metadata: auditing everything in "
        "full copies request bodies into the log and fills the disk.",
        fr=f"Des lectures banales sont enregistrées au niveau {trop} au lieu de Metadata : tout "
        "auditer en entier recopie les corps de requête dans le journal et sature le disque.",
    )


# ======================================================================
# P05 : la boutique refuse un Pod hors standard restricted.
# ======================================================================
def test_p05_la_boutique_refuse_un_pod_hors_standard_restricted(host):
    rc, _, refus = _envoyer(host, _pod_sonde("sonde-interdite", BOUTIQUE, BUSYBOX_EPINGLEE, conforme=False),
                            "apply --dry-run=server")
    assert rc != 0, message(
        en=f"The {BOUTIQUE} space accepts a Pod that runs as root with no hardening at all: nothing "
        "enforces the restricted standard there (the baseline standard lets such a Pod through).",
        fr=f"L'espace {BOUTIQUE} accepte un Pod qui tourne en root sans aucun durcissement : rien n'y "
        "applique le standard restricted (le standard baseline laisse passer un tel Pod).",
    )
    assert "podsecurity" in refus.lower().replace(" ", ""), message(
        en=f"The forbidden Pod is refused, but not by the Pod security standard: {refus[:300]}",
        fr=f"Le Pod interdit est refusé, mais pas par le standard de sécurité des Pods : {refus[:300]}",
    )
    rc, _, diagnostic = _envoyer(host, _pod_sonde("sonde-conforme", BOUTIQUE, BUSYBOX_EPINGLEE),
                                 "apply --dry-run=server")
    assert rc == 0, message(
        en=f"A Pod that satisfies the restricted standard, with a pinned image, is refused too: "
        f"{diagnostic[:300]}. The rule must sort, not block the space.",
        fr=f"Un Pod qui satisfait le standard restricted, image épinglée, est refusé lui aussi : "
        f"{diagnostic[:300]}. La règle doit trier, pas bloquer l'espace.",
    )


# ======================================================================
# P06 : une image par tag est refusée dans la boutique, et seulement là.
# ======================================================================
def _supprimer_sonde(host, nom: str, ns: str = BOUTIQUE) -> None:
    _kubectl(host, f"-n {ns} delete pod {nom} --ignore-not-found --wait=true --timeout=60s")


def _creer_sonde(host, nom: str, image: str):
    _supprimer_sonde(host, nom)
    resultat = _envoyer(host, _pod_sonde(nom, BOUTIQUE, image), "create")
    _supprimer_sonde(host, nom)
    return resultat


def test_p06_une_image_par_tag_est_refusee_dans_la_boutique_seulement(host):
    rc, _, refus = _creer_sonde(host, "sonde-tag", BUSYBOX_TAG)
    if rc == 0:
        # Une politique fraîchement posée met quelques secondes à agir.
        for _ in range(4):
            time.sleep(4)
            rc, _, refus = _creer_sonde(host, "sonde-tag", BUSYBOX_TAG)
            if rc != 0:
                break
    assert rc != 0, message(
        en=f"The {BOUTIQUE} space accepts a compliant Pod whose image is named by a tag "
        f"({BUSYBOX_TAG}). A tag can be repointed at other content without any manifest changing.",
        fr=f"L'espace {BOUTIQUE} accepte un Pod conforme dont l'image est désignée par un tag "
        f"({BUSYBOX_TAG}). Un tag peut être redirigé vers un autre contenu sans qu'aucun manifeste ne change.",
    )
    texte = refus.lower()
    assert "validatingadmissionpolicy" in texte or "denied request" in texte, message(
        en=f"The Pod by tag is refused, but not by an admission rule of the cluster itself: {refus[:300]}",
        fr=f"Le Pod par tag est refusé, mais pas par une règle d'admission du cluster lui-même : {refus[:300]}",
    )
    rc, _, diagnostic = _creer_sonde(host, "sonde-digest", BUSYBOX_EPINGLEE)
    assert rc == 0, message(
        en=f"The compliant Pod with a pinned image is refused too: {diagnostic[:300]}. The rule must "
        "tell a pinned image from a tag, not block the space.",
        fr=f"Le Pod conforme à l'image épinglée est refusé lui aussi : {diagnostic[:300]}. La règle "
        "doit distinguer une image épinglée d'un tag, pas bloquer l'espace.",
    )
    rc, _, diagnostic = _envoyer(host, _pod_sonde("sonde-ailleurs", "default", BUSYBOX_TAG), "apply --dry-run=server")
    assert rc == 0, message(
        en=f"A Pod by tag is refused in the default space too: {diagnostic[:300]}. The rule reaches "
        "beyond the shop, where nothing asked for it (system images are not pinned).",
        fr=f"Un Pod par tag est refusé dans l'espace default aussi : {diagnostic[:300]}. La règle "
        "déborde de la boutique, où rien ne l'exigeait (les images système ne sont pas épinglées).",
    )


# ======================================================================
# P07 : le Pod privilégié hérité est remplacé.
# ======================================================================
def test_p07_le_pod_privilegie_herite_est_remplace(host):
    rc, _, _ = _kubectl(host, f"-n {BOUTIQUE} get pod outil-ancien")
    assert rc != 0, message(
        en="outil-ancien still runs: a fix placed next to the flaw fixes nothing.",
        fr="outil-ancien tourne toujours : un correctif posé à côté de la faille ne corrige rien.",
    )
    pod = _exiger_en_marche(host, BOUTIQUE, "outil")
    spec = pod["spec"]
    conteneur = spec["containers"][0]
    ctx_pod = spec.get("securityContext") or {}
    ctx = conteneur.get("securityContext") or {}
    restants = []
    if spec.get("hostPID") or spec.get("hostNetwork") or spec.get("hostIPC"):
        restants.append(message(en="shares a host namespace", fr="partage un namespace de l'hôte"))
    if ctx.get("privileged"):
        restants.append(message(en="privileged container", fr="conteneur privilégié"))
    if ctx.get("allowPrivilegeEscalation") is not False:
        restants.append(message(en="privilege escalation not forbidden", fr="escalade de privilèges non interdite"))
    identites = [ctx_pod.get("runAsUser"), ctx.get("runAsUser")]
    if 0 in identites or not any(i for i in identites if i):
        restants.append(message(en="runs as root, or imposes no user", fr="tourne en root, ou n'impose aucun utilisateur"))
    if "ALL" not in ((ctx.get("capabilities") or {}).get("drop") or []):
        restants.append(message(en="capabilities not all dropped", fr="capabilities pas toutes retirées"))
    image = conteneur.get("image", "")
    if image.endswith(":latest") or ":" not in image.rsplit("/", 1)[-1]:
        restants.append(message(en=f"floating image {image}", fr=f"image flottante {image}"))
    assert not restants, message(
        en=f"The replacement Pod outil keeps defects of the original: {restants}.",
        fr=f"Le Pod de remplacement outil garde des défauts de l'original : {restants}.",
    )
    rc, sortie, diagnostic = _dans(host, BOUTIQUE, "outil", "ps -eo pid | wc -l")
    assert rc == 0 and sortie.isdigit(), message(
        en=f"Cannot count the processes seen by outil. {diagnostic}",
        fr=f"Impossible de compter les processus que voit outil. {diagnostic}",
    )
    assert int(sortie) <= 30, message(
        en=f"outil sees {sortie} processes: those of the NODE, kubelet and containerd included.",
        fr=f"outil voit {sortie} processus : ceux du NŒUD, kubelet et containerd compris.",
    )


# ======================================================================
# P08 : AppArmor.
# ======================================================================
def test_p08_apparmor_refuse_l_ecriture_et_laisse_lire(host):
    pod = _exiger_en_marche(host, FACTURATION, "consultation")
    assert pod["spec"].get("nodeName") == NOEUD, message(
        en=f"consultation runs on {pod['spec'].get('nodeName')}, not on {NOEUD}, the node where profiles are loaded.",
        fr=f"consultation tourne sur {pod['spec'].get('nodeName')}, et non sur {NOEUD}, le nœud où les profils sont chargés.",
    )
    noms = [p.get("localhostProfile") for p in _profils_du_pod(pod, "appArmorProfile") if p.get("type") == "Localhost"]
    assert noms, message(
        en="consultation declares no AppArmor profile loaded on the node (type Localhost).",
        fr="consultation ne déclare aucun profil AppArmor chargé sur le nœud (type Localhost).",
    )
    profils = json.loads(host.run("sudo aa-status --json").stdout or "{}").get("profiles", {})
    modes = {n: profils.get(n, "absent") for n in noms}
    assert all(m == "enforce" for m in modes.values()), message(
        en=f"The profile declared by consultation is not loaded in enforce mode on {NOEUD}: {modes}.",
        fr=f"Le profil que déclare consultation n'est pas chargé en mode enforce sur {NOEUD} : {modes}.",
    )
    _, presence, _ = _dans(host, FACTURATION, "consultation", f"test -d {REPERTOIRE_INTERDIT}; echo CODE=$?")
    assert "CODE=0" in presence, message(
        en=f"{REPERTOIRE_INTERDIT} does not exist in consultation: a write there cannot prove a refusal.",
        fr=f"{REPERTOIRE_INTERDIT} n'existe pas dans consultation : une écriture y échouerait sans rien prouver.",
    )
    _, ecriture, _ = _dans(host, FACTURATION, "consultation",
                           f"echo test > {REPERTOIRE_INTERDIT}/preuve 2>/dev/null; echo CODE=$?")
    assert "CODE=" in ecriture and "CODE=0" not in ecriture, message(
        en=f"consultation can still write into {REPERTOIRE_INTERDIT}: the profile does not deny it. Output: {ecriture}",
        fr=f"consultation peut encore écrire dans {REPERTOIRE_INTERDIT} : le profil ne l'interdit pas. Sortie : {ecriture}",
    )
    _, lecture, _ = _dans(host, FACTURATION, "consultation", "cat /etc/hostname >/dev/null; echo CODE=$?")
    assert "CODE=0" in lecture, message(
        en=f"consultation cannot even read /etc/hostname: the profile forbids more than asked. Output: {lecture}",
        fr=f"consultation ne peut même plus lire /etc/hostname : le profil interdit plus que demandé. Sortie : {lecture}",
    )


# ======================================================================
# P09 : seccomp.
# ======================================================================
def test_p09_seccomp_refuse_chown_et_le_pod_tourne(host):
    pod = _exiger_en_marche(host, FACTURATION, "numerotation")
    chemins = [p.get("localhostProfile") for p in _profils_du_pod(pod, "seccompProfile") if p.get("type") == "Localhost"]
    assert chemins and pod["spec"].get("nodeName") == NOEUD, message(
        en=f"numerotation declares no local seccomp profile, or does not run on {NOEUD} where the profile lives.",
        fr=f"numerotation ne déclare aucun profil seccomp local, ou ne tourne pas sur {NOEUD}, où vit le profil.",
    )
    res = host.run(f"sudo cat /var/lib/kubelet/seccomp/{chemins[0]}")
    try:
        profil = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"The profile declared by numerotation ({chemins[0]}) is not readable JSON on the node.",
            fr=f"Le profil que déclare numerotation ({chemins[0]}) n'est pas un JSON lisible sur le nœud.",
        ))
    refuses = {n for r in profil.get("syscalls") or []
               if r.get("action") in ("SCMP_ACT_ERRNO", "SCMP_ACT_KILL", "SCMP_ACT_KILL_PROCESS")
               for n in r.get("names") or []}
    assert profil.get("defaultAction") == "SCMP_ACT_ALLOW" and refuses >= FAMILLE_CHOWN, message(
        en=f"The profile must allow by default and refuse {sorted(FAMILLE_CHOWN)}: defaultAction is "
        f"{profil.get('defaultAction')}, refused: {sorted(refuses & FAMILLE_CHOWN)}.",
        fr=f"Le profil doit autoriser par défaut et refuser {sorted(FAMILLE_CHOWN)} : defaultAction vaut "
        f"{profil.get('defaultAction')}, refusés : {sorted(refuses & FAMILLE_CHOWN)}.",
    )
    rc, sortie, diagnostic = _dans(host, FACTURATION, "numerotation", "touch /tmp/preuve && echo ok")
    assert rc == 0 and sortie == "ok", message(
        en=f"numerotation cannot even create a file: the filter refuses more than chown. {diagnostic}",
        fr=f"numerotation ne peut même plus créer un fichier : le filtre refuse plus que chown. {diagnostic}",
    )
    rc, _, diagnostic = _dans(host, FACTURATION, "numerotation", "chown 1000:1000 /tmp/preuve")
    assert rc != 0 and "not permitted" in diagnostic.lower(), message(
        en=f"chown is not refused by seccomp in numerotation (code {rc}, {diagnostic}).",
        fr=f"chown n'est pas refusé par seccomp dans numerotation (code {rc}, {diagnostic}).",
    )


# ======================================================================
# P10 : le maillage exige le TLS mutuel.
# ======================================================================
def _mode_effectif(host) -> str:
    """Le mode TLS mutuel qui s'applique à tout commandes : celui de l'espace
    s'il en déclare un pour tout l'espace, sinon celui du maillage entier."""
    items = (_json(host, "get peerauthentication -A") or {}).get("items", [])
    globaux = {o["metadata"]["namespace"]: ((o.get("spec") or {}).get("mtls") or {}).get("mode", "")
               for o in items if not (o.get("spec") or {}).get("selector")}
    return globaux.get(COMMANDES) or globaux.get("istio-system") or "PERMISSIVE"


def _joint_suivi(host, ns: str, pod: str) -> bool:
    rc, _, _ = _kubectl(host, f"-n {ns} exec {pod} -c outil --request-timeout=30s "
                              "-- wget -qO- -T 5 http://suivi.commandes.svc.cluster.local/")
    return rc == 0


def test_p10_le_maillage_exige_le_tls_mutuel(host):
    mode = _mode_effectif(host)
    assert mode == "STRICT", message(
        en=f"The mutual TLS mode in force for the {COMMANDES} space is {mode}: plain traffic is "
        "still accepted alongside encrypted traffic.",
        fr=f"Le mode TLS mutuel en vigueur pour l'espace {COMMANDES} est {mode} : le trafic en clair "
        "est encore accepté à côté du chiffré.",
    )
    for ns, pod in ((COMMANDES, "suivi"), (COMMANDES, "panier"), (PARTENAIRES, "transporteur")):
        _exiger_en_marche(host, ns, pod)
    fin = time.monotonic() + 30
    hors_maillage_passe = True
    while time.monotonic() < fin:
        hors_maillage_passe = _joint_suivi(host, PARTENAIRES, "transporteur")
        if not hors_maillage_passe:
            break
        time.sleep(3)
    assert not hors_maillage_passe, message(
        en="transporteur, without a sidecar, still reaches suivi in plain text after 30 seconds.",
        fr="transporteur, sans sidecar, joint toujours suivi en clair après 30 secondes.",
    )
    assert _joint_suivi(host, COMMANDES, "panier"), message(
        en="panier, which carries a sidecar, no longer reaches suivi: the requirement must cut "
        "what is outside the mesh, not the mesh itself.",
        fr="panier, qui porte un sidecar, ne joint plus suivi : l'exigence doit couper ce qui est "
        "hors du maillage, pas le maillage lui-même.",
    )


# ======================================================================
# P11 : paiement fermé par défaut, sauf le flux prévu et le DNS.
# ======================================================================
def _ip(host, ns: str, pod: str) -> str:
    rc, ip, diagnostic = _kubectl(host, f"-n {ns} get pod {pod} -o jsonpath='{{.status.podIP}}'")
    assert rc == 0 and ip, message(
        en=f"Pod {pod} of {ns} has no address: the setup placed it, it stays. {diagnostic}",
        fr=f"Le Pod {pod} de {ns} n'a pas d'adresse : le setup l'a posé, il reste. {diagnostic}",
    )
    return ip


def _joint(host, depuis: str, ns_cible: str, cible: str) -> bool:
    rc, _, _ = _kubectl(host, f"-n {PAIEMENT} exec {depuis} --request-timeout=30s -- "
                              f"wget -q -O- -T 4 http://{_ip(host, ns_cible, cible)}/")
    return rc == 0


def test_p11_paiement_est_ferme_sauf_le_flux_prevu_et_le_dns(host):
    directions = set()
    for politique in (_json(host, f"-n {PAIEMENT} get networkpolicy") or {}).get("items", []):
        spec = politique.get("spec") or {}
        if (spec.get("podSelector") or {}) == {}:
            directions |= {d for d in spec.get("policyTypes") or [] if not spec.get(d.lower())}
    manquantes = {"Ingress", "Egress"} - directions
    assert not manquantes, message(
        en=f"Nothing closes {PAIEMENT} by default for every Pod in: {', '.join(sorted(manquantes))}.",
        fr=f"Rien ne ferme {PAIEMENT} par défaut pour tous ses Pods en : {', '.join(sorted(manquantes))}.",
    )
    ecarts = []
    if _joint(host, "publicite", PAIEMENT, "fidelite"):
        ecarts.append(message(en="publicite reaches fidelite (inbound not closed)",
                              fr="publicite joint fidelite (entrée non fermée)"))
    if _joint(host, "grand-livre", PARTENAIRES, "site-partenaire"):
        ecarts.append(message(en="grand-livre reaches site-partenaire outside the space (outbound not closed)",
                              fr="grand-livre joint site-partenaire hors de l'espace (sortie non fermée)"))
    if not _joint(host, "caisse", PAIEMENT, "grand-livre"):
        ecarts.append(message(en="caisse no longer reaches grand-livre on port 80 (planned flow cut)",
                              fr="caisse ne joint plus grand-livre sur le port 80 (flux prévu coupé)"))
    if _joint(host, "publicite", PAIEMENT, "grand-livre"):
        ecarts.append(message(en="publicite reaches grand-livre", fr="publicite joint grand-livre"))
    rc, _, _ = _kubectl(host, f"-n {PAIEMENT} exec caisse --request-timeout=30s -- "
                              "nslookup kubernetes.default.svc.cluster.local")
    if rc != 0:
        ecarts.append(message(en="caisse resolves no name (DNS cut)", fr="caisse ne résout plus aucun nom (DNS coupé)"))
    if _joint(host, "caisse", PARTENAIRES, "site-partenaire"):
        ecarts.append(message(en="caisse reaches site-partenaire (outbound reopened too broadly)",
                              fr="caisse joint site-partenaire (sortie rouverte trop largement)"))
    assert not ecarts, message(
        en=f"The {PAIEMENT} space is not closed as required: {ecarts}.",
        fr=f"L'espace {PAIEMENT} n'est pas fermé comme demandé : {ecarts}.",
    )


# ======================================================================
# P12 : le bac à sable.
# ======================================================================
def _noyau(host, pod: str) -> str:
    rc, sortie, diagnostic = _kubectl(host, f"-n {FACTURATION} exec {pod} --request-timeout=30s -- cat /proc/version")
    assert rc == 0 and sortie, message(
        en=f"Cannot read the kernel seen by {pod}. {diagnostic}",
        fr=f"Impossible de lire le noyau que voit {pod}. {diagnostic}",
    )
    return sortie


def test_p12_le_bac_a_sable_lit_un_autre_noyau(host):
    pod = _exiger_en_marche(host, FACTURATION, "rendu")
    classe = pod["spec"].get("runtimeClassName")
    assert classe, message(
        en="rendu names no runtime class: it runs with the default runtime.",
        fr="rendu ne nomme aucune classe de runtime : il tourne avec le runtime par défaut.",
    )
    objet = _json(host, f"get runtimeclass {classe}") or {}
    assert objet.get("handler") == "runsc", message(
        en=f"The runtime class {classe} designates {objet.get('handler')}, not the node's sandbox "
        "runtime as containerd knows it.",
        fr=f"La classe de runtime {classe} désigne {objet.get('handler')}, et non le runtime bac à "
        "sable du nœud tel que containerd le connaît.",
    )
    rendu, temoin = _noyau(host, "rendu"), _noyau(host, "temoin-noyau")
    machine = host.run("uname -r").stdout.strip()
    assert machine and machine in temoin, message(
        en=f"The witness temoin-noyau does not read the machine's kernel ({machine}): no comparison point.",
        fr=f"Le témoin temoin-noyau ne lit pas le noyau de la machine ({machine}) : aucun point de comparaison.",
    )
    assert machine not in rendu and rendu != temoin, message(
        en=f"rendu reads the machine's kernel: {rendu}.",
        fr=f"rendu lit le noyau de la machine : {rendu}.",
    )


# ======================================================================
# P13 et P14 : Falco.
# ======================================================================
_FALCO: dict[str, list[dict]] = {}


def _falco_actif(host) -> None:
    res = host.run(f"systemctl is-active {FALCO_SERVICE}")
    assert res.stdout.strip() == "active", message(
        en=f"Falco is not running on {NOEUD}: a rule file it cannot load stops it "
        f"(sudo journalctl -u {FALCO_SERVICE}).",
        fr=f"Falco ne tourne pas sur {NOEUD} : un fichier de règles qu'il ne sait pas charger l'arrête "
        f"(sudo journalctl -u {FALCO_SERVICE}).",
    )


def _lignes_falco(host) -> int:
    res = host.run(f"sudo sh -c 'if [ -f {FALCO_JOURNAL} ]; then wc -l < {FALCO_JOURNAL}; else echo 0; fi'")
    return int(res.stdout.strip()) if res.stdout.strip().isdigit() else 0


def _alertes_apres_un_outil_reseau(host, ns: str, pod: str, essais: int) -> list[dict]:
    """Lance l'outil réseau dans le Pod, directement par l'exec (sans shell,
    pour que le processus créé soit bien wget), puis lit les alertes de la
    règle demandée. wget échoue faute de serveur : seul compte qu'il ait été
    lancé, ce que distingue le message « command terminated with exit code »
    d'un exec qui n'a pas abouti."""
    depuis = _lignes_falco(host)
    rc, _, diagnostic = _kubectl(host, f"-n {ns} exec {pod} --request-timeout=30s -- {OUTIL_RESEAU}")
    assert rc == 0 or "command terminated with exit code" in diagnostic, message(
        en=f"The grader cannot start wget in {pod} of {ns}: the setup placed it, it stays. {diagnostic}",
        fr=f"Le correcteur ne peut pas lancer wget dans {pod} de {ns} : le setup l'a posé, il reste. {diagnostic}",
    )
    for _ in range(essais):
        time.sleep(2)
        res = host.run(f"sudo tail -n +{depuis + 1} {FALCO_JOURNAL}")
        alertes = []
        for brute in res.stdout.splitlines():
            if brute.strip().startswith("{"):
                try:
                    alertes.append(json.loads(brute))
                except json.JSONDecodeError:
                    continue
        trouvees = [a for a in alertes if a.get("rule") == REGLE]
        if trouvees:
            return trouvees
    return []


def _alertes_de_facturation(host) -> list[dict]:
    if "facturation" not in _FALCO:
        _falco_actif(host)
        _exiger_en_marche(host, FACTURATION, "export-comptable")
        _FALCO["facturation"] = _alertes_apres_un_outil_reseau(host, FACTURATION, "export-comptable", essais=10)
    return _FALCO["facturation"]


def test_p13_falco_alerte_sur_un_outil_reseau_en_facturation_et_pas_ailleurs(host):
    alertes = _alertes_de_facturation(host)
    assert alertes, message(
        en=f"wget started in export-comptable ({FACTURATION}) raised no alert of rule {REGLE} within "
        f"20 seconds (read in {FALCO_JOURNAL}).",
        fr=f"wget lancé dans export-comptable ({FACTURATION}) n'a levé aucune alerte de la règle {REGLE} "
        f"en 20 secondes (lu dans {FALCO_JOURNAL}).",
    )
    priorites = sorted({str(a.get("priority", "")).lower() for a in alertes})
    assert PRIORITE in priorites, message(
        en=f"Rule {REGLE} fires with priority {priorites} instead of {PRIORITE.upper()}.",
        fr=f"La règle {REGLE} alerte avec la priorité {priorites} au lieu de {PRIORITE.upper()}.",
    )
    _exiger_en_marche(host, PARTENAIRES, "visiteur")
    ailleurs = _alertes_apres_un_outil_reseau(host, PARTENAIRES, "visiteur", essais=5)
    assert not ailleurs, message(
        en=f"wget in visiteur ({PARTENAIRES}) raises rule {REGLE} too: it is not limited to {FACTURATION}.",
        fr=f"wget dans visiteur ({PARTENAIRES}) déclenche aussi la règle {REGLE} : elle n'est pas "
        f"limitée à {FACTURATION}.",
    )


def test_p14_les_regles_falco_fournies_sont_intactes(host):
    attendu = host.run(
        "awk '$2 == \"etc/falco/falco_rules.yaml\" {print $1}' /var/lib/dpkg/info/falco.md5sums"
    ).stdout.strip()
    res = host.run(f"sudo md5sum {FALCO_REGLES}")
    actuel = res.stdout.split()[0] if res.rc == 0 and res.stdout.strip() else "absent"
    assert attendu and actuel == attendu, message(
        en=f"{FALCO_REGLES} differs from the file shipped with the package ({actuel}, expected "
        f"{attendu or 'unknown'}): a custom rule lives in its own file.",
        fr=f"{FALCO_REGLES} diffère du fichier livré par le paquet ({actuel}, attendu "
        f"{attendu or 'inconnu'}) : une règle personnalisée vit dans son propre fichier.",
    )
    assert _alertes_de_facturation(host), message(
        en=f"The shipped rules are intact, but rule {REGLE} raises nothing: half of the requirement.",
        fr=f"Les règles fournies sont intactes, mais la règle {REGLE} ne lève rien : la moitié de la demande.",
    )


# ======================================================================
# P15 à P19 : la boutique et sa chaîne d'approvisionnement.
# ======================================================================
def _deploiement(host) -> dict:
    d = _json(host, f"-n {BOUTIQUE} get deployment {DEPLOIEMENT}")
    assert d is not None, message(
        en=f"The {DEPLOIEMENT} deployment of the shop no longer exists: it was to be secured, not removed.",
        fr=f"Le déploiement {DEPLOIEMENT} de la boutique n'existe plus : il fallait le sécuriser, pas le retirer.",
    )
    return d


def _image(d: dict) -> str:
    conteneurs = d["spec"]["template"]["spec"]["containers"]
    return next((c for c in conteneurs if c["name"] == DEPLOIEMENT), conteneurs[0])["image"]


def _pods_du_catalogue(host) -> list[dict]:
    items = (_json(host, f"-n {BOUTIQUE} get pods -l app={DEPLOIEMENT}") or {}).get("items", [])
    return [p for p in items if not p["metadata"].get("deletionTimestamp")
            and any(o.get("kind") == "ReplicaSet" for o in p["metadata"].get("ownerReferences") or [])]


def test_p15_la_boutique_tourne_sur_le_digest_qu_elle_declare(host):
    d = _deploiement(host)
    declare = _digest(_image(d))
    assert declare.startswith("sha256:"), message(
        en=f"The shop still references its image by a mutable name: {_image(d)}.",
        fr=f"La boutique référence encore son image par un nom mutable : {_image(d)}.",
    )
    voulus = d["spec"].get("replicas", 1)
    assert d.get("status", {}).get("readyReplicas", 0) == voulus, message(
        en=f"{d.get('status', {}).get('readyReplicas', 0)} replica(s) out of {voulus} are ready.",
        fr=f"{d.get('status', {}).get('readyReplicas', 0)} réplica(s) sur {voulus} sont prêts.",
    )
    executes = [s.get("imageID", "") for p in _pods_du_catalogue(host)
                for s in p["status"].get("containerStatuses") or [] if s.get("name") == DEPLOIEMENT]
    ecarts = [e for e in executes if _digest(e) != declare]
    assert executes and not ecarts, message(
        en=f"The deployment declares {declare}, but its Pods run {ecarts or 'nothing readable'}: "
        "a reference shaped like a digest is not a pin.",
        fr=f"Le déploiement déclare {declare}, mais ses Pods exécutent {ecarts or 'rien de lisible'} : "
        "une référence qui a la forme d'un digest n'est pas un épinglage.",
    )


def _cle_publiee(host) -> str:
    """La clé publique publiée dans l'espace de la boutique, quel que soit
    l'objet choisi pour la publier. Aucun objet n'y porte de clé privée."""
    textes = []
    for objet in (_json(host, f"-n {BOUTIQUE} get configmaps") or {}).get("items", []):
        textes += [str(v) for v in (objet.get("data") or {}).values()]
    for objet in (_json(host, f"-n {BOUTIQUE} get secrets") or {}).get("items", []):
        for v in (objet.get("data") or {}).values():
            try:
                textes.append(base64.b64decode(v).decode(errors="replace"))
            except ValueError:
                continue
    assert not [t for t in textes if "PRIVATE KEY" in t], message(
        en=f"A PRIVATE key is published in the {BOUTIQUE} space: whoever reads it signs in your name.",
        fr=f"Une clé PRIVÉE est publiée dans l'espace {BOUTIQUE} : qui la lit signe en votre nom.",
    )
    publiques = [t for t in textes if "BEGIN PUBLIC KEY" in t]
    assert publiques, message(
        en=f"No public key is published in the {BOUTIQUE} space: nobody can verify the signature.",
        fr=f"Aucune clé publique n'est publiée dans l'espace {BOUTIQUE} : personne ne peut vérifier la signature.",
    )
    return publiques[0]


def _verifie(host, cle: str, image: str) -> bool:
    b64 = base64.b64encode(cle.encode()).decode()
    res = host.run(f"echo {b64} | base64 -d > /tmp/dsoxlab-verif-cosign.pub; "
                   f"sudo cosign verify --key /tmp/dsoxlab-verif-cosign.pub {image} >/dev/null 2>&1; echo CODE=$?")
    return "CODE=0" in res.stdout


def test_p16_l_image_signee_est_acceptee_et_une_autre_refusee(host):
    declare = _digest(_image(_deploiement(host)))
    assert declare.startswith("sha256:"), message(
        en="The shop runs no pinned image yet: there is no production digest to verify.",
        fr="La boutique ne tourne encore sur aucune image épinglée : il n'y a pas de digest de production à vérifier.",
    )
    cle = _cle_publiee(host)
    signee = f"{REGISTRE_SIGNE}@{declare}"
    assert _verifie(host, cle, signee), message(
        en=f"The published key does not validate {signee}, the copy in the local registry of the "
        "image the shop runs: not signed, signed with another key, or not copied there.",
        fr=f"La clé publiée ne valide pas {signee}, la copie dans le registre local de l'image que la "
        "boutique exécute : non signée, signée d'une autre clé, ou pas copiée là.",
    )
    assert not _verifie(host, cle, IMAGE_NON_SIGNEE), message(
        en=f"The published key also validates {IMAGE_NON_SIGNEE}, which nobody signed: the "
        "verification measures nothing.",
        fr=f"La clé publiée valide aussi {IMAGE_NON_SIGNEE}, que personne n'a signée : la "
        "vérification ne mesure rien.",
    )


def _critiques(host, image: str) -> int:
    res = host.run(f"sudo trivy image --quiet --scanners vuln --severity CRITICAL --format json {image} 2>/dev/null")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"trivy could not analyse {image} on the node.",
        fr=f"trivy n'a pas pu analyser {image} sur le nœud.",
    )
    return sum(len(r.get("Vulnerabilities") or []) for r in json.loads(res.stdout).get("Results") or [])


def test_p17_l_image_de_production_porte_moins_de_failles_critiques(host):
    image = _image(_deploiement(host))
    assert image != IMAGE_ORIGINE and _depot(image) == DEPOT_PROD, message(
        en=f"The shop runs {image}. Expected another image of {DEPOT_PROD} than the original {IMAGE_ORIGINE}.",
        fr=f"La boutique tourne sur {image}. Attendu une autre image de {DEPOT_PROD} que l'originale {IMAGE_ORIGINE}.",
    )
    avant, apres = _critiques(host, IMAGE_ORIGINE), _critiques(host, image)
    assert avant > 0, message(
        en=f"trivy finds no critical vulnerability in {IMAGE_ORIGINE}: its database is missing.",
        fr=f"trivy ne trouve aucune faille critique dans {IMAGE_ORIGINE} : sa base manque.",
    )
    assert apres < avant, message(
        en=f"The production image carries {apres} critical vulnerability(ies), against {avant} for "
        f"{IMAGE_ORIGINE}: the replacement does not reduce exposure. Scan before deploying.",
        fr=f"L'image de production porte {apres} faille(s) critique(s), contre {avant} pour "
        f"{IMAGE_ORIGINE} : le remplacement ne réduit pas l'exposition. Analysez avant de déployer.",
    )


CONSTATS = {
    "DS-0001": "tag latest",
    "DS-0002": "root",
    "DS-0004": "port 22",
    "DS-0026": "HEALTHCHECK",
    "DS-0029": "--no-install-recommends",
}


def test_p18_le_dockerfile_ne_porte_plus_ses_constats(host):
    res = host.run("sudo cat /root/boutique/Dockerfile")
    assert res.rc == 0 and res.stdout.strip(), message(
        en="/root/boutique/Dockerfile no longer exists: it was to be fixed, not removed.",
        fr="/root/boutique/Dockerfile n'existe plus : il fallait le corriger, pas le retirer.",
    )
    contenu = res.stdout.lower()
    assert "nginx" in contenu and "/usr/share/nginx/html" in contenu, message(
        en="The Dockerfile no longer builds an nginx image serving the shop's pages.",
        fr="Le Dockerfile ne construit plus une image nginx qui sert les pages de la boutique.",
    )
    analyse = host.run("sudo trivy config --quiet --format json /root/boutique 2>/dev/null")
    assert analyse.rc == 0 and analyse.stdout.strip(), message(
        en="trivy config could not analyse /root/boutique.",
        fr="trivy config n'a pas pu analyser /root/boutique.",
    )
    trouves = {str(m.get("ID")) for r in json.loads(analyse.stdout).get("Results") or []
               for m in r.get("Misconfigurations") or []}
    restants = sorted(trouves & set(CONSTATS))
    assert not restants, message(
        en=f"trivy config still reports: {', '.join(f'{i} ({CONSTATS[i]})' for i in restants)}.",
        fr=f"trivy config reproche encore : {', '.join(f'{i} ({CONSTATS[i]})' for i in restants)}.",
    )


def _ecarts_restricted(pod: dict) -> list[str]:
    spec = pod["spec"]
    ctx_pod = spec.get("securityContext") or {}
    ecarts = []
    for c in spec.get("containers") or []:
        ctx = c.get("securityContext") or {}
        if not (ctx.get("runAsNonRoot") or ctx_pod.get("runAsNonRoot")):
            ecarts.append("runAsNonRoot")
        if ctx.get("allowPrivilegeEscalation") is not False:
            ecarts.append("allowPrivilegeEscalation")
        if "ALL" not in ((ctx.get("capabilities") or {}).get("drop") or []):
            ecarts.append("capabilities drop ALL")
        seccomp = (ctx.get("seccompProfile") or ctx_pod.get("seccompProfile") or {}).get("type")
        if seccomp not in ("RuntimeDefault", "Localhost"):
            ecarts.append("seccompProfile")
    return sorted(set(ecarts))


def test_p19_la_boutique_repond_apres_les_durcissements(host):
    d = _deploiement(host)
    voulus = d["spec"].get("replicas", 1)
    statut = d.get("status") or {}
    assert voulus >= 2 and statut.get("readyReplicas", 0) == voulus and statut.get("updatedReplicas", 0) == voulus, message(
        en=f"The shop is not fully available: {statut.get('readyReplicas', 0)} ready out of {voulus} "
        "wanted (at least 2), rollout finished or not.",
        fr=f"La boutique n'est pas entièrement disponible : {statut.get('readyReplicas', 0)} prêts sur "
        f"{voulus} voulus (au moins 2), déploiement terminé ou non.",
    )
    pods = [p for p in _pods_du_catalogue(host) if p["status"].get("phase") == "Running"]
    non_durcis = {p["metadata"]["name"]: e for p in pods
                  if (e := _ecarts_restricted(p) + ([] if "@sha256:" in _image({"spec": {"template": p}})
                                                    else ["image par tag"]))}
    assert pods and not non_durcis, message(
        en=f"The shop's running Pods were not created under the hardening: {non_durcis or 'no Pod'}. "
        "Expected a pinned image and the restricted standard's settings.",
        fr=f"Les Pods en marche de la boutique n'ont pas été créés sous le durcissement : "
        f"{non_durcis or 'aucun Pod'}. Attendu une image épinglée et les réglages du standard restricted.",
    )
    rc, ip, _ = _kubectl(host, f"-n {BOUTIQUE} get service {SERVICE} -o jsonpath='{{.spec.clusterIP}}'")
    assert rc == 0 and ip, message(
        en=f"The shop's stable address, {SERVICE}, no longer exists.",
        fr=f"L'adresse stable de la boutique, {SERVICE}, n'existe plus.",
    )
    code = host.run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 10 http://{ip}/").stdout.strip()
    assert code == "200", message(
        en=f"The shop answers {code or 'nothing'} instead of 200 at its stable address: hardened, it no "
        "longer serves its pages.",
        fr=f"La boutique répond {code or 'rien'} au lieu de 200 à son adresse stable : durcie, elle ne "
        "sert plus ses pages.",
    )
