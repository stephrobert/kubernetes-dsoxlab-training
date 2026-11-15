"""test_functional.py : k8s-challenge-confiner-et-detecter

Le challenge du module « Confiner et détecter ». Ces tests lisent l'état du
NŒUD et du CLUSTER, jamais les commandes tapées ni les fichiers YAML de
l'apprenant. Un test vérifie un seul état de la fiche, dans l'ordre de la fiche.

Les preuves qui comptent exercent les deux côtés, comme dans les labs attestés
dont elles viennent : une écriture refusée ET une lecture permise, un chmod
refusé ET un fichier créé, un client hors maillage bloqué ET un client maillé
qui passe, un flux fermé ET le flux prévu ouvert. Une moitié seule serait vraie
avant le travail, ou vraie avec une application cassée.

Falco est lu sur sa sortie JSON (/var/log/falco/events.json, posée par le
setup) : le correcteur ouvre LUI-MÊME un shell dans le Pod protégé, puis dans un
Pod d'un autre namespace, et cherche l'alerte de la règle demandée parmi les
lignes écrites depuis. Les deux derniers tests réutilisent la première mesure :
« aucune alerte ailleurs » et « règles fournies intactes » sont vrais avant tout
travail, ils n'ont de sens qu'accolés à une règle qui alerte bel et bien.

Les seize tests échouent sur l'état que pose le setup : aucun profil chargé,
aucun Pod confiné, maillage permissif, donnees ouvert, aucune RuntimeClass, et
aucune règle Falco personnalisée.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-cp.lab"

COFFRE = "coffre"
MAILLE = "maille"
EXTERIEUR = "exterieur"
DONNEES = "donnees"

PROFIL_APPARMOR = "k8s-coffre-sans-tmp"
POD_APPARMOR = "lecteur"
ANNOTATION_OBSOLETE = "container.apparmor.security.beta.kubernetes.io/"

RACINE_SECCOMP = "/var/lib/kubelet/seccomp"
CHEMIN_SECCOMP = "profiles/coffre-sans-chmod.json"
POD_SECCOMP = "calcul"
FAMILLE_CHMOD = {"chmod", "fchmod", "fchmodat"}

CIBLE_MAILLE = "http://api.maille.svc.cluster.local/"
BUDGET_PROPAGATION_S = 60

RUNTIME_CLASS = "gvisor-coffre"
HANDLER = "runsc"
POD_BAC_A_SABLE = "isole"
TEMOIN_NOYAU = "ordinaire"

FALCO_SERVICE = "falco-modern-bpf.service"
FALCO_JOURNAL = "/var/log/falco/events.json"
FALCO_REGLES = "/etc/falco/falco_rules.yaml"
REGLE = "coffre-shell"
PRIORITE = "critical"
POD_PROTEGE = "tresor"
POD_AILLEURS = "curieux"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"{KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _dans(host, ns: str, pod: str, commande: str, conteneur: str = ""):
    option = f"-c {conteneur} " if conteneur else ""
    return _kubectl(host, f"-n {ns} exec {pod} {option}--request-timeout=30s -- sh -c '{commande}'")


def _pod(host, ns: str, nom: str) -> dict | None:
    rc, sortie, _ = _kubectl(host, f"-n {ns} get pod {nom} -o json")
    return json.loads(sortie) if rc == 0 and sortie else None


def _exiger_en_marche(host, ns: str, nom: str) -> dict:
    pod = _pod(host, ns, nom)
    assert pod is not None, message(
        en=f"No Pod {nom} in namespace {ns}.",
        fr=f"Aucun Pod {nom} dans le namespace {ns}.",
    )
    phase = pod["status"].get("phase")
    assert phase == "Running", message(
        en=f"Pod {nom} of {ns} is {phase}, not Running: its events "
        f"(kubectl -n {ns} describe pod {nom}) say why.",
        fr=f"Le Pod {nom} de {ns} est en {phase}, et non Running : ses events "
        f"(kubectl -n {ns} describe pod {nom}) disent pourquoi.",
    )
    return pod


def _profils_du_pod(pod: dict, champ: str) -> list[dict]:
    """Les profils déclarés au niveau du Pod et de chacun de ses conteneurs."""
    contextes = [pod["spec"].get("securityContext") or {}] + [
        c.get("securityContext") or {} for c in pod["spec"].get("containers") or []
    ]
    return [ctx[champ] for ctx in contextes if ctx.get(champ)]


# ======================================================================
# AppArmor
# ======================================================================
def test_profil_apparmor_charge_en_enforce(host):
    res = host.run("sudo aa-status --json")
    assert res.rc == 0, message(
        en=f"aa-status failed on {NOEUD}: {res.stderr.strip()[:200]}",
        fr=f"aa-status a échoué sur {NOEUD} : {res.stderr.strip()[:200]}",
    )
    profils = json.loads(res.stdout).get("profiles", {})
    assert PROFIL_APPARMOR in profils, message(
        en=f"No profile named {PROFIL_APPARMOR} is loaded in the kernel of {NOEUD}. A profile "
        "written on disk confines nothing until the kernel has read it, and the name the kernel "
        "knows is the one written after the word profile, not the file name.",
        fr=f"Aucun profil nommé {PROFIL_APPARMOR} n'est chargé dans le noyau de {NOEUD}. Un "
        "profil écrit sur le disque ne confine rien tant que le noyau ne l'a pas lu, et le nom "
        "que le noyau connaît est celui qui suit le mot profile, pas le nom du fichier.",
    )
    assert profils[PROFIL_APPARMOR] == "enforce", message(
        en=f"Profile {PROFIL_APPARMOR} is in {profils[PROFIL_APPARMOR]} mode. In complain mode, "
        "violations are logged and NOT blocked.",
        fr=f"Le profil {PROFIL_APPARMOR} est en mode {profils[PROFIL_APPARMOR]}. En complain, "
        "les violations sont journalisées et PAS bloquées.",
    )


def test_pod_confine_tourne_sur_le_noeud_du_profil_et_le_declare(host):
    pod = _exiger_en_marche(host, COFFRE, POD_APPARMOR)
    noeud = pod["spec"].get("nodeName")
    assert noeud == NOEUD, message(
        en=f"Pod {POD_APPARMOR} runs on {noeud}, while the profile is loaded on {NOEUD}. A "
        "profile loaded on one node only counts on that node.",
        fr=f"Le Pod {POD_APPARMOR} tourne sur {noeud}, alors que le profil est chargé sur "
        f"{NOEUD}. Un profil chargé sur un nœud ne vaut que sur ce nœud.",
    )
    annotations = pod["metadata"].get("annotations") or {}
    obsoletes = [c for c in annotations if c.startswith(ANNOTATION_OBSOLETE)]
    assert not obsoletes, message(
        en=f"The profile is attached through a deprecated annotation ({obsoletes[0] if obsoletes else ''}). "
        "Since 1.30, it is declared in securityContext.appArmorProfile.",
        fr=f"Le profil est rattaché par une annotation obsolète ({obsoletes[0] if obsoletes else ''}). "
        "Depuis la 1.30, il se déclare dans securityContext.appArmorProfile.",
    )
    profils = _profils_du_pod(pod, "appArmorProfile")
    noms = [p.get("localhostProfile") for p in profils if p.get("type") == "Localhost"]
    assert PROFIL_APPARMOR in noms, message(
        en=f"Pod {POD_APPARMOR} declares {profils or 'no AppArmor profile'}. Expected a Localhost "
        f"profile named {PROFIL_APPARMOR}: RuntimeDefault would apply the runtime's profile, "
        "not yours.",
        fr=f"Le Pod {POD_APPARMOR} déclare {profils or 'aucun profil AppArmor'}. Attendu un "
        f"profil Localhost nommé {PROFIL_APPARMOR} : RuntimeDefault appliquerait le profil du "
        "runtime, pas le vôtre.",
    )


def test_ecriture_dans_tmp_refusee_et_lecture_permise(host):
    _exiger_en_marche(host, COFFRE, POD_APPARMOR)
    _, ecriture, _ = _dans(host, COFFRE, POD_APPARMOR,
                           "echo test > /tmp/preuve-apparmor 2>/dev/null; echo CODE=$?")
    assert "CODE=" in ecriture and "CODE=0" not in ecriture, message(
        en=f"The write into /tmp from {POD_APPARMOR} SUCCEEDED (or could not be attempted): the "
        f"container is not confined by the profile. Output: {ecriture}",
        fr=f"L'écriture dans /tmp depuis {POD_APPARMOR} a RÉUSSI (ou n'a pas pu être tentée) : le "
        f"conteneur n'est pas confiné par le profil. Sortie : {ecriture}",
    )
    _, lecture, _ = _dans(host, COFFRE, POD_APPARMOR, "cat /etc/hostname >/dev/null; echo CODE=$?")
    assert "CODE=0" in lecture, message(
        en="Reading /etc/hostname fails too: the profile forbids more than writing into /tmp. "
        f"A confinement that breaks the application is worth no more than none. Output: {lecture}",
        fr="La lecture de /etc/hostname échoue aussi : le profil interdit plus que l'écriture "
        "dans /tmp. Un confinement qui casse l'application ne vaut pas mieux que rien. "
        f"Sortie : {lecture}",
    )


# ======================================================================
# seccomp
# ======================================================================
def test_profil_seccomp_refuse_chmod_et_autorise_le_reste(host):
    chemin = f"{RACINE_SECCOMP}/{CHEMIN_SECCOMP}"
    res = host.run(f"sudo cat {chemin}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No readable profile at {chemin} on {NOEUD}. The kubelet looks for local profiles "
        f"under {RACINE_SECCOMP}.",
        fr=f"Aucun profil lisible en {chemin} sur {NOEUD}. Le kubelet cherche les profils locaux "
        f"sous {RACINE_SECCOMP}.",
    )
    try:
        profil = json.loads(res.stdout)
    except json.JSONDecodeError as erreur:
        pytest.fail(message(
            en=f"The profile is not valid JSON: {erreur}.",
            fr=f"Le profil n'est pas un JSON valide : {erreur}.",
        ))
    assert profil.get("defaultAction") == "SCMP_ACT_ALLOW", message(
        en=f"defaultAction is {profil.get('defaultAction')}. Allow by default and refuse one "
        "family: refusing by default means listing every call a container needs to start.",
        fr=f"defaultAction vaut {profil.get('defaultAction')}. Autoriser par défaut et refuser une "
        "famille : refuser par défaut oblige à lister chaque appel dont un conteneur a besoin.",
    )
    refuses = {
        nom
        for regle in profil.get("syscalls") or []
        if regle.get("action") in ("SCMP_ACT_ERRNO", "SCMP_ACT_KILL", "SCMP_ACT_KILL_PROCESS")
        for nom in regle.get("names") or []
    }
    manquants = FAMILLE_CHMOD - refuses
    assert not manquants, message(
        en=f"The profile does not refuse: {', '.join(sorted(manquants))}. The family has three "
        "calls, and a modern libc goes through fchmodat.",
        fr=f"Le profil ne refuse pas : {', '.join(sorted(manquants))}. La famille compte trois "
        "appels, et une libc moderne passe par fchmodat.",
    )


def test_pod_declare_le_profil_seccomp_local_et_tourne(host):
    pod = _exiger_en_marche(host, COFFRE, POD_SECCOMP)
    profils = _profils_du_pod(pod, "seccompProfile")
    chemins = {p.get("localhostProfile") for p in profils if p.get("type") == "Localhost"}
    assert CHEMIN_SECCOMP in chemins, message(
        en=f"Pod {POD_SECCOMP} declares {profils or 'no seccomp profile'}. Expected type Localhost "
        f"with the path relative to {RACINE_SECCOMP}: {CHEMIN_SECCOMP}, no leading slash.",
        fr=f"Le Pod {POD_SECCOMP} déclare {profils or 'aucun profil seccomp'}. Attendu le type "
        f"Localhost avec le chemin relatif à {RACINE_SECCOMP} : {CHEMIN_SECCOMP}, sans barre "
        "oblique initiale.",
    )


def test_chmod_echoue_et_creation_de_fichier_fonctionne(host):
    _exiger_en_marche(host, COFFRE, POD_SECCOMP)
    rc, sortie, diagnostic = _dans(host, COFFRE, POD_SECCOMP, "touch /tmp/preuve && echo ok")
    assert rc == 0 and sortie == "ok", message(
        en=f"The confined container cannot even create a file: the profile refuses more than "
        f"the chmod family. Output: {diagnostic}",
        fr=f"Le conteneur confiné ne peut même plus créer un fichier : le profil refuse plus que "
        f"la famille chmod. Sortie : {diagnostic}",
    )
    rc, _, diagnostic = _dans(host, COFFRE, POD_SECCOMP, "chmod 700 /tmp/preuve")
    assert rc != 0, message(
        en="The confined container changed a file's permissions: the filter does not apply.",
        fr="Le conteneur confiné a changé les permissions d'un fichier : le filtre ne s'applique pas.",
    )
    assert "not permitted" in diagnostic.lower(), message(
        en=f"chmod failed, but not for the expected reason: {diagnostic}. A call refused by "
        "seccomp returns EPERM, Operation not permitted.",
        fr=f"chmod a échoué, mais pas pour la raison attendue : {diagnostic}. Un appel refusé par "
        "seccomp rend EPERM, Operation not permitted.",
    )


# ======================================================================
# mTLS (Istio)
# ======================================================================
def test_namespace_maille_exige_le_tls_mutuel(host):
    rc, sortie, diagnostic = _kubectl(host, f"-n {MAILLE} get peerauthentication -o json")
    assert rc == 0, message(
        en=f"Cannot read the mesh's authentication policies in {MAILLE}: {diagnostic}",
        fr=f"Impossible de lire les politiques d'authentification du maillage dans {MAILLE} : {diagnostic}",
    )
    objets = json.loads(sortie).get("items", [])
    stricts = [o for o in objets
               if not (o.get("spec") or {}).get("selector")
               and ((o.get("spec") or {}).get("mtls") or {}).get("mode") == "STRICT"]
    modes = {o["metadata"]["name"]: ((o.get("spec") or {}).get("mtls") or {}).get("mode") for o in objets}
    assert stricts, message(
        en=f"Nothing in {MAILLE} requires mutual TLS for the whole namespace (seen: {modes or 'nothing'}). "
        "The default mode accepts encrypted and plain traffic alike; a selector limits the "
        "requirement to the Pods it names.",
        fr=f"Rien dans {MAILLE} n'exige le TLS mutuel pour tout le namespace (vu : {modes or 'rien'}). "
        "Le mode par défaut accepte le chiffré comme le clair ; un selector limite l'exigence "
        "aux Pods qu'il désigne.",
    )


def _joint_api(host, ns: str, pod: str) -> bool:
    rc, _, _ = _kubectl(host, f"-n {ns} exec {pod} -c outil --request-timeout=30s "
                              f"-- wget -qO- -T 5 {CIBLE_MAILLE}")
    return rc == 0


def test_client_sans_sidecar_bloque_et_client_maille_passe(host):
    for ns, pod in ((MAILLE, "api"), (MAILLE, "client-maille"), (EXTERIEUR, "client-nu")):
        _exiger_en_marche(host, ns, pod)
    fin = time.monotonic() + BUDGET_PROPAGATION_S
    nu_passe = True
    while time.monotonic() < fin:
        nu_passe = _joint_api(host, EXTERIEUR, "client-nu")
        if not nu_passe:
            break
        time.sleep(3)
    assert not nu_passe, message(
        en=f"After {BUDGET_PROPAGATION_S} seconds, client-nu (no sidecar, in {EXTERIEUR}) still "
        f"reaches {CIBLE_MAILLE} in plain text: the namespace of the CALLED service does not "
        "require mutual TLS.",
        fr=f"Après {BUDGET_PROPAGATION_S} secondes, client-nu (sans sidecar, dans {EXTERIEUR}) "
        f"joint toujours {CIBLE_MAILLE} en clair : le namespace du service APPELÉ n'exige pas le "
        "TLS mutuel.",
    )
    assert _joint_api(host, MAILLE, "client-maille"), message(
        en=f"client-maille no longer reaches {CIBLE_MAILLE}, although it carries a sidecar. "
        "Requiring mutual TLS must cut what is outside the mesh, not the mesh itself.",
        fr=f"client-maille ne joint plus {CIBLE_MAILLE}, alors qu'il porte un sidecar. Exiger le "
        "TLS mutuel doit couper ce qui est hors du maillage, pas le maillage lui-même.",
    )


# ======================================================================
# NetworkPolicy
# ======================================================================
def _ip(host, ns: str, pod: str) -> str:
    rc, ip, diagnostic = _kubectl(host, f"-n {ns} get pod {pod} -o jsonpath='{{.status.podIP}}'")
    assert rc == 0 and ip, message(
        en=f"Pod {pod} of {ns} has no address: the setup placed it, it was not to be removed. {diagnostic}",
        fr=f"Le Pod {pod} de {ns} n'a pas d'adresse : le setup l'a posé, il ne fallait pas le "
        f"retirer. {diagnostic}",
    )
    return ip


def _joint(host, depuis: str, ns_cible: str, cible: str) -> bool:
    """Requête HTTP par ADRESSE depuis un Pod de donnees : le DNS ne s'en mêle pas."""
    rc, _, _ = _kubectl(host, f"-n {DONNEES} exec {depuis} --request-timeout=30s -- "
                              f"wget -q -O- -T 4 http://{_ip(host, ns_cible, cible)}/")
    return rc == 0


