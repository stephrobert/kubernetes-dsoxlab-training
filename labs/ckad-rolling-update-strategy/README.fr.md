# Régler une mise à jour progressive

Quand un Deployment change d'image, il remplace ses Pods. Sa **stratégie** dit
comment :

- **`Recreate`** arrête tous les anciens Pods, puis démarre les nouveaux. Le
  service est coupé pendant la bascule ;
- **`RollingUpdate`** remplace les Pods petit à petit. Le service continue de
  répondre.

Deux réglages pilotent `RollingUpdate`. **`maxSurge`** dit combien de Pods en
plus du nombre demandé peuvent exister pendant la bascule. **`maxUnavailable`**
dit combien de Pods peuvent manquer à l'appel. Dans ce cours, vous comparez les
deux stratégies et vous voyez l'effet de ces deux réglages.

Vous travaillez dans un namespace d'essai, `essai-strategie`, avec trois
Deployments de quatre Pods : `catalogue`, `panier` et `paiement`. Le challenge
vous demandera d'autres valeurs sur un autre Deployment : vous le ferez seul, à
la fin.

Page associée : [Rolling updates et rollbacks Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-rolling-update-strategy
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : lire la stratégie par défaut

Créez le namespace d'essai et un premier Deployment, `catalogue`, à quatre
Pods :

```bash
kubectl create namespace essai-strategie
kubectl create deployment catalogue --replicas=4 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-strategie
kubectl rollout status deployment/catalogue -n essai-strategie --timeout=180s | tail -1
```

```text
namespace/essai-strategie created
deployment.apps/catalogue created
deployment "catalogue" successfully rolled out
```

Vous n'avez écrit aucune stratégie. Lisez celle que le Deployment a reçue (le
champ `spec.strategy`) :

