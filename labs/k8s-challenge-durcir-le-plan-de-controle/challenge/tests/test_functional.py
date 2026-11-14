"""test_functional.py : k8s-challenge-durcir-le-plan-de-controle

Le challenge du module Durcir le cluster. Ces tests lisent le NŒUD et le
cluster, jamais les commandes tapées. Un test vérifie un seul état, dans
l'ordre de la fiche.

Ils reprennent les mesures attestées de trois labs guidés :
cks-api-server-hardening (états 1 et 2), cks-cis-benchmark-remediate
(états 3 et 4) et cks-audit-log-policy (états 5 à 7). Deux différences :

- le compte d'échecs CIS de départ n'est plus écrit en dur. Le setup a relancé
  kube-bench sur le plan de contrôle restauré et rangé son total sur le nœud ;
  l'état 4 compare à ce total, mesuré sur ce cluster ;
- l'état 6 lit le manifeste comme un objet, et non comme du texte : le chemin
  de la politique figure déjà dans le flag, sa seule présence ne dit pas que le
  fichier est monté dans le conteneur.

Les sept tests échouent sur l'état que pose le setup : manifestes d'origine,
profileur ouvert, aucune politique ni journal d'audit.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
MANIFESTES = "/etc/kubernetes/manifests"
MANIFESTE_API = f"{MANIFESTES}/kube-apiserver.yaml"
COMPOSANTS = ("kube-apiserver", "kube-controller-manager", "kube-scheduler")
NAMESPACE = "conformite"
SECRET = "jeton-de-paiement"  # noqa: S105 - nom d'un Secret, pas un mot de passe
POLITIQUE = "/etc/kubernetes/audit-policy.yaml"
JOURNAL = "/var/log/kubernetes/audit.log"
DEPART = "/var/lib/dsoxlab/k8s-challenge-durcir-le-plan-de-controle/echecs-au-depart"
#: Les trois contrôles que le référentiel CIS reproche au plan de contrôle par
#: défaut, et qui partagent une même cause.
CONTROLES_VISES = ("1.2.15", "1.3.2", "1.4.1")
FLAGS_DE_DURCISSEMENT = (
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


def _lire(host, chemin: str) -> str:
    res = host.run(f"sudo cat {chemin}")
    assert res.rc == 0, message(
        en=f"{chemin} cannot be read on the node.",
        fr=f"{chemin} est illisible sur le nœud.",
    )
    return res.stdout


def _commande_api(host) -> list[str]:
    """La ligne de commande du conteneur kube-apiserver, lue dans le manifeste."""
    manifeste = yaml.safe_load(_lire(host, MANIFESTE_API)) or {}
    conteneurs = (manifeste.get("spec") or {}).get("containers") or [{}]
    return [str(a) for a in (conteneurs[0].get("command") or []) + (conteneurs[0].get("args") or [])]


def _attendre_le_plan_de_controle(host) -> None:
    """Attend que les Pods statiques soient revenus, sans en faire un test.

    « Le plan de contrôle répond » est vrai avant le travail comme après : un
    test toujours vrai ne mesure rien. Mais une mesure prise pendant qu'un Pod
    statique redémarre rendrait rouge un travail juste (mesuré le 2026-09-16
    sur le lab guidé : « Running Running Running Pending »).
    """
    phases = ""
    rc = 1
    for _ in range(40):
        rc, phases, _ = _kubectl(
            host,
            "-n kube-system get pods -l tier=control-plane "
            "-o jsonpath='{.items[*].status.phase}'",
        )
        if rc == 0 and phases and "Pending" not in phases:
            return
        host.run("sleep 3")
    assert rc == 0 and phases and "Pending" not in phases, message(
        en=f"A control plane Pod stays {phases or 'in an unreadable state'} after two "
        "minutes. The kubelet could not restart it with the new settings: "
        "`sudo crictl ps -a` then `sudo crictl logs <id>` give the reason.",
        fr=f"Un Pod du plan de contrôle reste en {phases or 'état illisible'} après deux "
        "minutes. Le kubelet n'a pas réussi à le redémarrer avec les nouveaux "
        "réglages : `sudo crictl ps -a` puis `sudo crictl logs <id>` donnent la raison.",
    )


# ----------------------------------------------------------------------
# 1. Le manifeste de l'API server porte les réglages de durcissement.
# ----------------------------------------------------------------------
def test_l_api_server_porte_les_reglages_de_durcissement(host):
    commande = _commande_api(host)
    manquants = [f for f in FLAGS_DE_DURCISSEMENT if not any(a.startswith(f) for a in commande)]
    assert not manquants, message(
        en=f"The API server manifest does not carry: {', '.join(manquants)}. "
        "The specification asks for the profiler off, the check that a "
        "presented token still exists, and a TLS floor.",
        fr=f"Le manifeste de l'API server ne porte pas : {', '.join(manquants)}. "
        "Le cahier des charges demande le profileur coupé, la vérification qu'un "
        "jeton présenté existe toujours, et un plancher TLS.",
    )
    assert "--anonymous-auth=false" not in commande, message(
        en="The manifest carries --anonymous-auth=false. It was not asked for, "
        "and it breaks this cluster: the probes kubeadm writes in that very "
        "manifest query /livez and /readyz without authenticating, and the "
        "kubelet then kills the API server in a loop.",
        fr="Le manifeste porte --anonymous-auth=false. Ce n'était pas demandé, et "
        "il casse ce cluster : les sondes que kubeadm écrit dans ce même "
        "manifeste interrogent /livez et /readyz sans s'authentifier, et le "
        "kubelet tue alors l'API server en boucle.",
    )


# ----------------------------------------------------------------------
# 2. Le profileur est fermé, et l'API répond toujours.
# ----------------------------------------------------------------------
def test_le_profileur_est_ferme_et_l_api_repond_toujours(host):
    """Les deux moitiés dans la même mesure : un API server arrêté ferme le
    profileur aussi sûrement qu'un flag bien posé."""
    rc, sortie, _ = _kubectl(host, "get --raw /debug/pprof/")
    assert rc != 0, message(
        en="The profiler still answers on /debug/pprof/: it tells anyone who "
        "reaches it about the memory, the goroutines and the load of the API "
        f"server. Output received: {sortie[:120]}",
        fr="Le profileur répond encore sur /debug/pprof/ : il renseigne qui "
        "l'atteint sur la mémoire, les goroutines et la charge de l'API server. "
        f"Sortie reçue : {sortie[:120]}",
    )
    _attendre_le_plan_de_controle(host)
    rc, version, diagnostic = _kubectl(host, "get --raw /version")
    assert rc == 0 and "gitVersion" in version, message(
        en="The profiler is closed, but the API no longer serves ordinary "
        "requests either. A stopped component closes every door: that is not "
        f"a hardening. Output: {diagnostic}",
        fr="Le profileur est fermé, mais l'API ne sert plus les requêtes "
        "ordinaires non plus. Un composant arrêté ferme toutes ses portes : ce "
        f"n'est pas un durcissement. Sortie : {diagnostic}",
    )


