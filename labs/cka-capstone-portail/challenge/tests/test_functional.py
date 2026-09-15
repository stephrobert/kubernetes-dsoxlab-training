"""test_functional.py : cka-capstone-portail

Huit affirmations, qui lisent l'état du CLUSTER et jamais les commandes
tapées. Le scénario ne dit pas où sont les défauts, et ces tests ne disent pas
comment les corriger : ils mesurent le résultat.

Un capstone de dépannage se mesure autrement qu'un micro-lab. Il ne suffit pas
de constater qu'un objet a été édité, puisqu'on ne sait pas lequel le candidat
a choisi d'éditer : le défaut du sélecteur se corrige côté Service comme côté
labels des Pods, et le défaut de stockage en créant un volume comme en
réécrivant la réclamation. On interroge donc des EFFETS, et le dernier test
interroge le portail depuis chacun des deux nœuds, comme la supervision le
fera.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "production"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
PORTAIL = "portail"
ARCHIVES = "archives"
SERVICE = "portail-svc"
RECLAMATION = "portail-data"
NODE_PORT = 30080


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Joue une commande kubectl sur le control plane.

    Rend (code, sortie standard, diagnostic), et les trois restent SÉPARÉS :
    le client SSH écrit un avertissement sur stderr, et un test qui déciderait
    sur la concaténation des deux ne mesurerait plus rien.
    """
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str, quoi: str) -> dict:
    rc, sortie, diagnostic = _kubectl(host, f"{args} -o json")
    assert rc == 0 and sortie, (
        f"{quoi} n'existe plus dans le namespace {NAMESPACE}. Il faisait partie "
        "de la livraison : le supprimer n'est pas une correction, et le "
        f"recréer sous un autre nom non plus. Sortie : {diagnostic}"
    )
    return json.loads(sortie)


def _ips_des_noeuds(host) -> list[str]:
    rc, sortie, _ = _kubectl(
        host,
        "get nodes -o jsonpath='{range .items[*]}"
        '{.status.addresses[?(@.type=="InternalIP")].address}{"\\n"}{end}\'',
    )
    assert rc == 0 and sortie, "Impossible de lire les adresses des nœuds."
    return [ligne.strip() for ligne in sortie.splitlines() if ligne.strip()]


def _cpu_allouable_max(host) -> float:
    """Le plus gros nœud du cluster, en CPU, tel que l'API le déclare.

    Mesuré et non écrit en dur : un cluster redimensionné ne doit pas faire
    échouer un test qui parle de ce que le cluster possède.
    """
    rc, sortie, _ = _kubectl(
        host, "get nodes -o jsonpath='{range .items[*]}{.status.allocatable.cpu}{\"\\n\"}{end}'"
    )
    assert rc == 0 and sortie, "Impossible de lire le CPU allouable des nœuds."
    valeurs = []
    for brut in sortie.split():
        valeurs.append(float(brut[:-1]) / 1000 if brut.endswith("m") else float(brut))
    return max(valeurs)


def _curl(host, url: str, patience_s: int = 12) -> tuple[bool, str]:
    """Une requête HTTP depuis le nœud, avec de la patience.

    La patience n'est pas de la complaisance, elle corrige un faux négatif
    mesuré. Un Service est à jour dans l'API dès qu'on l'a modifié, mais c'est
    kube-proxy qui programme la règle du NodePort sur chaque nœud, et il le
    fait APRÈS avoir été notifié : la chaîne KUBE-NODEPORTS est encore vide
    dans la seconde qui suit, puis la règle apparaît en un peu plus d'une
    seconde au premier passage. Sans cette attente, un candidat qui lance
    `dsoxlab check` juste après avoir corrigé son Service serait recalé pour
    une correction qui est bonne, ce qui est le pire défaut qu'un test puisse
    avoir.

    Le budget reste borné : un accès qui ne s'ouvre pas en une douzaine de
    secondes ne s'ouvrira pas, et le test doit alors échouer pour de bon.
    """
    res = host.run(
        "for _ in $(seq 1 %d); do "
        "code=$(curl -sS -o /dev/null -w '%%{http_code}' -m 3 %s 2>/dev/null); "
        '[ "$code" = "200" ] && break; sleep 1; done; echo -n "$code"'
        % (patience_s, url)
    )
    return res.stdout.strip() == "200", res.stdout.strip() or res.stderr.strip()