```bash
kubectl get deployment catalogue -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
{"rollingUpdate":{"maxSurge":"25%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

Par défaut, un Deployment est en `RollingUpdate`, avec `maxSurge` et
`maxUnavailable` à 25 % du nombre de Pods demandé.

## 📚 Exercice 2 : Recreate, tout arrêter puis tout redémarrer

Passez `catalogue` en `Recreate` :

```bash
kubectl patch deployment catalogue -n essai-strategie -p '{"spec":{"strategy":{"type":"Recreate"}}}'
```

```text
The Deployment "catalogue" is invalid: spec.strategy.rollingUpdate: Forbidden: may not be specified when strategy `type` is 'Recreate'
```

Refusé. Le bloc `rollingUpdate` de la stratégie par défaut est toujours là, et
`Recreate` n'en veut pas : il n'a rien à régler. Il faut retirer ce bloc dans
la même commande, en lui donnant la valeur `null` :

```bash
kubectl patch deployment catalogue -n essai-strategie -p '{"spec":{"strategy":{"type":"Recreate","rollingUpdate":null}}}'
kubectl get deployment catalogue -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
deployment.apps/catalogue patched
{"type":"Recreate"}
```

Changez maintenant l'image, puis lisez les **événements** du Deployment. Ils
racontent, dans l'ordre, ce qu'il a fait de ses ReplicaSets (l'objet qui fait
tourner les Pods d'une version) :

```bash
kubectl set image deployment/catalogue \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-strategie
kubectl rollout status deployment/catalogue -n essai-strategie --timeout=180s | tail -1
kubectl events --for deployment/catalogue -n essai-strategie
```

```text
deployment.apps/catalogue image updated
deployment "catalogue" successfully rolled out
LAST SEEN   TYPE     REASON              OBJECT                 MESSAGE
4s          Normal   ScalingReplicaSet   Deployment/catalogue   Scaled up replica set catalogue-75867bdb5 from 0 to 4
3s          Normal   ScalingReplicaSet   Deployment/catalogue   Scaled down replica set catalogue-75867bdb5 from 4 to 0
1s          Normal   ScalingReplicaSet   Deployment/catalogue   Scaled up replica set catalogue-5f44879b68 from 0 to 4
```

Lisez ligne par ligne :

1. la création : l'ancien ReplicaSet passe de 0 à 4 Pods ;
2. l'ancien ReplicaSet passe **d'un coup** de 4 à 0 Pod ;
3. le nouveau passe de 0 à 4 Pods.

Entre la ligne 2 et la ligne 3, aucun Pod ne tourne : le service est coupé.

## 📚 Exercice 3 : RollingUpdate, un Pod de plus à la fois

Créez un deuxième Deployment, `panier`, qui garde la stratégie par défaut, et
réglez-la : au plus **un** Pod en plus pendant la bascule (`maxSurge: 1`), et
**aucun** Pod qui manque (`maxUnavailable: 0`) :

```bash
kubectl create deployment panier --replicas=4 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-strategie
kubectl rollout status deployment/panier -n essai-strategie --timeout=180s | tail -1
kubectl patch deployment panier -n essai-strategie -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0}}}}'
kubectl get deployment panier -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
deployment.apps/panier created
deployment "panier" successfully rolled out
deployment.apps/panier patched
{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0},"type":"RollingUpdate"}
```

Changez l'image et lisez les événements :

```bash
kubectl set image deployment/panier \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-strategie
kubectl rollout status deployment/panier -n essai-strategie --timeout=180s | tail -1
kubectl events --for deployment/panier -n essai-strategie
```

```text
deployment.apps/panier image updated
deployment "panier" successfully rolled out
LAST SEEN   TYPE     REASON              OBJECT              MESSAGE
4s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-686df6f77c from 0 to 4
3s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 0 to 1
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 4 to 3
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 1 to 2
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 3 to 2
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 2 to 3
1s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 2 to 1
1s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 3 to 4
0s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 1 to 0
```

Cette fois, la bascule se fait un Pod à la fois. Le nouveau ReplicaSet monte
d'un Pod (il y en a alors 5, soit un de plus que les 4 demandés). Une fois ce
Pod prêt, l'ancien descend d'un Pod. Et ainsi de suite. Il y a toujours au
moins 4 Pods prêts : le service n'est jamais coupé.

## 📚 Exercice 4 : des pourcentages

`maxSurge` et `maxUnavailable` acceptent aussi un pourcentage du nombre de
Pods demandé. Créez un troisième Deployment, `paiement`, avec 50 % en plus et
25 % qui peuvent manquer :

```bash
kubectl create deployment paiement --replicas=4 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-strategie
kubectl rollout status deployment/paiement -n essai-strategie --timeout=180s | tail -1
kubectl patch deployment paiement -n essai-strategie -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":"50%","maxUnavailable":"25%"}}}}'
kubectl get deployment paiement -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
deployment.apps/paiement created
deployment "paiement" successfully rolled out
deployment.apps/paiement patched
{"rollingUpdate":{"maxSurge":"50%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

Les pourcentages s'écrivent entre guillemets : `"50%"` est un texte, `1` est un
nombre. Sur 4 Pods, 50 % donne **2** Pods en plus, et 25 % donne **1** Pod qui
peut manquer. Vérifiez-le sur les événements :

```bash
kubectl set image deployment/paiement \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-strategie
kubectl rollout status deployment/paiement -n essai-strategie --timeout=180s | tail -1
kubectl events --for deployment/paiement -n essai-strategie
```

```text
deployment.apps/paiement image updated
deployment "paiement" successfully rolled out
LAST SEEN   TYPE     REASON              OBJECT                MESSAGE
2s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-6d6f5b7db9 from 0 to 4
1s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-65dc89d74d from 0 to 2
1s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 4 to 3
1s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-65dc89d74d from 2 to 3
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 3 to 2
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-65dc89d74d from 3 to 4
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 2 to 1
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 1 to 0
```

Le nouveau ReplicaSet démarre avec **deux** Pods d'un coup (`from 0 to 2`), et
l'ancien perd tout de suite un Pod (`from 4 to 3`), sans attendre. La bascule
est plus rapide qu'avec `panier`, mais elle demande la place de deux Pods en
plus, et le service tourne un moment avec un Pod de moins.

## 📚 Exercice 5 : un réglage refusé

Essayez d'interdire à la fois les Pods en plus et les Pods qui manquent :

```bash
kubectl patch deployment paiement -n essai-strategie -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":0,"maxUnavailable":0}}}}'
kubectl get deployment paiement -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
The Deployment "paiement" is invalid: spec.strategy.rollingUpdate.maxUnavailable: Invalid value: 0: may not be 0 when `maxSurge` is 0
{"rollingUpdate":{"maxSurge":"50%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

Refusé, et la stratégie n'a pas bougé. Avec 0 et 0, le Deployment ne pourrait
ni ajouter un Pod neuf, ni retirer un ancien : la bascule ne pourrait jamais
commencer. L'un des deux réglages doit valoir au moins 1.

## 📚 Exercice 6 : la stratégie ne fait pas de révision

Vous avez changé deux fois `paiement` : sa stratégie, puis son image. Lisez son
historique et ses ReplicaSets (`-l app=paiement` ne garde que les siens) :

```bash
kubectl rollout history deployment/paiement -n essai-strategie
kubectl get rs -n essai-strategie -l app=paiement -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PRETS:.status.readyReplicas'
```

```text
deployment.apps/paiement
REVISION  CHANGE-CAUSE
1         <none>
2         <none>

NOM                   REVISION   IMAGE                                                                                  PRETS
paiement-65dc89d74d   2          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   4
paiement-6d6f5b7db9   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

Deux révisions seulement : la création et le changement d'image. Changer la
stratégie n'a créé ni révision ni Pod, parce qu'elle ne fait pas partie du
modèle des Pods. Elle sert seulement **au prochain** remplacement. Réglez donc
toujours la stratégie **avant** de changer l'image. L'ancien ReplicaSet reste
là, à zéro Pod (`<none>`), prêt pour un retour en arrière.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-strategie
```

```text
namespace "essai-strategie" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-rolling-update-strategy
dsoxlab check ckad-rolling-update-strategy
```

```text
╭─ Résultat : ckad-rolling-update-strategy ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests          │
╰───────────────────────────────────────────╯
```

0 sur 8 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Deployment en `Recreate` doit passer en mise à
jour progressive, avec des limites précises, puis changer d'image.

```bash
dsoxlab run ckad-rolling-update-strategy
dsoxlab challenge ckad-rolling-update-strategy
```
