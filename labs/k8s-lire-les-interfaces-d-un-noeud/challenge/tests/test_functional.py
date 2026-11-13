"""test_functional.py : k8s-lire-les-interfaces-d-un-noeud

Un lab de lecture se prouve par ce que l'apprenant a trouvé. Chaque test
compare une réponse de ~/interfaces/reponses.yaml à la valeur RÉELLE, relue sur
k8s-cp.lab au moment du check : le socket que déclare le kubelet, le runtime
que le nœud annonce à l'API, le premier fichier de /etc/cni/net.d et les
CSIDriver du cluster. Aucune valeur n'est écrite dans le test : une réponse
recopiée d'une documentation ne correspond pas au cluster.

Les quatre échouent sur l'état de départ : le fichier de réponses est vide.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-cp.lab"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _reponses(host) -> dict:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    fichier = host.file(f"{maison}/interfaces/reponses.yaml")
    assert fichier.exists, message(
        en="~/interfaces/reponses.yaml is missing: the setup created it, the answers go in it.",
        fr="~/interfaces/reponses.yaml est absent : le setup l'a créé, les réponses s'y écrivent.",
    )
    try:
        return yaml.safe_load(fichier.content_string) or {}
    except yaml.YAMLError as erreur:
        pytest.fail(message(en=f"reponses.yaml is not valid YAML: {erreur}",
                            fr=f"reponses.yaml n'est pas du YAML valide : {erreur}"))


def _sans_schema(socket: str) -> str:
    return socket.strip().removeprefix("unix://")


def _socket_du_kubelet(host) -> str:
    """Le socket que le kubelet emploie : son fichier de configuration
    (containerRuntimeEndpoint), sinon l'option de ligne de commande."""
    config = yaml.safe_load(host.check_output("sudo cat /var/lib/kubelet/config.yaml")) or {}
    if config.get("containerRuntimeEndpoint"):
        return config["containerRuntimeEndpoint"]
    options = host.run("sudo cat /var/lib/kubelet/kubeadm-flags.env").stdout
    for mot in options.replace('"', " ").split():
        if mot.startswith("--container-runtime-endpoint="):
            return mot.split("=", 1)[1]
    return ""


def test_le_socket_du_runtime_est_celui_du_kubelet(host):
    attendu = _socket_du_kubelet(host)
    donne = str(_reponses(host).get("runtime_socket") or "")
    assert attendu and _sans_schema(donne) == _sans_schema(attendu), message(
        en=f"runtime_socket is {donne!r}; it is not the socket the kubelet of {NOEUD} declares in its "
        "configuration.",
        fr=f"runtime_socket vaut {donne!r} ; ce n'est pas le socket que le kubelet de {NOEUD} déclare dans sa "
        "configuration.",
    )


def test_le_runtime_et_sa_version_sont_ceux_du_noeud(host):
    noeud = json.loads(host.check_output(f"{KUBECTL} get node {NOEUD} -o json"))
    attendu = noeud["status"]["nodeInfo"]["containerRuntimeVersion"]
    donne = str(_reponses(host).get("runtime") or "").strip()
    assert donne == attendu, message(
        en=f"runtime is {donne!r}; it is not the runtime and version {NOEUD} reports to the API.",
        fr=f"runtime vaut {donne!r} ; ce n'est pas le runtime et la version que {NOEUD} annonce à l'API.",
    )


def test_la_configuration_cni_est_celle_en_vigueur(host):
    # Le runtime prend le premier fichier, par ordre alphabétique, des
    # extensions qu'il reconnaît : c'est lui qui est en vigueur.
    fichiers = sorted(f for f in host.check_output("sudo ls /etc/cni/net.d").split()
                      if f.endswith((".conflist", ".conf", ".json")))
    assert fichiers, message(en=f"No CNI configuration in /etc/cni/net.d on {NOEUD}.",
                             fr=f"Aucune configuration CNI dans /etc/cni/net.d sur {NOEUD}.")
    en_vigueur = fichiers[0]
    contenu = json.loads(host.check_output(f"sudo cat /etc/cni/net.d/{en_vigueur}"))
    plugin = (contenu.get("plugins") or [contenu])[0].get("type", "")
    reponses = _reponses(host)
    donne = (str(reponses.get("cni_config") or "").strip(), str(reponses.get("cni_plugin") or "").strip())
    assert donne == (en_vigueur, plugin), message(
        en=f"cni_config and cni_plugin are {donne}; they are not the configuration file in force in "
        "/etc/cni/net.d and the type of its first plugin.",
        fr=f"cni_config et cni_plugin valent {donne} ; ce ne sont pas le fichier de configuration en vigueur "
        "dans /etc/cni/net.d et le type de son premier plugin.",
    )


def test_les_pilotes_csi_sont_ceux_du_cluster(host):
    pilotes = json.loads(host.check_output(f"{KUBECTL} get csidrivers -o json")).get("items", [])
    attendus = sorted(p["metadata"]["name"] for p in pilotes)
    donnes = _reponses(host).get("csi_drivers") or []
    donnes = sorted(str(d).strip() for d in donnes) if isinstance(donnes, list) else []
    assert donnes == attendus and attendus, message(
        en=f"csi_drivers is {donnes}; it is not exactly the list of CSI drivers registered in the cluster.",
        fr=f"csi_drivers vaut {donnes} ; ce n'est pas exactement la liste des pilotes CSI enregistrés dans "
        "le cluster.",
    )
