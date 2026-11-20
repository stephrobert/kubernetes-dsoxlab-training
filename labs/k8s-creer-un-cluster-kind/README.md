# Create a multi-node kind cluster

kind creates a Kubernetes cluster on your machine. Each machine of the
cluster, called a **node**, is a Docker container there. The lesson shows how
to create, stop and delete a cluster. This course makes you meet the kind and
kubectl errors it does not show, and the failure of a node.

You work on scratch clusters, `kind`, `essai`, `duo` and `faux`. The challenge will ask you
for another cluster, `atelier`: you will build it on your own, at the end.

Related page: [Create your first Kubernetes cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/fundamentals/first-cluster/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-creer-un-cluster-kind
```

You are now connected to the `k8s-kind.lab` machine. Docker, kind and kubectl
are installed there. The lab installed kind for you: the lesson shows how to do
it while checking its fingerprint. To leave you enough memory, the lab deleted
the clusters of the other labs: no cluster is running. The challenge's
`~/atelier/` directory is empty.

The outputs shown in this course were recorded on this machine (Debian 13.7,
4 GB of memory, kind `v0.33.0`, Docker `29.9.3`) on 20 November 2026.

## 📚 Exercise 1: create a cluster without a name or an image

The lesson always gives `--name` and `--image`. See what kind does when you
leave them out:

```bash
kind create cluster
```

```text title="Excerpt of the output"
Creating cluster "kind" ...
Set kubectl context to "kind-kind"
```

Without `--name`, the cluster is called `kind`, and the kubectl context
`kind-kind`. Between these two lines, kind prints its steps, among them
`Ensuring node image (kindest/node:v1.37.0)`: the image it picked. Without
`--image`, kind takes the image chosen when it was built. Look at it:

```bash
docker ps --format "table {{.Names}}\t{{.Image}}"
```

```text
NAMES                IMAGE
kind-control-plane   kindest/node:v1.37.0
```

With this kind `v0.33.0`, it is `kindest/node:v1.37.0`, with no digest. The
version happens to be right here, by chance: another kind binary would have
given another Kubernetes version. And without a digest, the name `v1.37.0` can
point to another image the day it is republished. Delete this cluster:

```bash
kind delete cluster
```

```text
Deleting cluster "kind" ...
Deleted nodes: ["kind-control-plane"]
```

Without `--name`, `kind delete cluster` also targets the `kind` cluster, and
deletes it without asking for confirmation.

## 📚 Exercise 2: create a cluster whose name is already taken

Create the `essai` cluster the way the lesson does, with its name and its
image pinned by digest. Then run exactly the same command again:

```bash
kind create cluster --name essai \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
kind create cluster --name essai \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

```text title="End of the output"
ERROR: failed to create cluster: node(s) already exist for a cluster with the name "essai"
```

The first command creates the cluster. The second one refuses: kind never
replaces an existing cluster. To start from scratch, you must first run
`kind delete cluster --name essai`. Keep `essai`: you need it in the next
exercise.

## 📚 Exercise 3: check what survives a stop

The lesson states that a cluster stopped with `docker stop` keeps its objects.
Check it. First create a witness object: a **ConfigMap**, a small object that
stores settings. Note its **UID**, the unique identifier Kubernetes gives it
when it is created:

```bash
kubectl create configmap temoin --from-literal=couleur=vert
kubectl get configmap temoin -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
configmap/temoin created
30183449-6477-45af-abeb-ff7b1b4a3a42
```

Stop the `essai` node, then start it again:

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

The `Forbidden` refusal is temporary. The API server has just restarted: it
already answers, but it has not loaded yet the rules that say who may do what.
Depending on the moment, you may also see `connection refused`. Wait a few
seconds, run `kubectl wait` again, then read the witness again:

```bash
kubectl get configmap temoin -o jsonpath='{.metadata.uid} {.data.couleur}{"\n"}'
```

```text
30183449-6477-45af-abeb-ff7b1b4a3a42 vert
```

Same UID, same value: it is the same object, it was not recreated. The data of
the cluster lives in the node's container, and `docker stop` does not delete
the container.

## 📚 Exercise 4: read the error of a configuration file

A cluster of several nodes is described in a file. Write `~/essai/kind-duo.yaml`
for one control plane and one **worker**, the node that runs the applications.
Slip a mistake into it: `Worker` with a capital letter.

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

kind reads the file before creating anything. It names the faulty node by its
position in the list, counting from 0: node 1 is the second one. No `duo`
cluster was created. Fix the mistake:

```bash
sed -i "s/role: Worker/role: worker/" ~/essai/kind-duo.yaml
grep role ~/essai/kind-duo.yaml
```

```text
  - role: control-plane
  - role: worker
```

## 📚 Exercise 5: put the image in the file

Your file gives the image of each node with `image:`. So you no longer need
`--image`. Create `duo` with the file alone:

```bash
kind create cluster --name duo --config ~/essai/kind-duo.yaml
docker ps --filter "name=duo-" --format "table {{.Names}}\t{{.Image}}"
```

```text title="Excerpt of the output"
Creating cluster "duo" ...
Set kubectl context to "kind-duo"
NAMES               IMAGE
duo-worker          kindest/node:v1.37.0
duo-control-plane   kindest/node:v1.37.0
```

During the creation, the `Joining worker nodes` step attaches the worker to the
control plane. Both nodes run the image from the file. If you also give
`--image`, it wins, for every node. Check it with a file that names an image
that does not exist:

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

```text title="Excerpt of the output"
kindest/node:v1.37.0
Deleting cluster "faux" ...
Switched to context "kind-duo".
```

The `faux` cluster started on the `--image` image: the one in the file was
never downloaded. Both ways are valid: the image in the command, or node by
node in the file.

## 📚 Exercise 6: watch a worker go down

Stop the container of the `duo` worker, as if a machine broke down. Wait one
minute, then look at the nodes:

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

The node is not `NotReady` right away: on this machine, it became so after
about 55 seconds. Read why:

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

The **kubelet** is the program that runs on each node and reports to the
control plane. Its last message (`LastHeartbeatTime`) dates from 06:53:13. One
minute later (`LastTransitionTime`), with no news, the control plane set every
condition to `Unknown`. It does not know what happened to the node: it only
knows the node no longer answers. Start the worker again:

```bash
docker start duo-worker
kubectl wait --for=condition=Ready node/duo-worker --timeout=120s
```

```text
duo-worker
node/duo-worker condition met
```

## 📚 Exercise 7: delete the cluster you are working on

The active context is `kind-duo`. Delete this cluster, then run a kubectl
command:

```bash
kubectl config current-context
kind delete cluster --name duo
kubectl config current-context
kubectl get nodes
```

```text title="Excerpt of the output"
kind-duo
Deleting cluster "duo" ...
Deleted nodes: ["duo-worker" "duo-control-plane"]
error: current-context is not set
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

kind removed the `kind-duo` context with the cluster. kubectl has no active
context any more, and it falls back to a default address, `localhost:8080`,
where nothing listens. Several `memcache.go` lines come before this message:
they say the same thing. A message that names `localhost:8080` therefore
points to a kubectl without an active context, even if your clusters are
running. Pick one:

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

No star in the `CURRENT` column: no context was active. After `use-context`,
kubectl finds `essai` and its witness again.

## 🧹 Clean up

First delete what you created during the exercises: the `essai` cluster and
the `~/essai` directory.

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

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-creer-un-cluster-kind
dsoxlab check k8s-creer-un-cluster-kind
```

```text
╭─ Result: k8s-creer-un-cluster-kind ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests    │
╰─────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you, untouched.

## 🎯 The challenge

Your turn, on your own this time: create the `atelier` cluster, described in
its own file, with one control plane and two workers.

```bash
dsoxlab run k8s-creer-un-cluster-kind
dsoxlab challenge k8s-creer-un-cluster-kind
```
