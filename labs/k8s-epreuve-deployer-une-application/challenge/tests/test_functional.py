"""test_functional.py : k8s-epreuve-deployer-une-application

Épreuve du niveau 2 (fiche KUBERN-EPREUVE-N2). Ces tests lisent l'état du
cluster « multi », le dossier ~/boutique/ et les volumes sur les nœuds. Un test
vérifie un seul état demandé, P01 à P10.

Cinq états sont critiques (exam_blocking_checks, décision D06) : P01, P02, P05,
P06 et P07. Aucune moyenne ne les compense.

P06 agit sur le cluster, comme la fiche le demande : le correcteur écrit une
donnée dans la base, supprime le Pod qui la porte, et la relit sur le Pod
recréé.

Tous échouent avant le travail : magasin est vide, ~/boutique/ aussi, et aucune
ressource Sauvegarde n'existe. Une attente ne s'ouvre que si l'objet attendu
existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/multi.kubeconfig"
NS = "magasin"
VITRINE, BASE, SAUVEGARDE, AGENT = "vitrine", "catalogue", "sauvegarde", "collecteur"
IMAGE = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
REPLICAS_VITRINE, REPLICAS_BASE = 3, 2
DONNEES = "/data"
ARCHIVES = "archives"
PLANNING = "30 2 * * *"
TAINT = "node-role.kubernetes.io/control-plane"
CRD, API = "sauvegardes.atelier.formation.k8s", "atelier.formation.k8s/v1"
ATTENTE = 150
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _planification(expression: str | None) -> list[str]:
    """Les cinq champs d'une planification cron, zéros de tête retirés : « 30 02 * * * »
    et « 30 2 * * * » disent la même heure."""
    return [(c.lstrip("0") or "0") if c.isdigit() else c for c in (expression or "").split()]


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _attendre(host, args: str, pret) -> dict | None:
    objet = _json(host, args)
    fin = time.monotonic() + ATTENTE
    while objet is not None and not pret(objet) and time.monotonic() < fin:
        time.sleep(PAS)
        objet = _json(host, args) or objet
    return objet


def _deploiement_pret(d: dict) -> bool:
    s = d.get("status") or {}
    voulus = d["spec"].get("replicas", 1)
    return s.get("observedGeneration") == d["metadata"]["generation"] \
        and s.get("updatedReplicas") == voulus and s.get("availableReplicas") == voulus


def _sts_pret(sts: dict) -> bool:
    s = sts.get("status") or {}
    voulus = sts["spec"].get("replicas")
    return s.get("observedGeneration") == sts["metadata"]["generation"] \
        and s.get("readyReplicas") == voulus and s.get("updatedReplicas") == voulus


def _ds_pret(ds: dict) -> bool:
    s = ds.get("status") or {}
    return s.get("observedGeneration") == ds["metadata"]["generation"] \
        and s.get("desiredNumberScheduled", 0) > 0 and s.get("numberReady") == s.get("desiredNumberScheduled")


def _pods(host, selecteur: dict) -> list[dict]:
    texte = ",".join(f"{k}={v}" for k, v in selecteur.items())
    return [p for p in (_json(host, f"-n {NS} get pods -l {texte}") or {}).get("items", [])
            if not p["metadata"].get("deletionTimestamp")]


def _nom_exact(host, sorte: str, nom: str, en: str, fr: str) -> None:
    """Échoue si l'objet n'existe pas sous son nom exact, en citant les noms
    approchants : un overlay avec namePrefix rend prod-vitrine, pas vitrine."""
    if host.run(f"{ADMIN} -n {NS} get {sorte} {nom}").rc == 0:
        return
    approchants = sorted(o["metadata"]["name"] for o in (_json(host, f"-n {NS} get {sorte}") or {}).get("items", [])
                         if nom in o["metadata"]["name"])
    pytest.fail(message(
        en=f"{en} Found under a close name: {approchants}; the requirements ask for exactly {nom}, "
        "with no prefix or suffix." if approchants else en,
        fr=f"{fr} Trouvé sous un nom approchant : {approchants} ; le cahier des charges demande exactement "
        f"{nom}, sans préfixe ni suffixe." if approchants else fr,
    ))


def _vitrine(host) -> dict:
    _nom_exact(host, "deployment", VITRINE,
               en=f"Nothing in {NS} keeps {VITRINE} running with interchangeable copies.",
               fr=f"Rien dans {NS} ne fait tourner {VITRINE} en exemplaires interchangeables.")
    d = _attendre(host, f"-n {NS} get deployment {VITRINE}", _deploiement_pret)
    if d is None:
        pytest.fail(message(
            en=f"Nothing in {NS} keeps {VITRINE} running with interchangeable copies.",
            fr=f"Rien dans {NS} ne fait tourner {VITRINE} en exemplaires interchangeables.",
        ))
    return d


def _base(host) -> dict:
    sts = _attendre(host, f"-n {NS} get statefulset {BASE}", _sts_pret)
    if sts is None:
        pytest.fail(message(
            en=f"Nothing in {NS} serves {BASE} with replicas of stable identity.",
            fr=f"Rien dans {NS} ne sert {BASE} avec des réplicas à identité stable.",
        ))
    return sts


def _est_l_image(image: str | None) -> bool:
    """Même dépôt et même digest que l'image demandée ; le tag est facultatif."""
    if not image or "@" not in image:
        return False
    nom, digest = image.split("@", 1)
    nom = nom.removeprefix("docker.io/library/")
    return digest == IMAGE.split("@")[1] and nom.split(":")[0] == "nginx" \
        and (":" not in nom or nom.split(":")[1] == "1.30.6")