# ----------------------------------------------------------------------
# Exigence 1. Deux exemplaires, et ils tournent.
# ----------------------------------------------------------------------
def test_les_deux_exemplaires_du_portail_sont_prets(host):
    """On lit readyReplicas, pas replicas : un Deployment qui demande deux
    copies dont aucune ne démarre annonce quand même 2 en souhaité, et c'est
    exactement l'état dans lequel le lab commence."""
    d = _json(host, f"-n {NAMESPACE} get deployment {PORTAIL}", f"Le Deployment {PORTAIL}")
    assert d["spec"].get("replicas") == 2, (
        f"Le portail demande {d['spec'].get('replicas')} exemplaire(s), on en "
        "attend deux. Ce n'est pas le nombre d'exemplaires qui était en cause."
    )
    prets = d.get("status", {}).get("readyReplicas", 0)
    assert prets == 2, (
        f"{prets} exemplaire(s) sur 2 sont prêts. Un Pod qui ne démarre pas dit "
        "pourquoi : kubectl describe pod, section Events, tout en bas."
    )


def test_la_reserve_du_portail_tient_dans_un_noeud(host):
    """Le défaut est la RÉSERVE, pas la limite, et il se voit à l'ordonnancement.

    Ce test regarde la cause plutôt que le symptôme : le précédent passerait
    si quelqu'un ramenait le Deployment à zéro exemplaire puis à deux sur un
    cluster momentanément vide, celui-ci non.
    """
    d = _json(host, f"-n {NAMESPACE} get deployment {PORTAIL}", f"Le Deployment {PORTAIL}")
    plafond = _cpu_allouable_max(host)
    for conteneur in d["spec"]["template"]["spec"]["containers"]:
        brut = ((conteneur.get("resources") or {}).get("requests") or {}).get("cpu")
        if brut is None:
            continue
        demande = float(brut[:-1]) / 1000 if str(brut).endswith("m") else float(brut)
        assert demande <= plafond, (
            f"Le conteneur {conteneur['name']} réserve {brut} de CPU, quand le "
            f"plus gros nœud du cluster en déclare {plafond}. Aucun ordonnanceur "
            "ne peut placer un Pod qui réserve plus que ce qui existe : la "
            "réserve exprime un besoin garanti, pas un souhait."
        )


# ----------------------------------------------------------------------
# Exigence 2. Le Service désigne vraiment les Pods, et il répond.
# ----------------------------------------------------------------------
def test_le_service_designe_vraiment_les_pods_du_portail(host):
    """Un Service dont le sélecteur ne correspond à rien existe, répond à
    `kubectl get`, et n'a aucun endpoint. C'est l'endpoint qu'on interroge,
    pas le sélecteur : le candidat a pu corriger l'un OU les labels des Pods,
    et les deux sont justes."""
    rc, sortie, _ = _kubectl(
        host,
        f"-n {NAMESPACE} get endpointslice -l kubernetes.io/service-name={SERVICE} "
        "-o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{\" \"}{end}'",
    )
    assert rc == 0, f"Aucune EndpointSlice pour le Service {SERVICE}."
    adresses = sortie.split()
    assert len(adresses) == 2, (
        f"Le Service {SERVICE} a {len(adresses)} endpoint(s), on en attend deux, "
        "un par exemplaire. Un Service ne connaît que les Pods que son sélecteur "
        "désigne : comparez-le aux labels que portent réellement les Pods."
    )


def test_le_portail_repond_dans_le_cluster(host):
    """La preuve, depuis le nœud : kube-proxy route les adresses de Service
    depuis l'hôte aussi bien que depuis un Pod."""
    svc = _json(host, f"-n {NAMESPACE} get service {SERVICE}", f"Le Service {SERVICE}")
    ip = svc["spec"].get("clusterIP")
    ports = [p.get("port") for p in svc["spec"].get("ports", [])]
    assert 80 in ports, (
        f"Le Service présente le(s) port(s) {ports}, on attend le port 80 côté client."
    )
    repond, code = _curl(host, f"http://{ip}:80/")
    assert repond, (
        f"Le portail ne répond pas sur son adresse de Service {ip}:80 (obtenu : "
        f"{code}). Si le Service a ses deux endpoints, regardez le targetPort : "
        "c'est le port du conteneur, pas celui du client."
    )


