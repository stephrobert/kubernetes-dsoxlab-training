# Étiqueter un nœud, afficher son rôle et le réserver à une équipe

La leçon montre comment gérer les nœuds : labels, rôles, `cordon` et taints.
Ce cours ajoute des cas qu'elle ne montre pas : un nœud qui porte deux rôles,
plusieurs nœuds étiquetés d'un coup par sélecteur, une annotation qu'on ne
peut pas sélectionner, une valeur que l'API refuse, et un label existant qu'on
ne remplace pas sans le demander.

Vous travaillez sur `k8s-w1.lab`, avec des labels qui commencent par
`essai`. Le challenge porte sur un autre nœud : vous le ferez seul, à la fin.

Page associée : [Gérer les nœuds Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/gerer-noeuds-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-etiqueter-et-isoler-un-noeud
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🏷️ Exercice 1 : deux rôles pour un nœud

La colonne `ROLES` de `kubectl get nodes` n'est pas un champ à part : elle
liste les labels dont la clé commence par `node-role.kubernetes.io/`. Posez-en
deux sur `k8s-w1.lab` :

```bash
kubectl label node k8s-w1.lab node-role.kubernetes.io/essai= node-role.kubernetes.io/etagere=; kubectl get nodes
```

```text
node/k8s-w1.lab labeled
NAME         STATUS   ROLES           AGE     VERSION
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2
k8s-w1.lab   Ready    essai,etagere   6h26m   v1.37.2
k8s-w2.lab   Ready    <none>          87s     v1.37.2
```

Les deux rôles s'affichent, séparés par une virgule. Un rôle n'a aucun effet
sur le placement des Pods : c'est une étiquette comme une autre.

## 📦 Exercice 2 : étiqueter plusieurs nœuds d'un coup

`kubectl label` accepte un sélecteur à la place d'un nom. Étiquetez tous les
nœuds qui ne sont pas le control plane, et affichez la valeur en colonne :

```bash
kubectl label nodes -l '!node-role.kubernetes.io/control-plane' essai-salle=b; kubectl get nodes -L essai-salle
```

```text
node/k8s-w1.lab labeled
node/k8s-w2.lab labeled
NAME         STATUS   ROLES           AGE     VERSION   ESSAI-SALLE
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2   
k8s-w1.lab   Ready    essai,etagere   6h26m   v1.37.2   b
k8s-w2.lab   Ready    <none>          87s     v1.37.2   b
```

Le `!` devant la clé veut dire « qui ne porte pas ce label ». Les deux workers
ont reçu `essai-salle=b` en une seule commande.

## 📝 Exercice 3 : une annotation ne se sélectionne pas

Une annotation porte une information pour les humains ou les outils, comme un
contact. Posez-en une, puis essayez de la chercher comme un label :

```bash
kubectl annotate node k8s-w1.lab essai-contact=atelier@formation.test; kubectl get nodes -l essai-contact=atelier@formation.test
```

```text
node/k8s-w1.lab annotated
Error from server (BadRequest): Unable to find "/v1, Resource=nodes" that match label selector "essai-contact=atelier@formation.test", field selector "": unable to parse requirement: values[0][essai-contact]: Invalid value: "atelier@formation.test": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345', regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
```

L'annotation est posée, mais la recherche échoue : `-l` ne sait lire que des
labels, et une adresse avec `@` n'est même pas une valeur de label valide.
Pour retrouver les nœuds qui portent une annotation, il faut filtrer la sortie
avec un jsonpath :

```bash
kubectl get nodes -o jsonpath='{range .items[?(@.metadata.annotations.essai-contact)]}{.metadata.name}{"\n"}{end}'
```

```text
k8s-w1.lab
```

## 🚫 Exercice 4 : une valeur que l'API refuse

Une valeur de label ne peut contenir que des lettres, des chiffres, `-`, `_`
et `.`. Essayez une valeur avec une espace :

```bash
kubectl label node k8s-w1.lab essai-salle='salle b'
```

```text
error: invalid label value: "essai-salle=salle b": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345', regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
```

Refusé, avec l'expression régulière exacte que la valeur doit respecter.

## ✏️ Exercice 5 : changer une valeur existante

`k8s-w1.lab` porte déjà `essai-salle=b`. Essayez de passer à `c` :

```bash
kubectl label node k8s-w1.lab essai-salle=c
```

```text
error: 'essai-salle' already has a value (b), and --overwrite is false
```

kubectl refuse d'écraser une valeur sans qu'on le demande. Avec `--overwrite` :

```bash
kubectl label node k8s-w1.lab essai-salle=c --overwrite; kubectl get nodes -L essai-salle
```

```text
node/k8s-w1.lab labeled
NAME         STATUS   ROLES           AGE     VERSION   ESSAI-SALLE
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2   
k8s-w1.lab   Ready    essai,etagere   6h26m   v1.37.2   c
k8s-w2.lab   Ready    <none>          88s     v1.37.2   b
```

Seul `k8s-w1.lab` a changé. Cette protection évite d'écraser par erreur un
label qu'un autre outil ou une autre équipe a posé.

## 🧹 Nettoyage

Retirez les labels et l'annotation d'essai. Un `-` après la clé supprime le
label :

```bash
kubectl label nodes --all essai-salle- node-role.kubernetes.io/essai- node-role.kubernetes.io/etagere- 2>&1 | grep -v 'not found'; kubectl annotate node k8s-w1.lab essai-contact-; kubectl get nodes
```

```text
node/k8s-cp.lab not labeled
node/k8s-w1.lab unlabeled
node/k8s-w2.lab unlabeled
node/k8s-w1.lab annotated
NAME         STATUS   ROLES           AGE     VERSION
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2
k8s-w1.lab   Ready    <none>          6h26m   v1.37.2
k8s-w2.lab   Ready    <none>          88s     v1.37.2
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-etiqueter-et-isoler-un-noeud
dsoxlab check cka-etiqueter-et-isoler-un-noeud
```

```text
╭─ Résultat : cka-etiqueter-et-isoler-un-noeud ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests              │
╰───────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un nœud à étiqueter, à présenter avec son rôle, puis
à réserver à une équipe.

```bash
dsoxlab run cka-etiqueter-et-isoler-un-noeud
dsoxlab challenge cka-etiqueter-et-isoler-un-noeud
```
