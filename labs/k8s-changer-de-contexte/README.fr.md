# Changer de contexte et fixer le namespace par défaut

kubectl sait parler à plusieurs clusters. Il trouve leurs adresses et vos
identifiants dans un fichier, `~/.kube/config`, qu'on appelle le
**kubeconfig**. Un **contexte** est une entrée de ce fichier qui dit : tel
cluster, avec tel utilisateur, et éventuellement tel namespace. Un
**namespace** est un espace de rangement à l'intérieur d'un cluster.

La leçon montre les commandes `kubectl config`. Ce cours vous les fait
employer sur deux clusters à la fois, et vous fait diagnostiquer les erreurs
qu'elles produisent : un contexte qui vise un cluster inconnu, un nom de
contexte qui a changé, un kubeconfig copié avec de mauvais droits.

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
13.7, kubectl et clusters en `v1.37.0`) le 20 novembre 2026.

## 📚 Exercice 1 : interroger l'autre cluster sans changer de contexte

Le contexte utilisé est `kind-boutique`. L'option `--context` vise un autre
contexte pour une seule commande. Interrogez le cluster de recette, puis
regardez si le contexte utilisé a changé :

```bash
kubectl config current-context
kubectl --context=recette get nodes
kubectl config current-context
```

```text
kind-boutique
NAME                STATUS   ROLES           AGE   VERSION
lab-control-plane   Ready    control-plane   63s   v1.37.0
kind-boutique
```

Le nœud affiché, `lab-control-plane`, appartient au cluster de recette.
Pourtant le contexte utilisé reste `kind-boutique`. `--context` ne modifie
pas le kubeconfig : c'est l'option à employer dans un script, qui ne doit pas
dépendre de l'état du fichier.

## 📚 Exercice 2 : voir que `-n` l'emporte sur le namespace du contexte

Fixez `local-path-storage` comme namespace par défaut du contexte utilisé,
puis listez les Pods avec et sans `-n` :

```bash
kubectl config set-context --current --namespace=local-path-storage
kubectl get pods
kubectl get pods -n kube-system -o name | head -3
kubectl config view --minify -o jsonpath='{..namespace}'; echo
```

```text
Context "kind-boutique" modified.
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-h65dp   1/1     Running   0          15s
pod/coredns-559f6c778d-jwhr5
pod/coredns-559f6c778d-sz6ll
pod/etcd-boutique-control-plane
local-path-storage
```

Sans `-n`, kubectl travaille dans le namespace du contexte. Avec `-n`, il
travaille dans celui que vous donnez, pour cette commande seulement. La
dernière ligne montre que le namespace du contexte n'a pas bougé.

## 📚 Exercice 3 : créer un objet sans préciser où, puis le chercher

C'est le geste du challenge, sur un autre cluster et un autre namespace.
Créez une **ConfigMap**, un petit objet qui stocke des réglages, sans
`--context` ni `-n`, puis demandez où elle se trouve :

```bash
kubectl create configmap essai-ici --from-literal=origine=cours
kubectl get configmap essai-ici -o jsonpath='{.metadata.namespace}{"\n"}'
```

```text
configmap/essai-ici created
local-path-storage
```

Elle est dans `local-path-storage`, le namespace du contexte utilisé.
Cherchez-la maintenant sur l'autre cluster, dans le même namespace :

```bash
kubectl --context=recette get configmap essai-ici -n local-path-storage
```

```text
Error from server (NotFound): configmaps "essai-ici" not found
```

Le cluster de recette a lui aussi un namespace `local-path-storage`, mais la
ConfigMap n'y est pas. Deux clusters ne partagent rien : un objet n'existe que
sur le cluster où il a été créé. Remettez le namespace `default` sur votre
contexte :

```bash
kubectl config set-context --current --namespace=default
```

```text
Context "kind-boutique" modified.
```

## 📚 Exercice 4 : diagnostiquer un contexte qui vise un cluster inconnu

Un contexte associe un cluster et un utilisateur par leurs noms. Créez-en un,
`casse`, avec une faute de frappe dans le nom du cluster (`kind-boutiqe`), et
utilisez-le :

```bash
kubectl config set-context casse --cluster=kind-boutiqe --user=kind-boutique
kubectl --context=casse get nodes
```

```text title="Extrait de la sortie"
Context "casse" created.
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

kubectl a créé le contexte sans vérifier que le cluster existe. Ensuite, il
n'a trouvé aucune adresse pour `kind-boutiqe` et il s'est rabattu sur
`localhost:8080`, où rien n'écoute. Plusieurs lignes `memcache.go` précèdent
ce message et disent la même chose. Le message ne cite pas la faute : il faut
la trouver en comparant les noms.

```bash
kubectl config get-clusters
kubectl config get-contexts casse
```

```text
NAME
kind-boutique
recette
CURRENT   NAME    CLUSTER        AUTHINFO        NAMESPACE
          casse   kind-boutiqe   kind-boutique
