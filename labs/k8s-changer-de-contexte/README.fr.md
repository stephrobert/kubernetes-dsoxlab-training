# Changer de contexte et fixer le namespace par défaut

kubectl sait parler à plusieurs clusters. Il trouve leurs adresses et vos
identifiants dans un fichier, `~/.kube/config`, qu'on appelle le
**kubeconfig**. Un **contexte** est une entrée de ce fichier qui dit : tel
cluster, avec tel utilisateur, et éventuellement tel namespace. Un
**namespace** est un espace de rangement à l'intérieur d'un cluster.

Dans ce cours, vous refaites les gestes de la leçon : voir quel contexte est
utilisé, en viser un autre le temps d'une commande, fixer le namespace par
défaut, créer et supprimer un contexte, créer un objet au bon endroit, et
protéger un kubeconfig.

Vous travaillez sur le contexte `kind-boutique` et sur des objets d'essai. Le
challenge vous demandera de passer sur `recette` : vous le ferez seul, à la
fin.

Page associée : [kubeconfig et contextes kubectl](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-contexte/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-changer-de-contexte
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Deux clusters y
tournent. Votre kubeconfig connaît deux contextes : `kind-boutique`, utilisé
en ce moment, et `recette`.

Les sorties montrées dans ce cours ont été relevées sur cette machine (Debian
13.7, kubectl et clusters en `v1.37.0`) le 19 novembre 2026.

## 📚 Exercice 1 : voir quel contexte est utilisé

Avant de modifier quoi que ce soit, regardez quel cluster vous visez. Listez
les contextes, puis affichez seulement celui qui est utilisé :

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

L'étoile montre le contexte utilisé : `kind-boutique`. La colonne `NAMESPACE`
est vide : aucun namespace n'est fixé, donc kubectl travaille dans le namespace
`default`. Vous pouvez le vérifier ainsi :

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo
```

La commande affiche une ligne vide : aucun namespace n'est fixé.

## 📚 Exercice 2 : viser un autre namespace le temps d'une commande

Listez les Pods sans option, puis dans le namespace `local-path-storage` :

```bash
kubectl get pods
kubectl get pods -n local-path-storage
```

```text
No resources found in default namespace.
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          33s
```

Le namespace `default` est vide. L'option `-n` vise un autre namespace, pour
cette commande seulement : elle ne change rien dans le kubeconfig.

## 📚 Exercice 3 : viser un autre contexte le temps d'une commande

L'option `--context` fait la même chose pour le contexte : elle vaut pour une
seule commande, sans changer le contexte utilisé. C'est la bonne façon de faire
dans un script.

```bash
kubectl --context=kind-boutique get nodes
```

```text
NAME                     STATUS   ROLES           AGE   VERSION
boutique-control-plane   Ready    control-plane   43s   v1.37.0
```

Tapez maintenant un nom de contexte qui n'existe pas, de deux façons :

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

Les deux commandes refusent le nom, chacune avec son message : apprenez à les
reconnaître. Le contexte utilisé n'a pas changé.

## 📚 Exercice 4 : fixer le namespace par défaut

Si vous travaillez longtemps dans le même namespace, fixez-le sur le contexte
utilisé. Vous n'aurez plus à taper `-n` :

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

Sans `-n`, `kubectl get pods` liste maintenant le namespace que vous avez
fixé.

Attention à un piège : kubectl ne vérifie pas que le namespace existe. Faites
exprès une faute de frappe :

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

kubectl accepte le nom mal tapé sans rien dire, et la commande suivante répond
comme si le namespace était vide. Si un objet semble avoir disparu, regardez
d'abord la colonne `NAMESPACE` : ici, elle montre la faute.

## 📚 Exercice 5 : créer un contexte, l'utiliser, puis le supprimer

Créez un contexte `boutique-stockage`. Il vise le même cluster que
`kind-boutique`, avec le même utilisateur, mais directement dans le namespace
`local-path-storage`. Passez dessus, puis revenez :

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

`use-context` enregistre le changement dans le kubeconfig. Il vaut donc pour
tous vos terminaux en même temps. Supprimez ensuite le contexte d'essai :

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

Supprimer un contexte ne supprime ni le cluster ni l'utilisateur : seulement
l'entrée. Remarquez que `kind-boutique` garde la faute de frappe de l'exercice
4 : vous la corrigez à l'exercice suivant.

## 📚 Exercice 6 : créer un objet au bon endroit

Remettez le namespace `default` sur le contexte utilisé. Créez ensuite une
**ConfigMap**, un petit objet qui stocke des réglages, sans préciser ni
contexte ni namespace :

```bash
kubectl config set-context --current --namespace=default
kubectl create configmap essai --from-literal=origine=cours
```

```text
Context "kind-boutique" modified.
configmap/essai created
```

Cherchez où elle a été créée :

```bash
kubectl get configmap essai -n default
kubectl get configmap essai -n local-path-storage
```

```text
NAME    DATA   AGE
essai   1      0s
Error from server (NotFound): configmaps "essai" not found
```

Sans option, kubectl crée l'objet dans le contexte utilisé et dans son
namespace par défaut, et nulle part ailleurs. C'est pour cela qu'on vérifie le
contexte avant d'agir.

## 📚 Exercice 7 : protéger un kubeconfig

Un kubeconfig contient de quoi agir sur le cluster avec vos droits. Regardez
quelle identité il vous donne :

```bash
kubectl auth whoami
```

```text
ATTRIBUTE                                           VALUE
Username                                            kubernetes-admin
Groups                                              [kubeadm:cluster-admins system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=8cf552b482997b7b400d7673cd364a6bdb0ef0046946c01837da00bc5cbd3b8e]
```

Le groupe `kubeadm:cluster-admins` donne tous les droits sur le cluster. Ce
fichier se protège donc comme un mot de passe : vous seul devez pouvoir le
lire. Entraînez-vous sur une copie :

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

Avant, `-rw-r--r--` : tous les comptes de la machine pouvaient lire le
fichier. Après `chmod 600`, `-rw-------` : vous seul pouvez le lire et le
modifier.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : la ConfigMap `essai` et la copie du kubeconfig.

```bash
kubectl delete configmap essai
rm ~/essai-kubeconfig
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-changer-de-contexte
dsoxlab check k8s-changer-de-contexte
```

```text
╭─ Résultat : k8s-changer-de-contexte ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests     │
╰──────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : passer sur le cluster de recette, y fixer le bon
namespace, y créer la ConfigMap demandée, et protéger votre kubeconfig.

```bash
dsoxlab run k8s-changer-de-contexte
dsoxlab challenge k8s-changer-de-contexte
```
