"""test_functional.py : cks-api-server-hardening

Deux affirmations qui lisent le manifeste du nœud et interrogent l'API server
lui-même, jamais les commandes tapées.

Le dernier test exerce les deux moitiés de la même exigence, et c'est tout
l'enjeu d'un durcissement : la porte visée doit être fermée, ET le service
doit continuer de rendre le sien. Un API server arrêté ferme le profileur
aussi sûrement qu'un flag bien posé, et c'est le contresens le plus fréquent
du domaine.
"""

from __future__ import annotations

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
MANIFESTE = "/etc/kubernetes/manifests/kube-apiserver.yaml"
FLAGS_ATTENDUS = (
    "--profiling=false",
    "--service-account-lookup=true",
    "--tls-min-version=",
)


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


# ----------------------------------------------------------------------
# 1. Les trois flags sont dans le manifeste.
# ----------------------------------------------------------------------
def test_le_manifeste_porte_les_trois_flags(host):
    """Ce test ne prouve rien à lui seul, et c'est assumé : un flag écrit dans
    un manifeste que le kubelet n'a pas repris ne change rien. Il est là pour
    que l'échec soit diagnosticable."""
    res = host.run(f"sudo cat {MANIFESTE}")
    assert res.rc == 0, message(
        en=f"Manifest {MANIFESTE} cannot be read.",
        fr=f"Le manifeste {MANIFESTE} est illisible.",
    )
    manquants = [flag for flag in FLAGS_ATTENDUS if flag not in res.stdout]
    assert not manquants, message(
        en=f"The manifest does not carry: {', '.join(manquants)}. They are added to "
        "the kube-apiserver container's `command` list, and the kubelet "
        "redeploys the Pod as soon as the file changes.",
        fr=f"Le manifeste ne porte pas : {', '.join(manquants)}. Ils s'ajoutent à "
        "la liste `command` du conteneur kube-apiserver, et le kubelet "
        "redéploie le Pod dès que le fichier change.",
    )
    assert "--anonymous-auth=false" not in res.stdout, message(
        en="The manifest carries --anonymous-auth=false. That flag was not "
        "asked for, and it breaks the cluster on this base: the probes kubeadm "
        "writes in that very manifest query /livez and /readyz WITHOUT "
        "authenticating. The kubelet sees them fail and kills the API server in "
        "a loop. A hardening that stops the service is not one.",
        fr="Le manifeste porte --anonymous-auth=false. Ce flag n'était pas "
        "demandé, et il casse le cluster sur ce socle : les sondes que kubeadm "
        "écrit dans ce même manifeste interrogent /livez et /readyz SANS "
        "s'authentifier. Le kubelet les voit échouer et tue l'API server en "
        "boucle. Un durcissement qui arrête le service n'en est pas un.",
    )


# ----------------------------------------------------------------------
# 2. LE test : le profileur est fermé, et l'API sert toujours.
# ----------------------------------------------------------------------
def test_le_profileur_est_ferme_et_l_api_sert_toujours(host):
    """Les deux moitiés dans la même mesure.

    Avant le travail, `/debug/pprof/` rend une page HTML : le profileur Go de
    l'API server est ouvert à qui sait l'atteindre, et il renseigne sur la
    mémoire, les goroutines et la charge du composant le plus sensible du
    cluster.

    Après, il doit rendre une erreur. Mais exiger seulement cela laisserait
    passer un API server à l'arrêt, qui ne répond plus à rien : on exige donc
    dans le même test que les requêtes normales aboutissent.
    """
    rc, sortie, _ = _kubectl(host, "get --raw /debug/pprof/")
    assert rc != 0, message(
        en="The profiler still answers on /debug/pprof/: it reports on the "
        "memory, the goroutines and the load of the API server. The "
        "--profiling=false flag closes it, and the kubelet must have picked up the "
        f"manifest. Output received: {sortie[:120]}",
        fr="Le profileur répond encore sur /debug/pprof/ : il renseigne sur la "
        "mémoire, les goroutines et la charge de l'API server. Le flag "
        "--profiling=false le ferme, et le kubelet doit avoir repris le "
        f"manifeste. Sortie reçue : {sortie[:120]}",
    )

    # Le Pod statique doit être REVENU, pas seulement l'API répondre : le
    # kubelet recrée le conteneur et l'état de l'objet met une seconde à
    # remonter. Cette vérification n'a pas de test à elle, « le cluster
    # répond » étant vrai AVANT le travail comme après : un test toujours vrai
    # ne mesure rien, et la validation l'a rendu ROUGE pour cette raison.
    rc, phases, _ = _kubectl(
        host,
        "-n kube-system get pods -l component=kube-apiserver "
        "-o jsonpath='{.items[*].status.phase}'",
    )
    assert rc == 0 and phases and "Pending" not in phases, message(
        en=f"The API server's static Pod is {phases or 'in an unreadable state'}. "
        "The kubelet could not restart it with the new flags.",
        fr=f"Le Pod statique de l'API server est en {phases or 'état illisible'}. "
        "Le kubelet n'a pas réussi à le redémarrer avec les nouveaux flags.",
    )

    rc, version, diagnostic = _kubectl(host, "get --raw /version")
    assert rc == 0 and "gitVersion" in version, message(
        en="The profiler is indeed closed, but the API no longer serves ordinary "
        "requests either. A stopped component closes every door: "
        f"that is not a hardening. Output: {diagnostic}",
        fr="Le profileur est bien fermé, mais l'API ne sert plus les requêtes "
        "ordinaires non plus. Un composant arrêté ferme toutes ses portes : "
        f"ce n'est pas un durcissement. Sortie : {diagnostic}",
    )
