# Extraire une information précise avec kubectl

`kubectl get` affiche un tableau pensé pour être lu par un humain. Pour un
script, ou pour ne garder qu'une valeur, kubectl sait extraire exactement les
champs voulus : **JSONPath** suit un chemin dans l'objet, et
**custom-columns** construit un tableau avec vos propres colonnes. La leçon
montre les deux. Ce cours s'arrête sur ce qui piège : une clé qui contient des
points, une faute de casse qui ne lève aucune erreur, un retour à la ligne
oublié, un filtre sur l'état des Pods, et un Deployment qui ne dit pas la même
chose que ses Pods.

Vous travaillez dans un namespace d'essai, `essai-extraction`, avec une
application `inventaire`. Le challenge vous demandera d'autres champs sur une
autre application : vous le ferez seul, à la fin.

Page associée : [kubectl](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-extraire-avec-kubectl
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026.

## 📚 Exercice 1 : trouver le chemin d'un champ

Créez le namespace d'essai et l'application `inventaire`, à trois Pods nginx :

```bash
kubectl create namespace essai-extraction
kubectl create deployment inventaire --replicas=3 --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-extraction
kubectl rollout status deployment/inventaire -n essai-extraction --timeout=180s | tail -1
```

```text
namespace/essai-extraction created
deployment.apps/inventaire created
deployment "inventaire" successfully rolled out
```

Pour extraire un champ, il faut connaître son **chemin**. On le lit dans le
YAML de l'objet, en suivant l'indentation. Voici, dans le YAML du Deployment,
les lignes qui mènent au nombre de Pods et à l'image (`grep` ne garde qu'elles) :

```bash
kubectl get deployment inventaire -n essai-extraction -o yaml | sed -n '/^spec:/,/^status:/p' | grep -E '^spec:|^  replicas:|^  template:|^    spec:|^      containers:|^      - image:'
```

```text
spec:
  replicas: 3
  template:
    spec:
      containers:
      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Le nombre de Pods se trouve donc dans `spec`, puis `replicas`. L'image se
trouve dans `spec`, puis `template`, puis `spec`, puis `containers`, au premier
élément de la liste (le tiret), puis `image`.

## 📚 Exercice 2 : une clé qui contient des points

Le Deployment porte une annotation que Kubernetes tient à jour : le numéro de
sa révision. Affichez ses annotations :

```bash
kubectl get deployment inventaire -n essai-extraction -o yaml | sed -n '/^  annotations:/,/^  [a-z]/p'
```

```text
  annotations:
    deployment.kubernetes.io/revision: "1"
  creationTimestamp: "2026-11-20T14:32:10Z"
```

La clé est `deployment.kubernetes.io/revision`. Écrivez-la telle quelle dans
le chemin JSONPath :

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.metadata.annotations.deployment.kubernetes.io/revision}{"\n"}'; echo "(code $?)"
```

```text

(code 0)
```

Une ligne vide, et le code 0 : aucune erreur. En JSONPath, le point sépare
deux niveaux. kubectl a donc cherché une clé `deployment`, puis dedans une clé
`kubernetes`, puis `io/revision`. Rien de cela n'existe, et kubectl rend du
vide sans rien dire. Un `\` devant chaque point de la clé indique qu'il fait
partie du nom :

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}{"\n"}'
```

```text
1
```

Les labels et les annotations de Kubernetes contiennent souvent des points
(`app.kubernetes.io/name`, `kubernetes.io/hostname`) : le même `\.` sert pour
eux tous.

## 📚 Exercice 3 : une faute de casse, sans aucune erreur

Listez chaque Pod avec le nœud qui l'héberge. `range … end` répète le motif
pour chaque Pod, et `{"\t"}` met une tabulation. Le nom du champ est ici écrit
avec une faute, `nodename` au lieu de `nodeName` :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodename}{"\n"}{end}'; echo "(code $?)"
```

```text
inventaire-869d7bc7cf-4wrrg
inventaire-869d7bc7cf-mrxvn
inventaire-869d7bc7cf-tmqqc
(code 0)
```

La colonne du nœud est vide, et le code vaut 0. JSONPath respecte la casse :
`nodename` n'existe pas, et un champ absent rend du vide, pas une erreur. Quand
une colonne reste vide, cherchez le vrai nom du champ dans le YAML :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o yaml | grep -i -m1 'nodename'
```

```text
    nodeName: boutique-control-plane
```

`grep -i` ignore la casse, et `-m1` s'arrête au premier résultat. Le vrai nom
est `nodeName`, avec un `N` majuscule :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\n"}{end}'
```

```text
inventaire-869d7bc7cf-4wrrg	boutique-control-plane
inventaire-869d7bc7cf-mrxvn	boutique-control-plane
inventaire-869d7bc7cf-tmqqc	boutique-control-plane
```

## 📚 Exercice 4 : sans retour à la ligne

JSONPath n'écrit **que** ce que vous lui demandez. Retirez le `{"\n"}` du
motif :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{end}'; echo; echo '(fin)'
```

```text
inventaire-869d7bc7cf-4wrrginventaire-869d7bc7cf-mrxvninventaire-869d7bc7cf-tmqqc
(fin)
```

