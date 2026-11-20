# Resize a Pod in place, without restarting it

For a long time, changing a Pod's budget meant creating it again, and cutting
off what it was doing. Kubernetes can now **resize a Pod in place**: change
its requests and limits while it runs. In this course, you prepare a Pod for
resizing, you see the ordinary way refused, you go through the right door, you
choose which resource restarts the container, and you ask for an impossible
resize.

You work in a scratch namespace, `essai-resize`, with the `souple` ("flexible")
and `strict` Pods. The challenge will ask you to resize another Pod, in another
namespace: you will do it on your own, at the end.

Related page: [Requests and limits](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-in-place-pod-vertical-scaling
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a Pod ready to be resized

Create the scratch namespace and an nginx `souple` Pod. Its `resizePolicy`
block says, resource by resource, whether a change must restart the container:
here `NotRequired`, so no, neither for CPU nor for memory.

```bash
kubectl create namespace essai-resize
cat <<'YAML' | kubectl apply -n essai-resize -f -
apiVersion: v1
kind: Pod
metadata:
  name: souple
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 64Mi
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: NotRequired
YAML
kubectl wait --for=condition=Ready pod/souple -n essai-resize --timeout=120s
```

```text
namespace/essai-resize created
pod/souple created
pod/souple condition met
```

```bash
kubectl get pod souple -n essai-resize -o jsonpath='{range .spec.containers[0].resizePolicy[*]}{.resourceName}: {.restartPolicy}{"\n"}{end}'
```

```text
cpu: NotRequired
memory: NotRequired
```

Note the Pod's creation date, its number of restarts (`redemarrages`) and the
limits the kernel enforces (in the container's cgroup):

```bash
kubectl get pod souple -n essai-resize -o jsonpath='creation={.metadata.creationTimestamp} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'; kubectl exec souple -n essai-resize -- cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max
```

```text
creation=2026-11-20T05:56:18Z redemarrages=0
10000 100000
67108864
```

`10000 100000`: 10 % of one core, which is `100m`. `67108864` bytes, which is
`64Mi`.

## 📚 Exercise 2: the ordinary way is refused

Try to change the CPU limit with an ordinary `kubectl patch`:

```bash
kubectl patch pod souple -n essai-resize -p '{"spec":{"containers":[{"name":"web","resources":{"limits":{"cpu":"300m"}}}]}}' 2>&1 | head -1 | cut -c1-150
```

```text
The Pod "souple" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`,`spec.initContainers[*].image`,`
```

Refused: a Pod's resources cannot be changed the ordinary way, nor with
`kubectl edit` or `kubectl apply`. (`head` and `cut` shorten a very long
message.)

## 📚 Exercise 3: resize through the resize subresource

Resizing goes through a dedicated **subresource**, `resize`.
`kubectl patch --subresource resize` targets it. The patch names the container
(`web`) and its new resources:

```bash
kubectl patch pod souple -n essai-resize --subresource resize -p '{"spec":{"containers":[{"name":"web","resources":{"requests":{"cpu":"150m","memory":"48Mi"},"limits":{"cpu":"300m","memory":"96Mi"}}}]}}'
```

```text
pod/souple patched
```

The Pod holds two pieces of information: what is **requested** (in `spec`,
"demande"), and what the kubelet has really **applied** (in `status`,
"applique"). They can differ for a moment:

```bash
sleep 5; kubectl get pod souple -n essai-resize -o jsonpath='demande={.spec.containers[0].resources.limits} applique={.status.containerStatuses[0].resources.limits}{"\n"}'
```

```text
demande={"cpu":"300m","memory":"96Mi"} applique={"cpu":"300m","memory":"96Mi"}
```

Both are equal: the resize is done. Read the creation date, the restarts and
the cgroup again:

```bash
kubectl get pod souple -n essai-resize -o jsonpath='creation={.metadata.creationTimestamp} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'; kubectl exec souple -n essai-resize -- cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max
```

```text
creation=2026-11-20T05:56:18Z redemarrages=0
30000 100000
100663296
```

Same creation date, no restart: it is the same Pod, and its container was not
interrupted. The kernel already enforces the new limits: 30 % of one core
(`300m`) and `100663296` bytes (`96Mi`).

## 📚 Exercise 4: a policy that restarts the container

Some applications do not see a memory change until they restart. So the
`strict` Pod asks for a restart for memory (`RestartContainer`), but not for
CPU:

```bash
cat <<'YAML' | kubectl apply -n essai-resize -f -
apiVersion: v1
kind: Pod
metadata:
  name: strict
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 64Mi
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
YAML
kubectl wait --for=condition=Ready pod/strict -n essai-resize --timeout=120s
```

```text
pod/strict created
pod/strict condition met
```

Change its memory limit, then look at the Pod 10 seconds later:

```bash
kubectl patch pod strict -n essai-resize --subresource resize -p '{"spec":{"containers":[{"name":"web","resources":{"limits":{"memory":"128Mi"}}}]}}' && sleep 10; kubectl get pod strict -n essai-resize; kubectl exec strict -n essai-resize -- cat /sys/fs/cgroup/memory.max
```

```text
pod/strict patched
NAME     READY   STATUS    RESTARTS     AGE
strict   1/1     Running   1 (9s ago)   11s
134217728
```

`RESTARTS 1`: this time, the container restarted, as the policy asked. The Pod
itself is still the same one (`AGE 11s`), and the new limit (`134217728`
bytes, which is `128Mi`) is applied.

## 📚 Exercise 5: an impossible resize

Ask for 64 CPU cores for `souple`, more than the node has:

```bash
kubectl patch pod souple -n essai-resize --subresource resize -p '{"spec":{"containers":[{"name":"web","resources":{"requests":{"cpu":"64"},"limits":{"cpu":"64"}}}]}}'
```

```text
Error from server (Forbidden): pods "souple" is forbidden: node didn't have enough allocatable resources: cpu, requested: 64000, allocatable: 2000
```

Refused at once: the node only has 2 cores to give (`2000` thousandths). The
Pod keeps its previous budget:

```bash
kubectl get pod souple -n essai-resize -o jsonpath='demande={.spec.containers[0].resources.requests.cpu} applique={.status.containerStatuses[0].resources.requests.cpu}{"\n"}'
```

```text
demande=150m applique=150m
```

A Pod resized in place stays on its node. It can only grow within the room
that node still has.

## 🧹 Clean up

Delete the scratch namespace, with its Pods:

```bash
kubectl delete namespace essai-resize
```

```text
namespace "essai-resize" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-in-place-pod-vertical-scaling
dsoxlab check ckad-in-place-pod-vertical-scaling
```

```text
╭─ Result: ckad-in-place-pod-vertical-scaling ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests             │
╰──────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another Pod, which holds a session that must
not be interrupted, to resize without creating it again.

```bash
dsoxlab run ckad-in-place-pod-vertical-scaling
dsoxlab challenge ckad-in-place-pod-vertical-scaling
```
