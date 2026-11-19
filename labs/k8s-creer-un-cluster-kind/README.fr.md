# Créer un cluster kind multi-nœuds

kind est un outil qui crée un cluster Kubernetes sur votre machine. Chaque
machine du cluster, qu'on appelle un **nœud**, y est un simple conteneur
Docker. Dans ce cours, vous refaites les gestes de la leçon : créer un cluster,
voir ce que kind a créé, vérifier qu'il est prêt, l'arrêter, le décrire dans un
fichier, passer d'un cluster à l'autre, puis les supprimer.

Vous travaillez sur deux clusters d'essai, `essai` et `duo`. Le challenge vous
demandera un autre cluster, `atelier` : vous le ferez seul, à la fin.

Page associée : [Créer votre premier cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-cluster/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-creer-un-cluster-kind
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Docker, kind et
kubectl y sont installés. Pour vous laisser assez de mémoire, le lab a supprimé
les clusters des autres labs : aucun cluster ne tourne. Le répertoire
`~/atelier/` du challenge est vide.

Les sorties montrées dans ce cours ont été relevées sur cette machine (Debian
13.7, 4 Go de mémoire, kind `v0.33.0`, Docker `29.9.3`) le 19 novembre 2026.

## 📚 Exercice 1 : créer un cluster d'un seul nœud

Créez un cluster nommé `essai`. L'option `--image` choisit l'image du nœud,
et donc la version de Kubernetes. La partie `@sha256:...` est le **digest** de
l'image : il garantit que vous recevez exactement l'image prévue, même si
quelqu'un republie une image sous le même nom.

```bash
kind create cluster --name essai \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

```text title="Extrait de la sortie"
Creating cluster "essai" ...
Set kubectl context to "kind-essai"
You can now use your cluster with:

kubectl cluster-info --context kind-essai
```

Entre ces lignes, kind affiche ses étapes une par une, avec des petits
dessins. Regardez la ligne `Set kubectl context` : kind a réglé kubectl pour
qu'il parle à ce nouveau cluster. On dit que kubectl utilise le **contexte**
`kind-essai`.

## 📚 Exercice 2 : voir ce que kind a créé

Un nœud kind est un conteneur Docker. Listez les conteneurs dont le nom
contient `essai`, puis demandez à kind la liste de ses clusters :

```bash
docker ps --filter "name=essai" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
kind get clusters
```

```text
NAMES                 IMAGE                  STATUS
essai-control-plane   kindest/node:v1.37.0   Up 9 seconds
essai
```

Un seul conteneur, `essai-control-plane`. Le **control plane** est le nœud qui
dirige le cluster. Dans un cluster d'un seul nœud, il fait aussi tourner vos
applications.

## 📚 Exercice 3 : vérifier que le cluster est prêt

Un cluster qui répond n'est pas forcément prêt à travailler. Vérifiez d'abord
que kubectl vise bien `essai`, puis attendez que le nœud soit prêt avant de
l'afficher :

```bash
kubectl config current-context
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes
```

```text
kind-essai
node/essai-control-plane condition met
NAME                  STATUS   ROLES           AGE   VERSION
essai-control-plane   Ready    control-plane   20s   v1.37.0
```

`kubectl wait` attend que tous les nœuds soient `Ready`, puis rend la main.
La colonne `VERSION` affiche `v1.37.0` : c'est la version de l'image que vous
avez choisie.

Listez maintenant les programmes que Kubernetes fait tourner pour lui-même :

```bash
kubectl get pods -A
```

```text
NAMESPACE            NAME                                          READY   STATUS    RESTARTS   AGE
kube-system          coredns-559f6c778d-lpbgw                      1/1     Running   0          13s
kube-system          coredns-559f6c778d-mqndf                      1/1     Running   0          13s
kube-system          etcd-essai-control-plane                      1/1     Running   0          19s
kube-system          kindnet-vnpfq                                 1/1     Running   0          13s
kube-system          kube-apiserver-essai-control-plane            1/1     Running   0          19s
kube-system          kube-controller-manager-essai-control-plane   1/1     Running   0          19s
kube-system          kube-proxy-4dpvs                              1/1     Running   0          13s
kube-system          kube-scheduler-essai-control-plane            1/1     Running   0          19s
local-path-storage   local-path-provisioner-75f7fc7dc5-cj7dr       1/1     Running   0          13s
```

Vous n'avez encore rien déployé, et pourtant neuf programmes tournent : ce sont
les composants du cluster lui-même (base de données, réseau, noms, stockage).
Ils doivent tous être `Running`. Juste après la création, certains peuvent
encore afficher `ContainerCreating` : attendez quelques secondes et relancez la
commande.

## 📚 Exercice 4 : arrêter le cluster, puis le relancer

kind n'a pas de commande pour arrêter un cluster. Mais comme un nœud est un
conteneur, Docker peut l'arrêter. Arrêtez le nœud d'`essai`, puis interrogez le
cluster :

```bash
docker stop $(docker ps -q --filter "name=essai-")
kubectl get nodes
```

```text
e8568b1489b6
The connection to the server 127.0.0.1:45357 was refused - did you specify the right host or port?
```

Plus rien ne répond. Retenez ce message : vous le verrez chaque fois qu'un
cluster est arrêté, ou que kubectl vise le mauvais cluster. Relancez le nœud et
attendez qu'il soit prêt :

```bash
docker start $(docker ps -aq --filter "name=essai-")
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes
```

```text
e8568b1489b6
node/essai-control-plane condition met
NAME                  STATUS   ROLES           AGE   VERSION
essai-control-plane   Ready    control-plane   38s   v1.37.0
```

Le nœud est de nouveau `Ready`. Son âge (`AGE`) a continué d'augmenter : rien
n'a été recréé. Arrêter un cluster libère de la mémoire sans rien perdre.

## 📚 Exercice 5 : décrire un cluster dans un fichier

Pour un cluster de plusieurs nœuds, kind a besoin d'un fichier qui décrit les
nœuds. Écrivez `~/essai/kind-duo.yaml` : un control plane et un **worker**, un
nœud qui fait tourner les applications. Le worker reçoit une étiquette de
**zone**, comme dans un vrai centre de données.

```bash
mkdir -p ~/essai
cat > ~/essai/kind-duo.yaml <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
    labels:
      topology.kubernetes.io/zone: zone-a
EOF
```

Chaque élément de la liste `nodes` est un nœud, et `role` dit lequel. L'image
ne se met pas dans ce fichier : elle se donne à la commande, avec le nom du
cluster et le chemin du fichier.

```bash
kind create cluster --name duo \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5 \
  --config ~/essai/kind-duo.yaml
```

```text title="Extrait de la sortie"
Creating cluster "duo" ...
Set kubectl context to "kind-duo"
```

Une étape s'ajoute à celles de l'exercice 1 : `Joining worker nodes`, pendant
laquelle le worker rejoint le control plane. Attendez les deux nœuds, puis
affichez-les avec leur zone :

```bash
kubectl wait --for=condition=Ready nodes --all --timeout=180s
kubectl get nodes -L topology.kubernetes.io/zone
```

```text
node/duo-control-plane condition met
node/duo-worker condition met
NAME                STATUS   ROLES           AGE   VERSION   ZONE
duo-control-plane   Ready    control-plane   27s   v1.37.0
duo-worker          Ready    <none>          13s   v1.37.0   zone-a
```

Le worker porte bien la zone écrite dans le fichier. Sa colonne `ROLES` affiche
`<none>` : c'est normal, Kubernetes n'écrit le rôle que sur le control plane.

## 📚 Exercice 6 : passer d'un cluster à l'autre

Deux clusters tournent maintenant, mais kubectl ne parle qu'à un seul à la
fois. Listez les contextes, puis revenez sur `essai` :

```bash
kubectl config get-contexts
kubectl config use-context kind-essai
kubectl get nodes
```

```text
CURRENT   NAME         CLUSTER      AUTHINFO     NAMESPACE
*         kind-duo     kind-duo     kind-duo
          kind-essai   kind-essai   kind-essai
Switched to context "kind-essai".
NAME                  STATUS   ROLES           AGE   VERSION
essai-control-plane   Ready    control-plane   75s   v1.37.0
```

L'étoile montre le contexte utilisé : c'était `kind-duo`, le dernier cluster
créé. Après `use-context`, `kubectl get nodes` montre bien le nœud d'`essai`.
Prenez l'habitude de vérifier le contexte avant d'agir : c'est ce qui évite de
travailler sur le mauvais cluster.

## 📚 Exercice 7 : supprimer un cluster

La suppression est définitive, et kind ne demande pas de confirmation. Relisez
le nom avant de valider.

```bash
kind delete cluster --name duo
kubectl config get-contexts
```

```text
Deleting cluster "duo" ...
Deleted nodes: ["duo-control-plane" "duo-worker"]
CURRENT   NAME         CLUSTER      AUTHINFO     NAMESPACE
*         kind-essai   kind-essai   kind-essai
```

Le contexte `kind-duo` a disparu en même temps que le cluster. Il ne reste
qu'`essai`.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le cluster `essai` et le répertoire `~/essai`.

```bash
kind delete cluster --name essai
rm -r ~/essai
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