def _revendications_de_la_base(host, sts: dict) -> list[dict]:
    gabarits = [g["metadata"]["name"] for g in sts["spec"].get("volumeClaimTemplates") or []]
    return [pvc for g in gabarits for i in range(sts["spec"].get("replicas", 0))
            if (pvc := _json(host, f"-n {NS} get pvc {g}-{BASE}-{i}")) is not None]


def _sonde_80(c: dict, nom: str) -> bool:
    sonde = c.get(nom) or {}
    ports = {p.get("name"): p.get("containerPort") for p in c.get("ports") or []}
    cible = (sonde.get("httpGet") or sonde.get("tcpSocket") or {}).get("port")
    return (ports.get(cible, cible) if isinstance(cible, str) else cible) == 80


# ----------------------------------------------------------------------
# P01. Base et overlay Kustomize, sans écart avec le cluster. CRITIQUE.
# ----------------------------------------------------------------------
def test_p01_livree_depuis_une_base_et_un_overlay_sans_ecart(host):
    maison = _maison(host)
    overlay = host.file(f"{maison}/boutique/overlays/prod/kustomization.yaml")
    base = host.file(f"{maison}/boutique/base/kustomization.yaml")
    contenu = overlay.content_string if overlay.exists else ""
    assert base.exists and "../../base" in contenu, message(
        en="~/boutique/ does not hold a base and a prod overlay built on it (base/ and overlays/prod/).",
        fr="~/boutique/ ne contient pas une base et un overlay prod construit sur elle (base/ et overlays/prod/).",
    )
    _vitrine(host)
    code = host.run(f"{ADMIN} diff -k {maison}/boutique/overlays/prod").rc
    assert code == 0, message(
        en=f"Comparing the prod overlay with the cluster gives the code {code}: differences, or a comparison "
        "that cannot be made.",
        fr=f"Comparer l'overlay prod au cluster donne le code {code} : des différences, ou une comparaison "
        "impossible.",
    )


