"""test_functional.py : k8s-challenge-livrer-une-image-verifiee

Le challenge du module Chaîne d'approvisionnement. Ces tests lisent l'état du
NŒUD, du registre et du cluster, jamais les commandes tapées. Un test vérifie
un seul état, dans l'ordre de la fiche.

Les neuf premiers reprennent les mesures attestées de quatre labs guidés :
cks-image-pinned-digest (états 1 à 3), cks-dockerfile-static-analysis (état
4), cks-cosign-verify-image (états 5 à 7) et cks-image-scanning-trivy (états 8
et 9). Les analyses sont REJOUÉES ici, jamais lues dans un rapport.

Le dixième est nouveau : le cluster doit refuser, à la création, un Pod dont
l'image ne porte pas de signature valide, et accepter l'image signée. Il se lit
par deux soumissions à sec côté serveur (`--dry-run=server`) : elles traversent
toute la chaîne d'admission, webhooks compris, sans rien créer ni tirer
d'image. Kyverno déclare ses webhooks sans effet de bord en dry-run, ce qui
rend ces soumissions légitimes.

Les dix tests échouent sur l'état que pose le setup : vitrine sur un tag,
Dockerfile fautif, ni clé ni signature, boutique sur nginx:1.21, Kyverno sans
aucune politique.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "livraison"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
EPINGLE = "vitrine"
IMAGE_DEMANDEE = "nginx:1.27-alpine"
SCANNE = "boutique"
IMAGE_ORIGINE = "nginx:1.21"
REPERTOIRE = "/root/inventaire"
DOCKERFILE = f"{REPERTOIRE}/Dockerfile"
CONFIGMAP = "cosign-pub-key"
IMAGE_SIGNEE = "localhost:5000/appli/web:1.0"
IMAGE_NUE = "localhost:5000/appli/outil:1.0"
#: Les cinq constats que l'analyse fait sur le Dockerfile de départ, mesurés
#: le 2026-09-16 avec Trivy 0.74.0 (lab guidé cks-dockerfile-static-analysis).
CONSTATS_DU_DEPART = {
    "DS-0001": "le tag flottant « latest »",
    "DS-0002": "l'image tourne en root",
    "DS-0004": "le port 22 est exposé",
    "DS-0026": "aucun HEALTHCHECK",
    "DS-0029": "apt-get sans --no-install-recommends",
}
#: Kyverno enregistre ses webhooks quelques secondes après qu'une politique est
#: acceptée : budget borné pour ne pas recaler une correction juste.
BUDGET_S = 60


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _deploiement(host, nom: str) -> dict:
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get deployment {nom} -o json")
    assert rc == 0 and sortie, message(
        en=f"Deployment {nom} no longer exists in {NAMESPACE}: setup had placed it "
        f"there, it had to be changed, not replaced. Output: {diagnostic}",
        fr=f"Le Deployment {nom} n'existe plus dans {NAMESPACE} : le setup l'avait "
        f"posé, il fallait le modifier, pas le remplacer. Sortie : {diagnostic}",
    )
    return json.loads(sortie)


def _image(deploiement: dict) -> str:
    return deploiement["spec"]["template"]["spec"]["containers"][0]["image"]


def _digest(reference: str) -> str:
    """Le digest d'une référence d'image (après le dernier @), ou une chaîne vide."""
    return reference.split("@")[-1] if "@" in reference else ""


# ----------------------------------------------------------------------
# 1. vitrine référence son image par son digest.
# ----------------------------------------------------------------------
def test_vitrine_reference_son_image_par_digest(host):
    image = _image(_deploiement(host, EPINGLE))
    assert "@sha256:" in image, message(
        en=f"Deployment {EPINGLE} still references its image by a mutable name: "
        f"\"{image}\". The expected form is repository@sha256:<hexadecimal>.",
        fr=f"Le Deployment {EPINGLE} référence encore son image par un nom mutable : "
        f"« {image} ». La forme attendue est dépôt@sha256:<hexadécimal>.",
    )
    assert ":1.27-alpine@" not in image, message(
        en=f"The reference \"{image}\" keeps the tag next to the digest. Kubernetes "
        "ignores the tag, but it suggests the tag still counts: keep only the digest.",
        fr=f"La référence « {image} » garde le tag à côté du digest. Kubernetes ignore "
        "le tag, mais il laisse croire que le tag compte encore : ne gardez que le digest.",
    )


# ----------------------------------------------------------------------
# 2. C'est toujours l'image demandée.
# ----------------------------------------------------------------------
def test_c_est_toujours_l_image_demandee(host):
    """On compare au digest que le runtime du nœud connaît pour
    nginx:1.27-alpine ; le setup l'a tiré sur le plan de contrôle."""
    image = _image(_deploiement(host, EPINGLE))
    depot = image.split("@")[0]
    assert depot.split("/")[-1].split(":")[0] == "nginx", message(
        en=f"The reference points at \"{depot}\": nginx had to be pinned, not swapped.",
        fr=f"La référence pointe « {depot} » : il fallait épingler nginx, pas en changer.",
    )
    res = host.run(f"sudo crictl inspecti -o json {IMAGE_DEMANDEE}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"The node's runtime does not know {IMAGE_DEMANDEE}: the digest cannot be "
        f"checked. {res.stderr.strip()[:200]}",
        fr=f"Le runtime du nœud ne connaît pas {IMAGE_DEMANDEE} : impossible de "
        f"vérifier le digest. {res.stderr.strip()[:200]}",
    )
    connus = {
        _digest(r) for r in (json.loads(res.stdout).get("status") or {}).get("repoDigests", [])
    }
    assert _digest(image) in connus, message(
        en=f"The declared digest is not the one of {IMAGE_DEMANDEE}. Declared: "
        f"{_digest(image) or 'none'}. Known to the runtime: {', '.join(sorted(connus)) or 'none'}.",
        fr=f"Le digest déclaré n'est pas celui de {IMAGE_DEMANDEE}. Déclaré : "
        f"{_digest(image) or 'aucun'}. Connu(s) du runtime : {', '.join(sorted(connus)) or 'aucun'}.",
    )


