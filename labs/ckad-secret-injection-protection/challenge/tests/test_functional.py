"""test_functional.py : ckad-secret-injection-protection

Ces tests lisent l'état réel du CLUSTER et l'intérieur du conteneur, jamais un
fichier YAML du poste ni les commandes tapées.

Un test par état demandé par l'énoncé, et neuf états. Le découpage n'est pas
cosmétique : regroupés, le premier échec masquait les suivants, et chaque moitié
pesait la moitié de la note au lieu de sa part.

Deux tests ferment une faute que la version précédente laissait passer : rendre
100 en laissant le mot de passe en clair ailleurs. Le premier
(`test_le_secret_porte_le_mot_de_passe`) LIT le `.data` du Secret, le décode et
le compare ; le cinquième
(`test_le_mot_de_passe_n_est_en_clair_nulle_part_ailleurs`) balaye les
ConfigMaps du namespace et refuse la valeur. Sans eux, un ConfigMap portant le
mot de passe en clair, injecté par `envFrom`, satisfaisait tout le reste.

CHAQUE TEST EXIGE L'ÉTAT D'ARRIVÉE, JAMAIS UN ÉTAT DÉJÀ VRAI AU DÉPART.
Mesuré le 2026-11-10 : trois des neuf passaient AVANT le travail, donc
donnaient des points pour la situation posée par le setup. Un test qui ne sait
pas refuser ne mesure rien, et les trois se trompaient de la même façon : ils
regardaient un fait vrai au départ au lieu de l'état que le travail produit.

- le cinquième mesure une ABSENCE, et une absence est vraie avant qu'on
  commence : aucun ConfigMap du namespace ne porte le mot de passe sur un lab
  neuf. Il est donc CONDITIONNÉ à l'état qui lui donne son sens : la valeur est
  dans un Secret, ET elle n'est en clair dans aucun ConfigMap. Déplacer la
  valeur vers un ConfigMap échoue alors deux fois, et ne rend plus ce point ;
- le septième voyait « un Pod tourne », ce qui est vrai dès le setup. Il lit
  maintenant le `spec` du Pod QUI TOURNE et y exige la projection du Secret :
  seul un Pod né du gabarit modifié la porte ;
- le huitième voyait `DB_PASSWORD` porter la bonne valeur, ce qui est vrai dès
  le setup, puisque c'est le défaut même que le lab fait corriger. Il exige
  maintenant la valeur ET son origine, lue dans le Pod réel.

Le gabarit de Pod et le Pod réel ne se confondent pas : le premier dit ce que
le Deployment demande, le second dit ce qui tourne. Les tests 2 et 3 lisent le
gabarit, les tests 7 et 8 lisent le Pod.

Le choix du nom du Secret et de sa clé reste à l'apprenant : les tests
DÉCOUVRENT l'objet qui porte la valeur, puis exigent que ce soit CELUI-LÀ que
le Deployment référence et monte. C'est l'énoncé qui demande un objet dédié,
pas un nom imposé.
"""

from __future__ import annotations

import base64
import json
import shlex
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "paiement"
DEPLOYMENT = "passerelle"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
VALEUR = "Tr3s0r-2026"
VARIABLE = "DB_PASSWORD"
CHEMIN_MONTE = "/etc/passerelle"