def _resout(host, depuis: str) -> bool:
    rc, _, _ = _kubectl(host, f"-n {DONNEES} exec {depuis} --request-timeout=30s -- "
                              "nslookup kubernetes.default.svc.cluster.local")
    return rc == 0


def test_namespace_ferme_par_defaut_dans_les_deux_sens(host):
    rc, sortie, diagnostic = _kubectl(host, f"-n {DONNEES} get networkpolicy -o json")
    assert rc == 0, message(
        en=f"Cannot read the network policies of {DONNEES}: {diagnostic}",
        fr=f"Impossible de lire les politiques réseau de {DONNEES} : {diagnostic}",
    )
    directions = set()
    for politique in json.loads(sortie).get("items", []):
        spec = politique.get("spec") or {}
        if (spec.get("podSelector") or {}) != {}:
            continue
        for direction in spec.get("policyTypes") or []:
            if not spec.get(direction.lower()):
                directions.add(direction)
    manquantes = {"Ingress", "Egress"} - directions
    assert not manquantes, message(
        en=f"No default policy of {DONNEES} closes: {', '.join(sorted(manquantes))}. A default "
        "policy selects every Pod and declares the direction without any rule for it.",
        fr=f"Aucune politique par défaut de {DONNEES} ne ferme : {', '.join(sorted(manquantes))}. "
        "Une politique par défaut sélectionne tous les Pods et déclare la direction sans aucune "
        "règle pour elle.",
    )
    assert not _joint(host, "intrus", DONNEES, "annuaire"), message(
        en="intrus still reaches annuaire: inbound traffic is not closed for every Pod.",
        fr="intrus joint toujours annuaire : l'entrée n'est pas fermée pour tous les Pods.",
    )
    assert not _joint(host, "base", EXTERIEUR, "vitrine"), message(
        en=f"base still reaches vitrine, outside {DONNEES}: outbound traffic is not closed.",
        fr=f"base joint toujours vitrine, hors de {DONNEES} : la sortie n'est pas fermée.",
    )


