# Installer un opérateur et configurer ce qu'il fait tourner

La leçon montre un opérateur qui crée et entretient les objets d'une
application à partir d'une seule ressource. Tout opérateur repose sur un
mécanisme du cluster : chaque objet qu'il crée porte un propriétaire, et le
cluster en tire les conséquences. Ce cours vous fait manipuler ce mécanisme
avec les contrôleurs déjà présents dans Kubernetes, sans opérateur : lire qui
possède quoi, donner un propriétaire à un objet, supprimer sans les enfants
puis les faire adopter, sortir un enfant de son groupe, et supprimer au
premier plan.

Vous travaillez dans un namespace d'essai, `essai-proprio`, avec un
Deployment `comptoir` (nginx) et une ConfigMap `fiche`. Le challenge porte
sur l'opérateur MongoDB et ses objets : vous le ferez seul, à la fin.

Page associée : [Opérateurs Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-operateur-installer-et-configurer
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et un Deployment à deux réplicas :

```bash
kubectl create namespace essai-proprio; kubectl create deployment comptoir --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=2 -n essai-proprio; kubectl rollout status deployment/comptoir -n essai-proprio --timeout=120s
```

```text
namespace/essai-proprio created
deployment.apps/comptoir created
Waiting for deployment "comptoir" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "comptoir" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "comptoir" rollout to finish: 1 of 2 updated replicas are available...
deployment "comptoir" successfully rolled out
```

## 🔗 Exercice 1 : qui possède quoi

Chaque objet créé par un contrôleur porte son propriétaire dans le champ
`metadata.ownerReferences`. Lisez-le sur le ReplicaSet, puis sur les Pods :

```bash
kubectl get replicaset -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} <- {.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name} controller={.metadata.ownerReferences[0].controller}{"\n"}{end}'; kubectl get pods -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} <- {.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'
```

```text
comptoir-c9b9dfdf7 <- Deployment/comptoir controller=true
comptoir-c9b9dfdf7-nssb2 <- ReplicaSet/comptoir-c9b9dfdf7
comptoir-c9b9dfdf7-pvwtk <- ReplicaSet/comptoir-c9b9dfdf7
```

Le Deployment possède le ReplicaSet, qui possède les Pods. `controller=true`
désigne le propriétaire qui gère l'objet : un objet n'en a qu'un. C'est
exactement ce que fait un opérateur avec ce qu'il crée : quand le challenge
vous demande ce qu'il fait tourner, les `ownerReferences` répondent.

## 🏷️ Exercice 2 : donner un propriétaire à un objet

Un propriétaire se désigne par son type, son nom et son UID, l'identifiant
unique que l'API lui a donné à la création. Créez une ConfigMap possédée par
le Deployment :

```bash
UID_D=$(kubectl get deployment comptoir -n essai-proprio -o jsonpath='{.metadata.uid}'); cat <<YAML | kubectl apply -n essai-proprio -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: fiche
  ownerReferences:
    - apiVersion: apps/v1
      kind: Deployment
      name: comptoir
      uid: $UID_D
data:
  note: possédée par comptoir
YAML
kubectl get configmap fiche -n essai-proprio
```

```text
configmap/fiche created
NAME    DATA   AGE
fiche   1      0s
```

L'API accepte le champ tel quel. Le nom seul ne suffit pas : c'est l'UID qui
compte. Un Deployment supprimé puis recréé sous le même nom aura un autre UID,
et ne sera pas le propriétaire de cette ConfigMap.

## 👶 Exercice 3 : supprimer sans les enfants, puis les faire adopter

Supprimez le Deployment avec `--cascade=orphan` : les objets qu'il possède
restent en place.

```bash
kubectl delete deployment comptoir -n essai-proprio --cascade=orphan; sleep 5; kubectl get deployment,replicaset,pods,configmap -n essai-proprio
```

```text
deployment.apps "comptoir" deleted from essai-proprio namespace
NAME                                 DESIRED   CURRENT   READY   AGE
replicaset.apps/comptoir-c9b9dfdf7   2         2         2       6s

NAME                           READY   STATUS    RESTARTS   AGE
pod/comptoir-c9b9dfdf7-nssb2   1/1     Running   0          6s
pod/comptoir-c9b9dfdf7-pvwtk   1/1     Running   0          6s

NAME                         DATA   AGE
configmap/fiche              1      5s
configmap/kube-root-ca.crt   1      6s
```

Le ReplicaSet, les Pods et la ConfigMap sont toujours là. Le ReplicaSet n'a
plus de propriétaire :

```bash
kubectl get replicaset -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} propriétaires={.metadata.ownerReferences}{"\n"}{end}'
```

```text
comptoir-c9b9dfdf7 propriétaires=
```

Recréez le Deployment à l'identique :

```bash
kubectl create deployment comptoir --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=2 -n essai-proprio; sleep 5; kubectl get replicaset -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} <- {.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'; kubectl get pods -n essai-proprio
```

```text
deployment.apps/comptoir created
comptoir-c9b9dfdf7 <- Deployment/comptoir
NAME                       READY   STATUS    RESTARTS   AGE
comptoir-c9b9dfdf7-nssb2   1/1     Running   0          12s
comptoir-c9b9dfdf7-pvwtk   1/1     Running   0          12s
```

Le nouveau Deployment a adopté l'ancien ReplicaSet, dont les Pods n'ont pas
redémarré (leur âge continue). Il l'a reconnu à son sélecteur et à son
gabarit identique. C'est ainsi qu'on remplace un objet qu'on ne peut pas
modifier, sans couper l'application.

## 📄 Exercice 4 : la fiche a perdu son propriétaire

Regardez la ConfigMap `fiche` :

```bash
kubectl get configmap fiche -n essai-proprio -o jsonpath='{.metadata.name} propriétaires={.metadata.ownerReferences}{"\n"}'
```

```text
fiche propriétaires=
```

Elle n'a plus de propriétaire. La suppression avec `--cascade=orphan` a
retiré la référence de tous les objets possédés, y compris de la ConfigMap.
Et l'adoption de l'exercice 3 ne concerne que les ReplicaSets : le nouveau
Deployment ne reprend pas une ConfigMap.

## 🚪 Exercice 5 : un enfant qui sort du sélecteur

Changez l'étiquette `app` d'un des Pods, pour qu'il ne corresponde plus au
sélecteur du ReplicaSet :

```bash
P=$(kubectl get pods -n essai-proprio -l app=comptoir -o jsonpath='{.items[0].metadata.name}'); kubectl label pod $P -n essai-proprio app=rayon --overwrite; sleep 5; kubectl get pods -n essai-proprio -L app; kubectl get pod $P -n essai-proprio -o jsonpath='propriétaires : {.metadata.ownerReferences}{"\n"}'
```

```text
pod/comptoir-c9b9dfdf7-nssb2 labeled
NAME                       READY   STATUS    RESTARTS   AGE   APP
comptoir-c9b9dfdf7-jv825   1/1     Running   0          5s    comptoir
comptoir-c9b9dfdf7-nssb2   1/1     Running   0          17s   rayon
comptoir-c9b9dfdf7-pvwtk   1/1     Running   0          17s   comptoir
propriétaires : 
```

Le ReplicaSet a relâché ce Pod (il n'a plus de propriétaire) et en a créé un
autre pour revenir à deux. Le Pod relâché tourne toujours, hors de tout
contrôle. C'est un geste de dépannage connu : on sort un Pod malade du
groupe pour l'examiner, sans réduire le nombre de réplicas.

## 🗑️ Exercice 6 : supprimer au premier plan

Rendez la ConfigMap au Deployment, avec son nouvel UID :

```bash
UID_D=$(kubectl get deployment comptoir -n essai-proprio -o jsonpath='{.metadata.uid}'); kubectl patch configmap fiche -n essai-proprio --type merge -p "{\"metadata\":{\"ownerReferences\":[{\"apiVersion\":\"apps/v1\",\"kind\":\"Deployment\",\"name\":\"comptoir\",\"uid\":\"$UID_D\"}]}}"; kubectl get configmap fiche -n essai-proprio -o jsonpath='{.metadata.ownerReferences[0].name}{"\n"}'
```

```text
configmap/fiche patched
comptoir
```

Supprimez le Deployment avec `--cascade=foreground`, sans attendre la fin,
puis regardez-le avant et après le travail du ramasse-miettes du cluster :

```bash
kubectl delete deployment comptoir -n essai-proprio --cascade=foreground --wait=false; kubectl get deployment comptoir -n essai-proprio -o jsonpath='finalizers={.metadata.finalizers} suppression={.metadata.deletionTimestamp}{"\n"}'; sleep 15; kubectl get deployment,replicaset,pods,configmap -n essai-proprio
```

```text
deployment.apps "comptoir" deleted from essai-proprio namespace
finalizers=["foregroundDeletion"] suppression=2026-11-21T00:50:00Z
NAME                           READY   STATUS    RESTARTS   AGE
pod/comptoir-c9b9dfdf7-nssb2   1/1     Running   0          32s

NAME                         DATA   AGE
configmap/kube-root-ca.crt   1      32s
```

Juste après la commande, le Deployment existe encore, marqué pour
suppression, avec le finalizer `foregroundDeletion` : il attend que ses
enfants soient supprimés avant de disparaître. Quinze secondes plus tard, le
ReplicaSet, ses Pods et la ConfigMap sont partis. Seul reste le Pod relâché à
l'exercice 5 : il n'avait plus de propriétaire. Avec un opérateur, c'est le
même mécanisme qui retire tout ce qu'il a créé quand vous supprimez sa
ressource.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-proprio
```

```text
namespace "essai-proprio" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-operateur-installer-et-configurer
dsoxlab check cka-operateur-installer-et-configurer
```

```text
╭─ Résultat : cka-operateur-installer-et-configurer ─╮
│  0 / 100 pts                                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests                   │
╰────────────────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : installer l'opérateur MongoDB, lui faire créer une
base, et régler ce qu'il fait tourner.

```bash
dsoxlab run cka-operateur-installer-et-configurer
dsoxlab challenge cka-operateur-installer-et-configurer
```