# ----------------------------------------------------------------------
# P02. Réplicas disponibles, image par digest, aucun redémarrage. CRITIQUE.
# ----------------------------------------------------------------------
def test_p02_vitrine_disponible_sur_le_digest_sans_redemarrage(host):
    d = _vitrine(host)
    pods = _pods(host, d["spec"]["selector"].get("matchLabels", {}))
    images = {s.get("image") for p in pods for s in (p.get("status") or {}).get("containerStatuses") or []
              if s.get("name") == d["spec"]["template"]["spec"]["containers"][0]["name"]}
    voulue = d["spec"]["template"]["spec"]["containers"][0].get("image")
    redemarres = sorted({p["metadata"]["name"] for p in (_json(host, f"-n {NS} get pods") or {}).get("items", [])
                         for s in ((p.get("status") or {}).get("containerStatuses") or [])
                         + ((p.get("status") or {}).get("initContainerStatuses") or [])
                         if (s.get("restartCount") or 0) > 0})
    s = d.get("status") or {}
    assert d["spec"].get("replicas") == REPLICAS_VITRINE and _deploiement_pret(d) and _est_l_image(voulue) \
        and len(pods) == REPLICAS_VITRINE and not redemarres, message(
        en=f"{VITRINE}: {s.get('availableReplicas', 0)} available out of {d['spec'].get('replicas')}, image "
        f"{voulue!r} (run: {sorted(i for i in images if i)}), restarted Pods: {redemarres}. Expected "
        f"{REPLICAS_VITRINE} available on the image referred to by digest, and no Pod of the {NS} space restarted.",
        fr=f"{VITRINE} : {s.get('availableReplicas', 0)} disponible(s) sur {d['spec'].get('replicas')}, image "
        f"{voulue!r} (en marche : {sorted(i for i in images if i)}), Pods redémarrés : {redemarres}. Attendu "
        f"{REPLICAS_VITRINE} disponibles sur l'image référencée par digest, et aucun Pod de l'espace {NS} "
        "redémarré.",
    )


# ----------------------------------------------------------------------
# P03. Requests, limits et trois sondes sur le port de la vitrine.
# ----------------------------------------------------------------------
def test_p03_ressources_et_trois_sondes_declarees(host):
    spec = _vitrine(host)["spec"]["template"]["spec"]
    conteneurs = spec["containers"] + (spec.get("initContainers") or [])
    sans = [c["name"] for c in conteneurs
            if not ((c.get("resources") or {}).get("requests") and (c.get("resources") or {}).get("limits"))]
    principal = spec["containers"][0]
    sondes = [n for n in ("startupProbe", "livenessProbe", "readinessProbe") if _sonde_80(principal, n)]
    assert not sans and len(sondes) == 3, message(
        en=f"Containers without requests and limits: {sans}; probes on port 80 of {principal['name']}: {sondes}. "
        "Expected every container budgeted, and the three probes on the port of the storefront.",
        fr=f"Conteneurs sans requests et limits : {sans} ; sondes sur le port 80 de {principal['name']} : "
        f"{sondes}. Attendu chaque conteneur budgété, et les trois sondes sur le port de la vitrine.",
    )


# ----------------------------------------------------------------------
# P04. Init container terminé, sidecar natif qui relaie le volume partagé.
# ----------------------------------------------------------------------
def test_p04_init_container_et_sidecar_relaient_le_volume_partage(host):
    d = _vitrine(host)
    spec = d["spec"]["template"]["spec"]
    ordinaires = [c["name"] for c in spec.get("initContainers") or [] if c.get("restartPolicy") != "Always"]
    sidecars = [c["name"] for c in spec.get("initContainers") or [] if c.get("restartPolicy") == "Always"]
    pods = [p for p in _pods(host, d["spec"]["selector"].get("matchLabels", {}))
            if p["status"].get("phase") == "Running"]
    # Un compagnon déclaré comme un second conteneur ordinaire démarre EN MÊME
    # TEMPS que le serveur et peut s'arrêter avant lui : il perd des lignes. Le
    # cahier des charges demande un compagnon prêt avant le serveur et arrêté
    # après lui, ce que seul un sidecar natif garantit.
    voisins = [c["name"] for c in spec.get("containers") or []][1:]
    assert sidecars or not voisins, message(
        en=f"In {VITRINE}, the companion {voisins} starts at the same time as the server: it is not ready before "
        "the server, so the first lines can be lost.",
        fr=f"Dans {VITRINE}, le compagnon {voisins} démarre en même temps que le serveur : il n'est pas prêt avant "
        "lui, et les premières lignes peuvent se perdre.",
    )
    assert ordinaires and sidecars and pods, message(
        en=f"{VITRINE} needs a preparation container that finishes before the start and a companion ready "
        f"before the server (found:{ordinaires or 'none'}, {sidecars or 'none'}), and a running Pod.",
        fr=f"{VITRINE} doit porter un conteneur de préparation qui finit avant le démarrage et un compagnon prêt "
        f"avant le serveur (trouvé : {ordinaires or 'aucun'}, {sidecars or 'aucun'}), et un Pod en marche.",
    )
    pod = pods[0]
    etats = {s["name"]: s.get("state") or {} for s in pod["status"].get("initContainerStatuses") or []}
    fini = (etats.get(ordinaires[0]) or {}).get("terminated") or {}
    jeton = f"correcteur-{int(time.time())}"
    nom = pod["metadata"]["name"]
    host.run(f"{ADMIN} -n {NS} exec {nom} -c {sidecars[0]} -- wget -q -O /dev/null -T 3 http://127.0.0.1/{jeton}")
    time.sleep(3)
    logs = host.run(f"{ADMIN} -n {NS} logs {nom} -c {sidecars[0]} --tail=100").stdout
    termine = fini.get("reason") == "Completed"
    init_en = "completed" if termine else "did not complete"
    init_fr = "est terminé" if termine else "n'est pas terminé"
    relai_en = "passes on" if jeton in logs else "does not pass on"
    relai_fr = "relaie" if jeton in logs else "ne relaie pas"
    assert termine and jeton in logs, message(
        en=f"In {nom}, the preparation container {init_en}, and the companion {relai_en} the lines the storefront "
        "writes on the shared volume.",
        fr=f"Dans {nom}, le conteneur de préparation {init_fr}, et le compagnon {relai_fr} les lignes que la "
        "vitrine écrit sur le volume partagé.",
    )