def test_seul_le_flux_prevu_atteint_la_base(host):
    assert _joint(host, "appli", DONNEES, "base"), message(
        en="appli no longer reaches base on port 80. The flow must be allowed at both ends: "
        "appli's outbound AND base's inbound.",
        fr="appli ne joint plus base sur le port 80. Le flux doit être permis aux deux bouts : "
        "la sortie d'appli ET l'entrée de base.",
    )
    assert not _joint(host, "intrus", DONNEES, "base"), message(
        en="intrus reaches base although nothing allows it: the rule opened is broader than "
        "the single appli to base flow.",
        fr="intrus joint base alors que rien ne l'y autorise : la règle ouverte est plus large "
        "que le seul flux d'appli vers base.",
    )


def test_dns_resout_sans_rouvrir_la_sortie(host):
    assert _resout(host, "appli"), message(
        en="appli resolves no name any more. A closed egress cuts DNS too: the cluster's "
        "resolver listens on port 53, over UDP and TCP.",
        fr="appli ne résout plus aucun nom. Une sortie fermée coupe aussi le DNS : le résolveur "
        "du cluster écoute sur le port 53, en UDP et en TCP.",
    )
    assert not _joint(host, "appli", EXTERIEUR, "vitrine"), message(
        en=f"DNS works, but appli reaches vitrine, outside {DONNEES}: the egress was reopened "
        "too broadly. An egress rule with no destination allows every destination.",
        fr=f"Le DNS fonctionne, mais appli joint vitrine, hors de {DONNEES} : la sortie a été "
        "rouverte trop largement. Une règle de sortie sans destination les autorise toutes.",
    )


