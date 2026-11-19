# Changer de contexte et fixer le namespace par défaut

Ce cours vous fait pratiquer, sur la machine du lab, chaque geste de la leçon :
lire le contexte actif, viser un autre namespace ou un autre contexte pour une
seule commande, fixer le namespace par défaut, créer et supprimer un contexte,
créer un objet là où le contexte le dit, et protéger un kubeconfig. Vous
travaillez sur le contexte `kind-boutique` et sur des objets d'essai : la
bascule vers `recette` est le challenge, il reste pour la fin.

Page associée : [kubeconfig et contextes kubectl](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-contexte/).

## 🔧 Avant de commencer

```bash
dsoxlab run k8s-changer-de-contexte
```

La commande prépare la machine `k8s-kind.lab` et vous y connecte. Deux
clusters kind tournent, et votre `~/.kube/config` connaît deux contextes :
`kind-boutique`, actif, et `recette`. Les sorties ci-dessous ont été relevées
sur cette machine (Debian 13.7, kubectl et clusters en `v1.37.0`) le
19 novembre 2026.

## 📚 Exercice 1 : lire où vous êtes

Avant toute commande qui modifie, on regarde quel cluster on vise. Listez les
contextes, puis demandez le seul nom du contexte actif.

```bash
kubectl config get-contexts
kubectl config current-context
```

```text
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique
          recette         recette         recette
kind-boutique
```

L'astérisque marque le contexte actif, `kind-boutique`. La colonne
`NAMESPACE` est vide pour les deux contextes : sans réglage, kubectl travaille
dans `default`. Vérifiez-le sur le seul contexte courant :

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo
```

La sortie est une ligne vide : aucun namespace n'est fixé.

## 📚 Exercice 2 : changer de namespace pour une seule commande

Listez les Pods sans option, puis dans le namespace `local-path-storage`.

```bash
kubectl get pods
kubectl get pods -n local-path-storage
```

```text
No resources found in default namespace.
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          33s
```

La première commande interroge `default`, qui est vide. La seconde vise un
autre namespace pour elle seule : l'option `-n` ne modifie rien dans le
fichier.

## 📚 Exercice 3 : viser un contexte pour une seule commande

`--context` fait la même chose que `-n`, pour le contexte : il vaut pour une
commande, sans toucher au contexte actif. C'est la forme à employer dans un
script.

```bash
kubectl --context=kind-boutique get nodes
```

```text
NAME                     STATUS   ROLES           AGE   VERSION
boutique-control-plane   Ready    control-plane   43s   v1.37.0
```

Tapez maintenant un nom de contexte qui n'existe pas, sous les deux formes :

```bash
kubectl --context=xxx get nodes
kubectl config use-context xxx
kubectl config current-context
```

```text
Error in configuration: context was not found for specified context: xxx
error: no context exists with the name: "xxx"
kind-boutique
```

Les deux formes refusent le nom, avec un message différent : apprenez à les
reconnaître. Le contexte actif n'a pas bougé.

## 📚 Exercice 4 : fixer le namespace par défaut du contexte courant

Quand vous passez du temps dans le même namespace, fixez-le sur le contexte
actif plutôt que de répéter `-n`.

```bash
kubectl config set-context --current --namespace=local-path-storage
kubectl config view --minify -o jsonpath='{..namespace}'; echo
kubectl get pods
```

```text
Context "kind-boutique" modified.
local-path-storage
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          33s
```

`kubectl get pods`, sans `-n`, liste maintenant le namespace fixé. Voyez le
piège : kubectl ne vérifie pas que le namespace existe. Faites exprès une faute
de frappe :

```bash
kubectl config set-context --current --namespace=local-path-storag
kubectl get pods
kubectl config get-contexts
```

```text
Context "kind-boutique" modified.
No resources found in local-path-storag namespace.
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique   local-path-storag
          recette         recette         recette
```

La faute est acceptée sans un mot, et la commande suivante répond comme si le
namespace était vide. Quand une ressource semble avoir disparu, regardez d'abord
la colonne `NAMESPACE` : elle montre ici le nom mal tapé.

## 📚 Exercice 5 : créer un contexte, basculer, revenir, le supprimer

Un contexte n'est qu'un nom posé sur un cluster, un utilisateur et un
namespace. Créez `boutique-stockage`, sur le même cluster que `kind-boutique`,
directement dans `local-path-storage`. Basculez dessus, puis revenez.

```bash
kubectl config set-context boutique-stockage \
  --cluster=kind-boutique --user=kind-boutique --namespace=local-path-storage
