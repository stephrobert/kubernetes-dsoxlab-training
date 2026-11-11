"""test_functional.py : k8s-epreuve-livrer-et-mettre-a-jour

L'épreuve du niveau 1 (D33, D34, D35). Le cahier des charges ne nomme aucun
type d'objet : ces tests retrouvent sur le cluster ce que l'apprenant a choisi.
La vitrine est le Deployment nginx de l'espace livraison ; le composant en
panne est le Deployment stock de l'espace entrepot, posé par le setup. Un test
vérifie un seul critère de la grille, et ne lit que l'état du cluster et le
fichier ~/epreuve/cause-stock.txt.

C5 juge le RÉSULTAT d'une mise à jour, pas une valeur écrite : le nombre
d'exemplaires qui peuvent manquer est calculé pour le nombre de réplicas, valeur
par défaut comprise (25 % de 3, arrondi vers le bas, donne 0).

Aucun test n'attend tant que le travail n'est pas commencé : une attente ne
s'ouvre que si l'état demandé est déjà déclaré et converge encore.
"""

from __future__ import annotations

import json
import math
import time
import unicodedata

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "livraison"
ENTREPOT = "entrepot"
V1 = "nginx:1.30.5"
V2 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
MESSAGE = "Bienvenue"
MOT_DE_PASSE = "Boutique-2026"
SEUIL = "10"
REVISION = "deployment.kubernetes.io/revision"
#: Ce qui dit qu'une chose manque, dans un diagnostic : l'état affiché par
#: Kubernetes, le message du kubelet, ou une phrase en français ou en anglais.
DIT_LE_MANQUE = ("createcontainerconfigerror", "couldntfind", "couldnotfind", "notfound",
                 "manque", "manquant", "absent", "introuvable", "inexistant", "missing",
                 "nexistepas", "trouvepas", "pasdecle")
ATTENTE = 90
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, ns: str, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {ns} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _sans_registre(reference: str) -> str:
    for prefixe in ("docker.io/library/", "index.docker.io/library/"):
        if reference.startswith(prefixe):
            return reference[len(prefixe):]
    return reference


def _vitrine(host) -> dict:
    """Le Deployment nginx de livraison : la vitrine, quel que soit son nom."""
    items = (_json(host, NS, "get deployments") or {}).get("items") or []
    nginx = [d for d in items
             if _sans_registre(d["spec"]["template"]["spec"]["containers"][0].get("image", "")).startswith("nginx:")]
    assert len(nginx) == 1, message(
        en=f"Expected exactly one nginx Deployment, the storefront, in the {NS} space; found "
        f"{[d['metadata']['name'] for d in nginx]}. The storefront runs as copies that replace "
        "themselves, in the space of its team.",
        fr=f"Attendu exactement un Deployment nginx, la vitrine, dans l'espace {NS} ; trouvé "
        f"{[d['metadata']['name'] for d in nginx]}. La vitrine tourne en exemplaires qui se "
        "remplacent seuls, dans l'espace de son équipe.",
    )
    return nginx[0]


def _selecteur(dep: dict) -> str:
    etiquettes = (dep["spec"].get("selector") or {}).get("matchLabels") or {}
    return ",".join(f"{k}={v}" for k, v in sorted(etiquettes.items()))


def _pods_vivants(host, ns: str, selecteur: str) -> list[dict]:
    pods = (_json(host, ns, f"get pods -l {selecteur}") or {}).get("items") or []
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")
            and (p.get("status") or {}).get("phase") == "Running"]


def _conteneur(dep: dict) -> dict:
    return (dep["spec"]["template"]["spec"].get("containers") or [{}])[0]


def _compact(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if c.isalnum())


def _effectif(valeur, replicas: int, defaut: str, arrondi) -> int:
    v = defaut if valeur is None else valeur
    if isinstance(v, str) and v.endswith("%"):
        return int(arrondi(replicas * int(v[:-1]) / 100))
    return int(v)