# ----------------------------------------------------------------------
# P05. Base à identité stable, Pods ordonnés Ready, une revendication chacun. CRITIQUE.
# ----------------------------------------------------------------------
def test_p05_base_a_identite_stable_avec_une_revendication_par_replica(host):
    sts = _base(host)
    prets = [f"{BASE}-{i}" for i in range(sts["spec"].get("replicas", 0))
             if {c["type"]: c["status"] for c in (((_json(host, f"-n {NS} get pod {BASE}-{i}") or {})
                 .get("status") or {}).get("conditions") or [])}.get("Ready") == "True"]
    liees = [p["metadata"]["name"] for p in _revendications_de_la_base(host, sts)
             if (p.get("status") or {}).get("phase") == "Bound"]
    assert sts["spec"].get("replicas") == REPLICAS_BASE and len(prets) == REPLICAS_BASE \
        and len(liees) == REPLICAS_BASE, message(
        en=f"{BASE}: {sts['spec'].get('replicas')} replica(s), Ready {prets}, Bound claims {liees}. Expected "
        f"{REPLICAS_BASE} ordered replicas, all Ready, each with its own Bound claim.",
        fr=f"{BASE} : {sts['spec'].get('replicas')} réplica(s), Ready {prets}, revendications Bound {liees}. "
        f"Attendu {REPLICAS_BASE} réplicas ordonnés, tous Ready, chacun avec sa revendication Bound.",
    )


# ----------------------------------------------------------------------
# P06. La donnée du correcteur survit à la suppression de son Pod. CRITIQUE.
# ----------------------------------------------------------------------
def test_p06_la_donnee_du_correcteur_survit_a_son_pod(host):
    _base(host)
    pod = f"{BASE}-0"
    jeton = f"correcteur-{int(time.time())}"
    ecrit = host.run(f"{ADMIN} -n {NS} exec {pod} -- sh -c 'echo {jeton} > {DONNEES}/correcteur.txt'")
    assert ecrit.rc == 0, message(
        en=f"The grader cannot write into {DONNEES} of {pod}: the volume is not mounted there, or is read-only.",
        fr=f"Le correcteur ne peut pas écrire dans {DONNEES} de {pod} : le volume n'y est pas monté, ou est en "
        "lecture seule.",
    )
    avant = (_json(host, f"-n {NS} get pod {pod}") or {}).get("metadata", {}).get("uid")
    host.run(f"{ADMIN} -n {NS} delete pod {pod} --wait=true --timeout=120s")
    recree = _attendre(host, f"-n {NS} get pod {pod}",
                       lambda p: p["metadata"]["uid"] != avant and any(
                           c["type"] == "Ready" and c["status"] == "True"
                           for c in (p.get("status") or {}).get("conditions") or []))
    relu = host.run(f"{ADMIN} -n {NS} exec {pod} -- cat {DONNEES}/correcteur.txt").stdout.strip()
    assert recree is not None and recree["metadata"]["uid"] != avant and relu == jeton, message(
        en=f"After the deletion of {pod}, the recreated Pod reads {relu or 'nothing'!r} instead of the data the "
        "grader wrote: it did not survive.",
        fr=f"Après la suppression de {pod}, le Pod recréé lit {relu or 'rien'!r} au lieu de la donnée écrite par "
        "le correcteur : elle n'a pas survécu.",
    )