# ======================================================================
# gVisor
# ======================================================================
def test_runtimeclass_designe_le_runtime_du_noeud(host):
    rc, sortie, diagnostic = _kubectl(host, f"get runtimeclass {RUNTIME_CLASS} -o json")
    assert rc == 0 and sortie, message(
        en=f"No RuntimeClass named {RUNTIME_CLASS}. It is a cluster object, with no namespace. "
        f"{diagnostic}",
        fr=f"Aucune RuntimeClass nommée {RUNTIME_CLASS}. C'est un objet de cluster, sans "
        f"namespace. {diagnostic}",
    )
    handler = json.loads(sortie).get("handler")
    assert handler == HANDLER, message(
        en=f"The RuntimeClass names handler {handler}. containerd knows the sandbox runtime "
        "under another name, written in /etc/containerd/config.toml.",
        fr=f"La RuntimeClass désigne le handler {handler}. containerd connaît le runtime bac à "
        "sable sous un autre nom, écrit dans /etc/containerd/config.toml.",
    )


def _noyau(host, pod: str) -> str:
    rc, sortie, diagnostic = _kubectl(host, f"-n {COFFRE} exec {pod} --request-timeout=30s -- cat /proc/version")
    assert rc == 0 and sortie, message(
        en=f"Cannot read the kernel from Pod {pod}. {diagnostic}",
        fr=f"Impossible de lire le noyau depuis le Pod {pod}. {diagnostic}",
    )
    return sortie