# ----------------------------------------------------------------------
# C1 (critique) : trois exemplaires disponibles, tous en version 2.
# ----------------------------------------------------------------------
def test_c1_trois_exemplaires_disponibles_en_version_2(host):
    dep = _vitrine(host)
    demandes = dep["spec"].get("replicas", 1)
    modele = _sans_registre(_conteneur(dep).get("image", ""))
    assert demandes == 3 and modele == V2, message(
        en=f"The storefront asks for {demandes} copy(ies) of {modele!r}, expected 3 of version 2, "
        f"referenced by digest: {V2}.",
        fr=f"La vitrine demande {demandes} exemplaire(s) de {modele!r}, attendu 3 de la version 2, "
        f"référencée par digest : {V2}.",
    )
    # La demande est juste : on laisse la mise à jour finir.
    fin = time.monotonic() + ATTENTE
    while True:
        dep = _vitrine(host)
        disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
        images = sorted({_sans_registre(c.get("image", ""))
                         for p in _pods_vivants(host, NS, _selecteur(dep))
                         for c in p["spec"].get("containers") or []})
        if (disponibles == 3 and images == [V2]) or time.monotonic() >= fin:
            break
        time.sleep(PAS)
    assert disponibles == 3 and images == [V2], message(
        en=f"The storefront has {disponibles} available copy(ies), running {images}; expected 3, "
        "all on version 2.",
        fr=f"La vitrine a {disponibles} exemplaire(s) disponible(s), qui tournent sur {images} ; "
        "attendu 3, tous en version 2.",
    )


# ----------------------------------------------------------------------
# C2 (critique) : une adresse stable, servie par les trois exemplaires.
# ----------------------------------------------------------------------
def test_c2_une_adresse_stable_servie_par_les_trois_exemplaires(host):
    _vitrine(host)
    assert _json(host, NS, "get service vitrine") is not None, message(
        en=f"Nothing answers at the address http://vitrine.{NS} the requirements give: no stable "
        f"address named vitrine in the {NS} space.",
        fr=f"Rien ne répond à l'adresse http://vitrine.{NS} que donne le cahier des charges : "
        f"aucune adresse stable nommée vitrine dans l'espace {NS}.",
    )
    tranches = (_json(host, NS, "get endpointslices -l kubernetes.io/service-name=vitrine") or {}).get("items") or []
    prets = {a for t in tranches for ep in t.get("endpoints") or []
             if (ep.get("conditions") or {}).get("ready") for a in ep.get("addresses") or []}
    assert len(prets) == 3, message(
        en=f"The address vitrine is served by {len(prets)} ready copy(ies), expected the three of "
        "the storefront.",
        fr=f"L'adresse vitrine est servie par {len(prets)} exemplaire(s) prêt(s), attendu les trois "
        "de la vitrine.",
    )
    host.run(f"{ADMIN} -n {NS} delete pod sonde-epreuve --ignore-not-found --wait=true")
    res = host.run(f"{ADMIN} -n {NS} run sonde-epreuve --rm -i --restart=Never --image={BUSYBOX} "
                   f"-- wget -qO- -T 5 http://vitrine.{NS}")
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en=f"From a Pod of the cluster, http://vitrine.{NS} does not answer HTTP.",
        fr=f"Depuis un Pod du cluster, http://vitrine.{NS} ne répond pas en HTTP.",
    )


# ----------------------------------------------------------------------
# C3 (critique) : configuration et mot de passe hors de l'image et du manifeste.
# ----------------------------------------------------------------------
def _vient_de(conteneur: dict, variable: str, cle_ref: str, cle_from: str) -> bool:
    for e in conteneur.get("env") or []:
        if e.get("name") == variable:
            return bool((e.get("valueFrom") or {}).get(cle_ref))
    return any(src.get(cle_from) for src in conteneur.get("envFrom") or [])