# ----------------------------------------------------------------------
# 3. Le digest déclaré est celui que le nœud exécute, les réplicas tournent.
# ----------------------------------------------------------------------
def test_le_digest_declare_est_celui_que_le_noeud_execute(host):
    """`status.containerStatuses[].imageID` est écrit par le kubelet après que
    le runtime a résolu l'image : il dit ce qui tourne. La santé du
    déploiement n'a pas de test à elle, deux réplicas prêts étant vrais avant
    le travail ; ici elle ne s'atteint qu'après un épinglage qui n'a rien
    cassé."""
    d = _deploiement(host, EPINGLE)
    declare = _digest(_image(d))
    assert declare, message(
        en=f"Deployment {EPINGLE} declares no digest: there is nothing to compare.",
        fr=f"Le Deployment {EPINGLE} ne déclare aucun digest : il n'y a rien à comparer.",
    )
    prets = (d.get("status") or {}).get("readyReplicas", 0)
    assert prets == 2, message(
        en=f"{prets} replica(s) out of 2 are ready after the pinning. A digest that "
        "matches no image leaves the Pod in ImagePullBackOff: look at its events.",
        fr=f"{prets} réplica(s) sur 2 sont prêts après l'épinglage. Un digest qui ne "
        "correspond à aucune image laisse le Pod en ImagePullBackOff : regardez ses events.",
    )
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} get pods -l app={EPINGLE} "
        "-o jsonpath='{range .items[*]}{.status.containerStatuses[0].imageID}{\"\\n\"}{end}'",
    )
    resolus = [ligne.strip() for ligne in sortie.splitlines() if ligne.strip()]
    assert rc == 0 and len(resolus) == 2, message(
        en=f"{len(resolus)} replica(s) of {EPINGLE} return their imageID; two are "
        f"expected. A rollout may still be running. {diagnostic}",
        fr=f"{len(resolus)} réplica(s) de {EPINGLE} rendent leur imageID, on en attend "
        f"deux. Un déploiement est peut-être encore en cours. {diagnostic}",
    )
    ecarts = [r for r in resolus if _digest(r) != declare]
    assert not ecarts, message(
        en=f"The Deployment declares {declare}, but at least one replica runs something "
        f"else: {', '.join(ecarts)}.",
        fr=f"Le Deployment déclare {declare}, mais un réplica au moins exécute autre "
        f"chose : {', '.join(ecarts)}.",
    )


