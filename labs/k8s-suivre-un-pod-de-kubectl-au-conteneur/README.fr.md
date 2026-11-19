# Suivre un Pod de kubectl au conteneur

Quand vous créez une application, plusieurs composants de Kubernetes
travaillent l'un après l'autre avant qu'un conteneur tourne. Chacun laisse une
trace : un **événement**, qui dit ce qui s'est passé et qui l'a fait. Dans ce
cours, vous suivez ce trajet geste par geste, comme dans la leçon :

- l'**API server** reçoit et enregistre votre demande ;
- les **contrôleurs** créent les objets manquants (ReplicaSet, Pods) ;
- le **scheduler** choisit un nœud pour chaque Pod ;
- le **kubelet** du nœud choisi lance le conteneur.

Vous travaillez dans un namespace d'essai, `essai-trajet`, avec un Deployment
`trajet` de trois Pods. Le challenge vous demandera de relever ce trajet pour
une autre application : vous le ferez seul, à la fin.

Page associée : [Architecture Kubernetes : comprendre le cluster en 15 minutes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/architecture/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-suivre-un-pod-de-kubectl-au-conteneur
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`architecture` y tourne, avec un control plane et trois workers, et votre
kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : créer un Deployment de trois Pods

Créez le namespace d'essai, puis un Deployment de trois Pods, et attendez
qu'ils tournent :

```bash
kubectl create namespace essai-trajet
kubectl create deployment trajet \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=3 -n essai-trajet
kubectl wait --for=condition=Available deployment/trajet -n essai-trajet --timeout=180s
```

```text
namespace/essai-trajet created
deployment.apps/trajet created
deployment.apps/trajet condition met
```

La ligne `created` veut dire que l'API server a accepté et enregistré votre
demande. À ce moment, rien ne tourne encore. La ligne `condition met`
n'apparaît que quand les trois Pods tournent : entre les deux, tout le trajet
a eu lieu.

## 📚 Exercice 2 : voir sur quel nœud tourne chaque Pod

```bash
kubectl get pods -n essai-trajet -o wide
```

```text
NAME                     READY   STATUS    RESTARTS   AGE   IP           NODE                   NOMINATED NODE   READINESS GATES
trajet-fb65d8867-5rx62   1/1     Running   0          18s   10.244.2.2   architecture-worker    <none>           <none>
trajet-fb65d8867-7x5hz   1/1     Running   0          18s   10.244.1.2   architecture-worker2   <none>           <none>
trajet-fb65d8867-nzjkn   1/1     Running   0          18s   10.244.3.2   architecture-worker3   <none>           <none>
```

La colonne `NODE` montre le nœud choisi pour chaque Pod : le scheduler a
réparti les trois Pods sur les trois workers. La colonne `IP` montre que
chaque Pod a sa propre adresse. Chez vous, les noms et la répartition
peuvent être différents.

## 📚 Exercice 3 : lire les événements d'un Pod

Rangez le nom du premier Pod dans une variable, puis affichez la fin de son
`describe`, à partir de la ligne `Events:` :

```bash
POD=$(kubectl get pods -n essai-trajet -o jsonpath='{.items[0].metadata.name}')
echo $POD
kubectl describe pod $POD -n essai-trajet | sed -n '/^Events:/,$p'
```

```text
trajet-fb65d8867-5rx62
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  18s   default-scheduler  Successfully assigned essai-trajet/trajet-fb65d8867-5rx62 to architecture-worker
  Normal  Pulling    17s   kubelet            spec.containers{nginx}: Pulling image "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
  Normal  Pulled     0s    kubelet            spec.containers{nginx}: Successfully pulled image "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb" in 16.7s (16.7s including waiting). Image size: 63638242 bytes.
  Normal  Created    0s    kubelet            spec.containers{nginx}: Container created
  Normal  Started    0s    kubelet            spec.containers{nginx}: Container started
```

Regardez la colonne `From`, qui dit qui a fait quoi :

- `Scheduled` vient de `default-scheduler` : il a placé le Pod sur
  `architecture-worker` ;
- `Pulling`, `Pulled`, `Created` et `Started` viennent de `kubelet` : celui de
  `architecture-worker` a téléchargé l'image, créé le conteneur, puis l'a
  démarré.

## 📚 Exercice 4 : lire les événements du ReplicaSet

Les étapes d'avant, la création des Pods, se lisent sur le ReplicaSet :

```bash
kubectl get rs -n essai-trajet
RS=$(kubectl get rs -n essai-trajet -o jsonpath='{.items[0].metadata.name}')
kubectl describe rs $RS -n essai-trajet \
  | grep -E '^(Name|Controlled By|Replicas|Pods Status):|SuccessfulCreate'
```

```text
NAME               DESIRED   CURRENT   READY   AGE
trajet-fb65d8867   3         3         3       18s
Name:           trajet-fb65d8867
Controlled By:  Deployment/trajet
Replicas:       3 current / 3 desired
Pods Status:    3 Running / 0 Waiting / 0 Succeeded / 0 Failed
  Normal  SuccessfulCreate  18s   replicaset-controller  Created pod: trajet-fb65d8867-7x5hz
  Normal  SuccessfulCreate  18s   replicaset-controller  Created pod: trajet-fb65d8867-nzjkn
  Normal  SuccessfulCreate  18s   replicaset-controller  Created pod: trajet-fb65d8867-5rx62
```

`Controlled By: Deployment/trajet` : ce ReplicaSet appartient au Deployment.
Les trois lignes `SuccessfulCreate`, écrites par `replicaset-controller`, sont
la création des trois Pods.

## 📚 Exercice 5 : voir tous les événements, avec leur source

`kubectl get events -o wide` liste les événements de tout le namespace. La
colonne `SOURCE` dit quel composant a écrit chacun. La sortie est très large,
en voici le début :

```bash
kubectl get events -n essai-trajet -o wide --sort-by=.lastTimestamp | head -8
```

```text title="Extrait de la sortie"
LAST SEEN   TYPE     REASON              OBJECT                        SUBOBJECT                SOURCE                          MESSAGE                                                                                                                                                                              FIRST SEEN   COUNT   NAME
18s         Normal   SuccessfulCreate    replicaset/trajet-fb65d8867                            replicaset-controller           Created pod: trajet-fb65d8867-7x5hz                                                                                                                                                  18s          1       trajet-fb65d8867.18e96d5a3c35bb4a
18s         Normal   Scheduled           pod/trajet-fb65d8867-nzjkn                             default-scheduler               Successfully assigned essai-trajet/trajet-fb65d8867-nzjkn to architecture-worker3                                                                                                    18s          1       trajet-fb65d8867-nzjkn.18e96d5a3fe8a4e4
18s         Normal   ScalingReplicaSet   deployment/trajet                                      deployment-controller           Scaled up replica set trajet-fb65d8867 from 0 to 3                                                                                                                                   18s          1       trajet.18e96d5a3b02c2d9
```

Trois composants apparaissent : `deployment-controller` a créé le ReplicaSet,
`replicaset-controller` a créé les Pods, `default-scheduler` les a placés.

## 📚 Exercice 6 : supprimer un Pod et voir Kubernetes le remplacer

Vous avez demandé trois Pods. Supprimez-en un :

```bash
POD=$(kubectl get pods -n essai-trajet -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD -n essai-trajet
sleep 5
kubectl get pods -n essai-trajet
```

```text
pod "trajet-fb65d8867-5rx62" deleted from essai-trajet namespace
NAME                     READY   STATUS    RESTARTS   AGE
trajet-fb65d8867-7x5hz   1/1     Running   0          25s
trajet-fb65d8867-mqvjk   1/1     Running   0          7s
trajet-fb65d8867-nzjkn   1/1     Running   0          25s
```

Il y a de nouveau trois Pods. Le Pod supprimé n'est pas revenu : c'est un Pod
**neuf** (`mqvjk`, 7 secondes). Le ReplicaSet a vu deux Pods au lieu de trois,
et il en a créé un. Les événements racontent la suite :

```bash
kubectl get events -n essai-trajet --sort-by=.lastTimestamp | tail -6
```

```text
7s          Normal   Scheduled           pod/trajet-fb65d8867-mqvjk    Successfully assigned essai-trajet/trajet-fb65d8867-mqvjk to architecture-worker
7s          Normal   Created             pod/trajet-fb65d8867-5rx62    Container created
6s          Normal   Started             pod/trajet-fb65d8867-mqvjk    Container started
6s          Normal   Killing             pod/trajet-fb65d8867-5rx62    Stopping container nginx
6s          Normal   Created             pod/trajet-fb65d8867-mqvjk    Container created
6s          Normal   Pulled              pod/trajet-fb65d8867-mqvjk    Container image "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb" already present on machine and can be accessed by the pod
```

Le nouveau Pod suit le même trajet : `Scheduled`, puis `Created` et `Started`.
L'image était déjà sur le nœud (`already present on machine`) : pas de
téléchargement cette fois. `Killing` est l'arrêt du conteneur du Pod
supprimé.

## 📚 Exercice 7 : joindre un Pod par son adresse

Chaque Pod a sa propre adresse, et tout Pod peut joindre tout autre Pod
directement. Relevez l'adresse d'un Pod :

```bash
kubectl get pods -n essai-trajet -o jsonpath='{.items[0].status.podIP}'; echo
```

```text
10.244.1.2
```

Lancez un Pod temporaire et demandez la page à cette adresse. Remplacez
`10.244.1.2` par l'adresse que vous avez relevée :

```bash
kubectl run test --rm -i --restart=Never -n essai-trajet \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  -- wget -qO- http://10.244.1.2
```

```text title="Extrait de la sortie"
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
pod "test" deleted from essai-trajet namespace
```

La page de nginx s'affiche : le Pod `test` a joint un Pod du cluster par son
adresse, sans rien configurer. Il arrive que la page s'affiche **deux fois**,
avec la ligne `warning: couldn't attach to pod/test, falling back to streaming
logs` : le Pod a fini avant que kubectl s'y branche, et kubectl relit sa
sortie. Ce n'est pas une erreur.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-trajet
```

```text
namespace "essai-trajet" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```

```text
╭─ Résultat : k8s-suivre-un-pod-de-kubectl-au-conteneur ─╮
│  0 / 100 pts                                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                       │
╰────────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : créer l'application du challenge, puis relever dans
ses événements qui l'a placée, qui l'a lancée, et sur quel nœud.

```bash
dsoxlab run k8s-suivre-un-pod-de-kubectl-au-conteneur
dsoxlab challenge k8s-suivre-un-pod-de-kubectl-au-conteneur
```