def test_pod_en_bac_a_sable_lit_un_autre_noyau(host):
    pod = _exiger_en_marche(host, COFFRE, POD_BAC_A_SABLE)
    declare = pod["spec"].get("runtimeClassName")
    assert declare == RUNTIME_CLASS, message(
        en=f"Pod {POD_BAC_A_SABLE} declares runtimeClassName {declare or 'nothing'}, not "
        f"{RUNTIME_CLASS}. The field cannot change on an existing Pod: recreate it.",
        fr=f"Le Pod {POD_BAC_A_SABLE} déclare runtimeClassName {declare or 'rien'}, et non "
        f"{RUNTIME_CLASS}. Le champ ne change pas sur un Pod existant : il faut le recréer.",
    )
    noyau_isole = _noyau(host, POD_BAC_A_SABLE)
    noyau_temoin = _noyau(host, TEMOIN_NOYAU)
    noyau_machine = host.run("uname -r").stdout.strip()
    assert noyau_machine and noyau_machine in noyau_temoin, message(
        en=f"The witness Pod {TEMOIN_NOYAU} does not read the machine's kernel ({noyau_machine}) "
        f"but {noyau_temoin}: without that comparison point, the measurement means nothing.",
        fr=f"Le Pod témoin {TEMOIN_NOYAU} ne lit pas le noyau de la machine ({noyau_machine}) "
        f"mais {noyau_temoin} : sans ce point de comparaison, la mesure ne veut rien dire.",
    )
    assert noyau_machine not in noyau_isole and noyau_isole != noyau_temoin, message(
        en=f"Pod {POD_BAC_A_SABLE} reads the machine's kernel: {noyau_isole}. It is not in the sandbox.",
        fr=f"Le Pod {POD_BAC_A_SABLE} lit le noyau de la machine : {noyau_isole}. Il n'est pas "
        "dans le bac à sable.",
    )


