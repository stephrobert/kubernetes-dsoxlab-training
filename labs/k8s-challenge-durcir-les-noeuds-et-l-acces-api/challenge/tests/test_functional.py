"""test_functional.py : k8s-challenge-durcir-les-noeuds-et-l-acces-api

Ces tests lisent l'état de k8s-w2.lab et de k8s-cp.lab, jamais les commandes
tapées : les ports réellement en écoute, les paquets installés, de VRAIES
sessions SSH par une clé d'essai, les droits sudo calculés par sudo lui-même,
les codes HTTP rendus par le kubelet et l'API server à un client anonyme puis à
un compte sans droit, de vraies connexions neuves entre les nœuds, et un vrai
redémarrage du nœud.

Aucun test n'est vrai avant le travail : le setup laisse deux services
superflus, un compte de prestataire qui entre par mot de passe et tient sudo,
un kubelet ouvert à l'anonyme avec son port en lecture seule, aucun pare-feu,
et un API server qui répond à l'anonyme sur /version.

Les triches refusées par construction :
  - arrêter les services sans les retirer : le redémarrage les ramène ;
  - couper TOUT accès anonyme à l'API server : la lecture de cluster-info, dont
    kubeadm join a besoin, tombe avec ;
  - un pare-feu qui ferme tout : le kubelet, SSH depuis le control plane et le
    trafic des Pods doivent passer ;
  - un pare-feu chargé à la main : il ne revient pas après le redémarrage ;
  - arrêter le kubelet pour qu'il ne réponde plus : le test attend un 401, pas
    un refus de connexion, et le nœud doit rester Ready.

Deux exigences sont bloquantes : l'API server qui ne répond à l'anonyme que
pour la santé et la découverte, et le nœud qui reste durci et Ready après un
redémarrage. Ce sont les deux « sans rien casser » du module.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_host_ip, message

NOEUD = "k8s-w2.lab"
PLAN = "k8s-cp.lab"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
GROUPE = "ops-noeuds"
PRESTATAIRE = "prestataire"
CLE_ESSAI = "/root/.lab-durcir/essai_ed25519"
OPTIONS_SSH = (
    "-o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
    "-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
)
PORTS_SUPERFLUS = (80, 9090, 10255)
NS = "sonde-durcissement"
BUSYBOX = "busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
NGINX = "nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d"
API = "https://127.0.0.1:6443"
CLUSTER_INFO = "/api/v1/namespaces/kube-public/configmaps/cluster-info"
SANTE = ("/livez", "/readyz", "/healthz")
FERMES = ("/version", "/api", "/apis", "/api/v1/namespaces/default/pods")
# Les deux liaisons d'origine vers les anonymes (relevé du 2026-11-17,
# kubeadm v1.37) : system:public-info-viewer, posée par l'API server à son
# démarrage, et kubeadm:bootstrap-signer-clusterinfo, créée par kubeadm pour
# la lecture de cluster-info. Toute autre est une porte ouverte.
LIAISONS_KUBEADM = {
    ("ClusterRoleBinding", "", "system:public-info-viewer"),
    ("RoleBinding", "kube-public", "kubeadm:bootstrap-signer-clusterinfo"),
}


@pytest.fixture(scope="module")
def w2():
    return lab_host(NOEUD)


@pytest.fixture(scope="module")
def w1():
    return lab_host("k8s-w1.lab")


@pytest.fixture(scope="module")
def cp():
    return lab_host(PLAN)


@pytest.fixture(scope="module")
def ip_w2():
    return lab_host_ip(NOEUD)


# ----------------------------------------------------------------------
# Outils de lecture
# ----------------------------------------------------------------------
def _ports_en_ecoute(w2) -> set[int]:
    res = w2.run("sudo ss -Htlnu")
    ports = set()
    for ligne in res.stdout.splitlines():
        champs = ligne.split()
        if len(champs) >= 5:
            fin = champs[4].rsplit(":", 1)[-1]
            if fin.isdigit():
                ports.add(int(fin))
    return ports


def _superflus_en_ecoute(w2) -> list[int]:
    return sorted(set(PORTS_SUPERFLUS) & _ports_en_ecoute(w2))


def _chaines_d_entree_en_drop(w2) -> list[str]:
    res = w2.run("sudo nft -j list ruleset")
    if res.rc != 0 or not res.stdout.strip():
        return []
    chaines = []
    for objet in json.loads(res.stdout).get("nftables", []):
        chaine = objet.get("chain")
        if chaine and chaine.get("hook") == "input" and chaine.get("policy") == "drop":
            chaines.append(f"{chaine.get('family')} {chaine.get('table')} {chaine.get('name')}")
    return chaines


def _joint(source, ip: str, port: int) -> bool:
    return source.run(f"nc -z -w 3 {ip} {port}").rc == 0


def _code(host, url: str, jeton: str = "") -> str:
    entete = f"-H 'Authorization: Bearer {jeton}' " if jeton else ""
    res = host.run(f"curl -sk -m 5 -o /dev/null -w '%{{http_code}}' {entete}{url}")
    return res.stdout.strip()


def _session(w2, compte: str) -> tuple[int, str]:
    """Ouvre une session SSH par la clé d'essai : rend (code, diagnostic)."""
    # testinfra lève une exception sur le code 255, celui d'un ssh refusé : la
    # commande sort donc toujours en 0, et le code se lit dans sa sortie.
    res = w2.run(
        f"sudo ssh {OPTIONS_SSH} -i {CLE_ESSAI} {compte}@127.0.0.1 true 2>&1; echo \"code=$?\""
    )
    lignes = res.stdout.strip().splitlines()
    code = int(lignes[-1].removeprefix("code=")) if lignes and lignes[-1].startswith("code=") else -1
    return code, " ".join(lignes[:-1]).strip()