Les trois noms sont collés en un seul mot, illisible et inutilisable par un
script. Quand une sortie JSONPath paraît bizarre, cherchez d'abord le retour à
la ligne qui manque.

## 📚 Exercice 5 : des colonnes à soi

`custom-columns` construit un tableau : chaque colonne a un titre, deux-points,
puis le chemin du champ. Le chemin part de chaque objet, sans `.items` :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-4wrrg   10.244.0.118
inventaire-869d7bc7cf-mrxvn   10.244.0.116
inventaire-869d7bc7cf-tmqqc   10.244.0.117
```

`--no-headers` retire la ligne de titres, pour un script :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP --no-headers
```

```text
inventaire-869d7bc7cf-4wrrg   10.244.0.118
inventaire-869d7bc7cf-mrxvn   10.244.0.116
inventaire-869d7bc7cf-tmqqc   10.244.0.117
```

## 📚 Exercice 6 : filtrer et trier

Créez un Pod qui échoue tout de suite : sa commande sort en erreur. Attendez
qu'il passe en phase `Failed`, puis listez les Pods du namespace :

```bash
kubectl run en-panne --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-extraction -- sh -c 'exit 1'
kubectl wait --for=jsonpath='{.status.phase}'=Failed pod/en-panne -n essai-extraction --timeout=60s
kubectl get pods -n essai-extraction
```

```text
pod/en-panne created
pod/en-panne condition met
NAME                          READY   STATUS    RESTARTS   AGE
en-panne                      0/1     Error     0          2s
inventaire-869d7bc7cf-4wrrg   1/1     Running   0          3s
inventaire-869d7bc7cf-mrxvn   1/1     Running   0          3s
inventaire-869d7bc7cf-tmqqc   1/1     Running   0          3s
```

JSONPath sait filtrer une liste avec `?(…)`. `@` désigne l'objet examiné. Ici,
ne garder que les Pods dont la phase n'est pas `Running` :

```bash
kubectl get pods -n essai-extraction -o jsonpath='{range .items[?(@.status.phase!="Running")]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
```

```text
en-panne	Failed
```

Sur un gros namespace, ce filtre trouve en une commande les Pods qui ne
tournent pas. `--sort-by` trie la sortie selon un champ, ici l'adresse IP :

```bash
kubectl get pods -l app=inventaire -n essai-extraction --sort-by=.status.podIP -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-mrxvn   10.244.0.116
inventaire-869d7bc7cf-tmqqc   10.244.0.117
inventaire-869d7bc7cf-4wrrg   10.244.0.118
```

## 📚 Exercice 7 : garder une sortie dans un fichier

Une sortie de kubectl se redirige dans un fichier, comme toute autre (`>`).
`wc -l` compte ses lignes, et `cut` raccourcit l'affichage :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o 'custom-columns=POD:.metadata.name,IMAGE:.spec.containers[0].image' > ~/inventaire.txt; wc -l ~/inventaire.txt; head -2 ~/inventaire.txt | cut -c1-60
```

```text
4 /home/ansible/inventaire.txt
POD                           IMAGE
inventaire-869d7bc7cf-4wrrg   nginx:1.30.5@sha256:9bf97bd771
```

Quatre lignes : la ligne de titres, puis une par Pod.

## 📚 Exercice 8 : ce que veut le Deployment, et ce que font ses Pods

Mettez la mise à jour du Deployment en **pause**, puis changez son image :

```bash
kubectl rollout pause deployment/inventaire -n essai-extraction
kubectl set image deployment/inventaire nginx=nginx:1.30.4@sha256:d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c -n essai-extraction
```

```text
deployment.apps/inventaire paused
deployment.apps/inventaire image updated
```

Comparez l'image demandée par le **modèle de Pod** du Deployment avec celle
des Pods qui tournent :

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}'
```

```text
nginx:1.30.4@sha256:d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Le Deployment **veut** déjà la 1.30.4, mais ses Pods tournent encore en
1.30.5 : la pause a bloqué leur remplacement. Pour connaître ce qu'un
Deployment demande, lisez son modèle. Pour savoir ce qui tourne, lisez ses
Pods. Relancez la mise à jour :

```bash
kubectl rollout resume deployment/inventaire -n essai-extraction && kubectl rollout status deployment/inventaire -n essai-extraction --timeout=180s | tail -1
```

```text
deployment.apps/inventaire resumed
deployment "inventaire" successfully rolled out
```

## 🧹 Nettoyage

Supprimez le fichier de travail et le namespace d'essai :

```bash
rm -f ~/inventaire.txt; kubectl delete namespace essai-extraction
```

```text
namespace "essai-extraction" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-extraire-avec-kubectl
dsoxlab check k8s-extraire-avec-kubectl
```

```text
╭─ Résultat : k8s-extraire-avec-kubectl ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests       │
╰────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : extraire l'image que demande un Deployment, puis
lister ses Pods et leur nœud, avec JSONPath et avec custom-columns.

```bash
dsoxlab run k8s-extraire-avec-kubectl
dsoxlab challenge k8s-extraire-avec-kubectl
```
