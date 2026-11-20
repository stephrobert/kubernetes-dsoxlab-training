# Créer un cluster kind multi-nœuds

kind crée un cluster Kubernetes sur votre machine. Chaque machine du cluster,
qu'on appelle un **nœud**, y est un conteneur Docker. La leçon montre comment
créer, arrêter et supprimer un cluster. Ce cours vous fait rencontrer les
erreurs de kind et de kubectl qu'elle ne montre pas, et la panne d'un nœud.

Vous travaillez sur des clusters d'essai, `kind`, `essai`, `duo` et `faux`. Le challenge vous
demandera un autre cluster, `atelier` : vous le ferez seul, à la fin.

Page associée : [Créer votre premier cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-cluster/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-creer-un-cluster-kind
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Docker, kind et
kubectl y sont installés. Le lab a installé kind pour vous : la leçon montre
comment le faire en vérifiant son empreinte. Pour vous laisser assez de
mémoire, le lab a supprimé les clusters des autres labs : aucun cluster ne
tourne. Le répertoire `~/atelier/` du challenge est vide.

Les sorties montrées dans ce cours ont été relevées sur cette machine (Debian
13.7, 4 Go de mémoire, kind `v0.33.0`, Docker `29.9.3`) le 20 novembre 2026.

## 📚 Exercice 1 : créer un cluster sans nom ni image

La leçon donne toujours `--name` et `--image`. Voyez ce que kind fait quand
vous les oubliez :

```bash
kind create cluster
```

```text title="Extrait de la sortie"
Creating cluster "kind" ...
Set kubectl context to "kind-kind"
```

Sans `--name`, le cluster s'appelle `kind`, et le contexte de kubectl
`kind-kind`. Entre ces deux lignes, kind affiche ses étapes. L'une d'elles,
`Ensuring node image (kindest/node:v1.37.0)`, nomme l'image du nœud. Sans
`--image`, kind prend l'image fixée à la construction du binaire kind.
Regardez-la :

```bash
docker ps --format "table {{.Names}}\t{{.Image}}"
```

```text
NAMES                IMAGE
kind-control-plane   kindest/node:v1.37.0
```

Avec ce kind `v0.33.0`, c'est `kindest/node:v1.37.0`, sans digest. La version
tombe juste ici, mais par hasard : un autre binaire kind aurait donné une
autre version de Kubernetes. Et sans digest, le nom `v1.37.0` peut désigner une
autre image le jour où elle est republiée. Supprimez ce cluster :

```bash
kind delete cluster
```

```text
Deleting cluster "kind" ...
Deleted nodes: ["kind-control-plane"]
```

Sans `--name`, `kind delete cluster` vise lui aussi le cluster `kind`, et le
supprime sans demander de confirmation.

## 📚 Exercice 2 : créer un cluster dont le nom est déjà pris

Créez le cluster `essai` comme le fait la leçon, avec son nom et son image
épinglée par digest. Puis relancez exactement la même commande :

```bash
kind create cluster --name essai \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
kind create cluster --name essai \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

```text title="Fin de la sortie"
ERROR: failed to create cluster: node(s) already exist for a cluster with the name "essai"
```

La première commande crée le cluster. La seconde refuse : kind ne remplace
jamais un cluster existant. Pour repartir de zéro, il faut d'abord
`kind delete cluster --name essai`. Gardez `essai` : il sert à l'exercice
suivant.

## 📚 Exercice 3 : vérifier ce qui survit à un arrêt

La leçon affirme qu'un cluster arrêté par `docker stop` garde ses objets.
Vérifiez-le. Créez d'abord un objet témoin : un **ConfigMap**, un petit objet
qui stocke des réglages. Relevez son **UID**, l'identifiant unique que
Kubernetes lui donne à sa création :

```bash
kubectl create configmap temoin --from-literal=couleur=vert
kubectl get configmap temoin -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
configmap/temoin created
30183449-6477-45af-abeb-ff7b1b4a3a42
```

Arrêtez le nœud d'`essai`, puis relancez-le :

```bash
docker stop $(docker ps -q --filter "name=essai-")
docker start $(docker ps -aq --filter "name=essai-")
kubectl wait --for=condition=Ready nodes --all --timeout=120s
```

```text
8e98c8e38245
8e98c8e38245
Error from server (Forbidden): nodes is forbidden: User "kubernetes-admin" cannot list resource "nodes" in API group "" at the cluster scope
```

Le refus `Forbidden` est passager. Le serveur d'API vient de redémarrer : il
répond déjà, mais il n'a pas encore chargé les règles qui disent qui a le droit
de faire quoi. Selon le moment, vous pouvez aussi voir `connection refused`.
Attendez quelques secondes, relancez `kubectl wait`, puis relisez le témoin :

```bash
kubectl get configmap temoin -o jsonpath='{.metadata.uid} {.data.couleur}{"\n"}'
```

```text
30183449-6477-45af-abeb-ff7b1b4a3a42 vert
```

Même UID, même valeur : c'est le même objet, il n'a pas été recréé. Les
données du cluster vivent dans le conteneur du nœud, et `docker stop` ne
supprime pas le conteneur.

## 📚 Exercice 4 : lire l'erreur d'un fichier de configuration

Un cluster de plusieurs nœuds se décrit dans un fichier. Écrivez
`~/essai/kind-duo.yaml` pour un control plane et un **worker**, le nœud qui
fait tourner les applications. Glissez-y une faute : `Worker` avec une
majuscule.

```bash
mkdir -p ~/essai
cat > ~/essai/kind-duo.yaml <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
  - role: Worker
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
EOF
kind create cluster --name duo --config ~/essai/kind-duo.yaml
kind get clusters
```

```text
ERROR: failed to create cluster: invalid configuration for node 1: "Worker" is not a valid node role
essai
```

kind lit le fichier avant de créer quoi que ce soit. Il nomme le nœud fautif
par sa position dans la liste, en comptant à partir de 0 : le nœud 1 est le
second. Aucun cluster `duo` n'a été créé. Corrigez la faute :

```bash
sed -i "s/role: Worker/role: worker/" ~/essai/kind-duo.yaml
grep role ~/essai/kind-duo.yaml
```

```text
  - role: control-plane
  - role: worker
```

## 📚 Exercice 5 : mettre l'image dans le fichier

Votre fichier donne l'image de chaque nœud avec `image:`. Vous n'avez donc plus
besoin de `--image`. Créez `duo` avec le seul fichier :

```bash
kind create cluster --name duo --config ~/essai/kind-duo.yaml
docker ps --filter "name=duo-" --format "table {{.Names}}\t{{.Image}}"
```

```text title="Extrait de la sortie"
Creating cluster "duo" ...
Set kubectl context to "kind-duo"
NAMES               IMAGE
duo-worker          kindest/node:v1.37.0
duo-control-plane   kindest/node:v1.37.0
```

Pendant la création, l'étape `Joining worker nodes` rattache le worker au
control plane. Les deux nœuds tournent sur l'image du fichier. Si vous donnez
aussi `--image`, c'est elle qui l'emporte, pour tous les nœuds. Vérifiez-le
avec un fichier qui cite une image qui n'existe pas :

```bash
cat > ~/essai/kind-faux.yaml <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    image: kindest/node:v0.0.0-image-qui-n-existe-pas
EOF
kind create cluster --name faux --config ~/essai/kind-faux.yaml \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
docker ps --filter "name=faux-" --format "{{.Image}}"
kind delete cluster --name faux
kubectl config use-context kind-duo
```

```text title="Extrait de la sortie"
kindest/node:v1.37.0
Deleting cluster "faux" ...
Switched to context "kind-duo".
```

Le cluster `faux` a démarré sur l'image de `--image` : celle du fichier n'a
jamais été téléchargée. Les deux façons sont donc valables : l'image dans la
commande, ou nœud par nœud dans le fichier.

## 📚 Exercice 6 : voir un worker tomber

Arrêtez le conteneur du worker de `duo`, comme une panne de machine. Attendez
une minute, puis regardez les nœuds :

```bash
docker stop duo-worker
sleep 60
kubectl get nodes
```

```text
duo-worker
NAME                STATUS     ROLES           AGE   VERSION
duo-control-plane   Ready      control-plane   87s   v1.37.0
duo-worker          NotReady   <none>          77s   v1.37.0
```

Le nœud n'est pas `NotReady` tout de suite : sur cette machine, il l'est devenu
au bout de 55 secondes environ. Lisez pourquoi :

```bash
kubectl describe node duo-worker | grep -A6 "^Conditions"
```

```text
Conditions:
  Type             Status    LastHeartbeatTime                 LastTransitionTime                Reason              Message
  ----             ------    -----------------                 ------------------                ------              -------
  MemoryPressure   Unknown   Fri, 20 Nov 2026 06:53:13 +0000   Fri, 20 Nov 2026 06:54:13 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
  DiskPressure     Unknown   Fri, 20 Nov 2026 06:53:13 +0000   Fri, 20 Nov 2026 06:54:13 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
  PIDPressure      Unknown   Fri, 20 Nov 2026 06:53:13 +0000   Fri, 20 Nov 2026 06:54:13 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
  Ready            Unknown   Fri, 20 Nov 2026 06:53:13 +0000   Fri, 20 Nov 2026 06:54:13 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
```

Le **kubelet** est le programme qui tourne sur chaque nœud et donne de ses
nouvelles au control plane. Son dernier message (`LastHeartbeatTime`) date de
06:53:13. Une minute plus tard (`LastTransitionTime`), sans nouvelles, le
control plane a passé toutes les conditions à `Unknown`. Il ne sait pas ce
qu'est devenu le nœud : il sait seulement qu'il ne répond plus. Relancez le
worker :

```bash
docker start duo-worker
kubectl wait --for=condition=Ready node/duo-worker --timeout=120s
```

```text
duo-worker
node/duo-worker condition met
```

## 📚 Exercice 7 : supprimer le cluster sur lequel on travaille

Le contexte actif est `kind-duo`. Supprimez ce cluster, puis lancez une
commande kubectl :

```bash
kubectl config current-context
kind delete cluster --name duo
kubectl config current-context
kubectl get nodes
```

```text title="Extrait de la sortie"
kind-duo
Deleting cluster "duo" ...
Deleted nodes: ["duo-worker" "duo-control-plane"]
error: current-context is not set
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

kind a retiré le contexte `kind-duo` avec le cluster. kubectl n'a plus de
contexte actif, et il se rabat sur une adresse par défaut, `localhost:8080`,
où rien n'écoute. Plusieurs lignes `memcache.go` précèdent ce message : elles
disent la même chose. Un message qui cite `localhost:8080` signale donc un
kubectl sans contexte actif, même si vos clusters tournent. Choisissez-en un :

```bash
kubectl config get-contexts
kubectl config use-context kind-essai
kubectl get configmap temoin
```

```text
CURRENT   NAME         CLUSTER      AUTHINFO     NAMESPACE
          kind-essai   kind-essai   kind-essai
Switched to context "kind-essai".
NAME     DATA   AGE
temoin   1      114s
```

Aucune étoile dans la colonne `CURRENT` : aucun contexte n'était actif. Après
`use-context`, kubectl retrouve `essai` et son témoin.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le cluster
`essai` et le répertoire `~/essai`.

```bash
kind delete cluster --name essai
rm -r ~/essai
kind get clusters
```

```text
Deleting cluster "essai" ...
Deleted nodes: ["essai-control-plane"]
No kind clusters found.
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-creer-un-cluster-kind
dsoxlab check k8s-creer-un-cluster-kind
```

```text
╭─ Résultat : k8s-creer-un-cluster-kind ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests       │
╰────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : créer le cluster `atelier`, décrit dans son propre
fichier, avec un control plane et deux workers.

```bash
dsoxlab run k8s-creer-un-cluster-kind
dsoxlab challenge k8s-creer-un-cluster-kind
```
