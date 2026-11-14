"""test_functional.py : k8s-detecter-une-persistance

Lab guidé de la leçon KUBERN-S-05 (persistance). Ces tests lisent l'état du
CLUSTER et du nœud, jamais les commandes tapées. Un test vérifie un seul état,
dans l'ordre de la fiche.

Le constat se prouve par l'UID du CronJob, relevé par le setup dans un fichier
que seul root lit : un export de l'objet vivant le porte, un fichier écrit de
mémoire après la suppression ne peut pas le porter.

Le retour de l'accès se juge APRÈS la minute de planification suivante : un
compte supprimé à la main sans retirer la charge planifiée revient au plus une
minute plus tard, et un test qui regarderait tout de suite le croirait parti.

Le dernier test ne juge l'application légitime qu'une fois la persistance
retirée : avant le travail, l'application tourne, et un test vrai avant le
travail ne mesure rien.

Les cinq tests échouent sur l'état que pose le setup : aucun constat, le
CronJob rotation-journaux planifié chaque minute, support-n2 lié au ClusterRole
edit pour tout le cluster, et le Pod d'origine outil-debug en marche.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import pytest

from conftest import lab_host, lab_target_host, message

NS = "facturation"
CRONJOB = "rotation-journaux"
COMPTE = "support-n2"
POD_ORIGINE = "outil-debug"
CONSTAT = "/root/constat-persistance.yaml"
REFERENCE = "/var/lib/dsoxlab-labs/k8s-detecter-une-persistance.uid"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
SUJET = f"system:serviceaccount:{NS}:{COMPTE}"

#: Ce que l'application légitime doit garder : ses réplicas, son identité, sa
#: liaison dans le namespace et son propre CronJob, planifié la nuit.
APPLICATION = "facturation"
REPLICAS = 2
LIAISON_LEGITIME = "facturation-lecture"
CRONJOB_LEGITIME = "purge-factures"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _vivant(objet: dict | None) -> bool:
    return objet is not None and not objet["metadata"].get("deletionTimestamp")


def _liaisons_de_cluster_du_namespace(host) -> list[str]:
    """Les ClusterRoleBindings qui nomment un ServiceAccount de facturation."""
    liaisons = (_json(host, "get clusterrolebindings") or {}).get("items") or []
    return sorted(
        b["metadata"]["name"] for b in liaisons
        if any(s.get("kind") == "ServiceAccount" and s.get("namespace") == NS for s in b.get("subjects") or [])
    )


def _lit_les_secrets_du_cluster(host) -> bool:
    res = host.run(f"{ADMIN} auth can-i list secrets --all-namespaces --as {SUJET}")
    return res.stdout.strip() == "yes"


def _charge_planifiee_presente(host) -> bool:
    return _vivant(_json(host, f"-n {NS} get cronjob {CRONJOB}"))


# ----------------------------------------------------------------------
# 1. La charge planifiée est consignée, depuis l'objet vivant.
# ----------------------------------------------------------------------
def test_le_constat_nomme_l_objet_de_persistance(host):
    reference = host.run(f"sudo cat {REFERENCE}").stdout.strip()
    assert reference, message(
        en=f"The reference {REFERENCE} that the setup writes is missing: replay `dsoxlab run`.",
        fr=f"La référence {REFERENCE} que pose le setup est absente : rejouez `dsoxlab run`.",
    )
    res = host.run(f"sudo cat {CONSTAT}")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"No record in {CONSTAT}. Before deleting anything, the object that recreates the access is "
        "exported there: once deleted, nothing in the cluster tells what it did any more.",
        fr=f"Aucun constat dans {CONSTAT}. Avant de supprimer quoi que ce soit, l'objet qui recrée l'accès y "
        "est exporté : une fois supprimé, plus rien dans le cluster ne dit ce qu'il faisait.",
    )
    contenu = res.stdout
    manque = [m for m in ("CronJob", CRONJOB) if m not in contenu]
    assert not manque, message(
        en=f"{CONSTAT} does not name the object that recreates the access (missing: {manque}). Look at what "
        f"is scheduled in {NS}, and at what it runs.",
        fr=f"{CONSTAT} ne nomme pas l'objet qui recrée l'accès (manque : {manque}). Regardez ce qui est "
        f"planifié dans {NS}, et ce que cela exécute.",
    )
    assert reference in contenu, message(
        en=f"{CONSTAT} names {CRONJOB} but does not carry the UID of the live object: it was not exported "
        "from the cluster before the deletion. A record is the object itself, in full, as the cluster "
        "returns it.",
        fr=f"{CONSTAT} nomme {CRONJOB} mais ne porte pas l'UID de l'objet vivant : il n'a pas été exporté du "
        "cluster avant la suppression. Un constat, c'est l'objet lui-même, complet, tel que le cluster le rend.",
    )


# ----------------------------------------------------------------------
# 2. La charge planifiée est supprimée, avec ses Jobs et leurs Pods.
# ----------------------------------------------------------------------
def test_la_charge_planifiee_est_supprimee(host):
    assert not _charge_planifiee_presente(host), message(
        en=f"The CronJob {CRONJOB} is still in {NS}: every minute, it recreates {COMPTE} and its binding.",
        fr=f"Le CronJob {CRONJOB} est toujours dans {NS} : chaque minute, il recrée {COMPTE} et sa liaison.",
    )
    jobs = (_json(host, f"-n {NS} get jobs") or {}).get("items") or []
    restes = [
        j["metadata"]["name"] for j in jobs
        if _vivant(j) and any(o.get("kind") == "CronJob" and o.get("name") == CRONJOB
                              for o in j["metadata"].get("ownerReferences") or [])
    ]
    pods = (_json(host, f"-n {NS} get pods") or {}).get("items") or []
    restes += [
        p["metadata"]["name"] for p in pods
        if _vivant(p) and (p["metadata"].get("labels") or {}).get("job-name", "").startswith(f"{CRONJOB}-")
    ]
    assert not restes, message(
        en=f"The CronJob is gone but its Jobs or Pods remain: {restes}. A run in progress can still recreate "
        "the access.",
        fr=f"Le CronJob a disparu mais ses Jobs ou ses Pods restent : {restes}. Un passage en cours peut encore "
        "recréer l'accès.",
    )


# ----------------------------------------------------------------------
# 3. L'accès de l'attaquant est retiré.
# ----------------------------------------------------------------------
def test_l_acces_de_l_attaquant_est_retire(host):
    comptes = [c for c in (COMPTE, CRONJOB) if _vivant(_json(host, f"-n {NS} get serviceaccount {c}"))]
    liaisons = _liaisons_de_cluster_du_namespace(host)
    assert not comptes and not liaisons, message(
        en=f"The attacker's identities or their cluster-wide bindings remain: accounts {comptes}, "
        f"ClusterRoleBindings {liaisons}. No account of {NS} needs a right on the whole cluster.",
        fr=f"Les identités de l'attaquant ou leurs liaisons à l'échelle du cluster restent : comptes {comptes}, "
        f"ClusterRoleBindings {liaisons}. Aucun compte de {NS} n'a besoin d'un droit sur tout le cluster.",
    )
    assert not _lit_les_secrets_du_cluster(host), message(
        en=f"{SUJET} can still list the Secrets of every namespace. RBAC grants a name, not an object: as "
        "long as a binding names this account, recreating it gives the access back.",
        fr=f"{SUJET} peut encore lister les Secrets de tous les namespaces. RBAC accorde un nom, pas un objet : "
        "tant qu'une liaison nomme ce compte, le recréer rend l'accès.",
    )


# ----------------------------------------------------------------------
# 4. Le Pod d'origine supprimé, l'accès ne revient pas.
# ----------------------------------------------------------------------
def test_l_acces_ne_revient_pas(host):
    assert not _vivant(_json(host, f"-n {NS} get pod {POD_ORIGINE}")), message(
        en=f"The original Pod {POD_ORIGINE} still runs in {NS}, under the stolen account: it is the "
        "attacker's way in, it goes too.",
        fr=f"Le Pod d'origine {POD_ORIGINE} tourne toujours dans {NS}, sous le compte volé : c'est la porte "
        "d'entrée de l'attaquant, il part aussi.",
    )
    assert not _charge_planifiee_presente(host), message(
        en=f"The CronJob {CRONJOB} still exists: the access comes back at its next run.",
        fr=f"Le CronJob {CRONJOB} existe toujours : l'accès revient à son prochain passage.",
    )
    assert not _vivant(_json(host, f"-n {NS} get serviceaccount {COMPTE}")), message(
        en=f"The account {COMPTE} is there: the access has not even been removed yet.",
        fr=f"Le compte {COMPTE} est là : l'accès n'a même pas encore été retiré.",
    )
    # La minute de planification suivante, plus le temps qu'un Job démarre et
    # appelle l'API : c'est là qu'un mécanisme oublié recréerait l'accès.
    time.sleep(60 - datetime.now(UTC).second + 25)
    revenu = []
    if _vivant(_json(host, f"-n {NS} get serviceaccount {COMPTE}")):
        revenu.append(message(en=f"the account {COMPTE}", fr=f"le compte {COMPTE}"))
    if liaisons := _liaisons_de_cluster_du_namespace(host):
        revenu.append(message(en=f"the ClusterRoleBindings {liaisons}", fr=f"les ClusterRoleBindings {liaisons}"))
    if _lit_les_secrets_du_cluster(host):
        revenu.append(message(en="reading the Secrets of the cluster", fr="la lecture des Secrets du cluster"))
    assert not revenu, message(
        en=f"After the next minute of scheduling, the access came back: {revenu}. Something still recreates "
        "it: look again at what is scheduled, and at the events of the namespace.",
        fr=f"Après la minute de planification suivante, l'accès est revenu : {revenu}. Quelque chose le recrée "
        "encore : regardez de nouveau ce qui est planifié, et les événements du namespace.",
    )


# ----------------------------------------------------------------------
# 5. L'application légitime est intacte.
# ----------------------------------------------------------------------
def test_l_application_legitime_est_intacte(host):
    assert not _charge_planifiee_presente(host) and not _vivant(
        _json(host, f"-n {NS} get serviceaccount {COMPTE}")), message(
        en="The persistence is not removed yet: the legitimate application is judged once it is.",
        fr="La persistance n'est pas encore retirée : l'application légitime se juge une fois qu'elle l'est.",
    )
    ecarts = []
    dep = _json(host, f"-n {NS} get deployment {APPLICATION}")
    if dep is None:
        ecarts.append(message(en=f"the Deployment {APPLICATION} is gone", fr=f"le Deployment {APPLICATION} a disparu"))
    else:
        prets = (dep.get("status") or {}).get("availableReplicas") or 0
        if dep["spec"].get("replicas") != REPLICAS or prets != REPLICAS:
            ecarts.append(message(
                en=f"{APPLICATION} has {prets} available replica(s) out of {dep['spec'].get('replicas')}, "
                f"{REPLICAS} expected",
                fr=f"{APPLICATION} a {prets} réplica(s) disponible(s) sur {dep['spec'].get('replicas')}, "
                f"{REPLICAS} attendus"))
        if dep["spec"]["template"]["spec"].get("serviceAccountName") != APPLICATION:
            ecarts.append(message(en=f"{APPLICATION} no longer runs under its own identity",
                                  fr=f"{APPLICATION} ne tourne plus sous sa propre identité"))
    if not _vivant(_json(host, f"-n {NS} get serviceaccount {APPLICATION}")):
        ecarts.append(message(en=f"its account {APPLICATION} is gone", fr=f"son compte {APPLICATION} a disparu"))
    if _json(host, f"-n {NS} get rolebinding {LIAISON_LEGITIME}") is None:
        ecarts.append(message(en=f"its RoleBinding {LIAISON_LEGITIME} is gone",
                              fr=f"son RoleBinding {LIAISON_LEGITIME} a disparu"))
    if _json(host, f"-n {NS} get cronjob {CRONJOB_LEGITIME}") is None:
        ecarts.append(message(en=f"its own CronJob {CRONJOB_LEGITIME} is gone",
                              fr=f"son propre CronJob {CRONJOB_LEGITIME} a disparu"))
    svc = _json(host, f"-n {NS} get service {APPLICATION}")
    ip = (svc or {}).get("spec", {}).get("clusterIP")
    code = host.run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 http://{ip}/").stdout.strip() \
        if ip else ""
    if code != "200":
        ecarts.append(message(en=f"its Service does not answer (HTTP {code or 'none'})",
                              fr=f"son Service ne répond pas (HTTP {code or 'aucun'})"))
    assert not ecarts, message(
        en=f"The legitimate application of {NS} was damaged: {ecarts}. Removing a persistence means removing "
        "the attacker's objects, one by one, not the namespace or everything that looks scheduled.",
        fr=f"L'application légitime de {NS} a été abîmée : {ecarts}. Retirer une persistance, c'est retirer les "
        "objets de l'attaquant, un par un, pas le namespace ni tout ce qui ressemble à une planification.",
    )