# ======================================================================
# Falco
# ======================================================================
_FALCO: dict[str, list[dict]] = {}


def _falco_actif(host) -> None:
    res = host.run(f"systemctl is-active {FALCO_SERVICE}")
    assert res.stdout.strip() == "active", message(
        en=f"Falco is not running on {NOEUD} ({res.stdout.strip()}). A rule file Falco cannot "
        f"load stops the service: sudo journalctl -u {FALCO_SERVICE} names the faulty line.",
        fr=f"Falco ne tourne pas sur {NOEUD} ({res.stdout.strip()}). Un fichier de règles que "
        f"Falco ne sait pas charger arrête le service : sudo journalctl -u {FALCO_SERVICE} "
        "nomme la ligne fautive.",
    )


def _lignes_du_journal(host) -> int:
    res = host.run(f"sudo sh -c 'if [ -f {FALCO_JOURNAL} ]; then wc -l < {FALCO_JOURNAL}; else echo 0; fi'")
    try:
        return int(res.stdout.strip() or 0)
    except ValueError:
        return 0


def _alertes_depuis(host, depuis: int) -> list[dict]:
    res = host.run(f"sudo tail -n +{depuis + 1} {FALCO_JOURNAL}")
    alertes = []
    for brute in res.stdout.splitlines():
        ligne = brute.strip()
        if not ligne.startswith("{"):
            continue
        try:
            alertes.append(json.loads(ligne))
        except json.JSONDecodeError:
            continue
    return alertes