#: Attente du rollout : 18 tours de 5 s, soit 90 s, comme les autres labs du
#: catalogue qui modifient un Deployment.
TOURS = 18
DELAI = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS.

    Un appel en échec et un appel qui rend du vide appellent deux gestes
    opposés : les assertions ne les confondent jamais.
    """
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _deployment(host) -> dict:
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json"
    )
    assert rc == 0 and sortie, message(
        en=f"Deployment {DEPLOYMENT} cannot be read in {NAMESPACE}. Setup had "
        "placed it there: it must be MODIFIED, not deleted and recreated. "
        f"{diagnostic}",
        fr=f"Le Deployment {DEPLOYMENT} est illisible dans {NAMESPACE}. Le setup "
        "l'avait posé : il doit être MODIFIÉ, pas supprimé puis recréé. "
        f"{diagnostic}",
    )
    return json.loads(sortie)


def _spec_pod(host) -> dict:
    """Le `spec` du gabarit de Pod, celui que le Deployment impose."""
    return _deployment(host)["spec"]["template"]["spec"]


def _attendre_rollout(host) -> dict:
    """Rend le Deployment une fois sa mise à jour terminée, ou au bout du délai.

    Sans cette attente, les tests qui entrent dans un conteneur peuvent tomber
    sur l'ANCIEN Pod, encore en Running pendant la bascule, et rendre rouge un
    travail correct.
    """
    d = {}
    for _ in range(TOURS):
        d = _deployment(host)
        attendu = d["spec"].get("replicas") or 0
        statut = d.get("status") or {}
        if (
            attendu
            and statut.get("readyReplicas", 0) == attendu
            and statut.get("updatedReplicas", 0) == attendu
        ):
            break
        time.sleep(DELAI)
    return d


def _secrets_du_namespace(host) -> dict[str, dict[str, str | None]]:
    """Les Secrets Opaque du namespace : {nom: {clé: valeur décodée ou None}}.

    Une valeur qui n'est pas du base64 lisible en texte rend None : c'est une
    donnée de l'apprenant, elle ne doit pas faire lever le test.
    """
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get secret -o json")
    assert rc == 0 and sortie, message(
        en=f"Cannot read the Secrets of {NAMESPACE}. {diagnostic}",
        fr=f"Impossible de lire les Secrets de {NAMESPACE}. {diagnostic}",
    )
    inventaire: dict[str, dict[str, str | None]] = {}
    for s in json.loads(sortie).get("items", []):
        if s.get("type") != "Opaque":
            continue
        contenu: dict[str, str | None] = {}
        for cle, brut in (s.get("data") or {}).items():
            try:
                contenu[cle] = base64.b64decode(brut).decode()
            except (ValueError, UnicodeDecodeError):
                contenu[cle] = None
        inventaire[s["metadata"]["name"]] = contenu
    return inventaire


def _porteurs(inventaire: dict[str, dict[str, str | None]]) -> list[tuple[str, str]]:
    """Les couples (nom du Secret, clé) dont la valeur décodée EST le mot de passe."""
    return [
        (nom, cle)
        for nom, contenu in inventaire.items()
        for cle, valeur in contenu.items()
        if valeur is not None and valeur.strip() == VALEUR
    ]


def _message_sans_porteur() -> str:
    return message(
        en="No Secret in the namespace holds the password as the content of one "
        "of its keys. That is the first state asked for, and the other tests "
        "all rest on it: they look for the Secret BY ITS CONTENT, not by a "
        "name imposed on you.",
        fr="Aucun Secret du namespace ne porte le mot de passe comme contenu "
        "d'une de ses clés. C'est le premier état demandé, et les autres tests "
        "s'appuient tous dessus : ils cherchent le Secret PAR SON CONTENU, pas "
        "par un nom qui vous serait imposé.",
    )


def _secret_requis(host) -> tuple[str, str]:
    """Le Secret qui porte la valeur, et la clé sous laquelle il la porte."""
    porteurs = _porteurs(_secrets_du_namespace(host))
    assert porteurs, _message_sans_porteur()
    return porteurs[0]


def _variables_declarees(spec: dict) -> list[str | None]:
    """Les noms de toutes les variables d'environnement déclarées, pour le message."""
    return [
        v.get("name")
        for c in spec.get("containers") or []
        for v in c.get("env") or []
    ]


def _entrees_de_la_variable(spec: dict) -> list[dict]:
    """Les déclarations de DB_PASSWORD trouvées dans ce `spec`."""
    return [
        v
        for c in spec.get("containers") or []
        for v in c.get("env") or []
        if v.get("name") == VARIABLE
    ]


def _secrets_references_par_la_variable(spec: dict) -> list[str | None]:
    """Le Secret que chaque déclaration de DB_PASSWORD désigne, ou None.

    Un `value:` nu rend None : c'est exactement ce que le setup pose, et ce que
    le travail doit remplacer.
    """
    return [
        ((v.get("valueFrom") or {}).get("secretKeyRef") or {}).get("name")
        for v in _entrees_de_la_variable(spec)
    ]