# ----------------------------------------------------------------------
# 3. Les trois composants portent la correction de l'écart CIS.
# ----------------------------------------------------------------------
def test_les_trois_composants_portent_la_correction_cis(host):
    """Le référentiel reproche le même réglage à trois composants. En corriger
    un seul laisse deux portes ouvertes."""
    manquants = []
    for composant in COMPOSANTS:
        res = host.run(f"sudo cat {MANIFESTES}/{composant}.yaml")
        if res.rc != 0:
            manquants.append(f"{composant} (manifeste illisible)")
            continue
        conteneurs = ((yaml.safe_load(res.stdout) or {}).get("spec") or {}).get("containers") or [{}]
        commande = [str(a) for a in (conteneurs[0].get("command") or []) + (conteneurs[0].get("args") or [])]
        if "--profiling=false" not in commande:
            manquants.append(composant)
    assert not manquants, message(
        en=f"These components do not carry the fix: {', '.join(manquants)}. The "
        "CIS benchmark holds the same setting against all three, under three "
        "different numbers.",
        fr=f"Ces composants ne portent pas la correction : {', '.join(manquants)}. "
        "Le référentiel CIS reproche le même réglage aux trois, sous trois "
        "numéros différents.",
    )


# ----------------------------------------------------------------------
# 4. kube-bench relancé compte moins d'échecs, et les trois contrôles passent.
# ----------------------------------------------------------------------
def _audit_cis(host) -> dict:
    """Relance kube-bench et rend son rapport, décodé.

    L'audit est REJOUÉ ici : un rapport s'édite, un audit qui tourne sous nos
    yeux ne s'édite pas.
    """
    _kubectl(host, f"-n {NAMESPACE} delete job kube-bench --ignore-not-found "
             "--cascade=foreground --wait=true")
    rc, _, diagnostic = _kubectl(host, "apply -f /root/kube-bench-job.yaml")
    assert rc == 0, message(
        en=f"The kube-bench Job could not be created. {diagnostic}",
        fr=f"Le Job kube-bench n'a pas pu être créé. {diagnostic}",
    )
    rc, _, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} wait --for=condition=complete job/kube-bench --timeout=180s"
    )
    assert rc == 0, message(
        en=f"The kube-bench audit did not finish. {diagnostic}",
        fr=f"L'audit kube-bench ne s'est pas terminé. {diagnostic}",
    )
    rc, pod, _ = _kubectl(
        host, f"-n {NAMESPACE} get pods -l job-name=kube-bench "
        "-o jsonpath='{.items[0].metadata.name}'"
    )
    assert rc == 0 and pod, message(
        en="The audit's Pod cannot be found.",
        fr="Le Pod de l'audit est introuvable.",
    )
    rc, journal, diagnostic = _kubectl(host, f"-n {NAMESPACE} logs {pod}")
    debut = journal.find("{")
    assert rc == 0 and debut >= 0, message(
        en=f"kube-bench's output contains no JSON. {diagnostic}",
        fr=f"La sortie de kube-bench ne contient pas de JSON. {diagnostic}",
    )
    return json.loads(journal[debut:])