def _shell(host, ns: str, pod: str) -> None:
    rc, _, diagnostic = _kubectl(host, f"-n {ns} exec {pod} --request-timeout=30s -- sh -c 'echo dsoxlab-correcteur'")
    assert rc == 0, message(
        en=f"The grader cannot open a shell in Pod {pod} of {ns}: the setup placed it, it stays. "
        f"{diagnostic}",
        fr=f"Le correcteur ne peut pas ouvrir de shell dans le Pod {pod} de {ns} : le setup l'a "
        f"posé, il reste. {diagnostic}",
    )


def _alertes_apres_un_shell(host, ns: str, pod: str, essais: int) -> list[dict]:
    depuis = _lignes_du_journal(host)
    _shell(host, ns, pod)
    trouvees: list[dict] = []
    for _ in range(essais):
        time.sleep(2)
        trouvees = [a for a in _alertes_depuis(host, depuis) if a.get("rule") == REGLE]
        if trouvees:
            break
    return trouvees


def _alertes_du_coffre(host) -> list[dict]:
    """Un shell dans le Pod protégé, et les alertes de la règle qui ont suivi.
    Mesuré une fois par check : les deux derniers tests s'appuient dessus."""
    if "coffre" not in _FALCO:
        _falco_actif(host)
        _exiger_en_marche(host, COFFRE, POD_PROTEGE)
        _FALCO["coffre"] = _alertes_apres_un_shell(host, COFFRE, POD_PROTEGE, essais=15)
    return _FALCO["coffre"]


