"""test_functional.py : ckad-secret-injection-protection

Deux affirmations qui lisent l'état réel du cluster et l'intérieur du
conteneur, jamais les commandes tapées.

Le dernier test exerce LES DEUX CÔTÉS : la valeur a quitté le manifeste, et
elle arrive quand même dans le conteneur, par les deux chemins demandés.
Séparées, ces deux moitiés ne mesureraient rien de bon. « La valeur n'est plus
dans le manifeste » serait vert si le candidat l'avait simplement supprimée, en
cassant l'application ; « le conteneur voit la valeur » est vrai AVANT le
travail, puisque le manifeste la lui donne en clair.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "paiement"
DEPLOYMENT = "passerelle"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
VALEUR = "Tr3s0r-2026"
CHEMIN_MONTE = "/etc/passerelle"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _un_pod(host) -> str:
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} get pod -l app={DEPLOYMENT} "
        "--field-selector=status.phase=Running "
        "-o jsonpath='{.items[0].metadata.name}'",
    )
    assert rc == 0 and sortie, message(
        en=f"No Pod of {DEPLOYMENT} is running in {NAMESPACE}. A Pod that "
        "references a missing Secret, or a key that does not exist in that "
        "Secret, does not start: it stays in CreateContainerConfigError, and "
        "`kubectl describe pod` names the missing key in its events. "
        f"{diagnostic}",
        fr=f"Aucun Pod de {DEPLOYMENT} ne tourne dans {NAMESPACE}. Un Pod qui "
        "référence un Secret absent, ou une clé qui n'existe pas dans ce "
        "Secret, ne démarre pas : il reste en CreateContainerConfigError, et "
        "`kubectl describe pod` nomme la clé manquante dans ses events. "
        f"{diagnostic}",
    )
    return sortie


# ----------------------------------------------------------------------
# 1. Un Secret porte la valeur, et le Deployment le référence.
# ----------------------------------------------------------------------
def test_un_secret_porte_la_valeur_et_le_deployment_le_reference(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable, et pour nommer celui des deux
    chemins d'injection qui manque."""
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get secret -o json")
    assert rc == 0, message(
        en=f"Cannot read the Secrets of {NAMESPACE}. {diagnostic}",
        fr=f"Impossible de lire les Secrets de {NAMESPACE}. {diagnostic}",
    )

    secrets = [
        s for s in json.loads(sortie).get("items", [])
        if s.get("type") == "Opaque"
    ]
    assert secrets, message(
        en=f"No application Secret in {NAMESPACE}. That is the object in which "
        "a sensitive value stops living in the middle of the application's "
        "manifest.",
        fr=f"Aucun Secret applicatif dans {NAMESPACE}. C'est l'objet dans lequel "
        "une valeur sensible cesse de vivre au milieu du manifeste de "
        "l'application.",
    )

    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json"
    )
    assert rc == 0 and sortie, message(
        en=f"Deployment {DEPLOYMENT} cannot be found. Setup had placed it there: "
        f"it must be MODIFIED, not replaced. {diagnostic}",
        fr=f"Le Deployment {DEPLOYMENT} est introuvable. Le setup l'avait posé : "
        f"il doit être MODIFIÉ, pas remplacé. {diagnostic}",
    )
    spec = json.loads(sortie)["spec"]["template"]["spec"]
    conteneurs = spec.get("containers", [])
    assert conteneurs, message(
        en="The Deployment declares no container.",
        fr="Le Deployment ne déclare aucun conteneur.",
    )

    par_variable = any(
        (v.get("valueFrom") or {}).get("secretKeyRef")
        for c in conteneurs for v in c.get("env", [])
    )
    par_volume = any(v.get("secret") for v in spec.get("volumes", []))
    manques = []
    if not par_variable:
        manques.append(
            "aucune variable d'environnement ne tire sa valeur d'un Secret"
        )
    if not par_volume:
        manques.append("aucun volume ne provient d'un Secret")
    assert not manques, message(
        en="The injection is incomplete: " + ", and ".join(manques) + ". Both "
        "paths were asked for, and they are not equivalent: a variable is "
        "frozen for the life of the process, whereas a mounted file is "
        "refreshed when the Secret changes.",
        fr="L'injection est incomplète : " + ", et ".join(manques) + ". Les deux "
        "chemins étaient demandés, et ils ne se valent pas : une variable est "
        "figée pour la vie du processus, tandis qu'un fichier monté est "
        "rafraîchi quand le Secret change.",
    )


