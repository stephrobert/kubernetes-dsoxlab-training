# Create a multi-node kind cluster

This course has you practise, on the lab machine, every move of the lesson:
create a kind cluster on a pinned image, see what it set up, check that it is
ready, stop and restart it, describe it in a file, work with two clusters, then
delete them. You work on two scratch clusters, `essai` and `duo`: the
challenge's `atelier` cluster is left for the end.

Related page: [Create your first Kubernetes cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/fundamentals/first-cluster/).

## 🔧 Before you start

```bash
dsoxlab run k8s-creer-un-cluster-kind
```

The command prepares the `k8s-kind.lab` machine and connects you to it. Docker,
kind and kubectl are installed. To leave you the memory, the lab deleted the
clusters of the other labs: no kind cluster is running, and the challenge's
`~/atelier/` directory is empty. The outputs below were recorded on this
machine (Debian 13.7, 4 GB of memory, kind `v0.33.0`, Docker `29.9.3`) on
19 November 2026.

## 📚 Exercise 1: create a single-node cluster, on a pinned image

Create a cluster named `essai`. Always give the node image, with its digest:
without it, kind uses the version frozen in its binary.

```bash
kind create cluster --name essai \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

```text title="Excerpt of the output"
Creating cluster "essai" ...
Set kubectl context to "kind-essai"
You can now use your cluster with:

kubectl cluster-info --context kind-essai
```

Between these lines, kind shows its steps one by one: node image, preparation,
configuration, control plane start, network (CNI) and storage. Look at the
`Set kubectl context` line: kind has already switched kubectl to the new
cluster.

## 📚 Exercise 2: see what kind created on the machine

A kind node is nothing but a Docker container. List it, then ask kind for its
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

The container is named after the cluster, followed by its role,
`control-plane`. kind only knows its own clusters: a cluster created by
another tool would not show up here.

## 📚 Exercise 3: check that the cluster is ready

A cluster that answers is not necessarily ready. Check the context, then let
kubectl wait for the node to be `Ready` before listing it.

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

The `VERSION` column confirms `v1.37.0`, the version of the pinned image. Now
list the system components:

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

Every component is `Running` before you have deployed anything: `etcd`, the
three other control plane components, the network (`kindnet`, `kube-proxy`),
name resolution (`coredns`) and local storage. Right after creation, some may
still be in `ContainerCreating`: run the command again a few seconds later.

## 📚 Exercise 4: stop the cluster, then restart it

kind has no `stop` command, but its nodes are containers. Stop the one of the
`essai` cluster, then query the cluster.

```bash
docker stop $(docker ps -q --filter "name=essai-")
kubectl get nodes
```

```text
e8568b1489b6
The connection to the server 127.0.0.1:45357 was refused - did you specify the right host or port?
```

With the container stopped, nobody answers at the API address anymore: this is
the message you will see whenever a cluster is stopped or the context points
elsewhere. Restart the node and wait for it to be ready.

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

The node is back to `Ready`, and its `AGE` kept running: nothing was
recreated. Stopping a cluster frees its memory without losing any of its
content.

## 📚 Exercise 5: describe a cluster in a file

Beyond one node, kind expects a configuration file. Write
`~/essai/kind-duo.yaml`: one control plane and one worker, the latter tagged
with a zone.

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

Each entry of the `nodes` list is a node, and its `role` says which one. The
node image is not in the file: it is passed to the command, with the cluster
name and the file path.

```bash
kind create cluster --name duo \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5 \
  --config ~/essai/kind-duo.yaml
```

```text title="Excerpt of the output"
Creating cluster "duo" ...
Set kubectl context to "kind-duo"
```

Among the steps shown, only one is new: `Joining worker nodes`, where the
worker joins the control plane. Wait for both nodes, then show their zone:

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

The worker carries the zone declared in the file. Its `ROLES` column shows
`<none>`: Kubernetes sets no role label on a worker, only the control plane
gets one. That is expected.

## 📚 Exercise 6: work with two clusters

Two clusters are now running, but kubectl only talks to one at a time. List
the contexts, then go back to `essai`.

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

The asterisk was on `kind-duo`: the last cluster created becomes the active
context. After `use-context`, `kubectl get nodes` does show the node of
`essai`. Checking the context before acting keeps you from working on the
wrong cluster.

## 📚 Exercise 7: delete a cluster

Deletion is final and asks for no confirmation: read the name again before
pressing Enter.

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

The `kind-duo` context left the kubeconfig together with the cluster. Only
`essai` remains, and it is the active context.

## 🧹 Clean up

Delete the `essai` cluster and the scratch directory, then check that the
machine is back to the starting state of the challenge:

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

No cluster left, and so no active context. Leave the session and check:

```bash
exit
dsoxlab check k8s-creer-un-cluster-kind
```

```text
╭─ Result: k8s-creer-un-cluster-kind ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests    │
╰─────────────────────────────────────╯
```

Zero out of four: nothing the exercises did is left on the machine.

## 🎯 The challenge

Now do the challenge on your own: the `atelier` cluster, described in its own
file, with one control plane and two workers.

```bash
dsoxlab run k8s-creer-un-cluster-kind
dsoxlab challenge k8s-creer-un-cluster-kind
```