def test_kube_bench_relance_compte_moins_d_echecs(host):
    res = host.run(f"sudo cat {DEPART}")
    depart = res.stdout.strip()
    assert res.rc == 0 and depart.isdigit(), message(
        en=f"The starting failure count, measured by setup, is missing from {DEPART}. "
        "Run `dsoxlab reset` on this challenge: setup measures it again.",
        fr=f"Le compte d'échecs de départ, mesuré par le setup, manque en {DEPART}. "
        "Jouez `dsoxlab reset` sur ce challenge : le setup le remesure.",
    )
    _attendre_le_plan_de_controle(host)
    rapport = _audit_cis(host)

    etats = {
        str(r.get("test_number")): str(r.get("status"))
        for c in rapport.get("Controls", [])
        for g in c.get("tests", [])
        for r in g.get("results", [])
    }
    encore = [c for c in CONTROLES_VISES if etats.get(c) != "PASS"]
    assert not encore, message(
        en="These CIS checks still fail after the audit was run again: "
        + ", ".join(f"{c} ({etats.get(c, 'absent from the report')})" for c in encore)
        + ". Each check carries a remediation section in the report: read it.",
        fr="Ces contrôles CIS échouent toujours après l'audit relancé : "
        + ", ".join(f"{c} ({etats.get(c, 'absent du rapport')})" for c in encore)
        + ". Chaque contrôle porte une section remediation dans le rapport : lisez-la.",
    )
    total = sum(int(c.get("total_fail", 0)) for c in rapport.get("Controls", []))
    assert total < int(depart), message(
        en=f"The audit still counts {total} failure(s), against {depart} at the start. "
        "Fixing one check by breaking another does not bring the count down, and "
        "that is what this global measurement catches.",
        fr=f"L'audit compte encore {total} échec(s), contre {depart} au départ. "
        "Corriger un contrôle en cassant un autre ne fait pas baisser le compte, et "
        "c'est ce que cette mesure globale attrape.",
    )


