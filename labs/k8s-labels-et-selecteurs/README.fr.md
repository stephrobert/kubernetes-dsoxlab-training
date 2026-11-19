# Étiqueter et sélectionner des Pods

Un **label** est une étiquette `clé=valeur` posée sur un objet Kubernetes.
Il sert à **trier et à choisir** des objets : un Service ou un ReplicaSet
retrouve ses Pods par leurs labels. Une **annotation** ressemble à un label,
mais elle sert seulement à **documenter** : on ne peut pas choisir des objets
avec. Dans ce cours, vous posez, modifiez et retirez des labels, vous filtrez
des Pods avec un **sélecteur**, vous rendez un label durable, et vous
documentez un objet avec une annotation.

Vous travaillez dans un namespace d'essai, `essai-labels`, avec deux
Deployments, `front` et `back`. Le challenge vous demandera le même travail
sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [Labels et annotations Kubernetes : kubectl label et annotate](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-label-annotate/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-labels-et-selecteurs
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : créer deux Deployments et lire leurs labels

Créez le namespace d'essai, puis deux Deployments : `front` avec trois Pods,
`back` avec deux.

```bash
kubectl create namespace essai-labels
kubectl create deployment front --replicas=3 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-labels
kubectl create deployment back --replicas=2 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-labels
kubectl rollout status deployment/front -n essai-labels --timeout=120s | tail -1
kubectl rollout status deployment/back -n essai-labels --timeout=120s | tail -1
kubectl get pods -n essai-labels --show-labels
```

```text
namespace/essai-labels created
deployment.apps/front created
deployment.apps/back created
deployment "front" successfully rolled out
deployment "back" successfully rolled out
NAME                     READY   STATUS    RESTARTS   AGE   LABELS
back-77679779f-flc9h     1/1     Running   0          1s    app=back,pod-template-hash=77679779f
back-77679779f-wzlqt     1/1     Running   0          1s    app=back,pod-template-hash=77679779f
front-5f4649c9cf-dk8hj   1/1     Running   0          1s    app=front,pod-template-hash=5f4649c9cf
front-5f4649c9cf-fmszn   1/1     Running   0          1s    app=front,pod-template-hash=5f4649c9cf
front-5f4649c9cf-q6hf8   1/1     Running   0          1s    app=front,pod-template-hash=5f4649c9cf
```

Chaque Pod a déjà deux labels, que vous n'avez pas écrits : `app`, avec le nom
du Deployment, et `pod-template-hash`, posé par le Deployment.

## 📚 Exercice 2 : poser, modifier et retirer un label

Rangez le nom du premier Pod `front` dans une variable, puis posez-lui le
label `niveau=bronze` :

```bash
POD=$(kubectl get pods -n essai-labels -l app=front -o jsonpath='{.items[0].metadata.name}')
echo $POD
kubectl label pod $POD niveau=bronze -n essai-labels
```

```text
front-5f4649c9cf-dk8hj
pod/front-5f4649c9cf-dk8hj labeled
```

Essayez de changer sa valeur, puis recommencez avec `--overwrite` :

```bash
kubectl label pod $POD niveau=argent -n essai-labels
kubectl label pod $POD niveau=argent --overwrite -n essai-labels
```

```text
error: 'niveau' already has a value (bronze), and --overwrite is false
pod/front-5f4649c9cf-dk8hj labeled
```

La première commande est refusée : kubectl n'écrase pas une valeur par
accident. `--overwrite` lève cette protection. Pour retirer un label, collez
un tiret derrière la clé :

```bash
kubectl label pod $POD niveau- -n essai-labels
kubectl label pod $POD niveau- -n essai-labels
```

```text
pod/front-5f4649c9cf-dk8hj unlabeled
label "niveau" not found.
pod/front-5f4649c9cf-dk8hj not labeled
```

La seconde fois, le label n'existe plus : kubectl le dit, sans erreur.

## 📚 Exercice 3 : étiqueter plusieurs Pods d'un coup

`kubectl label` accepte un sélecteur `-l`, pour toucher tous les Pods qui
correspondent. Avant une modification en masse, `--dry-run=server` montre ce
qui serait touché, **sans rien modifier** :

```bash
kubectl label pods -l app=front role=vitrine-web --dry-run=server -n essai-labels
kubectl label pods -l app=back role=donnees -n essai-labels
kubectl get pods -n essai-labels -L role
```

```text
pod/front-5f4649c9cf-dk8hj labeled (server dry run)
pod/front-5f4649c9cf-fmszn labeled (server dry run)
pod/front-5f4649c9cf-q6hf8 labeled (server dry run)
pod/back-77679779f-flc9h labeled
pod/back-77679779f-wzlqt labeled
NAME                     READY   STATUS    RESTARTS   AGE   ROLE
back-77679779f-flc9h     1/1     Running   0          2s    donnees
back-77679779f-wzlqt     1/1     Running   0          2s    donnees
front-5f4649c9cf-dk8hj   1/1     Running   0          2s
front-5f4649c9cf-fmszn   1/1     Running   0          2s
front-5f4649c9cf-q6hf8   1/1     Running   0          2s
```

`-L role` affiche le label `role` en colonne. Les Pods `back` l'ont reçu. Les
Pods `front`, eux, ne l'ont pas : leur commande n'était qu'un essai
(`server dry run`).

## 📚 Exercice 4 : filtrer avec un sélecteur

Posez un niveau différent sur deux Pods `front` :

```bash
P1=$(kubectl get pods -n essai-labels -l app=front -o jsonpath='{.items[0].metadata.name}')
P2=$(kubectl get pods -n essai-labels -l app=front -o jsonpath='{.items[1].metadata.name}')
kubectl label pod $P1 niveau=or -n essai-labels
kubectl label pod $P2 niveau=argent -n essai-labels
kubectl get pods -n essai-labels -l app=front,niveau=or
```

```text
pod/front-5f4649c9cf-dk8hj labeled
pod/front-5f4649c9cf-fmszn labeled
NAME                     READY   STATUS    RESTARTS   AGE
front-5f4649c9cf-dk8hj   1/1     Running   0          2s
```

Dans un sélecteur, la virgule veut dire « et » : `app=front,niveau=or` ne
garde que le Pod qui a les deux. Il y a d'autres formes. Comptez les Pods que
chacune retient (`wc -l` compte les lignes) :

```bash
kubectl get pods -n essai-labels -l 'niveau!=argent' --no-headers | wc -l
kubectl get pods -n essai-labels -l 'niveau in (or, argent)' --no-headers | wc -l
kubectl get pods -n essai-labels -l niveau --no-headers | wc -l
kubectl get pods -n essai-labels -l '!niveau' --no-headers | wc -l
kubectl get pods -n essai-labels -l 'niveau,niveau!=argent' --no-headers | wc -l
```

```text
4
2
2
3
1
```

Ligne par ligne :

- `niveau!=argent` : **4** Pods. Attention au piège : cette forme garde aussi
  les Pods qui n'ont **pas du tout** de label `niveau` (les trois autres) ;
- `niveau in (or, argent)` : 2 Pods, ceux qui ont l'une des deux valeurs ;
- `niveau` : 2 Pods, ceux qui ont la clé, quelle que soit sa valeur ;
- `!niveau` : 3 Pods, ceux qui n'ont pas la clé ;
- `niveau,niveau!=argent` : 1 Pod. On demande la clé **et** une valeur
  différente d'`argent`.

Mettez entre apostrophes les sélecteurs qui contiennent `!`, des parenthèses
ou des espaces : sinon, le shell les modifie avant kubectl.

## 📚 Exercice 5 : rendre un label durable

Un label posé sur un Pod disparaît avec lui. Supprimez le Pod qui a
`niveau=or`, et regardez celui qui le remplace :

```bash
P1=$(kubectl get pods -n essai-labels -l niveau=or -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $P1 -n essai-labels
kubectl rollout status deployment/front -n essai-labels --timeout=120s | tail -1
kubectl get pods -n essai-labels -l app=front -L niveau
```

```text
pod "front-5f4649c9cf-dk8hj" deleted from essai-labels namespace
deployment "front" successfully rolled out
NAME                     READY   STATUS    RESTARTS   AGE   NIVEAU
front-5f4649c9cf-95sjc   1/1     Running   0          2s
front-5f4649c9cf-fmszn   1/1     Running   0          4s    argent
front-5f4649c9cf-q6hf8   1/1     Running   0          4s
```

Le nouveau Pod (`95sjc`) n'a pas le label : le Deployment l'a fabriqué à
partir de son **modèle de Pod**, qui ne connaît pas `niveau`. Un label durable
s'écrit donc dans ce modèle. `kubectl patch` modifie un champ du Deployment :

```bash
kubectl patch deployment front -n essai-labels \
  -p '{"spec":{"template":{"metadata":{"labels":{"equipe":"vente"}}}}}'
kubectl rollout status deployment/front -n essai-labels --timeout=120s | tail -1
kubectl get pods -n essai-labels -l equipe=vente
```

```text
deployment.apps/front patched
deployment "front" successfully rolled out
NAME                     READY   STATUS    RESTARTS   AGE
front-79b5b7cccb-5mplw   1/1     Running   0          0s
front-79b5b7cccb-dsn5b   1/1     Running   0          1s
front-79b5b7cccb-kwg4s   1/1     Running   0          2s
```

Les trois Pods ont `equipe=vente`. Comme le modèle a changé, le Deployment a
remplacé tous les Pods. Ils le garderont, même s'ils sont recréés.

À l'inverse, un label posé sur le Deployment lui-même ne descend pas jusqu'aux
Pods :

```bash
kubectl label deployment back equipe=stock -n essai-labels
kubectl get pods -n essai-labels -l equipe=stock
```

```text
deployment.apps/back labeled
No resources found in essai-labels namespace.
```

Aucun Pod n'a `equipe=stock` : les Pods reçoivent les labels du modèle de Pod,
pas ceux du Deployment.

## 📚 Exercice 6 : documenter un objet avec une annotation

`kubectl annotate` s'utilise comme `kubectl label`. La valeur, elle, est un
texte libre. Ajoutez une adresse de contact au Deployment `front`, puis
changez-la :

```bash
kubectl annotate deployment front contact='equipe-vente@exemple.fr' -n essai-labels
kubectl annotate deployment front contact='support@exemple.fr' -n essai-labels
kubectl annotate deployment front contact='support@exemple.fr' --overwrite -n essai-labels
```

```text
deployment.apps/front annotated
error: --overwrite is false but found the following declared annotation(s): 'contact' already has a value (equipe-vente@exemple.fr)
deployment.apps/front annotated
```

Comme pour un label, changer une valeur demande `--overwrite`. Lisez
l'annotation, puis essayez de vous en servir pour choisir des objets :

```bash
kubectl get deployment front -n essai-labels -o jsonpath='{.metadata.annotations.contact}{"\n"}'
kubectl get deployments -n essai-labels -l contact
```

```text
support@exemple.fr
No resources found in essai-labels namespace.
```

`-l contact` ne trouve rien : une annotation ne sert pas à sélectionner. Si
vous devez un jour choisir des objets par une information, c'est un label.
Sinon, c'est une annotation.

## 📚 Exercice 7 : voir un label refusé

Essayez de mettre une phrase dans un label :

```bash
kubectl label deployment back 'resume=Stockage des commandes' -n essai-labels
```

```text
error: invalid label value: "resume=Stockage des commandes": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345', regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
```

Refusé : la valeur d'un label n'accepte ni espaces ni accents, et fait 63
caractères au plus. Une phrase va dans une annotation.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

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