# ----------------------------------------------------------------------
# Exigence 3. L'accès depuis l'extérieur, sur chaque nœud.
# ----------------------------------------------------------------------
def test_le_service_est_expose_sur_le_port_30080(host):
    """Le port est imposé par la supervision : il ne s'improvise pas."""
    svc = _json(host, f"-n {NAMESPACE} get service {SERVICE}", f"Le Service {SERVICE}")
    type_svc = svc["spec"].get("type")
    assert type_svc in ("NodePort", "LoadBalancer"), (
        f"Le Service {SERVICE} est de type {type_svc} : il n'est donc joignable "
        "que depuis l'intérieur du cluster. On demande un accès depuis "
        "l'extérieur, sur un port des nœuds."
    )
    ports_noeud = [p.get("nodePort") for p in svc["spec"].get("ports", [])]
    assert NODE_PORT in ports_noeud, (
        f"Le Service ouvre le(s) port(s) {ports_noeud} sur les nœuds, la "
        f"supervision interrogera le {NODE_PORT}. Sans nodePort explicite, "
        "Kubernetes en attribue un au hasard dans la plage 30000-32767."
    )


def test_le_portail_repond_sur_chaque_noeud(host):
    """LE test qui prouve quelque chose, et il porte sur les DEUX nœuds.

    Un NodePort s'ouvre sur tous les nœuds, y compris ceux qui ne portent
    aucun exemplaire : c'est la propriété qu'on mesure ici, et elle ne se lit
    dans aucune spec. Interroger seulement le control plane laisserait passer
    un cluster dont le réseau entre nœuds est cassé.
    """
    ips = _ips_des_noeuds(host)
    assert len(ips) >= 2, (
        f"Le cluster ne déclare que {len(ips)} nœud(s) : le worker manque, et "
        "l'exigence « sur chaque nœud » ne veut plus rien dire."
    )
    echecs = []
    for ip in ips:
        repond, code = _curl(host, f"http://{ip}:{NODE_PORT}/")
        if not repond:
            echecs.append(f"{ip} a rendu {code}")
    assert not echecs, (
        f"Le portail ne répond pas sur le port {NODE_PORT} de : "
        f"{', '.join(echecs)}. Un NodePort s'ouvre sur TOUS les nœuds, même "
        "ceux qui ne portent aucun exemplaire, et le trafic est routé vers un "
        "Pod prêt. S'il répond sur un nœud et pas sur l'autre, ce n'est pas le "
        "Service qu'il faut regarder mais le réseau du cluster."
    )


# ----------------------------------------------------------------------
# Exigence 4. Le stockage des archives existe vraiment.
# ----------------------------------------------------------------------
def test_la_reclamation_de_stockage_est_satisfaite(host):
    pvc = _json(
        host, f"-n {NAMESPACE} get pvc {RECLAMATION}", f"La réclamation {RECLAMATION}"
    )
    phase = pvc.get("status", {}).get("phase")
    assert phase == "Bound", (
        f"La réclamation {RECLAMATION} est en {phase}. Elle cherche une classe de "
        "stockage, une taille et un mode d'accès : kubectl describe pvc dit "
        "lesquels, et tant qu'aucun volume ne réunit les trois, elle attend."
    )


def test_les_archives_ecrivent_vraiment_dans_leur_volume(host):
    """La preuve, prise DANS le conteneur.

    Une réclamation liée dont le Pod ne démarre pas ne sert à rien, et un
    volume monté en lecture seule non plus. On écrit, on relit, on efface.
    """
    rc, pod, _ = _kubectl(
        host,
        f"-n {NAMESPACE} get pods -l app={ARCHIVES} --field-selector=status.phase=Running "
        "-o jsonpath='{.items[0].metadata.name}'",
    )
    assert rc == 0 and pod, (
        "Aucun Pod archives ne tourne. Un Pod qui monte une réclamation non "
        "satisfaite reste Pending indéfiniment : le stockage se règle d'abord."
    )
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec {pod} --request-timeout=30s -- "
        "sh -c 'echo preuve > /data/preuve.txt && cat /data/preuve.txt && rm /data/preuve.txt'",
    )
    assert rc == 0 and sortie == "preuve", (
        "Le Pod archives ne peut pas écrire dans /data. Le volume est peut-être "
        "monté en lecture seule, ou monté ailleurs que sur /data. Sortie : "
        f"{diagnostic}"
    )