# ----------------------------------------------------------------------
# 5. La politique d'audit distingue les Secrets du reste.
# ----------------------------------------------------------------------
def test_la_politique_d_audit_distingue_les_secrets_du_reste(host):
    res = host.run(f"sudo cat {POLITIQUE}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No readable audit policy at {POLITIQUE}. It is not a cluster object: "
        "it is a file on the node, which the API server reads at startup.",
        fr=f"Aucune politique d'audit lisible en {POLITIQUE}. Ce n'est pas un objet "
        "du cluster : c'est un fichier du nœud, que l'API server lit au démarrage.",
    )
    contenu = res.stdout
    assert "RequestResponse" in contenu and "secrets" in contenu, message(
        en="The policy does not record Secrets at the RequestResponse level, the "
        "only one that keeps the body of the request and of the response.",
        fr="La politique n'enregistre pas les Secrets au niveau RequestResponse, le "
        "seul qui garde le corps de la requête et de la réponse.",
    )
    assert "Metadata" in contenu, message(
        en="The policy carries no Metadata level for the rest. Auditing everything "
        "at RequestResponse copies every body into the log and fills the disk.",
        fr="La politique ne porte pas de niveau Metadata pour le reste. Tout auditer "
        "en RequestResponse recopie chaque corps dans le journal et sature le disque.",
    )


# ----------------------------------------------------------------------
# 6. L'API server tourne avec l'audit, politique et journal montés.
# ----------------------------------------------------------------------
def test_l_api_server_tourne_avec_l_audit_monte(host):
    """Des flags sans volumes donnent un conteneur qui boucle : l'API server est
    un Pod, il ne voit du nœud que ce qu'on lui monte."""
    manifeste = yaml.safe_load(_lire(host, MANIFESTE_API)) or {}
    spec = manifeste.get("spec") or {}
    conteneur = (spec.get("containers") or [{}])[0]
    commande = [str(a) for a in (conteneur.get("command") or []) + (conteneur.get("args") or [])]

    attendus = (f"--audit-policy-file={POLITIQUE}", f"--audit-log-path={JOURNAL}")
    manquants = [a for a in attendus if a not in commande]
    assert not manquants, message(
        en=f"The kube-apiserver command does not carry: {', '.join(manquants)}.",
        fr=f"La commande de kube-apiserver ne porte pas : {', '.join(manquants)}.",
    )

    volumes = {
        v.get("name"): (v.get("hostPath") or {}).get("path", "")
        for v in spec.get("volumes") or []
    }
    montes = {
        m.get("mountPath", ""): volumes.get(m.get("name"), "")
        for m in conteneur.get("volumeMounts") or []
    }

    def _visible(chemin: str) -> bool:
        """Le chemin est-il atteint par un montage hostPath du même chemin ?"""
        return any(
            hote and (chemin == point or chemin.startswith(point.rstrip("/") + "/"))
            and (hote.rstrip("/") == point.rstrip("/"))
            for point, hote in montes.items()
        )

    absents = [c for c in (POLITIQUE, JOURNAL) if not _visible(c)]
    assert not absents, message(
        en=f"The container does not see {', '.join(absents)} from the node. Each "
        "path given in a flag needs a hostPath volume and its volumeMount, at "
        "the same path.",
        fr=f"Le conteneur ne voit pas {', '.join(absents)} depuis le nœud. Chaque "
        "chemin donné dans un flag demande un volume hostPath et son volumeMount, "
        "au même chemin.",
    )

    _attendre_le_plan_de_controle(host)
    rc, _, diagnostic = _kubectl(host, "get --raw /healthz")
    assert rc == 0, message(
        en="The API server no longer answers with the audit on. `sudo crictl logs` "
        f"on the kube-apiserver container says why in one line. Output: {diagnostic}",
        fr="L'API server ne répond plus avec l'audit. `sudo crictl logs` sur le "
        f"conteneur kube-apiserver dit pourquoi en une ligne. Sortie : {diagnostic}",
    )