def _volumes_du_secret(spec: dict, nom_secret: str) -> list[str]:
    """Les noms des volumes du gabarit qui proviennent de ce Secret."""
    return [
        v["name"]
        for v in spec.get("volumes") or []
        if (v.get("secret") or {}).get("secretName") == nom_secret
    ]


def _montages(spec: dict, noms_de_volumes: list[str]) -> list[dict]:
    return [
        m
        for c in spec.get("containers") or []
        for m in c.get("volumeMounts") or []
        if m.get("name") in noms_de_volumes
    ]


def _chemin_attendu(spec: dict, nom_secret: str, cle: str) -> str:
    """Le chemin, dans le conteneur, où la clé du Secret doit apparaître.

    Un Secret monté en volume dépose chaque clé comme un fichier portant son
    nom. L'apprenant peut renommer ce fichier (`items[].path`) ou monter la
    seule clé (`subPath`) : on vise alors le chemin qu'il a déclaré, jamais un
    `cat` de tout le répertoire. Concaténer le répertoire ferait échouer un
    état atteint dès que le Secret porte une deuxième clé.
    """
    noms = _volumes_du_secret(spec, nom_secret)
    volumes = {v["name"]: v for v in spec.get("volumes") or []}
    fichier = cle
    for montage in _montages(spec, noms):
        if montage.get("mountPath") != CHEMIN_MONTE:
            continue
        items = (volumes.get(montage["name"], {}).get("secret") or {}).get("items") or []
        for item in items:
            if item.get("key") == cle and item.get("path"):
                fichier = item["path"]
        if montage.get("subPath"):
            return CHEMIN_MONTE
    return f"{CHEMIN_MONTE}/{fichier}"


def _message_sans_pod(diagnostic: str) -> str:
    return message(
        en=f"No up-to-date Pod of {DEPLOYMENT} is ready in {NAMESPACE} after "
        f"{TOURS * DELAI} s. A Pod that references a missing Secret, or a key "
        "that does not exist in that Secret, does not start: it stays in "
        "CreateContainerConfigError, and `kubectl describe pod` names the "
        f"missing key in its events. {diagnostic}",
        fr=f"Aucun Pod à jour de {DEPLOYMENT} n'est prêt dans {NAMESPACE} après "
        f"{TOURS * DELAI} s. Un Pod qui référence un Secret absent, ou une clé "
        "qui n'existe pas dans ce Secret, ne démarre pas : il reste en "
        "CreateContainerConfigError, et `kubectl describe pod` nomme la clé "
        f"manquante dans ses events. {diagnostic}",
    )


def _un_pod(host) -> tuple[str, str]:
    """Rend (nom du Pod à jour et prêt, diagnostic), sans jamais lever.

    On attend d'abord la fin du rollout, puis on retient le plus RÉCENT des
    Pods prêts et non en cours de suppression. Prendre `items[0]` tombait sur
    l'ancien Pod pendant une bascule.
    """
    _attendre_rollout(host)
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get pod -l app={DEPLOYMENT} -o json"
    )
    if rc != 0 or not sortie:
        return "", diagnostic
    candidats = []
    for p in json.loads(sortie).get("items", []):
        meta = p.get("metadata") or {}
        statut = p.get("status") or {}
        if meta.get("deletionTimestamp") or statut.get("phase") != "Running":
            continue
        pret = any(
            c.get("type") == "Ready" and c.get("status") == "True"
            for c in statut.get("conditions") or []
        )
        if pret:
            candidats.append((meta.get("creationTimestamp", ""), meta.get("name", "")))
    if not candidats:
        return "", diagnostic
    return max(candidats)[1], diagnostic


def _pod_requis(host) -> str:
    nom, diagnostic = _un_pod(host)
    assert nom, _message_sans_pod(diagnostic)
    return nom


