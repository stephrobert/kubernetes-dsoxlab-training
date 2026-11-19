# Ranger des applications dans des namespaces

Un cluster accueille souvent plusieurs équipes ou plusieurs applications. Les
**namespaces** les rangent dans des espaces séparés : chaque objet appartient à
un namespace, et deux objets peuvent porter le même nom s'ils sont dans deux
namespaces différents. Mais un namespace ne coupe pas le réseau : un Pod peut
joindre un Service d'un autre namespace, s'il le nomme bien. Dans ce cours,
vous créez deux namespaces, vous y rangez des objets de même nom, vous changez
le namespace visé par défaut, puis vous faites parler deux Pods de part et
d'autre.

Vous travaillez avec deux namespaces d'essai, `essai-nord` et `essai-sud`. Le
challenge vous demandera de ranger une autre application : vous le ferez seul,
à la fin.

Page associée : [Namespaces Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/namespaces/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-isoler-par-namespace
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : les namespaces, et celui qu'on vise sans le dire

Listez les namespaces du cluster :

```bash
kubectl get namespaces
```

```text
NAME                 STATUS   AGE
acces                Active   25m
configuration        Active   14m
default              Active   25m
kube-node-lease      Active   25m
kube-public          Active   25m
kube-system          Active   25m
local-path-storage   Active   25m
```

`default` est le namespace par défaut. Ceux qui commencent par `kube-`
appartiennent à Kubernetes lui-même. Votre liste peut en compter d'autres,
laissés par les labs que vous avez déjà joués, comme `acces` et
`configuration` ici.

Une commande sans `-n` vise le namespace de votre **contexte** kubectl.
Lisez-le :

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo "<- namespace du contexte (vide = default)"
```

```text
<- namespace du contexte (vide = default)
```

Rien avant la flèche : aucun namespace n'est réglé dans le contexte, donc les
commandes sans `-n` visent `default`.

## 📚 Exercice 2 : le même nom dans deux namespaces

Créez les deux namespaces d'essai, puis un ConfigMap `reglages` dans chacun,
avec une valeur différente :

```bash
kubectl create namespace essai-nord; kubectl create namespace essai-sud
kubectl create configmap reglages --from-literal=region=nord -n essai-nord; kubectl create configmap reglages --from-literal=region=sud -n essai-sud
kubectl get configmap reglages -n essai-nord -o jsonpath='{.data.region}{"\n"}'; kubectl get configmap reglages -n essai-sud -o jsonpath='{.data.region}{"\n"}'
```

```text
namespace/essai-nord created
namespace/essai-sud created
configmap/reglages created
configmap/reglages created
nord
sud
```

Deux objets `reglages`, un par namespace, chacun avec sa valeur : un namespace
sépare les **noms**. Sans `-n`, kubectl cherche dans `default`, où il n'y a
rien :

```bash
kubectl get configmap reglages
```

```text
Error from server (NotFound): configmaps "reglages" not found
```

## 📚 Exercice 3 : un namespace, ou tous

`-n` vise un namespace précis :

```bash
kubectl get configmaps -n essai-nord
```

```text
NAME               DATA   AGE
kube-root-ca.crt   1      0s
reglages           1      0s
```

`kube-root-ca.crt` est posé par Kubernetes dans chaque namespace. `-A` (pour
`--all-namespaces`) cherche partout, et ajoute une colonne `NAMESPACE`. Le
filtre ne garde que les objets nommés `reglages` :

```bash
kubectl get configmaps -A --field-selector metadata.name=reglages
```

```text
NAMESPACE    NAME       DATA   AGE
essai-nord   reglages   1      0s
essai-sud    reglages   1      0s
```

## 📚 Exercice 4 : changer le namespace par défaut du contexte

Taper `-n essai-nord` à chaque commande est vite pénible. Vous pouvez régler le
namespace par défaut de votre contexte :

```bash
kubectl config set-context --current --namespace=essai-nord
kubectl get configmap reglages -o jsonpath='{.data.region}{"\n"}'
```

```text
Context "kind-boutique" modified.
nord
```

Sans `-n`, la commande a visé `essai-nord`. C'est pratique, mais trompeur :
oubliez ce réglage, et vos commandes suivantes agiront dans le mauvais
namespace. Remettez `default` tout de suite :

```bash
kubectl config set-context --current --namespace=default
kubectl config view --minify -o jsonpath='{..namespace}{"\n"}'
```

```text
Context "kind-boutique" modified.
default
```

## 📚 Exercice 5 : le réseau traverse les namespaces

Créez une petite application web `carte` dans `essai-nord`, avec son Service,
puis un Pod `visiteur` dans `essai-sud` :

```bash
kubectl create deployment carte --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-nord -- sh -c 'echo carte-du-nord > /tmp/index.html && httpd -f -p 8080 -h /tmp'
kubectl expose deployment carte --port=80 --target-port=8080 -n essai-nord
kubectl run visiteur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-sud -- sleep 3600
kubectl rollout status deployment/carte -n essai-nord --timeout=120s | tail -1; kubectl wait --for=condition=Ready pod/visiteur -n essai-sud --timeout=60s
```

```text
deployment.apps/carte created
service/carte exposed
pod/visiteur created
deployment "carte" successfully rolled out
pod/visiteur condition met
```

Depuis `visiteur`, essayez le nom court du Service, puis son nom suivi du
namespace :

```bash
kubectl exec visiteur -n essai-sud -- wget -qO- -T 3 http://carte
kubectl exec visiteur -n essai-sud -- wget -qO- -T 3 http://carte.essai-nord
```

```text
wget: bad address 'carte'
command terminated with exit code 1
carte-du-nord
```

Le nom court échoue (`bad address` : le nom n'existe pas). Le nom suivi du
namespace répond. Le fichier de résolution des noms du Pod explique pourquoi :

```bash
kubectl exec visiteur -n essai-sud -- cat /etc/resolv.conf
```

```text
search essai-sud.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

La ligne `search` liste les suffixes essayés pour un nom court. Le premier est
`essai-sud.svc.cluster.local` : le nom court `carte` ne se cherche donc que
dans le namespace **du Pod**. Avec `carte.essai-nord`, le suffixe
`svc.cluster.local` complète le nom, et il est trouvé. Le réseau, lui, n'a
jamais été coupé.

## 📚 Exercice 6 : supprimer un namespace supprime tout ce qu'il contient

Regardez ce que contient `essai-nord`, puis supprimez-le :

```bash
kubectl get all -n essai-nord
```

```text
NAME                        READY   STATUS    RESTARTS   AGE
pod/carte-5d5c55866-kbgsf   1/1     Running   0          5s

NAME            TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)   AGE
service/carte   ClusterIP   10.96.56.18   <none>        80/TCP    5s

NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/carte   1/1     1            1           5s

NAME                              DESIRED   CURRENT   READY   AGE
replicaset.apps/carte-5d5c55866   1         1         1       5s
```

```bash
kubectl delete namespace essai-nord
kubectl get all -n essai-nord
```

```text
namespace "essai-nord" deleted
No resources found in essai-nord namespace.
```

Le Pod, le Service, le Deployment et le ReplicaSet sont partis avec le
namespace. C'est pratique pour faire le ménage, et dangereux pour la
même raison : vérifiez toujours le nom avant de supprimer un namespace.

## 🧹 Nettoyage

Supprimez le second namespace d'essai :

```bash
kubectl delete namespace essai-sud
```

```text
namespace "essai-sud" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-isoler-par-namespace
dsoxlab check k8s-isoler-par-namespace
```

```text
╭─ Résultat : k8s-isoler-par-namespace ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests      │
╰───────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : ranger une application et un client dans deux
namespaces, puis constater lequel des deux noms du Service répond.

```bash
dsoxlab run k8s-isoler-par-namespace
dsoxlab challenge k8s-isoler-par-namespace
```