# ----------------------------------------------------------------------
# 4. Les constats du Dockerfile ont disparu, l'application est la même.
# ----------------------------------------------------------------------
def test_les_constats_du_dockerfile_ont_disparu(host):
    """Les constats sont nommés par leur numéro : exiger « zéro constat »
    deviendrait rouge le jour où Trivy ajouterait une règle."""
    res = host.run(f"sudo cat {DOCKERFILE}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No readable Dockerfile at {DOCKERFILE}. Deleting it silences the "
        "analysis, it does not satisfy it.",
        fr=f"Aucun Dockerfile lisible en {DOCKERFILE}. Le supprimer fait taire "
        "l'analyse, cela ne la satisfait pas.",
    )
    contenu = res.stdout
    assert "node" in contenu.lower() and "server.js" in contenu, message(
        en="The Dockerfile no longer starts from a Node image or no longer runs "
        "server.js: the findings had to be fixed, not the application changed.",
        fr="Le Dockerfile ne part plus d'une image Node ou ne lance plus server.js : "
        "il fallait corriger les constats, pas changer l'application.",
    )
    res = host.run(f"sudo trivy config --quiet --format json {REPERTOIRE} 2>/dev/null")
    assert res.rc == 0 and res.stdout.strip(), message(
        en="Trivy could not analyse the application's directory. The tool is "
        f"installed by setup. Output: {res.stderr.strip()[:300]}",
        fr="Trivy n'a pas pu analyser le répertoire de l'application. L'outil est "
        f"posé par le setup. Sortie : {res.stderr.strip()[:300]}",
    )
    trouves = {
        str(m.get("ID"))
        for r in json.loads(res.stdout).get("Results") or []
        for m in r.get("Misconfigurations") or []
    }
    restants = trouves & set(CONSTATS_DU_DEPART)
    assert not restants, message(
        en="The analysis still reports:\n  "
        + "\n  ".join(f"{i}: {CONSTATS_DU_DEPART[i]}" for i in sorted(restants)),
        fr="L'analyse reproche encore :\n  "
        + "\n  ".join(f"{i} : {CONSTATS_DU_DEPART[i]}" for i in sorted(restants)),
    )


# ----------------------------------------------------------------------
# 5. La clé publique est publiée dans le cluster.
# ----------------------------------------------------------------------
def test_la_cle_publique_est_publiee_dans_le_cluster(host):
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get configmap {CONFIGMAP} -o json")
    assert rc == 0 and sortie, message(
        en=f"No ConfigMap {CONFIGMAP} in {NAMESPACE}. Output: {diagnostic}",
        fr=f"Aucun ConfigMap {CONFIGMAP} dans {NAMESPACE}. Sortie : {diagnostic}",
    )
    donnees = json.loads(sortie).get("data") or {}
    assert "BEGIN PUBLIC KEY" in str(donnees.get("cosign.pub", "")), message(
        en=f"ConfigMap {CONFIGMAP} carries no public key under the cosign.pub key. "
        f"It carries {sorted(donnees)}.",
        fr=f"Le ConfigMap {CONFIGMAP} ne porte pas de clé publique sous la clé "
        f"cosign.pub. Il porte {sorted(donnees)}.",
    )
    assert "PRIVATE KEY" not in "\n".join(str(v) for v in donnees.values()), message(
        en="The ConfigMap contains a PRIVATE key: whoever reads it can sign any image "
        "in your name. Only the public key is published.",
        fr="Le ConfigMap contient une clé PRIVÉE : qui la lit peut signer n'importe "
        "quelle image en votre nom. Seule la clé publique se publie.",
    )