def _spec_du_pod_reel(host, nom: str) -> dict:
    """Le `spec` du Pod qui tourne, lu sur le Pod lui-même.

    Le gabarit du Deployment dit ce qui est DEMANDÉ ; ce Pod dit ce qui TOURNE.
    Un Pod tournait déjà avant le travail, posé par le setup : c'est en lisant
    son propre `spec` qu'on distingue celui-là du Pod né du gabarit modifié.
    """
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get pod {nom} -o json")
    assert rc == 0 and sortie, message(
        en=f"Pod {nom} cannot be read in {NAMESPACE}, so nothing was measured "
        f"about what it carries. {diagnostic}",
        fr=f"Le Pod {nom} est illisible dans {NAMESPACE}, donc rien n'a été mesuré "
        f"sur ce qu'il porte. {diagnostic}",
    )
    return json.loads(sortie)["spec"]


# ----------------------------------------------------------------------
# 1. Un objet dédié porte la valeur, et on le LIT.
# ----------------------------------------------------------------------
def test_le_secret_porte_le_mot_de_passe(host):
    inventaire = _secrets_du_namespace(host)
    assert inventaire, message(
        en=f"No application Secret in {NAMESPACE}. That is the object in which a "
        "sensitive value stops living in the middle of the application's "
        "manifest. It is created in one command, without writing YAML.",
        fr=f"Aucun Secret applicatif dans {NAMESPACE}. C'est l'objet dans lequel "
        "une valeur sensible cesse de vivre au milieu du manifeste de "
        "l'application. Il se crée en une commande, sans écrire de YAML.",
    )
    porteurs = _porteurs(inventaire)
    cles_lues = {nom: sorted(contenu) for nom, contenu in inventaire.items()}
    assert porteurs, message(
        en="A Secret exists, but none of its keys holds the password. Keys read: "
        f"{cles_lues}. The value a Secret carries is base64-encoded, which is "
        "transport and not protection: `kubectl get secret <name> -o "
        "jsonpath=\"{.data}\"` shows what was really stored, and `base64 -d` "
        "reads it back. Comparing the two is the way to see what was captured.",
        fr="Un Secret existe, mais aucune de ses clés ne porte le mot de passe. "
        f"Clés lues : {cles_lues}. La valeur qu'un Secret porte y est encodée en "
        "base64, ce qui est un transport et non une protection : `kubectl get "
        "secret <nom> -o jsonpath=\"{.data}\"` montre ce qui a vraiment été "
        "stocké, et `base64 -d` le relit. Comparer les deux est le moyen de voir "
        "ce qui a été capturé.",
    )


# ----------------------------------------------------------------------
# 2. La variable que l'application attend vient de CE Secret.
# ----------------------------------------------------------------------
def test_db_password_vient_du_secret_par_reference(host):
    nom_secret, _ = _secret_requis(host)
    spec = _spec_pod(host)
    declarees = _variables_declarees(spec)
    entrees = _entrees_de_la_variable(spec)
    assert entrees, message(
        en=f"The container declares no {VARIABLE} environment variable. Variables "
        f"declared: {declarees}. The application still expects its password "
        "under that exact name: taking the value out of the manifest was to "
        "change nothing FOR THE APPLICATION.",
        fr=f"Le conteneur ne déclare aucune variable d'environnement {VARIABLE}. "
        f"Variables déclarées : {declarees}. L'application attend toujours son "
        "mot de passe sous ce nom exact : sortir la valeur du manifeste ne "
        "devait rien changer POUR L'APPLICATION.",
    )
    references = _secrets_references_par_la_variable(spec)
    assert nom_secret in references, message(
        en=f"{VARIABLE} does not take its value from Secret {nom_secret!r}, the one "
        f"that holds the password. What it references: {references}. A variable "
        "reads a Secret through valueFrom.secretKeyRef, which names the Secret "
        "and the key; a plain `value:` would put the password back into the "
        "manifest.",
        fr=f"{VARIABLE} ne tire pas sa valeur du Secret {nom_secret!r}, celui qui "
        f"porte le mot de passe. Ce qu'elle référence : {references}. Une "
        "variable lit un Secret par valueFrom.secretKeyRef, qui nomme le Secret "
        "et la clé ; un `value:` nu remettrait le mot de passe dans le "
        "manifeste.",
    )