# ----------------------------------------------------------------------
# P07. Volumes créés par la StorageClass, reclaim policy demandée. CRITIQUE.
# ----------------------------------------------------------------------
def test_p07_volumes_crees_par_la_classe_en_retain(host):
    sts = _base(host)
    ecarts = []
    revendications = _revendications_de_la_base(host, sts)
    for pvc in revendications:
        pv = _json(host, f"get pv {(pvc.get('spec') or {}).get('volumeName')}") if pvc["spec"].get("volumeName") else None
        classe = _json(host, f"get storageclass {pvc['spec'].get('storageClassName')}") \
            if pvc["spec"].get("storageClassName") else None
        fournisseur = ((pv or {}).get("metadata", {}).get("annotations") or {}).get("pv.kubernetes.io/provisioned-by")
        if pv is None or classe is None or fournisseur != classe.get("provisioner") \
                or pv["spec"].get("persistentVolumeReclaimPolicy") != "Retain":
            ecarts.append(pvc["metadata"]["name"])
    assert revendications and not ecarts, message(
        en=f"These claims of {BASE} are not bound to a volume the class created for them, kept with the "
        f"reclaim policy Retain: {ecarts or 'no claim'}.",
        fr=f"Ces revendications de {BASE} ne sont pas liées à un volume que la classe a créé pour elles, gardé "
        f"avec la reclaim policy Retain : {ecarts or 'aucune revendication'}.",
    )


# ----------------------------------------------------------------------
# P08. Sauvegarde planifiée, et un lancement à la main terminé qui a écrit.
# ----------------------------------------------------------------------
def test_p08_sauvegarde_planifiee_et_lancee_a_la_main(host):
    _nom_exact(host, "cronjob", SAUVEGARDE,
               en=f"No scheduled task named {SAUVEGARDE} in {NS}.",
               fr=f"Aucune tâche planifiée nommée {SAUVEGARDE} dans {NS}.")
    cj = _json(host, f"-n {NS} get cronjob {SAUVEGARDE}")
    assert cj is not None and _planification(cj["spec"].get("schedule")) == _planification(PLANNING), message(
        en=f"{SAUVEGARDE} is not scheduled every day at 2:30 (found: {(cj or {}).get('spec', {}).get('schedule')!r}).",
        fr=f"{SAUVEGARDE} n'est pas planifiée chaque jour à 2 h 30 (trouvé : "
        f"{(cj or {}).get('spec', {}).get('schedule')!r}).",
    )
    manuels = [j for j in (_json(host, f"-n {NS} get jobs") or {}).get("items", [])
               if any(o.get("kind") == "CronJob" and o.get("name") == SAUVEGARDE
                      for o in j["metadata"].get("ownerReferences") or [])
               and (j["metadata"].get("annotations") or {}).get("cronjob.kubernetes.io/instantiate") == "manual"]
    reussis = [j for j in manuels if (j.get("status") or {}).get("succeeded", 0) >= 1]
    pvc = _json(host, f"-n {NS} get pvc {ARCHIVES}")
    pv = _json(host, f"get pv {pvc['spec']['volumeName']}") if pvc and pvc["spec"].get("volumeName") else None
    fichiers = ""
    if pv is not None:
        chemin = (pv["spec"].get("hostPath") or pv["spec"].get("local") or {}).get("path", "")
        termes = (((pv["spec"].get("nodeAffinity") or {}).get("required") or {}).get("nodeSelectorTerms") or [{}])
        noeud = next((v for t in termes for e in t.get("matchExpressions") or [] for v in e.get("values") or []), "")
        if chemin and noeud:
            fichiers = host.run(f"sudo docker exec {noeud} ls {chemin}").stdout
    assert reussis and "sauvegarde" in fichiers, message(
        en=f"Hand-started runs of {SAUVEGARDE}: {len(manuels)}, completed: {len(reussis)}; files in the volume "
        f"{ARCHIVES}: {fichiers.split() or 'none'}. Expected a run started by hand from the schedule, completed, "
        "that wrote its file in the volume.",
        fr=f"Lancements à la main de {SAUVEGARDE} : {len(manuels)}, terminés : {len(reussis)} ; fichiers du volume "
        f"{ARCHIVES} : {fichiers.split() or 'aucun'}. Attendu un lancement à la main depuis la planification, "
        "terminé, qui a écrit son fichier dans le volume.",
    )


