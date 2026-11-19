# Créer un cluster kind multi-nœuds

Ce cours vous fait pratiquer, sur la machine du lab, chaque geste de la leçon :
créer un cluster kind sur une image épinglée, voir ce qu'il a posé, vérifier
qu'il est prêt, l'arrêter et le relancer, le décrire dans un fichier,
travailler avec deux clusters, puis les supprimer. Vous travaillez sur deux
clusters d'essai, `essai` et `duo` : le cluster `atelier` du challenge reste à
faire à la fin.

Page associée : [Créer votre premier cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-cluster/).

## 🔧 Avant de commencer

```bash
dsoxlab run k8s-creer-un-cluster-kind
```

La commande prépare la machine `k8s-kind.lab` et vous y connecte. Docker, kind
et kubectl sont installés. Pour vous laisser la mémoire, le lab a supprimé les
clusters des autres labs : aucun cluster kind ne tourne, et le répertoire
`~/atelier/` du challenge est vide. Les sorties ci-dessous ont été relevées sur
cette machine (Debian 13.7, 4 Go de mémoire, kind `v0.33.0`, Docker `29.9.3`)
le 19 novembre 2026.

## 📚 Exercice 1 : créer un cluster à un nœud, sur une image épinglée

Créez un cluster nommé `essai`. Précisez toujours l'image du nœud, avec son
digest : sans elle, kind prend la version figée dans son binaire.

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

Entre ces lignes, kind affiche ses étapes une à une : image du nœud,
préparation, configuration, démarrage du control plane, réseau (CNI) et
stockage. Regardez la ligne `Set kubectl context` : kind a déjà basculé
kubectl sur le nouveau cluster.

## 📚 Exercice 2 : voir ce que kind a créé sur la machine

Un nœud kind n'est qu'un conteneur Docker. Listez-le, puis demandez à kind ses
clusters.

```bash
docker ps --filter "name=essai" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
kind get clusters
```

```text
NAMES                 IMAGE                  STATUS
essai-control-plane   kindest/node:v1.37.0   Up 9 seconds
essai
```

Le conteneur porte le nom du cluster suivi de son rôle, `control-plane`. kind
ne connaît que ses propres clusters : un cluster créé par un autre outil
n'apparaîtrait pas ici.

## 📚 Exercice 3 : vérifier que le cluster est prêt

Un cluster qui répond n'est pas forcément prêt. Contrôlez le contexte, puis
laissez kubectl attendre que le nœud soit `Ready` avant de le lister.

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

La colonne `VERSION` confirme `v1.37.0`, la version de l'image épinglée.
Listez maintenant les composants système :

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

Tous les composants sont `Running` avant que vous ayez déployé quoi que ce
soit : `etcd`, les trois autres composants du control plane, le réseau
(`kindnet`, `kube-proxy`), la résolution de noms (`coredns`) et le stockage
local. Juste après la création, certains peuvent encore être en
`ContainerCreating` : relancez la commande quelques secondes plus tard.

## 📚 Exercice 4 : arrêter le cluster, puis le relancer

kind n'a pas de commande `stop`, mais ses nœuds sont des conteneurs. Arrêtez
celui du cluster `essai`, puis interrogez le cluster.

```bash
docker stop $(docker ps -q --filter "name=essai-")
kubectl get nodes
```

```text
e8568b1489b6
The connection to the server 127.0.0.1:45357 was refused - did you specify the right host or port?
```

Le conteneur arrêté, plus personne ne répond à l'adresse de l'API : c'est le
message que vous verrez chaque fois qu'un cluster est arrêté ou que le contexte
pointe ailleurs. Relancez le nœud et attendez qu'il soit prêt.

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

Le nœud est revenu `Ready`, et son `AGE` a continué de courir : rien n'a été
recréé. Arrêter un cluster libère sa mémoire sans rien perdre de son contenu.

## 📚 Exercice 5 : décrire un cluster dans un fichier

Au-delà d'un nœud, kind attend un fichier de configuration. Écrivez
`~/essai/kind-duo.yaml` : un control plane et un worker, ce dernier marqué
d'une zone.

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

Chaque entrée de la liste `nodes` est un nœud, et son `role` dit lequel.
L'image du nœud ne figure pas dans le fichier : elle se passe à la commande,
avec le nom du cluster et le chemin du fichier.

```bash
kind create cluster --name duo \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5 \
  --config ~/essai/kind-duo.yaml
```

```text title="Extrait de la sortie"
Creating cluster "duo" ...
Set kubectl context to "kind-duo"
```

Parmi les étapes affichées, une seule est nouvelle : `Joining worker nodes`,
où le worker rejoint le control plane. Attendez les deux nœuds, puis affichez
leur zone :

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

Le worker porte la zone déclarée dans le fichier. Sa colonne `ROLES` vaut
`<none>` : Kubernetes ne pose aucun libellé de rôle sur un worker, seul le
control plane en porte un. C'est normal.

## 📚 Exercice 6 : travailler avec deux clusters

Deux clusters tournent maintenant, mais kubectl ne parle qu'à un seul à la
fois. Listez les contextes, puis revenez sur `essai`.

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

L'astérisque était sur `kind-duo` : le dernier cluster créé devient le contexte
actif. Après `use-context`, `kubectl get nodes` montre bien le nœud d'`essai`.
Vérifier le contexte avant d'agir évite de travailler sur le mauvais cluster.

## 📚 Exercice 7 : supprimer un cluster

La suppression est définitive et sans confirmation : relisez le nom avant de
valider.

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

Le contexte `kind-duo` a disparu du kubeconfig avec le cluster. Seul `essai`
reste, et il est le contexte actif.

## 🧹 Nettoyage

Supprimez le cluster `essai` et le répertoire d'essai, puis vérifiez que la
machine est revenue à l'état de départ du challenge :

```bash
kind delete cluster --name essai
rm -r ~/essai
kind get clusters
kubectl config current-context
```

```text
Deleting cluster "essai" ...
Deleted nodes: ["essai-control-plane"]
No kind clusters found.
error: current-context is not set
```

Plus aucun cluster, et donc plus de contexte actif. Quittez la session et
vérifiez :

```bash
exit
dsoxlab check k8s-creer-un-cluster-kind
```

```text
╭─ Résultat : k8s-creer-un-cluster-kind ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests       │
╰────────────────────────────────────────╯
```

Zéro sur quatre : rien de ce que les exercices ont fait ne reste sur la
machine.

## 🎯 Le challenge

Faites maintenant le challenge seul : le cluster `atelier`, décrit dans son
propre fichier, avec un control plane et deux workers.

```bash
dsoxlab run k8s-creer-un-cluster-kind
dsoxlab challenge k8s-creer-un-cluster-kind
```
