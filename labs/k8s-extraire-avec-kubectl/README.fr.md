# Extraire une information précise avec kubectl

`kubectl get` affiche un tableau pensé pour être lu par un humain. Pour un
script, ou pour ne garder qu'une valeur, kubectl sait extraire exactement les
champs voulus : **JSONPath** suit un chemin dans l'objet, et
**custom-columns** construit un tableau avec vos propres colonnes. Dans ce
cours, vous trouvez le chemin d'un champ, vous l'extrayez d'un objet puis d'une
liste, vous construisez vos colonnes, vous filtrez et triez, puis vous voyez
pourquoi un Deployment et ses Pods ne disent pas toujours la même chose.

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
19 novembre 2026.

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

## 📚 Exercice 2 : JSONPath sur un objet

En JSONPath, ce chemin s'écrit avec des points, en partant de la racine de
l'objet. Un élément de liste se désigne par son rang entre crochets, en
commençant à 0. `{"\n"}` ajoute un retour à la ligne :

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.replicas}{"\n"}'
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
3
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Les apostrophes autour de l'expression empêchent le shell d'interpréter les
crochets et les accolades.

## 📚 Exercice 3 : JSONPath sur une liste

`kubectl get pods` rend une **liste** : les objets sont rangés sous `.items`.
`[*]` les prend tous :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{.items[*].metadata.name}{"\n"}'
```

```text
inventaire-869d7bc7cf-8cvtv inventaire-869d7bc7cf-dsws2 inventaire-869d7bc7cf-pq5ck
```

Les trois noms tiennent sur une ligne. Pour une ligne par Pod, `range … end`
répète un motif pour chaque objet. Ici, le nom, une tabulation (`{"\t"}`),
l'adresse IP du Pod, puis un retour à la ligne :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.podIP}{"\n"}{end}'
```

```text
inventaire-869d7bc7cf-8cvtv	10.244.0.25
inventaire-869d7bc7cf-dsws2	10.244.0.26
inventaire-869d7bc7cf-pq5ck	10.244.0.24
```

## 📚 Exercice 4 : sans retour à la ligne

JSONPath n'écrit **que** ce que vous lui demandez. Retirez le `{"\n"}` du
motif :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{end}'; echo; echo '(fin)'
```

```text
inventaire-869d7bc7cf-8cvtvinventaire-869d7bc7cf-dsws2inventaire-869d7bc7cf-pq5ck
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
inventaire-869d7bc7cf-8cvtv   10.244.0.25
inventaire-869d7bc7cf-dsws2   10.244.0.26
inventaire-869d7bc7cf-pq5ck   10.244.0.24
```

`--no-headers` retire la ligne de titres, pour un script :

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP --no-headers
```

```text
inventaire-869d7bc7cf-8cvtv   10.244.0.25
inventaire-869d7bc7cf-dsws2   10.244.0.26
inventaire-869d7bc7cf-pq5ck   10.244.0.24
```

## 📚 Exercice 6 : filtrer et trier

JSONPath sait filtrer une liste avec `?(…)`. `@` désigne l'objet examiné. Ici,
parmi les Pods de **tous** les namespaces (`-A`), ne garder que ceux de
`essai-extraction` :

```bash
kubectl get pods -A -o jsonpath='{range .items[?(@.metadata.namespace=="essai-extraction")]}{.metadata.name}{"\n"}{end}'
```

```text
inventaire-869d7bc7cf-8cvtv
inventaire-869d7bc7cf-dsws2
inventaire-869d7bc7cf-pq5ck
```

`--sort-by` trie la sortie selon un champ, ici l'adresse IP :

```bash
kubectl get pods -l app=inventaire -n essai-extraction --sort-by=.status.podIP -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-pq5ck   10.244.0.24
inventaire-869d7bc7cf-8cvtv   10.244.0.25
inventaire-869d7bc7cf-dsws2   10.244.0.26
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
inventaire-869d7bc7cf-8cvtv   nginx:1.30.5@sha256:9bf97bd771
```

Quatre lignes : la ligne de titres, puis une par Pod.

## 📚 Exercice 8 : ce que veut le Deployment, et ce que font ses Pods

Mettez la mise à jour du Deployment en **pause**, puis changez son image :

```bash
kubectl rollout pause deployment/inventaire -n essai-extraction
kubectl set image deployment/inventaire nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 -n essai-extraction
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
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Le Deployment **veut** déjà la 1.30.6, mais ses Pods tournent encore en
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