# ----------------------------------------------------------------------
# P09. L'agent tourne sur chaque nœud, taint gardé.
# ----------------------------------------------------------------------
def test_p09_agent_sur_chaque_noeud_taint_garde(host):
    noeuds = (_json(host, "get nodes") or {}).get("items", [])
    plans = [n for n in noeuds if TAINT in (n["metadata"].get("labels") or {})]
    teinte = all(any(t.get("key") == TAINT for t in n["spec"].get("taints") or []) for n in plans)
    _nom_exact(host, "daemonset", AGENT,
               en=f"No agent named {AGENT} in {NS}.",
               fr=f"Aucun agent nommé {AGENT} dans {NS}.")
    ds = _attendre(host, f"-n {NS} get daemonset {AGENT}", _ds_pret)
    prets = set()
    if ds is not None:
        for p in _pods(host, ds["spec"]["selector"].get("matchLabels", {})):
            if any(c["type"] == "Ready" and c["status"] == "True" for c in (p.get("status") or {}).get("conditions") or []):
                prets.add(p["spec"].get("nodeName"))
    tous = {n["metadata"]["name"] for n in noeuds}
    assert plans and teinte and ds is not None and prets == tous, message(
        en=f"{AGENT} is Ready on {sorted(prets)}, the cluster has {sorted(tous)}, and the taint of the control "
        f"plane is {'there' if teinte else 'gone'}. Expected one Ready agent on each node, taint kept.",
        fr=f"{AGENT} est Ready sur {sorted(prets)}, le cluster compte {sorted(tous)}, et le taint du control plane "
        f"{'est là' if teinte else 'a disparu'}. Attendu un agent Ready sur chaque nœud, taint gardé.",
    )


# ----------------------------------------------------------------------
# P10. La ressource personnalisée demandée, et un refus hors bornes.
# ----------------------------------------------------------------------
def test_p10_ressource_personnalisee_conforme_et_borne_refusee(host):
    r = _json(host, f"-n {NS} get {CRD} nocturne")
    spec = (r or {}).get("spec") or {}
    essai = (
        f"printf '%s' '{{\"apiVersion\":\"{API}\",\"kind\":\"Sauvegarde\",\"metadata\":{{\"name\":\"essai-borne\","
        f"\"namespace\":\"{NS}\"}},\"spec\":{{\"source\":\"{BASE}\",\"retentionJours\":400}}}}' "
        f"| {ADMIN} apply --dry-run=server -f -"
    )
    refus = host.run(essai)
    refuse = refus.rc != 0 and "less than or equal to 365" in refus.stderr
    assert spec == {"source": BASE, "retentionJours": 14} and refuse, message(
        en=f"The Sauvegarde nocturne has {spec or 'nothing'}, and a retention of 400 days is "
        f"{'refused' if refuse else 'accepted'}. Expected the source and the retention of the requirements, and "
        "an API that still refuses an out-of-bounds value.",
        fr=f"La Sauvegarde nocturne porte {spec or 'rien'}, et une rétention de 400 jours est "
        f"{'refusée' if refuse else 'acceptée'}. Attendu la source et la rétention du cahier des charges, et une "
        "API qui refuse toujours une valeur hors bornes.",
    )