```

La colonne `CLUSTER` du contexte cite `kind-boutiqe`, absent de la liste des
clusters. Supprimez ce contexte :

```bash
kubectl config delete-context casse
```

```text
deleted context casse from /home/ansible/.kube/config
```

## 📚 Exercice 5 : changer de contexte dans un seul terminal

`kubectl config use-context` écrit dans `~/.kube/config`. Le changement vaut
donc pour tous vos terminaux. La variable `KUBECONFIG` indique à kubectl un
autre fichier : un changement fait dans ce fichier ne touche pas les autres
terminaux. Travaillez sur une copie :

```bash
cp ~/.kube/config ~/essai-kubeconfig
chmod 600 ~/essai-kubeconfig
KUBECONFIG=~/essai-kubeconfig kubectl config use-context recette
KUBECONFIG=~/essai-kubeconfig kubectl config current-context
kubectl config current-context
```

```text
Switched to context "recette".
recette
kind-boutique
```

La copie utilise `recette`. Votre `~/.kube/config` utilise toujours
`kind-boutique`. Dans un terminal où vous lancez
`export KUBECONFIG=~/essai-kubeconfig`, toutes les commandes kubectl suivantes
liront la copie, jusqu'à la fermeture du terminal.

## 📚 Exercice 6 : renommer un contexte

Un nom de contexte apparaît dans vos commandes et vos scripts. Renommez
`recette` dans la copie, puis lancez une commande qui utilise l'ancien nom :

```bash
KUBECONFIG=~/essai-kubeconfig kubectl config rename-context recette recette-essai
KUBECONFIG=~/essai-kubeconfig kubectl --context=recette get nodes
KUBECONFIG=~/essai-kubeconfig kubectl config get-contexts
```

```text
Context "recette" renamed to "recette-essai".
Error in configuration: context was not found for specified context: recette
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
          kind-boutique   kind-boutique   kind-boutique   default
*         recette-essai   recette         recette
```

Seul le nom du contexte a changé : il vise toujours le cluster `recette` et
l'utilisateur `recette`, et il reste le contexte utilisé de la copie. Tout
script qui écrivait `--context=recette` échoue maintenant. Ce message
`context was not found` est celui d'une faute de frappe : quand vous le voyez,
listez les contextes. Supprimez la copie :

```bash
rm ~/essai-kubeconfig
```

## 📚 Exercice 7 : voir ce qui protège vraiment le kubeconfig

Regardez les droits du fichier, et ceux des deux répertoires qui le
contiennent :

```bash
ls -ld ~ ~/.kube ~/.kube/config
```

```text
drwx------ 15 ansible ansible  4096 Nov 20 07:02 /home/ansible
drwx------  3 ansible ansible  4096 Nov 20 07:02 /home/ansible/.kube
-rw-r--r--  1 ansible ansible 11119 Nov 20 07:02 /home/ansible/.kube/config
```

Le fichier est en `-rw-r--r--` : ses droits permettent à tout compte de le
lire. Mais les deux répertoires sont en `drwx------`, et un autre compte ne
peut pas les traverser. Vérifiez-le avec le compte `nobody`, qui n'a aucun
droit particulier :

```bash
sudo -u nobody head -1 ~/.kube/config
```

```text
head: cannot open '/home/ansible/.kube/config' for reading: Permission denied
```

Aujourd'hui, ce sont les répertoires qui protègent le fichier. Cette
protection disparaît dès que le fichier est copié ailleurs, car la copie garde
ses droits. Copiez-le dans `/tmp`, un répertoire que tous les comptes
traversent, et cherchez-y les clés privées avec le compte `nobody` :

```bash
cp ~/.kube/config /tmp/essai-kubeconfig
ls -l /tmp/essai-kubeconfig
sudo -u nobody grep -c client-key-data /tmp/essai-kubeconfig
```

```text
-rw-r--r-- 1 ansible ansible 11119 Nov 20 07:02 /tmp/essai-kubeconfig
2
```

`nobody` lit la copie : elle contient deux clés privées, une par cluster. Avec
elles, n'importe qui agit sur les deux clusters avec vos droits. Corrigez les
droits de la copie, puis recommencez :

```bash
chmod 600 /tmp/essai-kubeconfig
sudo -u nobody grep -c client-key-data /tmp/essai-kubeconfig
rm /tmp/essai-kubeconfig
```

```text
grep: /tmp/essai-kubeconfig: Permission denied
```

Avec `-rw-------`, le fichier se protège lui-même, où qu'il soit copié.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : la ConfigMap
`essai-ici`. Les copies du kubeconfig sont déjà supprimées.

```bash
kubectl delete configmap essai-ici -n local-path-storage
kubectl config get-contexts
```

```text
configmap "essai-ici" deleted from local-path-storage namespace
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique   default
          recette         recette         recette
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
