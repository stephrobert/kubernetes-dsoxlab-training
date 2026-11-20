# Ranger des applications dans des namespaces

Un cluster accueille souvent plusieurs équipes ou plusieurs applications. Les
**namespaces** les rangent dans des espaces séparés : chaque objet appartient à
un namespace, et deux objets peuvent porter le même nom s'ils sont dans deux
namespaces différents. Mais un namespace ne coupe pas le réseau : un Pod peut
joindre un Service d'un autre namespace, s'il le nomme bien. La leçon montre
ces règles. Ce cours vous fait voir les cas où l'on se trompe : un manifeste
qui atterrit dans le namespace du contexte, un `-n` qui contredit le
manifeste, un nom court qui ne se résout pas, et un namespace qui refuse de
disparaître.

Vous travaillez avec deux namespaces d'essai, `essai-nord` et `essai-sud`. Le
challenge vous demandera de remettre en ordre une autre application : vous le
ferez seul, à la fin.

Page associée : [Namespaces Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/namespaces/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-isoler-par-namespace
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026.

## 📚 Exercice 1 : les namespaces, et celui qu'on vise sans le dire

Listez les namespaces du cluster :

```bash
kubectl get namespaces
```

```text
NAME                 STATUS   AGE
caisse               Active   1s
default              Active   7h14m
kube-node-lease      Active   7h14m
kube-public          Active   7h14m
kube-system          Active   7h14m
local-path-storage   Active   7h14m
stock                Active   1s
```

`default` est le namespace par défaut. Ceux qui commencent par `kube-`
appartiennent à Kubernetes lui-même. `caisse` et `stock` sont ceux du
challenge, posés par la préparation du lab : n'y touchez pas pendant le cours.
Votre liste peut en compter d'autres, laissés par les labs que vous avez déjà
joués.

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
avec une valeur différente. Cherchez-le ensuite sans `-n` :

```bash
kubectl create namespace essai-nord; kubectl create namespace essai-sud
kubectl create configmap reglages --from-literal=region=nord -n essai-nord; kubectl create configmap reglages --from-literal=region=sud -n essai-sud
kubectl get configmap reglages
```

```text
namespace/essai-nord created
namespace/essai-sud created
configmap/reglages created
configmap/reglages created
Error from server (NotFound): configmaps "reglages" not found
```

Deux objets `reglages` coexistent, un par namespace. Sans `-n`, kubectl
cherche dans `default`, où il n'y a rien.

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

## 📚 Exercice 4 : où atterrit un manifeste

Écrivez deux manifestes de ConfigMap. Le premier, `horaires`, ne dit pas de
namespace. Le second, `tarifs`, en dit un dans `metadata.namespace` :
`essai-sud`.

```bash
cat > ~/horaires.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: horaires
data:
  ouverture: "8h"
YAML
cat > ~/tarifs.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: tarifs
  namespace: essai-sud
data:
  ticket: "2 euros"
YAML
```

Réglez le namespace par défaut du contexte sur `essai-nord`, puis appliquez
`horaires` sans `-n`, et regardez où il est créé :

```bash
kubectl config set-context --current --namespace=essai-nord
kubectl apply -f ~/horaires.yaml
kubectl get configmaps -A --field-selector metadata.name=horaires
```

```text
Context "kind-boutique" modified.
configmap/horaires created
NAMESPACE    NAME       DATA   AGE
essai-nord   horaires   1      0s
```

Un manifeste sans namespace atterrit dans celui du contexte. Le même fichier,
appliqué par un collègue dont le contexte vise `default`, créerait l'objet
dans `default`. Appliquez maintenant `tarifs`, toujours sans `-n` :

```bash
kubectl apply -f ~/tarifs.yaml
kubectl get configmaps -A --field-selector metadata.name=tarifs
```

```text
configmap/tarifs created
NAMESPACE   NAME     DATA   AGE
essai-sud   tarifs   1      0s
```

Le namespace écrit dans le manifeste l'emporte sur celui du contexte. Et si
`-n` dit autre chose que le manifeste ?

```bash
kubectl apply -f ~/tarifs.yaml -n essai-nord
```

```text
error: the namespace from the provided object "essai-sud" does not match the namespace "essai-nord". You must pass '--namespace=essai-sud' to perform this operation.
```

kubectl refuse et ne crée rien : il ne choisit pas entre deux namespaces qui se
contredisent. Remettez le contexte sur `default` tout de suite, sinon vos
commandes suivantes agiront dans `essai-nord` :

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

## 📚 Exercice 6 : un namespace qui refuse de disparaître

Supprimer un namespace supprime tout ce qu'il contient. Mais un objet peut
porter un **finalizer** : une marque qui demande à Kubernetes d'attendre avant
de le supprimer, le temps qu'un programme fasse son travail de fin. Tant que la
marque reste, l'objet reste, et son namespace aussi. Posez un finalizer
inventé sur `reglages` d'`essai-nord`, puis supprimez le namespace sans
attendre (`--wait=false`) :

```bash
kubectl patch configmap reglages -n essai-nord --type=merge -p '{"metadata":{"finalizers":["formation.exemple.fr/retenue"]}}'
kubectl delete namespace essai-nord --wait=false
```

```text
configmap/reglages patched
namespace "essai-nord" deleted
```

Kubernetes vide le namespace, puis dit ce qui le bloque dans les conditions du
namespace. La boucle les relit toutes les 5 secondes, 2 minutes au plus,
jusqu'à ce que la condition `NamespaceFinalizersRemaining` passe à `True` :

```bash
debut=$SECONDS; for i in $(seq 1 24); do kubectl get namespace essai-nord -o jsonpath='{.status.conditions[?(@.type=="NamespaceFinalizersRemaining")].status}' | grep -q True && break; sleep 5; done; echo "attente : $((SECONDS - debut)) s"
kubectl get namespace essai-nord
kubectl get all,configmaps -n essai-nord
```

```text
attente : 45 s
NAME         STATUS        AGE
essai-nord   Terminating   51s
NAME                 DATA   AGE
configmap/reglages   1      51s
```

Le namespace reste en `Terminating`, et il ne contient plus que `reglages`. Le
Deployment, le Pod et le Service de `carte` sont partis. Lisez les conditions
du namespace :

```bash
kubectl get namespace essai-nord -o jsonpath='{range .status.conditions[*]}{.type}={.status}: {.message}{"\n"}{end}'
```

```text
NamespaceDeletionDiscoveryFailure=False: All resources successfully discovered
NamespaceDeletionGroupVersionParsingFailure=False: All legacy kube types successfully parsed
NamespaceDeletionContentFailure=False: All content successfully deleted, may be waiting on finalization
NamespaceContentRemaining=True: Some resources are remaining: configmaps. has 1 resource instances
NamespaceFinalizersRemaining=True: Some content in the namespace has finalizers remaining: formation.exemple.fr/retenue in 1 resource instances
```

Les deux dernières lignes nomment la cause : il reste un ConfigMap, retenu par
le finalizer `formation.exemple.fr/retenue`. Ne relisez pas ces conditions trop
tôt : pendant les premières secondes, elles disent encore que tout est
supprimé, alors que le contenu part à peine.

Ici, aucun programme ne viendra retirer ce finalizer : vous l'avez inventé.
Retirez-le vous-même, et le namespace disparaît :

```bash
kubectl patch configmap reglages -n essai-nord --type=merge -p '{"metadata":{"finalizers":null}}'
kubectl wait --for=delete namespace/essai-nord --timeout=60s
```

```text
configmap/reglages patched
namespace/essai-nord condition met
```

Sur un vrai cluster, un finalizer appartient à un programme, souvent un
opérateur. Le retirer à la main saute le travail de fin que ce programme
devait faire. Cherchez d'abord pourquoi il ne l'a pas fait.

## 🧹 Nettoyage

Supprimez les fichiers de travail et le second namespace d'essai :

```bash
rm -f ~/horaires.yaml ~/tarifs.yaml
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

À vous, seul cette fois : une application a été créée dans le mauvais
namespace. Rangez-la dans le bon, puis joignez-la depuis un autre namespace.

```bash
dsoxlab run k8s-isoler-par-namespace
dsoxlab challenge k8s-isoler-par-namespace
```