def _sshd_t(w2) -> dict[str, str]:
    res = w2.run("sudo sshd -T")
    assert res.rc == 0, message(
        en=f"sudo sshd -T fails on {NOEUD}: the SSH configuration does not parse. Output: {res.stderr.strip()}",
        fr=f"sudo sshd -T échoue sur {NOEUD} : la configuration SSH ne se lit pas. Sortie : {res.stderr.strip()}",
    )
    valeurs: dict[str, str] = {}
    for ligne in res.stdout.splitlines():
        cle, _, valeur = ligne.partition(" ")
        valeurs.setdefault(cle.lower(), valeur.strip())
    return valeurs


def _pret(cp) -> str:
    return cp.run(
        f"{KUBECTL} get node {NOEUD} -o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'"
    ).stdout.strip()


def _servir_et_joindre(cp) -> tuple[bool, str]:
    """Un Pod nginx sur k8s-w2, joint par un Service depuis un Pod de k8s-w1.

    Rend (joint, diagnostic). Le namespace est retiré dans tous les cas.
    """
    cp.run(f"{KUBECTL} delete namespace {NS} --ignore-not-found --wait=true --timeout=90s")
    cp.run(f"{KUBECTL} create namespace {NS}")
    manifeste = {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {"apiVersion": "v1", "kind": "Pod",
             "metadata": {"name": "web", "namespace": NS, "labels": {"app": "web"}},
             "spec": {"nodeName": NOEUD, "containers": [{"name": "nginx", "image": NGINX}]}},
            {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "web", "namespace": NS},
             "spec": {"selector": {"app": "web"}, "ports": [{"port": 80, "targetPort": 80}]}},
            {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "client", "namespace": NS},
             "spec": {"nodeName": "k8s-w1.lab",
                      "containers": [{"name": "c", "image": BUSYBOX, "command": ["sleep", "600"]}]}},
        ],
    }
    # Juste après un redémarrage de l'API server, le controller manager met
    # quelques secondes à reprendre : le compte de service `default` d'un
    # namespace neuf n'existe pas encore, et l'API refuse les Pods (mesuré le
    # 2026-11-22 : premier passage sans Pod, les suivants verts).
    for _ in range(30):
        if cp.run(f"{KUBECTL} -n {NS} get serviceaccount default").rc == 0:
            break
        time.sleep(2)
    applique = cp.run(f"echo '{json.dumps(manifeste)}' | {KUBECTL} apply -f -")
    try:
        if applique.rc != 0:
            return False, f"les Pods de sonde ne se créent pas : {applique.stderr.strip()[:200]}"
        pret = cp.run(f"{KUBECTL} -n {NS} wait --for=condition=Ready pod/web pod/client --timeout=240s")
        if pret.rc != 0:
            etat = cp.run(f"{KUBECTL} -n {NS} get pods -o wide --no-headers").stdout.strip()
            evenements = cp.run(
                f"{KUBECTL} -n {NS} get events --sort-by=.lastTimestamp -o custom-columns=R:.reason,M:.message "
                "--no-headers"
            ).stdout.strip().splitlines()[-3:]
            return False, f"Pods de sonde pas prêts ({etat}) : {' / '.join(evenements)[:300]}"
        res = cp.run(f"{KUBECTL} -n {NS} exec client -- wget -qO- -T 5 http://web.{NS}/")
        if "Welcome to nginx" not in res.stdout:
            return False, "un Pod de k8s-w1 ne joint pas le Pod de k8s-w2 par son Service"
        res = cp.run(f"{KUBECTL} -n {NS} logs web --request-timeout=15s")
        if res.rc != 0:
            return False, f"kubectl logs sur le Pod de k8s-w2 échoue : {res.stderr.strip()[:160]}"
        return True, ""
    finally:
        cp.run(f"{KUBECTL} delete namespace {NS} --ignore-not-found --wait=true --timeout=120s")