# ----------------------------------------------------------------------
# 3. Le même Secret est monté, et à l'endroit demandé.
# ----------------------------------------------------------------------
def test_le_secret_est_monte_sous_etc_passerelle(host):
    nom_secret, _ = _secret_requis(host)
    spec = _spec_pod(host)
    declares = [v.get("name") for v in spec.get("volumes") or []]
    noms = _volumes_du_secret(spec, nom_secret)
    assert noms, message(
        en=f"No volume of the Pod template comes from Secret {nom_secret!r}. "
        f"Volumes declared: {declares}. The second injection path asked for is a "
        "volume of type `secret` under spec.template.spec.volumes.",
        fr=f"Aucun volume du gabarit de Pod ne provient du Secret {nom_secret!r}. "
        f"Volumes déclarés : {declares}. Le second chemin d'injection demandé est "
        "un volume de type `secret` sous spec.template.spec.volumes.",
    )
    montages = _montages(spec, noms)
    assert montages, message(
        en=f"Volume {noms} is declared but never mounted in the container: a "
        "declared volume alone puts no file anywhere. It takes a volumeMount in "
        "the container that places it at a path.",
        fr=f"Le volume {noms} est déclaré mais jamais monté dans le conteneur : un "
        "volume déclaré seul ne pose aucun fichier. Il faut un volumeMount dans "
        "le conteneur qui le place à un chemin.",
    )
    chemins = [m.get("mountPath") for m in montages]
    assert CHEMIN_MONTE in chemins, message(
        en=f"The Secret is mounted at {chemins}, and the directory asked for is "
        f"{CHEMIN_MONTE}. The path is part of the contract with the "
        "application: it is where it goes and reads its password.",
        fr=f"Le Secret est monté sur {chemins}, et le répertoire demandé est "
        f"{CHEMIN_MONTE}. Le chemin fait partie du contrat avec l'application : "
        "c'est là qu'elle va lire son mot de passe.",
    )


# ----------------------------------------------------------------------
# 4. La valeur a quitté le manifeste de l'application.
# ----------------------------------------------------------------------
def test_le_mot_de_passe_a_quitte_le_manifeste(host):
    """Mesuré le 2026-09-17 : avant le travail, `kubectl get deployment -o yaml`
    rend la valeur en clair au milieu du manifeste."""
    rc, manifeste, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o yaml"
    )
    assert rc == 0 and manifeste, message(
        en=f"Cannot read Deployment {DEPLOYMENT}. {diagnostic}",
        fr=f"Impossible de lire le Deployment {DEPLOYMENT}. {diagnostic}",
    )
    assert VALEUR not in manifeste, message(
        en=f"The password still appears in clear text in the manifest of "
        f"{DEPLOYMENT}. That is precisely what had to stop: this manifest is "
        "versioned, reviewed and copied, and anything that can read it can read "
        "the value. Moving it into a Secret does not encrypt it, but it stops "
        "sitting in the middle of the application's configuration.",
        fr=f"Le mot de passe apparaît encore en clair dans le manifeste de "
        f"{DEPLOYMENT}. C'est précisément ce qu'il fallait faire cesser : ce "
        "manifeste est versionné, relu et copié, et tout ce qui peut le lire "
        "peut lire la valeur. La déplacer dans un Secret ne la chiffre pas, "
        "mais elle cesse d'être au milieu de la configuration de "
        "l'application.",
    )


