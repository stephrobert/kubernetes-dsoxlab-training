# Create a multi-node kind cluster

kind is a tool that creates a Kubernetes cluster on your machine. Each machine
of the cluster, called a **node**, is just a Docker container there. In this
course, you redo the moves of the lesson: create a cluster, see what kind
created, check that it is ready, stop it, describe it in a file, switch from
one cluster to another, then delete them.

You work on two scratch clusters, `essai` and `duo`. The challenge will ask you
for another cluster, `atelier`: you will build it on your own, at the end.

Related page: [Create your first Kubernetes cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/fundamentals/first-cluster/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-creer-un-cluster-kind
```

You are now connected to the `k8s-kind.lab` machine. Docker, kind and kubectl
are installed there. To leave you enough memory, the lab deleted the clusters
of the other labs: no cluster is running. The challenge's `~/atelier/`
directory is empty.

The outputs shown in this course were recorded on this machine (Debian 13.7,
4 GB of memory, kind `v0.33.0`, Docker `29.9.3`) on 19 November 2026.

## 📚 Exercise 1: create a single-node cluster

Create a cluster named `essai`. The `--image` option picks the node image, and
so the Kubernetes version. The `@sha256:...` part is the image **digest**: it
guarantees you get exactly the intended image, even if someone republishes an
image under the same name.

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

Between these lines, kind shows its steps one by one, with small pictures.
Look at the `Set kubectl context` line: kind set kubectl up to talk to this new
cluster. We say kubectl uses the `kind-essai` **context**.

## 📚 Exercise 2: see what kind created

A kind node is a Docker container. List the containers whose name contains
`essai`, then ask kind for the list of its clusters:

```bash
docker ps --filter "name=essai" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
kind get clusters
```

```text
NAMES                 IMAGE                  STATUS
essai-control-plane   kindest/node:v1.37.0   Up 9 seconds
essai
```

A single container, `essai-control-plane`. The **control plane** is the node
that runs the cluster. In a single-node cluster, it also runs your
applications.

## 📚 Exercise 3: check that the cluster is ready

A cluster that answers is not necessarily ready to work. First check that
kubectl targets `essai`, then wait for the node to be ready before showing it:

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

`kubectl wait` waits for every node to be `Ready`, then gives the prompt back.
The `VERSION` column shows `v1.37.0`: the version of the image you picked.

Now list the programs Kubernetes runs for itself:

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

You have deployed nothing yet, and still nine programs are running: they are
the components of the cluster itself (database, network, names, storage). They
must all be `Running`. Right after creation, some may still show
`ContainerCreating`: wait a few seconds and run the command again.

## 📚 Exercise 4: stop the cluster, then restart it

kind has no command to stop a cluster. But since a node is a container, Docker
can stop it. Stop the node of `essai`, then query the cluster:

```bash
docker stop $(docker ps -q --filter "name=essai-")
kubectl get nodes
```

```text
e8568b1489b6
The connection to the server 127.0.0.1:45357 was refused - did you specify the right host or port?
```

Nothing answers anymore. Remember this message: you will see it whenever a
cluster is stopped, or kubectl targets the wrong cluster. Restart the node and
wait for it to be ready:

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

The node is `Ready` again. Its age (`AGE`) kept growing: nothing was
recreated. Stopping a cluster frees memory without losing anything.

## 📚 Exercise 5: describe a cluster in a file

For a cluster of several nodes, kind needs a file that describes the nodes.
Write `~/essai/kind-duo.yaml`: one control plane and one **worker**, a node
that runs applications. The worker gets a **zone** label, as in a real data
centre.

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

Each item of the `nodes` list is a node, and `role` says which one. The image
does not go in this file: you give it to the command, with the cluster name and
the file path.

```bash
kind create cluster --name duo \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5 \
  --config ~/essai/kind-duo.yaml
```

```text title="Excerpt of the output"
Creating cluster "duo" ...
Set kubectl context to "kind-duo"
```

One step is added to those of exercise 1: `Joining worker nodes`, during which
the worker joins the control plane. Wait for both nodes, then show them with
their zone:

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

The worker carries the zone written in the file. Its `ROLES` column shows
`<none>`: that is expected, Kubernetes only writes the role on the control
plane.

## 📚 Exercise 6: switch from one cluster to another

Two clusters are now running, but kubectl only talks to one at a time. List
the contexts, then go back to `essai`:

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

The asterisk shows the context in use: it was `kind-duo`, the last cluster
created. After `use-context`, `kubectl get nodes` does show the node of
`essai`. Make a habit of checking the context before acting: it keeps you from
working on the wrong cluster.

## 📚 Exercise 7: delete a cluster

Deletion is final, and kind asks for no confirmation. Read the name again
before pressing Enter.

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

The `kind-duo` context disappeared together with the cluster. Only `essai` is
left.

## 🧹 Clean up

First delete what you created during the exercises: the `essai` cluster and the `~/essai` directory.

```bash
kind delete cluster --name essai
rm -r ~/essai
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