# ----------------------------------------------------------------------
# 1. La surface du nœud est réduite.
# ----------------------------------------------------------------------
def test_la_surface_du_noeud_est_reduite(w2):
    ecarts = []
    ouverts = [p for p in _superflus_en_ecoute(w2) if p != 10255]
    if ouverts:
        ecarts.append(f"le(s) port(s) {ouverts} écoute(nt) encore")
    statut = w2.run("dpkg-query -W -f='${db:Status-Abbrev}' apache2").stdout.strip()
    if statut.startswith(("ii", "rc")):
        ecarts.append(f"apache2 n'est pas purgé (état dpkg « {statut} »)")
    unite = "releve-inventaire.socket"
    actif = w2.run(f"systemctl is-active {unite}").stdout.strip()
    active = w2.run(f"systemctl is-enabled {unite}").stdout.strip()
    if actif == "active" or active == "enabled":
        ecarts.append(f"{unite} est {actif}, {active}")
    assert not ecarts, message(
        en="The node still exposes what it does not need: " + "; ".join(ecarts) + ". A package is purged, "
        "and a unit that no package provides is stopped and disabled, socket included.",
        fr="Le nœud expose encore ce dont il n'a pas besoin : " + "; ".join(ecarts) + ". Un paquet se purge, "
        "et une unité qu'aucun paquet ne fournit s'arrête et se désactive, socket compris.",
    )


# ----------------------------------------------------------------------
# 2. SSH est réservé au groupe, par clé seulement.
# ----------------------------------------------------------------------
def test_ssh_est_reserve_au_groupe_et_par_cle(w2):
    valeurs = _sshd_t(w2)
    ecarts = []
    if valeurs.get("allowgroups", "").split() != [GROUPE]:
        ecarts.append(f"allowgroups vaut « {valeurs.get('allowgroups', '')} »")
    if valeurs.get("passwordauthentication") != "no":
        ecarts.append("le mot de passe est encore accepté")
    if valeurs.get("permitrootlogin") != "no":
        ecarts.append(f"permitrootlogin vaut {valeurs.get('permitrootlogin')}")
    for compte in ("ansible", "student"):
        rc, diag = _session(w2, compte)
        if rc != 0:
            ecarts.append(f"une session {compte} est refusée ({diag[:80]})")
    # Cinq essais : un ancien « sshd -D [listener] » garde l'ancienne
    # configuration et ne sert qu'une partie des connexions (mesuré le
    # 2026-11-17 dans le lab guidé).
    ouvertes = sum(1 for _ in range(5) if _session(w2, PRESTATAIRE)[0] == 0)
    if ouvertes:
        ecarts.append(f"{ouvertes} session(s) {PRESTATAIRE} sur 5 s'ouvrent encore")
    assert not ecarts, message(
        en=f"SSH on {NOEUD} is not restricted as required: " + "; ".join(ecarts) + f". Expected: only the "
        f"members of {GROUPE} (ansible, student), by key, never root.",
        fr=f"SSH sur {NOEUD} n'est pas restreint comme demandé : " + "; ".join(ecarts) + f". Attendu : seuls "
        f"les membres de {GROUPE} (ansible, student), par clé, jamais root.",
    )


