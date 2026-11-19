# Déployer, exposer et mettre à l'échelle une première application

Ce cours vous fait déployer votre première application dans Kubernetes, geste
par geste, comme dans la leçon : créer un namespace, lancer l'application,
la rendre joignable, vérifier qu'elle répond, puis en lancer une copie de plus.

Quelques mots reviennent tout le long :

- un **Pod** est la plus petite unité que Kubernetes fait tourner : un ou
  plusieurs conteneurs ;
- un **Deployment** dit « je veux N Pods de cette image », et Kubernetes les
  crée et les remplace s'ils tombent ;
- un **Service** donne une adresse stable pour joindre ces Pods, même quand
  ils changent ;
- un **namespace** est un espace de rangement à l'intérieur du cluster.

Vous travaillez dans un namespace d'essai, `essai-web`, avec une application
nommée `accueil`. Le challenge vous demandera une autre application, dans un
autre namespace : vous la déploierez seul, à la fin.

Page associée : [Déployer votre première application](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-deploiement/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-premier-deploiement
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, en Kubernetes `v1.37.0`, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : créer un namespace

Créez le namespace `essai-web`, puis vérifiez qu'il existe :

```bash
kubectl create namespace essai-web
kubectl get namespace essai-web
```

```text
namespace/essai-web created
NAME        STATUS   AGE
essai-web   Active   0s
```

`Active` : le namespace est prêt. Toutes les commandes suivantes portent
l'option `-n essai-web`. Sans elle, vos objets iraient dans le namespace
`default`.

## 📚 Exercice 2 : lancer l'application avec un Deployment

Créez un Deployment `accueil` qui lance le serveur web nginx. L'image est
donnée avec son digest (`@sha256:...`) : vous êtes sûr d'avoir exactement
celle de la leçon.

```bash
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web
```

```text
deployment.apps/accueil created
```

Attendez que l'application soit disponible, puis regardez le Deployment :

```bash
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
kubectl get deployment accueil -n essai-web
```

```text
deployment.apps/accueil condition met
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
accueil   1/1     1            1           0s
```

La colonne `READY` affiche `1/1` : un Pod demandé, un Pod prêt.

Le Deployment n'a pas créé le Pod lui-même. Il a créé un **ReplicaSet**, qui
a créé le Pod. Voyez les deux :

```bash
kubectl get replicasets -n essai-web
kubectl get pods -n essai-web
```

```text
NAME                 DESIRED   CURRENT   READY   AGE
accueil-654cbccb8f   1         1         1       0s
NAME                       READY   STATUS    RESTARTS   AGE
accueil-654cbccb8f-stcjv   1/1     Running   0          0s
```

Le nom du Pod commence par celui du ReplicaSet, qui commence par celui du
Deployment. La fin du nom est tirée au hasard : la vôtre sera différente.

## 📚 Exercice 3 : rendre l'application joignable avec un Service

Un Pod peut disparaître et revenir avec une autre adresse. Pour le joindre de
façon stable, on crée un Service. Celui-ci écoute sur le port `8080` et
transmet au port `80`, celui de nginx :

```bash
kubectl expose deployment accueil --port=8080 --target-port=80 -n essai-web
kubectl get service accueil -n essai-web
```

```text
service/accueil exposed
NAME      TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
accueil   ClusterIP   10.96.209.14   <none>        8080/TCP   0s
```

Le type `ClusterIP` veut dire que le Service n'est joignable que depuis
l'intérieur du cluster. Son adresse (`CLUSTER-IP`) sera différente chez vous.

## 📚 Exercice 4 : voir comment le Service trouve les Pods

Le Service ne connaît pas les Pods par leur nom. Il les trouve grâce à une
**étiquette** (label) posée sur eux. Affichez les étiquettes du Pod :

```bash
kubectl get pods -n essai-web --show-labels
```

```text
NAME                       READY   STATUS    RESTARTS   AGE   LABELS
accueil-654cbccb8f-stcjv   1/1     Running   0          1s    app=accueil,pod-template-hash=654cbccb8f
```

Le Pod porte l'étiquette `app=accueil`, posée automatiquement d'après le nom du
Deployment. Regardez maintenant ce que cherche le Service :

```bash
kubectl describe service accueil -n essai-web | grep -E "^(Selector|Port|TargetPort|Endpoints)"
```

```text
Selector:                 app=accueil
Port:                     <unset>  8080/TCP
TargetPort:               80/TCP
Endpoints:                10.244.0.9:80
```

`Selector` dit quelle étiquette le Service cherche : `app=accueil`, celle du
Pod. `Endpoints` donne l'adresse du Pod trouvé.

Créez maintenant un Service qui ne trouve rien, pour voir à quoi ressemble la
panne :

```bash
kubectl create service clusterip vide --tcp=80:80 -n essai-web
kubectl describe service vide -n essai-web | grep -E "^(Selector|Endpoints)"
kubectl get endpointslice -n essai-web
```

```text
service/vide created
Selector:                 app=vide
Endpoints:
NAME            ADDRESSTYPE   PORTS     ENDPOINTS    AGE
accueil-qnnz4   IPv4          80        10.244.0.9   1s
vide-ccv5r      IPv4          <unset>   <unset>      0s
```

Le Service `vide` cherche l'étiquette `app=vide`, qu'aucun Pod ne porte : sa
ligne `Endpoints` est vide. Aucune erreur ne s'affiche pourtant, ni à la
création ni après. Retenez ce réflexe : un Service qui ne répond pas, on
regarde d'abord ses endpoints.

## 📚 Exercice 5 : interroger l'application depuis un Pod

Le nom `accueil` d'un Service n'existe qu'à l'intérieur du cluster. Lancez un
Pod temporaire avec l'image busybox, qui contient la commande `wget`, et
demandez la page :

```bash
kubectl run client \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  --rm -i --restart=Never -n essai-web -- wget -qO- http://accueil:8080
```

```text title="Extrait de la sortie"
All commands and output from this session will be recorded in container logs, including credentials and sensitive information passed through the command prompt.
If you don't see a command prompt, try pressing enter.
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
pod "client" deleted from essai-web namespace
```

Les deux premières lignes sont des messages de kubectl, pas une erreur. Vient
ensuite la page d'accueil de nginx : l'application répond. L'option `--rm`
supprime le Pod `client` dès qu'il a fini, d'où la dernière ligne.

## 📚 Exercice 6 : lancer une copie de plus

Demandez deux Pods au lieu d'un, puis attendez qu'ils soient prêts :

```bash
kubectl scale deployment accueil --replicas=2 -n essai-web
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
kubectl get pods -n essai-web -l app=accueil
```

```text
deployment.apps/accueil scaled
deployment.apps/accueil condition met
NAME                       READY   STATUS    RESTARTS   AGE
accueil-654cbccb8f-stcjv   1/1     Running   0          6s
accueil-654cbccb8f-t8j4n   1/1     Running   0          0s
```

Un second Pod est apparu. L'option `-l app=accueil` ne liste que les Pods qui
portent cette étiquette. Le Service, lui, a trouvé le nouveau Pod tout seul :

```bash
kubectl get endpointslice -n essai-web -l kubernetes.io/service-name=accueil
```

```text
NAME            ADDRESSTYPE   PORTS   ENDPOINTS                AGE
accueil-qnnz4   IPv4          80      10.244.0.9,10.244.0.12   6s
```

Deux adresses maintenant : le Service répartit les demandes entre les deux
Pods, sans que vous ayez rien changé.

## 📚 Exercice 7 : suivre ce que fait l'application

Lisez les dernières lignes du journal de l'application :

```bash
kubectl logs deployment/accueil -n essai-web --tail=3
```

```text
Found 2 pods, using pod/accueil-654cbccb8f-stcjv
2026/11/19 10:45:23 [notice] 1#1: start worker process 37
10.244.0.10 - - [19/Nov/2026:10:45:25 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
10.244.0.11 - - [19/Nov/2026:10:45:27 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
```

Le journal vient toujours d'un Pod : kubectl en a choisi un des deux. On y voit
les demandes `GET /` faites par `wget` à l'exercice 5, avec le code `200`
(réussite).

Regardez enfin ce que Kubernetes a fait, dans l'ordre :

```bash
kubectl get events -n essai-web --sort-by=.lastTimestamp | tail -6
```

```text title="Extrait de la sortie"
1s          Normal   ScalingReplicaSet   deployment/accueil              Scaled up replica set accueil-654cbccb8f from 1 to 2
1s          Normal   SuccessfulCreate    replicaset/accueil-654cbccb8f   Created pod: accueil-654cbccb8f-t8j4n
1s          Normal   Scheduled           pod/accueil-654cbccb8f-t8j4n    Successfully assigned essai-web/accueil-654cbccb8f-t8j4n to boutique-control-plane
1s          Normal   Started             pod/accueil-654cbccb8f-t8j4n    Container started
```

Vous y lisez la chaîne de l'exercice 6 : le Deployment demande un Pod de plus
au ReplicaSet, qui le crée, puis le Pod est placé sur un nœud et démarre.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Tout ce qu'il contient disparaît avec lui :
le Deployment, ses Pods et les deux Services.

```bash
kubectl delete namespace essai-web
```

```text
namespace "essai-web" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-premier-deploiement
dsoxlab check k8s-premier-deploiement
```

```text
╭─ Résultat : k8s-premier-deploiement ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests     │
╰──────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : déployer, exposer et mettre à l'échelle
l'application du challenge, puis garder sa réponse dans un fichier.

```bash
dsoxlab run k8s-premier-deploiement
dsoxlab challenge k8s-premier-deploiement
```