# ----------------------------------------------------------------------
# 5. Elle est dans un Secret, ET elle n'est pas allée en clair ailleurs.
# ----------------------------------------------------------------------
def test_le_mot_de_passe_n_est_en_clair_nulle_part_ailleurs(host):
    """Le test qui ferme le contournement, conditionné à l'état qui lui donne sens.

    Déplacer la valeur du manifeste vers un ConfigMap la fait bien disparaître
    du Deployment, et ne protège rien : un ConfigMap se lit comme le reste de
    la configuration, sans la moindre convention de confidentialité.

    Mais l'absence seule ne mesure rien : sur un lab neuf, aucun ConfigMap ne
    porte le mot de passe, et ce test passait donc AVANT le travail. L'état
    demandé n'est pas « nulle part », il est « dans le Secret, et nulle part
    ailleurs » : les deux moitiés se tiennent, et ensemble elles ne sont
    atteintes que par le travail.

    Le contournement reste refusé des deux façons : sans Secret, la première
    assertion tombe ; avec un Secret ET un ConfigMap porteurs, la seconde.
    """
    _secret_requis(host)
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get configmap -o json")
    assert rc == 0 and sortie, message(
        en=f"Cannot read the ConfigMaps of {NAMESPACE}. {diagnostic}",
        fr=f"Impossible de lire les ConfigMaps de {NAMESPACE}. {diagnostic}",
    )
    fautifs = []
    for cm in json.loads(sortie).get("items", []):
        nom = (cm.get("metadata") or {}).get("name", "?")
        for cle, valeur in (cm.get("data") or {}).items():
            if VALEUR in valeur:
                fautifs.append(f"{nom}/{cle}")
        for cle, brut in (cm.get("binaryData") or {}).items():
            try:
                texte = base64.b64decode(brut).decode()
            except (ValueError, UnicodeDecodeError):
                continue
            if VALEUR in texte:
                fautifs.append(f"{nom}/{cle}")
    assert not fautifs, message(
        en=f"The password is written in clear text in {fautifs}. A ConfigMap is "
        "read, copied and dumped like any other piece of configuration: moving "
        "the value there only changes which object exposes it. The object asked "
        "for is the one Kubernetes treats as sensitive, with its own RBAC "
        "verbs and its own encryption at rest.",
        fr=f"Le mot de passe est écrit en clair dans {fautifs}. Un ConfigMap se "
        "lit, se copie et s'exporte comme n'importe quelle configuration : y "
        "déplacer la valeur ne change que l'objet qui l'expose. L'objet demandé "
        "est celui que Kubernetes traite comme sensible, avec ses propres "
        "verbes RBAC et son chiffrement au repos.",
    )


# ----------------------------------------------------------------------
# 6. Le Deployment a été modifié, pas remplacé, et la bascule est finie.
# ----------------------------------------------------------------------
def test_le_deployment_a_ete_modifie_pas_remplace(host):
    """`metadata.generation` dit la vérité ici : le setup pose le Deployment à la
    génération 1, et toute modification de son `spec` l'incrémente. Un objet
    supprimé puis recréé repart à 1, et c'est ce que l'énoncé refuse."""
    d = _attendre_rollout(host)
    generation = (d.get("metadata") or {}).get("generation", 0)
    assert generation >= 2, message(
        en=f"Deployment {DEPLOYMENT} is still at generation {generation}: its spec "
        "has never been modified, so this object was created from scratch rather "
        "than updated. The one asked for is the one that was already running, "
        "with its history: `kubectl rollout history` shows it.",
        fr=f"Le Deployment {DEPLOYMENT} est encore à la génération {generation} : son "
        "spec n'a jamais été modifié, donc cet objet a été créé de zéro plutôt "
        "que mis à jour. Celui qui est demandé est celui qui tournait déjà, avec "
        "son historique : `kubectl rollout history` le montre.",
    )
    attendu = d["spec"].get("replicas") or 0
    statut = d.get("status") or {}
    prets = statut.get("readyReplicas", 0)
    a_jour = statut.get("updatedReplicas", 0)
    assert prets == attendu and a_jour == attendu, message(
        en=f"{prets} ready and {a_jour} up to date out of {attendu} after "
        f"{TOURS * DELAI} s: the rollout did not finish. The application was to "
        f"keep running. `kubectl -n {NAMESPACE} rollout status "
        f"deployment/{DEPLOYMENT}` says where it is stuck, and `kubectl describe "
        "pod` why.",
        fr=f"{prets} prêts et {a_jour} à jour sur {attendu} après "
        f"{TOURS * DELAI} s : la bascule n'est pas allée au bout. L'application "
        f"devait continuer de tourner. `kubectl -n {NAMESPACE} rollout status "
        f"deployment/{DEPLOYMENT}` dit où elle bloque, et `kubectl describe pod` "
        "pourquoi.",
    )