# ----------------------------------------------------------------------
# 3. Le prestataire garde son compte et perd ses droits.
# ----------------------------------------------------------------------
def test_le_prestataire_perd_ses_droits(w2):
    assert w2.user(PRESTATAIRE).exists, message(
        en=f"The account {PRESTATAIRE} is gone: its files are kept for the audit, cut its rights instead.",
        fr=f"Le compte {PRESTATAIRE} a disparu : ses fichiers sont gardés pour l'audit, coupez ses droits à la "
        "place.",
    )
    droits = w2.run(f"sudo sudo -l -U {PRESTATAIRE}").stdout
    groupes = w2.run(f"id -nG {PRESTATAIRE}").stdout.split()
    assert "is not allowed to run sudo" in droits or "n'est pas autorisé" in droits, message(
        en=f"sudo -l -U {PRESTATAIRE} still lists rights (groups: {' '.join(groupes)}). A right can come from a "
        "group as well as from a file of /etc/sudoers.d.",
        fr=f"sudo -l -U {PRESTATAIRE} liste encore des droits (groupes : {' '.join(groupes)}). Un droit peut "
        "venir d'un groupe comme d'un fichier de /etc/sudoers.d.",
    )


# ----------------------------------------------------------------------
# 4. Le kubelet refuse l'anonyme, délègue ses décisions, et ferme son port
#    en lecture seule.
# ----------------------------------------------------------------------
def test_le_kubelet_refuse_l_anonyme_et_delegue(w2, cp, ip_w2):
    kubelet = f"https://{ip_w2}:10250/pods"
    anonyme = _code(cp, kubelet)
    cp.run(f"{KUBECTL} delete namespace {NS}-jeton --ignore-not-found --wait=true --timeout=60s")
    cp.run(f"{KUBECTL} create namespace {NS}-jeton")
    cp.run(f"{KUBECTL} -n {NS}-jeton create serviceaccount sans-droit")
    jeton = cp.run(f"{KUBECTL} -n {NS}-jeton create token sans-droit --duration=10m").stdout.strip()
    sans_droit = _code(cp, kubelet, jeton)
    cp.run(f"{KUBECTL} delete namespace {NS}-jeton --ignore-not-found --wait=false")
    lecture_seule = 10255 in _ports_en_ecoute(w2)
    assert anonyme == "401" and sans_droit == "403" and not lecture_seule, message(
        en=f"The kubelet of {NOEUD} answers {anonyme or 'nothing'} to an anonymous client (401 expected), "
        f"{sans_droit or 'nothing'} to an account with no rights (403 expected: it asks the API server), and "
        f"its read-only port 10255 {'still listens' if lecture_seule else 'is closed'}.",
        fr=f"Le kubelet de {NOEUD} répond {anonyme or 'rien'} à un client anonyme (401 attendu), "
        f"{sans_droit or 'rien'} à un compte sans droit (403 attendu : il pose la question à l'API server), et "
        f"son port en lecture seule 10255 {'écoute encore' if lecture_seule else 'est fermé'}.",
    )


# ----------------------------------------------------------------------
# 5. Le pare-feu ne laisse passer que les flux utiles.
# ----------------------------------------------------------------------
def test_le_pare_feu_ne_laisse_passer_que_les_flux_utiles(w2, w1, cp, ip_w2):
    chaines = _chaines_d_entree_en_drop(w2)
    ecarts = []
    if not chaines:
        ecarts.append("aucune chaîne d'entrée en policy drop n'est chargée")
    else:
        if _joint(w1, ip_w2, 22):
            ecarts.append("SSH répond encore à k8s-w1, qui n'est pas un poste d'administration")
        if _joint(w1, ip_w2, 10256):
            ecarts.append("le port 10256 répond encore à k8s-w1")
        if not _joint(w1, ip_w2, 10250):
            ecarts.append("le kubelet refuse k8s-w1")
        if not _joint(cp, ip_w2, 22):
            ecarts.append("SSH refuse le control plane")
        joint, diag = _servir_et_joindre(cp)
        if not joint:
            ecarts.append(diag)
    assert not ecarts, message(
        en=f"The firewall of {NOEUD} does not do its job: " + "; ".join(ecarts) + ". Expected an input chain "
        "with policy drop, SSH from the administration workstation and the control plane only, the kubelet "
        "and the network plugin open to the cluster.",
        fr=f"Le pare-feu de {NOEUD} ne fait pas son travail : " + "; ".join(ecarts) + ". Attendu une chaîne "
        "d'entrée en policy drop, SSH depuis le poste d'administration et le control plane seulement, le "
        "kubelet et le plugin réseau ouverts au cluster.",
    )