# ----------------------------------------------------------------------
# 6. La signature est poussée dans le registre, à côté de l'image.
# ----------------------------------------------------------------------
def test_la_signature_est_poussee_dans_le_registre(host):
    """cosign 3.1.3 range la signature sous un tag `sha256-<digest>`, sans le
    suffixe `.sig` des versions antérieures (mesuré le 2026-09-16) : on la
    reconnaît à son préfixe."""
    res = host.run("sudo crane ls localhost:5000/appli/web 2>/dev/null")
    assert res.rc == 0, message(
        en="The local registry does not answer on localhost:5000.",
        fr="Le registre local ne répond pas sur localhost:5000.",
    )
    tags = res.stdout.split()
    assert any(t.startswith("sha256-") for t in tags), message(
        en=f"Repository appli/web only carries {tags}: no signature has been pushed "
        "next to the image.",
        fr=f"Le dépôt appli/web ne porte que {tags} : aucune signature n'a été poussée "
        "à côté de l'image.",
    )


# ----------------------------------------------------------------------
# 7. La clé publiée accepte l'image signée et refuse l'autre.
# ----------------------------------------------------------------------
def _verifie(host, image: str) -> bool:
    """cosign accepte-t-il cette image avec la clé lue DANS le ConfigMap ?"""
    res = host.run(
        "set -e; "
        f"sudo {KUBECTL} -n {NAMESPACE} get configmap {CONFIGMAP} "
        "-o jsonpath='{.data.cosign\\.pub}' > /tmp/verif-livraison.pub; "
        f"sudo cosign verify --key /tmp/verif-livraison.pub {image} >/dev/null 2>&1; "
        "echo $?"
    )
    return res.stdout.strip().endswith("0")


def test_la_cle_accepte_l_image_signee_et_refuse_l_autre(host):
    assert _verifie(host, IMAGE_SIGNEE), message(
        en=f"The published key does not validate {IMAGE_SIGNEE}. A pair regenerated "
        "after the signature never validates anything.",
        fr=f"La clé publiée ne valide pas {IMAGE_SIGNEE}. Une paire régénérée après la "
        "signature ne valide jamais rien.",
    )
    assert not _verifie(host, IMAGE_NUE), message(
        en=f"The published key also validates {IMAGE_NUE}, which nobody signed: the "
        "verification measures nothing.",
        fr=f"La clé publiée valide aussi {IMAGE_NUE}, que personne n'a signée : la "
        "vérification ne mesure rien.",
    )


# ----------------------------------------------------------------------
# 8. L'image de boutique n'est plus celle d'origine.
# ----------------------------------------------------------------------
def test_l_image_de_boutique_n_est_plus_celle_d_origine(host):
    image = _image(_deploiement(host, SCANNE))
    assert image != IMAGE_ORIGINE, message(
        en=f"Deployment {SCANNE} still runs on {IMAGE_ORIGINE}. Analysing an image "
        "without replacing it reduces no exposure.",
        fr=f"Le Deployment {SCANNE} tourne toujours sur {IMAGE_ORIGINE}. Analyser une "
        "image sans la remplacer ne réduit aucune exposition.",
    )
    assert image.split("@")[0].split(":")[0].split("/")[-1] == "nginx", message(
        en=f"The image has become \"{image}\": nginx had to be updated, not the "
        "application changed.",
        fr=f"L'image est devenue « {image} » : il fallait mettre nginx à jour, pas "
        "changer d'application.",
    )


# ----------------------------------------------------------------------
# 9. La nouvelle image porte strictement moins de failles critiques.
# ----------------------------------------------------------------------
def _critiques(host, image: str) -> int:
    """Le nombre de failles CRITICAL que Trivy trouve. Un scan qui échoue n'est
    pas compté comme zéro."""
    res = host.run(
        f"sudo trivy image --quiet --scanners vuln --severity CRITICAL --format json {image} 2>/dev/null"
    )
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"Trivy could not analyse {image} on the node. Output: {res.stderr.strip()[:300]}",
        fr=f"Trivy n'a pas pu analyser {image} sur le nœud. Sortie : {res.stderr.strip()[:300]}",
    )
    rapport = json.loads(res.stdout)
    return sum(len(r.get("Vulnerabilities") or []) for r in rapport.get("Results") or [])