kubectl config use-context boutique-stockage
kubectl get pods
kubectl config use-context kind-boutique
```

```text
Context "boutique-stockage" created.
Switched to context "boutique-stockage".
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          34s
Switched to context "kind-boutique".
```

`use-context` réécrit `current-context` dans le fichier : la bascule vaut pour
tous vos terminaux. Supprimez maintenant le contexte d'essai :

```bash
kubectl config delete-context boutique-stockage
kubectl config get-contexts
```

```text
deleted context boutique-stockage from /home/ansible/.kube/config
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique   local-path-storag
          recette         recette         recette
```

Supprimer un contexte ne supprime que ce raccourci : le cluster et
l'utilisateur restent dans le fichier. Et `kind-boutique` garde le namespace
mal tapé de l'exercice précédent : on le corrige à l'exercice suivant.

## 📚 Exercice 6 : créer un objet là où le contexte le dit

Remettez le namespace `default` sur le contexte courant, puis créez une
ConfigMap sans nommer ni contexte ni namespace.

```bash
kubectl config set-context --current --namespace=default
kubectl create configmap essai --from-literal=origine=cours
```

```text
Context "kind-boutique" modified.
configmap/essai created
```

Cherchez maintenant où elle a atterri :

```bash
kubectl get configmap essai -n default
kubectl get configmap essai -n local-path-storage
```

```text
NAME    DATA   AGE
essai   1      0s
Error from server (NotFound): configmaps "essai" not found
```

Une commande sans option crée l'objet dans le contexte actif et dans son
namespace par défaut, et nulle part ailleurs. C'est pour cela qu'on vérifie le
contexte avant d'agir.

## 📚 Exercice 7 : protéger un kubeconfig

Un kubeconfig contient de quoi agir sur le cluster avec vos droits. Regardez
l'identité qu'il porte :

```bash
kubectl auth whoami
```

```text
ATTRIBUTE                                           VALUE
Username                                            kubernetes-admin
Groups                                              [kubeadm:cluster-admins system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=8cf552b482997b7b400d7673cd364a6bdb0ef0046946c01837da00bc5cbd3b8e]
```

Le groupe `kubeadm:cluster-admins` donne tous les droits sur le cluster. Un tel
fichier se protège comme une clé SSH. Exercez-vous sur une copie :

```bash
cp ~/.kube/config ~/essai-kubeconfig
ls -l ~/essai-kubeconfig
chmod 600 ~/essai-kubeconfig
ls -l ~/essai-kubeconfig
```

```text
-rw-r--r-- 1 ansible ansible 11119 Nov 19 09:50 /home/ansible/essai-kubeconfig
-rw------- 1 ansible ansible 11119 Nov 19 09:50 /home/ansible/essai-kubeconfig
```

Avant, `-rw-r--r--` : tous les comptes de la machine pouvaient le lire. Après,
`-rw-------` : lecture et écriture pour vous, rien pour les autres.

## 🧹 Nettoyage

Retirez ce que les exercices ont posé et remettez le contexte comme vous l'avez
trouvé :

```bash
kubectl delete configmap essai
kubectl config unset contexts.kind-boutique.namespace
rm ~/essai-kubeconfig
kubectl config get-contexts
```

```text
configmap "essai" deleted from default namespace
Property "contexts.kind-boutique.namespace" unset.
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique
          recette         recette         recette
```

`unset` retire le namespace du contexte : la colonne est de nouveau vide,
comme au départ. Quittez la session et vérifiez :

```bash
exit
dsoxlab check k8s-changer-de-contexte
```

```text
╭─ Résultat : k8s-changer-de-contexte ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests     │
╰──────────────────────────────────────╯
```

Zéro sur quatre : la machine est revenue à l'état de départ du challenge.

## 🎯 Le challenge

Faites maintenant le challenge seul : passer sur la recette, y fixer le bon
namespace, y créer la preuve, et protéger votre kubeconfig.

```bash
dsoxlab run k8s-changer-de-contexte
dsoxlab challenge k8s-changer-de-contexte
```
