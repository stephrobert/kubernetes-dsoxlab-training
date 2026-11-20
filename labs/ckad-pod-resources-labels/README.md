# A two-container Pod and its resource budgets

On a shared cluster, each container declares a **budget**: what it **asks
for** (requests), which the cluster reserves for it, and what it **will not
exceed** (limits), which the kernel enforces. In this course, you look at a Pod
with no budget, you give a budget to each container of a Pod, you read what the
kernel really enforces, you see the quality of service classes, then you make a
container go over its memory limit.

You work in a scratch namespace, `essai-budgets`, with the `libre` ("free"),
`borne` ("bounded"), `garanti` ("guaranteed") and `gourmand` ("greedy") Pods.
The challenge will ask you for other budgets, on another Pod, in another
namespace: you will do it on your own, at the end.

Related page: [Requests and limits](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-pod-resources-labels
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a Pod with no budget

Create the scratch namespace and a `libre` Pod, with no budget at all:

```bash
kubectl create namespace essai-budgets
kubectl run libre --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-budgets -- sh -c 'sleep 3600'; kubectl wait --for=condition=Ready pod/libre -n essai-budgets --timeout=60s
```

```text
namespace/essai-budgets created
pod/libre created
pod/libre condition met
```

Look at its resources and its quality of service (QoS) class:

```bash
kubectl get pod libre -n essai-budgets -o jsonpath='resources={.spec.containers[0].resources} qos={.status.qosClass}{"\n"}'
```

```text
resources={} qos=BestEffort
```

No budget, so the `BestEffort` class: the Pod takes what is left. The kernel
puts each container into a **cgroup**, a group whose resources it bounds. The
limits are read from inside the container:

```bash
kubectl exec libre -n essai-budgets -- cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/cpu.max
```

```text
max
max 100000
```

`max` everywhere: no limit, neither on memory nor on CPU.

## 📚 Exercise 2: a budget per container

Budgets are declared **container by container**, in a `resources` block, with
`requests` and `limits`. Create a `borne` Pod with two containers. Units
matter: `150m` means 150 thousandths of a CPU, so 0.15 core, and `48Mi` means
48 mebibytes.

```bash
cat <<'YAML' | kubectl apply -n essai-budgets -f -
apiVersion: v1
kind: Pod
metadata:
  name: borne
spec:
  containers:
    - name: site
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 150m
          memory: 48Mi
        limits:
          cpu: 300m
          memory: 96Mi
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "while true; do sleep 5; done"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
        limits:
          cpu: 50m
          memory: 24Mi
YAML
kubectl wait --for=condition=Ready pod/borne -n essai-budgets --timeout=120s
```

```text
pod/borne created
pod/borne condition met
```

The `compteur` container runs in a loop: a busybox image with no command would
stop at once. Read the budgets again ("demande" means "requests", "limite"
means "limit"):

```bash
kubectl get pod borne -n essai-budgets -o jsonpath='{range .spec.containers[*]}{.name}: demande {.resources.requests.cpu} et {.resources.requests.memory}, limite {.resources.limits.cpu} et {.resources.limits.memory}{"\n"}{end}'
```

```text
site: demande 150m et 48Mi, limite 300m et 96Mi
compteur: demande 20m et 16Mi, limite 50m et 24Mi
```

## 📚 Exercise 3: what the kernel enforces

A limit is not a wish: the kernel enforces it. Read the cgroup of each
container (`-c` picks the container):

```bash
for c in site compteur; do echo "$c : memory.max=$(kubectl exec borne -n essai-budgets -c $c -- cat /sys/fs/cgroup/memory.max) cpu.max=$(kubectl exec borne -n essai-budgets -c $c -- cat /sys/fs/cgroup/cpu.max)"; done
```

```text
site : memory.max=100663296 cpu.max=30000 100000
compteur : memory.max=25165824 cpu.max=5000 100000
```

Memory is in bytes. The shell does the conversion ("octets" means "bytes"):

```bash
echo "96Mi = $((96*1024*1024)) octets, 24Mi = $((24*1024*1024)) octets"
```

```text
96Mi = 100663296 octets, 24Mi = 25165824 octets
```

Both numbers match. For CPU, `30000 100000` means "30,000 microseconds of
computing per slice of 100,000": 30 % of one core, which is the `300m`
declared. And `5000 100000` is 5 %, which is `50m`.

## 📚 Exercise 4: the quality of service class

Create a `garanti` Pod whose requests are **equal** to its limits:

```bash
cat <<'YAML' | kubectl apply -n essai-budgets -f -
apiVersion: v1
kind: Pod
metadata:
  name: garanti
spec:
  containers:
    - name: site
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 100m
          memory: 64Mi
YAML
kubectl wait --for=condition=Ready pod/garanti -n essai-budgets --timeout=120s
```

```text
pod/garanti created
pod/garanti condition met
```

Compare the class of the three Pods:

```bash
kubectl get pods -n essai-budgets -o custom-columns=POD:.metadata.name,QOS:.status.qosClass
```

```text
POD       QOS
borne     Burstable
garanti   Guaranteed
libre     BestEffort
```

- `Guaranteed`: requests equal to limits, for every container;
- `Burstable`: a budget, but limits above the requests;
- `BestEffort`: no budget.

When a node runs short of memory, Kubernetes evicts the `BestEffort` Pods
first, then the `Burstable` ones, and the `Guaranteed` ones last.

## 📚 Exercise 5: go over the memory limit

The `gourmand` Pod has a 64 MiB limit, and its command tries to fill 200
(`head -c 200m /dev/zero | tail` keeps everything in memory; "je remplis la
memoire" means "I am filling memory"):

```bash
cat <<'YAML' | kubectl apply -n essai-budgets -f -
apiVersion: v1
kind: Pod
metadata:
  name: gourmand
spec:
  restartPolicy: Never
  containers:
    - name: appetit
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo je remplis la memoire; head -c 200m /dev/zero | tail"]
      resources:
        requests:
          memory: 32Mi
        limits:
          memory: 64Mi
YAML
```

```text
pod/gourmand created
```

15 seconds later:

```bash
sleep 15; kubectl get pod gourmand -n essai-budgets
kubectl get pod gourmand -n essai-budgets -o jsonpath='{.status.containerStatuses[0].state.terminated.reason} {.status.containerStatuses[0].state.terminated.exitCode}{"\n"}'
```

```text
NAME       READY   STATUS      RESTARTS   AGE
gourmand   0/1     OOMKilled   0          15s
OOMKilled 137
```

`OOMKilled`: the kernel killed the container because it went over its memory
limit (OOM means "out of memory"). Code 137 means a forced stop. CPU is
different: a container that goes over its CPU limit is slowed down, not
killed.

## 🧹 Clean up

Delete the scratch namespace, with its Pods:

```bash
kubectl delete namespace essai-budgets
```

```text
namespace "essai-budgets" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-pod-resources-labels
dsoxlab check ckad-pod-resources-labels
```

```text
╭─ Result: ckad-pod-resources-labels ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests    │
╰─────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another two-container Pod, with its own
budgets, which the kernel must enforce.

```bash
dsoxlab run ckad-pod-resources-labels
dsoxlab challenge ckad-pod-resources-labels
```
