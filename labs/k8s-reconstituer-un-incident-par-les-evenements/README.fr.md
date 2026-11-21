# Reconstituer un incident à partir des Events d'un namespace

La leçon montre les Events : les messages que les composants du cluster
laissent sur les objets. Ce cours vous fait reconstituer une suite de pannes
à partir d'eux, et ajoute des cas que la leçon ne montre pas : les
événements d'un seul objet, un événement répété qui ne se duplique pas, le
tri qui dit qui a été touché en premier, la durée de conservation des
événements, et les événements d'un Deployment.

Vous travaillez dans un namespace d'essai, `essai-journal`, avec trois Pods
en panne : `introuvable`, `impatient` et `grossiste`. Le challenge porte sur
un autre namespace : vous le ferez seul, à la fin.

Page associée : [Analyser les événements Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/analyser-evenements-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-reconstituer-un-incident-par-les-evenements
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez trois pannes, à quelques secondes d'écart : une image qui n'existe pas
(`introuvable`), un conteneur qui sort en erreur (`impatient`), et un Pod qui
demande 64 CPU (`grossiste`). La commande attend ensuite 40 secondes :

```bash
kubectl create namespace essai-journal; kubectl run introuvable --image=registry.invalid/essai:1 -n essai-journal; sleep 4; kubectl run impatient --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-journal -- sh -c 'exit 3'; sleep 4; kubectl run grossiste --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-journal --overrides='{"spec":{"containers":[{"name":"g","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"64"}}}]}}' -- sleep 3600; sleep 40
```

```text
namespace/essai-journal created
pod/introuvable created
pod/impatient created
pod/grossiste created
```

## 🎯 Exercice 1 : les événements d'un seul objet

`kubectl events --for` filtre les événements d'un objet, et `--types` ne garde
que les avertissements :

```bash
kubectl events -n essai-journal --for pod/impatient --types=Warning
```

```text
LAST SEEN          TYPE      REASON    OBJECT          MESSAGE
8s (x4 over 42s)   Warning   BackOff   Pod/impatient   Back-off restarting failed container impatient in pod impatient_essai-journal(d94b35c2-7661-4627-ae5f-ff1705a2ac5b)
```

Une seule ligne, alors que le conteneur a redémarré plusieurs fois :
`(x4 over 42s)` dit que cet événement s'est produit 4 fois en 42 secondes.

## 🔁 Exercice 2 : un événement répété ne se duplique pas

Lisez le compteur et les deux dates de cet événement :

```bash
kubectl get events -n essai-journal --field-selector involvedObject.name=impatient,reason=BackOff -o custom-columns=RAISON:.reason,NOMBRE:.count,PREMIER:.firstTimestamp,DERNIER:.lastTimestamp
```

```text
RAISON    NOMBRE   PREMIER                DERNIER
BackOff   4        2026-11-21T04:40:09Z   2026-11-21T04:40:43Z
```

Attendez 90 secondes et relisez :

```bash
sleep 90; kubectl get events -n essai-journal --field-selector involvedObject.name=impatient,reason=BackOff -o custom-columns=RAISON:.reason,NOMBRE:.count,PREMIER:.firstTimestamp,DERNIER:.lastTimestamp
```

```text
RAISON    NOMBRE   PREMIER                DERNIER
BackOff   5        2026-11-21T04:40:09Z   2026-11-21T04:41:38Z
```

Le même objet Event a été mis à jour : le compteur passe à 5, la première date
ne bouge pas, la dernière avance. Un Pod qui redémarre en boucle ne crée donc
pas des centaines d'événements, mais un seul, dont le compteur grandit.

## 🥇 Exercice 3 : qui a été touché en premier ?

Triez les avertissements par leur première date :

```bash
kubectl get events -n essai-journal --field-selector type=Warning --sort-by=.firstTimestamp -o custom-columns=PREMIER:.firstTimestamp,OBJET:.involvedObject.name,RAISON:.reason
```

```text
PREMIER                OBJET         RAISON
2026-11-21T04:40:03Z   introuvable   Failed
2026-11-21T04:40:03Z   introuvable   Failed
2026-11-21T04:40:04Z   introuvable   Failed
2026-11-21T04:40:09Z   impatient     BackOff
2026-11-21T04:40:11Z   grossiste     FailedScheduling
```

`introuvable` a été touché en premier, puis `impatient`, puis `grossiste` :
l'ordre de création des pannes. Triez maintenant par la dernière date :

```bash
kubectl get events -n essai-journal --field-selector type=Warning --sort-by=.lastTimestamp -o custom-columns=DERNIER:.lastTimestamp,OBJET:.involvedObject.name,RAISON:.reason
```

```text
DERNIER                OBJET         RAISON
2026-11-21T04:40:11Z   grossiste     FailedScheduling
2026-11-21T04:41:37Z   introuvable   Failed
2026-11-21T04:41:37Z   introuvable   Failed
2026-11-21T04:41:38Z   impatient     BackOff
2026-11-21T04:42:18Z   introuvable   Failed
```

L'ordre change complètement : les pannes qui se répètent remontent sans cesse.
Pour trouver le début d'un incident, triez par `firstTimestamp`. Le tri par
défaut de `kubectl get events` n'est pas fait pour ça.

## ⏳ Exercice 4 : combien de temps les événements restent-ils ?

La durée de conservation des événements se règle sur l'API server, par
l'option `--event-ttl`. Cherchez-la dans son manifeste :

```bash
sudo grep -c -- '--event-ttl' /etc/kubernetes/manifests/kube-apiserver.yaml
```

```text
0
```

Absente : la valeur par défaut s'applique, une heure. Un incident de la veille
n'a donc plus aucun événement à montrer. Pour garder l'historique, il faut
copier les événements ailleurs avant leur expiration.

## 🚀 Exercice 5 : les événements d'un Deployment

Créez un Deployment, passez-le à 3 réplicas, et lisez ses événements :

```bash
kubectl create deployment etalage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-journal --replicas=1 -- sleep 3600 >/dev/null; kubectl scale deployment etalage -n essai-journal --replicas=3; sleep 5; kubectl events -n essai-journal --for deployment/etalage
```

```text
deployment.apps/etalage scaled
LAST SEEN   TYPE     REASON              OBJECT               MESSAGE
5s          Normal   ScalingReplicaSet   Deployment/etalage   Scaled up replica set etalage-75b6945bb6 from 0 to 1
5s          Normal   ScalingReplicaSet   Deployment/etalage   Scaled up replica set etalage-75b6945bb6 from 1 to 3
```

Le Deployment ne parle que de son ReplicaSet (`ScalingReplicaSet`). Les
erreurs d'un Pod sont sur le Pod, et celles de création des Pods sur le
ReplicaSet : pour reconstituer un incident, il faut lire chaque niveau.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Ses événements partent avec lui :

```bash
kubectl delete namespace essai-journal
```

```text
namespace "essai-journal" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-reconstituer-un-incident-par-les-evenements
dsoxlab check k8s-reconstituer-un-incident-par-les-evenements
```

```text
╭─ Résultat : k8s-reconstituer-un-incident-par-les-evenements ─╮
│  0 / 100 pts                                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                             │
╰──────────────────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un namespace où plusieurs applications sont en
panne, et le rapport qui dit ce qui est arrivé à chacune, et dans quel ordre.

```bash
dsoxlab run k8s-reconstituer-un-incident-par-les-evenements
dsoxlab challenge k8s-reconstituer-un-incident-par-les-evenements
```