# ----------------------------------------------------------------------
# 2. LE test : la valeur a quitté le manifeste, et arrive quand même.
# ----------------------------------------------------------------------
def test_la_valeur_a_quitte_le_manifeste_et_arrive_quand_meme(host):
    """La preuve, prise des deux côtés.

    Mesuré le 2026-09-17 : avant le travail, `kubectl get deployment -o yaml`
    rend la valeur en clair au milieu du manifeste.
    """
    rc, manifeste, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o yaml"
    )
    assert rc == 0 and manifeste, message(
        en=f"Cannot read Deployment {DEPLOYMENT}. {diagnostic}",
        fr=f"Impossible de lire le Deployment {DEPLOYMENT}. {diagnostic}",
    )
    assert VALEUR not in manifeste, message(
        en=f"The password still appears in clear text in the manifest of "
        f"{DEPLOYMENT}. That is precisely what had to stop: this "
        "manifest is versioned, reviewed and copied, and anything that can read it "
        "can read the value. Moving it into a Secret does not encrypt it, "
        "but it stops sitting in the middle of the application's "
        "configuration.",
        fr=f"Le mot de passe apparaît encore en clair dans le manifeste de "
        f"{DEPLOYMENT}. C'est précisément ce qu'il fallait faire cesser : ce "
        "manifeste est versionné, relu et copié, et tout ce qui peut le lire "
        "peut lire la valeur. La déplacer dans un Secret ne la chiffre pas, "
        "mais elle cesse d'être au milieu de la configuration de "
        "l'application.",
    )

    pod = _un_pod(host)
    rc, variable, _ = _kubectl(
        host,
        f"-n {NAMESPACE} exec {pod} --request-timeout=30s "
        "-- sh -c 'printf %s \"$DB_PASSWORD\"'",
    )
    assert rc == 0 and variable == VALEUR, message(
        en=f"Variable DB_PASSWORD is \"{variable or 'nothing'}\" in the "
        f"container, instead of the expected value. Taking the value out of the "
        "manifest was to change nothing FOR THE APPLICATION: it still expects "
        "its password under that variable name.",
        fr=f"La variable DB_PASSWORD vaut « {variable or 'rien'} » dans le "
        f"conteneur, au lieu de la valeur attendue. Sortir la valeur du "
        "manifeste ne devait rien changer POUR L'APPLICATION : elle attend "
        "toujours son mot de passe sous ce nom de variable.",
    )

    rc, fichier, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec {pod} --request-timeout=30s "
        f"-- sh -c 'cat {CHEMIN_MONTE}/*'",
    )
    assert rc == 0 and fichier.strip() == VALEUR, message(
        en=f"No file in {CHEMIN_MONTE} contains the value: \""
        f"{fichier or diagnostic or 'nothing'}\". A Secret mounted as a volume "
        "drops each key as a file NAMED AFTER IT, with no added "
        "extension. Check the mount point, and that the volume does name "
        "the Secret.",
        fr=f"Aucun fichier de {CHEMIN_MONTE} ne contient la valeur : « "
        f"{fichier or diagnostic or 'rien'} ». Un Secret monté en volume "
        "dépose chaque clé comme un fichier PORTANT SON NOM, sans extension "
        "ajoutée. Vérifiez le point de montage, et que le volume désigne bien "
        "le Secret.",
    )
