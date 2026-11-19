# Revenir en arrière sur un déploiement bloqué

Un Deployment garde l'historique de ses versions. Chaque changement du modèle
de ses Pods (une nouvelle image, par exemple) crée une **révision** numérotée,
et l'ancienne version reste en réserve, à zéro Pod. Quand une mise à jour se
passe mal, on peut donc **revenir en arrière** en une commande, sans rien
reconstruire. Dans ce cours, vous livrez une nouvelle image, vous écrivez la
raison du changement, vous provoquez une livraison qui bloque, puis vous
revenez à une version qui marche.

Vous travaillez dans un namespace d'essai, `essai-rollout`, avec un Deployment
`vitrine`. Le challenge vous demandera le même travail sur un autre Deployment,
déjà bloqué : vous le ferez seul, à la fin.

Page associée : [Deployments Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-deployment-rollout-rollback
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : créer un Deployment et lire son historique

Créez le namespace d'essai et un Deployment `vitrine` à deux Pods, en
nginx 1.30.5 :

```bash
kubectl create namespace essai-rollout
kubectl create deployment vitrine --replicas=2 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
namespace/essai-rollout created
deployment.apps/vitrine created
Waiting for deployment "vitrine" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "vitrine" rollout to finish: 1 of 2 updated replicas are available...
deployment "vitrine" successfully rolled out
```

`kubectl rollout status` suit le déploiement et rend la main quand tous les
Pods sont prêts. Lisez maintenant l'historique :

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
```

Une seule révision, la 1. La colonne `CHANGE-CAUSE` dit pourquoi une révision
existe. Elle est vide (`<none>`) : personne ne l'a encore remplie.

## 📚 Exercice 2 : livrer une nouvelle image

`kubectl set image` change l'image d'un conteneur du Deployment. Ici, le
conteneur s'appelle `nginx`, comme l'image de départ :

```bash
kubectl set image deployment/vitrine \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
deployment.apps/vitrine image updated
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Les Pods sont remplacés un par un. Regardez l'historique, puis les
ReplicaSets du namespace. Un ReplicaSet est l'objet qui fait tourner les Pods
d'une version. La commande affiche pour chacun son numéro de révision, son
image et son nombre de Pods prêts :

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         <none>

NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   2          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2
vitrine-8469487455   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

Deux révisions, et un ReplicaSet pour chacune. Celui de la révision 1 n'a plus
de Pod (`<none>` veut dire zéro), mais il est toujours là : c'est lui qui
servira pour revenir en arrière.

## 📚 Exercice 3 : écrire la cause du changement

La cause d'une révision vient de l'annotation `kubernetes.io/change-cause`,
posée sur le Deployment. Écrivez-la :

```bash
kubectl annotate deployment vitrine kubernetes.io/change-cause='passage en nginx 1.30.6' -n essai-rollout
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine annotated
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         passage en nginx 1.30.6
```

La révision en cours, la 2, a maintenant sa raison. Gardez en tête que cette
annotation reste sur le Deployment : vous allez voir ce que cela donne au
changement suivant.

## 📚 Exercice 4 : une livraison qui bloque

Par défaut, un Deployment attend 10 minutes avant de déclarer qu'une livraison
n'avance plus. Pour ne pas attendre aussi longtemps, ramenez ce délai à
30 secondes avec le champ `progressDeadlineSeconds` :

```bash
kubectl patch deployment vitrine -n essai-rollout -p '{"spec":{"progressDeadlineSeconds":30}}'
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine patched
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         passage en nginx 1.30.6
```

Pas de nouvelle révision : ce champ ne touche pas au modèle des Pods. Livrez
maintenant une image qui n'existe pas, `nginx:1.30.99`, comme si vous aviez
fait une faute de frappe :

```bash
kubectl set image deployment/vitrine nginx=nginx:1.30.99 -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=60s
```

```text
deployment.apps/vitrine image updated
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
error: deployment "vitrine" exceeded its progress deadline
```

La livraison est bloquée. Regardez les Pods :

```bash
kubectl get pods -n essai-rollout
```

```text
NAME                       READY   STATUS         RESTARTS   AGE
vitrine-56d8956678-hbc6x   1/1     Running        0          40s
vitrine-56d8956678-w8rqc   1/1     Running        0          48s
vitrine-75b7b686f9-9mz6h   0/1     ErrImagePull   0          31s
```

Le nouveau Pod n'arrive pas à télécharger son image (`ErrImagePull`). Les deux
anciens Pods tournent toujours : Kubernetes ne retire un ancien Pod qu'une fois
le nouveau prêt. Le service n'est donc pas coupé, mais la livraison n'avance
plus. Les ReplicaSets le montrent aussi :

```bash
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   2          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2
vitrine-75b7b686f9   3          nginx:1.30.99                                                                          <none>
vitrine-8469487455   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

La révision 3 existe, avec zéro Pod prêt. Pour savoir pourquoi le Deployment
n'avance plus, lisez ses conditions (`sed` coupe la sortie de `describe` pour
n'en garder que ce bloc) :

```bash
kubectl describe deployment vitrine -n essai-rollout | sed -n '/^Conditions:/,/^OldReplicaSets/p'
```

```text
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    False   ProgressDeadlineExceeded
OldReplicaSets:  vitrine-8469487455 (0/0 replicas created), vitrine-56d8956678 (2/2 replicas created)
```

`Available True` : assez de Pods répondent. `Progressing False` avec
`ProgressDeadlineExceeded` : la livraison a dépassé son délai.

## 📚 Exercice 5 : lire une révision avant d'y revenir

Avant de revenir en arrière, regardez l'historique :

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         passage en nginx 1.30.6
3         passage en nginx 1.30.6
```

La révision 3, celle de l'image fautive, affiche « passage en nginx 1.30.6 ».
C'est faux, mais c'est normal : l'annotation était restée sur le Deployment,
et chaque nouvelle révision la recopie. **Après chaque changement, réécrivez la
cause**, sinon l'historique ment.

Pour voir ce que contient une révision avant d'y revenir, ajoutez
`--revision` :

```bash
kubectl rollout history deployment/vitrine -n essai-rollout --revision=2
```

```text
deployment.apps/vitrine with revision #2
Pod Template:
  Labels:	app=vitrine
	pod-template-hash=56d8956678
  Annotations:	kubernetes.io/change-cause: passage en nginx 1.30.6
  Containers:
   nginx:
    Image:	nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
    Port:	<none>
    Host Port:	<none>
    Environment:	<none>
    Mounts:	<none>
  Volumes:	<none>
  Node-Selectors:	<none>
  Tolerations:	<none>
```

La révision 2 est bien celle de nginx 1.30.6, celle qui marchait.

## 📚 Exercice 6 : revenir à la révision précédente

`kubectl rollout undo` revient à la révision juste avant celle en cours :

```bash
kubectl rollout undo deployment/vitrine -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
deployment.apps/vitrine rolled back
deployment "vitrine" successfully rolled out
```

Le retour est immédiat : les Pods de la révision 2 tournaient encore. Lisez
l'historique et les ReplicaSets :

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
3         passage en nginx 1.30.6
4         passage en nginx 1.30.6

NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   4          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2
vitrine-75b7b686f9   3          nginx:1.30.99                                                                          <none>
vitrine-8469487455   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

La révision 2 a disparu de la liste, et une révision 4 est apparue. C'est le
même ReplicaSet (`vitrine-56d8956678`), qui a reçu un **nouveau numéro**. Un
retour en arrière ne détruit rien : il réactive l'ancien ReplicaSet et le
renumérote. Le ReplicaSet fautif, lui, reste là, à zéro Pod. Son Pod en
erreur est en cours de suppression :

```bash
kubectl get pods -n essai-rollout
```

```text
NAME                       READY   STATUS        RESTARTS   AGE
vitrine-56d8956678-hbc6x   1/1     Running       0          40s
vitrine-56d8956678-w8rqc   1/1     Running       0          48s
vitrine-75b7b686f9-9mz6h   0/1     Terminating   0          31s
```

## 📚 Exercice 7 : revenir à une révision précise

`--to-revision` revient à n'importe quelle révision de l'historique, pas
seulement à la précédente. Revenez à la toute première, nginx 1.30.5 :

```bash
kubectl rollout undo deployment/vitrine --to-revision=1 -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
deployment.apps/vitrine rolled back
Waiting for deployment "vitrine" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Cette fois, les Pods sont remplacés un par un, comme pour une livraison
normale. Regardez le résultat :

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
3         passage en nginx 1.30.6
4         passage en nginx 1.30.6
5         <none>

NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   4          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   <none>
vitrine-75b7b686f9   3          nginx:1.30.99                                                                          <none>
vitrine-8469487455   5          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   2
```

Le ReplicaSet de la révision 1 est devenu la révision 5, et porte les deux
Pods. Sa cause est vide : un retour en arrière remet aussi la cause de la
révision choisie, et la révision 1 n'en avait pas. Là encore, il faudrait
réécrire la cause.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-rollout
```

```text
namespace "essai-rollout" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-deployment-rollout-rollback
dsoxlab check cka-deployment-rollout-rollback
```

```text
╭─ Résultat : cka-deployment-rollout-rollback ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 8 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Deployment est bloqué sur une image qui n'existe
pas. Revenez à la version qui marchait, puis livrez la bonne image, avec sa
cause.

```bash
dsoxlab run cka-deployment-rollout-rollback
dsoxlab challenge cka-deployment-rollout-rollback
```