def test_c3_configuration_et_mot_de_passe_hors_de_l_image_et_du_manifeste(host):
    dep = _vitrine(host)
    conteneur = _conteneur(dep)
    assert _vient_de(conteneur, "MESSAGE_ACCUEIL", "configMapKeyRef", "configMapRef"), message(
        en="MESSAGE_ACCUEIL is not taken from a configuration managed apart: a value written in "
        "the storefront's description does not count.",
        fr="MESSAGE_ACCUEIL ne vient pas d'une configuration gérée à part : une valeur écrite dans "
        "la description de la vitrine ne compte pas.",
    )
    assert _vient_de(conteneur, "DB_PASSWORD", "secretKeyRef", "secretRef"), message(
        en="DB_PASSWORD is not taken from an object made to hold a password.",
        fr="DB_PASSWORD ne vient pas d'un objet fait pour garder un mot de passe.",
    )
    assert MOT_DE_PASSE not in json.dumps(dep), message(
        en="The password appears in clear in the storefront's description.",
        fr="Le mot de passe apparaît en clair dans la description de la vitrine.",
    )
    pods = _pods_vivants(host, NS, _selecteur(dep))
    assert pods, message(
        en="No running copy of the storefront to read its variables from.",
        fr="Aucun exemplaire de la vitrine en marche où lire ses variables.",
    )
    pod = pods[0]["metadata"]["name"]
    vus = {v: host.run(f"{ADMIN} -n {NS} exec {pod} -- printenv {v}").stdout.strip()
           for v in ("MESSAGE_ACCUEIL", "DB_PASSWORD")}
    assert vus == {"MESSAGE_ACCUEIL": MESSAGE, "DB_PASSWORD": MOT_DE_PASSE}, message(
        en=f"Inside a copy of the storefront, the variables read {vus}; expected the welcome "
        "message and the password of the requirements.",
        fr=f"Dans un exemplaire de la vitrine, les variables valent {vus} ; attendu le message "
        "d'accueil et le mot de passe du cahier des charges.",
    )


# ----------------------------------------------------------------------
# C4 (critique) : une révision de retour sur la version 1.
# ----------------------------------------------------------------------
def test_c4_une_revision_de_retour_sur_la_version_1(host):
    dep = _vitrine(host)
    actuelle = int((dep["metadata"].get("annotations") or {}).get(REVISION, "0"))
    tous = (_json(host, NS, "get replicasets") or {}).get("items") or []
    siens = [rs for rs in tous
             if any(r.get("uid") == dep["metadata"]["uid"] for r in rs["metadata"].get("ownerReferences") or [])]
    precedents = sorted(
        (int((rs["metadata"].get("annotations") or {}).get(REVISION, "0")), rs) for rs in siens
        if int((rs["metadata"].get("annotations") or {}).get(REVISION, "0")) < actuelle
    )
    assert precedents, message(
        en="The storefront keeps no previous revision: it was delivered directly in its final "
        "version, or recreated. Deliver version 1 first, then update it.",
        fr="La vitrine ne garde aucune révision précédente : elle a été livrée directement dans "
        "sa version finale, ou recréée. Livrez d'abord la version 1, puis mettez-la à jour.",
    )
    # Toute révision conservée en version 1 suffit : `rollout undo --to-revision`
    # ramène n'importe laquelle, pas seulement la précédente. Livrer la v1, puis
    # la v2, puis ajouter le mot de passe (une troisième révision, toujours en
    # v2) garde un retour possible vers la révision 1.
    images = {num: _sans_registre(rs["spec"]["template"]["spec"]["containers"][0].get("image", ""))
              for num, rs in precedents}
    en_v1 = sorted(num for num, image in images.items() if image.split("@", 1)[0] == V1)
    assert en_v1, message(
        en=f"No revision kept by the storefront runs version 1 ({V1}): the kept revisions run "
        f"{images}. No rollback could bring version 1 back.",
        fr=f"Aucune révision conservée par la vitrine ne porte la version 1 ({V1}) : les "
        f"révisions conservées portent {images}. Aucun retour arrière ne ramènerait la version 1.",
    )