# ----------------------------------------------------------------------
# 7. Le Pod qui tourne est né du gabarit modifié : il porte la projection.
# ----------------------------------------------------------------------
def test_un_pod_a_jour_porte_la_projection_du_secret(host):
    """« Un Pod tourne » était vrai dès le setup, qui pose un Deployment à une
    réplique prête : ce test donnait un neuvième de la note pour la situation
    de départ. Ce qui prouve quelque chose, c'est QUEL Pod tourne, et on le
    reconnaît à ce qu'il porte : la projection du Secret dans son propre
    `spec`, celle que seul le gabarit modifié produit."""
    nom_secret, _ = _secret_requis(host)
    nom = _pod_requis(host)
    spec = _spec_du_pod_reel(host, nom)
    declares = [v.get("name") for v in spec.get("volumes") or []]
    noms = _volumes_du_secret(spec, nom_secret)
    assert noms, message(
        en=f"Pod {nom} is running, but no volume of ITS OWN spec comes from Secret "
        f"{nom_secret!r}. Volumes it carries: {declares}. A Pod was already "
        "running before you started, so a running Pod proves nothing by itself. "
        "The one asked for is the Pod born FROM the modified template: if you "
        "changed the Deployment and this Pod still carries nothing, the old Pod "
        f"is the one that survived. `kubectl -n {NAMESPACE} get pod -o wide` and "
        "`kubectl describe pod` say which generation it belongs to.",
        fr=f"Le Pod {nom} tourne, mais aucun volume de SON PROPRE spec ne provient "
        f"du Secret {nom_secret!r}. Volumes qu'il porte : {declares}. Un Pod "
        "tournait déjà avant que vous commenciez : un Pod qui tourne ne prouve "
        "donc rien à lui seul. Celui qui est demandé est le Pod né DU gabarit "
        "modifié : si vous avez changé le Deployment et que ce Pod ne porte "
        f"rien, c'est l'ancien qui a survécu. `kubectl -n {NAMESPACE} get pod -o "
        "wide` et `kubectl describe pod` disent de quelle génération il est.",
    )
    chemins = [m.get("mountPath") for m in _montages(spec, noms)]
    assert CHEMIN_MONTE in chemins, message(
        en=f"Pod {nom} carries volume {noms} from the Secret, but mounted at "
        f"{chemins} instead of {CHEMIN_MONTE}. The template may have been fixed "
        "after this Pod was born: the running Pod is the one that counts, and a "
        "rollout is what replaces it.",
        fr=f"Le Pod {nom} porte le volume {noms} issu du Secret, mais monté sur "
        f"{chemins} au lieu de {CHEMIN_MONTE}. Le gabarit a peut-être été corrigé "
        "après la naissance de ce Pod : c'est le Pod qui tourne qui compte, et "
        "c'est une bascule qui le remplace.",
    )