# ----------------------------------------------------------------------
# 6. L'API server ne répond à l'anonyme que pour la santé. BLOQUANT.
# ----------------------------------------------------------------------
def test_l_api_server_ne_repond_a_l_anonyme_que_pour_la_sante(cp):
    ecarts = []
    for chemin in FERMES:
        code = _code(cp, f"{API}{chemin}")
        if code != "401":
            ecarts.append(f"{chemin} rend {code or 'rien'}")
    for chemin in SANTE:
        code = _code(cp, f"{API}{chemin}")
        if code != "200":
            ecarts.append(f"{chemin} rend {code or 'rien'} au lieu de 200")
    code = _code(cp, f"{API}{CLUSTER_INFO}")
    if code != "200":
        ecarts.append(f"cluster-info rend {code or 'rien'} : kubeadm join ne trouverait plus le cluster")
    res = cp.run(f"{KUBECTL} get clusterrolebindings,rolebindings -A -o json")
    liaisons = set()
    for objet in json.loads(res.stdout).get("items", []) if res.rc == 0 else []:
        sujets = objet.get("subjects") or []
        if any(s.get("name") in ("system:anonymous", "system:unauthenticated") for s in sujets):
            liaisons.add((objet["kind"], objet["metadata"].get("namespace", ""), objet["metadata"]["name"]))
    if liaisons - LIAISONS_KUBEADM:
        ecarts.append(f"liaison(s) RBAC en trop vers les anonymes : {sorted(liaisons - LIAISONS_KUBEADM)}")
    assert not ecarts, message(
        en="The API server does not answer anonymous clients as required: " + "; ".join(ecarts) + ". Expected "
        "401 everywhere except the health paths and what kubeadm join reads, the configuration in "
        "/etc/kubernetes/authn-config.yaml.",
        fr="L'API server ne répond pas à l'anonyme comme demandé : " + "; ".join(ecarts) + ". Attendu 401 "
        "partout, sauf les chemins de santé et ce que lit kubeadm join, la configuration dans "
        "/etc/kubernetes/authn-config.yaml.",
    )


# ----------------------------------------------------------------------
# 7. Le nœud reste durci et Ready après un redémarrage. BLOQUANT.
# ----------------------------------------------------------------------
def test_le_noeud_reste_durci_apres_redemarrage(w2, cp, ip_w2):
    avant = _chaines_d_entree_en_drop(w2)
    restants = _superflus_en_ecoute(w2)
    assert avant and not restants, message(
        en=f"Nothing to reboot yet on {NOEUD}: drop input chain {'loaded' if avant else 'missing'}, superfluous "
        f"ports still listening: {restants or 'none'}. Harden the node first.",
        fr=f"Rien à redémarrer encore sur {NOEUD} : chaîne d'entrée en drop {'chargée' if avant else 'absente'}, "
        f"ports superflus encore en écoute : {restants or 'aucun'}. Durcissez d'abord le nœud.",
    )
    w2.run("sudo systemd-run --on-active=2 systemctl reboot")
    time.sleep(20)
    for _ in range(36):
        if w2.run("systemctl is-active kubelet").stdout.strip() == "active":
            break
        time.sleep(5)
    time.sleep(15)
    etat = ""
    for _ in range(36):
        etat = _pret(cp)
        if etat == "True":
            break
        time.sleep(5)
    ecarts = []
    if etat != "True":
        ecarts.append(f"le nœud ne revient pas Ready ({etat or 'inconnu'})")
    if not _chaines_d_entree_en_drop(w2):
        ecarts.append("aucune chaîne d'entrée en drop n'est rechargée")
    if _superflus_en_ecoute(w2):
        ecarts.append(f"le(s) port(s) {_superflus_en_ecoute(w2)} écoute(nt) de nouveau")
    if _code(cp, f"https://{ip_w2}:10250/pods") != "401":
        ecarts.append("le kubelet ne rend plus 401 à l'anonyme")
    if etat == "True":
        joint, diag = _servir_et_joindre(cp)
        if not joint:
            ecarts.append(diag)
    assert not ecarts, message(
        en=f"After a real reboot of {NOEUD}: " + "; ".join(ecarts) + ". What is hardened by hand and not "
        "persisted comes back at boot.",
        fr=f"Après un vrai redémarrage de {NOEUD} : " + "; ".join(ecarts) + ". Ce qui est durci à la main sans "
        "être rendu persistant revient au démarrage.",
    )