# ----------------------------------------------------------------------
# 7. Le journal trace les Secrets en entier, le reste en métadonnées.
# ----------------------------------------------------------------------
def _lignes_d_audit(host, motif: str, depuis: int = 600) -> list[dict]:
    """Les dernières lignes du journal qui portent ce motif, décodées."""
    res = host.run(f"sudo tail -n {depuis} {JOURNAL} 2>/dev/null | grep -F '{motif}' || true")
    lignes = []
    for brute in res.stdout.splitlines():
        try:
            lignes.append(json.loads(brute))
        except json.JSONDecodeError:
            continue
    return lignes


def test_le_journal_trace_les_secrets_en_entier_et_le_reste_en_metadonnees(host):
    """Le test provoque deux lectures réelles, une sensible et une banale, puis
    relit ce que l'audit vient d'en écrire. Une politique qui enregistrerait
    tout au niveau maximum échoue sur la seconde moitié, et c'est voulu."""
    rc, _, diagnostic = _kubectl(host, f"-n {NAMESPACE} get secret {SECRET}")
    assert rc == 0, message(
        en=f"Secret {SECRET} from setup cannot be found. {diagnostic}",
        fr=f"Le Secret {SECRET} du setup est introuvable. {diagnostic}",
    )
    _kubectl(host, f"-n {NAMESPACE} get pods")
    host.run("sleep 5")

    res = host.run(f"sudo test -s {JOURNAL}")
    assert res.rc == 0, message(
        en=f"Log {JOURNAL} is empty or absent although requests have just been "
        "made. The API server writes nothing there.",
        fr=f"Le journal {JOURNAL} est vide ou absent alors que des requêtes viennent "
        "d'être faites. L'API server n'y écrit rien.",
    )

    secrets = [
        ligne for ligne in _lignes_d_audit(host, f'"name":"{SECRET}"')
        if (ligne.get("objectRef") or {}).get("resource") == "secrets"
    ]
    niveaux = {ligne.get("level") for ligne in secrets}
    assert "RequestResponse" in niveaux, message(
        en=f"The read of Secret {SECRET} is recorded at level(s) {niveaux or 'none'}, "
        "not at RequestResponse. The API server keeps the FIRST rule that "
        "matches: a catch-all rule placed before the one for Secrets wins.",
        fr=f"La lecture du Secret {SECRET} est enregistrée au(x) niveau(x) "
        f"{niveaux or 'aucun'}, pas en RequestResponse. L'API server retient la "
        "PREMIÈRE règle qui correspond : une règle attrape-tout placée avant celle "
        "des Secrets l'emporte.",
    )

    banales = [
        ligne for ligne in _lignes_d_audit(host, '"resource":"pods"')
        if (ligne.get("objectRef") or {}).get("resource") == "pods"
    ]
    assert banales, message(
        en="No trace of the Pod reads: the catch-all rule at Metadata is missing.",
        fr="Aucune trace des lectures de Pods : la règle attrape-tout en Metadata manque.",
    )
    bavardes = {ligne.get("level") for ligne in banales if ligne.get("level") != "Metadata"}
    assert not bavardes, message(
        en=f"Ordinary requests are recorded at level(s) {bavardes} instead of Metadata.",
        fr=f"Des requêtes banales sont enregistrées au(x) niveau(x) {bavardes} au lieu de Metadata.",
    )