# ----------------------------------------------------------------------
# 8. Dans le conteneur, la variable porte la valeur, et elle vient du Secret.
# ----------------------------------------------------------------------
def test_dans_le_conteneur_db_password_vient_du_secret_et_vaut_la_valeur(host):
    """La valeur seule ne mesure rien : au départ, `DB_PASSWORD` porte DÉJÀ la
    bonne valeur dans le conteneur, en clair depuis le manifeste, et c'est
    précisément le défaut que le lab fait corriger. L'état demandé est donc la
    valeur ET son origine, lue sur le Pod qui tourne."""
    nom_secret, _ = _secret_requis(host)
    pod = _pod_requis(host)
    spec = _spec_du_pod_reel(host, pod)
    entrees = _entrees_de_la_variable(spec)
    assert entrees, message(
        en=f"Running Pod {pod} declares no {VARIABLE} environment variable. "
        f"Variables declared: {_variables_declarees(spec)}. The application "
        "still expects its password under that exact name.",
        fr=f"Le Pod {pod} qui tourne ne déclare aucune variable d'environnement "
        f"{VARIABLE}. Variables déclarées : {_variables_declarees(spec)}. "
        "L'application attend toujours son mot de passe sous ce nom exact.",
    )
    references = _secrets_references_par_la_variable(spec)
    assert nom_secret in references, message(
        en=f"In running Pod {pod}, {VARIABLE} does not take its value from Secret "
        f"{nom_secret!r}: {references}. Before you started, that variable ALREADY "
        "carried the right value, written in clear text in the manifest, so its "
        "value alone proves nothing. What is measured is where it comes from: "
        "valueFrom.secretKeyRef, read on the Pod that is running and not only on "
        "the template.",
        fr=f"Dans le Pod {pod} qui tourne, {VARIABLE} ne tire pas sa valeur du "
        f"Secret {nom_secret!r} : {references}. Avant que vous commenciez, cette "
        "variable portait DÉJÀ la bonne valeur, écrite en clair dans le "
        "manifeste : sa valeur seule ne prouve donc rien. Ce qui est mesuré, "
        "c'est son origine : valueFrom.secretKeyRef, lu sur le Pod qui tourne et "
        "pas seulement sur le gabarit.",
    )
    rc, variable, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec {pod} --request-timeout=30s "
        f"-- sh -c 'printf %s \"${VARIABLE}\"'",
    )
    assert rc == 0, message(
        en=f"`kubectl exec` into Pod {pod} failed, so nothing was measured about "
        f"{VARIABLE}: this is not a verdict on your manifest. {diagnostic}",
        fr=f"`kubectl exec` dans le Pod {pod} a échoué, donc rien n'a été mesuré "
        f"sur {VARIABLE} : ce n'est pas un verdict sur votre manifeste. "
        f"{diagnostic}",
    )
    assert variable == VALEUR, message(
        en=f"Inside the container, {VARIABLE} carries \"{variable or 'nothing'}\", "
        "not the expected value. The reference to the Secret is declared, but it "
        "may not point at the key that holds the password: "
        "secretKeyRef names a Secret AND a key.",
        fr=f"Dans le conteneur, {VARIABLE} porte « {variable or 'rien'} », pas la "
        "valeur attendue. La référence au Secret est déclarée, mais elle ne "
        "désigne peut-être pas la clé qui porte le mot de passe : secretKeyRef "
        "nomme un Secret ET une clé.",
    )


# ----------------------------------------------------------------------
# 9. Dans le conteneur, le fichier porte la valeur.
# ----------------------------------------------------------------------
def test_dans_le_conteneur_le_fichier_porte_la_valeur(host):
    nom_secret, cle = _secret_requis(host)
    chemin = _chemin_attendu(_spec_pod(host), nom_secret, cle)
    pod = _pod_requis(host)
    rc, contenu, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec {pod} --request-timeout=30s -- cat {shlex.quote(chemin)}",
    )
    assert rc == 0, message(
        en=f"{chemin} cannot be read in the container. A Secret mounted as a "
        "volume drops each key as a file NAMED AFTER IT, with no added "
        f"extension: key {cle!r} gives {chemin}. Check the mount point, and that "
        f"the volume does name Secret {nom_secret!r}. {diagnostic}",
        fr=f"{chemin} est illisible dans le conteneur. Un Secret monté en volume "
        "dépose chaque clé comme un fichier PORTANT SON NOM, sans extension "
        f"ajoutée : la clé {cle!r} donne {chemin}. Vérifiez le point de montage, "
        f"et que le volume désigne bien le Secret {nom_secret!r}. {diagnostic}",
    )
    assert contenu == VALEUR, message(
        en=f"{chemin} exists but carries \"{contenu or 'nothing'}\", not the "
        "expected value. A mounted file holds exactly what its key holds, so it "
        "is the content of the Secret that is to be looked at, not the mount.",
        fr=f"{chemin} existe mais porte « {contenu or 'rien'} », pas la valeur "
        "attendue. Un fichier monté porte exactement ce que porte sa clé : "
        "c'est donc le contenu du Secret qu'il faut regarder, pas le montage.",
    )
