# Étiqueter et sélectionner des Pods

Un **label** est une étiquette `clé=valeur` posée sur un objet Kubernetes.
Il sert à **trier et à choisir** des objets : un Service ou un ReplicaSet
retrouve ses Pods par leurs labels. Une **annotation** ressemble à un label,
mais elle sert seulement à **documenter** : on ne peut pas choisir des objets
avec. La leçon pose des labels un par un et filtre avec `=` et `!=`. Ce cours
vous fait agir sur plusieurs objets à la fois avec `-l`, utiliser les
sélecteurs `in`, `notin` et l'absence d'une clé, et lire où un label durable
est rangé.

Vous travaillez dans un namespace d'essai, `essai-labels`, avec trois
Deployments, `panier`, `stock` et `journal`. Le challenge vous demandera le
même genre de travail sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [Labels et annotations Kubernetes : kubectl label et annotate](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-label-annotate/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-labels-et-selecteurs
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026.

## 📚 Exercice 1 : étiqueter plusieurs objets d'un coup

Créez le namespace d'essai et trois Deployments :

```bash
kubectl create namespace essai-labels
kubectl create deployment panier \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=2 -n essai-labels
kubectl create deployment stock \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=2 -n essai-labels
kubectl create deployment journal \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=1 -n essai-labels
```

```text
namespace/essai-labels created
deployment.apps/panier created
deployment.apps/stock created
deployment.apps/journal created
```

`kubectl label` accepte un sélecteur à la place d'un nom : il étiquette alors
tous les objets choisis. Le sélecteur `in` choisit les objets dont la valeur
fait partie d'une liste. Posez `equipe=ventes` sur `panier` et `stock` en une
commande, puis `equipe=exploitation` sur `journal` :

```bash
kubectl label deployments -n essai-labels -l "app in (panier,stock)" equipe=ventes
kubectl label deployment journal -n essai-labels equipe=exploitation
kubectl get deployments -n essai-labels -L equipe
```

```text
deployment.apps/panier labeled
deployment.apps/stock labeled
deployment.apps/journal labeled
NAME      READY   UP-TO-DATE   AVAILABLE   AGE   EQUIPE
journal   1/1     1            1           1s    exploitation
panier    2/2     2            2           2s    ventes
stock     2/2     2            2           1s    ventes
```

L'option `-L equipe` ajoute une colonne avec la valeur de cette clé.

## 📚 Exercice 2 : choisir avec `notin` et l'absence d'une clé

`notin` est le contraire de `in`. Retirez ensuite le label de `journal`, et
comparez quatre sélecteurs :

```bash
kubectl get deployments -n essai-labels -l "equipe notin (exploitation)"
kubectl label deployment journal -n essai-labels equipe-
kubectl get deployments -n essai-labels -l "equipe notin (ventes)"
kubectl get deployments -n essai-labels -l "equipe!=ventes"
kubectl get deployments -n essai-labels -l "!equipe"
kubectl get deployments -n essai-labels -l "equipe"
```

```text
NAME     READY   UP-TO-DATE   AVAILABLE   AGE
panier   2/2     2            2           2s
stock    2/2     2            2           1s
deployment.apps/journal unlabeled
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
journal   1/1     1            1           1s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
journal   1/1     1            1           1s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
journal   1/1     1            1           1s
NAME     READY   UP-TO-DATE   AVAILABLE   AGE
panier   2/2     2            2           2s
stock    2/2     2            2           1s
```

`journal` n'a plus de clé `equipe`, et pourtant `notin (ventes)` et
`!= ventes` le rendent : une négation garde aussi les objets qui n'ont pas du
tout la clé. `!equipe` choisit seulement les objets sans la clé, et
`equipe` seul ceux qui l'ont, quelle que soit sa valeur. Avant de vous fier à
une négation, regardez ce qu'elle rend.

## 📚 Exercice 3 : voir où vit un label durable

Les labels de l'exercice 1 sont sur les Deployments. Regardez ceux des Pods de
`stock` :

```bash
kubectl get pods -n essai-labels -l app=stock --show-labels
```

```text
NAME                     READY   STATUS    RESTARTS   AGE   LABELS
stock-565d974c88-jpx84   1/1     Running   0          1s    app=stock,pod-template-hash=565d974c88
stock-565d974c88-xr8rp   1/1     Running   0          1s    app=stock,pod-template-hash=565d974c88
```

Aucun `equipe` : un label posé sur un Deployment ne descend pas jusqu'à ses
Pods. Les Pods sont fabriqués depuis le **modèle** du Deployment. Écrivez-y
`niveau=critique`, attendez le remplacement des Pods, puis comparez les deux
endroits :

```bash
kubectl patch deployment stock -n essai-labels \
  -p '{"spec":{"template":{"metadata":{"labels":{"niveau":"critique"}}}}}'
kubectl rollout status deployment/stock -n essai-labels --timeout=120s
kubectl get deployment stock -n essai-labels -o jsonpath='{.spec.template.metadata.labels}{"\n"}'
kubectl get deployment stock -n essai-labels -o jsonpath='{.metadata.labels}{"\n"}'
kubectl get pods -n essai-labels -l niveau=critique
```

```text title="Extrait de la sortie"
deployment.apps/stock patched
deployment "stock" successfully rolled out
{"app":"stock","niveau":"critique"}
{"app":"stock","equipe":"ventes"}
NAME                    READY   STATUS    RESTARTS   AGE
stock-6bb545dd4-8vs9f   1/1     Running   0          2s
stock-6bb545dd4-8wc75   1/1     Running   0          1s
```

`spec.template.metadata.labels` porte `niveau=critique` : c'est là que les
nouveaux Pods prennent leurs labels, et chaque Pod remplacé le recevra.
`metadata.labels`, les labels du Deployment lui-même, porte `equipe=ventes`.
Ajouter un label au modèle change le modèle : les deux Pods ont été remplacés,
leur nom a changé.

## 📚 Exercice 4 : agir sur tous les objets choisis

Un sélecteur sert aussi à supprimer ou à annoter. Supprimez tous les Pods de
`panier` d'un coup :

```bash
kubectl delete pods -n essai-labels -l app=panier
kubectl get pods -n essai-labels -l app=panier
```

```text
pod "panier-686df6f77c-lrcrq" deleted from essai-labels namespace
pod "panier-686df6f77c-t8rtz" deleted from essai-labels namespace
NAME                      READY   STATUS    RESTARTS   AGE
panier-686df6f77c-bbqng   1/1     Running   0          1s
panier-686df6f77c-pfvxj   1/1     Running   0          1s
```

Le Deployment les a aussitôt remplacés. Annotez maintenant les Deployments de
l'équipe ventes, puis essayez de choisir par cette annotation :

```bash
kubectl annotate deployments -n essai-labels -l equipe=ventes revue="relu le 20 novembre 2026"
kubectl get deployments -n essai-labels -o custom-columns=NOM:.metadata.name,REVUE:.metadata.annotations.revue
kubectl get deployments -n essai-labels -l revue
```

```text
deployment.apps/panier annotated
deployment.apps/stock annotated
NOM       REVUE
journal   <none>
panier    relu le 20 novembre 2026
stock     relu le 20 novembre 2026
No resources found in essai-labels namespace.
```

L'annotation accepte une phrase avec des espaces, ce qu'un label refuse. Mais
`-l revue` ne trouve rien : un sélecteur ne lit que les labels, jamais les
annotations.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai, avec ses trois Deployments.

```bash
kubectl delete namespace essai-labels
```

```text
namespace "essai-labels" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-labels-et-selecteurs
dsoxlab check k8s-labels-et-selecteurs
```

```text
╭─ Résultat : k8s-labels-et-selecteurs ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests      │
╰───────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : étiqueter durablement les Pods d'une application,
documenter son Deployment, et écrire un sélecteur avec une négation.

```bash
dsoxlab run k8s-labels-et-selecteurs
dsoxlab challenge k8s-labels-et-selecteurs
```