# ----------------------------------------------------------------------
# C5 : une mise à jour ne prive jamais la vitrine d'un exemplaire disponible.
# ----------------------------------------------------------------------
def test_c5_une_mise_a_jour_ne_prive_d_aucun_exemplaire(host):
    dep = _vitrine(host)
    strategie = dep["spec"].get("strategy") or {}
    assert strategie.get("type", "RollingUpdate") == "RollingUpdate", message(
        en=f"The update strategy is {strategie.get('type')!r}: every copy is stopped before the "
        "new ones start, the storefront is down during the update.",
        fr=f"La stratégie de mise à jour est {strategie.get('type')!r} : tous les exemplaires "
        "s'arrêtent avant que les nouveaux démarrent, la vitrine est coupée pendant la mise à jour.",
    )
    replicas = dep["spec"].get("replicas", 1)
    progressive = strategie.get("rollingUpdate") or {}
    manquants = _effectif(progressive.get("maxUnavailable"), replicas, "25%", math.floor)
    en_plus = _effectif(progressive.get("maxSurge"), replicas, "25%", math.ceil)
    assert manquants == 0 and en_plus >= 1, message(
        en=f"With {replicas} copies, an update may leave {manquants} copy(ies) unavailable and "
        f"start {en_plus} extra one(s): expected none unavailable, and at least one extra so the "
        "update can move forward.",
        fr=f"Avec {replicas} exemplaires, une mise à jour peut laisser {manquants} exemplaire(s) "
        f"indisponible(s) et en démarrer {en_plus} de plus : attendu aucun indisponible, et au "
        "moins un de plus pour que la mise à jour avance.",
    )


# ----------------------------------------------------------------------
# C6 : l'application vit dans son propre espace, rien dans default.
# ----------------------------------------------------------------------
def test_c6_l_application_vit_dans_son_propre_espace(host):
    dep = _vitrine(host)
    conteneur = _conteneur(dep)
    references = {
        ("configmap", ((e.get("valueFrom") or {}).get("configMapKeyRef") or {}).get("name"))
        for e in conteneur.get("env") or []
    } | {
        ("secret", ((e.get("valueFrom") or {}).get("secretKeyRef") or {}).get("name"))
        for e in conteneur.get("env") or []
    } | {
        ("configmap", (s.get("configMapRef") or {}).get("name")) for s in conteneur.get("envFrom") or []
    } | {
        ("secret", (s.get("secretRef") or {}).get("name")) for s in conteneur.get("envFrom") or []
    }
    # L'adresse vitrine n'est pas exigée ici : C2 la juge déjà, et une adresse
    # mal nommée ne doit pas faire tomber deux critères pour une seule faute.
    references = {(k, n) for k, n in references if n}
    absents = sorted(f"{k}/{n}" for k, n in references if host.run(f"{ADMIN} -n {NS} get {k} {n}").rc != 0)
    assert not absents, message(
        en=f"Part of the application is not in the {NS} space: {absents}.",
        fr=f"Une partie de l'application n'est pas dans l'espace {NS} : {absents}.",
    )
    # Rien d'elle dans default : ni la vitrine ni son adresse sous leur nom, ni
    # une copie de la configuration ou du mot de passe qu'elle lit.
    egares = [f"{k}/vitrine" for k in ("deployment", "service")
              if host.run(f"{ADMIN} -n default get {k} vitrine").rc == 0]
    egares += [f"{k}/{n}" for k, n in sorted(references)
               if host.run(f"{ADMIN} -n default get {k} {n}").rc == 0]
    assert not egares, message(
        en=f"Something named vitrine is left in the default space: {egares}.",
        fr=f"Quelque chose nommé vitrine traîne dans l'espace par défaut : {egares}.",
    )