def test_la_nouvelle_image_porte_moins_de_failles_critiques(host):
    """Les deux images sont scannées MAINTENANT, avec la même base."""
    d = _deploiement(host, SCANNE)
    image = _image(d)
    prets = (d.get("status") or {}).get("readyReplicas", 0)
    assert prets == 2, message(
        en=f"{prets} replica(s) of {SCANNE} out of 2 are ready after the image change: "
        "look at the Pods' events and logs.",
        fr=f"{prets} réplica(s) de {SCANNE} sur 2 sont prêts après le changement "
        "d'image : regardez les events et les logs des Pods.",
    )
    avant = _critiques(host, IMAGE_ORIGINE)
    apres = _critiques(host, image)
    assert avant > 0, message(
        en=f"Trivy finds no critical vulnerability in {IMAGE_ORIGINE}: the "
        "vulnerability database is probably absent or truncated.",
        fr=f"Trivy ne trouve aucune faille critique dans {IMAGE_ORIGINE} : la base de "
        "vulnérabilités est probablement absente ou tronquée.",
    )
    assert apres < avant, message(
        en=f"{image} carries {apres} critical vulnerability(ies), against {avant} for "
        f"{IMAGE_ORIGINE}. Scan several candidates BEFORE deploying.",
        fr=f"{image} porte {apres} faille(s) critique(s), contre {avant} pour "
        f"{IMAGE_ORIGINE}. Scannez plusieurs candidates AVANT de déployer.",
    )


# ----------------------------------------------------------------------
# 10. Le cluster refuse l'image non signée et accepte l'image signée.
# ----------------------------------------------------------------------
def _soumettre(host, nom: str, image: str) -> tuple[bool, str]:
    """Soumet un Pod à l'admission sans rien créer : (accepté, réponse)."""
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} run {nom} --image={image} --restart=Never "
        "--dry-run=server -o name --command -- sh -c 'sleep 30'",
    )
    return rc == 0, diagnostic or sortie


def test_le_cluster_refuse_l_image_non_signee_et_accepte_la_signee(host):
    """Les deux sens dans le même test : sans politique tout passe, avec une
    politique qui refuse tout le Pod signé tomberait aussi. Seule la paire dit
    que le cluster vérifie une signature."""
    fin = time.monotonic() + BUDGET_S
    accepte, refus = True, ""
    while time.monotonic() < fin:
        accepte, refus = _soumettre(host, "sonde-non-signee", IMAGE_NUE)
        if not accepte:
            break
        time.sleep(5)
    assert not accepte, message(
        en=f"After {BUDGET_S} seconds, the cluster still admits a Pod running "
        f"{IMAGE_NUE}, which nobody signed. Nothing checks signatures at admission.",
        fr=f"Après {BUDGET_S} secondes, le cluster admet toujours un Pod qui exécute "
        f"{IMAGE_NUE}, que personne n'a signée. Rien ne vérifie les signatures à "
        "l'admission.",
    )
    bas = refus.lower()
    assert "admission webhook" in bas and ("verif" in bas or "signature" in bas), message(
        en=f"The Pod was refused, but not by a signature check. The refusal says: {refus[:400]}",
        fr=f"Le Pod a été refusé, mais pas par une vérification de signature. Le refus "
        f"dit : {refus[:400]}",
    )
    accepte, reponse = _soumettre(host, "sonde-signee", IMAGE_SIGNEE)
    assert accepte, message(
        en=f"The signed image {IMAGE_SIGNEE} is refused too: {reponse[:400]}. A cluster "
        "that refuses everything is an outage; check the key in the policy and how "
        "the signature is stored.",
        fr=f"L'image signée {IMAGE_SIGNEE} est refusée elle aussi : {reponse[:400]}. Un "
        "cluster qui refuse tout est en panne ; vérifiez la clé de la politique et la "
        "façon dont la signature est rangée.",
    )