def test_shell_dans_le_coffre_declenche_la_regle_falco(host):
    alertes = _alertes_du_coffre(host)
    assert alertes, message(
        en=f"A shell opened in Pod {POD_PROTEGE} of {COFFRE} raised no alert of rule {REGLE} within "
        f"30 seconds (read in {FALCO_JOURNAL}). The rule must exist under that exact name, be "
        "loaded by Falco, and match a shell process started in a container of that namespace.",
        fr=f"Un shell ouvert dans le Pod {POD_PROTEGE} de {COFFRE} n'a levé aucune alerte de la "
        f"règle {REGLE} en 30 secondes (lu dans {FALCO_JOURNAL}). La règle doit exister sous ce "
        "nom exact, être chargée par Falco, et reconnaître un processus shell lancé dans un "
        "conteneur de ce namespace.",
    )
    priorites = sorted({str(a.get("priority", "")).lower() for a in alertes})
    assert PRIORITE in priorites, message(
        en=f"Rule {REGLE} fires, but with priority {priorites} instead of {PRIORITE.upper()}.",
        fr=f"La règle {REGLE} alerte, mais avec la priorité {priorites} au lieu de {PRIORITE.upper()}.",
    )


def test_shell_ailleurs_ne_declenche_pas_la_regle(host):
    assert _alertes_du_coffre(host), message(
        en=f"Rule {REGLE} does not fire for a shell in {COFFRE}: that it stays silent elsewhere "
        "proves nothing yet.",
        fr=f"La règle {REGLE} n'alerte pas pour un shell dans {COFFRE} : qu'elle se taise ailleurs "
        "ne prouve encore rien.",
    )
    _exiger_en_marche(host, EXTERIEUR, POD_AILLEURS)
    ailleurs = _alertes_apres_un_shell(host, EXTERIEUR, POD_AILLEURS, essais=6)
    assert not ailleurs, message(
        en=f"A shell opened in Pod {POD_AILLEURS} of {EXTERIEUR} raises rule {REGLE} too: its "
        f"condition does not restrict it to the {COFFRE} namespace.",
        fr=f"Un shell ouvert dans le Pod {POD_AILLEURS} de {EXTERIEUR} déclenche aussi la règle "
        f"{REGLE} : sa condition ne la limite pas au namespace {COFFRE}.",
    )


def test_regles_falco_fournies_intactes(host):
    attendu = host.run(
        "awk '$2 == \"etc/falco/falco_rules.yaml\" {print $1}' /var/lib/dpkg/info/falco.md5sums"
    ).stdout.strip()
    assert attendu, message(
        en="The Falco package no longer records the fingerprint of its rules: is it still installed?",
        fr="Le paquet Falco ne garde plus l'empreinte de ses règles : est-il toujours installé ?",
    )
    res = host.run(f"sudo md5sum {FALCO_REGLES}")
    actuel = res.stdout.split()[0] if res.rc == 0 and res.stdout.strip() else "absent"
    assert actuel == attendu, message(
        en=f"{FALCO_REGLES} differs from the file shipped with the package ({actuel} instead of "
        f"{attendu}). The shipped rules are replaced at each update: a custom rule lives in "
        "its own file, which Falco also loads.",
        fr=f"{FALCO_REGLES} diffère du fichier livré par le paquet ({actuel} au lieu de "
        f"{attendu}). Les règles fournies sont remplacées à chaque mise à jour : une règle "
        "personnalisée vit dans son propre fichier, que Falco charge aussi.",
    )
    assert _alertes_du_coffre(host), message(
        en=f"The shipped rules are intact, but rule {REGLE} raises nothing: leaving the rules "
        "alone is only half of the requirement.",
        fr=f"Les règles fournies sont intactes, mais la règle {REGLE} ne lève rien : ne pas "
        "toucher aux règles n'est que la moitié de la demande.",
    )