# ----------------------------------------------------------------------
# C7 (critique) : stock tourne, sa cause consignée avant la réparation.
# ----------------------------------------------------------------------
def test_c7_stock_tourne_et_sa_cause_a_ete_consignee_avant(host):
    fichier = f"{_maison(host)}/epreuve/cause-stock.txt"
    cause = host.file(fichier)
    assert cause.exists, message(
        en="~/epreuve/cause-stock.txt is missing: the cause of the failure is recorded before "
        "the repair.",
        fr="~/epreuve/cause-stock.txt est absent : la cause de la panne se consigne avant la "
        "réparation.",
    )
    # Un diagnostic se juge sur le fond : il nomme ce que stock cherche (la clé
    # SEUIL) et dit que cela manque, que ce soit par l'état affiché par
    # Kubernetes ou par une phrase.
    lue = _compact(cause.content_string)
    dit_le_manque = any(m in lue for m in DIT_LE_MANQUE)
    assert "seuil" in lue and dit_le_manque, message(
        en="cause-stock.txt must say what the stock container looks for without finding it, and "
        "that it is missing: the waiting reason Kubernetes shows, or a sentence that says it.",
        fr="cause-stock.txt doit dire ce que le conteneur de stock cherche sans le trouver, et que "
        "cela manque : la raison d'attente qu'affiche Kubernetes, ou une phrase qui le dit.",
    )
    dep = _json(host, ENTREPOT, "get deployment stock")
    assert dep is not None, message(
        en=f"No Deployment stock in the {ENTREPOT} space any more: it is repaired, not removed.",
        fr=f"Plus de Deployment stock dans l'espace {ENTREPOT} : il se répare, il ne se retire pas.",
    )
    # stock doit lire son seuil dans une configuration gérée à part : la clé
    # manquante ajoutée au ConfigMap d'origine, ou un ConfigMap versionné vers
    # lequel le Deployment est repointé (la pratique de la leçon ConfigMaps),
    # sont acceptés. Retirer la variable, ou l'écrire en dur, ne l'est pas.
    ref = next((((e.get("valueFrom") or {}).get("configMapKeyRef") or {})
                for e in _conteneur(dep).get("env") or [] if e.get("name") == "STOCK_SEUIL"), {})
    assert ref.get("name") and ref.get("key"), message(
        en="stock no longer reads STOCK_SEUIL from a configuration managed apart: the repair "
        "gives the configuration what is missing, it does not remove what the component reads, "
        "nor write it in its description.",
        fr="stock ne lit plus STOCK_SEUIL dans une configuration gérée à part : la réparation "
        "donne à la configuration ce qui lui manque, elle ne retire pas ce que le composant lit, "
        "et ne l'écrit pas dans sa description.",
    )
    seuil = ((_json(host, ENTREPOT, f"get configmap {ref['name']}") or {}).get("data") or {}).get(ref["key"])
    assert seuil == SEUIL, message(
        en=f"The threshold stock reads (key {ref['key']} of {ref['name']}) is {seuil!r}, expected "
        f"{SEUIL!r} as the requirements say.",
        fr=f"Le seuil que lit stock (clé {ref['key']} de {ref['name']}) vaut {seuil!r}, attendu "
        f"{SEUIL!r} comme le dit le cahier des charges.",
    )
    # La configuration est juste : le kubelet redémarre le conteneur, on l'attend.
    fin = time.monotonic() + ATTENTE
    pods = _pods_vivants(host, ENTREPOT, "app=stock")
    while not pods and time.monotonic() < fin:
        time.sleep(PAS)
        pods = _pods_vivants(host, ENTREPOT, "app=stock")
    assert pods, message(
        en=f"stock is still not running after {ATTENTE}s, although its configuration is complete.",
        fr=f"stock ne tourne toujours pas après {ATTENTE}s, alors que sa configuration est complète.",
    )
    demarre = ((pods[0]["status"].get("containerStatuses") or [{}])[0].get("state") or {}).get("running", {}).get("startedAt", "")
    ecart = host.run(f"echo $(( $(date -d '{demarre}' +%s) - $(stat -c %Y {fichier}) ))")
    assert ecart.rc == 0 and int(ecart.stdout.strip() or "-1") >= 0, message(
        en="cause-stock.txt was written or modified after the repaired container started: the "
        "cause is recorded BEFORE the repair, then left untouched.",
        fr="cause-stock.txt a été écrit ou modifié après le démarrage du conteneur réparé : la "
        "cause se consigne AVANT la réparation, puis on n'y touche plus.",
    )
